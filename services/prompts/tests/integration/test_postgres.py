import os
import pytest
import pytest_asyncio

from sqlmodel import SQLModel, select

from prompt_manager.dal.database import Database
from prompt_manager.models.orm import Prompt
from prompt_manager.utils.config import DatabaseConfig

if os.getenv("RUN_POSTGRES_TESTS") != "1":
    pytest.skip("Postgres tests disabled", allow_module_level=True)


@pytest_asyncio.fixture(scope="function")
async def pg_db():
    dsn = os.getenv("POSTGRES_DSN", "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb")
    cfg = DatabaseConfig(type="postgres", path=dsn, pool_size=2, max_overflow=4)
    db = Database(cfg)
    async with db.engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield db
    await db.engine.dispose()


@pytest.mark.asyncio
async def test_pg_connect_and_crud(pg_db):
    async with pg_db.get_session() as session:
        p = Prompt(name="pg_test")
        session.add(p)
        await session.commit()
        stmt = select(Prompt).where(Prompt.name == "pg_test")
        res = (await session.execute(stmt)).scalar_one()
        assert res.name == "pg_test"
