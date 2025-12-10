# Copyright (c) Kirky.X. 2025. All rights reserved.
import struct
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy import text
from prompt_manager.dal.vector_index import VectorIndex


class TestVectorIndex:
    def test_init_validation(self):
        """Test initialization validation."""
        with pytest.raises(ValueError, match="dimension must be positive"):
            VectorIndex(dimension=0)
        
        with pytest.raises(ValueError, match="dimension must be positive"):
            VectorIndex(dimension=-1)
            
        idx = VectorIndex(dimension=128)
        assert idx.dimension == 128
        assert idx.use_virtual is True

    def test_serialize_vector_sqlite(self):
        """Test vector serialization for SQLite."""
        idx = VectorIndex(dimension=4)
        vec = [1.0, 2.0, 3.0, 4.0]
        
        # Should raise error for empty vector
        with pytest.raises(ValueError, match="embedding must not be empty"):
            idx._serialize_vector_sqlite([])
            
        # Should return bytes
        packed = idx._serialize_vector_sqlite(vec)
        assert isinstance(packed, bytes)
        assert len(packed) == 4 * 4  # 4 floats * 4 bytes
        
        # Verify unpacking works
        unpacked = struct.unpack('4f', packed)
        assert list(unpacked) == vec

    def test_format_vector_postgres(self):
        """Test vector formatting for PostgreSQL."""
        idx = VectorIndex(dimension=2)
        vec = [1.0, 2.0]
        
        # Should raise error for empty vector
        with pytest.raises(ValueError, match="embedding must not be empty"):
            idx._format_vector_postgres([])
            
        # Should return string
        formatted = idx._format_vector_postgres(vec)
        assert isinstance(formatted, str)
        assert formatted == "[1.0, 2.0]"

    @pytest.mark.asyncio
    async def test_create_index_virtual_success(self):
        """Test successful virtual table creation for SQLite."""
        idx = VectorIndex(dimension=1536)
        session = AsyncMock()
        
        # Mock dialect
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)
        
        await idx.create_index(session)
        
        # Should execute CREATE VIRTUAL TABLE and validation query
        assert session.execute.call_count >= 1
        args = session.execute.call_args_list[0][0][0]
        assert "CREATE VIRTUAL TABLE IF NOT EXISTS vec_prompts" in str(args)
        assert idx.use_virtual is True

    @pytest.mark.asyncio
    async def test_create_index_postgresql(self):
        """Test table creation for PostgreSQL."""
        idx = VectorIndex(dimension=1536)
        session = AsyncMock()
        
        # Mock dialect
        mock_bind = MagicMock()
        mock_bind.dialect.name = "postgresql"
        session.get_bind = MagicMock(return_value=mock_bind)
        
        await idx.create_index(session)
        
        # Should execute CREATE EXTENSION and CREATE TABLE
        # Verify calls
        calls = session.execute.call_args_list
        assert any("CREATE EXTENSION IF NOT EXISTS vector" in str(c[0][0]) for c in calls)
        assert any("CREATE TABLE IF NOT EXISTS vec_prompts" in str(c[0][0]) for c in calls)
        assert any("vector(1536)" in str(c[0][0]) for c in calls)

    @pytest.mark.asyncio
    async def test_create_index_fallback_sqlite(self):
        """Test fallback to standard table for SQLite (without extension)."""
        idx = VectorIndex(dimension=1536)
        session = AsyncMock()
        
        # Mock dialect
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)

        # Mock first execution failure (virtual table creation or verification)
        # We need to be careful about which call fails.
        # 1. CREATE VIRTUAL TABLE
        # 2. SELECT ... MATCH x'00' (verification)
        # Let's fail the verification
        session.execute.side_effect = [
            None, # CREATE VIRTUAL TABLE success (or ignored)
            Exception("sqlite-vec extension not working"), # Verification fails
            None  # CREATE TABLE fallback
        ]
        
        await idx.create_index(session)
        
        assert idx.use_virtual is False
        # Last call should be standard CREATE TABLE with BLOB
        args = session.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS vec_prompts" in str(args)
        assert "BLOB" in str(args)

    @pytest.mark.asyncio
    async def test_insert_dimension_mismatch(self):
        """Test insert with wrong dimension."""
        idx = VectorIndex(dimension=4)
        session = AsyncMock()
        
        with pytest.raises(ValueError, match="Embedding dimension mismatch"):
            await idx.insert(session, "id", [1.0, 2.0])

    @pytest.mark.asyncio
    async def test_insert_postgresql(self):
        """Test insert logic for PostgreSQL."""
        idx = VectorIndex(dimension=2)
        session = AsyncMock()
        
        # Mock dialect
        mock_bind = MagicMock()
        mock_bind.dialect.name = "postgresql"
        session.get_bind = MagicMock(return_value=mock_bind)
        
        await idx.insert(session, "test_id", [1.0, 2.0])
        
        args = session.execute.call_args[0][0]
        params = session.execute.call_args[0][1]
        
        assert "ON CONFLICT (version_id) DO UPDATE" in str(args)
        assert params["id"] == "test_id"
        assert params["vec"] == "[1.0, 2.0]"

    @pytest.mark.asyncio
    async def test_insert_sqlite(self):
        """Test insert logic for SQLite."""
        idx = VectorIndex(dimension=2)
        session = AsyncMock()
        
        # Mock dialect
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)
        
        await idx.insert(session, "test_id", [1.0, 2.0])
        
        args = session.execute.call_args[0][0]
        params = session.execute.call_args[0][1]
        
        assert "INSERT OR REPLACE INTO" in str(args)
        assert params["id"] == "test_id"

    @pytest.mark.asyncio
    async def test_search_dimension_mismatch(self):
        """Test search with wrong dimension."""
        idx = VectorIndex(dimension=4)
        session = AsyncMock()
        
        with pytest.raises(ValueError, match="Query embedding dimension mismatch"):
            await idx.search(session, [1.0, 2.0])

    @pytest.mark.asyncio
    async def test_search_virtual_success(self):
        """Test search using virtual table (SQLite)."""
        idx = VectorIndex(dimension=2)
        idx.use_virtual = True
        session = AsyncMock()
        
        # Mock dialect
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)

        # Mock result
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("id1", 0.1), ("id2", 0.2)]
        session.execute.return_value = mock_result
        
        results = await idx.search(session, [1.0, 2.0], k=5)
        
        assert len(results) == 2
        assert results[0][0] == "id1"
        
        args = session.execute.call_args[0][0]
        params = session.execute.call_args[0][1]
        
        assert "MATCH :query" in str(args)
        assert params["k"] == 5

    @pytest.mark.asyncio
    async def test_search_sqlite_failure(self):
        """Test search failure in SQLite returns empty list."""
        idx = VectorIndex(dimension=2)
        idx.use_virtual = True
        session = AsyncMock()
        
        # Mock dialect
        mock_bind = MagicMock()
        mock_bind.dialect.name = "sqlite"
        session.get_bind = MagicMock(return_value=mock_bind)
        
        session.execute.side_effect = Exception("Virtual table error")
        
        results = await idx.search(session, [1.1, 1.1], k=1)
        
        assert results == []

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete operation."""
        idx = VectorIndex(dimension=4)
        session = AsyncMock()
        
        await idx.delete(session, "test_id")
        
        args = session.execute.call_args[0][0]
        params = session.execute.call_args[0][1]
        
        assert "DELETE FROM vec_prompts" in str(args)
        assert params["id"] == "test_id"
