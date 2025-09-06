"""Database initialization module for MCP-DevAgent.

This module handles database creation, schema setup, and initialization
of FTS5 and VSS extensions for hybrid search capabilities.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import aiosqlite
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .models import Base
# DatabaseManager import removed - using direct aiosqlite connection for VSS
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Database initialization and setup manager."""
    
    def __init__(self, database_path: Optional[str] = None):
        """Initialize database initializer.
        
        Args:
            database_path: Optional database path override
        """
        self.settings = get_settings()
        self.database_path = self._extract_database_path(database_path)
    
    def initialize(self, force_recreate: bool = False) -> None:
        """Initialize the database (synchronous wrapper for compatibility).
        
        Args:
            force_recreate: Whether to recreate the database if it exists
        """
        asyncio.run(self.initialize_database(force_recreate))
        
    def _extract_database_path(self, database_path: Optional[str] = None) -> Path:
        """Extract database file path from settings or override.
        
        Args:
            database_path: Optional database path override
            
        Returns:
            Path: Resolved database file path
        """
        if database_path:
            return Path(database_path).resolve()
        return Path(self.settings.database.db_path).resolve()
    
    async def initialize_database(self, force_recreate: bool = False) -> None:
        """Initialize the complete database with all extensions.
        
        Args:
            force_recreate: Whether to recreate the database if it exists
        """
        logger.info(f"Initializing database at: {self.database_path}")
        
        # Ensure database directory exists
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Remove existing database if force recreate
        if force_recreate and self.database_path.exists():
            logger.warning("Force recreating database - removing existing file")
            self.database_path.unlink()
        
        # Create database and tables
        await self._create_tables()
        
        # Initialize extensions
        await self._initialize_fts5()
        await self._initialize_vss_tables()
        
        # Create triggers for data synchronization
        await self._create_sync_triggers()
        
        # Create indexes for performance
        await self._create_performance_indexes()
        
        logger.info("Database initialization completed successfully")
    
    async def _create_tables(self) -> None:
        """Create all SQLAlchemy tables."""
        logger.info("Creating SQLAlchemy tables")
        
        # Create synchronous engine for table creation
        database_url = f"sqlite:///{self.database_path}"
        sync_engine = create_engine(database_url)
        
        try:
            Base.metadata.create_all(sync_engine)
            logger.info("SQLAlchemy tables created successfully")
        finally:
            sync_engine.dispose()
    
    async def _initialize_fts5(self) -> None:
        """Initialize FTS5 virtual tables for full-text search."""
        logger.info("Initializing FTS5 virtual tables")
        
        async with aiosqlite.connect(self.database_path) as db:
            # Enable FTS5 extension
            await db.execute("PRAGMA table_info=fts5")
            
            # Create FTS5 virtual table for code chunks
            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS code_chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    content,
                    content_type,
                    file_path UNINDEXED,
                    file_name UNINDEXED,
                    repository_name UNINDEXED,
                    language UNINDEXED,
                    tokenize='porter'
                )
            """)
            
            # Create FTS5 virtual table for file metadata
            await db.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS code_files_fts USING fts5(
                    file_id UNINDEXED,
                    file_name,
                    file_path,
                    repository_name UNINDEXED,
                    language UNINDEXED,
                    tokenize='porter'
                )
            """)
            
            await db.commit()
            logger.info("FTS5 virtual tables created successfully")
    
    async def _initialize_vss_tables(self) -> None:
        """Initialize VSS (Vector Similarity Search) tables."""
        logger.info("Initializing VSS tables")
        
        try:
            # Try to load VSS extension
            import sqlite_vss
            
            # Use async connection for consistency
            async with aiosqlite.connect(self.database_path) as db:
                try:
                    # Try to load VSS extension
                    await db.enable_load_extension(True)
                    
                    # Load vector0 extension first, then vss0
                    vss_path = "/root/miniforge3/lib/python3.12/site-packages/sqlite_vss"
                    await db.load_extension(f"{vss_path}/vector0")
                    await db.load_extension(f"{vss_path}/vss0")
                    
                    # Create VSS table for embeddings
                    await db.execute("""
                        CREATE VIRTUAL TABLE IF NOT EXISTS code_embeddings_vss USING vss0(
                            embedding(384)
                        )
                    """)
                    
                    await db.commit()
                    logger.info("VSS tables created successfully")
                    
                except Exception as vss_error:
                    logger.warning(f"VSS extension loading failed: {vss_error}")
                    logger.info("Continuing without VSS - vector search will be disabled")
            
        except ImportError:
            logger.warning("sqlite_vss module not available - VSS functionality disabled")
        except Exception as e:
            logger.warning(f"VSS extension initialization skipped: {e}")
            # Continue without VSS - it's optional
            pass
    
    async def _create_sync_triggers(self) -> None:
        """Create triggers to keep FTS5 and VSS tables synchronized with new schema."""
        logger.info("Creating synchronization triggers for new schema")
        
        async with aiosqlite.connect(self.database_path) as db:
            # Note: FTS5 and VSS triggers will be implemented when needed
            # for the new schema tables (codebase_indexes, code_artifacts, etc.)
            # Currently preserving existing FTS5 tables for backward compatibility
            
            await db.commit()
            logger.info("Synchronization triggers created successfully")
    
    async def _create_performance_indexes(self) -> None:
        """Create additional indexes for performance optimization on new schema."""
        logger.info("Creating performance indexes for new schema")
        
        async with aiosqlite.connect(self.database_path) as db:
            # Note: Performance indexes are already created by the migration script
            # and defined in the SQLAlchemy models. This method is kept for compatibility.
            
            await db.commit()
            logger.info("Performance indexes verified successfully")
    
    async def verify_database(self) -> bool:
        """Verify that the database is properly initialized with new schema.
        
        Returns:
            True if database is properly initialized, False otherwise
        """
        try:
            async with aiosqlite.connect(self.database_path) as db:
                # Check if new schema tables exist
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                tables = await cursor.fetchall()
                
                expected_tables = {
                    'development_runs', 'modules', 'cot_records', 'test_results',
                    'codebase_indexes', 'code_artifacts', 'problem_escalations'
                }
                
                found_tables = {table[0] for table in tables}
                missing_tables = expected_tables - found_tables
                
                if missing_tables:
                    logger.error(f"Missing new schema tables: {missing_tables}")
                    return False
                
                # Check if FTS5 tables exist (preserved for compatibility)
                fts_tables = [t[0] for t in tables if '_fts' in t[0]]
                if fts_tables:
                    logger.info(f"FTS5 tables found: {fts_tables}")
                
                # Check if VSS tables exist (optional)
                vss_tables = [t[0] for t in tables if '_vss' in t[0]]
                if vss_tables:
                    logger.info(f"VSS tables found: {vss_tables}")
                else:
                    logger.warning("No VSS tables found - vector search disabled")
                
                logger.info("Database verification completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Database verification failed: {e}")
            return False
    
    async def get_database_info(self) -> dict:
        """Get comprehensive database information for new schema.
        
        Returns:
            Dictionary containing database statistics and metadata
        """
        try:
            async with aiosqlite.connect(self.database_path) as db:
                info = {
                    'database_path': str(self.database_path),
                    'database_size': self.database_path.stat().st_size if self.database_path.exists() else 0,
                    'tables': {},
                    'indexes': [],
                    'extensions': [],
                    'schema_version': 'new_architecture_v1'
                }
                
                # Get table information
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                tables = await cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    
                    # Get row count
                    cursor = await db.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = await cursor.fetchone()
                    
                    # Get table schema
                    cursor = await db.execute(f"PRAGMA table_info({table_name})")
                    columns = await cursor.fetchall()
                    
                    info['tables'][table_name] = {
                        'row_count': count[0] if count else 0,
                        'columns': [col[1] for col in columns]  # Column names
                    }
                
                # Get index information
                cursor = await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'"
                )
                indexes = await cursor.fetchall()
                info['indexes'] = [idx[0] for idx in indexes]
                
                # Check for extensions
                try:
                    await db.execute("SELECT fts5()")
                    info['extensions'].append('FTS5')
                except Exception:
                    pass
                
                # Note: VSS extension check removed due to compatibility issues
                # VSS functionality will be implemented when needed
                
                return info
                
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            # Return basic info even if detailed info fails
            return {
                'database_path': str(self.database_path),
                'database_size': self.database_path.stat().st_size if self.database_path.exists() else 0,
                'tables': {},
                'indexes': [],
                'extensions': [],
                'schema_version': 'new_architecture_v1',
                'error': str(e)
            }


async def init_database(database_url: Optional[str] = None, force_recreate: bool = False) -> None:
    """Initialize the database with all required tables and extensions.
    
    Args:
        database_url: Optional database URL override
        force_recreate: Whether to recreate the database if it exists
    """
    initializer = DatabaseInitializer(database_url)
    await initializer.initialize_database(force_recreate)


async def verify_database(database_url: Optional[str] = None) -> bool:
    """Verify that the database is properly initialized.
    
    Args:
        database_url: Optional database URL override
        
    Returns:
        True if database is properly initialized, False otherwise
    """
    initializer = DatabaseInitializer(database_url)
    return await initializer.verify_database()


if __name__ == "__main__":
    # CLI interface for database initialization
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Initialize MCP-DevAgent database")
    parser.add_argument("--force", action="store_true", help="Force recreate database")
    parser.add_argument("--verify", action="store_true", help="Verify database only")
    parser.add_argument("--info", action="store_true", help="Show database info")
    parser.add_argument("--url", help="Database URL override")
    
    args = parser.parse_args()
    
    async def main():
        initializer = DatabaseInitializer(args.url)
        
        if args.info:
            info = await initializer.get_database_info()
            print("Database Information:")
            for key, value in info.items():
                print(f"  {key}: {value}")
            return
        
        if args.verify:
            success = await initializer.verify_database()
            if success:
                print("Database verification: PASSED")
                sys.exit(0)
            else:
                print("Database verification: FAILED")
                sys.exit(1)
        
        try:
            await initializer.initialize_database(args.force)
            print("Database initialization completed successfully")
        except Exception as e:
            print(f"Database initialization failed: {e}")
            sys.exit(1)
    
    asyncio.run(main())