"""Semantic search recommendation engine using FAISS + sentence-transformers."""
import asyncio
import json
import logging
import time as _time

import faiss
import numpy as np
import redis.asyncio as redis
from sentence_transformers import SentenceTransformer

from app.utils.config import get_settings
from app.utils.metrics import (
    CACHE_HIT, CACHE_MISS, INDEX_SIZE, RECOMMENDATION_COUNT, RETRIEVAL_LATENCY,
)
from app.utils.db import db

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
EMBEDDING_CACHE_KEY = "product_embeddings_v1"
EMBEDDING_TTL = 86400  # 24 hours


class RecommendationEngine:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.index: faiss.Index | None = None
        self.product_ids: list[str] = []
        self._lock = asyncio.Lock()
        self.redis = redis.from_url(
            get_settings().redis_url,
            decode_responses=False,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

    # ------------------------------------------------------------------
    # Sync wrappers (used by eval scripts)
    # ------------------------------------------------------------------
    def build_index_sync(self) -> None:
        """Sync wrapper for index building."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                new_loop = asyncio.new_event_loop()
                new_loop.run_until_complete(self._build_index())
                new_loop.close()
            else:
                loop.run_until_complete(self._build_index())
        except RuntimeError:
            asyncio.run(self._build_index())

    def get_recommendations_sync(
        self,
        user_query: str,
        user_id: str | None = None,
        top_k: int = 3,
    ) -> list[str]:
        """Sync wrapper for get_recommendations."""
        try:
            return asyncio.run(
                self.get_recommendations(user_query, user_id=user_id, top_k=top_k)
            )
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self.get_recommendations(user_query, user_id=user_id, top_k=top_k)
                )
            finally:
                loop.close()

    # ------------------------------------------------------------------
    # Index building
    # ------------------------------------------------------------------
    async def _build_index(self) -> None:
        """Build FAISS index from product catalog. Caches embeddings in Redis."""
        async with self._lock:
            if self.index is not None:
                return

            products = db.get_products()
            if not products:
                logger.warning("No products in DB — cannot build index")
                self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
                self.product_ids = []
                INDEX_SIZE.set(0)
                return

            self.product_ids = [p["id"] for p in products]

            cached = await self._cache_get(EMBEDDING_CACHE_KEY)
            if cached:
                embeddings = np.frombuffer(cached, dtype=np.float32).reshape(
                    -1, EMBEDDING_DIM
                )
                logger.info(f"Loaded {len(embeddings)} embeddings from cache")
            else:
                texts = [
                    f"{p['name']} {p.get('description', '')}" for p in products
                ]
                embeddings = self.model.encode(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                await self._cache_set(
                    EMBEDDING_CACHE_KEY,
                    embeddings.astype(np.float32).tobytes(),
                    EMBEDDING_TTL,
                )
                logger.info(f"Computed {len(embeddings)} embeddings")

            self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
            self.index.add(embeddings.astype(np.float32))
            INDEX_SIZE.set(self.index.ntotal)

    # ------------------------------------------------------------------
    # Cache helpers (fail-safe: Redis outages never crash the app)
    # ------------------------------------------------------------------
    async def _cache_get(self, key: str):
        if not get_settings().redis_enabled:
            return None
        try:
            result = await self.redis.get(key)
            if result is not None:
                CACHE_HIT.labels(cache_type=self._cache_type(key)).inc()
            else:
                CACHE_MISS.labels(cache_type=self._cache_type(key)).inc()
            return result
        except Exception as e:
            logger.warning(f"Redis GET failed: {e}")
            return None

    @staticmethod
    def _cache_type(key: str) -> str:
        if key.startswith("product_embeddings"):
            return "embeddings"
        if key.startswith("rec:"):
            return "recommendations"
        if key.startswith("desc:"):
            return "descriptions"
        return "other"

    async def _cache_set(self, key: str, value: bytes, ttl: int) -> None:
        if not get_settings().redis_enabled:
            return
        try:
            await self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Redis SET failed: {e}")

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------
    async def get_recommendations(
        self,
        user_query: str,
        user_id: str | None = None,
        top_k: int = 3,
    ) -> list[str]:
        await self._build_index()

        if self.index is None or self.index.ntotal == 0:
            return []

        query_text = self._augment_query(user_query, user_id)

        cache_key = f"rec:{user_query}:{user_id or 'anon'}:{top_k}"
        cached = await self._cache_get(cache_key)
        if cached:
            try:
                recommended = json.loads(cached)
                RECOMMENDATION_COUNT.inc(len(recommended))
                return recommended
            except json.JSONDecodeError:
                pass

        _t0 = _time.perf_counter()

        q_emb = self.model.encode(
            [query_text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

        k = min(top_k, self.index.ntotal)
        _, indices = self.index.search(q_emb, k)
        recommended = [
            self.product_ids[i] for i in indices[0] if 0 <= i < len(self.product_ids)
        ]

        RETRIEVAL_LATENCY.observe(_time.perf_counter() - _t0)
        RECOMMENDATION_COUNT.inc(len(recommended))

        await self._cache_set(cache_key, json.dumps(recommended).encode(), 3600)
        return recommended

    async def get_scores(
        self,
        user_query: str,
        user_id: str | None = None,
        top_k: int = 3,
    ) -> list[tuple[str, float]]:
        """Like get_recommendations but returns (product_id, similarity)."""
        await self._build_index()

        if self.index is None or self.index.ntotal == 0:
            return []

        query_text = self._augment_query(user_query, user_id)

        q_emb = self.model.encode(
            [query_text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(q_emb, k)
        return [
            (self.product_ids[i], float(s))
            for i, s in zip(indices[0], scores[0])
            if 0 <= i < len(self.product_ids)
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _augment_query(self, user_query: str, user_id: str | None) -> str:
        """Append user context (purchase history + preferences) to the query."""
        if not user_id:
            return user_query
        user = db.get_user(user_id)
        if not user:
            return user_query

        context_parts: list[str] = []
        for p in user.get("purchase_history", []):
            if isinstance(p, dict):
                context_parts.append(p.get("product_id", ""))
            else:
                context_parts.append(str(p))
        context_parts.extend(user.get("preferences", []))

        if not context_parts:
            return user_query
        return f"{user_query} {' '.join(context_parts)}"


_engine: RecommendationEngine | None = None


def get_rec_engine() -> RecommendationEngine:
    global _engine
    if _engine is None:
        _engine = RecommendationEngine()
    return _engine


class _LazyEngine:
    def __getattr__(self, name):
        return getattr(get_rec_engine(), name)


rec_engine = _LazyEngine()