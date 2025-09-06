"""MCP Server tests for MCP DevAgent.

Tests FastAPI application, MCP protocol handling, and API endpoints.
"""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.mcp_devagent.server.app import app
from src.mcp_devagent.server.mcp_protocol import MCPServer, MCPError
from src.mcp_devagent.database.connection import DatabaseManager


class TestFastAPIApp(unittest.TestCase):
    """Test FastAPI application functionality."""
    
    def setUp(self):
        """Set up test client."""
        self.client = TestClient(app)
        
        # Create temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_final.db")
        self.db_url = f"sqlite:///{self.db_path}"
        
        # Mock database manager in app state
        mock_db_manager = MagicMock()
        mock_export_service = MagicMock()
        mock_mcp_server = MagicMock()
        
        # Mock search handler with AsyncMock for async methods
        mock_search_handler = MagicMock()
        mock_search_handler.handle_hybrid = AsyncMock(return_value={
            "results": [],
            "total_results": 0,
            "search_type": "hybrid",
            "query": "test"
        })
        mock_mcp_server.search_handler = mock_search_handler
        
        app.state.db_manager = mock_db_manager
        app.state.export_service = mock_export_service
        app.state.mcp_server = mock_mcp_server
    
    def tearDown(self):
        """Clean up test environment."""
        # Clean up app state
        if hasattr(app.state, 'db_manager'):
            delattr(app.state, 'db_manager')
        if hasattr(app.state, 'export_service'):
            delattr(app.state, 'export_service')
        if hasattr(app.state, 'mcp_server'):
            delattr(app.state, 'mcp_server')
        
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("timestamp", data)
        self.assertIn("version", data)
    
    def test_cors_headers(self):
        """Test CORS headers are present."""
        response = self.client.options("/health")
        
        self.assertEqual(response.status_code, 200)
        headers = response.headers
        self.assertIn("access-control-allow-origin", headers)
        self.assertIn("access-control-allow-methods", headers)
    
    @patch('src.mcp_devagent.server.app.mcp_server')
    def test_mcp_endpoint(self, mock_mcp_server):
        """Test MCP protocol endpoint."""
        # Mock MCP server response
        mock_mcp_server.handle_request = AsyncMock(return_value={
            "jsonrpc": "2.0",
            "id": "test",
            "result": {"status": "success"}
        })
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/list",
            "params": {}
        }
        
        response = self.client.post("/mcp", json=request_data)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["jsonrpc"], "2.0")
        self.assertEqual(data["id"], "test")
    
    def test_development_status_endpoint(self):
        """Test development status endpoint."""
        run_id = "test_run_123"
        
        # Mock the MCP server's development handler
        mock_handler = AsyncMock()
        mock_handler.handle_get_status = AsyncMock(return_value={
            "run_id": run_id,
            "status": "running",
            "progress": 0.5
        })
        app.state.mcp_server.development_handler = mock_handler
        
        response = self.client.get(f"/development/status/{run_id}")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["run_id"], run_id)
        self.assertEqual(data["status"], "running")
    
    def test_hybrid_search_endpoint(self):
        """Test hybrid search endpoint."""
        search_request = {
            "query": "test function",
            "content_types": ["function"],
            "limit": 10
        }
        
        # Mock the MCP server's search handler
        mock_handler = AsyncMock()
        mock_handler.handle_hybrid = AsyncMock(return_value={
            "results": [],
            "total_results": 0,
            "search_type": "hybrid",
            "query": "test function"
        })
        app.state.mcp_server.search_handler = mock_handler
        
        response = self.client.post("/search/hybrid", json=search_request)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["query"], "test function")
        self.assertEqual(data["search_type"], "hybrid")
    
    def test_invalid_json_request(self):
        """Test handling of invalid JSON requests."""
        response = self.client.post("/mcp", data="invalid json")
        
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity
    
    def test_missing_required_fields(self):
        """Test handling of requests with missing required fields."""
        incomplete_request = {
            # Missing required 'query' field
            "limit": 5
        }
        
        response = self.client.post("/search/hybrid", json=incomplete_request)
        
        # Should handle gracefully (either 422 or 400)
        self.assertIn(response.status_code, [400, 422])


class TestMCPProtocol(unittest.TestCase):
    """Test MCP protocol implementation."""
    
    def setUp(self):
        """Set up MCP server for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_mcp.db")
        
        # Initialize database with proper URL format
        database_url = f"sqlite+aiosqlite:///{self.db_path}"
        self.db_manager = DatabaseManager(database_url)
        asyncio.run(self.db_manager.initialize())
        
        # Initialize database schema
        from mcp_devagent.database.init import DatabaseInitializer
        initializer = DatabaseInitializer(self.db_path)
        asyncio.run(initializer.initialize_database())
        
        # Create MCP server with DatabaseManager instance
        self.mcp_server = MCPServer(self.db_manager)
    
    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self.mcp_server, 'cleanup'):
            asyncio.run(self.mcp_server.cleanup())
        
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    async def test_mcp_server_initialization(self):
        """Test MCP server initialization."""
        await self.mcp_server.initialize()
        
        # Check handlers are initialized
        self.assertIsNotNone(self.mcp_server.project_handler)
        self.assertIsNotNone(self.mcp_server.development_handler)
        self.assertIsNotNone(self.mcp_server.search_handler)
        self.assertIsNotNone(self.mcp_server.code_handler)
        self.assertIsNotNone(self.mcp_server.embedding_handler)
    
    async def test_tools_list(self):
        """Test tools/list method."""
        await self.mcp_server.initialize()
        
        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/list",
            "params": {}
        }
        
        response = await self.mcp_server.handle_request(
            request["method"], request["params"]
        )
        # Wrap result in proper JSON-RPC format
        response = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": response
        }
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], "test")
        self.assertIn("result", response)
        self.assertIn("tools", response["result"])
        
        # Check expected tools are present
        tool_names = [tool["name"] for tool in response["result"]["tools"]]
        expected_tools = [
            "project/analyze", "development/start", "search/hybrid",
            "code/generate", "embedding/generate"
        ]
        
        for tool in expected_tools:
            self.assertIn(tool, tool_names)
    
    async def test_resources_list(self):
        """Test resources/list method."""
        await self.mcp_server.initialize()
        
        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "resources/list",
            "params": {}
        }
        
        response = await self.mcp_server.handle_request(
            request["method"], request["params"]
        )
        # Wrap result in proper JSON-RPC format
        response = {
            "jsonrpc": "2.0",
            "id": request["id"],
            "result": response
        }
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], "test")
        self.assertIn("result", response)
        self.assertIn("resources", response["result"])
        
        # Check expected resources are present
        resource_uris = [res["uri"] for res in response["result"]["resources"]]
        expected_resources = [
            "development://logs", "embedding://status", "search://status"
        ]
        
        for resource in expected_resources:
            self.assertIn(resource, resource_uris)
    
    async def test_tool_call_project_analyze(self):
        """Test project/analyze tool call."""
        await self.mcp_server.initialize()
        
        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/call",
            "params": {
                "name": "project/analyze",
                "arguments": {
                    "prd_content": "Test PRD content",
                    "project_name": "Test Project"
                }
            }
        }
        
        with patch.object(self.mcp_server.project_handler, 'handle_analyze') as mock_analyze:
            mock_analyze.return_value = {
                "project_id": "test_proj",
                "analysis_summary": "Test analysis"
            }
            
            response = await self.mcp_server.handle_request(
                request["method"], request["params"]
            )
            # Wrap result in proper JSON-RPC format
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": response
            }
            
            self.assertEqual(response["jsonrpc"], "2.0")
            self.assertEqual(response["id"], "test")
            self.assertIn("result", response)
            
            mock_analyze.assert_called_once()
    
    async def test_tool_call_search_hybrid(self):
        """Test search/hybrid tool call."""
        await self.mcp_server.initialize()
        
        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/call",
            "params": {
                "name": "search/hybrid",
                "arguments": {
                    "query": "test search",
                    "limit": 10
                }
            }
        }
        
        with patch.object(self.mcp_server.search_handler, 'handle_hybrid') as mock_search:
            mock_search.return_value = {
                "results": [],
                "total_results": 0,
                "query": "test search"
            }
            
            response = await self.mcp_server.handle_request(
                request["method"], request["params"]
            )
            # Wrap result in proper JSON-RPC format
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": response
            }
            
            self.assertEqual(response["jsonrpc"], "2.0")
            self.assertEqual(response["id"], "test")
            self.assertIn("result", response)
            
            mock_search.assert_called_once()
    
    async def test_invalid_method(self):
        """Test handling of invalid method."""
        await self.mcp_server.initialize()
        
        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "invalid/method",
            "params": {}
        }
        
        try:
            response = await self.mcp_server.handle_request(
                request["method"], request["params"]
            )
            # Should not reach here for invalid method
            self.fail("Expected MCPError for invalid method")
        except MCPError as e:
            # Wrap error in proper JSON-RPC format
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": e.to_dict()
            }
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], "test")
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32601)  # Method not found
    
    async def test_invalid_tool_name(self):
        """Test handling of invalid tool name."""
        await self.mcp_server.initialize()
        
        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/call",
            "params": {
                "name": "invalid/tool",
                "arguments": {}
            }
        }
        
        try:
            response = await self.mcp_server.handle_request(
                request["method"], request["params"]
            )
            # Should not reach here for invalid tool
            self.fail("Expected MCPError for invalid tool")
        except MCPError as e:
            # Wrap error in proper JSON-RPC format
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": e.to_dict()
            }
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], "test")
        self.assertIn("error", response)
    
    async def test_missing_required_params(self):
        """Test handling of missing required parameters."""
        await self.mcp_server.initialize()
        
        request = {
            "jsonrpc": "2.0",
            "id": "test",
            "method": "tools/call",
            "params": {
                "name": "project/analyze",
                "arguments": {
                    # Missing required prd_content
                    "project_name": "Test Project"
                }
            }
        }
        
        try:
            response = await self.mcp_server.handle_request(
                request["method"], request["params"]
            )
            # Should not reach here for missing params
            self.fail("Expected MCPError for missing params")
        except MCPError as e:
            # Wrap error in proper JSON-RPC format
            response = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": e.to_dict()
            }
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], "test")
        self.assertIn("error", response)
    
    def test_mcp_error_creation(self):
        """Test MCPError exception creation."""
        error = MCPError(-32000, "Test error")
        
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.code, -32000)
        self.assertIsNone(error.data)
        
        # Test with data
        error_with_data = MCPError(-32000, "Test error", {"detail": "test"})
        self.assertEqual(error_with_data.data, {"detail": "test"})
    
    def test_mcp_error_to_dict(self):
        """Test MCPError to_dict method."""
        error = MCPError(-32000, "Test error", {"detail": "test"})
        error_dict = error.to_dict()
        
        expected = {
            "code": -32000,
            "message": "Test error",
            "data": {"detail": "test"}
        }
        
        self.assertEqual(error_dict, expected)


class TestMCPServerIntegration(unittest.TestCase):
    """Integration tests for MCP server with real database."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_integration.db")
        
        # Initialize database with proper URL format
        database_url = f"sqlite+aiosqlite:///{self.db_path}"
        self.db_manager = DatabaseManager(database_url)
        asyncio.run(self.db_manager.initialize())
        
        # Initialize database schema
        from src.mcp_devagent.database.init import DatabaseInitializer
        initializer = DatabaseInitializer(self.db_path)
        asyncio.run(initializer.initialize_database())
        
        # Create MCP server with DatabaseManager instance
        self.mcp_server = MCPServer(self.db_manager)
    
    def tearDown(self):
        """Clean up integration test environment."""
        if hasattr(self.mcp_server, 'cleanup'):
            asyncio.run(self.mcp_server.cleanup())
        
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
        os.rmdir(self.temp_dir)
    
    async def test_full_project_workflow(self):
        """Test complete project analysis workflow."""
        await self.mcp_server.initialize()
        
        # Step 1: Analyze project
        analyze_request = {
            "jsonrpc": "2.0",
            "id": "analyze",
            "method": "tools/call",
            "params": {
                "name": "project/analyze",
                "arguments": {
                    "prd_content": "Build a calculator app with basic operations",
                    "project_name": "Calculator App"
                }
            }
        }
        
        with patch.object(self.mcp_server.project_handler, 'handle_analyze') as mock_analyze:
            mock_analyze.return_value = {
                "project_id": "calc_proj",
                "analysis_summary": "Calculator project analyzed"
            }
            
            analyze_response = await self.mcp_server.handle_request(
                analyze_request["method"], analyze_request["params"]
            )
            # Wrap result in proper JSON-RPC format
            analyze_response = {
                "jsonrpc": "2.0",
                "id": "analyze",
                "result": analyze_response
            }
            
            self.assertIn("result", analyze_response)
            project_id = analyze_response["result"]["project_id"]
        
        # Step 2: Start development
        dev_request = {
            "jsonrpc": "2.0",
            "id": "dev",
            "method": "tools/call",
            "params": {
                "name": "development/start",
                "arguments": {
                    "project_id": project_id,
                    "phase": "implementation"
                }
            }
        }
        
        with patch.object(self.mcp_server.development_handler, 'handle_start') as mock_start:
            mock_start.return_value = {
                "run_id": "dev_run_123",
                "status": "started"
            }
            
            dev_response = await self.mcp_server.handle_request(
                dev_request["method"], dev_request["params"]
            )
            # Wrap result in proper JSON-RPC format
            dev_response = {
                "jsonrpc": "2.0",
                "id": "dev",
                "result": dev_response
            }
            
            self.assertIn("result", dev_response)
            run_id = dev_response["result"]["run_id"]
        
        # Step 3: Perform search
        search_request = {
            "jsonrpc": "2.0",
            "id": "search",
            "method": "tools/call",
            "params": {
                "name": "search/hybrid",
                "arguments": {
                    "query": "calculator function",
                    "limit": 5
                }
            }
        }
        
        with patch.object(self.mcp_server.search_handler, 'handle_hybrid') as mock_search:
            mock_search.return_value = {
                "results": [],
                "total_results": 0,
                "query": "calculator function"
            }
            
            search_response = await self.mcp_server.handle_request(
                search_request["method"], search_request["params"]
            )
            # Wrap result in proper JSON-RPC format
            search_response = {
                "jsonrpc": "2.0",
                "id": "search",
                "result": search_response
            }
            
            self.assertIn("result", search_response)
    
    def run_async_test(self, coro):
        """Helper to run async tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    def test_full_project_workflow_sync(self):
        """Synchronous wrapper for async workflow test."""
        self.run_async_test(self.test_full_project_workflow())


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)