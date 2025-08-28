"""
Custom exceptions for TimeMaster
"""


class TimeMasterError(Exception):
    """Base exception for TimeMaster errors"""

    pass


class NetworkError(TimeMasterError):
    """Raised when there are network connectivity issues"""

    pass


class TimezoneError(TimeMasterError):
    """Raised when there are timezone-related errors"""

    pass


class APIError(TimeMasterError):
    """Raised when API requests fail"""

    pass
