class CacheError(Exception):
    """Base exception for cache errors."""
    pass

class CacheConfigurationError(CacheError):
    """Raised when cache configuration is invalid."""
    pass

class BackendConnectionError(CacheError):
    """Raised when connection to cache backend fails."""
    pass
