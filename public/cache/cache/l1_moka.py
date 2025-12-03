from typing import Any, Optional, Union, Dict
from datetime import timedelta, datetime
from .base import BaseCache

try:
    from moka import Moka
except Exception:
    Moka = None

try:
    from cacheout import Cache
except Exception:
    Cache = None

class SimpleCache:
    def __init__(self, maxsize: int = 10000, ttl: int = 3600):
        self.store: Dict[str, Any] = {}
        self.expire: Dict[str, float] = {}
        self.maxsize = maxsize
        self.ttl = ttl

    def _now(self) -> float:
        return datetime.now().timestamp()

    def _expired(self, key: str) -> bool:
        ts = self.expire.get(key)
        return ts is not None and ts <= self._now()

    def get(self, key: str) -> Any:
        if key in self.store and not self._expired(key):
            return self.store.get(key)
        self.store.pop(key, None)
        self.expire.pop(key, None)
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if len(self.store) >= self.maxsize and key not in self.store:
            if self.store:
                self.store.pop(next(iter(self.store)))
        self.store[key] = value
        ttl_seconds = int(ttl) if ttl is not None else self.ttl
        self.expire[key] = self._now() + ttl_seconds

    def delete(self, key: str) -> None:
        self.store.pop(key, None)
        self.expire.pop(key, None)

    def has(self, key: str) -> bool:
        return key in self.store and not self._expired(key)

    def clear(self) -> None:
        self.store.clear()
        self.expire.clear()

    def size(self) -> int:
        return len(self.store)

class MokaCache(BaseCache):
    """
    L1 Cache implementation using Moka (High performance Rust-based cache)
    or fallback to Cacheout/Dict if Moka is not available.
    """
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.use_moka = Moka is not None
        
        if self.use_moka:
            self._cache = Moka(
                capacity=max_size,
                time_to_live=timedelta(seconds=default_ttl)
            )
        elif Cache is not None:
            self._cache = Cache(maxsize=max_size, ttl=default_ttl)
        else:
            self._cache = SimpleCache(maxsize=max_size, ttl=default_ttl)

    def get(self, key: str) -> Any:
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> None:
        if ttl is None:
            ttl_seconds = self.default_ttl
        elif isinstance(ttl, timedelta):
            ttl_seconds = int(ttl.total_seconds())
        else:
            ttl_seconds = int(ttl)
            
        if self.use_moka:
            self._cache.insert(key, value)
        else:
            self._cache.set(key, value, ttl=ttl_seconds)

    def delete(self, key: str) -> None:
        if self.use_moka:
            self._cache.remove(key)
        else:
            self._cache.delete(key)

    def exists(self, key: str) -> bool:
        if self.use_moka:
            return self._cache.contains(key)
        else:
            return self._cache.has(key)

    def clear(self) -> None:
        if self.use_moka:
            self._cache.invalidate_all()
        else:
            self._cache.clear()

    def close(self) -> None:
        pass

    def get_stats(self) -> Dict[str, Any]:
        if self.use_moka:
            return {
                "type": "moka",
                "size": self._cache.entry_count(),
                "max_size": self.max_size
            }
        if Cache is not None:
            return {
                "type": "cacheout",
                "size": self._cache.size(),
                "max_size": self._cache.maxsize
            }
        return {
            "type": "simple",
            "size": self._cache.size(),
            "max_size": self.max_size
        }
