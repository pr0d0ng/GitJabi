from enum import Enum, auto

__all__ = (
    'CacheBackendEnum',
)

class CacheBackendEnum(Enum):
    LOCAL_CACHE = auto()
    REDIS = auto()
