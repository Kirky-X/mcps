"""
TimeMaster MCP - A canonical, high-reliability, developer-first modular common component
for handling timezones and time in Python.
"""

from .config import TimeMasterConfig
from .core import TimeMaster
from .exceptions import TimeMasterError, NetworkError, TimezoneError, APIError

__all__ = [
    "TimeMaster",
    "TimeMasterError",
    "NetworkError",
    "TimezoneError",
    "APIError",
    "TimeMasterConfig",
]

__version__ = "0.1.2"
