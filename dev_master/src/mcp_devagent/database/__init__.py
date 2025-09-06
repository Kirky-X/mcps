"""Database module for MCP DevAgent.

Provides database connection management, models, and initialization.
"""

from .connection import DatabaseManager
from .models import CodeFile, CodeChunk
from .init import init_database

__all__ = [
    "DatabaseManager",
    "CodeFile",
    "CodeChunk",
    "init_database"
]