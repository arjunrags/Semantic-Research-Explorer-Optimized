import redis.asyncio as aioredis
import json
import hashlib
from typing import Optional, Any
from core.config import get_settings
from core.logging import logger

settings = get_settings()

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def cache_key(*parts: str) -> str:
    return ":".join(["sre"] + list(parts))


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def cache_get(key: str) -> Optional[Any]:
    try:
        r = await get_redis()
        raw = await r.get(key)
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning("cache_get_error", key=key, error=str(e))
        return None


async def cache_set(key: str, value: Any, ttl: int) -> bool:
    try:
        r = await get_redis()
        await r.setex(key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.warning("cache_set_error", key=key, error=str(e))
        return False


async def cache_delete(key: str) -> bool:
    try:
        r = await get_redis()
        await r.delete(key)
        return True
    except Exception as e:
        logger.warning("cache_delete_error", key=key, error=str(e))
        return False
