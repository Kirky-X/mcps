"""异常定义模块"""


class LibraryMasterError(Exception):
    """LibraryMaster基础异常"""
    pass


class LibraryNotFoundError(LibraryMasterError):
    """库未找到异常"""
    pass


class VersionNotFoundError(LibraryMasterError):
    """版本未找到异常"""
    pass


class UpstreamError(LibraryMasterError):
    """上游服务异常"""
    pass


class TimeoutError(LibraryMasterError):
    """超时异常"""
    pass


class ValidationError(LibraryMasterError):
    """验证异常"""
    pass


class CacheError(LibraryMasterError):
    """缓存异常"""
    pass