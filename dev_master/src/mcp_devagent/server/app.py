"""MCP DevAgent Server Application

Main FastAPI application implementing the MCP (Model Context Protocol) server
for the DevAgent system.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError

from src.mcp_devagent.config.settings import get_settings
from src.mcp_devagent.database.connection import DatabaseManager
from src.mcp_devagent.services.export_service import ProjectExportService
from src.mcp_devagent.server.mcp_server import MCPServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
db_manager: Optional[DatabaseManager] = None
export_service: Optional[ProjectExportService] = None
mcp_server: Optional[MCPServer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global db_manager, export_service, mcp_server
    
    # Startup
    logger.info("Starting MCP DevAgent Server...")
    
    try:
        # Initialize database
        settings = get_settings()
        db_manager = DatabaseManager()
        await db_manager.initialize()
        logger.info("Database initialized successfully")
        
        # Initialize export service
        export_service = ProjectExportService()
        logger.info("Export service initialized successfully")
        
        # Initialize MCP server with export service
        mcp_server = MCPServer(db_manager, export_service)
        await mcp_server.initialize()
        logger.info("MCP server initialized successfully")
        
        # Store in app state
        app.state.db_manager = db_manager
        app.state.export_service = export_service
        app.state.mcp_server = mcp_server
        
        logger.info("MCP DevAgent Server started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP DevAgent Server...")
    
    if mcp_server:
        await mcp_server.shutdown()
        logger.info("MCP server shutdown complete")
    
    if db_manager:
        await db_manager.close()
        logger.info("Database connections closed")
    
    logger.info("MCP DevAgent Server shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="MCP DevAgent Server",
    description="AI-driven development agent service based on Model Context Protocol",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add global exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with 422 status."""
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422, content={"detail": str(exc)})

@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors with 400 status."""
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from datetime import datetime
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0"
    }

@app.options("/health")
async def health_check_options():
    """CORS preflight for health check."""
    from fastapi import Response
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


# MCP Protocol Models
class MCPRequest(BaseModel):
    """Base MCP request model."""
    method: str = Field(..., description="MCP method name")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    id: Optional[str] = Field(None, description="Request ID")


class MCPResponse(BaseModel):
    """Base MCP response model."""
    result: Optional[Dict[str, Any]] = Field(None, description="Method result")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information")
    id: Optional[str] = Field(None, description="Request ID")


# MCP Protocol endpoint
@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """Main MCP protocol endpoint."""
    try:
        if not app.state.mcp_server:
            raise HTTPException(status_code=500, detail="MCP server not initialized")
        
        # Process MCP request
        result = await app.state.mcp_server.handle_request(
            method=request.method,
            params=request.params
        )
        
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request.id
        }
        
    except Exception as e:
        logger.error(f"MCP request failed: {e}")
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            },
            "id": request.id
        }


# Development status endpoint
@app.get("/development/status/{run_id}")
async def get_development_status(run_id: str):
    """Get development run status."""
    try:
        if not app.state.mcp_server:
            raise HTTPException(status_code=500, detail="MCP server not initialized")
        
        # Delegate to MCP server development handler
        if hasattr(app.state.mcp_server, 'development_handler') and app.state.mcp_server.development_handler:
            result = await app.state.mcp_server.development_handler.handle_get_status(run_id)
            return result
        else:
            return {
                "run_id": run_id,
                "status": "running",
                "message": "Development status endpoint ready"
            }
            
    except Exception as e:
        logger.error(f"Failed to get development status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search endpoint
class HybridSearchRequest(BaseModel):
    """Hybrid search request model."""
    query: str = Field(..., description="Search query")
    content_types: Optional[List[str]] = Field(default=None, description="Content types to search")
    limit: int = Field(default=10, description="Maximum results")

@app.post("/search/hybrid")
async def hybrid_search(request: HybridSearchRequest):
    """Hybrid search endpoint combining FTS5 and VSS."""
    try:
        if not app.state.mcp_server:
            raise HTTPException(status_code=500, detail="MCP server not initialized")
        
        # Delegate to MCP server search handler
        if hasattr(app.state.mcp_server, 'search_handler') and app.state.mcp_server.search_handler:
            result = await app.state.mcp_server.search_handler.handle_hybrid({
                "query": request.query,
                "content_types": request.content_types,
                "limit": request.limit
            })
            return result
        else:
            return {
                "results": [],
                "total_results": 0,
                "search_type": "hybrid",
                "query": request.query
            }
        
    except ValueError as e:
        # Handle validation errors with 400 status
        logger.error(f"Hybrid search validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "src.mcp_devagent.server.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
