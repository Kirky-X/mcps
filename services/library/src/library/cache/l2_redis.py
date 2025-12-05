try:
    import redis  # type: ignore
except Exception:
    redis = None
import pickle
from typing import Any, Optional, Union, Dict
from datetime import timedelta
from .base import BaseCache

class RedisCache(BaseCache):
    def __init__(
        self, 
        host: str = 'localhost', 
        port: int = 6379, 
        db: int = 0, 
        password: Optional[str] = None,
        default_ttl: int = 3600,
        key_prefix: str = "cache:",
        redis_client: Optional[redis.Redis] = None
    ):
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        
        if redis_client:
            self._redis = redis_client
        else:
            if redis is None:
                # mark unavailable
                self._redis = None  # type: ignore
            else:
                self._redis = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=False
                )

    def _make_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    def get(self, key: str) -> Any:
        if not self._redis:
            return None
        data = self._redis.get(self._make_key(key))
        if data is None:
            return None
        try:
            return pickle.loads(data)
        except pickle.UnpicklingError:
            return None

    def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> None:
        dumped = pickle.dumps(value)
        
        if ttl is None:
            ttl_seconds = self.default_ttl
        elif isinstance(ttl, timedelta):
            ttl_seconds = int(ttl.total_seconds())
        else:
            ttl_seconds = int(ttl)
            
        if not self._redis:
            return
        self._redis.setex(self._make_key(key), ttl_seconds, dumped)

    def delete(self, key: str) -> None:
        if not self._redis:
            return
        self._redis.delete(self._make_key(key))

    def exists(self, key: str) -> bool:
        if not self._redis:
            return False
        return bool(self._redis.exists(self._make_key(key)))

    def clear(self) -> None:
        if not self._redis:
            return
        cursor = '0'
        pattern = f"{self.key_prefix}*"
        while cursor != 0:
            cursor, keys = self._redis.scan(cursor=cursor, match=pattern, count=1000)
            if keys:
                self._redis.delete(*keys)

    def close(self) -> None:
        if self._redis:
            self._redis.close()

    def get_stats(self) -> Dict[str, Any]:
        if not self._redis:
            return {"type": "redis", "available": False}
        info = self._redis.info()
        return {
            "type": "redis",
            "available": True,
            "used_memory": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "db_keys": self._redis.dbsize()
        }
