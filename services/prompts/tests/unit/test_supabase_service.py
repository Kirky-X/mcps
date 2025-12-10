import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from prompt_manager.services.supabase_service import SupabaseService, DatabaseError
from prompt_manager.utils.config import SupabaseConfig

@pytest.fixture
def mock_supabase_client():
    client = AsyncMock()
    # Mock table().select()... chains
    # table() returns a query builder
    # select() returns a query builder
    # execute() returns response
    
    query_builder = AsyncMock()
    # Important: table() is not async, it returns a builder immediately
    # But AsyncMock makes all calls async by default unless configured otherwise
    # We need client.table to be a normal Mock that returns an AsyncMock (query_builder)
    # Wait, supabase-py AsyncClient.table() is synchronous, returning a builder.
    # The builder methods (select, insert, etc) return builder.
    # Only execute() is async.
    
    # Let's re-configure:
    client.table = MagicMock(return_value=query_builder)
    client.rpc = MagicMock(return_value=query_builder)
    
    # Chainable methods
    query_builder.select = MagicMock(return_value=query_builder)
    query_builder.insert = MagicMock(return_value=query_builder)
    query_builder.update = MagicMock(return_value=query_builder)
    query_builder.delete = MagicMock(return_value=query_builder)
    query_builder.eq = MagicMock(return_value=query_builder)
    query_builder.order = MagicMock(return_value=query_builder)
    query_builder.limit = MagicMock(return_value=query_builder)
    query_builder.range = MagicMock(return_value=query_builder)
    
    # Execute return
    response = MagicMock()
    response.data = [{"id": 1, "name": "test"}]
    query_builder.execute = AsyncMock(return_value=response)
    
    return client

@pytest.fixture
def supabase_service(mock_supabase_client):
    config = SupabaseConfig(url="http://test.supabase.co", key="test-key")
    service = SupabaseService(config)
    service.client = mock_supabase_client
    service._initialized = True
    return service

@pytest.mark.asyncio
async def test_initialize_success(supabase_service):
    # Reset initialized state to test initialize flow
    supabase_service._initialized = False
    supabase_service.client = None
    
    with patch("prompt_manager.services.supabase_service.AsyncClient.create", new_callable=AsyncMock) as mock_create:
        mock_client = AsyncMock()
        # Mock internal structure of the created client too
        mock_query_builder = AsyncMock()
        mock_client.table = MagicMock(return_value=mock_query_builder)
        mock_query_builder.select = MagicMock(return_value=mock_query_builder)
        mock_query_builder.limit = MagicMock(return_value=mock_query_builder)
        mock_query_builder.execute = AsyncMock(return_value=MagicMock(data=[]))
        
        mock_create.return_value = mock_client
        
        await supabase_service.initialize()
        
        assert supabase_service._initialized is True
        assert supabase_service.client is not None

@pytest.mark.asyncio
async def test_initialize_failure(supabase_service):
    supabase_service._initialized = False
    supabase_service.client = None
    
    with patch("prompt_manager.services.supabase_service.AsyncClient.create", side_effect=Exception("Init failed")):
        with pytest.raises(DatabaseError, match="Supabase operation failed"):
            await supabase_service.initialize()

@pytest.mark.asyncio
async def test_check_connection_success(supabase_service):
    # Setup mock for success
    # .table().select().limit().execute()
    query_builder = supabase_service.client.table.return_value
    query_builder.select.return_value.limit.return_value.execute.return_value = MagicMock()
    
    await supabase_service.check_connection()
    # Should not raise

@pytest.mark.asyncio
async def test_check_connection_failure(supabase_service):
    # Setup mock for failure
    query_builder = supabase_service.client.table.return_value
    query_builder.select.return_value.limit.return_value.execute.side_effect = Exception("Connection failed")
    
    with pytest.raises(DatabaseError, match="Supabase operation failed"):
        await supabase_service.check_connection()

@pytest.mark.asyncio
async def test_select_basic(supabase_service):
    result = await supabase_service.select("users")
    
    assert result == [{"id": 1, "name": "test"}]
    supabase_service.client.table.assert_called_with("users")
    supabase_service.client.table().select.assert_called_with("*")

@pytest.mark.asyncio
async def test_select_with_filters(supabase_service):
    await supabase_service.select("users", filters={"id": 1, "active": True})
    
    # Verify chain calls
    # Since eq returns self, we check call count
    assert supabase_service.client.table().select().eq.call_count == 2

@pytest.mark.asyncio
async def test_select_failure(supabase_service):
    supabase_service.client.table("users").select("*").execute.side_effect = Exception("Select failed")
    
    with pytest.raises(DatabaseError, match="Supabase operation failed"):
        await supabase_service.select("users")

@pytest.mark.asyncio
async def test_insert_success(supabase_service):
    data = {"name": "new_user"}
    result = await supabase_service.insert("users", data)
    
    assert result == [{"id": 1, "name": "test"}]
    supabase_service.client.table("users").insert.assert_called_with(data)

@pytest.mark.asyncio
async def test_update_success(supabase_service):
    data = {"name": "updated"}
    filters = {"id": 1}
    
    result = await supabase_service.update("users", data, filters)
    
    assert result == [{"id": 1, "name": "test"}]
    supabase_service.client.table("users").update.assert_called_with(data)
    supabase_service.client.table().update().eq.assert_called_with("id", 1)

@pytest.mark.asyncio
async def test_update_missing_filters(supabase_service):
    with pytest.raises(DatabaseError, match="Update requires filters"):
        await supabase_service.update("users", {"name": "updated"}, {})

@pytest.mark.asyncio
async def test_delete_success(supabase_service):
    filters = {"id": 1}
    result = await supabase_service.delete("users", filters)
    
    assert result == [{"id": 1, "name": "test"}]
    supabase_service.client.table("users").delete.assert_called()
    supabase_service.client.table().delete().eq.assert_called_with("id", 1)

@pytest.mark.asyncio
async def test_delete_missing_filters(supabase_service):
    with pytest.raises(DatabaseError, match="Delete requires filters"):
        await supabase_service.delete("users", {})

@pytest.mark.asyncio
async def test_search_vectors(supabase_service):
    embedding = [0.1, 0.2, 0.3]
    
    # Mock RPC call
    rpc_mock = MagicMock()
    rpc_mock.execute = AsyncMock()
    rpc_mock.execute.return_value.data = [{"id": "uuid-1", "similarity": 0.95}]
    supabase_service.client.rpc.return_value = rpc_mock
    
    results = await supabase_service.search_vectors(embedding)
    
    assert len(results) == 1
    assert results[0] == ("uuid-1", 0.95)
    supabase_service.client.rpc.assert_called_with(
        "match_prompt_versions", 
        {
            "query_embedding": embedding,
            "match_threshold": 0.7,
            "match_count": 10
        }
    )
