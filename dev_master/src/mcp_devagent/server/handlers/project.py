"""Project Handler for MCP Protocol

Handles project analysis and requirement processing operations.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseHandler


class ProjectHandler(BaseHandler):
    """Handler for project-related MCP operations."""
    
    async def _initialize_impl(self):
        """Initialize project handler."""
        # Verify database tables exist
        async with self.db_manager.get_raw_connection() as conn:
            # Check if required tables exist (new schema)
            cursor = await conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('development_runs', 'modules', 'cot_records')"
            )
            tables = [row[0] for row in await cursor.fetchall()]
            
            if 'development_runs' not in tables or 'modules' not in tables or 'cot_records' not in tables:
                raise RuntimeError("Required database tables not found")
    
    async def handle_analyze(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze project requirements and generate development blueprint.
        
        Args:
            params: {
                "prd_content": str,  # Product requirements document content
                "tech_stack": str,  # Optional preferred technology stack
            }
        
        Returns:
            {
                "status": "success",
                "data": {
                    "project_id": str,
                    "blueprint": dict,
                    "analysis_summary": str
                }
            }
        """
        self._validate_params(params, ["prd_content"])
        
        prd_content = params["prd_content"]
        tech_stack = self._get_param(params, "tech_stack", "")
        
        return await self._execute_with_error_handling(
            "project_analyze",
            self._analyze_project_requirements,
            prd_content,
            tech_stack
        )
    
    async def _analyze_project_requirements(self, prd_content: str, tech_stack: str) -> Dict[str, Any]:
        """Analyze project requirements and generate blueprint."""
        project_id = str(uuid.uuid4())
        
        # Parse PRD content and extract key information
        analysis_result = await self._parse_prd_content(prd_content)
        
        # Generate development blueprint
        blueprint = await self._generate_development_blueprint(
            analysis_result, tech_stack
        )
        
        # Store project information
        await self._store_project_info(project_id, prd_content, tech_stack, blueprint)
        
        # Generate analysis summary
        summary = await self._generate_analysis_summary(analysis_result, blueprint)
        
        return self._format_response({
            "project_id": project_id,
            "blueprint": blueprint,
            "analysis_summary": summary
        })
    
    async def _parse_prd_content(self, prd_content: str) -> Dict[str, Any]:
        """Parse PRD content and extract structured information."""
        # This is a simplified implementation
        # In a real system, this would use NLP/LLM to parse the PRD
        
        analysis = {
            "project_name": "Extracted Project Name",
            "description": "Project description extracted from PRD",
            "features": [
                "Feature 1: User authentication",
                "Feature 2: Data management",
                "Feature 3: API integration"
            ],
            "requirements": {
                "functional": [
                    "User registration and login",
                    "Data CRUD operations",
                    "Real-time updates"
                ],
                "non_functional": [
                    "Performance: < 200ms response time",
                    "Security: OAuth 2.0 authentication",
                    "Scalability: Support 1000+ concurrent users"
                ]
            },
            "constraints": {
                "technical": ["Must use REST API", "Database agnostic"],
                "business": ["Budget: $50k", "Timeline: 3 months"]
            }
        }
        
        return analysis
    
    async def _generate_development_blueprint(self, analysis: Dict[str, Any], tech_stack: str) -> Dict[str, Any]:
        """Generate development blueprint based on analysis."""
        blueprint = {
            "project_info": {
                "name": analysis["project_name"],
                "description": analysis["description"],
                "version": "1.0.0"
            },
            "architecture": {
                "pattern": "MVC",
                "layers": ["Presentation", "Business Logic", "Data Access"],
                "components": [
                    "Frontend (React/Vue)",
                    "Backend API (FastAPI/Express)",
                    "Database (PostgreSQL/MongoDB)",
                    "Authentication Service",
                    "File Storage Service"
                ]
            },
            "technology_stack": {
                "frontend": tech_stack if "frontend" in tech_stack.lower() else "React",
                "backend": tech_stack if "backend" in tech_stack.lower() else "FastAPI",
                "database": "PostgreSQL",
                "deployment": "Docker + Kubernetes"
            },
            "development_phases": [
                {
                    "phase": 1,
                    "name": "Foundation Setup",
                    "duration": "2 weeks",
                    "deliverables": ["Project structure", "Database schema", "Authentication"]
                },
                {
                    "phase": 2,
                    "name": "Core Features",
                    "duration": "4 weeks",
                    "deliverables": ["CRUD operations", "API endpoints", "Frontend components"]
                },
                {
                    "phase": 3,
                    "name": "Integration & Testing",
                    "duration": "2 weeks",
                    "deliverables": ["Integration tests", "Performance optimization", "Deployment"]
                }
            ],
            "features": analysis["features"],
            "requirements": analysis["requirements"]
        }
        
        return blueprint
    
    async def _store_project_info(self, project_id: str, prd_content: str, tech_stack: str, blueprint: Dict[str, Any]):
        """Store project information in database."""
        async with self.db_manager.get_raw_connection() as conn:
            # Store as a code repository with project metadata
            await conn.execute(
                """
                INSERT INTO code_repositories (
                    name, path, description, language, framework,
                    repo_metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    blueprint["project_info"]["name"],
                    f"/projects/{project_id}",  # Virtual path for project
                    blueprint["project_info"]["description"],
                    tech_stack,
                    blueprint["technology_stack"]["backend"],
                    json.dumps({
                        "project_id": project_id,
                        "prd_content": prd_content,
                        "blueprint": blueprint,
                        "status": "analyzed"
                    }),
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                )
            )
            await conn.commit()
    
    async def _generate_analysis_summary(self, analysis: Dict[str, Any], blueprint: Dict[str, Any]) -> str:
        """Generate human-readable analysis summary."""
        summary = f"""
项目分析完成：{analysis['project_name']}

核心功能：
{chr(10).join(f'• {feature}' for feature in analysis['features'])}

技术架构：
• 架构模式：{blueprint['architecture']['pattern']}
• 前端技术：{blueprint['technology_stack']['frontend']}
• 后端技术：{blueprint['technology_stack']['backend']}
• 数据库：{blueprint['technology_stack']['database']}

开发阶段：
{chr(10).join(f'阶段{phase["phase"]}：{phase["name"]} ({phase["duration"]})' for phase in blueprint['development_phases'])}

项目已准备好进入开发阶段。
        """.strip()
        
        return summary
    
    async def handle_get_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get project information by ID.
        
        Args:
            params: {
                "project_id": str
            }
        
        Returns:
            Project information including blueprint
        """
        self._validate_params(params, ["project_id"])
        
        project_id = params["project_id"]
        
        return await self._execute_with_error_handling(
            "get_project_info",
            self._get_project_info,
            project_id
        )
    
    async def _get_project_info(self, project_id: str) -> Dict[str, Any]:
        """Retrieve project information from database."""
        async with self.db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,)
            )
            row = await cursor.fetchone()
            
            if not row:
                raise ValueError(f"Project not found: {project_id}")
            
            # Convert row to dict
            columns = [desc[0] for desc in cursor.description]
            project_data = dict(zip(columns, row))
            
            # Parse JSON fields
            if project_data["blueprint"]:
                project_data["blueprint"] = json.loads(project_data["blueprint"])
            
            return self._format_response(project_data)