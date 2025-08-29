"""基于 CacheOut 的缓存管理器"""

import time
from typing import Optional, Dict, Any
from threading import RLock
from cacheout import Cache, LRUCache
from ..exceptions import CacheError


class CacheOutManager:
    """基于 CacheOut 的缓存管理器
    
    提供与原有 CacheManager 兼容的接口，但使用 CacheOut 库实现
    """
    
    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        """初始化缓存管理器
        
        Args:
            default_ttl: 默认TTL(秒)
            max_size: 最大缓存条目数
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.lock = RLock()
        
        # 使用 LRUCache 实现 LRU 淘汰策略
        self.cache = LRUCache(
            maxsize=max_size,
            ttl=default_ttl,
            timer=time.time
        )
        
        # 统计信息
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值或None
        """
        with self.lock:
            try:
                value = self.cache.get(key)
                if value is not None:
                    self.hit_count += 1
                    return value
                else:
                    self.miss_count += 1
                    return None
            except KeyError:
                self.miss_count += 1
                return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒)，None使用默认TTL
        """
        with self.lock:
            if ttl is None:
                # 使用默认TTL
                self.cache.set(key, value)
            else:
                # 使用指定TTL
                self.cache.set(key, value, ttl=ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self.lock:
            try:
                self.cache.delete(key)
                return True
            except KeyError:
                return False
    
    def clear(self) -> None:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            # 重置统计信息
            self.hit_count = 0
            self.miss_count = 0
    
    def size(self) -> int:
        """获取缓存大小
        
        Returns:
            当前缓存条目数
        """
        with self.lock:
            return len(self.cache)
    
    def generate_key(self, language: str, library: str, 
                    operation: str, version: Optional[str] = None) -> str:
        """生成缓存键
        
        Args:
            language: 编程语言
            library: 库名
            operation: 操作类型
            version: 版本号(可选)
            
        Returns:
            缓存键
        """
        parts = [language, library, operation]
        if version:
            parts.append(version)
        return ":".join(parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        with self.lock:
            total_entries = len(self.cache)
            total_requests = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
            
            # CacheOut 不直接提供过期条目统计，这里简化处理
            return {
                "total_entries": total_entries,
                "expired_entries": 0,  # CacheOut 自动清理过期条目
                "active_entries": total_entries,
                "max_size": self.max_size,
                "default_ttl": self.default_ttl,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate": round(hit_rate, 2),
                "cache_type": "cacheout"
            }
    
    def evict_expired(self) -> int:
        """手动清理过期条目
        
        Returns:
            清理的条目数
        """
        with self.lock:
            # CacheOut 自动处理过期条目，这里返回0
            return 0
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存详细信息
        
        Returns:
            缓存详细信息
        """
        with self.lock:
            return {
                "cache_type": "LRUCache",
                "maxsize": self.max_size,
                "ttl": self.default_ttl,
                "current_size": len(self.cache),
                "hit_count": self.hit_count,
                "miss_count": self.miss_count
            }