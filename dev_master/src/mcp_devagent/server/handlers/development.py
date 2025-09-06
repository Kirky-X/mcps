"""Development Handler for MCP Protocol

Handles development run management and chain of thought tracking.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseHandler


class DevelopmentHandler(BaseHandler):
    """Handler for development-related MCP operations."""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.active_runs = {}  # In-memory tracking of active development runs
    
    async def _initialize_impl(self):
        """Initialize development handler."""
        # Verify database tables exist (updated for new schema)
        async with self.db_manager.get_raw_connection() as conn:
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('development_runs', 'cot_records')"
            )
            tables = [row[0] for row in await cursor.fetchall()]
            
            if 'development_runs' not in tables or 'cot_records' not in tables:
                raise RuntimeError("Required database tables not found")
        
        # Load active runs from database
        await self._load_active_runs()
    
    async def _load_active_runs(self):
        """Load active development runs from database."""
        async with self.db_manager.get_raw_connection() as conn:
            cursor = await conn.execute(
                "SELECT run_id, final_status, initial_prd, tech_stack FROM development_runs WHERE final_status = 'IN_PROGRESS'"
            )
            rows = await cursor.fetchall()
            
            for row in rows:
                run_id, status, initial_prd, tech_stack = row
                self.active_runs[run_id] = {
                    "status": status,
                    "metadata": {
                        "initial_prd": initial_prd,
                        "tech_stack": tech_stack
                    },
                    "last_updated": datetime.utcnow()
                }
        
        self.logger.info(f"Loaded {len(self.active_runs)} active development runs")
    
    async def handle_start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new development run.
        
        Args:
            params: {
                "project_blueprint": dict,  # Project development blueprint
                "tech_constraints": dict,   # Optional technology constraints
                "run_config": dict         # Optional run configuration
            }
        
        Returns:
            {
                "status": "success",
                "data": {
                    "run_id": str,
                    "status": "running",
                    "created_at": str
                }
            }
        """
        self._validate_params(params, ["project_blueprint"])
        
        project_blueprint = params["project_blueprint"]
        tech_constraints = self._get_param(params, "tech_constraints", {})
        run_config = self._get_param(params, "run_config", {})
        
        return await self._execute_with_error_handling(
            "start_development_run",
            self._start_development_run,
            project_blueprint,
            tech_constraints,
            run_config
        )
    
    async def _start_development_run(self, project_blueprint: Dict[str, Any], 
                                   tech_constraints: Dict[str, Any], 
                                   run_config: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new development run."""
        run_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        # Prepare run metadata
        metadata = {
            "project_blueprint": project_blueprint,
            "tech_constraints": tech_constraints,
            "run_config": run_config,
            "phases": project_blueprint.get("development_phases", []),
            "current_phase": 0,
            "progress": {
                "completed_tasks": 0,
                "total_tasks": len(project_blueprint.get("features", [])),
                "percentage": 0.0
            }
        }
        
        # Store in database
        async with self.db_manager.get_raw_connection() as conn:
            await conn.execute(
                """
                INSERT INTO development_runs (
                    initial_prd, tech_stack, final_status
                ) VALUES (?, ?, ?)
                """,
                (
                    json.dumps(project_blueprint),
                    json.dumps(tech_constraints),
                    "IN_PROGRESS"
                )
            )
            # Get the run_id from the inserted row
            cursor = await conn.execute("SELECT last_insert_rowid()")
            run_id = (await cursor.fetchone())[0]
            await conn.commit()
        
        # Add to active runs
        self.active_runs[run_id] = {
            "status": "running",
            "metadata": metadata,
            "last_updated": created_at
        }
        
        # Log initial CoT record
        await self._log_cot_record(
            run_id,
            "system",
            "development_start",
            "Development run started",
            {
                "project_name": project_blueprint.get("project_info", {}).get("name"),
                "phases_count": len(metadata["phases"]),
                "features_count": metadata["progress"]["total_tasks"]
            }
        )
        
        return self._format_response({
            "run_id": run_id,
            "status": "running",
            "created_at": created_at.isoformat()
        })
    
    async def handle_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get development run status.
        
        Args:
            params: {
                "run_id": str
            }
        
        Returns:
            Development run status and progress information
        """
        self._validate_params(params, ["run_id"])
        
        run_id = params["run_id"]
        
        return await self._execute_with_error_handling(
            "get_development_status",
            self._get_development_status,
            run_id
        )
    
    async def _get_development_status(self, run_id: str) -> Dict[str, Any]:
        """Get development run status and progress."""
        # Check active runs first
        if run_id in self.active_runs:
            active_run = self.active_runs[run_id]
            
            # Get latest CoT records
            recent_records = await self._get_recent_cot_records(run_id, limit=10)
            
            return self._format_response({
                "run_id": run_id,
                "status": active_run["status"],
                "metadata": active_run["metadata"],
                "last_updated": active_run["last_updated"].isoformat(),
                "recent_activity": recent_records
            })
        
        # Query database for completed/stopped runs
        async with self.db_manager.get_raw_connection() as conn:
            cursor = await conn.execute(
                "SELECT run_id, start_time, end_time, initial_prd, tech_stack, final_status FROM development_runs WHERE run_id = ?",
                (run_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                raise ValueError(f"Development run not found: {run_id}")
            
            # Convert row to dict
            run_id_db, start_time, end_time, initial_prd, tech_stack, final_status = row
            run_data = {
                "run_id": run_id_db,
                "start_time": start_time,
                "end_time": end_time,
                "status": final_status,
                "metadata": {
                    "initial_prd": json.loads(initial_prd) if initial_prd else {},
                    "tech_stack": json.loads(tech_stack) if tech_stack else {}
                }
            }
            
            # Get recent CoT records
            recent_records = await self._get_recent_cot_records(run_id, limit=10)
            run_data["recent_activity"] = recent_records
            
            return self._format_response(run_data)
    
    async def handle_update_progress(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update development run progress.
        
        Args:
            params: {
                "run_id": str,
                "progress_update": dict,  # Progress information
                "cot_record": dict       # Optional chain of thought record
            }
        
        Returns:
            Updated run status
        """
        self._validate_params(params, ["run_id", "progress_update"])
        
        run_id = params["run_id"]
        progress_update = params["progress_update"]
        cot_record = self._get_param(params, "cot_record")
        
        return await self._execute_with_error_handling(
            "update_development_progress",
            self._update_development_progress,
            run_id,
            progress_update,
            cot_record
        )
    
    async def _update_development_progress(self, run_id: str, 
                                         progress_update: Dict[str, Any],
                                         cot_record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Update development run progress."""
        if run_id not in self.active_runs:
            raise ValueError(f"Active development run not found: {run_id}")
        
        active_run = self.active_runs[run_id]
        metadata = active_run["metadata"]
        
        # Update progress
        if "completed_tasks" in progress_update:
            metadata["progress"]["completed_tasks"] = progress_update["completed_tasks"]
        
        if "current_phase" in progress_update:
            metadata["current_phase"] = progress_update["current_phase"]
        
        # Recalculate percentage
        total_tasks = metadata["progress"]["total_tasks"]
        completed_tasks = metadata["progress"]["completed_tasks"]
        metadata["progress"]["percentage"] = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Update timestamp
        updated_at = datetime.utcnow()
        active_run["last_updated"] = updated_at
        
        # Update database
        async with self.db_manager.get_raw_connection() as conn:
            await conn.execute(
                "UPDATE development_runs SET final_status = ? WHERE run_id = ?",
                ("IN_PROGRESS", run_id)
            )
            await conn.commit()
        
        # Log CoT record if provided
        if cot_record:
            await self._log_cot_record(
                run_id,
                cot_record.get("agent_type", "system"),
                cot_record.get("operation_type", "progress_update"),
                cot_record.get("reasoning", "Progress updated"),
                cot_record.get("context", progress_update)
            )
        
        return self._format_response({
            "run_id": run_id,
            "status": active_run["status"],
            "progress": metadata["progress"],
            "updated_at": updated_at.isoformat()
        })
    
    async def _log_cot_record(self, run_id: str, agent_type: str, operation_type: str, 
                            reasoning: str, context: Dict[str, Any]):
        """Log a chain of thought record."""
        created_at = datetime.utcnow()
        
        async with self.db_manager.get_raw_connection() as conn:
            await conn.execute(
                """
                INSERT INTO cot_records (
                    run_id, node_name, thought_process, input_context, output_result
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    operation_type,
                    reasoning,
                    json.dumps(context),
                    json.dumps({"agent_type": agent_type})
                )
            )
            await conn.commit()
    
    async def _get_recent_cot_records(self, run_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent chain of thought records for a run."""
        async with self.db_manager.get_raw_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT cot_id, node_name, timestamp, thought_process, input_context, output_result 
                FROM cot_records 
                WHERE run_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
                """,
                (run_id, limit)
            )
            rows = await cursor.fetchall()
            
            records = []
            for row in rows:
                cot_id, node_name, timestamp, thought_process, input_context, output_result = row
                records.append({
                    "cot_id": cot_id,
                    "node_name": node_name,
                    "timestamp": timestamp,
                    "thought_process": thought_process,
                    "input_context": input_context,
                    "output_result": output_result
                })
            
            return records
    
    async def handle_stop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Stop a development run.
        
        Args:
            params: {
                "run_id": str,
                "reason": str  # Optional reason for stopping
            }
        
        Returns:
            Final run status
        """
        self._validate_params(params, ["run_id"])
        
        run_id = params["run_id"]
        reason = self._get_param(params, "reason", "Manual stop")
        
        return await self._execute_with_error_handling(
            "stop_development_run",
            self._stop_development_run,
            run_id,
            reason
        )
    
    async def _stop_development_run(self, run_id: str, reason: str) -> Dict[str, Any]:
        """Stop a development run."""
        if run_id not in self.active_runs:
            raise ValueError(f"Active development run not found: {run_id}")
        
        # Update status
        stopped_at = datetime.utcnow()
        
        async with self.db_manager.get_raw_connection() as conn:
            await conn.execute(
                "UPDATE development_runs SET final_status = ?, end_time = ? WHERE run_id = ?",
                ("COMPLETED", stopped_at.isoformat(), run_id)
            )
            await conn.commit()
        
        # Log final CoT record
        await self._log_cot_record(
            run_id,
            "system",
            "development_stop",
            f"Development run stopped: {reason}",
            {"reason": reason, "stopped_at": stopped_at.isoformat()}
        )
        
        # Remove from active runs
        final_status = self.active_runs.pop(run_id)
        
        return self._format_response({
            "run_id": run_id,
            "status": "stopped",
            "reason": reason,
            "stopped_at": stopped_at.isoformat(),
            "final_progress": final_status["metadata"]["progress"]
        })