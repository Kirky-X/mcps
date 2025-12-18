# Copyright (c) Kirky.X. 2025. All rights reserved.
from datetime import timedelta
from typing import Any, Optional

from .local_cache import Cache
import os
from pathlib import Path

from ..utils.config import Config


class CacheManager:
    def __init__(self, config: Config):
        """初始化内存缓存管理器

        基于 `moka` 构建可选启用的 LRU/TTL 缓存，支持最大容量、存活时间与空闲过期配置。

        Args:
            config (Config): 全局配置对象，读取 `cache` 段落进行初始化。

        Returns:
            None

        Raises:
            Exception: 当缓存构建失败时可能抛出异常。
        """
        self.enabled = config.cache.get("enabled", False)
        if self.enabled:
            cache_type = config.cache.get("type", "moka")
            if cache_type == "filesystem":
                dir_env = os.getenv("PROMPT_MANAGER_CACHE_DIR")
                cache_dir = dir_env or config.cache.get("dir") or \
                    str(Path("/home/dev/mcps/public/cache").resolve())
                p = Path(cache_dir)
                p.mkdir(parents=True, exist_ok=True)
                # simple file-backed wrapper using local cache for index + files under p
                self.cache = Cache.builder() \
                    .max_capacity(config.cache.get("max_capacity", 1000)) \
                    .time_to_live(timedelta(seconds=config.cache.get("ttl_seconds", 3600))) \
                    .time_to_idle(timedelta(seconds=config.cache.get("idle_timeout_seconds", 1800))) \
                    .build()
                setattr(self, "_cache_dir", p)
            else:
                self.cache = Cache.builder() \
                    .max_capacity(config.cache.get("max_capacity", 1000)) \
                    .time_to_live(timedelta(seconds=config.cache.get("ttl_seconds", 3600))) \
                    .time_to_idle(timedelta(seconds=config.cache.get("idle_timeout_seconds", 1800))) \
                    .build()
        else:
            self.cache = None

    def get(self, key: str) -> Optional[Any]:
        """从缓存获取值

        Args:
            key (str): 键名。

        Returns:
            Optional[Any]: 命中返回值，未启用或未命中返回 `None`。
        """
        if not self.enabled:
            return None
        val = self.cache.get(key)
        if val is not None:
            return val
        # fallback: filesystem cache
        if getattr(self, "_cache_dir", None):
            fp = Path(self._cache_dir) / f"{key}.json"
            try:
                if fp.exists():
                    import json
                    val = json.loads(fp.read_text(encoding="utf-8"))
                    # warm memory cache
                    self.cache.insert(key, val)
                    return val
            except Exception:
                return None
        return None

    def insert(self, key: str, value: Any):
        """写入缓存键值对

        Args:
            key (str): 键名。
            value (Any): 值对象。

        Returns:
            None
        """
        if self.enabled:
            self.cache.insert(key, value)
            cache_dir = getattr(self, "_cache_dir", None)
            if cache_dir:
                fp = Path(self._cache_dir) / f"{key}.json"
                try:
                    import json
                    # Only serialize if the value is JSON-serializable
                    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
                        fp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                    else:
                        # For complex objects, don't create a cache file
                        pass
                except Exception:
                    # If serialization fails, don't create a cache file
                    pass
        else:
            pass

    def invalidate(self, key: str):
        """使某个键失效

        Args:
            key (str): 键名。

        Returns:
            None
        """
        if self.enabled:
            self.cache.invalidate(key)
            if getattr(self, "_cache_dir", None):
                fp = Path(self._cache_dir) / f"{key}.json"
                try:
                    if fp.exists():
                        fp.unlink()
                except Exception:
                    pass

    def invalidate_pattern(self, name: str):
        if not self.enabled:
            return
        prefix = f"prompt:{name}:"
        impl = getattr(self.cache, "_impl", None)
        if not impl:
            return
        keys = list(impl.store.keys())
        for k in keys:
            if k.startswith(prefix):
                impl.invalidate(k)

    def generate_key(self, name: str, version: str) -> str:
        """生成缓存键

        以统一格式 `prompt:{name}:v{version}` 生成提示缓存键。

        Args:
            name (str): 提示名称。
            version (str): 版本字符串或标识。

        Returns:
            str: 规范化的缓存键。
        """
        return f"prompt:{name}:v{version}"
