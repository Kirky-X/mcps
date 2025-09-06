"""Configuration settings for MCP DevAgent.

Defines configuration classes for database, LLM providers, embedding services,
and other system components.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    
    # Database file path
    db_path: str = "./data/mcp_devagent.db"
    
    # Connection pool settings
    max_connections: int = 10
    connection_timeout: int = 30
    
    # SQLite-specific settings
    enable_wal_mode: bool = True
    enable_foreign_keys: bool = True
    
    # FTS5 settings
    fts_tokenizer: str = "unicode61"
    fts_remove_diacritics: bool = True
    
    # VSS settings
    vss_dimension: int = 384  # Default for sentence-transformers
    vss_metric: str = "cosine"  # cosine, l2, ip
    
    # Backup settings
    auto_backup: bool = True
    backup_interval_hours: int = 24
    max_backup_files: int = 7
    
    def __post_init__(self):
        """Validate and normalize configuration."""
        # Ensure database directory exists
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate VSS settings
        if self.vss_dimension <= 0:
            raise ValueError("VSS dimension must be positive")
        
        if self.vss_metric not in ["cosine", "l2", "ip"]:
            raise ValueError(f"Invalid VSS metric: {self.vss_metric}")


@dataclass
class LLMConfig:
    """LLM provider configuration settings."""
    
    # Provider settings
    default_provider: str = "openai"
    enabled_providers: List[str] = field(default_factory=lambda: ["openai", "anthropic"])
    
    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 4000
    openai_temperature: float = 0.1
    openai_timeout: int = 60
    
    # Anthropic settings
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    anthropic_max_tokens: int = 4000
    anthropic_temperature: float = 0.1
    anthropic_timeout: int = 60
    
    # Retry and rate limiting
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_requests_per_minute: int = 60
    
    # Performance monitoring
    enable_metrics: bool = True
    log_requests: bool = False
    
    def __post_init__(self):
        """Load API keys from environment if not provided."""
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Validate default provider
        if self.default_provider not in self.enabled_providers:
            raise ValueError(f"Default provider {self.default_provider} not in enabled providers")


@dataclass
class EmbeddingConfig:
    """Embedding service configuration settings."""
    
    # Provider settings
    default_provider: str = "openai"
    enabled_providers: List[str] = field(default_factory=lambda: ["openai", "huggingface"])
    
    # OpenAI embeddings
    openai_api_key: Optional[str] = None
    openai_model: str = "text-embedding-3-small"
    openai_dimensions: int = 384
    openai_timeout: int = 30
    
    # HuggingFace embeddings
    huggingface_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    huggingface_device: str = "cpu"  # cpu, cuda, mps
    huggingface_batch_size: int = 32
    
    # Caching settings
    enable_cache: bool = True
    cache_ttl_hours: int = 24
    max_cache_size_mb: int = 100
    
    # Performance settings
    max_batch_size: int = 100
    max_text_length: int = 8000
    
    # Retry settings
    max_retries: int = 3
    retry_delay: float = 1.0
    
    def __post_init__(self):
        """Load API keys from environment if not provided."""
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Validate default provider
        if self.default_provider not in self.enabled_providers:
            raise ValueError(f"Default provider {self.default_provider} not in enabled providers")
        
        # Validate dimensions
        if self.openai_dimensions <= 0:
            raise ValueError("OpenAI dimensions must be positive")


@dataclass
class SearchConfig:
    """Search engine configuration settings."""
    
    # Hybrid search weights
    fts_weight: float = 0.6
    vss_weight: float = 0.4
    
    # Search limits
    default_limit: int = 20
    max_limit: int = 100
    
    # FTS settings
    fts_min_score: float = 0.1
    fts_boost_exact_match: float = 1.5
    fts_boost_phrase_match: float = 1.2
    
    # VSS settings
    vss_min_similarity: float = 0.3
    vss_similarity_threshold: float = 0.7
    
    # Result merging
    enable_deduplication: bool = True
    dedup_similarity_threshold: float = 0.9
    boost_hybrid_matches: float = 1.3
    
    # Performance
    enable_query_cache: bool = True
    cache_ttl_minutes: int = 30
    
    def __post_init__(self):
        """Validate search configuration."""
        if self.fts_weight + self.vss_weight != 1.0:
            raise ValueError("FTS and VSS weights must sum to 1.0")
        
        if self.default_limit > self.max_limit:
            raise ValueError("Default limit cannot exceed max limit")


@dataclass
class MCPConfig:
    """MCP server configuration settings."""
    
    # Server settings
    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    
    # CORS settings
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE"])
    cors_headers: List[str] = field(default_factory=lambda: ["*"])
    
    # Request limits
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    request_timeout: int = 300  # 5 minutes
    
    # Logging
    log_level: str = "INFO"
    log_requests: bool = True
    log_responses: bool = False
    
    # Development features
    enable_development_endpoints: bool = True
    enable_metrics_endpoint: bool = True
    enable_health_check: bool = True
    
    def __post_init__(self):
        """Validate MCP configuration."""
        if not (1 <= self.port <= 65535):
            raise ValueError("Port must be between 1 and 65535")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {self.log_level}")


@dataclass
class Settings:
    """Main application settings container."""
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    
    # Environment settings
    environment: str = "development"  # development, staging, production
    debug: bool = True
    
    # Application metadata
    app_name: str = "MCP DevAgent"
    app_version: str = "0.1.0"
    
    # Data directories
    data_dir: str = "./data"
    logs_dir: str = "./logs"
    cache_dir: str = "./cache"
    
    def __post_init__(self):
        """Initialize settings and create directories."""
        # Create required directories
        for dir_path in [self.data_dir, self.logs_dir, self.cache_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # Update database path to use data directory
        if not os.path.isabs(self.database.db_path):
            self.database.db_path = os.path.join(self.data_dir, "mcp_devagent.db")
        
        # Environment-specific adjustments
        if self.environment == "production":
            self.debug = False
            self.mcp.debug = False
            self.llm.log_requests = False
            self.mcp.log_responses = False
        elif self.environment == "development":
            self.debug = True
            self.mcp.debug = True
            self.llm.log_requests = True
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables."""
        settings = cls()
        
        # Override with environment variables
        if env_val := os.getenv("MCP_ENVIRONMENT"):
            settings.environment = env_val
        
        if env_val := os.getenv("MCP_DEBUG"):
            settings.debug = env_val.lower() in ("true", "1", "yes")
        
        if env_val := os.getenv("MCP_HOST"):
            settings.mcp.host = env_val
        
        if env_val := os.getenv("MCP_PORT"):
            settings.mcp.port = int(env_val)
        
        if env_val := os.getenv("MCP_DATABASE_PATH"):
            settings.database.db_path = env_val
        
        # LLM settings
        if env_val := os.getenv("MCP_LLM_DEFAULT_PROVIDER"):
            settings.llm.default_provider = env_val
        
        if env_val := os.getenv("OPENAI_API_KEY"):
            settings.llm.openai_api_key = env_val
            settings.embedding.openai_api_key = env_val
        
        if env_val := os.getenv("ANTHROPIC_API_KEY"):
            settings.llm.anthropic_api_key = env_val
        
        # Embedding settings
        if env_val := os.getenv("MCP_EMBEDDING_DEFAULT_PROVIDER"):
            settings.embedding.default_provider = env_val
        
        if env_val := os.getenv("MCP_EMBEDDING_MODEL"):
            if settings.embedding.default_provider == "openai":
                settings.embedding.openai_model = env_val
            elif settings.embedding.default_provider == "huggingface":
                settings.embedding.huggingface_model = env_val
        
        return settings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "database": {
                "db_path": self.database.db_path,
                "max_connections": self.database.max_connections,
                "enable_wal_mode": self.database.enable_wal_mode,
                "vss_dimension": self.database.vss_dimension,
                "vss_metric": self.database.vss_metric
            },
            "llm": {
                "default_provider": self.llm.default_provider,
                "enabled_providers": self.llm.enabled_providers,
                "openai_model": self.llm.openai_model,
                "anthropic_model": self.llm.anthropic_model,
                "max_retries": self.llm.max_retries
            },
            "embedding": {
                "default_provider": self.embedding.default_provider,
                "enabled_providers": self.embedding.enabled_providers,
                "openai_model": self.embedding.openai_model,
                "huggingface_model": self.embedding.huggingface_model,
                "max_batch_size": self.embedding.max_batch_size
            },
            "search": {
                "fts_weight": self.search.fts_weight,
                "vss_weight": self.search.vss_weight,
                "default_limit": self.search.default_limit,
                "enable_deduplication": self.search.enable_deduplication
            },
            "mcp": {
                "host": self.mcp.host,
                "port": self.mcp.port,
                "debug": self.mcp.debug,
                "log_level": self.mcp.log_level
            },
            "app": {
                "name": self.app_name,
                "version": self.app_version,
                "environment": self.environment,
                "debug": self.debug
            }
        }
    
    def validate(self) -> List[str]:
        """Validate all configuration settings."""
        errors = []
        
        # Check required API keys for enabled providers
        if "openai" in self.llm.enabled_providers and not self.llm.openai_api_key:
            errors.append("OpenAI API key required for LLM service")
        
        if "anthropic" in self.llm.enabled_providers and not self.llm.anthropic_api_key:
            errors.append("Anthropic API key required for LLM service")
        
        if "openai" in self.embedding.enabled_providers and not self.embedding.openai_api_key:
            errors.append("OpenAI API key required for embedding service")
        
        # Check database path is writable
        db_dir = Path(self.database.db_path).parent
        if not db_dir.exists() or not os.access(db_dir, os.W_OK):
            errors.append(f"Database directory not writable: {db_dir}")
        
        # Check data directories
        for dir_name, dir_path in [("data", self.data_dir), ("logs", self.logs_dir), ("cache", self.cache_dir)]:
            if not os.access(dir_path, os.W_OK):
                errors.append(f"{dir_name} directory not writable: {dir_path}")
        
        return errors


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance.
    
    Returns:
        Settings: The global settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance.
    
    This is mainly used for testing purposes.
    """
    global _settings
    _settings = None