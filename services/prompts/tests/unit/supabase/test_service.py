import asyncio
import pytest
from unittest.mock import MagicMock, patch
from prompt_manager.dal.supabase.service import SupabaseService as DomainSupabaseService
from prompt_manager.services.supabase_service import SupabaseService as GenericSupabaseService
from prompt_manager.utils.exceptions import DatabaseError

@pytest.fixture
def mock_generic_service():
    return MagicMock(spec=GenericSupabaseService)

@pytest.fixture
def service(mock_generic_service):
    return DomainSupabaseService(mock_generic_service)

@pytest.mark.asyncio
async def test_get_prompt_version_success(service, mock_generic_service):
    # Setup mocks
    mock_generic_service.select.return_value = [{"id": "p1"}]
    
    # Mock client chain for complex query
    mock_query_builder = MagicMock()
    mock_query_builder.eq.return_value = mock_query_builder
    mock_query_builder.select.return_value = mock_query_builder
    
    # Mock execute response
    mock_response = MagicMock()
    mock_response.data = [{"id": "v1", "version": "1.0"}]
    
    # Async execute
    async def async_execute():
        return mock_response
    mock_query_builder.execute.side_effect = async_execute
    
    # Mock client property
    mock_client = MagicMock()
    mock_client.table.return_value = mock_query_builder
    mock_generic_service.client = mock_client
    
    result = await service.get_prompt_version("test_prompt", "1.0")
    
    assert result == {"id": "v1", "version": "1.0"}
    mock_generic_service.select.assert_called_once_with("prompts", columns="id", filters={"name": "test_prompt"})

@pytest.mark.asyncio
async def test_get_prompt_version_not_found(service, mock_generic_service):
    mock_generic_service.select.return_value = []
    
    result = await service.get_prompt_version("unknown_prompt")
    
    assert result is None

@pytest.mark.asyncio
async def test_create_prompt_version(service, mock_generic_service):
    mock_generic_service.insert.return_value = [{"id": "v1"}]
    
    result = await service.create_prompt_version({"version": "1.0"})
    
    assert result == {"id": "v1"}
    mock_generic_service.insert.assert_called_once_with("prompt_versions", {"version": "1.0"})

@pytest.mark.asyncio
async def test_get_prompt_id_by_name(service, mock_generic_service):
    mock_generic_service.select.return_value = [{"id": "p1"}]
    
    result = await service.get_prompt_id_by_name("test")
    
    assert result == "p1"

@pytest.mark.asyncio
async def test_update_prompt_status(service, mock_generic_service):
    mock_generic_service.update.return_value = [{"id": "v1"}]
    
    result = await service.update_prompt_status("v1", False)
    
    assert result is True
    mock_generic_service.update.assert_called_once_with(
        "prompt_versions", 
        {"is_active": False}, 
        filters={"id": "v1"}
    )

@pytest.mark.asyncio
async def test_search_vectors(service, mock_generic_service):
    mock_generic_service.search_vectors.return_value = [("v1", 0.9)]
    
    result = await service.search_vectors([0.1, 0.2], k=5)
    
    assert result == [("v1", 0.9)]
    mock_generic_service.search_vectors.assert_called_once_with([0.1, 0.2], k=5)

@pytest.mark.asyncio
async def test_error_handling(service, mock_generic_service):
    mock_generic_service.insert.side_effect = DatabaseError("Insert failed")
    
    with pytest.raises(DatabaseError):
        await service.create_prompt_version({})
