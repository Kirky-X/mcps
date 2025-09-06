"""Base Handler for MCP Protocol Operations

Provides the base class for all MCP protocol handlers.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ...database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Base class for MCP protocol handlers."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialized = False
    
    async def initialize(self):
        """Initialize the handler."""
        if self._initialized:
            return
        
        self.logger.info(f"Initializing {self.__class__.__name__}...")
        
        try:
            await self._initialize_impl()
            self._initialized = True
            self.logger.info(f"{self.__class__.__name__} initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the handler."""
        if not self._initialized:
            return
        
        self.logger.info(f"Shutting down {self.__class__.__name__}...")
        
        try:
            await self._shutdown_impl()
            self._initialized = False
            self.logger.info(f"{self.__class__.__name__} shutdown successfully")
        except Exception as e:
            self.logger.error(f"Error shutting down {self.__class__.__name__}: {e}")
    
    @abstractmethod
    async def _initialize_impl(self):
        """Implementation-specific initialization logic."""
        pass
    
    async def _shutdown_impl(self):
        """Implementation-specific shutdown logic."""
        # Default implementation does nothing
        pass
    
    def _validate_params(self, params: Dict[str, Any], required_fields: list) -> None:
        """Validate that required parameters are present."""
        missing_fields = [field for field in required_fields if field not in params]
        if missing_fields:
            raise ValueError(f"Missing required parameters: {missing_fields}")
    
    def _get_param(self, params: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Get parameter value with optional default."""
        return params.get(key, default)
    
    async def _execute_with_error_handling(self, operation_name: str, operation_func, *args, **kwargs) -> Any:
        """Execute operation with standardized error handling."""
        try:
            self.logger.debug(f"Executing {operation_name}...")
            result = await operation_func(*args, **kwargs)
            self.logger.debug(f"{operation_name} completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Error in {operation_name}: {e}")
            raise
    
    def _format_response(self, data: Any, status: str = "success", message: Optional[str] = None) -> Dict[str, Any]:
        """Format standardized response."""
        response = {
            "status": status,
            "data": data
        }
        
        if message:
            response["message"] = message
        
        return response
    
    def _format_error_response(self, error: str, code: Optional[str] = None) -> Dict[str, Any]:
        """Format standardized error response."""
        response = {
            "status": "error",
            "error": error
        }
        
        if code:
            response["error_code"] = code
        
        return response