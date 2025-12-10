import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from sqlalchemy import text
from prompt_manager.api.http_server import _init_supabase_schema

@pytest.mark.asyncio
async def test_init_supabase_schema_success():
    """Test successful initialization of Supabase schema"""
    connection_string = "postgresql+asyncpg://user:pass@localhost/db"
    dimension = 1024

    # Create a mock for the connection
    mock_conn = AsyncMock()
    
    # Create a mock for the engine
    # Note: engine.begin() is a synchronous method that returns an async context manager.
    # So we use MagicMock for the engine, but dispose() is async so it needs AsyncMock.
    mock_engine = MagicMock()
    mock_engine.dispose = AsyncMock()
    
    # Mock the context manager returned by begin()
    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)
    
    mock_engine.begin.return_value = mock_context_manager
    
    # Patch where create_async_engine is DEFINED
    with patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine) as mock_create_engine:
        with patch("prompt_manager.api.http_server.SQLModel") as mock_sqlmodel:
            # Execute
            await _init_supabase_schema(connection_string, dimension)
            
            # Verify engine creation
            mock_create_engine.assert_called_once_with(connection_string, echo=False)
            
            # Verify SQLModel create_all called
            mock_conn.run_sync.assert_called_once_with(mock_sqlmodel.metadata.create_all)
            
            # Verify SQL executions
            assert mock_conn.execute.call_count == 3
            
            # Check calls
            calls = mock_conn.execute.call_args_list
            
            # 1. Extension
            assert "CREATE EXTENSION IF NOT EXISTS vector" in str(calls[0][0][0])
            
            # 2. Table (check dimension injection)
            table_sql = str(calls[1][0][0])
            assert "CREATE TABLE IF NOT EXISTS vec_prompts" in table_sql
            assert f"vector({dimension})" in table_sql
            
            # 3. Function (check dimension injection)
            func_sql = str(calls[2][0][0])
            assert "CREATE OR REPLACE FUNCTION match_prompt_versions" in func_sql
            assert f"query_embedding vector({dimension})" in func_sql
            
            # Verify engine disposal
            mock_engine.dispose.assert_awaited_once()

@pytest.mark.asyncio
async def test_init_supabase_schema_failure():
    """Test failure handling during initialization"""
    connection_string = "postgresql+asyncpg://user:pass@localhost/db"
    
    with patch("sqlalchemy.ext.asyncio.create_async_engine") as mock_create_engine:
        # Same setup as success case but with failure
        mock_engine = MagicMock()
        
        # Mock failure in begin()
        mock_context_manager = MagicMock()
        # __aenter__ should be an async mock that raises exception
        mock_context_manager.__aenter__ = AsyncMock(side_effect=Exception("DB Connection Failed"))
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        
        mock_engine.begin.return_value = mock_context_manager
        
        mock_create_engine.return_value = mock_engine
        
        # Should raise exception
        with pytest.raises(Exception, match="DB Connection Failed"):
            await _init_supabase_schema(connection_string)
