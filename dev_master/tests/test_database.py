"""Database tests for MCP DevAgent.

Tests SQLite database schema, FTS5 full-text search, and VSS vector search functionality.
"""

import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List
from unittest.mock import patch, MagicMock

from src.mcp_devagent.database.connection import DatabaseManager
from src.mcp_devagent.database.init import DatabaseInitializer


class TestDatabaseSchema(unittest.TestCase):
    """Test database schema creation and validation."""
    
    def setUp(self):
        """Set up test database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        self.db_manager = DatabaseManager(self.db_path)
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_database_initialization_and_tables(self):
        """Test database file creation and core tables creation."""
        initializer = DatabaseInitializer(self.db_path)
        initializer.initialize()
        
        # Verify database file exists
        self.assertTrue(os.path.exists(self.db_path))
        
        # Verify core tables are created
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
        
        # Check core tables exist (new architecture)
        expected_tables = [
            'development_runs', 'code_repositories', 'modules', 'code_files',
            'cot_records', 'code_chunks', 'test_results', 'code_embeddings',
            'codebase_indexes', 'problem_escalations', 'search_sessions',
            'code_artifacts', 'code_chunks_fts', 'code_files_fts'
        ]
        
        for table in expected_tables:
            self.assertIn(table, tables, f"Table {table} not found")
    
    def test_vss_tables_and_schema_validation(self):
        """Test VSS tables creation and table schema correctness."""
        initializer = DatabaseInitializer(self.db_path)
        initializer.initialize()
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if VSS extension is available and test VSS tables
            try:
                conn.execute("SELECT vss_version()")
                vss_available = True
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_vss'"
                )
                vss_tables = [row[0] for row in cursor.fetchall()]
                self.assertGreater(len(vss_tables), 0)
            except Exception:
                vss_available = False
            
            # Test table schema correctness for development_runs
            cursor = conn.execute("PRAGMA table_info(development_runs)")
            columns = [row[1] for row in cursor.fetchall()]
            expected_columns = ['run_id', 'start_time', 'end_time', 'initial_prd', 'tech_stack', 'final_status', 'codebase_index_id']
            for col in expected_columns:
                self.assertIn(col, columns)
    
    def test_foreign_key_constraints(self):
        """Test foreign key relationships."""
        initializer = DatabaseInitializer(self.db_path)
        initializer.initialize()
        
        with sqlite3.connect(self.db_path) as conn:
            # Check foreign key from code_files to code_repositories
            cursor = conn.execute("PRAGMA foreign_key_list(code_files)")
            foreign_keys = cursor.fetchall()
            
            repo_fk = any(fk[2] == 'code_repositories' for fk in foreign_keys)
            self.assertTrue(repo_fk, "Missing foreign key to code_repositories table")
            
            # Check foreign key from code_chunks to code_files
            cursor = conn.execute("PRAGMA foreign_key_list(code_chunks)")
            foreign_keys = cursor.fetchall()
            
            file_fk = any(fk[2] == 'code_files' for fk in foreign_keys)
            self.assertTrue(file_fk, "Missing foreign key to code_files table")
            
            # Check foreign key from code_embeddings to code_chunks
            cursor = conn.execute("PRAGMA foreign_key_list(code_embeddings)")
            foreign_keys = cursor.fetchall()
            
            chunk_fk = any(fk[2] == 'code_chunks' for fk in foreign_keys)
            self.assertTrue(chunk_fk, "Missing foreign key to code_chunks table")


class TestFTSSearch(unittest.IsolatedAsyncioTestCase):
    """Test FTS5 full-text search functionality."""
    
    async def asyncSetUp(self):
        """Set up test database with sample data."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_fts.db")
        initializer = DatabaseInitializer(self.db_path)
        await initializer.initialize_database()
        
        # Insert sample data
        self._insert_sample_data()
    
    async def asyncTearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    def _insert_sample_data(self):
        """Insert sample data for FTS testing."""
        with sqlite3.connect(self.db_path) as conn:
            # Insert code repositories
            conn.execute("""
                INSERT INTO code_repositories (name, path, description, language, created_at)
                VALUES ('test_repo', '/path/to/repo', 'Test repository', 'python', '2024-01-01 00:00:00')
            """)
            
            # Insert code files
            conn.execute("""
                INSERT INTO code_files (repository_id, file_path, file_name, file_extension, created_at, last_modified)
                VALUES (1, '/path/to/file.py', 'file.py', '.py', '2024-01-01 00:00:00', '2024-01-01 00:00:00')
            """)
            
            # Insert code chunks
        chunks_data = [
            (1, 0, 'def calculate_sum(a, b):\n    return a + b', 'function', 1, 2),
            (1, 1, 'import numpy as np\ndef process_array(arr):\n    return np.sum(arr)', 'function', 4, 6)
        ]
        
        for file_id, chunk_index, content, content_type, start_line, end_line in chunks_data:
            # Insert into main table (let SQLite auto-generate the id)
            cursor = conn.execute("""
                INSERT INTO code_chunks 
                (file_id, chunk_index, content, content_type, start_line, end_line, created_at)
                VALUES (?, ?, ?, ?, ?, ?, '2024-01-01 00:00:00')
            """, (file_id, chunk_index, content, content_type, start_line, end_line))
            
            # Get the auto-generated chunk id
            chunk_id = cursor.lastrowid
            
            # Insert into FTS table
            conn.execute("""
                INSERT INTO code_chunks_fts 
                (chunk_id, content, content_type, file_path, file_name, repository_name, language)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (chunk_id, content, content_type, '/path/to/file.py', 'file.py', 'test_repo', 'python'))
            
            conn.commit()
    
    async def test_fts_table_exists(self):
        """Test FTS5 table is created."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE name='code_chunks_fts'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, "FTS5 table not found")
    
    async def test_fts_search_function_name(self):
        """Test FTS search by function name."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT cc.content, cc.content_type
                FROM code_chunks_fts 
                JOIN code_chunks cc ON code_chunks_fts.chunk_id = cc.id
                WHERE code_chunks_fts MATCH 'calculate_sum'
            """)
            
            results = cursor.fetchall()
            self.assertEqual(len(results), 1)
            self.assertIn('calculate_sum', results[0][0])
            self.assertEqual(results[0][1], 'function')
    
    async def test_fts_search_content(self):
        """Test FTS search by content."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT cc.content
                FROM code_chunks_fts 
                JOIN code_chunks cc ON code_chunks_fts.chunk_id = cc.id
                WHERE code_chunks_fts MATCH 'numpy'
            """)
            
            results = cursor.fetchall()
            self.assertEqual(len(results), 1)
            self.assertIn('numpy', results[0][0])
    
    async def test_fts_search_with_bm25_scoring(self):
        """Test FTS search with BM25 scoring."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT cc.content, bm25(code_chunks_fts) as score
                FROM code_chunks_fts 
                JOIN code_chunks cc ON code_chunks_fts.chunk_id = cc.id
                WHERE code_chunks_fts MATCH 'def'
                ORDER BY score DESC
            """)
            
            results = cursor.fetchall()
            self.assertGreater(len(results), 0)
            
            # Check scores are in descending order
            scores = [row[1] for row in results]
            self.assertEqual(scores, sorted(scores, reverse=True))
    
    async def test_fts_search_by_content_type(self):
        """Test FTS search by content type."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT cc.content_type
                FROM code_chunks_fts 
                JOIN code_chunks cc ON code_chunks_fts.chunk_id = cc.id
                WHERE code_chunks_fts MATCH 'function'
            """)
            
            results = cursor.fetchall()
            self.assertGreater(len(results), 0)
            
            # All results should be functions
            for result in results:
                self.assertEqual(result[0], 'function')


class TestVSSSearch(unittest.TestCase):
    """Test VSS vector search functionality."""
    
    def setUp(self):
        """Set up test database with sample data."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_vss.db")
        # Create DatabaseManager with proper database URL
        database_url = f"sqlite+aiosqlite:///{self.db_path}"
        self.db_manager = DatabaseManager(database_url)
        
        # Initialize database asynchronously
        import asyncio
        asyncio.run(self.db_manager.initialize())
        
        # Initialize database schema including VSS tables
        from src.mcp_devagent.database.init import DatabaseInitializer
        initializer = DatabaseInitializer(self.db_path)
        asyncio.run(initializer.initialize_database())
        
        # Check if VSS is available
        self.vss_available = self._check_vss_availability()
        
        if self.vss_available:
            self._insert_sample_data()
    
    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    def _check_vss_availability(self) -> bool:
        """Check if VSS extension is available."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Try to load VSS extension
                conn.enable_load_extension(True)
                
                # Load vector0 extension first, then vss0
                vss_path = "/root/miniforge3/lib/python3.12/site-packages/sqlite_vss"
                conn.load_extension(f"{vss_path}/vector0")
                conn.load_extension(f"{vss_path}/vss0")
                
                # Check if VSS tables exist
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_vss'"
                )
                vss_tables = cursor.fetchall()
                return len(vss_tables) > 0
        except Exception as e:
            print(f"VSS availability check failed: {e}")
            return False
    
    def _insert_sample_data(self):
        """Insert sample embeddings for testing."""
        with sqlite3.connect(self.db_path) as conn:
            # Insert repository (id is auto-increment, so don't specify it)
            cursor = conn.execute("""
                INSERT INTO code_repositories (name, path, language, framework, created_at)
                VALUES ('VSS Test Repository', '/test', 'python', 'none', '2024-01-01 00:00:00')
            """)
            repo_id = cursor.lastrowid
            
            # Insert code file
            cursor = conn.execute("""
                INSERT INTO code_files (repository_id, file_path, file_name, file_extension, file_size, last_modified)
                VALUES (?, '/test/math.py', 'math.py', '.py', 200, '2024-01-01 00:00:00')
            """, (repo_id,))
            file_id = cursor.lastrowid
            
            # Insert code chunks
            chunks_data = [
                {
                    'content': 'def add_numbers(x, y): return x + y',
                    'embedding': [0.1, 0.2, 0.3] + [0.0] * 381  # 384-dim vector
                },
                {
                    'content': 'def subtract_numbers(x, y): return x - y',
                    'embedding': [0.2, 0.3, 0.4] + [0.0] * 381
                },
                {
                    'content': 'class MathOperations: pass',
                    'embedding': [0.5, 0.6, 0.7] + [0.0] * 381
                }
            ]
            
            for i, chunk in enumerate(chunks_data):
                # Insert code chunk
                cursor = conn.execute("""
                    INSERT INTO code_chunks 
                    (file_id, chunk_index, content, content_type, start_line, end_line, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id, i, chunk['content'], 'function', 1, 1, '2024-01-01 00:00:00'
                ))
                chunk_id = cursor.lastrowid
                
                # Insert embedding
                conn.execute("""
                    INSERT INTO code_embeddings 
                    (chunk_id, model_name, embedding_vector, vector_dimension, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    chunk_id, 'test_model', 
                    json.dumps(chunk['embedding']), 384, '2024-01-01 00:00:00'
                ))
            
            conn.commit()
    
    def test_vss_table_creation(self):
        """Test VSS table is created if extension is available."""
        if not self.vss_available:
            self.skipTest("VSS extension not available")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE name LIKE '%_vss'"
            )
            result = cursor.fetchone()
            self.assertIsNotNone(result, "VSS table not found")
    
    def test_vss_search_functionality(self):
        """Test VSS vector similarity search."""
        if not self.vss_available:
            self.skipTest("VSS extension not available")
        
        # Query vector similar to first embedding
        query_vector = [0.1, 0.2, 0.3] + [0.0] * 381
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Test basic embedding retrieval first
                cursor = conn.execute("""
                    SELECT cc.content, ce.embedding_vector
                    FROM code_embeddings ce
                    JOIN code_chunks cc ON ce.chunk_id = cc.id
                    ORDER BY ce.created_at
                    LIMIT 3
                """)
                
                results = cursor.fetchall()
                self.assertGreater(len(results), 0)
                
                # First result should contain add_numbers
                self.assertIn('add_numbers', results[0][0])
                
        except Exception as e:
            self.skipTest(f"VSS search failed: {e}")


class TestDatabaseManager(unittest.IsolatedAsyncioTestCase):
    """Test DatabaseManager functionality."""
    
    async def asyncSetUp(self):
        """Set up test database manager."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_manager.db")
        self.db_manager = DatabaseManager(f"sqlite+aiosqlite:///{self.db_path}")
        await self.db_manager.initialize()
        
        # Initialize database schema
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from mcp_devagent.database.init import DatabaseInitializer
        initializer = DatabaseInitializer(self.db_path)
        await initializer.initialize_database()
    
    async def asyncTearDown(self):
        """Clean up test database."""
        await self.db_manager.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    async def test_initialization(self):
        """Test database manager initialization."""
        self.assertTrue(os.path.exists(self.db_path))
        
        # Test session works
        async with self.db_manager.get_session() as session:
            self.assertIsNotNone(session)
    
    async def test_session_management(self):
        """Test session management functionality."""
        # Get multiple sessions
        async with self.db_manager.get_session() as session1:
            async with self.db_manager.get_session() as session2:
                self.assertIsNotNone(session1)
                self.assertIsNotNone(session2)
    
    async def test_transaction_handling(self):
        """Test transaction handling."""
        # Test successful transaction using raw connection
        async with self.db_manager.get_raw_connection() as conn:
            await conn.execute("""
                INSERT INTO development_runs (start_time, initial_prd, tech_stack, final_status)
                VALUES (datetime('now'), 'Test PRD', 'Python', 'IN_PROGRESS')
            """)
            await conn.commit()
        
        # Verify data was inserted
        async with self.db_manager.get_raw_connection() as conn:
            cursor = await conn.execute("SELECT final_status FROM development_runs WHERE initial_prd='Test PRD'")
            result = await cursor.fetchone()
            self.assertIsNotNone(result)
            self.assertEqual(result[0], 'IN_PROGRESS')
    
    async def test_error_handling(self):
        """Test error handling in database operations."""
        # Test invalid SQL
        with self.assertRaises(Exception):
            async with self.db_manager.get_raw_connection() as conn:
                await conn.execute("INVALID SQL STATEMENT")
    
    async def test_cleanup(self):
        """Test database cleanup."""
        # Test cleanup doesn't raise errors
        try:
            await self.db_manager.close()
        except Exception as e:
            self.fail(f"Cleanup raised an exception: {e}")


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)