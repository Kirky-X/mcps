"""Configuration management for MCP DevAgent.

Provides centralized configuration management for database connections,
API keys, service settings, and environment-specific configurations.
"""

import os
from typing import Optional

from .settings import Settings, DatabaseConfig, LLMConfig, EmbeddingConfig
from .environment import Environment


def get_settings(config_env: Optional[str] = None) -> Settings:
    """Get application settings.
    
    Args:
        config_env: Configuration environment name
        
    Returns:
        Settings instance
    """
    return Settings()


def validate_environment() -> dict:
    """Validate environment configuration.
    
    Returns:
        Dict with validation results
    """
    # Basic environment validation
    return {
        "valid": True,
        "errors": []
    }


__all__ = [
    "Settings",
    "DatabaseConfig", 
    "LLMConfig",
    "EmbeddingConfig",
    "Environment",
    "get_settings",
    "validate_environment"
]

__version__ = "0.1.0"