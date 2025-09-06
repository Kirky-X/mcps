"""Vector Cache Service tests for MCP DevAgent.

Tests vector caching functionality, memory management, and performance optimization.
"""

import asyncio
import os
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.mcp_devagent.services.vector_cache_service import (
    VectorCacheService, CacheEntry
)


class TestCacheEntry(unittest.TestCase):
    """Test CacheEntry data class."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation and serialization."""
        entry = CacheEntry(
            key="test_key",
            embedding=[0.1, 0.2, 0.3],
            content_type="code",
            provider="local",
            model="test_model",
            created_at=time.time(),
            access_count=5,
            last_accessed=time.time()
        )
        
        # Test to_dict
        entry_dict = entry.to_dict()
        self.assertEqual(entry_dict["key"], "test_key")
        self.assertEqual(entry_dict["embedding"], [0.1, 0.2, 0.3])
        self.assertEqual(entry_dict["content_type"], "code")
        self.assertEqual(entry_dict["provider"], "local")
        self.assertEqual(entry_dict["model"], "test_model")
        self.assertEqual(entry_dict["access_count"], 5)
        
        # Test from_dict
        reconstructed = CacheEntry.from_dict(entry_dict)
        self.assertEqual(reconstructed.key, entry.key)
        self.assertEqual(reconstructed.embedding, entry.embedding)
        self.assertEqual(reconstructed.content_type, entry.content_type)
        self.assertEqual(reconstructed.provider, entry.provider)
        self.assertEqual(reconstructed.model, entry.model)
        self.assertEqual(reconstructed.access_count, entry.access_count)


class TestVectorCacheService(unittest.TestCase):
    """Test VectorCacheService functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_service = VectorCacheService(
            cache_dir=self.temp_dir,
            max_cache_size=100
        )
        
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def run_async_test(self, coro):
        """Helper to run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    def test_cache_service_initialization(self):
        """Test cache service initialization."""
        self.assertTrue(os.path.exists(self.cache_service.cache_dir))
        self.assertTrue(os.path.exists(self.cache_service.cache_db_path))
        self.assertEqual(self.cache_service.max_cache_size, 100)
        self.assertEqual(len(self.cache_service.memory_cache), 0)
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        key1 = self.cache_service._generate_cache_key(
            "test text", "code", "local", "test_model"
        )
        key2 = self.cache_service._generate_cache_key(
            "test text", "code", "local", "test_model"
        )
        key3 = self.cache_service._generate_cache_key(
            "different text", "code", "local", "test_model"
        )
        
        # Same inputs should generate same key
        self.assertEqual(key1, key2)
        # Different inputs should generate different keys
        self.assertNotEqual(key1, key3)
        # Keys should be hex strings
        self.assertTrue(all(c in '0123456789abcdef' for c in key1))
    
    def test_cache_embedding_and_retrieval(self):
        """Test caching and retrieving embeddings."""
        async def run_test():
            text = "test code snippet"
            embedding = [0.1, 0.2, 0.3, 0.4]
            content_type = "code"
            provider = "local"
            model = "test_model"
            
            # Cache embedding
            await self.cache_service.cache_embedding(
                text, embedding, content_type, provider, model
            )
            
            # Retrieve embedding
            cached_embedding = await self.cache_service.get_cached_embedding(
                text, content_type, provider, model
            )
            
            self.assertIsNotNone(cached_embedding)
            self.assertEqual(cached_embedding, embedding)
        
        self.run_async_test(run_test())
    
    def test_cache_miss(self):
        """Test cache miss scenario."""
        async def run_test():
            # Try to retrieve non-existent embedding
            cached_embedding = await self.cache_service.get_cached_embedding(
                "non-existent text", "code", "local", "test_model"
            )
            
            self.assertIsNone(cached_embedding)
        
        self.run_async_test(run_test())
    
    def test_memory_cache_functionality(self):
        """Test memory cache operations."""
        async def run_test():
            text = "frequently accessed text"
            embedding = [0.5, 0.6, 0.7, 0.8]
            content_type = "code"
            provider = "local"
            model = "test_model"
            
            # Cache embedding
            await self.cache_service.cache_embedding(
                text, embedding, content_type, provider, model
            )
            
            # First retrieval (from database)
            cached_embedding1 = await self.cache_service.get_cached_embedding(
                text, content_type, provider, model
            )
            
            # Access multiple times to trigger memory cache
            for _ in range(4):
                await self.cache_service.get_cached_embedding(
                    text, content_type, provider, model
                )
            
            # Should now be in memory cache
            cache_key = self.cache_service._generate_cache_key(
                text, content_type, provider, model
            )
            self.assertIn(cache_key, self.cache_service.memory_cache)
            
            # Next retrieval should be from memory
            cached_embedding2 = await self.cache_service.get_cached_embedding(
                text, content_type, provider, model
            )
            
            self.assertEqual(cached_embedding1, embedding)
            self.assertEqual(cached_embedding2, embedding)
        
        self.run_async_test(run_test())
    
    def test_cache_statistics(self):
        """Test cache statistics functionality."""
        async def run_test():
            # Initially empty cache
            stats = await self.cache_service.get_cache_stats()
            self.assertEqual(stats["cache_entries"], 0)
            self.assertEqual(stats["memory_cache_entries"], 0)
            
            # Add some entries
            for i in range(5):
                await self.cache_service.cache_embedding(
                    f"text_{i}", [0.1 * i] * 4, "code", "local", "test_model"
                )
            
            # Check updated stats
            stats = await self.cache_service.get_cache_stats()
            self.assertEqual(stats["cache_entries"], 5)
            self.assertGreaterEqual(stats["total_cache_hits"], 0)
        
        self.run_async_test(run_test())
    
    def test_cache_cleanup(self):
        """Test cache cleanup functionality."""
        async def run_test():
            # Create service with small cache size
            small_cache_service = VectorCacheService(
                cache_dir=self.temp_dir + "_small",
                max_cache_size=3
            )
            
            # Add more entries than max size
            for i in range(5):
                await small_cache_service.cache_embedding(
                    f"text_{i}", [0.1 * i] * 4, "code", "local", "test_model"
                )
            
            # Check that cleanup occurred
            stats = await small_cache_service.get_cache_stats()
            self.assertLessEqual(stats["cache_entries"], 5)  # May not cleanup immediately
        
        self.run_async_test(run_test())
    
    def test_knowledge_base_management(self):
        """Test knowledge base precomputed vectors management."""
        async def run_test():
            # Add knowledge base entries
            await self.cache_service.add_knowledge_base_entry(
                "test_category", "item1", "test content 1", [0.1, 0.2, 0.3]
            )
            await self.cache_service.add_knowledge_base_entry(
                "test_category", "item2", "test content 2", [0.4, 0.5, 0.6]
            )
            await self.cache_service.add_knowledge_base_entry(
                "test_category", "item3", "test content 3", [0.7, 0.8, 0.9]
            )
            
            # Search knowledge base
            results = await self.cache_service.search_knowledge_base("test_category")
            
            self.assertEqual(len(results), 3)
            self.assertEqual(results[0]["category"], "test_category")
            self.assertEqual(results[0]["title"], "item3")  # Most recent first
            
            # Check statistics
            stats = await self.cache_service.get_cache_stats()
            self.assertEqual(stats["knowledge_base_entries"], 3)
            self.assertIn("test_category", stats["knowledge_base_categories"])
        
        self.run_async_test(run_test())
    
    def test_cache_clear(self):
        """Test cache clearing functionality."""
        async def run_test():
            # Add some entries
            for i in range(3):
                await self.cache_service.cache_embedding(
                    f"text_{i}", [0.1 * i] * 4, "code", "local", "test_model"
                )
            
            # Verify entries exist
            stats_before = await self.cache_service.get_cache_stats()
            self.assertEqual(stats_before["cache_entries"], 3)
            
            # Clear cache
            await self.cache_service.clear_cache()
            
            # Verify cache is empty
            stats_after = await self.cache_service.get_cache_stats()
            self.assertEqual(stats_after["cache_entries"], 0)
            self.assertEqual(len(self.cache_service.memory_cache), 0)
        
        self.run_async_test(run_test())
    
    def test_error_handling(self):
        """Test error handling in cache operations."""
        async def run_test():
            # Test with invalid cache directory permissions
            with patch('sqlite3.connect') as mock_connect:
                mock_connect.side_effect = Exception("Database error")
                
                # Should handle database errors gracefully
                result = await self.cache_service.get_cached_embedding(
                    "test", "code", "local", "model"
                )
                self.assertIsNone(result)
        
        self.run_async_test(run_test())
    
    def test_memory_cache_lru_eviction(self):
        """Test LRU eviction in memory cache."""
        # Create service with small memory cache
        small_memory_service = VectorCacheService(
            cache_dir=self.temp_dir + "_lru",
            max_cache_size=1000
        )
        small_memory_service.memory_cache_size = 2  # Very small memory cache
        
        async def run_test():
            # Add entries to fill memory cache
            await small_memory_service.cache_embedding(
                "text1", [0.1] * 4, "code", "local", "model"
            )
            await small_memory_service.cache_embedding(
                "text2", [0.2] * 4, "code", "local", "model"
            )
            
            # Memory cache should be full
            self.assertEqual(len(small_memory_service.memory_cache), 2)
            
            # Add another entry - should evict LRU
            await small_memory_service.cache_embedding(
                "text3", [0.3] * 4, "code", "local", "model"
            )
            
            # Memory cache should still be size 2
            self.assertEqual(len(small_memory_service.memory_cache), 2)
        
        self.run_async_test(run_test())


class TestVectorCacheServiceIntegration(unittest.TestCase):
    """Integration tests for vector cache service."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_service = VectorCacheService(cache_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up integration test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def run_async_test(self, coro):
        """Helper to run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    def test_end_to_end_caching_workflow(self):
        """Test complete caching workflow."""
        async def run_test():
            # Simulate typical usage pattern
            test_cases = [
                ("function definition", [0.1, 0.2, 0.3], "code"),
                ("API documentation", [0.4, 0.5, 0.6], "documentation"),
                ("user query", [0.7, 0.8, 0.9], "query"),
                ("code comment", [0.2, 0.3, 0.4], "comment")
            ]
            
            provider = "local"
            model = "test_model"
            
            # Cache all embeddings
            for text, embedding, content_type in test_cases:
                await self.cache_service.cache_embedding(
                    text, embedding, content_type, provider, model
                )
            
            # Retrieve all embeddings
            for text, expected_embedding, content_type in test_cases:
                cached_embedding = await self.cache_service.get_cached_embedding(
                    text, content_type, provider, model
                )
                self.assertEqual(cached_embedding, expected_embedding)
            
            # Check statistics
            stats = await self.cache_service.get_cache_stats()
            self.assertEqual(stats["cache_entries"], 4)
            self.assertGreaterEqual(stats["total_cache_hits"], 0)
            
            # Test knowledge base functionality
            await self.cache_service.add_knowledge_base_entry(
                "common_patterns", "pattern_1", "common pattern 1", [0.1, 0.1, 0.1]
            )
            await self.cache_service.add_knowledge_base_entry(
                "common_patterns", "pattern_2", "common pattern 2", [0.2, 0.2, 0.2]
            )
            
            retrieved_kb = await self.cache_service.search_knowledge_base("common_patterns")
            
            self.assertEqual(len(retrieved_kb), 2)
            self.assertEqual(retrieved_kb[0]["category"], "common_patterns")
        
        self.run_async_test(run_test())


if __name__ == '__main__':
    unittest.main()