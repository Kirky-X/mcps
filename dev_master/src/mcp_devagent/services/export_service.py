"""Project Export Service

Provides comprehensive project export functionality including code packaging,
project structure generation, and metadata export with multiple format support.
"""

import asyncio
import json
import logging
import os
import shutil
import tarfile
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..database.connection import get_db_connection
from ..database.models import DevelopmentRun, Module, CodeFile, TestResult


class ProjectExportService:
    """Service for exporting development projects with comprehensive metadata."""
    
    def __init__(self, base_export_dir: Optional[str] = None):
        """Initialize the export service.
        
        Args:
            base_export_dir: Base directory for exports. Defaults to ./exports
        """
        self.base_export_dir = Path(base_export_dir or "./exports")
        self.base_export_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    async def export_project(self, run_id: int, export_format: str = "zip",
                           include_metadata: bool = True,
                           include_tests: bool = True,
                           include_docs: bool = True) -> Dict[str, Any]:
        """Export a complete development project.
        
        Args:
            run_id: Development run ID to export
            export_format: Export format ('zip', 'tar.gz', 'directory')
            include_metadata: Whether to include project metadata
            include_tests: Whether to include test files
            include_docs: Whether to include documentation
            
        Returns:
            Export result with file path and metadata
        """
        try:
            # Get development run data
            self.logger.info(f"Getting run data for run_id: {run_id}")
            run_data = await self._get_run_data(run_id)
            if not run_data:
                raise ValueError(f"Development run {run_id} not found")
            
            # Create temporary directory for export preparation
            with tempfile.TemporaryDirectory() as temp_dir:
                export_dir = Path(temp_dir) / f"project_{run_id}"
                export_dir.mkdir()
                
                # Export project structure
                try:
                    self.logger.info("Exporting project structure")
                    await self._export_project_structure(run_id, export_dir)
                    self.logger.info("Project structure export completed")
                except Exception as e:
                    self.logger.error(f"Error in _export_project_structure: {e}")
                    raise
                
                # Export code files
                try:
                    self.logger.info("Exporting code files")
                    await self._export_code_files(run_id, export_dir)
                    self.logger.info("Code files export completed")
                except Exception as e:
                    self.logger.error(f"Error in _export_code_files: {e}")
                    raise
                
                # Export tests if requested
                if include_tests:
                    try:
                        self.logger.info("Exporting test files")
                        await self._export_test_files(run_id, export_dir)
                        self.logger.info("Test files export completed")
                    except Exception as e:
                        self.logger.error(f"Error in _export_test_files: {e}")
                        raise
                
                # Export documentation if requested
                if include_docs:
                    try:
                        self.logger.info("Exporting documentation")
                        await self._export_documentation(run_id, export_dir)
                        self.logger.info("Documentation export completed")
                    except Exception as e:
                        self.logger.error(f"Error in _export_documentation: {e}")
                        raise
                
                # Export metadata if requested
                if include_metadata:
                    try:
                        self.logger.info("Exporting metadata")
                        await self._export_metadata(run_id, export_dir, run_data)
                        self.logger.info("Metadata export completed")
                    except Exception as e:
                        self.logger.error(f"Error in _export_metadata: {e}")
                        raise
                
                # Create final export package
                self.logger.info(f"Creating export package in format: {export_format}")
                export_path = self._create_export_package(
                    export_dir, run_id, export_format
                )
                
                return {
                    "success": True,
                    "export_path": str(export_path),
                    "export_format": export_format,
                    "run_id": run_id,
                    "exported_at": datetime.now().isoformat(),
                    "file_size": export_path.stat().st_size,
                    "includes": {
                        "metadata": include_metadata,
                        "tests": include_tests,
                        "docs": include_docs
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to export project {run_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "run_id": run_id
            }
    
    async def _get_run_data(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get development run data from database."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            self.logger.info(f"Executing query for run_id: {run_id}")
            cursor.execute("""
                SELECT run_id, start_time, end_time, initial_prd, tech_stack, final_status
                FROM development_runs
                WHERE run_id = ?
            """, (run_id,))
            
            row = cursor.fetchone()
            self.logger.info(f"Query result: {row}")
            
            if not row:
                self.logger.warning(f"No data found for run_id: {run_id}")
                return None
            
            result = {
                "run_id": row[0],
                "start_time": row[1],
                "end_time": row[2],
                "initial_prd": row[3],
                "tech_stack": row[4],
                "final_status": row[5],
                "project_structure": {},  # Will be populated from other sources
                "final_deliverables": {}  # Will be populated from other sources
            }
            self.logger.info(f"Returning run data: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error in _get_run_data: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _get_run_data_sync(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get development run data from database (synchronous version)."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            self.logger.info(f"Executing query for run_id: {run_id}")
            cursor.execute("""
                SELECT run_id, start_time, end_time, initial_prd, tech_stack, final_status
                FROM development_runs
                WHERE run_id = ?
            """, (run_id,))
            
            row = cursor.fetchone()
            self.logger.info(f"Query result: {row}")
            
            if not row:
                self.logger.warning(f"No data found for run_id: {run_id}")
                return None
            
            result = {
                "run_id": row[0],
                "start_time": row[1],
                "end_time": row[2],
                "initial_prd": row[3],
                "tech_stack": row[4],
                "final_status": row[5],
                "project_structure": {},  # Will be populated from other sources
                "final_deliverables": {}  # Will be populated from other sources
            }
            self.logger.info(f"Returning run data: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Error in _get_run_data_sync: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()
    
    async def _export_project_structure(self, run_id: int, export_dir: Path):
        """Export project structure to files."""
        try:
            self.logger.info(f"Starting _export_project_structure for run_id: {run_id}")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Create directory structure
            structure_dir = export_dir / "project_structure"
            structure_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created structure directory: {structure_dir}")
            
            # Since project_structure table doesn't exist, use code_artifacts table instead
            self.logger.info("Executing project structure query from code_artifacts")
            cursor.execute("""
                SELECT file_path, artifact_type, created_at
                FROM code_artifacts
                WHERE run_id = ?
                ORDER BY file_path
            """, (run_id,))
            
            # Fix for StopIteration in async context
            rows_result = cursor.fetchall()
            rows = list(rows_result) if rows_result else []
            self.logger.info(f"Found {len(rows)} structure entries")
            
            structure_data = []
            for row in rows:
                structure_data.append({
                    "path": row[0],
                    "is_directory": False,  # All artifacts are files
                    "type": row[1],
                    "created_at": row[2],
                    "size": None  # Not available in code_artifacts
                })
            
            # Write structure data
            structure_file = structure_dir / "directory_structure.json"
            with open(structure_file, 'w', encoding='utf-8') as f:
                json.dump(structure_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Successfully exported project structure to {structure_file}")
                
        except Exception as e:
            self.logger.error(f"Error in _export_project_structure: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()
    
    async def _export_code_files(self, run_id: int, export_dir: Path):
        """Export generated code files."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT file_path, content, artifact_type, created_at
                FROM code_artifacts
                WHERE run_id = ? AND content IS NOT NULL
                ORDER BY created_at
            """, (run_id,))
            
            # Fix for StopIteration in async context
            code_files_result = cursor.fetchall()
            code_files = list(code_files_result) if code_files_result else []
            
            for file_data in code_files:
                file_path, content, artifact_type, created_at = file_data
                
                if file_path and content:
                    full_path = export_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write file content
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.logger.info(f"Exported code file: {file_path}")
        finally:
            conn.close()
    
    async def _export_test_files(self, run_id: int, export_dir: Path):
        """Export test files and results."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Export test files
            cursor.execute("""
                SELECT file_path, content
                FROM code_artifacts
                WHERE run_id = ? AND artifact_type = 'test' AND content IS NOT NULL
            """, (run_id,))
            
            # Fix for StopIteration in async context
            test_files_result = cursor.fetchall()
            test_files = list(test_files_result) if test_files_result else []
            
            for file_path, content in test_files:
                if file_path and content:
                    full_path = export_dir / file_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(content)
            
            # Export test results summary
            cursor.execute("""
                SELECT tr.module_id, tr.status, tr.error_details, tr.execution_time
                FROM test_results tr
                JOIN modules m ON tr.module_id = m.module_id
                WHERE m.run_id = ?
                ORDER BY tr.execution_time DESC
            """, (run_id,))
            
            # Fix for StopIteration in async context
            test_results_raw = cursor.fetchall()
            test_results = list(test_results_raw) if test_results_raw else []
            
            if test_results:
                test_summary = {
                    "total_tests": len(test_results),
                    "passed": sum(1 for r in test_results if r[1] == 'PASSED'),
                    "failed": sum(1 for r in test_results if r[1] == 'FAILED'),
                    "results": [
                        {
                            "module_id": r[0],
                            "status": r[1],
                            "error_details": r[2],
                            "execution_time": r[3]
                        } for r in test_results
                    ]
                }
                
                test_summary_path = export_dir / "test_results.json"
                with open(test_summary_path, 'w', encoding='utf-8') as f:
                    json.dump(test_summary, f, indent=2, ensure_ascii=False)
        finally:
            conn.close()
    
    async def _export_documentation(self, run_id: int, export_dir: Path):
        """Export project documentation."""
        docs_dir = export_dir / "docs"
        docs_dir.mkdir(exist_ok=True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get run data for README generation
            self.logger.info("Getting run data for documentation")
            run_data = self._get_run_data_sync(run_id)
            self.logger.info(f"Got run data: {run_data}")
            
            if run_data is None:
                self.logger.warning("No run data found, using default values")
                run_data = {
                    'run_id': run_id,
                    'final_status': 'Unknown',
                    'tech_stack': 'Not specified',
                    'initial_prd': 'No description available.',
                    'start_time': 'N/A',
                    'end_time': 'N/A'
                }
            
            # Generate README.md
            self.logger.info("Generating README content")
            readme_content = self._generate_readme(run_data)
            self.logger.info("Writing README file")
            with open(docs_dir / "README.md", 'w', encoding='utf-8') as f:
                f.write(readme_content)
            self.logger.info("README file written successfully")
            
            # Generate API documentation if available
            self.logger.info("Querying modules for API documentation")
            cursor.execute("""
                SELECT m.module_name, m.description, ca.content
                FROM modules m
                LEFT JOIN code_artifacts ca ON m.module_id = ca.module_id
                WHERE m.run_id = ? AND ca.artifact_type = 'implementation'
                ORDER BY m.development_order
            """, (run_id,))
            
            # Fix for StopIteration in async context
            modules_result = cursor.fetchall()
            modules = list(modules_result) if modules_result else []
            self.logger.info(f"Found {len(modules)} modules for API documentation")
            
            if modules:
                self.logger.info("Generating API documentation")
                self.logger.info(f"Modules data type: {type(modules)}")
                self.logger.info(f"First module sample: {modules[0] if modules else 'None'}")
                try:
                    api_doc = self._generate_api_documentation(modules)
                    self.logger.info("API documentation generated successfully")
                    self.logger.info("Writing API documentation file")
                    with open(docs_dir / "API.md", 'w', encoding='utf-8') as f:
                        f.write(api_doc)
                    self.logger.info("API documentation written successfully")
                except Exception as e:
                    self.logger.error(f"Error generating API documentation: {e}")
                    import traceback
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    raise
            else:
                self.logger.info("No modules found, skipping API documentation")
        finally:
            conn.close()
    
    async def _export_metadata(self, run_id: int, export_dir: Path, run_data: Dict[str, Any]):
        """Export comprehensive project metadata."""
        metadata = {
            "project_info": {
                "run_id": run_id,
                "generated_at": datetime.now().isoformat(),
                "mcp_devagent_version": "1.0.0",
                "export_format_version": "1.0"
            },
            "development_run": run_data,
            "modules": await self._get_modules_metadata(run_id),
            "thought_process": await self._get_thought_process(run_id),
            "performance_metrics": await self._get_performance_metrics(run_id)
        }
        
        metadata_path = export_dir / "project_metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    async def _get_modules_metadata(self, run_id: int) -> List[Dict[str, Any]]:
        """Get modules metadata for export."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT module_id, module_name, file_path, description,
                       development_order, status, created_at
                FROM modules
                WHERE run_id = ?
                ORDER BY development_order
            """, (run_id,))
            
            modules = []
            # Fix for StopIteration in async context
            rows_result = cursor.fetchall()
            rows = list(rows_result) if rows_result else []
            for row in rows:
                modules.append({
                    "module_id": row[0],
                    "name": row[1],
                    "file_path": row[2],
                    "description": row[3],
                    "dependencies": [],  # Default empty dependencies
                    "development_order": row[4],
                    "status": row[5],
                    "created_at": row[6],
                    "updated_at": None  # Not available in current schema
                })
            
            return modules
        finally:
            conn.close()
    
    async def _get_thought_process(self, run_id: int) -> List[Dict[str, Any]]:
        """Get thought process records for export."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT node_name, thought_process, selected_model, module_id, timestamp
                FROM cot_records
                WHERE run_id = ?
                ORDER BY timestamp
            """, (run_id,))
            
            records = []
            # Fix for StopIteration in async context
            rows_result = cursor.fetchall()
            rows = list(rows_result) if rows_result else []
            for row in rows:
                records.append({
                    "node_name": row[0],
                    "thought_process": row[1],
                    "selected_model": row[2],
                    "module_id": row[3],
                    "timestamp": row[4]
                })
            
            return records
        finally:
            conn.close()
    
    async def _get_performance_metrics(self, run_id: int) -> Dict[str, Any]:
        """Get performance metrics for export."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get basic timing metrics
            cursor.execute("""
                SELECT start_time, end_time
                FROM development_runs
                WHERE run_id = ?
            """, (run_id,))
            
            run_timing = cursor.fetchone()
            
            # Get module count and status distribution
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM modules
                WHERE run_id = ?
                GROUP BY status
            """, (run_id,))
            
            # Fix for StopIteration in async context
            status_results_raw = cursor.fetchall()
            status_results = list(status_results_raw) if status_results_raw else []
            status_counts = dict(status_results) if status_results else {}
            
            # Get test results summary
            cursor.execute("""
                SELECT tr.status, COUNT(*) as count
                FROM test_results tr
                JOIN modules m ON tr.module_id = m.module_id
                WHERE m.run_id = ?
                GROUP BY tr.status
            """, (run_id,))
            
            # Fix for StopIteration in async context
            test_results_raw = cursor.fetchall()
            test_results = list(test_results_raw) if test_results_raw else []
            test_counts = dict(test_results) if test_results else {}
            
            return {
                "timing": {
                    "start_time": run_timing[0] if run_timing else None,
                    "end_time": run_timing[1] if run_timing else None
                },
                "modules": {
                    "total": sum(status_counts.values()) if status_counts else 0,
                    "by_status": status_counts
                },
                "tests": {
                    "total": sum(test_counts.values()) if test_counts else 0,
                    "by_status": test_counts
                }
            }
        finally:
            conn.close()
    
    def _create_export_package(self, export_dir: Path, run_id: int, 
                                   export_format: str) -> Path:
        """Create final export package in specified format."""
        # Ensure base export directory exists
        self.base_export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"mcp_devagent_project_{run_id}_{timestamp}"
        
        if export_format == "zip":
            export_path = self.base_export_dir / f"{base_name}.zip"
            with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in export_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(export_dir)
                        zipf.write(file_path, arcname)
        
        elif export_format == "tar.gz":
            export_path = self.base_export_dir / f"{base_name}.tar.gz"
            with tarfile.open(export_path, 'w:gz') as tarf:
                tarf.add(export_dir, arcname=f"project_{run_id}")
        
        elif export_format == "directory":
            export_path = self.base_export_dir / base_name
            shutil.copytree(export_dir, export_path)
        
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        return export_path
    
    def _generate_readme(self, run_data: Dict[str, Any]) -> str:
        """Generate README.md content for the exported project."""
        return f"""# MCP-DevAgent Generated Project

## Project Information

- **Run ID**: {run_data.get('run_id', 'N/A')}
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Status**: {run_data.get('final_status', 'Unknown')}
- **Tech Stack**: {run_data.get('tech_stack', 'Not specified')}

## Project Description

{run_data.get('initial_prd', 'No description available.')}

## Development Timeline

- **Started**: {run_data.get('start_time', 'N/A')}
- **Completed**: {run_data.get('end_time', 'N/A')}

## Project Structure

This project was generated using MCP-DevAgent, an AI-powered development system that follows Test-Driven Development (TDD) principles.

### Generated Files

- **Source Code**: Implementation files generated by the DevelopmentAgent
- **Tests**: Comprehensive test suites created by the TestingAgent
- **Documentation**: Auto-generated API documentation and project guides
- **Metadata**: Complete development process records and metrics

## Getting Started

1. Review the generated code in the source directories
2. Run the test suite to verify functionality
3. Check the `docs/` directory for detailed documentation
4. Review `project_metadata.json` for complete development history

## Development Process

This project was created using a four-stage AI workflow:

1. **Planning**: Requirements analysis and module decomposition
2. **Testing**: Test case generation for each module
3. **Development**: Code implementation to pass all tests
4. **Validation**: Comprehensive testing and quality assurance

For more details, see the thought process records in the metadata.

---

*Generated by MCP-DevAgent v1.0.0*
"""
    
    def _generate_api_documentation(self, modules: List[tuple]) -> str:
        """Generate API documentation from modules."""
        doc_content = "# API Documentation\n\n"
        
        for module_name, description, content in modules:
            doc_content += f"## {module_name}\n\n"
            
            if description:
                doc_content += f"{description}\n\n"
            
            # Basic function extraction (simplified)
            if content:
                lines = content.split('\n')
                functions = []
                for line in lines:
                    line = line.strip()
                    if line.startswith('def ') or line.startswith('async def '):
                        functions.append(line)
                
                if functions:
                    doc_content += "### Functions\n\n"
                    for func in functions:
                        doc_content += f"- `{func}`\n"
                    doc_content += "\n"
        
        return doc_content
    
    async def list_available_exports(self) -> List[Dict[str, Any]]:
        """List all available export files."""
        exports = []
        
        if self.base_export_dir.exists():
            for file_path in self.base_export_dir.iterdir():
                if file_path.is_file():
                    stat = file_path.stat()
                    exports.append({
                        "filename": file_path.name,
                        "path": str(file_path),
                        "size": stat.st_size,
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        return sorted(exports, key=lambda x: x['created_at'], reverse=True)
    
    async def cleanup_old_exports(self, keep_count: int = 10) -> Dict[str, Any]:
        """Clean up old export files, keeping only the most recent ones."""
        exports = await self.list_available_exports()
        
        if len(exports) <= keep_count:
            return {"cleaned": 0, "kept": len(exports)}
        
        # Sort by creation time and remove oldest
        exports_to_remove = exports[keep_count:]
        removed_count = 0
        
        for export in exports_to_remove:
            try:
                Path(export['path']).unlink()
                removed_count += 1
            except Exception as e:
                self.logger.error(f"Failed to remove export {export['filename']}: {e}")
        
        return {"cleaned": removed_count, "kept": len(exports) - removed_count}
    
    async def get_export_status(self, export_id: str) -> Dict[str, Any]:
        """Get the status of a specific export."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT export_id, run_id, status, file_path, created_at, file_size
                FROM export_records
                WHERE export_id = ?
            """, (export_id,))
            
            record = cursor.fetchone()
            if not record:
                return {
                    "success": False,
                    "error": f"Export {export_id} not found"
                }
            
            return {
                "success": True,
                "export_id": record[0],
                "run_id": record[1],
                "status": record[2],
                "file_path": record[3],
                "created_at": record[4],
                "file_size": record[5]
            }
        finally:
            conn.close()
    
    async def list_export_options(self) -> Dict[str, Any]:
        """List available export options and formats."""
        return {
            "success": True,
            "formats": ["zip", "tar.gz", "directory"],
            "options": {
                "include_metadata": {
                    "description": "Include project metadata and development history",
                    "default": True
                },
                "include_tests": {
                    "description": "Include test files and results",
                    "default": True
                },
                "include_docs": {
                    "description": "Include generated documentation",
                    "default": True
                }
            }
        }