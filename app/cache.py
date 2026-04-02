import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            f"redis://{settings.redis_host}:{settings.redis_port}",
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def cache_get(key: str) -> Any | None:
    try:
        redis = await get_redis()
        value = await redis.get(key)
        if value:
            logger.info(f"Cache HIT: {key}")
            return json.loads(value)
        logger.info(f"Cache MISS: {key}")
        return None
    except Exception as e:
        logger.warning(f"Cache GET error for '{key}': {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    try:
        redis = await get_redis()
        await redis.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
        logger.info(f"Cache SET: {key} (TTL={ttl}s)")
    except Exception as e:
        logger.warning(f"Cache SET error for '{key}': {e}")


async def cache_delete(key: str) -> None:
    try:
        redis = await get_redis()
        await redis.delete(key)
        logger.info(f"Cache DELETE: {key}")
    except Exception as e:
        logger.warning(f"Cache DELETE error for '{key}': {e}")


async def cache_delete_pattern(pattern: str) -> None:
    try:
        redis = await get_redis()
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            logger.info(f"Cache DELETE pattern '{pattern}': {len(keys)} keys")
    except Exception as e:
        logger.warning(f"Cache DELETE pattern error for '{pattern}': {e}")


# Ключи кеша
# v2: safety_level, cost_level, cost_per_day_usd в GeoJSON properties
GEODATA_KEY = "countries:geodata:v2"
VISA_MAP_KEY = "visa_map:{iso2}"

# TTL в секундах
GEODATA_TTL = 60 * 60 * 24      # 24 часа — границы стран не меняются
VISA_MAP_TTL = 60 * 60           # 1 час — визовые режимы меняются редко