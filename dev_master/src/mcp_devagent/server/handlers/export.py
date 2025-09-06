"""Export Handler for MCP Protocol

Handles project export operations through MCP protocol.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseHandler
from ...services.export_service import ProjectExportService


class ExportHandler(BaseHandler):
    """Handler for export-related MCP operations."""
    
    def __init__(self, db_manager, export_service: ProjectExportService):
        super().__init__(db_manager)
        self.export_service = export_service
    
    async def _initialize_impl(self):
        """Initialize export handler."""
        # Verify database tables exist
        async with self.db_manager.get_raw_connection() as conn:
            # Check if required tables exist
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('code_repositories', 'agent_sessions')"
            )
            tables = [row[0] for row in await cursor.fetchall()]
            
            if 'code_repositories' not in tables or 'agent_sessions' not in tables:
                raise RuntimeError("Required database tables not found")
    
    async def handle_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Export project with specified format and options.
        
        Args:
            params: {
                "project_path": str,  # Path to project directory
                "export_format": str,  # Export format: 'zip', 'tar.gz', 'folder'
                "output_path": str,  # Optional output path
                "include_metadata": bool,  # Include project metadata
                "include_docs": bool,  # Include documentation
                "include_tests": bool,  # Include test files
                "exclude_patterns": List[str],  # Patterns to exclude
            }
        
        Returns:
            {
                "status": "success",
                "data": {
                    "export_id": str,
                    "export_path": str,
                    "export_size": int,
                    "exported_files": int,
                    "metadata": dict
                }
            }
        """
        self._validate_params(params, ["project_path", "export_format"])
        
        project_path = params["project_path"]
        export_format = params["export_format"]
        output_path = self._get_param(params, "output_path")
        include_metadata = self._get_param(params, "include_metadata", True)
        include_docs = self._get_param(params, "include_docs", True)
        include_tests = self._get_param(params, "include_tests", True)
        exclude_patterns = self._get_param(params, "exclude_patterns", [])
        
        return await self._execute_with_error_handling(
            "project_export",
            self._export_project,
            project_path,
            export_format,
            output_path,
            include_metadata,
            include_docs,
            include_tests,
            exclude_patterns
        )
    
    async def handle_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get export operation status.
        
        Args:
            params: {
                "export_id": str  # Export operation ID
            }
        
        Returns:
            {
                "status": "success",
                "data": {
                    "export_id": str,
                    "status": str,
                    "progress": float,
                    "message": str
                }
            }
        """
        self._validate_params(params, ["export_id"])
        
        export_id = params["export_id"]
        
        return await self._execute_with_error_handling(
            "export_status",
            self._get_export_status,
            export_id
        )
    
    async def handle_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available export formats and options.
        
        Returns:
            {
                "status": "success",
                "data": {
                    "formats": List[str],
                    "options": dict
                }
            }
        """
        return await self._execute_with_error_handling(
            "export_list",
            self._list_export_options
        )
    
    async def _export_project(
        self,
        project_path: str,
        export_format: str,
        output_path: Optional[str],
        include_metadata: bool,
        include_docs: bool,
        include_tests: bool,
        exclude_patterns: List[str]
    ) -> Dict[str, Any]:
        """Export project with specified options."""
        export_id = str(uuid.uuid4())
        
        # Validate export format
        if export_format not in ['zip', 'tar.gz', 'folder']:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        # Prepare export options
        export_options = {
            'include_metadata': include_metadata,
            'include_docs': include_docs,
            'include_tests': include_tests,
            'exclude_patterns': exclude_patterns
        }
        
        # Perform export
        export_result = await self.export_service.export_project(
            project_path=project_path,
            export_format=export_format,
            output_path=output_path,
            **export_options
        )
        
        # Store export record
        await self._store_export_record(
            export_id,
            project_path,
            export_format,
            export_result['export_path'],
            export_options,
            export_result
        )
        
        return self._format_response({
            "export_id": export_id,
            "export_path": export_result['export_path'],
            "export_size": export_result['export_size'],
            "exported_files": export_result['exported_files'],
            "metadata": export_result.get('metadata', {})
        })
    
    async def _get_export_status(self, export_id: str) -> Dict[str, Any]:
        """Get export operation status."""
        async with self.db_manager.get_raw_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM agent_sessions WHERE session_id = ?",
                (export_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                raise ValueError(f"Export operation not found: {export_id}")
            
            # Parse session data
            session_data = json.loads(row[6])  # session_data column
            
            return self._format_response({
                "export_id": export_id,
                "status": session_data.get('status', 'unknown'),
                "progress": session_data.get('progress', 0.0),
                "message": session_data.get('message', '')
            })
    
    async def _list_export_options(self) -> Dict[str, Any]:
        """List available export formats and options."""
        formats = ['zip', 'tar.gz', 'folder']
        options = {
            'include_metadata': {
                'type': 'boolean',
                'default': True,
                'description': 'Include project metadata in export'
            },
            'include_docs': {
                'type': 'boolean',
                'default': True,
                'description': 'Include documentation files'
            },
            'include_tests': {
                'type': 'boolean',
                'default': True,
                'description': 'Include test files'
            },
            'exclude_patterns': {
                'type': 'array',
                'items': {'type': 'string'},
                'default': [],
                'description': 'File patterns to exclude from export'
            }
        }
        
        return self._format_response({
            "formats": formats,
            "options": options
        })
    
    async def _store_export_record(
        self,
        export_id: str,
        project_path: str,
        export_format: str,
        export_path: str,
        export_options: Dict[str, Any],
        export_result: Dict[str, Any]
    ):
        """Store export operation record in database."""
        async with self.db_manager.get_raw_connection() as conn:
            # Store as an agent session with export metadata
            await conn.execute(
                """
                INSERT INTO agent_sessions (
                    session_id, agent_type, status, start_time,
                    end_time, session_data, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    export_id,
                    'export',
                    'completed',
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat(),
                    json.dumps({
                        'project_path': project_path,
                        'export_format': export_format,
                        'export_path': export_path,
                        'export_options': export_options,
                        'export_result': export_result,
                        'status': 'completed',
                        'progress': 1.0,
                        'message': 'Export completed successfully'
                    }),
                    datetime.utcnow().isoformat()
                )
            )
            await conn.commit()