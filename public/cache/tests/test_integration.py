import unittest
import time
import os
import sys
import redis

# Add public/cache to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cache.manager import MultiLevelCache
from cache.config import CacheConfig
from cache.l2_redis import RedisCache

class TestRealRedisIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Check if Redis is reachable
        try:
            r = redis.Redis(host='localhost', port=6379, password='secure_password', socket_connect_timeout=1)
            r.ping()
        except redis.ConnectionError:
            raise unittest.SkipTest("Redis not available at localhost:6379")

    def setUp(self):
        self.config = CacheConfig()
        self.config.L1_ENABLED = True
        self.config.L2_ENABLED = True
        self.config.REDIS_HOST = "localhost"
        self.config.REDIS_PORT = 6379
        self.config.REDIS_PASSWORD = "secure_password"
        self.config.CACHE_SYNC_ENABLED = True # Enable sync to test real pubsub
        self.config.AUTO_DETECT_REDIS = True
        
        self.cache = MultiLevelCache(self.config)

    def tearDown(self):
        self.cache.clear()
        self.cache.close()

    def test_real_redis_operations(self):
        # Set
        self.cache.set("real_key", "real_value")
        
        # Check L2 directly
        r = redis.Redis(host='localhost', port=6379, password='secure_password')
        # Key is prefixed
        self.assertTrue(r.exists("library:real_key"))
        
        # Get
        val = self.cache.get("real_key")
        self.assertEqual(val, "real_value")

    def test_degrade_without_redis(self):
        # Simulate environment without Redis by setting wrong host
        cfg = CacheConfig()
        cfg.L1_ENABLED = True
        cfg.L2_ENABLED = True
        cfg.REDIS_HOST = "127.0.0.2"  # unlikely local Redis
        cfg.CACHE_SYNC_ENABLED = False
        cfg.AUTO_DETECT_REDIS = True
        cfg.DEGRADE_ON_REDIS_UNAVAILABLE = True

        cache = MultiLevelCache(cfg)
        # Should degrade to L1 only
        self.assertIsNotNone(cache.l1)
        if cache.l2:
            # If l2 exists, it should fail ping, then be disabled; our manager removes l2 on ping failure.
            pass
        cache.set("dg", "v")
        self.assertEqual(cache.get("dg"), "v")
        cache.clear()
        self.assertIsNone(cache.get("dg"))
        cache.close()

    def test_sync_mechanism(self):
        # Create second instance
        cache2 = MultiLevelCache(self.config)
        
        # Set in cache1
        self.cache.set("sync_key", "val1")
        
        # Wait for sync (async thread)
        time.sleep(0.5)
        
        # cache2 should have it in L2, but L1 is empty initially.
        # If we access it, it populates L1.
        self.assertEqual(cache2.get("sync_key"), "val1")
        
        # Now update in cache1
        self.cache.set("sync_key", "val2")
        
        # Wait for invalidation message propagation
        time.sleep(0.5)
        
        # cache2 L1 should be invalidated. 
        # Getting it again should fetch new value from L2.
        self.assertEqual(cache2.get("sync_key"), "val2")
        
        cache2.close()

if __name__ == '__main__':
    unittest.main()
