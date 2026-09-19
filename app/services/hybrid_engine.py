"""Hybrid retrieval: dense (FAISS) + sparse (BM25) fused via RRF.

Optional cross-encoder reranking on the fused candidate list.

Selected via RETRIEVAL_MODE env var:
  dense          -> FAISS only (default, preserves existing behavior)
  hybrid         -> FAISS + BM25 with Reciprocal Rank Fusion
  hybrid_rerank  -> hybrid + cross-encoder reranking of top-K candidates
"""

import logging

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from app.services.rec_engine import RecommendationEngine
from app.utils.db import db

logger = logging.getLogger(__name__)

RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RRF_K = 60  # standard RRF constant


class HybridEngine:
    def __init__(self, dense: RecommendationEngine, mode: str = "dense"):
        self.dense = dense
        self.mode = mode
        self._bm25 = None
        self._bm25_product_ids: list[str] = []
        self._reranker = None

    def _ensure_bm25(self) -> None:
        if self._bm25 is not None:
            return
        products = db.get_products()
        if not products:
            self._bm25_product_ids = []
            self._bm25 = BM25Okapi([[""]])
            return
        self._bm25_product_ids = [p["id"] for p in products]
        corpus = [
            f"{p['name']} {p.get('description', '')} {p.get('category', '')}".lower().split()
            for p in products
        ]
        self._bm25 = BM25Okapi(corpus)

    def _ensure_reranker(self) -> None:
        if self._reranker is None:
            self._reranker = CrossEncoder(RERANK_MODEL)

    async def get_recommendations(
        self,
        query: str,
        user_id: str | None = None,
        top_k: int = 3,
    ) -> list[str]:
        if self.mode == "dense":
            return await self.dense.get_recommendations(query, user_id=user_id, top_k=top_k)

        # ---- Candidate generation ----
        pool = max(top_k * 4, 20)

        dense_ids = await self.dense.get_recommendations(query, user_id=user_id, top_k=pool)
        sparse_ids = self._bm25_search(query, top_k=pool)

        fused = self._rrf_fuse(dense_ids, sparse_ids)[:pool]

        if self.mode == "hybrid":
            return fused[:top_k]

        # ---- hybrid_rerank ----
        self._ensure_reranker()
        products = {p["id"]: p for p in db.get_products_by_ids(fused)}
        pairs = [
            (query, f"{products[i]['name']} {products[i].get('description', '')}")
            for i in fused
            if i in products
        ]
        scores = self._reranker.predict(pairs)
        order = np.argsort(-scores)
        reranked = [fused[i] for i in order]
        return reranked[:top_k]

    def _bm25_search(self, query: str, top_k: int) -> list[str]:
        self._ensure_bm25()
        if not self._bm25_product_ids:
            return []
        tokens = query.lower().split()
        scores = self._bm25.get_scores(tokens)
        order = np.argsort(-scores)[:top_k]
        return [self._bm25_product_ids[i] for i in order]

    @staticmethod
    def _rrf_fuse(dense_ids: list[str], sparse_ids: list[str]) -> list[str]:
        scores: dict[str, float] = {}
        for rank, doc_id in enumerate(dense_ids, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
        for rank, doc_id in enumerate(sparse_ids, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RRF_K + rank)
        return [d for d, _ in sorted(scores.items(), key=lambda x: -x[1])]
