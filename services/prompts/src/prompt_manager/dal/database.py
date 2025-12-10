# Copyright (c) Kirky.X. 2025. All rights reserved.
import sqlite3
# 延迟导入扩展，避免模块加载阶段失败
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

from ..utils.config import DatabaseConfig
from ..utils.logger import get_logger

logger = get_logger(__name__)


def _prime_sqlite_extensions(db_path: str):
    # 使用同步 sqlite3 连接加载扩展到数据库文件（确保后续连接可用）
    conn = sqlite3.connect(db_path)
    try:
        conn.enable_load_extension(True)
        try:
            import sqlite_vec
            sqlite_vec.load(conn)
        except Exception as e:
            logger.warning(f"prime load sqlite_vec failed: {e}")
        finally:
            try:
                conn.enable_load_extension(False)
            except Exception:
                pass
    finally:
        conn.close()


class Database:
    def __init__(self, config: DatabaseConfig):
        """初始化数据库引擎与会话工厂

        根据配置创建 `sqlite+aiosqlite` 异步引擎，并注册连接事件以在建立连接时加载所需扩展。随后构建 `AsyncSession` 的会话工厂用于事务管理。

        Args:
            config (DatabaseConfig): 数据库配置，包含文件路径、连接池大小等信息。

        Returns:
            None: 构造函数不返回值。

        Raises:
            Exception: 当引擎创建或事件注册失败时可能抛出异常。
        """
        self.config = config
        engine_kwargs = {
            "echo": False,
            "pool_pre_ping": True,
            "pool_recycle": 3600
        }

        if config.type == "supabase":
            # Supabase mode: No local engine/session factory needed
            # The connection is managed by SupabaseClient
            self.engine = None
            self.session_factory = None
            return

        if config.type == "sqlite":
            # Normalize empty path to in-memory to avoid invalid URL and StaticPool arg conflicts
            if not config.path:
                config.path = ":memory:"
            self.url = f"sqlite+aiosqlite:///{config.path}"
            if config.path and config.path != ":memory:":
                _prime_sqlite_extensions(config.path)
            
            # SQLite specific configuration
            # For :memory: databases, SQLAlchemy uses StaticPool by default which doesn't support pool_size
            if config.path and config.path != ":memory:":
                engine_kwargs["pool_size"] = config.pool_size
                engine_kwargs["max_overflow"] = config.max_overflow

            self.engine = create_async_engine(
                self.url,
                **engine_kwargs
            )
        elif config.type == "postgres":
            self.url = config.path
            engine_kwargs["pool_size"] = config.pool_size
            engine_kwargs["max_overflow"] = config.max_overflow
            
            self.engine = create_async_engine(
                self.url,
                **engine_kwargs
            )
        else:
            raise ValueError("Unsupported database type")

        # 为每个底层连接加载 sqlite-vec 扩展，确保虚拟表 vec0 与距离列可用
        if config.type == "sqlite":
            def _on_connect(dbapi_connection, connection_record):
                try:
                    import sqlite3
                    import sqlite_vec

                    # 获取底层的 sqlite3.Connection 对象（兼容 aiosqlite 包装层）
                    raw = dbapi_connection
                    # 常见属性路径：.connection -> sqlite3.Connection
                    if hasattr(raw, "connection") and isinstance(getattr(raw, "connection"), sqlite3.Connection):
                        raw = raw.connection
                    # 兼容 aiosqlite 内部属性
                    if hasattr(raw, "_connection"):
                        raw = raw._connection
                    if hasattr(raw, "_conn"):
                        raw = raw._conn

                    # 若最终仍非 sqlite3.Connection，则尝试直接调用 load（某些适配器会代理调用）
                    target = raw if isinstance(raw, sqlite3.Connection) else dbapi_connection

                    try:
                        if isinstance(target, sqlite3.Connection):
                            try:
                                target.enable_load_extension(True)
                            except Exception:
                                pass
                        sqlite_vec.load(target)
                    finally:
                        if isinstance(target, sqlite3.Connection):
                            try:
                                target.enable_load_extension(False)
                            except Exception:
                                pass
                except Exception as e:
                    logger.error(f"Error in on_connect listener: {e}")
                    # 不中断连接创建，后续将自动回退为普通 BLOB 存储
                    pass
            event.listen(self.engine.sync_engine, "connect", _on_connect)

        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    def get_session(self) -> AsyncSession:
        """获取一个新的异步会话实例

        返回一个基于 `AsyncSession` 的会话对象，用于执行数据库操作。会话默认 `expire_on_commit=False` 以避免提交后属性失效。

        Args:
            None

        Returns:
            AsyncSession: 异步 SQLAlchemy 会话对象，可用于 `async with` 管理事务。

        Raises:
            Exception: 当会话工厂不可用或创建失败时可能抛出异常。
        """
        if self.config.type == "supabase":
            raise NotImplementedError("Supabase mode does not support SQLAlchemy sessions. Use SupabaseService instead.")

        try:
            return self.session_factory()
        except Exception as e:
            logger.error("session creation failed", error=str(e))
            raise

    async def close(self):
        """关闭数据库连接引擎"""
        if self.engine:
            await self.engine.dispose()
