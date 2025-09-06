"""Tests for ExportHandler."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

import pytest

from src.mcp_devagent.server.handlers.export import ExportHandler
from src.mcp_devagent.services.export_service import ProjectExportService


class TestExportHandler:
    """Test cases for ExportHandler."""
    
    @pytest.fixture
    async def mock_export_service(self):
        """Mock export service."""
        mock_service = AsyncMock(spec=ProjectExportService)
        return mock_service
    
    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        mock_db = AsyncMock()
        
        # Create a proper async context manager
        @asynccontextmanager
        async def mock_connection_context():
            mock_connection = AsyncMock()
            # Mock the cursor for table existence check
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = [('code_repositories',), ('agent_sessions',)]
            mock_connection.execute.return_value = mock_cursor
            yield mock_connection
        
        mock_db.get_raw_connection = mock_connection_context
        return mock_db
    
    @pytest.fixture
    async def export_handler(self, mock_db_manager, mock_export_service):
        """Create export handler instance."""
        handler = ExportHandler(mock_db_manager, mock_export_service)
        await handler._initialize_impl()  # Initialize the handler
        return handler
    
    @pytest.mark.asyncio
    async def test_handle_project_export_success(self, export_handler, mock_export_service):
        """Test successful project export."""
        # Mock export service response
        mock_export_service.export_project.return_value = {
            "export_path": "/tmp/project.zip",
            "export_size": 1024000,
            "exported_files": 25,
            "metadata": {"project_name": "test_project"}
        }
        
        # Test parameters
        params = {
            "project_path": "/path/to/project",
            "output_path": "/tmp/exports",
            "export_format": "zip",
            "include_metadata": True,
            "include_docs": True,
            "include_tests": True,
            "exclude_patterns": [".git", "__pycache__"]
        }
        
        result = await export_handler.handle_project(params)
        
        # Verify service was called with correct parameters
        mock_export_service.export_project.assert_called_once_with(
            project_path="/path/to/project",
            output_path="/tmp/exports",
            export_format="zip",
            include_metadata=True,
            include_docs=True,
            include_tests=True,
            exclude_patterns=[".git", "__pycache__"]
        )
        
        # Verify response
        assert result["status"] == "success"
        assert "export_id" in result["data"]
        assert result["data"]["export_path"] == "/tmp/project.zip"
        assert result["data"]["export_size"] == 1024000
    
    @pytest.mark.asyncio
    async def test_handle_project_export_with_minimal_params(self, export_handler, mock_export_service):
        """Test project export with minimal parameters."""
        mock_export_service.export_project.return_value = {
            "export_path": "/tmp/project.zip",
            "export_size": 1024,
            "exported_files": 10,
            "metadata": {}
        }
        
        params = {
            "project_path": "/path/to/project",
            "export_format": "zip"
        }
        
        result = await export_handler.handle_project(params)
        
        assert result["status"] == "success"
        assert "export_id" in result["data"]
        assert result["data"]["export_path"] == "/tmp/project.zip"
    
    @pytest.mark.asyncio
    async def test_handle_project_export_failure(self, export_handler, mock_export_service):
        """Test project export failure handling."""
        mock_export_service.export_project.side_effect = FileNotFoundError("Project path does not exist")
        
        params = {
            "project_path": "/nonexistent/path",
            "export_format": "zip"
        }
        
        with pytest.raises(FileNotFoundError, match="Project path does not exist"):
            await export_handler.handle_project(params)
    
    @pytest.mark.asyncio
    async def test_handle_status_success(self, export_handler):
        """Test successful status query."""
        # Mock the _get_export_status method to return complete response (after _format_response)
        async def mock_get_export_status(export_id):
            return {
                "status": "success",
                "data": {
                    "export_id": export_id,
                    "status": "completed",
                    "progress": 1.0,
                    "message": "Export completed"
                }
            }
        
        export_handler._get_export_status = mock_get_export_status
        
        params = {
            "export_id": "export-123"
        }
        
        result = await export_handler.handle_status(params)
        
        assert result["status"] == "success"
        assert result["data"]["export_id"] == "export-123"
        assert result["data"]["status"] == "completed"
        assert result["data"]["progress"] == 1.0
    
    @pytest.mark.asyncio
    async def test_handle_status_not_found(self, export_handler):
        """Test status query for non-existent export."""
        # Mock the _get_export_status method to raise ValueError for not found
        async def mock_get_export_status(export_id):
            raise ValueError(f"Export operation not found: {export_id}")
        
        export_handler._get_export_status = mock_get_export_status
        
        params = {
            "export_id": "non-existent"
        }
        
        with pytest.raises(ValueError, match="Export operation not found"):
            await export_handler.handle_status(params)
    
    @pytest.mark.asyncio
    async def test_handle_list_success(self, export_handler, mock_export_service):
        """Test successful list export options."""
        # The list method doesn't use export_service, it's handled internally
        
        params = {
            "project_path": "/path/to/project"
        }
        
        result = await export_handler.handle_list(params)
        
        assert result["status"] == "success"
        assert "formats" in result["data"]
        assert "zip" in result["data"]["formats"]
        assert "tar.gz" in result["data"]["formats"]
        assert "options" in result["data"]
    
    @pytest.mark.asyncio
    async def test_handle_list_with_optional_project_path(self, export_handler, mock_export_service):
        """Test list export options without project path."""
        # The list method doesn't use export_service, it's handled internally
        
        params = {}  # No project_path provided
        
        result = await export_handler.handle_list(params)
        
        assert result["status"] == "success"
        assert "formats" in result["data"]
        assert "options" in result["data"]
    
    @pytest.mark.asyncio
    async def test_missing_export_service(self, mock_db_manager):
        """Test handler behavior when export service is not available."""
        # Create handler without export service
        handler = ExportHandler(mock_db_manager, export_service=None)
        await handler.initialize()
        
        params = {
            "project_path": "/path/to/project",
            "export_format": "zip"
        }
        
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'export_project'"):
             await handler.handle_project(params)
    
    @pytest.mark.asyncio
    async def test_handle_project_missing_required_param(self, export_handler):
        """Test project export with missing required parameters."""
        params = {}  # Missing project_path and export_format
        
        with pytest.raises(ValueError, match="Missing required parameters"):
            await export_handler.handle_project(params)
    
    @pytest.mark.asyncio
    async def test_handle_status_missing_required_param(self, export_handler):
        """Test status query with missing required parameters."""
        params = {}  # Missing export_id
        
        with pytest.raises(ValueError, match="Missing required parameters"):
            await export_handler.handle_status(params)
    
    @pytest.mark.asyncio
    async def test_exception_handling(self, export_handler, mock_export_service):
        """Test general exception handling."""
        mock_export_service.export_project.side_effect = RuntimeError("Unexpected error")
        
        params = {
            "project_path": "/path/to/project",
            "export_format": "zip"
        }
        
        with pytest.raises(RuntimeError, match="Unexpected error"):
            await export_handler.handle_project(params)


if __name__ == "__main__":
    pytest.main([__file__])