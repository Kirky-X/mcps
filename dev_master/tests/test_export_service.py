"""Tests for ProjectExportService."""

import asyncio
import os
import tempfile
import zipfile
import tarfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.mcp_devagent.services.export_service import ProjectExportService
from src.mcp_devagent.database.connection import DatabaseManager


class TestProjectExportService:
    """Test cases for ProjectExportService."""
    
    @pytest.fixture
    async def db_manager(self):
        """Mock database manager."""
        mock_db = AsyncMock(spec=DatabaseManager)
        mock_session = AsyncMock()
        mock_db.get_session.return_value.__aenter__.return_value = mock_session
        mock_db.get_session.return_value.__aexit__.return_value = None
        return mock_db
    
    @pytest.fixture
    async def export_service(self):
        """Create export service instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            return ProjectExportService(base_export_dir=temp_dir)
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory with sample files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()
            
            # Create sample files
            (project_path / "main.py").write_text("print('Hello, World!')")
            (project_path / "README.md").write_text("# Test Project")
            (project_path / "requirements.txt").write_text("requests==2.28.0")
            
            # Create subdirectories
            src_dir = project_path / "src"
            src_dir.mkdir()
            (src_dir / "__init__.py").write_text("")
            (src_dir / "module.py").write_text("def hello(): return 'Hello'")
            
            tests_dir = project_path / "tests"
            tests_dir.mkdir()
            (tests_dir / "test_module.py").write_text("def test_hello(): assert True")
            
            docs_dir = project_path / "docs"
            docs_dir.mkdir()
            (docs_dir / "api.md").write_text("# API Documentation")
            
            yield str(project_path)
    
    @pytest.mark.asyncio
    async def test_export_project_zip_format(self, export_service):
        """Test project export in ZIP format."""
        run_id = 1
        
        # Mock database data
        with patch('src.mcp_devagent.database.connection.get_db_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock database responses
            mock_cursor.fetchone.side_effect = [
                # For _get_run_data_sync call (6 fields only)
                (1, datetime(2024, 1, 1, 10, 0), datetime(2024, 1, 1, 12, 0), 
                 "Test PRD", "Python/FastAPI", "COMPLETED"),
                # For _get_performance_metrics call
                (1, 120.5, 95.0, 15, 2, 0.8)
            ]
            
            # Mock fetchall calls for different methods in order:
            # 1. _export_project_structure: (path, is_directory, size, created_at, modified_at)
            # 2. _export_code_files: (file_path, content, file_type, created_at)
            # 3. _export_test_files first query: (file_path, content)
            # 4. _export_test_files second query: (module_id, test_status, test_output, execution_time)
            # 5. _export_documentation: (name, description, content)
            # 6. _get_modules_metadata: (module_id, module_name, file_path, description, development_order, status, created_at)
            # 7. _get_thought_process: (node_name, thought_process, selected_model, module_id, timestamp)
            # 8. _get_performance_metrics first query: (status, count)
            # 9. _get_performance_metrics second query: (status, count)
            mock_cursor.fetchall.side_effect = [
                # Project structure data
                [
                    ("/src/main.py", False, 1024, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
                    ("/tests/", True, 0, "2024-01-01T00:00:00", "2024-01-01T00:00:00")
                ],
                # Code files data
                [
                    ("/src/main.py", "print('Hello, World!')", "implementation", "2024-01-01T00:00:00")
                ],
                # Test files data (first query: file_path, content)
                [
                    ("/tests/test_main.py", "def test_main(): pass")
                ],
                # Test results data (second query: module_id, status, error_message, execution_time)
                [
                    (1, "PASSED", None, 0.5)
                ],
                # Documentation modules data
                [
                    ("main", "Main module", "print('Hello, World!')")
                ],
                # Modules metadata
                [
                    (1, "main", "/src/main.py", "Main module", 1, "completed", "2024-01-01T00:00:00")
                ],
                # Thought process records
                [
                    ("development", "Implementing main module", "gpt-4", 1, "2024-01-01T00:00:00")
                ],
                # Performance metrics - module status counts
                [
                    ("completed", 1)
                ],
                # Performance metrics - test status counts
                [
                    ("PASSED", 1)
                ]
            ]
            
            result = await export_service.export_project(
                run_id=run_id,
                export_format="zip",
                include_metadata=True,
                include_docs=True,
                include_tests=True
            )
            
            assert result["success"] is True
            assert "export_path" in result
            assert result["run_id"] == run_id
            
            # Verify ZIP file exists
            zip_path = result["export_path"]
            assert os.path.exists(zip_path)
            assert zip_path.endswith(".zip")
    
    @pytest.mark.asyncio
    async def test_export_project_tar_gz_format(self, export_service):
        """Test project export in TAR.GZ format."""
        run_id = 2
        
        # Mock database data
        with patch('src.mcp_devagent.database.connection.get_db_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock database responses
            mock_cursor.fetchone.side_effect = [
                # For _get_run_data_sync call (6 fields only)
                (run_id, datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 1, 1, 0), 
                 "Test PRD", "Python", "completed"),
                # For _get_performance_metrics call
                (1, 120.5, 95.0, 15, 2, 0.8)
            ]
            
            # Mock fetchall calls for different methods in order:
            # 1. _export_project_structure: (path, is_directory, size, created_at, modified_at)
            # 2. _export_code_files: (file_path, content, file_type, created_at)
            # 3. _export_test_files first query: (file_path, content)
            # 4. _export_test_files second query: (module_id, test_status, test_output, execution_time)
            # 5. _export_documentation: (name, description, content)
            # 6. _get_modules_metadata: (module_id, module_name, file_path, description, development_order, status, created_at)
            # 7. _get_thought_process: (node_name, thought_process, selected_model, module_id, timestamp)
            # 8. _get_performance_metrics first query: (status, count)
            # 9. _get_performance_metrics second query: (status, count)
            mock_cursor.fetchall.side_effect = [
                # Project structure data
                [
                    ("/src/main.py", False, 1024, "2024-01-01T00:00:00", "2024-01-01T00:00:00"),
                    ("/tests/", True, 0, "2024-01-01T00:00:00", "2024-01-01T00:00:00")
                ],
                # Code files data
                [
                    ("/src/main.py", "print('Hello, World!')", "implementation", "2024-01-01T00:00:00")
                ],
                # Test files data (first query: file_path, content)
                [
                    ("/tests/test_main.py", "def test_main(): pass")
                ],
                # Test results data (second query: module_id, test_status, test_output, execution_time)
                [
                    (1, "PASSED", "All tests passed", 0.5)
                ],
                # Documentation modules data
                [
                    ("main", "Main module", "print('Hello, World!')")
                ],
                # Modules metadata
                [
                    (1, "main", "/src/main.py", "Main module", 1, "completed", "2024-01-01T00:00:00")
                ],
                # Thought process records
                [
                    ("development", "Implementing main module", "gpt-4", 1, "2024-01-01T00:00:00")
                ],
                # Performance metrics - module status counts
                [
                    ("completed", 1)
                ],
                # Performance metrics - test status counts
                [
                    ("PASSED", 1)
                ]
            ]
            
            result = await export_service.export_project(
                run_id=run_id,
                export_format="tar.gz",
                include_metadata=True
            )
            
            assert result["success"] is True
            assert "export_path" in result
            assert result["run_id"] == run_id
            
            # Verify TAR.GZ file exists
            tar_path = result["export_path"]
            assert os.path.exists(tar_path)
            assert tar_path.endswith(".tar.gz")
    
    @pytest.mark.asyncio
    async def test_export_with_exclude_patterns(self, export_service):
        """Test project export functionality."""
        run_id = 3
        
        # Mock database data
        with patch('src.mcp_devagent.services.export_service.get_db_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock fetchone calls:
            # 1. _get_run_data_sync: (run_id, start_time, end_time, initial_prd, tech_stack, final_status)
            # 2. _export_documentation -> _get_run_data_sync: (run_id, start_time, end_time, initial_prd, tech_stack, final_status)
            # 3. _get_performance_metrics: (start_time, end_time)
            mock_cursor.fetchone.side_effect = [
                # Run data (first call)
                (
                    run_id, "2024-01-01T00:00:00", "2024-01-01T01:00:00",
                    "Test PRD", "Python", "completed"
                ),
                # Run data (second call from _export_documentation)
                (
                    run_id, "2024-01-01T00:00:00", "2024-01-01T01:00:00",
                    "Test PRD", "Python", "completed"
                ),
                # Performance metrics timing data
                ("2024-01-01T00:00:00", "2024-01-01T01:00:00")
            ]
            
            # Mock fetchall calls for different methods in order:
            # 1. _export_project_structure: (file_path, artifact_type, created_at)
            # 2. _export_code_files: (file_path, content, file_type, created_at)
            # 3. _export_test_files first query: (file_path, content)
            # 4. _export_test_files second query: (module_id, status, error_message, execution_time)
            # 5. _export_documentation: (module_name, description, content)
            # 6. _get_modules_metadata: (module_id, module_name, file_path, description, development_order, status, created_at)
            # 7. _get_thought_process: (node_name, thought_process, selected_model, module_id, timestamp)
            # 8. _get_performance_metrics first query: (status, count)
            # 9. _get_performance_metrics second query: (status, count)
            mock_cursor.fetchall.side_effect = [
                # Project structure data
                [
                    ("/src/main.py", "implementation", "2024-01-01T00:00:00"),
                    ("/tests/test_main.py", "test", "2024-01-01T00:00:00")
                ],
                # Code files data
                [
                    ("/src/main.py", "print('Hello, World!')", "implementation", "2024-01-01T00:00:00")
                ],
                # Test files data (first query: file_path, content)
                [
                    ("/tests/test_main.py", "def test_main(): pass")
                ],
                # Test results data (second query: module_id, test_status, test_output, execution_time)
                [
                    (1, "PASSED", "All tests passed", 0.5)
                ],
                # Documentation modules data
                [
                    ("main", "Main module", "print('Hello, World!')")
                ],
                # Modules metadata
                [
                    (1, "main", "/src/main.py", "Main module", 1, "completed", "2024-01-01T00:00:00")
                ],
                # Thought process records
                [
                    ("development", "Implementing main module", "gpt-4", 1, "2024-01-01T00:00:00")
                ],
                # Performance metrics - module status counts
                [
                    ("completed", 1)
                ],
                # Performance metrics - test status counts
                [
                    ("PASSED", 1)
                ]
            ]
            
            result = await export_service.export_project(
                run_id=run_id,
                export_format="zip"
            )
            
            assert result["success"] is True
            assert "export_path" in result
            assert result["run_id"] == run_id
    
    @pytest.mark.asyncio
    async def test_export_without_optional_components(self, export_service):
        """Test project export without optional components."""
        run_id = 4
        
        # Mock database data
        with patch('src.mcp_devagent.services.export_service.get_db_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock run data (6 fields only)
            mock_cursor.fetchone.return_value = (
                run_id, datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 1, 1, 0),
                "Test PRD", "Python", "completed"
            )
            
            # Mock fetchall calls for different methods in order:
            # 1. _export_project_structure: (file_path, artifact_type, created_at)
            # 2. _export_code_files: (file_path, content, artifact_type, created_at)
            mock_cursor.fetchall.side_effect = [
                # Project structure data
                [
                    ("/src/main.py", "implementation", "2024-01-01T00:00:00"),
                    ("/tests/test_main.py", "test", "2024-01-01T00:00:00")
                ],
                # Code files data
                [
                    ("/src/main.py", "print('Hello, World!')", "implementation", "2024-01-01T00:00:00")
                ]
            ]
            
            result = await export_service.export_project(
                run_id=run_id,
                export_format="zip",
                include_metadata=False,
                include_tests=False,
                include_docs=False
            )
            
            assert result["success"] is True
            assert "export_path" in result
            assert result["run_id"] == run_id
    
    @pytest.mark.asyncio
    async def test_get_export_status(self, export_service):
        """Test getting export status."""
        export_id = "test-export-123"
        
        # Mock database data
        with patch('src.mcp_devagent.services.export_service.get_db_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock export record
            mock_cursor.fetchone.return_value = (
                export_id, 1, "completed", "/tmp/exports/project.zip",
                "2024-01-01T00:00:00", 1024
            )
            
            result = await export_service.get_export_status(export_id)
            
            assert result["success"] is True
            assert result["export_id"] == export_id
            assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_list_export_options(self, export_service):
        """Test listing available export options."""
        result = await export_service.list_export_options()
        
        assert result["success"] is True
        assert "formats" in result
        assert "zip" in result["formats"]
        assert "tar.gz" in result["formats"]
        assert "options" in result
        assert "include_metadata" in result["options"]
        assert "include_tests" in result["options"]
        assert "include_docs" in result["options"]
    
    @pytest.mark.asyncio
    async def test_export_nonexistent_project(self, export_service):
        """Test export with nonexistent run ID."""
        result = await export_service.export_project(
            run_id=99999,  # Non-existent run ID
            export_format="zip"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_export_invalid_format(self, export_service):
        """Test export with invalid format."""
        run_id = 1
        
        # Mock database data
        with patch('src.mcp_devagent.services.export_service.get_db_connection') as mock_get_conn:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock run data
            mock_cursor.fetchone.return_value = (
                run_id, "2024-01-01T00:00:00", "2024-01-01T01:00:00",
                "Test PRD", "Python", "completed", 
                '{"structure": "test"}', '{"deliverables": "test"}'
            )
            
            result = await export_service.export_project(
                run_id=run_id,
                export_format="invalid_format"
            )
            
            assert result["success"] is False
            assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__])