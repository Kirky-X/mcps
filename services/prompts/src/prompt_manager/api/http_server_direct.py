"""HTTP server with direct Supabase authentication - bypasses IPv6 issues"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..auth.direct_router import router as direct_auth_router
from ..utils.config import load_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    config = load_config()
    logger.info("Starting Prompt Manager API with direct Supabase authentication")
    
    # Initialize Supabase client for direct authentication
    try:
        from supabase import create_client
        app.state.supabase = create_client(
            config.database.supabase_url,
            config.database.supabase_key
        )
        logger.info("Direct Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise
    
    yield
    
    logger.info("Shutting down Prompt Manager API")


def create_app() -> FastAPI:
    """Create FastAPI application with direct Supabase auth."""
    config = load_config()
    
    app = FastAPI(
        title="Prompt Manager API",
        description="API for managing AI prompts with direct Supabase authentication",
        version="1.0.0",
        lifespan=lifespan,
    )
    
    # Configure CORS with default origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Default to allow all origins for testing
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    # app.include_router(health.router)  # Commented out - add if needed
    # app.include_router(prompts.router)  # Commented out - add if needed
    
    # Include direct authentication router (bypasses IPv6/SQLAlchemy issues)
    app.include_router(direct_auth_router)
    
    return app


# Create the app instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Prompt Manager API with Direct Supabase Authentication",
        "version": "1.0.0",
        "auth_mode": "direct_supabase",
        "status": "operational"
    }


@app.get("/info")
async def info():
    """Get application information."""
    config = load_config()
    return {
        "database_type": config.database.type,
        "auth_mode": "direct_supabase",
        "features": {
            "direct_auth": True,
            "ipv6_bypass": True,
            "schema_isolation": True
        }
    }