import pytest
import time
from unittest.mock import Mock, patch
from library.cache.manager import MultiLevelCache, create_cache_manager
from library.cache.config import CacheConfig

class TestCacheManager:
    def test_l1_only(self):
        config = CacheConfig()
        config.L2_ENABLED = False
        manager = MultiLevelCache(config)
        
        manager.set("test:key", "value")
        assert manager.get("test:key") == "value"
        assert manager.l2 is None
        
        manager.delete("test:key")
        assert manager.get("test:key") is None
        
    def test_l1_l2_fallback(self):
        config = CacheConfig()
        config.L2_ENABLED = True
        # Mock Redis to simulate failure
        with patch('library.cache.l2_redis.RedisCache') as mock_redis:
            mock_redis.side_effect = ImportError("Redis not installed")
            manager = MultiLevelCache(config)
            
            # Should degrade to L1
            assert manager.l1 is not None
            assert manager.l2 is None
            
            manager.set("test:key", "value")
            assert manager.get("test:key") == "value"

    def test_key_generation(self):
        manager = create_cache_manager()
        key = manager.generate_key("python", "requests", "latest", "1.0", 2)
        assert key == "python:requests:latest:1.0:2"
        
        key_none = manager.generate_key("python", "requests", "latest", None, None)
        assert key_none == "python:requests:latest::1"

    def test_cache_expiration(self):
        config = CacheConfig()
        config.L1_TTL = 0.1
        manager = MultiLevelCache(config)
        
        manager.set("expire:key", "value")
        assert manager.get("expire:key") == "value"
        
        time.sleep(0.2)
        assert manager.get("expire:key") is None
