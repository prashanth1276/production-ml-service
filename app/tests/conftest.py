"""Shared test fixtures. Uses mock LLM, stub DB, and disabled rate limiting."""
import os

os.environ["LLM_BACKEND"] = "mock"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(scope="session")
def client():
    with patch("redis.asyncio.from_url") as mock_redis_factory:
        mock_redis = MagicMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.evalsha = AsyncMock(return_value=0)
        mock_redis_factory.return_value = mock_redis

        from app.main import app
        with TestClient(app) as c:
            yield c


@pytest.fixture
def sample_products():
    return [
        {"id": "prod001", "name": "Blue T-Shirt",
         "description": "Comfortable cotton t-shirt", "category": "Clothing",
         "price": 499},
        {"id": "prod002", "name": "Black Sneakers",
         "description": "Stylish sneakers", "category": "Footwear",
         "price": 799},
        {"id": "prod003", "name": "Running Shoes",
         "description": "Performance running shoes", "category": "Footwear",
         "price": 899},
    ]