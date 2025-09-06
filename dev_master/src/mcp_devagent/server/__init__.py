"""MCP DevAgent Server Package

This package contains the MCP (Model Context Protocol) server implementation
for the DevAgent system.
"""

from .app import app

def create_app():
    """Create and return the FastAPI application instance.
    
    Returns:
        FastAPI: The configured application instance
    """
    return app

__all__ = ["create_app", "app"]
__version__ = "0.1.0"