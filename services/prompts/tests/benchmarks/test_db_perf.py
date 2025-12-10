import os
import time
import pytest
import pytest_asyncio

from sqlmodel import SQLModel

from prompt_manager.dal.database import Database
from prompt_manager.models.orm import Prompt, PromptVersion
from prompt_manager.utils.config import DatabaseConfig


if os.getenv("RUN_BENCH") != "1":
    pytest.skip("Benchmarks disabled", allow_module_level=True)


@pytest_asyncio.fixture(scope="session")
async def bench_db():
    db_path = "bench_prompts.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    cfg = DatabaseConfig(type="sqlite", path=db_path, pool_size=4, max_overflow=8)
    db = Database(cfg)
    async with db.engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield db
    await db.engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_insert_search_benchmark(bench_db):
    n = int(os.getenv("BENCH_N", "500"))
    t0 = time.perf_counter()
    async with bench_db.get_session() as session:
        async with session.begin():
            for i in range(n):
                p = Prompt(name=f"bench_{i}")
                session.add(p)
                await session.flush()
                v = PromptVersion(prompt_id=p.id, version="1.0", description=f"desc {i}", is_active=True, is_latest=True)
                session.add(v)
    insert_time = time.perf_counter() - t0

    t1 = time.perf_counter()
    async with bench_db.get_session() as session:
        res = (await session.execute(SQLModel.select(PromptVersion))).scalars().all()
        assert len(res) == n
    select_time = time.perf_counter() - t1

    print({"insert_sec": insert_time, "select_sec": select_time, "rows": n})
