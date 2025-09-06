"""Code Handler for MCP Protocol

Handles code generation and analysis operations.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseHandler


class CodeHandler(BaseHandler):
    """Handler for code-related MCP operations."""
    
    def __init__(self, db_manager):
        super().__init__(db_manager)
        self.llm_service = None  # Will be injected
    
    async def _initialize_impl(self):
        """Initialize code handler."""
        # Verify database tables exist
        async with self.db_manager.get_raw_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN (
                    'code_files', 'agent_interactions'
                )
                """
            )
            tables = [row[0] for row in await cursor.fetchall()]
            
            required_tables = ['code_files', 'agent_interactions']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                raise RuntimeError(f"Required code tables not found: {missing_tables}")
    
    def set_llm_service(self, llm_service):
        """Set LLM service for code generation."""
        self.llm_service = llm_service
    
    async def handle_generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code based on requirements.
        
        Args:
            params: {
                "requirements": str,
                "context": dict,         # Optional context
                "file_type": str,       # Optional: "python", "javascript", etc.
                "style_guide": str,     # Optional style preferences
                "project_id": str       # Optional project association
            }
        
        Returns:
            Generated code with metadata
        """
        self._validate_params(params, ["requirements"])
        
        if not self.llm_service:
            return self._format_error_response("LLM service not configured")
        
        requirements = params["requirements"]
        context = self._get_param(params, "context", {})
        file_type = self._get_param(params, "file_type", "python")
        style_guide = self._get_param(params, "style_guide", "")
        project_id = self._get_param(params, "project_id", None)
        
        return await self._execute_with_error_handling(
            "code_generation",
            self._generate_code,
            requirements,
            context,
            file_type,
            style_guide,
            project_id
        )
    
    async def _generate_code(self, requirements: str, context: Dict[str, Any], 
                           file_type: str, style_guide: str, 
                           project_id: Optional[str]) -> Dict[str, Any]:
        """Generate code using LLM service."""
        # Prepare generation prompt
        prompt = self._build_generation_prompt(
            requirements, context, file_type, style_guide
        )
        
        # Generate code using LLM
        generation_result = await self.llm_service.generate_code(
            prompt=prompt,
            file_type=file_type,
            max_tokens=2000
        )
        
        if not generation_result.get("success"):
            return self._format_error_response(
                f"Code generation failed: {generation_result.get('error', 'Unknown error')}"
            )
        
        generated_code = generation_result["code"]
        
        # Store code artifact
        artifact_id = await self._store_code_artifact(
            code=generated_code,
            file_type=file_type,
            requirements=requirements,
            context=context,
            project_id=project_id
        )
        
        # Record generation in CoT
        await self._record_generation_cot(
            artifact_id=artifact_id,
            requirements=requirements,
            context=context,
            generation_result=generation_result
        )
        
        return self._format_response({
            "artifact_id": artifact_id,
            "code": generated_code,
            "file_type": file_type,
            "requirements": requirements,
            "metadata": {
                "tokens_used": generation_result.get("tokens_used", 0),
                "model": generation_result.get("model", "unknown"),
                "generation_time": generation_result.get("generation_time", 0)
            }
        })
    
    async def handle_analyze(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze existing code.
        
        Args:
            params: {
                "code": str,
                "analysis_type": str,   # "quality", "security", "performance", "all"
                "file_type": str,       # Optional
                "context": dict         # Optional context
            }
        
        Returns:
            Code analysis results
        """
        self._validate_params(params, ["code"])
        
        if not self.llm_service:
            return self._format_error_response("LLM service not configured")
        
        code = params["code"]
        analysis_type = self._get_param(params, "analysis_type", "all")
        file_type = self._get_param(params, "file_type", "python")
        context = self._get_param(params, "context", {})
        
        return await self._execute_with_error_handling(
            "code_analysis",
            self._analyze_code,
            code,
            analysis_type,
            file_type,
            context
        )
    
    async def _analyze_code(self, code: str, analysis_type: str, 
                          file_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code using LLM service."""
        # Prepare analysis prompt
        prompt = self._build_analysis_prompt(code, analysis_type, file_type, context)
        
        # Analyze code using LLM
        analysis_result = await self.llm_service.analyze_code(
            prompt=prompt,
            code=code,
            analysis_type=analysis_type
        )
        
        if not analysis_result.get("success"):
            return self._format_error_response(
                f"Code analysis failed: {analysis_result.get('error', 'Unknown error')}"
            )
        
        # Record analysis in CoT
        await self._record_analysis_cot(
            code=code,
            analysis_type=analysis_type,
            analysis_result=analysis_result
        )
        
        return self._format_response({
            "analysis": analysis_result["analysis"],
            "analysis_type": analysis_type,
            "file_type": file_type,
            "suggestions": analysis_result.get("suggestions", []),
            "issues": analysis_result.get("issues", []),
            "metadata": {
                "tokens_used": analysis_result.get("tokens_used", 0),
                "model": analysis_result.get("model", "unknown"),
                "analysis_time": analysis_result.get("analysis_time", 0)
            }
        })
    
    async def handle_refactor(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Refactor existing code.
        
        Args:
            params: {
                "code": str,
                "refactor_type": str,   # "optimize", "modernize", "clean", "extract"
                "instructions": str,    # Specific refactoring instructions
                "file_type": str,       # Optional
                "preserve_behavior": bool  # Optional, default True
            }
        
        Returns:
            Refactored code with explanation
        """
        self._validate_params(params, ["code", "refactor_type"])
        
        if not self.llm_service:
            return self._format_error_response("LLM service not configured")
        
        code = params["code"]
        refactor_type = params["refactor_type"]
        instructions = self._get_param(params, "instructions", "")
        file_type = self._get_param(params, "file_type", "python")
        preserve_behavior = self._get_param(params, "preserve_behavior", True)
        
        return await self._execute_with_error_handling(
            "code_refactoring",
            self._refactor_code,
            code,
            refactor_type,
            instructions,
            file_type,
            preserve_behavior
        )
    
    async def _refactor_code(self, code: str, refactor_type: str, 
                           instructions: str, file_type: str, 
                           preserve_behavior: bool) -> Dict[str, Any]:
        """Refactor code using LLM service."""
        # Prepare refactoring prompt
        prompt = self._build_refactoring_prompt(
            code, refactor_type, instructions, file_type, preserve_behavior
        )
        
        # Refactor code using LLM
        refactor_result = await self.llm_service.refactor_code(
            prompt=prompt,
            original_code=code,
            refactor_type=refactor_type
        )
        
        if not refactor_result.get("success"):
            return self._format_error_response(
                f"Code refactoring failed: {refactor_result.get('error', 'Unknown error')}"
            )
        
        refactored_code = refactor_result["code"]
        
        # Store refactored code as new artifact
        artifact_id = await self._store_code_artifact(
            code=refactored_code,
            file_type=file_type,
            requirements=f"Refactored ({refactor_type}): {instructions}",
            context={"original_code": code, "refactor_type": refactor_type}
        )
        
        # Record refactoring in CoT
        await self._record_refactoring_cot(
            original_code=code,
            refactored_code=refactored_code,
            refactor_type=refactor_type,
            refactor_result=refactor_result
        )
        
        return self._format_response({
            "artifact_id": artifact_id,
            "original_code": code,
            "refactored_code": refactored_code,
            "refactor_type": refactor_type,
            "explanation": refactor_result.get("explanation", ""),
            "changes": refactor_result.get("changes", []),
            "metadata": {
                "tokens_used": refactor_result.get("tokens_used", 0),
                "model": refactor_result.get("model", "unknown"),
                "refactor_time": refactor_result.get("refactor_time", 0)
            }
        })
    
    async def _store_code_artifact(self, code: str, file_type: str, 
                                 requirements: str, context: Dict[str, Any],
                                 project_id: Optional[str] = None) -> str:
        """Store code artifact in database."""
        artifact_id = str(uuid.uuid4())
        
        async with self.db_manager.get_raw_connection() as conn:
            await conn.execute(
                """
                INSERT INTO code_files (
                    id, file_path, file_type, content, metadata, project_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    f"generated_{artifact_id}.{file_type}",
                    file_type,
                    code,
                    json.dumps({
                        "requirements": requirements,
                        "context": context,
                        "generated": True
                    }),
                    project_id,
                    datetime.utcnow().isoformat()
                )
            )
            await conn.commit()
        
        return artifact_id
    
    async def _record_generation_cot(self, artifact_id: str, requirements: str,
                                   context: Dict[str, Any], 
                                   generation_result: Dict[str, Any]):
        """Record code generation in CoT records."""
        cot_id = str(uuid.uuid4())
        
        async with self.db_manager.get_raw_connection() as conn:
            await conn.execute(
                """
                INSERT INTO agent_interactions (
                    id, session_id, interaction_type, content, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cot_id,
                    "code_generation",
                    "generate",
                    json.dumps({
                        "artifact_id": artifact_id,
                        "requirements": requirements,
                        "context": context,
                        "generation_result": generation_result
                    }),
                    json.dumps({
                        "agent_type": "code_handler"
                    }),
                    datetime.utcnow().isoformat()
                )
            )
            await conn.commit()
    
    async def _record_analysis_cot(self, code: str, analysis_type: str,
                                 analysis_result: Dict[str, Any]):
        """Record code analysis in CoT records."""
        cot_id = str(uuid.uuid4())
        
        async with self.db_manager.get_raw_connection() as conn:
            await conn.execute(
                """
                INSERT INTO agent_interactions (
                    id, session_id, interaction_type, content, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cot_id,
                    "code_analysis",
                    "analyze",
                    json.dumps({
                        "code": code,
                        "analysis_type": analysis_type,
                        "analysis_result": analysis_result
                    }),
                    json.dumps({
                        "agent_type": "code_handler",
                        "code_length": len(code)
                    }),
                    datetime.utcnow().isoformat()
                )
            )
            await conn.commit()
    
    async def _record_refactoring_cot(self, original_code: str, refactored_code: str,
                                    refactor_type: str, refactor_result: Dict[str, Any]):
        """Record code refactoring in CoT records."""
        cot_id = str(uuid.uuid4())
        
        async with self.db_manager.get_raw_connection() as conn:
            await conn.execute(
                """
                INSERT INTO agent_interactions (
                    id, session_id, interaction_type, content, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    cot_id,
                    "code_refactoring",
                    "refactor",
                    json.dumps({
                        "original_code": original_code,
                        "refactored_code": refactored_code,
                        "refactor_type": refactor_type,
                        "refactor_result": refactor_result
                    }),
                    json.dumps({
                        "agent_type": "code_handler",
                        "original_length": len(original_code),
                        "refactored_length": len(refactored_code)
                    }),
                    datetime.utcnow().isoformat()
                )
            )
            await conn.commit()
    
    def _build_generation_prompt(self, requirements: str, context: Dict[str, Any],
                               file_type: str, style_guide: str) -> str:
        """Build prompt for code generation."""
        prompt_parts = [
            f"Generate {file_type} code based on the following requirements:",
            f"Requirements: {requirements}"
        ]
        
        if context:
            prompt_parts.append(f"Context: {json.dumps(context, indent=2)}")
        
        if style_guide:
            prompt_parts.append(f"Style Guide: {style_guide}")
        
        prompt_parts.extend([
            "Please provide clean, well-documented, and efficient code.",
            "Include appropriate comments and follow best practices."
        ])
        
        return "\n\n".join(prompt_parts)
    
    def _build_analysis_prompt(self, code: str, analysis_type: str,
                             file_type: str, context: Dict[str, Any]) -> str:
        """Build prompt for code analysis."""
        prompt_parts = [
            f"Analyze the following {file_type} code for {analysis_type}:",
            f"Code:\n```{file_type}\n{code}\n```"
        ]
        
        if context:
            prompt_parts.append(f"Context: {json.dumps(context, indent=2)}")
        
        analysis_instructions = {
            "quality": "Focus on code quality, readability, maintainability, and best practices.",
            "security": "Focus on security vulnerabilities, potential exploits, and security best practices.",
            "performance": "Focus on performance bottlenecks, optimization opportunities, and efficiency.",
            "all": "Provide comprehensive analysis covering quality, security, and performance aspects."
        }
        
        instruction = analysis_instructions.get(analysis_type, analysis_instructions["all"])
        prompt_parts.append(instruction)
        
        prompt_parts.append("Provide specific suggestions and identify any issues.")
        
        return "\n\n".join(prompt_parts)
    
    def _build_refactoring_prompt(self, code: str, refactor_type: str,
                                instructions: str, file_type: str,
                                preserve_behavior: bool) -> str:
        """Build prompt for code refactoring."""
        prompt_parts = [
            f"Refactor the following {file_type} code:",
            f"Code:\n```{file_type}\n{code}\n```",
            f"Refactoring Type: {refactor_type}"
        ]
        
        if instructions:
            prompt_parts.append(f"Specific Instructions: {instructions}")
        
        if preserve_behavior:
            prompt_parts.append("IMPORTANT: Preserve the original behavior and functionality.")
        
        refactor_guidelines = {
            "optimize": "Focus on improving performance and efficiency while maintaining readability.",
            "modernize": "Update code to use modern language features and best practices.",
            "clean": "Improve code readability, remove redundancy, and enhance structure.",
            "extract": "Extract reusable components, functions, or modules from the code."
        }
        
        guideline = refactor_guidelines.get(refactor_type, "Apply general refactoring principles.")
        prompt_parts.append(guideline)
        
        prompt_parts.append("Provide the refactored code and explain the changes made.")
        
        return "\n\n".join(prompt_parts)