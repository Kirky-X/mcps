"""缓存管理器"""

import time
from typing import Optional, Dict, Any
from threading import RLock
from ..exceptions import CacheError


class CacheEntry:
    """缓存条目"""
    
    def __init__(self, value: Any, expires_at: float, created_at: float):
        self.value = value
        self.expires_at = expires_at
        self.created_at = created_at
        self.last_accessed = created_at
        self.access_count = 0
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > self.expires_at


class CacheManager:
    """内存缓存管理器"""
    
    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.lock = RLock()
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self.lock:
            entry = self.cache.get(key)
            if entry and not entry.is_expired():
                entry.access_count += 1
                entry.last_accessed = time.time()
                self.hit_count += 1
                return entry.value
            elif entry:
                # 过期则删除
                del self.cache[key]
            self.miss_count += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        with self.lock:
            ttl = ttl or self.default_ttl
            
            # 检查缓存大小限制
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            self.cache[key] = CacheEntry(
                value=value,
                expires_at=time.time() + ttl,
                created_at=time.time()
            )
            
            # 清理过期缓存
            self._cleanup_expired()
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        """获取缓存大小"""
        with self.lock:
            return len(self.cache)
    
    def _cleanup_expired(self) -> None:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items() 
            if entry.expires_at < current_time
        ]
        for key in expired_keys:
            del self.cache[key]
    
    def _evict_lru(self) -> None:
        """LRU淘汰策略"""
        if not self.cache:
            return
        
        # 找到最少使用的条目
        lru_key = min(
            self.cache.keys(),
            key=lambda k: (self.cache[k].access_count, self.cache[k].last_accessed)
        )
        del self.cache[lru_key]
    
    def generate_key(self, language: str, library: str, 
                    operation: str, version: Optional[str] = None) -> str:
        """生成缓存键"""
        parts = [language, library, operation]
        if version:
            parts.append(version)
        return ":".join(parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_entries = len(self.cache)
            expired_count = sum(
                1 for entry in self.cache.values() 
                if entry.is_expired()
            )
            
            total_requests = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
            
            return {
                "total_entries": total_entries,
                "expired_entries": expired_count,
                "active_entries": total_entries - expired_count,
                "max_size": self.max_size,
                "default_ttl": self.default_ttl,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate": round(hit_rate, 2)
            }