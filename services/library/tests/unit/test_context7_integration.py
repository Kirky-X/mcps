import pytest
import asyncio
from unittest.mock import Mock, patch
from library.clients.context7_client import Context7Client
from library.core.config import Settings
from library.tools.context7_tools import Context7Tools, create_context7_tools
import httpx

@pytest.fixture
def mock_settings():
    settings = Settings()
    settings.context7_api_key = "test-key"
    settings.context7_base_url = "https://test.api/v1"
    return settings

@pytest.fixture
def context7_client(mock_settings):
    return Context7Client(mock_settings)

@pytest.fixture
def context7_tools(mock_settings):
    return Context7Tools(mock_settings)

class TestContext7Client:
    @pytest.mark.asyncio
    async def test_search_success(self, context7_client):
        # Create a mock response object
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {"name": "test-lib", "language": "python", "description": "Test library"}
            ]
        }
        
        # Use patch on the instance method directly
        with patch.object(context7_client, '_make_request_with_retry', new_callable=Mock) as mock_req:
            # Configure the mock to return a future
            future = asyncio.Future()
            future.set_result(mock_response)
            mock_req.return_value = future
            
            # Since client filters results client-side when language is provided
            # we need to make sure our mock data passes the _matches_language check
            # "Test library" contains "test" but not "python"
            # Let's update the description to match the language keywords
            mock_response.json.return_value["results"][0]["description"] = "A python library"
            
            result = await context7_client.search("test", "python")
            assert len(result["results"]) == 1
            assert result["results"][0]["name"] == "test-lib"

    @pytest.mark.asyncio
    async def test_search_fallback(self, context7_client):
        with patch.object(context7_client, '_make_request_with_retry', new_callable=Mock) as mock_req:
            # Configure mock to raise exception
            future = asyncio.Future()
            future.set_exception(httpx.ConnectError("Network error"))
            mock_req.return_value = future
            
            # Should fallback to mock data
            result = await context7_client.search("requests", "python")
            assert "results" in result
            # Mock data contains 'requests'
            assert any(r["name"] == "requests" for r in result["results"])

    @pytest.mark.asyncio
    async def test_get_docs_success(self, context7_client):
        mock_response = Mock()
        mock_response.text = "# Documentation Content"
        
        with patch.object(context7_client, '_make_request_with_retry', new_callable=Mock) as mock_req:
            future = asyncio.Future()
            future.set_result(mock_response)
            mock_req.return_value = future
            
            # Mock search for ID resolution
            with patch.object(context7_client, 'search') as mock_search:
                search_future = asyncio.Future()
                search_future.set_result({"results": [{"id": "/test/lib"}]})
                mock_search.return_value = search_future
                
                result = await context7_client.get_docs("test-lib")
                assert result == "# Documentation Content"

    @pytest.mark.asyncio
    async def test_health_check(self, context7_client):
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        
        with patch.object(context7_client, '_make_request_with_retry', new_callable=Mock) as mock_req:
            future = asyncio.Future()
            future.set_result(mock_response)
            mock_req.return_value = future
            
            result = await context7_client.health_check()
            assert result["status"] == "healthy"
            assert result["api_available"] is True

class TestContext7Tools:
    @pytest.mark.asyncio
    async def test_search_libraries_tool(self, context7_tools):
        with patch.object(context7_tools.client, 'search') as mock_search:
            mock_search.return_value = {"results": ["item1"]}
            
            args = {"query": "test", "language": "python"}
            result = await context7_tools.search_libraries(args)
            
            assert result["success"] is True
            assert result["data"]["results"] == ["item1"]
            mock_search.assert_called_with(query="test", language="python")

    @pytest.mark.asyncio
    async def test_get_library_docs_tool(self, context7_tools):
        with patch.object(context7_tools.client, 'get_docs') as mock_docs:
            mock_docs.return_value = "Doc content"
            
            args = {"library_path": "lib", "doc_type": "api"}
            result = await context7_tools.get_library_docs(args)
            
            assert result["success"] is True
            assert result["data"] == "Doc content"

    def test_create_tools_validation(self):
        settings = Settings()
        settings.context7_api_key = None
        
        with patch('os.getenv', return_value=None):
            with pytest.raises(ValueError, match="Context7 API key is required"):
                create_context7_tools(settings)

    def test_create_tools_env_var(self):
        settings = Settings()
        settings.context7_api_key = None
        
        with patch('os.getenv', return_value="env-key"):
            tools = create_context7_tools(settings)
            assert tools.settings.context7_api_key == "env-key"
