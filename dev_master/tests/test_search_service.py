"""Search Service tests for MCP DevAgent.

Tests hybrid search engine, FTS5 full-text search, and VSS vector search.
"""

import asyncio
import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from src.mcp_devagent.services.search_service import (
    SearchService, SearchResult, FTSSearchEngine, VSSSearchEngine, HybridSearchEngine
)


class TestSearchResult(unittest.TestCase):
    """Test SearchResult data class."""
    
    def test_search_result_creation(self):
        """Test SearchResult creation and properties."""
        result = SearchResult(
            content="Test content",
            file_path="/test/file.py",
            content_type="code",
            score=0.85,
            search_type="fts",
            metadata={"type": "code", "language": "python"}
        )
        
        self.assertEqual(result.content, "Test content")
        self.assertEqual(result.file_path, "/test/file.py")
        self.assertEqual(result.content_type, "code")
        self.assertEqual(result.score, 0.85)
        self.assertEqual(result.search_type, "fts")
        self.assertEqual(result.metadata["type"], "code")
    
    def test_search_result_to_dict(self):
        """Test SearchResult to_dict method."""
        result = SearchResult(
            content="Test content",
            file_path="/test/file.py",
            content_type="code",
            score=0.85,
            search_type="vss",
            metadata={"type": "code"}
        )
        
        result_dict = result.to_dict()
        
        expected_dict = {
            "content": "Test content",
            "file_path": "/test/file.py",
            "content_type": "code",
            "score": 0.85,
            "search_type": "vss",
            "rank": 0,
            "metadata": {"type": "code"}
        }
        
        self.assertEqual(result_dict, expected_dict)
    
    def test_search_result_comparison(self):
        """Test SearchResult comparison by score."""
        result1 = SearchResult(
            content="content1",
            file_path="test1.py",
            content_type="code",
            score=0.9,
            search_type="fts",
            metadata={}
        )
        result2 = SearchResult(
            content="content2",
            file_path="test2.py",
            content_type="code",
            score=0.8,
            search_type="vss",
            metadata={}
        )
        result3 = SearchResult(
            content="content3",
            file_path="test3.py",
            content_type="code",
            score=0.9,
            search_type="hybrid",
            metadata={}
        )
        
        # Test sorting (higher scores first)
        results = [result2, result1, result3]
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)
        
        self.assertEqual(sorted_results[0].score, 0.9)
        self.assertEqual(sorted_results[2].score, 0.8)


class TestFTSSearchEngine(unittest.TestCase):
    """Test FTS5 full-text search engine."""
    
    def setUp(self):
        """Set up FTS search engine for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_fts.db")
        
        # Create test database with FTS5 table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create code_embeddings table first
        cursor.execute("""
            CREATE TABLE code_embeddings (
                id INTEGER PRIMARY KEY,
                content TEXT,
                file_path TEXT,
                language TEXT
            )
        """)
        
        # Create FTS5 table
        cursor.execute("""
            CREATE VIRTUAL TABLE code_search_fts USING fts5(
                content,
                file_path,
                language,
                content='code_embeddings',
                content_rowid='id'
            )
        """)
        

        
        # Insert test data
        test_data = [
            (1, "def calculate_sum(a, b): return a + b", "math_utils.py", "python"),
            (2, "function multiply(x, y) { return x * y; }", "math.js", "javascript"),
            (3, "class Calculator { add(a, b) { return a + b; } }", "calculator.js", "javascript"),
            (4, "import numpy as np\ndef matrix_multiply(a, b): return np.dot(a, b)", "matrix.py", "python")
        ]
        
        cursor.executemany(
            "INSERT INTO code_embeddings (id, content, file_path, language) VALUES (?, ?, ?, ?)",
            test_data
        )
        
        # Populate FTS5 table
        cursor.executemany(
            "INSERT INTO code_search_fts (rowid, content, file_path, language) VALUES (?, ?, ?, ?)",
            test_data
        )
        
        conn.commit()
        conn.close()
        
        self.engine = FTSSearchEngine(self.db_path)
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    async def test_fts_initialization_and_simple_search(self):
        """Test FTS engine initialization and simple search functionality."""
        await self.engine.initialize()
        self.assertTrue(self.engine.is_initialized)
        
        # Test simple search functionality
        results = await self.engine.search("calculate", limit=10)
        
        self.assertEqual(len(results), 1)
        self.assertIn("calculate_sum", results[0].content)
        self.assertEqual(results[0].search_type, "fts")
        self.assertGreater(results[0].score, 0)
    

    
    async def test_fts_multiple_results(self):
        """Test FTS search with multiple results."""
        await self.engine.initialize()
        
        results = await self.engine.search("multiply", limit=10)
        
        self.assertGreaterEqual(len(results), 1)
        # Should find both multiply function and matrix_multiply
        content_texts = [r.content for r in results]
        self.assertTrue(any("multiply" in text for text in content_texts))
    
    async def test_fts_language_filter(self):
        """Test FTS search with language filter."""
        await self.engine.initialize()
        
        # Search for functions in Python only
        results = await self.engine.search("def", filters={"language": "python"}, limit=10)
        
        self.assertGreater(len(results), 0)
        for result in results:
            self.assertEqual(result.metadata.get("language"), "python")
    
    async def test_fts_file_path_filter(self):
        """Test FTS search with file path filter."""
        await self.engine.initialize()
        
        # Search in JavaScript files only
        results = await self.engine.search("function", filters={"file_path": "*.js"}, limit=10)
        
        self.assertGreater(len(results), 0)
        for result in results:
            self.assertTrue(result.metadata.get("file_path", "").endswith(".js"))
    
    async def test_fts_no_results(self):
        """Test FTS search with no results."""
        await self.engine.initialize()
        
        results = await self.engine.search("nonexistent_function", limit=10)
        
        self.assertEqual(len(results), 0)
    
    async def test_fts_limit_results(self):
        """Test FTS search result limiting."""
        await self.engine.initialize()
        
        # Search for common term that should return multiple results
        results = await self.engine.search("return", limit=2)
        
        self.assertLessEqual(len(results), 2)
    
    async def test_fts_score_normalization(self):
        """Test FTS score normalization."""
        await self.engine.initialize()
        
        results = await self.engine.search("calculate", limit=10)
        
        for result in results:
            self.assertGreaterEqual(result.score, 0.0)
            self.assertLessEqual(result.score, 1.0)
    
    def run_async_test(self, coro):
        """Helper to run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class TestVSSSearchEngine(unittest.TestCase):
    """Test VSS vector search engine."""
    
    def setUp(self):
        """Set up VSS search engine for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_vss.db")
        
        # Create test database with VSS table
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # First create content table
        cursor.execute("""
            CREATE TABLE code_embeddings (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                file_path TEXT NOT NULL,
                content_type TEXT,
                line_start INTEGER,
                line_end INTEGER,
                function_name TEXT,
                class_name TEXT,
                language TEXT,
                embedding_vector BLOB
            )
        """)
        
        # Enable VSS extension
        try:
            conn.enable_load_extension(True)
            import sqlite_vss
            sqlite_vss.load(conn)
            cursor.execute("SELECT vss_version()")
        except (sqlite3.OperationalError, ImportError) as e:
            # VSS not available, skip VSS-specific tests
            conn.close()
            self.skipTest(f"VSS extension not available: {e}")
        
        # Create VSS table
        cursor.execute("""
            CREATE VIRTUAL TABLE code_embeddings_vss USING vss0(
                embedding(384)
            )
        """)
        

        
        # Insert test data with mock embeddings
        import struct
        test_data = [
            (1, "def calculate_sum(a, b): return a + b", "math_utils.py", "python", 1, 1, "calculate_sum", None, "python", 
             struct.pack('f' * 384, *([0.1] * 384))),
            (2, "function multiply(x, y) { return x * y; }", "math.js", "javascript", 1, 1, "multiply", None, "javascript",
             struct.pack('f' * 384, *([0.2] * 384))),
            (3, "class Calculator { add(a, b) { return a + b; } }", "calculator.js", "javascript", 1, 1, "add", "Calculator", "javascript",
             struct.pack('f' * 384, *([0.3] * 384))),
            (4, "import numpy as np\ndef matrix_multiply(a, b): return np.dot(a, b)", "matrix.py", "python", 1, 2, "matrix_multiply", None, "python",
             struct.pack('f' * 384, *([0.4] * 384)))
        ]
        
        cursor.executemany(
            "INSERT INTO code_embeddings (id, content, file_path, content_type, line_start, line_end, function_name, class_name, language, embedding_vector) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            test_data
        )
        
        # Insert into VSS table
        for id_, content, file_path, content_type, line_start, line_end, function_name, class_name, language, embedding in test_data:
            cursor.execute(
                "INSERT INTO code_embeddings_vss (rowid, embedding) VALUES (?, ?)",
                (id_, embedding)
            )
        
        conn.commit()
        conn.close()
        
        self.engine = VSSSearchEngine(self.db_path)
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_vss_initialization(self):
        """Test VSS engine initialization."""
        # VSS engine doesn't have initialize method, just check if it's available
        self.assertIsNotNone(self.engine)
        # Check if VSS is available (this was already checked in setUp)
    
    def test_vss_vector_search(self):
        """Test VSS vector search."""
        async def run_test():
            # Create query vector similar to first embedding
            query_vector = [0.1] * 384
            
            results = await self.engine.search(query_vector, limit=10)
            
            self.assertGreater(len(results), 0)
            self.assertEqual(results[0].search_type, "vss")
            self.assertGreater(results[0].score, 0)
        
        self.run_async_test(run_test())
    
    def test_vss_similarity_ranking(self):
        """Test VSS similarity ranking."""
        async def run_test():
            # Query vector most similar to first embedding
            query_vector = [0.1] * 384
            
            results = await self.engine.search(query_vector, limit=10)
            
            # Results should be ranked by similarity (highest first)
            if len(results) > 1:
                for i in range(len(results) - 1):
                    self.assertGreaterEqual(results[i].score, results[i + 1].score)
        
        self.run_async_test(run_test())
    
    def test_vss_language_filter(self):
        """Test VSS search with language filter."""
        async def run_test():
            query_vector = [0.2] * 384
            
            results = await self.engine.search(
                query_vector, 
                content_types=["python"], 
                limit=10
            )
            
            print(f"Found {len(results)} results")
            for i, result in enumerate(results):
                print(f"Result {i}: content_type={result.content_type}, language={result.metadata.get('language')}")
                self.assertEqual(result.metadata.get("language"), "python")
        
        self.run_async_test(run_test())
    
    def test_vss_limit_results(self):
        """Test VSS search result limiting."""
        async def run_test():
            query_vector = [0.3] * 384
            
            results = await self.engine.search(query_vector, limit=2)
            
            self.assertLessEqual(len(results), 2)
        
        self.run_async_test(run_test())
    
    def run_async_test(self, coro):
        """Helper to run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class TestHybridSearchEngine(unittest.TestCase):
    """Test hybrid search engine combining FTS and VSS."""
    
    def setUp(self):
        """Set up hybrid search engine for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_hybrid.db")
        
        # Create mock FTS and VSS engines
        self.mock_fts_engine = MagicMock()
        self.mock_vss_engine = MagicMock()
        
        # Mock embedding service
        self.mock_embedding_service = AsyncMock()
        
        self.engine = HybridSearchEngine(self.db_path, self.mock_embedding_service)
        self.engine.fts_engine = self.mock_fts_engine
        self.engine.vss_engine = self.mock_vss_engine
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_hybrid_initialization(self):
        """Test hybrid engine initialization."""
        async def run_test():
            self.mock_fts_engine.initialize = AsyncMock()
            self.mock_vss_engine.initialize = AsyncMock()
            
            await self.engine.initialize()
            
            self.mock_fts_engine.initialize.assert_called_once()
            self.mock_vss_engine.initialize.assert_called_once()
            self.assertTrue(self.engine.is_initialized)
        
        self.run_async_test(run_test())
    
    def test_hybrid_search_combination(self):
        """Test hybrid search combining FTS and VSS results."""
        async def run_test():
            # Mock FTS results
            fts_results = [
                SearchResult(
                    content="def calculate_sum(a, b)",
                    file_path="math_utils.py",
                    content_type="code",
                    score=0.9,
                    search_type="fts",
                    metadata={"language": "python"}
                ),
                SearchResult(
                    content="function multiply(x, y)",
                    file_path="math.js",
                    content_type="code",
                    score=0.7,
                    search_type="fts",
                    metadata={"language": "javascript"}
                )
            ]
            
            # Mock VSS results
            vss_results = [
                SearchResult(
                    content="class Calculator",
                    file_path="calculator.js",
                    content_type="code",
                    score=0.8,
                    search_type="vss",
                    metadata={"language": "javascript"}
                ),
                SearchResult(
                    content="def calculate_sum(a, b)",
                    file_path="math_utils.py",
                    content_type="code",
                    score=0.6,
                    search_type="vss",
                    metadata={"language": "python"}
                )  # Duplicate
            ]
            
            self.mock_fts_engine.search = AsyncMock(return_value=fts_results)
            self.mock_vss_engine.search = AsyncMock(return_value=vss_results)
            
            # Mock embedding generation
            self.mock_embedding_service.generate_embedding = AsyncMock(return_value={
                "embedding": [0.1] * 384
            })
            
            result = await self.engine.search(
                "calculate sum", 
                limit=10
            )
            
            # Should combine and deduplicate results
            results = result["results"]
            self.assertGreater(len(results), 0)
            self.assertLessEqual(len(results), 3)  # Max 3 unique results
            
            # Check that results are properly merged
            result_files = [r["file_path"] for r in results]
            self.assertIn("math_utils.py", result_files)  # Should appear once despite being in both
            self.assertIn("math.js", result_files)
            self.assertIn("calculator.js", result_files)
        
        self.run_async_test(run_test())
    
    def test_hybrid_search_text_only(self):
        """Test hybrid search with text query only."""
        async def run_test():
            fts_results = [
                SearchResult(
                    content="def calculate_sum(a, b)",
                    file_path="math_utils.py",
                    content_type="code",
                    score=0.9,
                    search_type="fts",
                    metadata={}
                )
            ]
            
            self.mock_fts_engine.search = AsyncMock(return_value=fts_results)
            self.mock_vss_engine.search = AsyncMock(return_value=[])
            
            result = await self.engine.search(
                "calculate", 
                search_type="fulltext",
                limit=10
            )
            
            results = result["results"]
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["search_type"], "fts")
            
            # Should only call FTS search
            self.mock_fts_engine.search.assert_called_once()
            self.mock_vss_engine.search.assert_not_called()
        
        self.run_async_test(run_test())
    
    def test_hybrid_search_embedding_only(self):
        """Test hybrid search with embedding query only."""
        async def run_test():
            vss_results = [
                SearchResult(
                    content="def calculate_sum(a, b)",
                    file_path="math_utils.py",
                    content_type="code",
                    score=0.8,
                    search_type="vss",
                    metadata={}
                )
            ]
            
            self.mock_fts_engine.search = AsyncMock(return_value=[])
            self.mock_vss_engine.search = AsyncMock(return_value=vss_results)
            
            # Mock embedding generation
            self.mock_embedding_service.generate_embedding = AsyncMock(return_value={
                "embedding": [0.1] * 384
            })
            
            query_embedding = [0.1] * 384
            # For embedding-only search, we need to use semantic search type
            result = await self.engine.search(
                "calculate",  # Still need a query string
                search_type="semantic",
                limit=10
            )
            
            results = result["results"]
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["search_type"], "vss")
            
            # Should only call VSS search
            self.mock_vss_engine.search.assert_called_once_with(
                [0.1] * 384, None, 10, 0.7
            )
            self.mock_fts_engine.search.assert_not_called()
        
        self.run_async_test(run_test())
    
    def test_score_normalization(self):
        """Test score normalization for result merging."""
        # Create test results with different scores
        fts_results = [
            SearchResult(
                content="content1",
                file_path="file1.py",
                content_type="code",
                score=10.5,
                search_type="fts",
                metadata={}
            ),
            SearchResult(
                content="content2",
                file_path="file2.py",
                content_type="code",
                score=2.3,
                search_type="fts",
                metadata={}
            )
        ]
        
        # Test score normalization
        normalized = self.engine._normalize_scores(fts_results, "fulltext")
        
        # Check that scores are normalized between 0 and 1
        for result in normalized:
            self.assertGreaterEqual(result.score, 0.0)
            self.assertLessEqual(result.score, 1.0)
        
        # Check that results are sorted by score
        self.assertGreaterEqual(normalized[0].score, normalized[1].score)
    
    def test_result_merging(self):
        """Test merging and deduplication of search results."""
        fts_results = [
            SearchResult(
                content="content1",
                file_path="file1.py",
                content_type="code",
                score=0.9,
                search_type="fts",
                metadata={}
            ),
            SearchResult(
                content="content2",
                file_path="file2.py",
                content_type="code",
                score=0.7,
                search_type="fts",
                metadata={}
            )
        ]
        
        vss_results = [
            SearchResult(
                content="content1",
                file_path="file1.py",
                content_type="code",
                score=0.8,
                search_type="vss",
                metadata={}
            ),  # Duplicate
            SearchResult(
                content="content3",
                file_path="file3.py",
                content_type="code",
                score=0.6,
                search_type="vss",
                metadata={}
            )
        ]
        
        merged = self.engine._merge_results(fts_results, vss_results, 0.6, 0.4)
        
        # Should have 3 unique results
        self.assertEqual(len(merged), 3)
        
        # Check deduplication (file1.py should appear once with higher score)
        result_files = [r.file_path for r in merged]
        self.assertEqual(result_files.count("file1.py"), 1)
        
        # Find the merged result for file1.py
        merged_result = next(r for r in merged if r.file_path == "file1.py")
        self.assertGreater(merged_result.score, 0.0)  # Should be boosted
        self.assertLessEqual(merged_result.score, 1.0)
        self.assertEqual(merged_result.search_type, "hybrid")
    
    def run_async_test(self, coro):
        """Helper to run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class TestSearchService(unittest.TestCase):
    """Test SearchService main interface."""
    
    def setUp(self):
        """Set up search service for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_search_service.db")
        
        # Mock embedding service
        self.mock_embedding_service = MagicMock()
        
        database_url = f"sqlite+aiosqlite:///{self.db_path}"
        self.service = SearchService(database_url, self.mock_embedding_service)
    
    def tearDown(self):
        """Clean up test environment."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_service_initialization(self):
        """Test search service initialization."""
        # SearchService doesn't have initialize method, test basic setup
        self.assertIsNotNone(self.service.hybrid_engine)
        self.assertIsNotNone(self.service.logger)
    
    def test_hybrid_search(self):
        """Test hybrid search through service interface."""
        # Mock hybrid engine search
        expected_result = {
            "results": [{
                "content": "test content",
                "file_path": "test_file.py",
                "content_type": "code",
                "score": 0.9,
                "search_type": "hybrid",
                "metadata": {}
            }],
            "total_results": 1,
            "search_type": "hybrid",
            "query": "test query",
            "execution_time": 0.1
        }
        
        async def run_test():
            with patch.object(self.service.hybrid_engine, 'search') as mock_search:
                mock_search.return_value = expected_result
                
                result = await self.service.search(
                    "test query",
                    search_type="hybrid",
                    limit=10
                )
            
            self.assertEqual(result["total_results"], 1)
            self.assertEqual(result["results"][0]["content"], "test content")
            
            mock_search.assert_called_once_with(
                "test query",
                search_type="hybrid",
                limit=10
            )
        
        self.run_async_test(run_test())
    
    def test_fulltext_search(self):
        """Test full-text search through service interface."""
        expected_result = {
            "results": [{
                "content": "test content",
                "file_path": "test_file.py",
                "content_type": "code",
                "score": 0.8,
                "search_type": "fulltext",
                "metadata": {}
            }],
            "total_results": 1,
            "search_type": "fulltext",
            "query": "test query",
            "execution_time": 0.1
        }
        
        async def run_test():
            with patch.object(self.service.hybrid_engine, 'search') as mock_search:
                mock_search.return_value = expected_result
                
                result = await self.service.fulltext_search(
                    "test query",
                    content_types=["code"],
                    limit=5
                )
            
            self.assertEqual(result["total_results"], 1)
            self.assertEqual(result["results"][0]["search_type"], "fulltext")
            
            mock_search.assert_called_once_with(
                "test query",
                search_type="fulltext",
                content_types=["code"],
                limit=5
            )
        
        self.run_async_test(run_test())
    
    def test_semantic_search(self):
        """Test semantic search through service interface."""
        expected_result = {
            "results": [{
                "content": "semantic content",
                "file_path": "semantic_file.py",
                "content_type": "code",
                "score": 0.95,
                "search_type": "semantic",
                "metadata": {}
            }],
            "total_results": 1,
            "search_type": "semantic",
            "query": "semantic query",
            "execution_time": 0.1
        }
        
        async def run_test():
            with patch.object(self.service.hybrid_engine, 'search') as mock_search:
                mock_search.return_value = expected_result
                
                result = await self.service.semantic_search(
                    "semantic query",
                    embedding_model="text-embedding-ada-002",
                    limit=3
                )
            
            self.assertEqual(result["total_results"], 1)
            self.assertEqual(result["results"][0]["search_type"], "semantic")
            
            mock_search.assert_called_once_with(
                "semantic query",
                search_type="semantic",
                embedding_model="text-embedding-ada-002",
                limit=3
            )
        
        self.run_async_test(run_test())
    
    def test_search_with_embedding_failure(self):
        """Test search behavior when embedding generation fails."""
        # Mock search to simulate embedding failure fallback
        fallback_result = {
            "results": [{
                "content": "fallback content",
                "file_path": "fallback_file.py",
                "content_type": "code",
                "score": 0.7,
                "search_type": "fulltext",
                "metadata": {}
            }],
            "total_results": 1,
            "search_type": "fulltext",
            "query": "test query",
            "execution_time": 0.1,
            "fallback_reason": "Embedding service unavailable"
        }
        
        async def run_test():
            with patch.object(self.service.hybrid_engine, 'search') as mock_search:
                mock_search.return_value = fallback_result
                
                result = await self.service.search(
                    "test query",
                    search_type="hybrid",
                    limit=10
                )
            
            self.assertEqual(result["total_results"], 1)
            self.assertEqual(result["results"][0]["search_type"], "fulltext")
            self.assertIn("fallback_reason", result)
            
            mock_search.assert_called_once_with(
                "test query",
                search_type="hybrid",
                limit=10
            )
        
        self.run_async_test(run_test())
    
    def test_get_status(self):
        """Test service status retrieval."""
        async def run_test():
            with patch.object(self.service.hybrid_engine, 'get_status') as mock_status:
                mock_status.return_value = {
                    "database_connected": True,
                    "tables": {
                        "documents": True,
                        "embeddings": True
                    },
                    "fts_ready": True,
                    "vss_ready": True,
                    "total_documents": 100,
                    "total_embeddings": 50
                }
                
                status = await self.service.get_status()
                
                self.assertIn("database_connected", status)
                self.assertIn("fts_ready", status)
                self.assertIn("vss_ready", status)
                self.assertTrue(status["database_connected"])
                
                mock_status.assert_called_once()
        
        self.run_async_test(run_test())
    
    def run_async_test(self, coro):
        """Helper to run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class TestSearchServiceIntegration(unittest.TestCase):
    """Integration tests for search service."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_integration.db")
        
        # Initialize database with test data
        from src.mcp_devagent.database.connection import DatabaseManager
        database_url = f"sqlite+aiosqlite:///{self.db_path}"
        self.db_manager = DatabaseManager(database_url)
        
        # Run async initialization in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.db_manager.initialize())
        finally:
            loop.close()
        
        # Mock embedding service
        self.mock_embedding_service = MagicMock()
        
        self.service = SearchService(self.db_path, self.mock_embedding_service)
    
    def tearDown(self):
        """Clean up integration test environment."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_end_to_end_search_workflow(self):
        """Test complete search workflow with real database."""
        # This would test the complete workflow from database setup
        # through search execution with real or mock data
        pass
    
    def run_async_test(self, coro):
        """Helper to run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)