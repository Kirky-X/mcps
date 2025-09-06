"""Workflow Integrations

Integrates existing services (LLM, Search, Embedding) with LangGraph workflow.
Provides adapters and service managers for seamless workflow execution.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from ..services.llm_service import LLMService
from ..services.search_service import SearchService
from ..services.embedding_service import EmbeddingService
from ..database.connection import DatabaseManager
from .config import WorkflowConfig, ModelConfig, get_default_workflow_config


class ServiceManager:
    """Manages all services required by the workflow."""
    
    def __init__(self, db_path: str, config: Optional[Dict[str, Any]] = None):
        self.db_path = db_path
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Services
        self.llm_service: Optional[LLMService] = None
        self.search_service: Optional[SearchService] = None
        self.embedding_service: Optional[EmbeddingService] = None
        self.db_manager: Optional[DatabaseManager] = None
        
        # Initialization status
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize all services."""
        try:
            # Initialize database manager
            self.db_manager = DatabaseManager(self.db_path)
            await self.db_manager.initialize()
            
            # Initialize embedding service
            self.embedding_service = EmbeddingService()
            embedding_config = self.config.get("embedding", {
                "providers": {
                    "huggingface": {
                        "model": "sentence-transformers/all-MiniLM-L6-v2"
                    }
                },
                "default_provider": "huggingface"
            })
            
            if not await self.embedding_service.initialize(embedding_config):
                self.logger.warning("Embedding service initialization failed")
            
            # Initialize search service
            self.search_service = SearchService(self.db_path, self.embedding_service)
            
            # Initialize LLM service
            self.llm_service = LLMService()
            llm_config = self.config.get("llm", {
                "providers": {
                    "openai": {
                        "api_key": "your-openai-key",
                        "model": "gpt-3.5-turbo"
                    }
                },
                "default_provider": "openai"
            })
            
            if not await self.llm_service.initialize(llm_config):
                self.logger.error("LLM service initialization failed")
                return False
            
            self.initialized = True
            self.logger.info("All services initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Service initialization failed: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown all services."""
        if self.db_manager:
            await self.db_manager.close()
        
        self.initialized = False
        self.logger.info("All services shut down")
    
    def get_llm_service(self) -> Optional[LLMService]:
        """Get LLM service instance."""
        return self.llm_service if self.initialized else None
    
    def get_search_service(self) -> Optional[SearchService]:
        """Get search service instance."""
        return self.search_service if self.initialized else None
    
    def get_embedding_service(self) -> Optional[EmbeddingService]:
        """Get embedding service instance."""
        return self.embedding_service if self.initialized else None
    
    def get_db_manager(self) -> Optional[DatabaseManager]:
        """Get database manager instance."""
        return self.db_manager if self.initialized else None


class LLMAdapter:
    """Adapter for LLM service integration with workflow."""
    
    def __init__(self, llm_service: LLMService, workflow_config: WorkflowConfig):
        self.llm_service = llm_service
        self.workflow_config = workflow_config
        self.logger = logging.getLogger(__name__)
    
    async def generate_response(self, prompt: str, 
                              model_config: Optional[ModelConfig] = None,
                              task_type: str = "default",
                              **kwargs) -> Optional[Dict[str, Any]]:
        """Generate response using configured LLM."""
        if not self.llm_service:
            return None
        
        # Use model config if provided
        if model_config:
            model = model_config.model_name
            temperature = model_config.temperature
            max_tokens = model_config.max_tokens
        else:
            model = None
            temperature = kwargs.get("temperature", 0.7)
            max_tokens = kwargs.get("max_tokens")
        
        # Prepare messages
        messages = [{"role": "user", "content": prompt}]
        
        # Add system message if provided
        system_message = kwargs.get("system_message")
        if system_message:
            messages.insert(0, {"role": "system", "content": system_message})
        
        try:
            response = await self.llm_service.generate_response(
                messages=messages,
                model=model,
                task_type=task_type,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"LLM response generation failed: {e}")
            return None
    
    async def generate_structured_response(self, prompt: str, schema: Dict[str, Any],
                                         model_config: Optional[ModelConfig] = None,
                                         task_type: str = "default") -> Optional[Dict[str, Any]]:
        """Generate structured response following a schema."""
        if not self.llm_service:
            return None
        
        model = model_config.model_name if model_config else None
        temperature = model_config.temperature if model_config else 0.3
        
        try:
            response = await self.llm_service.generate_structured_response(
                prompt=prompt,
                schema=schema,
                model=model,
                task_type=task_type,
                temperature=temperature
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Structured response generation failed: {e}")
            return None


class SearchAdapter:
    """Adapter for search service integration with workflow."""
    
    def __init__(self, search_service: SearchService):
        self.search_service = search_service
        self.logger = logging.getLogger(__name__)
    
    async def search_codebase(self, query: str, 
                            content_types: Optional[List[str]] = None,
                            search_type: str = "hybrid",
                            limit: int = 20) -> Dict[str, Any]:
        """Search codebase for relevant code snippets."""
        if not self.search_service:
            return {"results": [], "total_results": 0}
        
        try:
            results = await self.search_service.search(
                query=query,
                content_types=content_types,
                search_type=search_type,
                limit=limit
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Codebase search failed: {e}")
            return {"results": [], "total_results": 0, "error": str(e)}
    
    async def semantic_search(self, query: str, 
                            content_types: Optional[List[str]] = None,
                            limit: int = 20) -> Dict[str, Any]:
        """Perform semantic search on codebase."""
        return await self.search_codebase(
            query=query,
            content_types=content_types,
            search_type="semantic",
            limit=limit
        )
    
    async def fulltext_search(self, query: str,
                            content_types: Optional[List[str]] = None,
                            limit: int = 20) -> Dict[str, Any]:
        """Perform full-text search on codebase."""
        return await self.search_codebase(
            query=query,
            content_types=content_types,
            search_type="fulltext",
            limit=limit
        )


class DatabaseAdapter:
    """Adapter for database operations in workflow."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    async def save_workflow_state(self, run_id: str, state_data: Dict[str, Any]) -> bool:
        """Save workflow state to database."""
        try:
            async with self.db_manager.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO development_runs 
                    (run_id, status, current_phase, state_data, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        run_id,
                        state_data.get("status", "running"),
                        state_data.get("current_phase", "planning"),
                        str(state_data)
                    )
                )
                await conn.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save workflow state: {e}")
            return False
    
    async def load_workflow_state(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Load workflow state from database."""
        try:
            async with self.db_manager.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT state_data FROM development_runs WHERE run_id = ?",
                    (run_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    # Parse state data (simplified - in real implementation use JSON)
                    return eval(row[0])  # Note: Use proper JSON parsing in production
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to load workflow state: {e}")
            return None
    
    async def save_cot_record(self, run_id: str, agent_type: str, 
                            input_data: str, output_data: str,
                            reasoning: str) -> bool:
        """Save chain-of-thought record."""
        try:
            async with self.db_manager.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO cot_records 
                    (run_id, agent_type, input_data, output_data, reasoning, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (run_id, agent_type, input_data, output_data, reasoning)
                )
                await conn.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save CoT record: {e}")
            return False
    
    async def save_test_result(self, run_id: str, module_name: str,
                             test_type: str, status: str, 
                             details: str) -> bool:
        """Save test result."""
        try:
            async with self.db_manager.get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO test_results 
                    (run_id, module_name, test_type, status, details, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (run_id, module_name, test_type, status, details)
                )
                await conn.commit()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save test result: {e}")
            return False


class WorkflowIntegrationManager:
    """Main integration manager for workflow services."""
    
    def __init__(self, db_path: str, config: Optional[Dict[str, Any]] = None):
        self.service_manager = ServiceManager(db_path, config)
        self.workflow_config = get_default_workflow_config()
        
        # Adapters (initialized after services)
        self.llm_adapter: Optional[LLMAdapter] = None
        self.search_adapter: Optional[SearchAdapter] = None
        self.db_adapter: Optional[DatabaseAdapter] = None
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize all services and adapters."""
        # Initialize services
        if not await self.service_manager.initialize():
            return False
        
        # Initialize adapters
        llm_service = self.service_manager.get_llm_service()
        search_service = self.service_manager.get_search_service()
        db_manager = self.service_manager.get_db_manager()
        
        if llm_service:
            self.llm_adapter = LLMAdapter(llm_service, self.workflow_config)
        
        if search_service:
            self.search_adapter = SearchAdapter(search_service)
        
        if db_manager:
            self.db_adapter = DatabaseAdapter(db_manager)
        
        self.logger.info("Workflow integration manager initialized")
        return True
    
    async def shutdown(self):
        """Shutdown all services."""
        await self.service_manager.shutdown()
    
    def get_llm_adapter(self) -> Optional[LLMAdapter]:
        """Get LLM adapter."""
        return self.llm_adapter
    
    def get_search_adapter(self) -> Optional[SearchAdapter]:
        """Get search adapter."""
        return self.search_adapter
    
    def get_db_adapter(self) -> Optional[DatabaseAdapter]:
        """Get database adapter."""
        return self.db_adapter
    
    def get_workflow_config(self) -> WorkflowConfig:
        """Get workflow configuration."""
        return self.workflow_config
    
    async def get_status(self) -> Dict[str, Any]:
        """Get status of all integrated services."""
        status = {
            "service_manager_initialized": self.service_manager.initialized,
            "adapters": {
                "llm_adapter": self.llm_adapter is not None,
                "search_adapter": self.search_adapter is not None,
                "db_adapter": self.db_adapter is not None
            }
        }
        
        # Get service statuses
        if self.service_manager.initialized:
            llm_service = self.service_manager.get_llm_service()
            search_service = self.service_manager.get_search_service()
            embedding_service = self.service_manager.get_embedding_service()
            
            if llm_service:
                status["llm_service"] = await llm_service.get_status()
            
            if search_service:
                status["search_service"] = await search_service.get_status()
            
            if embedding_service:
                status["embedding_service"] = await embedding_service.get_status()
        
        return status