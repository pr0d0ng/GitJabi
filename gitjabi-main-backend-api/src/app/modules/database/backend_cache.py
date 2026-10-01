from typing import Generic, TypeVar, Optional, Any
from abc import ABC, abstractmethod
import redis.asyncio as redis
from cachetools import TTLCache
import json

CacheT = TypeVar('CacheT')

class CacheBackend(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int]=None):
        pass


class LocalCacheBackend(CacheBackend):
    def __init__(self, maxsize=100, ttl=3000):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)

    async def get(self, key: str):
        return self._cache.get(key)

    async def set(self, key: str, value: Any, ttl=None):
        self._cache[key] = value
        if ttl:
            raise RuntimeError(
                "Local Cache not support local ttl."
            )


class RedisCacheBackend(CacheBackend):
    def __init__(self, redis_url: str):
        self._redis = redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str):
        data = await self._redis.get(key)
        return json.loads(data) if data else None

    async def set(self, key: str, value: Any, ttl: Optional[int]=None):
        await self._redis.set(key, json.dumps(value), ex=ttl)

