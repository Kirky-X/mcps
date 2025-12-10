import asyncio
import datetime
import pytest
from unittest.mock import MagicMock

from prompt_manager.services.sync_engine import SyncEngine
from prompt_manager.services.config_service import ConfigService
from prompt_manager.dal.supabase.service import SupabaseService as DomainSupabaseService
from prompt_manager.services.supabase_service import SupabaseService as GenericSupabaseService
from prompt_manager.models.orm import Prompt, AppConfig


@pytest.mark.asyncio
async def test_sync_pull_insert_and_checkpoint(db_engine):
    config = ConfigService(db_engine)

    # Build mock Supabase client
    mock_client = MagicMock()
    mock_table = MagicMock()

    now = datetime.datetime.now(datetime.timezone.utc)
    iso_now = now.isoformat()

    # Select chain
    mock_table.select.return_value = mock_table
    mock_table.gt.return_value = mock_table

    select_resp = MagicMock()
    select_resp.data = [{
        "id": "p1",
        "name": "hello",
        "content": "world",
        "created_at": iso_now,
        "updated_at": iso_now,
        "is_deleted": False,
        "sync_hash": "abc"
    }]

    async def async_select_execute():
        return select_resp

    mock_table.execute.side_effect = async_select_execute

    # Upsert chain
    upsert_builder = MagicMock()
    upsert_resp = MagicMock()
    upsert_resp.data = []

    async def async_upsert_execute():
        return upsert_resp

    upsert_builder.execute.side_effect = async_upsert_execute
    mock_table.upsert.return_value = upsert_builder

    mock_client.table.return_value = mock_table

    generic = MagicMock(spec=GenericSupabaseService)
    generic.client = mock_client
    domain = DomainSupabaseService(generic)

    engine = SyncEngine(db_engine, domain, config)
    result = await engine.sync()

    assert result["pulled"] == 1
    assert result["inserted_local"] == 1
    assert result["pushed"] == 1

    # Verify local DB has the prompt and checkpoint updated
    async with db_engine.get_session() as session:
        p = await session.get(Prompt, "p1")
        assert p is not None
        appcfg = (await session.execute(
            AppConfig.__table__.select().where(AppConfig.key == "last_sync_time")
        )).first()
        assert appcfg is not None


@pytest.mark.asyncio
async def test_sync_pull_ignore_remote_older_and_push_local(db_engine):
    config = ConfigService(db_engine)

    # Prepare local newer record
    newer = datetime.datetime.now(datetime.timezone.utc)
    older = newer - datetime.timedelta(days=1)

    async with db_engine.get_session() as session:
        async with session.begin():
            session.add(Prompt(
                id="p2",
                name="local",
                content="new",
                created_at=newer,
                updated_at=newer,
                is_deleted=False,
            ))

    # Build mock Supabase client returning older remote
    mock_client = MagicMock()
    mock_table = MagicMock()

    mock_table.select.return_value = mock_table
    mock_table.gt.return_value = mock_table

    select_resp = MagicMock()
    select_resp.data = [{
        "id": "p2",
        "name": "remote",
        "content": "old",
        "created_at": older.isoformat(),
        "updated_at": older.isoformat(),
        "is_deleted": False,
        "sync_hash": "xyz"
    }]

    async def async_select_execute():
        return select_resp

    mock_table.execute.side_effect = async_select_execute

    # Upsert builder
    upsert_builder = MagicMock()
    upsert_resp = MagicMock()
    upsert_resp.data = []

    async def async_upsert_execute():
        return upsert_resp

    upsert_builder.execute.side_effect = async_upsert_execute
    mock_table.upsert.return_value = upsert_builder

    mock_client.table.return_value = mock_table

    generic = MagicMock(spec=GenericSupabaseService)
    generic.client = mock_client
    domain = DomainSupabaseService(generic)

    engine = SyncEngine(db_engine, domain, config)
    result = await engine.sync()

    assert result["pulled"] == 1
    assert result["updated_local"] == 0
    assert result["pushed"] == 1

    # Verify local record remains newer content
    async with db_engine.get_session() as session:
        p = await session.get(Prompt, "p2")
        assert p is not None
        assert p.content == "new"
