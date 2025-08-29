"""Configuration module for TimeMaster"""
import os
from typing import Optional
from datetime import datetime


class TimeMasterConfig:
    """Configuration class for TimeMaster with environment variable support"""

    # Default configuration values
    DEFAULT_API_ENDPOINT = "http://worldtimeapi.org/api"
    DEFAULT_TIMEOUT = 3  # seconds
    DEFAULT_CACHE_TTL = 2  # seconds
    DEFAULT_LOG_LEVEL = "INFO"
    
    # New v0.1.2 configuration defaults
    DEFAULT_OFFLINE_MODE = False
    DEFAULT_AUTO_TIMEZONE = True
    DEFAULT_TIMEZONE = "UTC"
    DEFAULT_TIMEZONE_CACHE_TTL = 86400  # 24 hours
    DEFAULT_HOLIDAY_CACHE_TTL = 604800  # 7 days
    DEFAULT_NETWORK_TIMEOUT = 5  # seconds
    DEFAULT_CACHE_SIZE = 10000
    DEFAULT_FILE_CACHE_ENABLED = False

    # Environment variable mappings
    ENV_MAPPING = {
        "TIMEMASTER_OFFLINE_MODE": "offline_mode",
        "TIMEMASTER_AUTO_TIMEZONE": "auto_timezone",
        "TIMEMASTER_DEFAULT_TIMEZONE": "default_timezone",
        "TIMEMASTER_TIMEZONE_CACHE_TTL": "timezone_cache_ttl",
        "TIMEMASTER_HOLIDAY_CACHE_TTL": "holiday_cache_ttl",
        "TIMEMASTER_NETWORK_TIMEOUT": "network_timeout",
        "TIMEMASTER_LOG_LEVEL": "log_level",
        "TIMEMASTER_CACHE_SIZE": "cache_size",
        "TIMEMASTER_FILE_CACHE_ENABLED": "file_cache_enabled",
        "TIMEMASTER_API_ENDPOINTS": "api_endpoints"
    }

    def __init__(self):
        # Legacy configuration
        self.api_endpoint = self.DEFAULT_API_ENDPOINT
        self.timeout = self.DEFAULT_TIMEOUT
        self.cache_ttl = self.DEFAULT_CACHE_TTL
        self.log_level = self.DEFAULT_LOG_LEVEL
        
        # New v0.1.2 configuration
        self.offline_mode = self.DEFAULT_OFFLINE_MODE
        self.auto_timezone = self.DEFAULT_AUTO_TIMEZONE
        self.default_timezone = self.DEFAULT_TIMEZONE
        self.timezone_cache_ttl = self.DEFAULT_TIMEZONE_CACHE_TTL
        self.holiday_cache_ttl = self.DEFAULT_HOLIDAY_CACHE_TTL
        self.network_timeout = self.DEFAULT_NETWORK_TIMEOUT
        self.cache_size = self.DEFAULT_CACHE_SIZE
        self.file_cache_enabled = self.DEFAULT_FILE_CACHE_ENABLED
        self.api_endpoints = [self.DEFAULT_API_ENDPOINT]
        
        # Runtime state
        self.detected_timezone: Optional[str] = None
        self.network_available: bool = True
        self.last_network_check: Optional[datetime] = None
        
        # Load from environment variables
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration from environment variables"""
        for env_var, attr_name in self.ENV_MAPPING.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    # Convert string values to appropriate types
                    if attr_name in ['offline_mode', 'auto_timezone', 'file_cache_enabled']:
                        value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif attr_name in ['timezone_cache_ttl', 'holiday_cache_ttl', 'network_timeout', 'cache_size']:
                        value = int(env_value)
                    elif attr_name == 'api_endpoints':
                        value = [endpoint.strip() for endpoint in env_value.split(',')]
                    else:
                        value = env_value
                    
                    setattr(self, attr_name, value)
                except (ValueError, TypeError) as e:
                    # Log warning but continue with default value
                    print(f"Warning: Invalid value for {env_var}: {env_value}. Using default. Error: {e}")

    def update(self, **kwargs):
        """Update configuration values"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
    def is_offline_mode(self) -> bool:
        """Check if offline mode is enabled"""
        return self.offline_mode
        
    def should_auto_detect_timezone(self) -> bool:
        """Check if automatic timezone detection is enabled"""
        return self.auto_timezone
        
    def get_timezone_cache_ttl(self) -> int:
        """Get timezone cache TTL in seconds"""
        return self.timezone_cache_ttl
        
    def get_holiday_cache_ttl(self) -> int:
        """Get holiday cache TTL in seconds"""
        return self.holiday_cache_ttl
