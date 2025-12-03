class CacheError(Exception):
    pass

class CacheConfigurationError(CacheError):
    pass

class BackendConnectionError(CacheError):
    pass
