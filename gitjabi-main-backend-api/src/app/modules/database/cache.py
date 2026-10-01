from typing import Generic, Optional, Any
from app.modules.database.backend_cache import CacheT, LocalCacheBackend, RedisCacheBackend

from app.settings import api_settings, CacheBackendEnum

class CacheProxy(Generic[CacheT]):
    def __init__(self, **kwargs):
        if api_settings.CACHE_BACKEND == CacheBackendEnum.LOCAL_CACHE:
            self._backend = LocalCacheBackend(**kwargs)
        elif api_settings.CACHE_BACKEND == CacheBackendEnum.LOCAL_CACHE:
            self._backend = RedisCacheBackend(**kwargs)
        else:
            raise RuntimeError(
                f"Invalid configuration for cache: {api_settings.CACHE_BACKEND}"
            ) 

    async def acontains(self, key: Any) -> bool:
        return await self.aget(key) is not None

    async def aget(self, key: Any):
        return await self._backend.get(key)

    async def aset(self, key: Any, value: Any, ttl: Optional[int] = None):
        await self._backend.set(key, value, ttl)

    async def aget_or_aset(self, key: Any, creator_func, ttl: Optional[int] = None):
        """유틸리티: 캐시가 있으면 가져오고, 없으면 생성해서 저장 - Get or Set"""
        cached = await self.aget(key)
        if cached is not None:
            return cached
        
        new_value = await creator_func()
        await self.aset(key, new_value, ttl)
        return new_value
