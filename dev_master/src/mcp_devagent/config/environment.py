"""Environment management for MCP DevAgent.

Handles environment variable loading, configuration file parsing,
and environment-specific settings management.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import asdict

from .settings import Settings


class Environment:
    """Environment configuration manager."""
    
    def __init__(self, env_name: Optional[str] = None):
        """Initialize environment manager.
        
        Args:
            env_name: Environment name (development, staging, production)
        """
        self.env_name = env_name or os.getenv("MCP_ENVIRONMENT", "development")
        self.config_dir = Path("./config")
        self.env_file = Path(".env")
        
        # Load environment variables from .env file
        self._load_env_file()
    
    def _load_env_file(self) -> None:
        """Load environment variables from .env file."""
        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        
                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value
    
    def load_config_file(self, config_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """Load configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        if config_path is None:
            # Try environment-specific config first
            config_path = self.config_dir / f"{self.env_name}.yaml"
            if not config_path.exists():
                config_path = self.config_dir / "default.yaml"
            if not config_path.exists():
                config_path = self.config_dir / f"{self.env_name}.json"
            if not config_path.exists():
                config_path = self.config_dir / "default.json"
        
        config_path = Path(config_path)
        
        if not config_path.exists():
            return {}
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif config_path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
        except Exception as e:
            raise RuntimeError(f"Failed to load config file {config_path}: {e}")
    
    def save_config_file(self, config: Dict[str, Any], config_path: Optional[Union[str, Path]] = None) -> None:
        """Save configuration to file.
        
        Args:
            config: Configuration dictionary
            config_path: Path to save configuration file
        """
        if config_path is None:
            self.config_dir.mkdir(exist_ok=True)
            config_path = self.config_dir / f"{self.env_name}.yaml"
        
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.safe_dump(config, f, default_flow_style=False, indent=2)
                elif config_path.suffix.lower() == '.json':
                    json.dump(config, f, indent=2)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
        except Exception as e:
            raise RuntimeError(f"Failed to save config file {config_path}: {e}")
    
    def create_settings(self) -> Settings:
        """Create Settings instance from environment and config files.
        
        Returns:
            Configured Settings instance
        """
        # Start with default settings
        settings = Settings()
        
        # Load from config file
        file_config = self.load_config_file()
        if file_config:
            settings = self._merge_config(settings, file_config)
        
        # Override with environment variables
        settings = self._apply_env_overrides(settings)
        
        # Set environment name
        settings.environment = self.env_name
        
        return settings
    
    def _merge_config(self, settings: Settings, config: Dict[str, Any]) -> Settings:
        """Merge configuration dictionary into settings.
        
        Args:
            settings: Base settings instance
            config: Configuration dictionary to merge
            
        Returns:
            Updated settings instance
        """
        # Database config
        if 'database' in config:
            db_config = config['database']
            if 'db_path' in db_config:
                settings.database.db_path = db_config['db_path']
            if 'max_connections' in db_config:
                settings.database.max_connections = db_config['max_connections']
            if 'enable_wal_mode' in db_config:
                settings.database.enable_wal_mode = db_config['enable_wal_mode']
            if 'vss_dimension' in db_config:
                settings.database.vss_dimension = db_config['vss_dimension']
            if 'vss_metric' in db_config:
                settings.database.vss_metric = db_config['vss_metric']
        
        # LLM config
        if 'llm' in config:
            llm_config = config['llm']
            if 'default_provider' in llm_config:
                settings.llm.default_provider = llm_config['default_provider']
            if 'enabled_providers' in llm_config:
                settings.llm.enabled_providers = llm_config['enabled_providers']
            if 'openai_model' in llm_config:
                settings.llm.openai_model = llm_config['openai_model']
            if 'anthropic_model' in llm_config:
                settings.llm.anthropic_model = llm_config['anthropic_model']
            if 'max_retries' in llm_config:
                settings.llm.max_retries = llm_config['max_retries']
        
        # Embedding config
        if 'embedding' in config:
            emb_config = config['embedding']
            if 'default_provider' in emb_config:
                settings.embedding.default_provider = emb_config['default_provider']
            if 'enabled_providers' in emb_config:
                settings.embedding.enabled_providers = emb_config['enabled_providers']
            if 'openai_model' in emb_config:
                settings.embedding.openai_model = emb_config['openai_model']
            if 'huggingface_model' in emb_config:
                settings.embedding.huggingface_model = emb_config['huggingface_model']
        
        # Search config
        if 'search' in config:
            search_config = config['search']
            if 'fts_weight' in search_config:
                settings.search.fts_weight = search_config['fts_weight']
            if 'vss_weight' in search_config:
                settings.search.vss_weight = search_config['vss_weight']
            if 'default_limit' in search_config:
                settings.search.default_limit = search_config['default_limit']
        
        # MCP config
        if 'mcp' in config:
            mcp_config = config['mcp']
            if 'host' in mcp_config:
                settings.mcp.host = mcp_config['host']
            if 'port' in mcp_config:
                settings.mcp.port = mcp_config['port']
            if 'debug' in mcp_config:
                settings.mcp.debug = mcp_config['debug']
            if 'log_level' in mcp_config:
                settings.mcp.log_level = mcp_config['log_level']
        
        # App config
        if 'app' in config:
            app_config = config['app']
            if 'debug' in app_config:
                settings.debug = app_config['debug']
            if 'data_dir' in app_config:
                settings.data_dir = app_config['data_dir']
            if 'logs_dir' in app_config:
                settings.logs_dir = app_config['logs_dir']
        
        return settings
    
    def _apply_env_overrides(self, settings: Settings) -> Settings:
        """Apply environment variable overrides to settings.
        
        Args:
            settings: Base settings instance
            
        Returns:
            Updated settings instance
        """
        # Database overrides
        if env_val := os.getenv("MCP_DATABASE_PATH"):
            settings.database.db_path = env_val
        
        if env_val := os.getenv("MCP_DATABASE_MAX_CONNECTIONS"):
            settings.database.max_connections = int(env_val)
        
        if env_val := os.getenv("MCP_DATABASE_VSS_DIMENSION"):
            settings.database.vss_dimension = int(env_val)
        
        # LLM overrides
        if env_val := os.getenv("MCP_LLM_DEFAULT_PROVIDER"):
            settings.llm.default_provider = env_val
        
        if env_val := os.getenv("OPENAI_API_KEY"):
            settings.llm.openai_api_key = env_val
            settings.embedding.openai_api_key = env_val
        
        if env_val := os.getenv("ANTHROPIC_API_KEY"):
            settings.llm.anthropic_api_key = env_val
        
        if env_val := os.getenv("MCP_LLM_OPENAI_MODEL"):
            settings.llm.openai_model = env_val
        
        if env_val := os.getenv("MCP_LLM_ANTHROPIC_MODEL"):
            settings.llm.anthropic_model = env_val
        
        # Embedding overrides
        if env_val := os.getenv("MCP_EMBEDDING_DEFAULT_PROVIDER"):
            settings.embedding.default_provider = env_val
        
        if env_val := os.getenv("MCP_EMBEDDING_OPENAI_MODEL"):
            settings.embedding.openai_model = env_val
        
        if env_val := os.getenv("MCP_EMBEDDING_HUGGINGFACE_MODEL"):
            settings.embedding.huggingface_model = env_val
        
        # MCP server overrides
        if env_val := os.getenv("MCP_HOST"):
            settings.mcp.host = env_val
        
        if env_val := os.getenv("MCP_PORT"):
            settings.mcp.port = int(env_val)
        
        if env_val := os.getenv("MCP_DEBUG"):
            settings.mcp.debug = env_val.lower() in ("true", "1", "yes")
            settings.debug = settings.mcp.debug
        
        if env_val := os.getenv("MCP_LOG_LEVEL"):
            settings.mcp.log_level = env_val.upper()
        
        # App overrides
        if env_val := os.getenv("MCP_DATA_DIR"):
            settings.data_dir = env_val
        
        if env_val := os.getenv("MCP_LOGS_DIR"):
            settings.logs_dir = env_val
        
        if env_val := os.getenv("MCP_CACHE_DIR"):
            settings.cache_dir = env_val
        
        return settings
    
    def export_env_template(self, output_path: Optional[Union[str, Path]] = None) -> None:
        """Export environment variable template.
        
        Args:
            output_path: Path to save template file
        """
        if output_path is None:
            output_path = Path(".env.template")
        
        template_content = '''# MCP DevAgent Environment Configuration

# Environment
MCP_ENVIRONMENT=development
MCP_DEBUG=true

# Server Configuration
MCP_HOST=localhost
MCP_PORT=8000
MCP_LOG_LEVEL=INFO

# Database Configuration
MCP_DATABASE_PATH=./data/mcp_devagent.db
MCP_DATABASE_MAX_CONNECTIONS=10
MCP_DATABASE_VSS_DIMENSION=384

# LLM Configuration
MCP_LLM_DEFAULT_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
MCP_LLM_OPENAI_MODEL=gpt-4
MCP_LLM_ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Embedding Configuration
MCP_EMBEDDING_DEFAULT_PROVIDER=openai
MCP_EMBEDDING_OPENAI_MODEL=text-embedding-3-small
MCP_EMBEDDING_HUGGINGFACE_MODEL=sentence-transformers/all-MiniLM-L6-v2

# Directory Configuration
MCP_DATA_DIR=./data
MCP_LOGS_DIR=./logs
MCP_CACHE_DIR=./cache
'''
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
    
    def export_config_template(self, output_path: Optional[Union[str, Path]] = None) -> None:
        """Export configuration file template.
        
        Args:
            output_path: Path to save template file
        """
        if output_path is None:
            self.config_dir.mkdir(exist_ok=True)
            output_path = self.config_dir / "default.yaml"
        
        # Create default settings and convert to dict
        default_settings = Settings()
        config_dict = default_settings.to_dict()
        
        # Save as YAML template
        self.save_config_file(config_dict, output_path)
    
    def get_env_info(self) -> Dict[str, Any]:
        """Get environment information.
        
        Returns:
            Environment information dictionary
        """
        return {
            "environment": self.env_name,
            "config_dir": str(self.config_dir),
            "env_file": str(self.env_file),
            "env_file_exists": self.env_file.exists(),
            "config_files": {
                "yaml": (self.config_dir / f"{self.env_name}.yaml").exists(),
                "json": (self.config_dir / f"{self.env_name}.json").exists(),
                "default_yaml": (self.config_dir / "default.yaml").exists(),
                "default_json": (self.config_dir / "default.json").exists()
            },
            "env_vars": {
                "MCP_ENVIRONMENT": os.getenv("MCP_ENVIRONMENT"),
                "MCP_DEBUG": os.getenv("MCP_DEBUG"),
                "MCP_HOST": os.getenv("MCP_HOST"),
                "MCP_PORT": os.getenv("MCP_PORT"),
                "OPENAI_API_KEY": "***" if os.getenv("OPENAI_API_KEY") else None,
                "ANTHROPIC_API_KEY": "***" if os.getenv("ANTHROPIC_API_KEY") else None
            }
        }


def get_settings(env_name: Optional[str] = None) -> Settings:
    """Get configured settings instance.
    
    Args:
        env_name: Environment name
        
    Returns:
        Configured Settings instance
    """
    env = Environment(env_name)
    return env.create_settings()


def validate_environment() -> Dict[str, Any]:
    """Validate current environment configuration.
    
    Returns:
        Validation results
    """
    env = Environment()
    settings = env.create_settings()
    
    validation_errors = settings.validate()
    env_info = env.get_env_info()
    
    return {
        "valid": len(validation_errors) == 0,
        "errors": validation_errors,
        "environment_info": env_info,
        "settings_summary": {
            "environment": settings.environment,
            "debug": settings.debug,
            "database_path": settings.database.db_path,
            "llm_provider": settings.llm.default_provider,
            "embedding_provider": settings.embedding.default_provider,
            "mcp_host": settings.mcp.host,
            "mcp_port": settings.mcp.port
        }
    }