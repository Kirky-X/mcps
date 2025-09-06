"""MCP Protocol Implementation

Implements the Model Context Protocol (MCP) for the DevAgent system.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

from ..database.connection import DatabaseManager
from .handlers import (
    BaseHandler,
    ProjectHandler,
    DevelopmentHandler,
    SearchHandler,
    CodeHandler,
    EmbeddingHandler,
    ExportHandler
)
logger = logging.getLogger(__name__)


class MCPError(Exception):
    """MCP protocol error."""
    
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error {code}: {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        result = {
            "code": self.code,
            "message": self.message
        }
        if self.data is not None:
            result["data"] = self.data
        return result


class MCPServer:
    """MCP Protocol Server Implementation."""
    
    def __init__(self, db_manager: DatabaseManager, export_service=None):
        self.db_manager = db_manager
        self.export_service = export_service
        self.handlers = {}
        self.capabilities = {
            "tools": [
                "project/analyze",
                "development/start",
                "development/status",
                "code/generate",
                "code/validate",
                "codebase/index",
                "search/hybrid",
                "search/fulltext",
                "search/semantic",
                "embedding/generate",
                "export/project",
                "export/status",
                "export/list",
                "cognitive/route",
                "problem/escalate"
            ],
            "resources": [
                "development/logs",
                "development/status",
                "embedding/status",
                "models/list",
                "export/history"
            ],
            "prompts": []
        }
    
    async def initialize(self):
        """Initialize MCP server and handlers."""
        logger.info("Initializing MCP server...")
        
        try:
            # Initialize handlers
            self.handlers = {
                "project": ProjectHandler(self.db_manager),
                "development": DevelopmentHandler(self.db_manager),
                "search": SearchHandler(self.db_manager),
                "code": CodeHandler(self.db_manager),
                "embedding": EmbeddingHandler(self.db_manager)
            }
            
            # Add export handler if export service is available
            if self.export_service:
                self.handlers["export"] = ExportHandler(self.db_manager, self.export_service)
            
            # Initialize each handler
            for name, handler in self.handlers.items():
                await handler.initialize()
                logger.info(f"Initialized {name} handler")
            
            logger.info("MCP server initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise
    
    @property
    def project_handler(self):
        """Get project handler."""
        return self.handlers.get("project")
    
    @property
    def development_handler(self):
        """Get development handler."""
        return self.handlers.get("development")
    
    @property
    def search_handler(self):
        """Get search handler."""
        return self.handlers.get("search")
    
    @property
    def code_handler(self):
        """Get code handler."""
        return self.handlers.get("code")
    
    @property
    def embedding_handler(self):
        """Get embedding handler."""
        return self.handlers.get("embedding")
    
    @property
    def export_handler(self):
        """Get export handler."""
        return self.handlers.get("export")
    
    async def shutdown(self):
        """Shutdown MCP server and handlers."""
        logger.info("Shutting down MCP server...")
        
        for name, handler in self.handlers.items():
            try:
                await handler.shutdown()
                logger.info(f"Shutdown {name} handler")
            except Exception as e:
                logger.error(f"Error shutting down {name} handler: {e}")
        
        logger.info("MCP server shutdown complete")
    
    async def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request."""
        logger.info(f"Handling MCP request: {method}")
        
        try:
            # Handle special MCP methods
            if method == "tools/list":
                tools = await self.list_tools()
                return {"tools": tools}
            elif method == "resources/list":
                return {"resources": []}
            elif method == "tools/call":
                # Extract tool name and arguments
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if not tool_name:
                    raise MCPError(-32602, "Missing tool name")
                
                # Parse tool name to determine handler
                if "/" not in tool_name:
                    raise MCPError(-32601, f"Invalid tool name format: {tool_name}")
                
                handler_name, action = tool_name.split("/", 1)
                
                # Get handler
                if handler_name not in self.handlers:
                    raise MCPError(-32601, f"Unknown handler: {handler_name}")
                
                handler = self.handlers[handler_name]
                
                # Route to appropriate handler method
                if hasattr(handler, f"handle_{action}"):
                    handler_method = getattr(handler, f"handle_{action}")
                    result = await handler_method(arguments)
                    
                    logger.info(f"Successfully handled {tool_name}")
                    return result
                else:
                    raise MCPError(-32601, f"Unknown action: {action} for handler: {handler_name}")
            else:
                # Parse method to determine handler for direct calls
                if "/" not in method:
                    raise MCPError(-32601, f"Invalid method format: {method}")
                
                handler_name, action = method.split("/", 1)
                
                # Get handler
                if handler_name not in self.handlers:
                    raise MCPError(-32601, f"Unknown handler: {handler_name}")
                
                handler = self.handlers[handler_name]
                
                # Route to appropriate handler method
                if hasattr(handler, f"handle_{action}"):
                    handler_method = getattr(handler, f"handle_{action}")
                    result = await handler_method(params)
                    
                    logger.info(f"Successfully handled {method}")
                    return result
                else:
                    raise MCPError(-32601, f"Unknown action: {action} for handler: {handler_name}")
        
        except MCPError:
            raise
        except Exception as e:
            logger.error(f"Error handling MCP request {method}: {e}")
            raise MCPError(-32603, "Internal error", str(e))
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools."""
        tools = []
        
        # Project tools
        tools.extend([
            {
                "name": "project/analyze",
                "description": "Analyze project requirements and generate development blueprint",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prd_content": {"type": "string", "description": "Product requirements document content"},
                        "tech_stack": {"type": "string", "description": "Preferred technology stack"}
                    },
                    "required": ["prd_content"]
                }
            }
        ])
        
        # Development tools
        tools.extend([
            {
                "name": "development/start",
                "description": "Start a new development run",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_blueprint": {"type": "object", "description": "Project development blueprint"},
                        "tech_constraints": {"type": "object", "description": "Technology constraints"}
                    },
                    "required": ["project_blueprint"]
                }
            },
            {
                "name": "development/status",
                "description": "Get development run status",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "run_id": {"type": "string", "description": "Development run ID"}
                    },
                    "required": ["run_id"]
                }
            }
        ])
        
        # Search tools
        tools.extend([
            {
                "name": "search/hybrid",
                "description": "Perform hybrid search combining FTS5 and VSS",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "search_type": {"type": "string", "enum": ["cot_records", "code_artifacts", "both"], "default": "both"},
                        "max_results": {"type": "integer", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search/fulltext",
                "description": "Perform FTS5 full-text search",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "search_type": {"type": "string", "enum": ["cot_records", "code_artifacts", "both"], "default": "both"},
                        "max_results": {"type": "integer", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "search/semantic",
                "description": "Perform semantic vector search",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "search_type": {"type": "string", "enum": ["cot_records", "code_artifacts", "both"], "default": "both"},
                        "max_results": {"type": "integer", "default": 10}
                    },
                    "required": ["query"]
                }
            }
        ])
        
        # Code tools
        tools.extend([
            {
                "name": "code/generate",
                "description": "Generate code module based on specifications",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "module_spec": {"type": "object", "description": "Module specification"},
                        "context": {"type": "object", "description": "Development context"}
                    },
                    "required": ["module_spec"]
                }
            },
            {
                "name": "code/validate",
                "description": "Validate generated code quality",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code_content": {"type": "string", "description": "Code to validate"},
                        "validation_rules": {"type": "object", "description": "Validation rules"}
                    },
                    "required": ["code_content"]
                }
            }
        ])
        
        # Embedding tools
        tools.extend([
            {
                "name": "embedding/generate",
                "description": "Generate text embeddings",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Text to embed"},
                        "model_name": {"type": "string", "description": "Embedding model name"}
                    },
                    "required": ["text"]
                }
            }
        ])
        
        # Export tools (only if export handler is available)
        if "export" in self.handlers:
            tools.extend([
                {
                    "name": "export/project",
                    "description": "Export project with code, structure, and metadata",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_path": {"type": "string", "description": "Path to project directory"},
                            "export_format": {"type": "string", "enum": ["zip", "tar.gz"], "default": "zip"},
                            "include_metadata": {"type": "boolean", "default": True},
                            "include_docs": {"type": "boolean", "default": True},
                            "include_tests": {"type": "boolean", "default": True},
                            "exclude_patterns": {"type": "array", "items": {"type": "string"}, "default": []}
                        },
                        "required": ["project_path"]
                    }
                },
                {
                    "name": "export/status",
                    "description": "Get export operation status",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "export_id": {"type": "string", "description": "Export operation ID"}
                        },
                        "required": ["export_id"]
                    }
                },
                {
                    "name": "export/list",
                    "description": "List available export options and formats",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project_path": {"type": "string", "description": "Path to project directory"}
                        }
                    }
                }
            ])
        
        return tools
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available MCP resources."""
        resources = [
            {
                "uri": "development://logs/{run_id}",
                "name": "Development Logs",
                "description": "Chain of thought records for development run",
                "mimeType": "application/json"
            },
            {
                "uri": "development://status/{run_id}",
                "name": "Development Status",
                "description": "Current status of development run",
                "mimeType": "application/json"
            },
            {
                "uri": "embedding://status",
                "name": "Embedding Status",
                "description": "Status of embedding generation pipeline",
                "mimeType": "application/json"
            },
            {
                "uri": "models://list",
                "name": "Available Models",
                "description": "List of available embedding models",
                "mimeType": "application/json"
            }
        ]
        
        # Add export resources if export handler is available
        if "export" in self.handlers:
            resources.extend([
                {
                    "uri": "export://history",
                    "name": "Export History",
                    "description": "History of project export operations",
                    "mimeType": "application/json"
                },
                {
                    "uri": "export://status/{export_id}",
                    "name": "Export Status",
                    "description": "Status of specific export operation",
                    "mimeType": "application/json"
                },
                {
                    "uri": "export://download/{export_id}",
                    "name": "Export Download",
                    "description": "Download exported project archive",
                    "mimeType": "application/octet-stream"
                }
            ])
        
        return resources
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get MCP server capabilities."""
        return self.capabilities