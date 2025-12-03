from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Union
from datetime import timedelta

class BaseCache(ABC):
    """Abstract base class for all cache implementations."""

    @abstractmethod
    def get(self, key: str) -> Any:
        """Retrieve an item from the cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> None:
        """Set an item in the cache with an optional TTL."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete an item from the cache."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all items from the cache."""
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close the cache connection/resources."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        pass
