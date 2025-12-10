# Copyright (c) Kirky.X. 2025. All rights reserved.
import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from prompt_manager.core.cache import CacheManager
from prompt_manager.core.manager import PromptManager
from prompt_manager.core.queue import UpdateQueue
from prompt_manager.dal.database import Database
from prompt_manager.dal.vector_index import VectorIndex
from sqlmodel import SQLModel
from prompt_manager.auth.models import Base as AuthBase
from prompt_manager.services.embedding import EmbeddingService
from prompt_manager.services.template import TemplateService
from prompt_manager.utils.config import Config, DatabaseConfig, VectorConfig


# ==========================================
# Mocks
# ==========================================

class MockEmbeddingService(EmbeddingService):
    """测试用嵌入服务替身，避免网络调用与费用

    通过重写 `generate` 方法返回可预测的向量结果，确保测试稳定性与可重复性。

    Args:
        dimension (int): 向量维度，默认 1536。

    Returns:
        None

    Raises:
        None
    """

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension

    async def generate(self, text: str) -> list[float]:
        """基于文本长度生成确定性向量用于测试

        Args:
            text (str): 输入文本。

        Returns:
            list[float]: 长度为 `dimension` 的浮点向量。

        Raises:
            None
        """
        seed = len(text) % 100 / 100.0
        return [seed] * self.dimension


# ==========================================
# Fixtures
# ==========================================

@pytest_asyncio.fixture(scope="session")
async def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
def test_config():
    """构建用于测试的配置对象

    返回包含数据库、向量、缓存、并发、日志与 API 的最小可运行配置。

    Args:
        None

    Returns:
        Config: 测试配置。

    Raises:
        None
    """
    return Config(
        database=DatabaseConfig(type="sqlite", path=":memory:", pool_size=1, max_overflow=0),
        vector=VectorConfig(enabled=True, dimension=4, embedding_model="test", embedding_api_key="sk-test"),
        cache={"enabled": True, "max_capacity": 100, "ttl_seconds": 60, "idle_timeout_seconds": 60},
        concurrency={"queue_enabled": False, "queue_max_size": 10},
        logging={"level": "DEBUG", "console_output": True},
        api={"http": {"enabled": True, "host": "localhost", "port": 8000}}
    )


@pytest_asyncio.fixture(scope="function")
async def db_engine(test_config):
    """为每个测试用例创建独立的数据库引擎

    初始化 SQLite 数据库与表结构，并创建向量索引虚拟表，测试结束后清理资源与临时文件。

    Args:
        test_config (Config): 测试配置对象。

    Returns:
        AsyncGenerator[Database, None]: 异步数据库封装对象的生成器。

    Raises:
        Exception: 当数据库或索引初始化失败时可能抛出。
    """
    # Note: We use a file-based DB for tests because shared cache in-memory
    # with async engines can be tricky with sqlite-vec extensions.
    # Using a temp file is safer for extension loading.
    test_db_path = "test_prompts.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    # Ensure auth deps use the same DB path via config
    os.environ["PROMPT_MANAGER_DB_PATH"] = test_db_path
    test_config.database.path = test_db_path
    db = Database(test_config.database)

    # Init Tables
    async with db.engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        await conn.run_sync(AuthBase.metadata.create_all)

    # Init Vector Index
    async with db.get_session() as session:
        idx = VectorIndex(test_config.vector.dimension)
        await idx.create_index(session)
        await session.commit()

    yield db

    await db.engine.dispose()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest_asyncio.fixture(scope="function")
async def prompt_manager(db_engine, test_config):
    """构建测试用 PromptManager 实例

    使用简化的向量维度与替身嵌入服务以提升测试速度与稳定性。

    Args:
        db_engine (Database): 数据库封装对象。
        test_config (Config): 测试配置对象。

    Returns:
        PromptManager: 管理器实例。

    Raises:
        None
    """
    cache = CacheManager(test_config)
    queue = UpdateQueue(10)
    # Use Mock Embedding with dimension 4 for speed
    embedding = MockEmbeddingService(dimension=4)
    template = TemplateService()
    vector_index = VectorIndex(dimension=4)

    manager = PromptManager(db_engine, cache, queue, embedding, template, vector_index)
    task = asyncio.create_task(manager.process_update_queue())
    try:
        yield manager
    finally:
        task.cancel()
        await queue.stop()
