from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class CacheConfig(BaseSettings):
    # General
    CACHE_ENABLED: bool = True
    CACHE_PREFIX: str = "library:"
    CACHE_STRATEGY: str = "auto"
    AUTO_DETECT_REDIS: bool = True
    DEGRADE_ON_REDIS_UNAVAILABLE: bool = True
    
    # L1 - Moka/Local
    L1_ENABLED: bool = True
    L1_MAX_SIZE: int = 10000
    L1_TTL: int = 300  # 5 minutes default for local
    
    # L2 - Redis
    L2_ENABLED: bool = True
    L2_TTL: int = 3600 # 1 hour default for remote
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Sync
    CACHE_SYNC_ENABLED: bool = True
    CACHE_SYNC_CHANNEL: str = "cache_invalidation"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LIB_",
        extra="ignore"
    )
