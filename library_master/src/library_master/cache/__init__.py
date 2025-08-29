"""缓存模块

提供多种缓存实现：
- CacheManager: 基于内存的缓存管理器
- CacheOutManager: 基于 CacheOut 库的缓存管理器
"""

from .manager import CacheManager
from .cacheout_manager import CacheOutManager
from ..core.config import Settings


def create_cache_manager(settings: Settings = None):
    """创建缓存管理器工厂函数
    
    Args:
        settings: 配置对象
        
    Returns:
        缓存管理器实例
    """
    if settings is None:
        settings = Settings()
    
    cache_type = getattr(settings, 'cache_type', 'cacheout')
    default_ttl = getattr(settings, 'cache_default_ttl', settings.cache_ttl)
    max_size = getattr(settings, 'cache_max_entries', settings.cache_max_size)
    
    if cache_type.lower() == 'memory':
        return CacheManager(
            default_ttl=default_ttl,
            max_size=max_size
        )
    elif cache_type.lower() == 'cacheout':
        return CacheOutManager(
            default_ttl=default_ttl,
            max_size=max_size
        )
    else:
        # 默认使用 CacheOut
        return CacheOutManager(
            default_ttl=default_ttl,
            max_size=max_size
        )


__all__ = [
    'CacheManager',
    'CacheOutManager', 
    'create_cache_manager'
]