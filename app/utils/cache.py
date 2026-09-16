"""Redis cache helpers. Fail-safe: returns None on connection errors."""

import logging

import redis.asyncio as redis

from app.utils.config import get_settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            get_settings().redis_url,
            decode_responses=False,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


async def cache_get(key: str) -> bytes | None:
    if not get_settings().redis_enabled:
        return None
    try:
        return await get_redis().get(key)
    except Exception as e:
        logger.warning(f"Cache GET failed for {key}: {e}")
        return None


async def cache_set(key: str, value: bytes | str, ttl: int = 3600) -> bool:
    if not get_settings().redis_enabled:
        return False
    try:
        if isinstance(value, str):
            value = value.encode()
        await get_redis().setex(key, ttl, value)
        return True
    except Exception as e:
        logger.warning(f"Cache SET failed for {key}: {e}")
        return False


async def cache_ping() -> bool:
    if not get_settings().redis_enabled:
        return False
    try:
        await get_redis().ping()
        return True
    except Exception as e:
        logger.warning(f"Cache PING failed: {e}")
        return False
