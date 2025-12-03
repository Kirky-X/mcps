import unittest
import time
import json
import threading
from datetime import timedelta
from unittest.mock import MagicMock, patch
import sys
import os

# Add public/cache to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cache.base import BaseCache
from cache.l1_moka import MokaCache
from cache.l2_redis import RedisCache
from cache.manager import MultiLevelCache, create_cache_manager
from cache.config import CacheConfig

# Try to import fakeredis
try:
    import fakeredis
except ImportError:
    fakeredis = None

class TestMokaCache(unittest.TestCase):
    def test_basic_ops(self):
        cache = MokaCache(max_size=100, default_ttl=10)
        cache.set("foo", "bar")
        self.assertEqual(cache.get("foo"), "bar")
        self.assertTrue(cache.exists("foo"))
        
        cache.delete("foo")
        self.assertIsNone(cache.get("foo"))
        self.assertFalse(cache.exists("foo"))

    def test_ttl(self):
        # Note: This test relies on sleep and might be flaky if time is tight, 
        # but we use a short TTL.
        cache = MokaCache(default_ttl=1)
        cache.set("short", "value", ttl=1)
        self.assertEqual(cache.get("short"), "value")
        time.sleep(1.1)
        # Depending on backend (cacheout or moka), expiration might be lazy or eager.
        # Cacheout is lazy (checks on get).
        self.assertIsNone(cache.get("short"))

class TestRedisCache(unittest.TestCase):
    def setUp(self):
        if not fakeredis:
            self.skipTest("fakeredis not installed")
        self.redis_client = fakeredis.FakeRedis()
        self.cache = RedisCache(redis_client=self.redis_client)

    def test_basic_ops(self):
        self.cache.set("rkey", {"a": 1})
        val = self.cache.get("rkey")
        self.assertEqual(val, {"a": 1})
        
        self.cache.delete("rkey")
        self.assertIsNone(self.cache.get("rkey"))

    def test_ttl(self):
        self.cache.set("rttl", "val", ttl=60)
        self.assertTrue(self.cache.exists("rttl"))
        # FakeRedis respects TTL? Yes usually.
        # But we can't wait in unit tests easily.
        # We can inspect ttl
        ttl = self.redis_client.ttl("cache:rttl")
        # Redis returns -1 if no expiry, -2 if missing.
        # Should be > 0
        self.assertTrue(ttl > 0, f"TTL was {ttl}")

class TestMultiLevelCache(unittest.TestCase):
    def setUp(self):
        if not fakeredis:
            self.skipTest("fakeredis not installed")
        
        self.config = CacheConfig()
        self.config.L1_ENABLED = True
        self.config.L2_ENABLED = True
        self.config.CACHE_SYNC_ENABLED = False # Disable sync thread for simple tests
        self.config.AUTO_DETECT_REDIS = False
        
        # Mock Redis for L2
        self.fake_redis = fakeredis.FakeRedis()
        
        # Patch RedisCache to use our fake redis
        with patch('cache.manager.RedisCache'):
            # We need to manually construct the manager because the constructor creates RedisCache
            # But since we patched RedisCache class, self.l2 will be a mock unless we side_effect.
            # Simpler: Create manager, then replace l2.
            pass
            
        self.cache = MultiLevelCache(self.config)
        self.cache.l2 = RedisCache(redis_client=self.fake_redis)

    def tearDown(self):
        self.cache.close()

    def test_hierarchical_get(self):
        # Set in L2 only
        self.cache.l2.set("key1", "value1")
        
        # Get should find in L2 and populate L1
        val = self.cache.get("key1")
        self.assertEqual(val, "value1")
        self.assertEqual(self.cache.l1.get("key1"), "value1")

    def test_set_propagation(self):
        self.cache.set("key2", "value2")
        self.assertEqual(self.cache.l1.get("key2"), "value2")
        self.assertEqual(self.cache.l2.get("key2"), "value2")

    def test_delete_propagation(self):
        self.cache.set("key3", "value3")
        self.cache.delete("key3")
        self.assertIsNone(self.cache.l1.get("key3"))
        self.assertIsNone(self.cache.l2.get("key3"))

    def test_degrade_when_redis_unavailable(self):
        cfg = CacheConfig()
        cfg.L1_ENABLED = True
        cfg.L2_ENABLED = True
        cfg.CACHE_SYNC_ENABLED = False
        cfg.AUTO_DETECT_REDIS = True
        cfg.DEGRADE_ON_REDIS_UNAVAILABLE = True

        class BrokenRedis:
            def ping(self):
                raise RuntimeError("no redis")

        # Patch RedisCache to use BrokenRedis
        with patch('cache.l2_redis.redis.Redis', return_value=BrokenRedis()):
            cache = MultiLevelCache(cfg)
            # L2 should be None, L1 present
            self.assertIsNotNone(cache.l1)
            self.assertIsNone(cache.l2)
            # Operations should work on L1 only
            cache.set("k", "v")
            self.assertEqual(cache.get("k"), "v")
            self.assertTrue(cache.exists("k"))
            cache.delete("k")
            self.assertIsNone(cache.get("k"))
            cache.close()

    def test_factory(self):
        # Test compatibility with mcp-library settings
        class MockSettings:
            cache_ttl = 500
            cache_max_size = 200
            
        # We need to mock RedisCache again to avoid connection attempts in factory
        with patch('cache.manager.RedisCache'):
             # Also mock sync listener start to avoid thread
             with patch('cache.manager.MultiLevelCache._start_sync_listener'):
                cache = create_cache_manager(MockSettings())
                self.assertEqual(cache.config.L1_TTL, 500)
                self.assertEqual(cache.config.L1_MAX_SIZE, 200)
                cache.close()

class TestConcurrency(unittest.TestCase):
    def setUp(self):
        if not fakeredis:
            self.skipTest("fakeredis not installed")
        self.config = CacheConfig()
        self.config.CACHE_SYNC_ENABLED = False
        self.cache = MultiLevelCache(self.config)
        self.cache.l2 = RedisCache(redis_client=fakeredis.FakeRedis())

    def test_concurrent_writes(self):
        def writer(start, count):
            for i in range(start, start + count):
                self.cache.set(f"ckey:{i}", f"val:{i}")

        threads = []
        for i in range(5):
            t = threading.Thread(target=writer, args=(i * 100, 100))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
            
        # Verify
        # Verify keys count directly as get_stats relies on INFO which fakeredis might not fully support
        keys = self.cache.l2._redis.keys("cache:ckey:*")
        self.assertEqual(len(keys), 500)
        self.assertEqual(self.cache.get("ckey:0"), "val:0")
        self.assertEqual(self.cache.get("ckey:499"), "val:499")

class TestBoundary(unittest.TestCase):
    def setUp(self):
        if not fakeredis:
            self.skipTest("fakeredis not installed")
        self.config = CacheConfig()
        self.config.CACHE_SYNC_ENABLED = False
        self.cache = MultiLevelCache(self.config)
        self.cache.l2 = RedisCache(redis_client=fakeredis.FakeRedis())

    def test_large_value(self):
        # 1MB string
        large_val = "x" * 1024 * 1024
        self.cache.set("large", large_val)
        self.assertEqual(len(self.cache.get("large")), 1024 * 1024)

    def test_empty_key(self):
        # Technically Redis supports empty key, but it's weird.
        # Our wrapper prefixes it.
        self.cache.set("", "empty")
        self.assertEqual(self.cache.get(""), "empty")

    def test_none_handling(self):
        # set None might mean delete or just store None?
        # Pickle can store None.
        self.cache.set("none_val", None)
        # get returns None if missing.
        # So we can't distinguish missing vs stored None easily unless we use exists.
        self.assertTrue(self.cache.exists("none_val"))
        self.assertIsNone(self.cache.get("none_val"))

    def test_types(self):
        # Store dict, list, int
        data = {"a": [1, 2], "b": 3}
        self.cache.set("complex", data)
        self.assertEqual(self.cache.get("complex"), data)

class TestMokaPath(unittest.TestCase):
    def test_moka_usage(self):
        # Simulate Moka library installed
        with patch('cache.l1_moka.Moka') as MockMoka:
            mock_instance = MagicMock()
            MockMoka.return_value = mock_instance
            mock_instance.entry_count.return_value = 5
            
            with patch('cache.l1_moka.Moka', new=MockMoka):
                # Verify it picks up Moka
                cache = MokaCache()
                self.assertTrue(cache.use_moka)
                
                cache.set("k", "v")
                mock_instance.insert.assert_called()
                
                cache.get("k")
                mock_instance.get.assert_called()
                
                cache.delete("k")
                mock_instance.remove.assert_called()
                
                cache.exists("k")
                mock_instance.contains.assert_called()
                
                cache.clear()
                mock_instance.invalidate_all.assert_called()
                
                stats = cache.get_stats()
                self.assertEqual(stats['type'], 'moka')

class TestSyncLogic(unittest.TestCase):
    def test_handle_message(self):
        config = CacheConfig()
        config.CACHE_SYNC_ENABLED = True
        # Don't start listener
        with patch('cache.manager.MultiLevelCache._start_sync_listener'):
            cache = MultiLevelCache(config)
            cache.l1 = MagicMock()
            
            # Case 1: Message from self
            msg_self = {'data': json.dumps({'source_id': cache.instance_id}).encode()}
            cache._handle_sync_message(msg_self)
            cache.l1.delete.assert_not_called()
            
            # Case 2: Delete message from other
            msg_del = {'data': json.dumps({'source_id': 'other', 'action': 'delete', 'key': 'k'}).encode()}
            cache._handle_sync_message(msg_del)
            cache.l1.delete.assert_called_with('k')
            
            # Case 3: Clear message
            msg_clear = {'data': json.dumps({'source_id': 'other', 'action': 'clear'}).encode()}
            cache._handle_sync_message(msg_clear)
            cache.l1.clear.assert_called()

if __name__ == '__main__':
    unittest.main()
