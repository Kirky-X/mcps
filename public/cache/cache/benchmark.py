import time
import sys
import os

# Add public/cache directory to path (so 'import cache' works)
# We are in public/cache/cache/benchmark.py
# We want to add public/cache to path.
# public/cache/cache -> .. -> public/cache.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import fakeredis
except ImportError:
    print("fakeredis not installed, skipping Redis benchmark")
    fakeredis = None

from cache.manager import MultiLevelCache
from cache.config import CacheConfig
from cache.l2_redis import RedisCache

def run_benchmark(name: str, cache, operations: int = 10000):
    print(f"\n--- Benchmarking {name} ---")
    
    # SET Benchmark
    start = time.time()
    for i in range(operations):
        cache.set(f"key:{i}", f"value:{i}")
    duration = time.time() - start
    print(f"SET: {operations} ops in {duration:.4f}s ({operations/duration:.2f} ops/s)")
    
    # GET Hit Benchmark
    start = time.time()
    hits = 0
    for i in range(operations):
        val = cache.get(f"key:{i}")
        if val:
            hits += 1
    duration = time.time() - start
    print(f"GET (Hit): {operations} ops in {duration:.4f}s ({operations/duration:.2f} ops/s)")
    
    # GET Miss Benchmark
    start = time.time()
    for i in range(operations):
        cache.get(f"key:miss:{i}")
    duration = time.time() - start
    print(f"GET (Miss): {operations} ops in {duration:.4f}s ({operations/duration:.2f} ops/s)")

def main():
    ops = 5000
    
    # 1. L1 Only (Moka/Cacheout)
    config_l1 = CacheConfig()
    config_l1.L1_ENABLED = True
    config_l1.L2_ENABLED = False
    config_l1.CACHE_SYNC_ENABLED = False
    cache_l1 = MultiLevelCache(config_l1)
    run_benchmark("L1 Cache (Local)", cache_l1, ops)
    
    # 2. L2 Only (Redis - Fake)
    if fakeredis:
        config_l2 = CacheConfig()
        config_l2.L1_ENABLED = False
        config_l2.L2_ENABLED = True
        config_l2.CACHE_SYNC_ENABLED = False
        
        # Patch RedisCache to use fakeredis
        # We need to manually inject it because MultiLevelCache creates it
        cache_l2 = MultiLevelCache(config_l2)
        # Replace l2 with fake redis
        cache_l2.l2 = RedisCache(redis_client=fakeredis.FakeRedis())
        
        run_benchmark("L2 Cache (FakeRedis)", cache_l2, ops)
        
        # 3. Multi-Level
        config_multi = CacheConfig()
        config_multi.L1_ENABLED = True
        config_multi.L2_ENABLED = True
        config_multi.CACHE_SYNC_ENABLED = False
        
        cache_multi = MultiLevelCache(config_multi)
        cache_multi.l2 = RedisCache(redis_client=fakeredis.FakeRedis())
        
        run_benchmark("Multi-Level Cache (L1 + FakeRedis)", cache_multi, ops)
        
        # Verify L1 population
        print("\nVerifying L1 population from L2...")
        cache_multi.l1.clear()
        cache_multi.l2.set("pop_test", "success")
        val = cache_multi.get("pop_test") # Should pull from L2 and set L1
        print(f"Value: {val}")
        print(f"L1 exists: {cache_multi.l1.exists('pop_test')}")

if __name__ == "__main__":
    main()
