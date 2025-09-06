"""Database migration management for MCP-DevAgent.

This module provides database migration functionality, including
schema versioning, migration execution, and rollback capabilities.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

import aiosqlite
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import get_db_session, get_raw_db_connection
from .models import Base
from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class Migration:
    """Represents a single database migration."""
    
    def __init__(self, version: str, name: str, up_sql: str, down_sql: str = ""):
        """Initialize a migration.
        
        Args:
            version: Migration version (e.g., "001", "002")
            name: Human-readable migration name
            up_sql: SQL to apply the migration
            down_sql: SQL to rollback the migration
        """
        self.version = version
        self.name = name
        self.up_sql = up_sql
        self.down_sql = down_sql
        self.timestamp = datetime.utcnow()
    
    def __str__(self) -> str:
        return f"Migration {self.version}: {self.name}"
    
    def __repr__(self) -> str:
        return f"Migration(version='{self.version}', name='{self.name}')"


class MigrationManager:
    """Manages database migrations and schema versioning."""
    
    def __init__(self, migrations_dir: Optional[Path] = None):
        """Initialize the migration manager.
        
        Args:
            migrations_dir: Directory containing migration files
        """
        self.settings = get_settings()
        self.migrations_dir = migrations_dir or Path("migrations")
        self.migrations_dir.mkdir(exist_ok=True)
        self._migrations: List[Migration] = []
        self._loaded = False
    
    async def initialize(self) -> None:
        """Initialize the migration system."""
        await self._ensure_migration_table()
        await self._load_migrations()
        self._loaded = True
        logger.info(f"Migration manager initialized with {len(self._migrations)} migrations")
    
    async def _ensure_migration_table(self) -> None:
        """Ensure the migration tracking table exists."""
        async with get_raw_db_connection() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    checksum TEXT
                )
            """)
            await conn.commit()
    
    async def _load_migrations(self) -> None:
        """Load migrations from the migrations directory."""
        self._migrations.clear()
        
        # Load built-in migrations first
        self._migrations.extend(self._get_builtin_migrations())
        
        # Load file-based migrations
        if self.migrations_dir.exists():
            for migration_file in sorted(self.migrations_dir.glob("*.sql")):
                migration = await self._load_migration_file(migration_file)
                if migration:
                    self._migrations.append(migration)
        
        # Sort migrations by version
        self._migrations.sort(key=lambda m: m.version)
    
    def _get_builtin_migrations(self) -> List[Migration]:
        """Get built-in migrations for core schema."""
        return [
            Migration(
                version="001",
                name="Create core tables",
                up_sql="""
                    -- This migration is handled by SQLAlchemy create_all()
                    -- Placeholder for tracking purposes
                    SELECT 1;
                """,
                down_sql="""
                    -- Drop all tables (use with caution)
                    DROP TABLE IF EXISTS agent_interactions;
                    DROP TABLE IF EXISTS agent_sessions;
                    DROP TABLE IF EXISTS search_results;
                    DROP TABLE IF EXISTS search_queries;
                    DROP TABLE IF EXISTS search_sessions;
                    DROP TABLE IF EXISTS code_embeddings;
                    DROP TABLE IF EXISTS code_chunks;
                    DROP TABLE IF EXISTS code_files;
                    DROP TABLE IF EXISTS code_repositories;
                """
            ),
            Migration(
                version="002",
                name="Initialize FTS5 tables",
                up_sql="""
                    -- Create FTS5 virtual table for code chunks
                    CREATE VIRTUAL TABLE IF NOT EXISTS code_chunks_fts USING fts5(
                        chunk_id UNINDEXED,
                        content,
                        file_path,
                        language,
                        content='code_chunks',
                        content_rowid='id'
                    );
                    
                    -- Create FTS5 virtual table for code files
                    CREATE VIRTUAL TABLE IF NOT EXISTS code_files_fts USING fts5(
                        file_id UNINDEXED,
                        file_path,
                        file_name,
                        language,
                        content='code_files',
                        content_rowid='id'
                    );
                    
                    -- Create triggers to keep FTS5 tables in sync
                    CREATE TRIGGER IF NOT EXISTS code_chunks_fts_insert AFTER INSERT ON code_chunks
                    BEGIN
                        INSERT INTO code_chunks_fts(chunk_id, content, file_path, language)
                        VALUES (NEW.id, NEW.content, 
                               (SELECT file_path FROM code_files WHERE id = NEW.file_id),
                               NEW.language);
                    END;
                    
                    CREATE TRIGGER IF NOT EXISTS code_chunks_fts_update AFTER UPDATE ON code_chunks
                    BEGIN
                        UPDATE code_chunks_fts 
                        SET content = NEW.content,
                            file_path = (SELECT file_path FROM code_files WHERE id = NEW.file_id),
                            language = NEW.language
                        WHERE chunk_id = NEW.id;
                    END;
                    
                    CREATE TRIGGER IF NOT EXISTS code_chunks_fts_delete AFTER DELETE ON code_chunks
                    BEGIN
                        DELETE FROM code_chunks_fts WHERE chunk_id = OLD.id;
                    END;
                    
                    CREATE TRIGGER IF NOT EXISTS code_files_fts_insert AFTER INSERT ON code_files
                    BEGIN
                        INSERT INTO code_files_fts(file_id, file_path, file_name, language)
                        VALUES (NEW.id, NEW.file_path, NEW.file_name, NEW.language);
                    END;
                    
                    CREATE TRIGGER IF NOT EXISTS code_files_fts_update AFTER UPDATE ON code_files
                    BEGIN
                        UPDATE code_files_fts 
                        SET file_path = NEW.file_path,
                            file_name = NEW.file_name,
                            language = NEW.language
                        WHERE file_id = NEW.id;
                    END;
                    
                    CREATE TRIGGER IF NOT EXISTS code_files_fts_delete AFTER DELETE ON code_files
                    BEGIN
                        DELETE FROM code_files_fts WHERE file_id = OLD.id;
                    END;
                """,
                down_sql="""
                    -- Drop FTS5 triggers
                    DROP TRIGGER IF EXISTS code_files_fts_delete;
                    DROP TRIGGER IF EXISTS code_files_fts_update;
                    DROP TRIGGER IF EXISTS code_files_fts_insert;
                    DROP TRIGGER IF EXISTS code_chunks_fts_delete;
                    DROP TRIGGER IF EXISTS code_chunks_fts_update;
                    DROP TRIGGER IF EXISTS code_chunks_fts_insert;
                    
                    -- Drop FTS5 tables
                    DROP TABLE IF EXISTS code_files_fts;
                    DROP TABLE IF EXISTS code_chunks_fts;
                """
            ),
            Migration(
                version="003",
                name="Initialize VSS tables",
                up_sql="""
                    -- Note: VSS tables are created programmatically after loading extension
                    -- This migration creates performance indexes only
                    
                    -- Create indexes for performance
                    CREATE INDEX IF NOT EXISTS idx_code_embeddings_chunk_id ON code_embeddings(chunk_id);
                    CREATE INDEX IF NOT EXISTS idx_code_embeddings_model ON code_embeddings(model_name);
                    CREATE INDEX IF NOT EXISTS idx_code_embeddings_dimensions ON code_embeddings(dimensions);
                    CREATE INDEX IF NOT EXISTS idx_code_chunks_file_id ON code_chunks(file_id);
                    CREATE INDEX IF NOT EXISTS idx_code_chunks_language ON code_chunks(language);
                    CREATE INDEX IF NOT EXISTS idx_code_files_repo_id ON code_files(repository_id);
                    CREATE INDEX IF NOT EXISTS idx_code_files_language ON code_files(language);
                    CREATE INDEX IF NOT EXISTS idx_search_queries_session_id ON search_queries(session_id);
                    CREATE INDEX IF NOT EXISTS idx_search_results_query_id ON search_results(query_id);
                    CREATE INDEX IF NOT EXISTS idx_agent_interactions_session_id ON agent_interactions(session_id);
                """,
                down_sql="""
                    -- Drop indexes
                    DROP INDEX IF EXISTS idx_agent_interactions_session_id;
                    DROP INDEX IF EXISTS idx_search_results_query_id;
                    DROP INDEX IF EXISTS idx_search_queries_session_id;
                    DROP INDEX IF EXISTS idx_code_files_language;
                    DROP INDEX IF EXISTS idx_code_files_repo_id;
                    DROP INDEX IF EXISTS idx_code_chunks_language;
                    DROP INDEX IF EXISTS idx_code_chunks_file_id;
                    DROP INDEX IF EXISTS idx_code_embeddings_dimensions;
                    DROP INDEX IF EXISTS idx_code_embeddings_model;
                    DROP INDEX IF EXISTS idx_code_embeddings_chunk_id;
                    
                    -- Note: VSS tables are dropped programmatically
                """
            )
        ]
    
    async def _load_migration_file(self, file_path: Path) -> Optional[Migration]:
        """Load a migration from a file.
        
        Args:
            file_path: Path to the migration file
            
        Returns:
            Migration object or None if file is invalid
        """
        try:
            # Extract version from filename (e.g., "004_add_indexes.sql" -> "004")
            filename = file_path.stem
            parts = filename.split("_", 1)
            if len(parts) < 2:
                logger.warning(f"Invalid migration filename: {filename}")
                return None
            
            version = parts[0]
            name = parts[1].replace("_", " ").title()
            
            # Read migration content
            content = file_path.read_text(encoding="utf-8")
            
            # Split into up and down sections if present
            if "-- DOWN" in content:
                up_sql, down_sql = content.split("-- DOWN", 1)
                up_sql = up_sql.replace("-- UP", "").strip()
                down_sql = down_sql.strip()
            else:
                up_sql = content.replace("-- UP", "").strip()
                down_sql = ""
            
            return Migration(version=version, name=name, up_sql=up_sql, down_sql=down_sql)
        
        except Exception as e:
            logger.error(f"Failed to load migration file {file_path}: {e}")
            return None
    
    async def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions.
        
        Returns:
            List of applied migration versions
        """
        async with get_raw_db_connection() as conn:
            cursor = await conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
    
    async def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations.
        
        Returns:
            List of pending migrations
        """
        if not self._loaded:
            await self.initialize()
        
        applied = await self.get_applied_migrations()
        return [m for m in self._migrations if m.version not in applied]
    
    async def apply_migration(self, migration: Migration) -> None:
        """Apply a single migration.
        
        Args:
            migration: Migration to apply
        """
        logger.info(f"Applying migration: {migration}")
        
        async with get_raw_db_connection() as conn:
            try:
                # Execute migration SQL
                if migration.up_sql.strip():
                    await conn.executescript(migration.up_sql)
                
                # Record migration as applied
                await conn.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                    (migration.version, migration.name)
                )
                
                await conn.commit()
                logger.info(f"Successfully applied migration: {migration}")
            
            except Exception as e:
                await conn.rollback()
                logger.error(f"Failed to apply migration {migration}: {e}")
                raise
    
    async def rollback_migration(self, migration: Migration) -> None:
        """Rollback a single migration.
        
        Args:
            migration: Migration to rollback
        """
        logger.info(f"Rolling back migration: {migration}")
        
        if not migration.down_sql.strip():
            raise ValueError(f"Migration {migration.version} has no rollback SQL")
        
        async with get_raw_db_connection() as conn:
            try:
                # Execute rollback SQL
                await conn.executescript(migration.down_sql)
                
                # Remove migration record
                await conn.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (migration.version,)
                )
                
                await conn.commit()
                logger.info(f"Successfully rolled back migration: {migration}")
            
            except Exception as e:
                await conn.rollback()
                logger.error(f"Failed to rollback migration {migration}: {e}")
                raise
    
    async def migrate_up(self, target_version: Optional[str] = None) -> None:
        """Apply all pending migrations up to target version.
        
        Args:
            target_version: Target migration version (None for all)
        """
        pending = await self.get_pending_migrations()
        
        if target_version:
            pending = [m for m in pending if m.version <= target_version]
        
        if not pending:
            logger.info("No pending migrations to apply")
            return
        
        logger.info(f"Applying {len(pending)} migrations")
        
        for migration in pending:
            await self.apply_migration(migration)
        
        logger.info("All migrations applied successfully")
    
    async def migrate_down(self, target_version: str) -> None:
        """Rollback migrations down to target version.
        
        Args:
            target_version: Target migration version to rollback to
        """
        applied = await self.get_applied_migrations()
        to_rollback = [v for v in applied if v > target_version]
        
        if not to_rollback:
            logger.info(f"Already at or below target version {target_version}")
            return
        
        # Find migrations to rollback
        migrations_to_rollback = []
        for version in reversed(sorted(to_rollback)):
            migration = next((m for m in self._migrations if m.version == version), None)
            if migration:
                migrations_to_rollback.append(migration)
        
        logger.info(f"Rolling back {len(migrations_to_rollback)} migrations")
        
        for migration in migrations_to_rollback:
            await self.rollback_migration(migration)
        
        logger.info(f"Successfully rolled back to version {target_version}")
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status.
        
        Returns:
            Dictionary containing migration status information
        """
        if not self._loaded:
            await self.initialize()
        
        applied = await self.get_applied_migrations()
        pending = await self.get_pending_migrations()
        
        return {
            "total_migrations": len(self._migrations),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied_versions": applied,
            "pending_versions": [m.version for m in pending],
            "current_version": applied[-1] if applied else None,
            "latest_version": self._migrations[-1].version if self._migrations else None,
        }
    
    async def create_migration_file(self, name: str, up_sql: str, down_sql: str = "") -> Path:
        """Create a new migration file.
        
        Args:
            name: Migration name
            up_sql: SQL for applying the migration
            down_sql: SQL for rolling back the migration
            
        Returns:
            Path to the created migration file
        """
        # Generate next version number
        existing_versions = [int(m.version) for m in self._migrations if m.version.isdigit()]
        next_version = str(max(existing_versions, default=0) + 1).zfill(3)
        
        # Create filename
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        filename = f"{next_version}_{safe_name}.sql"
        file_path = self.migrations_dir / filename
        
        # Create migration content
        content = f"-- UP\n{up_sql}\n"
        if down_sql:
            content += f"\n-- DOWN\n{down_sql}\n"
        
        # Write file
        file_path.write_text(content, encoding="utf-8")
        
        logger.info(f"Created migration file: {file_path}")
        return file_path


# Global migration manager instance
_migration_manager: Optional[MigrationManager] = None


async def get_migration_manager() -> MigrationManager:
    """Get the global migration manager instance.
    
    Returns:
        The global migration manager
    """
    global _migration_manager
    
    if _migration_manager is None:
        _migration_manager = MigrationManager()
        await _migration_manager.initialize()
    
    return _migration_manager


async def run_migrations() -> None:
    """Run all pending migrations."""
    manager = await get_migration_manager()
    await manager.migrate_up()


async def get_migration_status() -> Dict[str, Any]:
    """Get current migration status.
    
    Returns:
        Dictionary containing migration status information
    """
    manager = await get_migration_manager()
    return await manager.get_migration_status()