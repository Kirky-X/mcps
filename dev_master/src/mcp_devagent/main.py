"""Main application entry point for MCP DevAgent.

Provides unified startup interface and application lifecycle management.
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI

from .config import get_settings, validate_environment
from .database import DatabaseManager
from .services import EmbeddingService, LLMService, SearchService
from .server import create_app


class MCPDevAgent:
    """Main MCP DevAgent application."""
    
    def __init__(self, config_env: Optional[str] = None):
        """Initialize MCP DevAgent application.
        
        Args:
            config_env: Configuration environment name
        """
        self.settings = get_settings(config_env)
        self.app: Optional[FastAPI] = None
        self.db_manager: Optional[DatabaseManager] = None
        self.embedding_service: Optional[EmbeddingService] = None
        self.llm_service: Optional[LLMService] = None
        self.search_service: Optional[SearchService] = None
        self._shutdown_event = asyncio.Event()
        
        # Setup logging
        self._setup_logging()
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_logging(self) -> None:
        """Setup application logging."""
        # Create logs directory
        Path(self.settings.logs_dir).mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        log_level = getattr(logging, self.settings.mcp.log_level)
        
        # File handler
        file_handler = logging.FileHandler(
            Path(self.settings.logs_dir) / "mcp_devagent.log"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # Root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Application logger
        self.logger = logging.getLogger("mcp_devagent")
        self.logger.info(f"Logging initialized - Level: {self.settings.mcp.log_level}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def initialize(self) -> None:
        """Initialize all application components."""
        self.logger.info("Initializing MCP DevAgent...")
        
        try:
            # Validate configuration
            validation_result = validate_environment()
            if not validation_result["valid"]:
                for error in validation_result["errors"]:
                    self.logger.error(f"Configuration error: {error}")
                raise RuntimeError("Invalid configuration")
            
            self.logger.info(f"Configuration validated - Environment: {self.settings.environment}")
            
            # Initialize database
            self.logger.info("Initializing database...")
            self.db_manager = DatabaseManager()
            await self.db_manager.initialize()
            self.logger.info("Database initialized successfully")
            
            # Initialize embedding service
            self.logger.info("Initializing embedding service...")
            self.embedding_service = EmbeddingService()
            from dataclasses import asdict
            await self.embedding_service.initialize(asdict(self.settings.embedding))
            self.logger.info(f"Embedding service initialized - Provider: {self.embedding_service.default_provider.name if self.embedding_service.default_provider else 'None'}")
            
            # Initialize LLM service
            self.logger.info("Initializing LLM service...")
            self.llm_service = LLMService()
            await self.llm_service.initialize(asdict(self.settings.llm))
            self.logger.info(f"LLM service initialized - Provider: {self.llm_service.default_provider.name if self.llm_service.default_provider else 'None'}")
            
            # Initialize search service
            self.logger.info("Initializing search service...")
            self.search_service = SearchService(
                self.settings.database.db_path,
                self.embedding_service
            )
            await self.search_service.hybrid_engine.initialize()
            self.logger.info("Search service initialized successfully")
            
            # Create FastAPI application
            self.logger.info("Creating FastAPI application...")
            self.app = create_app()
            self.logger.info("FastAPI application created successfully")
            
            self.logger.info("MCP DevAgent initialization completed")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MCP DevAgent: {e}")
            await self.cleanup()
            raise
    
    async def run(self) -> None:
        """Run the MCP DevAgent server."""
        if not self.app:
            raise RuntimeError("Application not initialized")
        
        self.logger.info(f"Starting MCP DevAgent server on {self.settings.mcp.host}:{self.settings.mcp.port}")
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=self.app,
            host=self.settings.mcp.host,
            port=self.settings.mcp.port,
            log_level=self.settings.mcp.log_level.lower(),
            access_log=self.settings.mcp.log_requests,
            reload=self.settings.debug and self.settings.environment == "development"
        )
        
        server = uvicorn.Server(config)
        
        # Run server with graceful shutdown
        try:
            # Start server in background task
            server_task = asyncio.create_task(server.serve())
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
            # Graceful shutdown
            self.logger.info("Shutting down server...")
            server.should_exit = True
            
            # Wait for server to stop
            await server_task
            
        except Exception as e:
            self.logger.error(f"Server error: {e}")
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """Cleanup application resources."""
        self.logger.info("Cleaning up application resources...")
        
        try:
            # Cleanup database
            if self.db_manager:
                await self.db_manager.close()
                self.logger.info("Database closed")
            
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def get_status(self) -> dict:
        """Get application status.
        
        Returns:
            Application status dictionary
        """
        return {
            "app": {
                "name": self.settings.app_name,
                "version": self.settings.app_version,
                "environment": self.settings.environment,
                "debug": self.settings.debug
            },
            "server": {
                "host": self.settings.mcp.host,
                "port": self.settings.mcp.port,
                "running": self.app is not None
            },
            "database": {
                "path": self.settings.database.db_path,
                "initialized": self.db_manager is not None and self.db_manager.is_initialized
            },
            "services": {
                "embedding": {
                    "initialized": self.embedding_service is not None and self.embedding_service.is_initialized,
                    "provider": self.embedding_service.current_provider if self.embedding_service else None
                },
                "llm": {
                    "initialized": self.llm_service is not None and self.llm_service.is_initialized,
                    "provider": self.llm_service.current_provider if self.llm_service else None
                },
                "search": {
                    "initialized": self.search_service is not None and self.search_service.is_initialized
                }
            }
        }


async def main(config_env: Optional[str] = None) -> None:
    """Main application entry point.
    
    Args:
        config_env: Configuration environment name
    """
    app = MCPDevAgent(config_env)
    
    try:
        await app.initialize()
        await app.run()
    except KeyboardInterrupt:
        app.logger.info("Received keyboard interrupt")
    except Exception as e:
        app.logger.error(f"Application error: {e}")
        sys.exit(1)


def cli_main() -> None:
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP DevAgent Server")
    parser.add_argument(
        "--env",
        type=str,
        default=None,
        help="Configuration environment (development, staging, production)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and exit"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show application status and exit"
    )
    
    args = parser.parse_args()
    
    if args.validate:
        # Validate configuration
        result = validate_environment()
        if result["valid"]:
            print("✅ Configuration is valid")
            print(f"Environment: {result['environment_info']['environment']}")
            print(f"Database: {result['settings_summary']['database_path']}")
            print(f"LLM Provider: {result['settings_summary']['llm_provider']}")
            print(f"Embedding Provider: {result['settings_summary']['embedding_provider']}")
        else:
            print("❌ Configuration errors:")
            for error in result["errors"]:
                print(f"  - {error}")
            sys.exit(1)
        return
    
    if args.status:
        # Show status
        app = MCPDevAgent(args.env)
        status = app.get_status()
        print(f"App: {status['app']['name']} v{status['app']['version']}")
        print(f"Environment: {status['app']['environment']}")
        print(f"Server: {status['server']['host']}:{status['server']['port']}")
        print(f"Database: {status['database']['path']}")
        return
    
    # Run application
    try:
        asyncio.run(main(args.env))
    except KeyboardInterrupt:
        print("\nShutdown complete")


if __name__ == "__main__":
    cli_main()