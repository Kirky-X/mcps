# Copyright (c) Kirky.X. 2025. All rights reserved.
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import logging
from datetime import timedelta
from sqlmodel.ext.asyncio.session import AsyncSession
from prompt_manager.dal.database import Database, _prime_sqlite_extensions
from prompt_manager.utils.config import DatabaseConfig, Config, load_config, _replace_env_vars, VectorConfig
from prompt_manager.utils.logger import setup_logging, InterceptHandler, get_logger
from prompt_manager.core.queue import UpdateQueue
from prompt_manager.utils.exceptions import QueueFullError
from prompt_manager.core.local_cache import Cache as LocalCache, _CacheImpl
from prompt_manager.core.cache import CacheManager
import sqlite3
import os
import time

# --- Test Database ---

class TestDatabase:
    def test_init_sqlite(self):
        config = DatabaseConfig(type="sqlite", path=":memory:")
        # We need to mock create_async_engine where it is IMPORTED in the module under test
        with patch("prompt_manager.dal.database._prime_sqlite_extensions") as mock_prime, \
             patch("prompt_manager.dal.database.create_async_engine") as mock_engine, \
             patch("sqlalchemy.event.listen") as mock_listen:
            db = Database(config)
            # Check if engine was created with correct URL
            mock_engine.assert_called_once()
            args = mock_engine.call_args[0]
            assert str(args[0]) == "sqlite+aiosqlite:///:memory:"
            mock_prime.assert_not_called()
            mock_listen.assert_called_once()

        config_path = DatabaseConfig(type="sqlite", path="/tmp/test.db")
        with patch("prompt_manager.dal.database._prime_sqlite_extensions") as mock_prime, \
             patch("prompt_manager.dal.database.create_async_engine") as mock_engine, \
             patch("sqlalchemy.event.listen") as mock_listen:
            db = Database(config_path)
            assert str(db.url) == "sqlite+aiosqlite:////tmp/test.db"
            mock_prime.assert_called_once_with("/tmp/test.db")
            mock_listen.assert_called_once()

    def test_init_postgres(self):
        config = DatabaseConfig(type="postgres", path="postgresql+asyncpg://user:pass@localhost/db")
        with patch("prompt_manager.dal.database.create_async_engine") as mock_engine:
            db = Database(config)
            assert str(db.url) == "postgresql+asyncpg://user:pass@localhost/db"

    def test_init_unsupported(self):
        config = DatabaseConfig(type="mysql", path="mysql://localhost/db")
        with pytest.raises(ValueError, match="Unsupported database type"):
            Database(config)

    def test_prime_sqlite_extensions(self):
        with patch("sqlite3.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            with patch("sqlite_vec.load") as mock_load:
                _prime_sqlite_extensions("test.db")
                mock_conn.enable_load_extension.assert_any_call(True)
                mock_load.assert_called_once_with(mock_conn)
                mock_conn.enable_load_extension.assert_any_call(False)
                mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session(self):
        config = DatabaseConfig(type="sqlite", path=":memory:")
        db = Database(config)
        session = db.get_session()
        assert isinstance(session, AsyncSession)
        await session.close()
        await db.engine.dispose()

    def test_get_session_failure(self):
        config = DatabaseConfig(type="sqlite", path=":memory:")
        db = Database(config)
        db.session_factory = MagicMock(side_effect=Exception("Factory Error"))
        with pytest.raises(Exception, match="Factory Error"):
            db.get_session()

    def test_on_connect_hook(self):
        config = DatabaseConfig(type="sqlite", path=":memory:")
        with patch("sqlalchemy.event.listen") as mock_listen:
            db = Database(config)
            args = mock_listen.call_args[0]
            assert args[1] == "connect"
            on_connect = args[2]
            
            # Test the hook logic
            mock_dbapi_conn = MagicMock()
            # The structure in _on_connect is raw._connection (AsyncAdapt_aiosqlite_connection) -> raw._conn (sqlite3.Connection)
            # OR raw._connection (if not aiosqlite wrapper but similar)
            # The logic in Database._on_connect is:
            # raw = dbapi_connection
            # if hasattr(raw, "_connection"): raw = raw._connection
            # if hasattr(raw, "_conn"): raw = raw._conn
            # if isinstance(raw, sqlite3.Connection): ...
            
            # So we mock a nested structure
            mock_raw_conn = MagicMock(spec=sqlite3.Connection)
            
            # Setup the nested structure: dbapi_conn._connection._conn = mock_raw_conn
            mock_wrapper1 = MagicMock()
            mock_wrapper1._conn = mock_raw_conn
            mock_dbapi_conn._connection = mock_wrapper1
            
            with patch("sqlite_vec.load") as mock_load:
                on_connect(mock_dbapi_conn, None)
                mock_raw_conn.enable_load_extension.assert_any_call(True)
                mock_load.assert_called_once_with(mock_raw_conn)
                mock_raw_conn.enable_load_extension.assert_any_call(False)

# --- Test Queue ---

class TestUpdateQueue:
    def test_init_validation(self):
        with pytest.raises(ValueError, match="max_size must be positive"):
            UpdateQueue(max_size=0)
        q = UpdateQueue(max_size=10)
        assert q.queue.maxsize == 10
        assert q.is_running is False

    @pytest.mark.asyncio
    async def test_enqueue_full(self):
        q = UpdateQueue(max_size=1)
        await q.enqueue("t1", 1, {})
        with pytest.raises(QueueFullError, match="Update queue is full"):
            await q.enqueue("t2", 1, {})

    @pytest.mark.asyncio
    async def test_enqueue_success(self):
        q = UpdateQueue(max_size=1)
        future = await q.enqueue("t1", 1, {"k": "v"})
        assert not future.done()
        assert q.queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_get_task_done(self):
        q = UpdateQueue(max_size=1)
        await q.enqueue("t1", 1, {"k": "v"})
        item = await q.get()
        assert item[0] == "t1"
        q.task_done()
        assert q.queue._unfinished_tasks == 0

    @pytest.mark.asyncio
    async def test_stop(self):
        q = UpdateQueue(max_size=2)
        f1 = await q.enqueue("t1", 1, {})
        f2 = await q.enqueue("t2", 1, {})
        
        # Stop should cancel pending futures
        await q.stop()
        
        assert q.is_running is False
        assert q.queue.empty()
        with pytest.raises(asyncio.CancelledError):
            await f1
        with pytest.raises(asyncio.CancelledError):
            await f2

# --- Test Local Cache ---

class TestLocalCache:
    def test_lru_eviction(self):
        cache = LocalCache.builder().max_capacity(2).build()
        cache.insert("k1", "v1")
        cache.insert("k2", "v2")
        cache.insert("k3", "v3") # Should evict k1
        
        assert cache.get("k1") is None
        assert cache.get("k2") == "v2"
        assert cache.get("k3") == "v3"

    def test_ttl_expiration(self):
        cache = LocalCache.builder().time_to_live(timedelta(seconds=0.1)).build()
        cache.insert("k1", "v1")
        assert cache.get("k1") == "v1"
        time.sleep(0.2)
        assert cache.get("k1") is None

    def test_tti_expiration(self):
        cache = LocalCache.builder().time_to_idle(timedelta(seconds=0.1)).build()
        cache.insert("k1", "v1")
        time.sleep(0.05)
        assert cache.get("k1") == "v1" # Reset idle timer
        time.sleep(0.05) 
        assert cache.get("k1") == "v1" # Should still be there
        time.sleep(0.2)
        assert cache.get("k1") is None

    def test_invalidate(self):
        cache = LocalCache.builder().build()
        cache.insert("k1", "v1")
        cache.invalidate("k1")
        assert cache.get("k1") is None

# --- Test Cache Manager ---

class TestCacheManager:
    def test_disabled(self):
        config = MagicMock(spec=Config)
        config.cache = {"enabled": False}
        cm = CacheManager(config)
        assert cm.cache is None
        assert cm.get("k") is None
        cm.insert("k", "v") # Should do nothing
        cm.invalidate("k") # Should do nothing
        cm.invalidate_pattern("p") # Should do nothing

    def test_enabled(self):
        config = MagicMock(spec=Config)
        config.cache = {
            "enabled": True,
            "max_capacity": 10,
            "ttl_seconds": 60,
            "idle_timeout_seconds": 30
        }
        cm = CacheManager(config)
        assert cm.enabled is True
        assert cm.cache is not None
        
        cm.insert("k1", "v1")
        assert cm.get("k1") == "v1"
        cm.invalidate("k1")
        assert cm.get("k1") is None

    def test_invalidate_pattern(self):
        config = MagicMock(spec=Config)
        config.cache = {"enabled": True}
        cm = CacheManager(config)
        
        cm.insert("prompt:p1:v1", "v1")
        cm.insert("prompt:p1:v2", "v2")
        cm.insert("prompt:p2:v1", "v3")
        
        cm.invalidate_pattern("p1")
        
        assert cm.get("prompt:p1:v1") is None
        assert cm.get("prompt:p1:v2") is None
        assert cm.get("prompt:p2:v1") == "v3"
        
    def test_invalidate_pattern_no_impl(self):
        config = MagicMock(spec=Config)
        config.cache = {"enabled": True}
        cm = CacheManager(config)
        # Mock cache without _impl
        cm.cache = MagicMock()
        del cm.cache._impl
        cm.invalidate_pattern("p1") # Should not crash

    def test_generate_key(self):
        config = MagicMock(spec=Config)
        config.cache = {"enabled": False}
        cm = CacheManager(config)
        assert cm.generate_key("name", "1") == "prompt:name:v1"

# --- Test Logger ---

class TestLogger:
    def test_intercept_handler(self):
        handler = InterceptHandler()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__, lineno=1,
            msg="test message", args=(), exc_info=None
        )
        with patch("loguru.logger.opt") as mock_opt:
            handler.emit(record)
            mock_opt.assert_called()

    def test_setup_logging(self):
        config = {
            "level": "DEBUG",
            "console_output": True,
            "file_path": "/tmp/test.log",
            "max_size_mb": 5,
            "backup_count": 2
        }
        with patch("loguru.logger.add") as mock_add, \
             patch("loguru.logger.remove") as mock_remove, \
             patch("loguru.logger.configure") as mock_configure, \
             patch("logging.basicConfig") as mock_basic:
            
            setup_logging(config)
            
            mock_remove.assert_called_once()
            mock_configure.assert_called_once()
            assert mock_add.call_count == 2 # Console and File
            mock_basic.assert_called_once()

    def test_get_logger(self):
        logger = get_logger("test_module")
        # Check if bound logger has the extra name
        # Since loguru loggers are complex, we just check if it returns something valid
        assert logger is not None

# --- Test Config ---

class TestConfig:
    def test_replace_env_vars(self):
        os.environ["TEST_VAR"] = "value"
        assert _replace_env_vars({"k": "${TEST_VAR}"}) == {"k": "value"}
        assert _replace_env_vars(["${TEST_VAR}"]) == ["value"]
        assert _replace_env_vars("${TEST_VAR}") == "value"
        assert _replace_env_vars("plain") == "plain"
        del os.environ["TEST_VAR"]

    def test_load_config_success(self):
        with open("test_config.toml", "w") as f:
            f.write("""
            [database]
            type = "sqlite"
            path = ":memory:"
            
            [vector]
            dimension = 1536
            
            [cache]
            enabled = false
            
            [concurrency]
            max_workers = 10
            
            [logging]
            level = "INFO"
            
            [api]
            port = 8000
            """)
        
        try:
            config = load_config("test_config.toml")
            assert config.database.type == "sqlite"
            assert config.vector.dimension == 1536
            assert config.cache["enabled"] is False
        finally:
            os.remove("test_config.toml")

    def test_load_config_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config("non_existent.toml")
        
        with pytest.raises(FileNotFoundError):
            load_config("wrong_extension.txt")
