"""Unit tests for the recommendation engine (FAISS + embeddings)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def fake_products():
    return [
        {"id": "p1", "name": "Blue Shirt", "description": "cotton shirt"},
        {"id": "p2", "name": "Red Shoes", "description": "running shoes"},
        {"id": "p3", "name": "Green Hat", "description": "sun hat"},
    ]


@pytest.fixture
def mock_redis():
    client = MagicMock()
    client.get = AsyncMock(return_value=None)
    client.setex = AsyncMock(return_value=True)
    client.ping = AsyncMock(return_value=True)
    return client


@pytest.mark.asyncio
async def test_engine_builds_index(fake_products, mock_redis):
    with (
        patch("app.utils.db.db.get_products", return_value=fake_products),
        patch("redis.asyncio.from_url", return_value=mock_redis),
    ):
        from app.services.rec_engine import RecommendationEngine

        engine = RecommendationEngine()
        await engine._build_index()
        assert engine.index is not None
        assert engine.index.ntotal == 3
        assert engine.product_ids == ["p1", "p2", "p3"]


@pytest.mark.asyncio
async def test_engine_handles_empty_catalog(mock_redis):
    with (
        patch("app.utils.db.db.get_products", return_value=[]),
        patch("redis.asyncio.from_url", return_value=mock_redis),
    ):
        from app.services.rec_engine import RecommendationEngine

        engine = RecommendationEngine()
        await engine._build_index()
        assert engine.index is not None
        assert engine.index.ntotal == 0
        recs = await engine.get_recommendations("anything")
        assert recs == []


@pytest.mark.asyncio
async def test_engine_returns_top_k(fake_products, mock_redis):
    with (
        patch("app.utils.db.db.get_products", return_value=fake_products),
        patch("app.utils.db.db.get_user", return_value=None),
        patch("redis.asyncio.from_url", return_value=mock_redis),
    ):
        from app.services.rec_engine import RecommendationEngine

        engine = RecommendationEngine()
        recs = await engine.get_recommendations("shoes", top_k=2)
        assert len(recs) <= 2
        assert all(isinstance(r, str) for r in recs)
