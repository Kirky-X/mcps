"""Database connection management for MCP-DevAgent.

This module provides database connection pooling, session management,
and async database operations.
"""

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import aiosqlite
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ..config import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize the database manager.
        
        Args:
            database_url: Optional database URL override
        """
        self.settings = get_settings()
        if database_url:
            self.database_url = database_url
        else:
            # Construct database URL from db_path
            db_path = self.settings.database.db_path
            self.database_url = f"sqlite+aiosqlite:///{db_path}"
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None
        self._connection_pool_size = getattr(self.settings, 'database_pool_size', 10)
        self._max_overflow = getattr(self.settings, 'database_max_overflow', 20)
    
    async def initialize(self) -> None:
        """Initialize the database engine and session factory."""
        if self._engine is not None:
            logger.warning("Database manager already initialized")
            return
        
        logger.info(f"Initializing database connection to: {self.database_url}")
        
        # Configure engine parameters
        engine_kwargs = {
            "echo": self.settings.debug,
            "future": True,
        }
        
        # SQLite-specific configuration
        if "sqlite" in self.database_url:
            engine_kwargs.update({
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 30,
                },
            })
        else:
            # For other databases (PostgreSQL, MySQL, etc.)
            engine_kwargs.update({
                "pool_size": self._connection_pool_size,
                "max_overflow": self._max_overflow,
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            })
        
        # Create async engine
        self._engine = create_async_engine(self.database_url, **engine_kwargs)
        
        # Create session factory
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )
        
        # Set up event listeners for SQLite
        if "sqlite" in self.database_url:
            self._setup_sqlite_events()
        
        logger.info("Database manager initialized successfully")
    
    def _setup_sqlite_events(self) -> None:
        """Set up SQLite-specific event listeners."""
        @event.listens_for(self._engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas for performance and reliability."""
            cursor = dbapi_connection.cursor()
            
            # Performance settings
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
            
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")
            
            # Enable query optimization
            cursor.execute("PRAGMA optimize")
            
            cursor.close()
    
    async def close(self) -> None:
        """Close the database engine and all connections."""
        if self._engine is not None:
            logger.info("Closing database connections")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
    
    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine.
        
        Returns:
            The async database engine
            
        Raises:
            RuntimeError: If the manager is not initialized
        """
        if self._engine is None:
            raise RuntimeError("Database manager not initialized. Call initialize() first.")
        return self._engine
    
    @property
    def session_factory(self) -> async_sessionmaker:
        """Get the session factory.
        
        Returns:
            The async session factory
            
        Raises:
            RuntimeError: If the manager is not initialized
        """
        if self._session_factory is None:
            raise RuntimeError("Database manager not initialized. Call initialize() first.")
        return self._session_factory
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with automatic cleanup.
        
        Yields:
            An async database session
        """
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    @asynccontextmanager
    async def get_raw_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Get a raw SQLite connection for direct operations.
        
        This is useful for operations that require direct SQLite access,
        such as FTS5 and VSS operations.
        
        Yields:
            A raw aiosqlite connection
        """
        if "sqlite" not in self.database_url:
            raise RuntimeError("Raw connections are only supported for SQLite databases")
        
        # Extract database path from URL
        if self.database_url.startswith("sqlite+aiosqlite:///"):
            db_path = self.database_url[20:]  # Remove 'sqlite+aiosqlite:///'
        elif self.database_url.startswith("sqlite:///"):
            db_path = self.database_url[10:]  # Remove 'sqlite:///'
        else:
            raise ValueError(f"Unsupported SQLite URL format: {self.database_url}")
        
        # Convert relative path to absolute path
        import os
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)
        
        async with aiosqlite.connect(db_path) as conn:
            # Set up SQLite pragmas
            await conn.execute("PRAGMA foreign_keys=ON")
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            
            try:
                # Try to load VSS extension
                await conn.enable_load_extension(True)
                await conn.load_extension("vss0")
            except Exception as e:
                logger.debug(f"VSS extension not available: {e}")
            
            yield conn
    
    async def health_check(self) -> bool:
        """Perform a health check on the database connection.
        
        Returns:
            True if the database is healthy, False otherwise
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                result.fetchone()
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def get_connection_info(self) -> dict:
        """Get information about the current database connection.
        
        Returns:
            Dictionary containing connection information
        """
        info = {
            "database_url": self.database_url,
            "engine_initialized": self._engine is not None,
            "pool_size": self._connection_pool_size,
            "max_overflow": self._max_overflow,
        }
        
        if self._engine is not None:
            pool = self._engine.pool
            info.update({
                "pool_checked_in": pool.checkedin(),
                "pool_checked_out": pool.checkedout(),
                "pool_overflow": pool.overflow(),
                "pool_invalid": pool.invalid(),
            })
        
        return info
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a synchronous SQLite connection for compatibility.
        
        Returns:
            A synchronous SQLite connection
        """
        return get_db_connection()
    
    def cleanup(self) -> None:
        """Cleanup database resources (synchronous wrapper for compatibility)."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, schedule the cleanup
                asyncio.create_task(self.close())
            else:
                # If we're not in an async context, run it
                asyncio.run(self.close())
        except RuntimeError:
            # No event loop, run directly
            asyncio.run(self.close())


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


async def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance.
    
    Returns:
        The global database manager
    """
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager()
        await _db_manager.initialize()
    
    return _db_manager


async def close_database_manager() -> None:
    """Close the global database manager."""
    global _db_manager
    
    if _db_manager is not None:
        await _db_manager.close()
        _db_manager = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session from the global manager.
    
    Yields:
        An async database session
    """
    manager = await get_database_manager()
    async with manager.get_session() as session:
        yield session


@asynccontextmanager
async def get_raw_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Get a raw database connection from the global manager.
    
    Yields:
        A raw aiosqlite connection
    """
    manager = await get_database_manager()
    async with manager.get_raw_connection() as conn:
        yield conn


async def db_health_check() -> bool:
    """Perform a health check on the global database manager.
    
    Returns:
        True if the database is healthy, False otherwise
    """
    try:
        manager = await get_database_manager()
        return await manager.health_check()
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


# Context manager for database lifecycle
@asynccontextmanager
async def database_lifespan():
    """Context manager for database lifecycle management.
    
    Use this in FastAPI lifespan events or similar contexts.
    """
    try:
        # Initialize database manager
        await get_database_manager()
        logger.info("Database manager started")
        yield
    finally:
        # Clean up database manager
        await close_database_manager()
        logger.info("Database manager stopped")


def get_db_connection() -> sqlite3.Connection:
    """Get a synchronous SQLite database connection.
    
    This function is provided for compatibility with synchronous code
    that needs direct database access.
    
    Returns:
        A synchronous SQLite connection
    """
    settings = get_settings()
    db_path = settings.database.db_path
    
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
    
    # Set up SQLite pragmas for performance and reliability
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA optimize")
    cursor.close()
    
    return conn


# Synchronous SessionLocal for compatibility with existing tests
def create_sync_session_factory():
    """Create a synchronous session factory for compatibility.
    
    Returns:
        A synchronous SQLAlchemy session factory
    """
    settings = get_settings()
    db_path = settings.database.db_path
    sync_database_url = f"sqlite:///{db_path}"
    
    # Create synchronous engine
    sync_engine = create_engine(
        sync_database_url,
        echo=settings.debug,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },
    )
    
    # Set up SQLite pragmas
    @event.listens_for(sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA optimize")
        cursor.close()
    
    return sessionmaker(bind=sync_engine, autoflush=True, autocommit=False)


# Global synchronous session factory
_sync_session_factory = None


def get_sync_session_factory():
    """Get or create the global synchronous session factory."""
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = create_sync_session_factory()
    return _sync_session_factory


# SessionLocal for compatibility with existing test code
SessionLocal = get_sync_session_factory()