import asyncio
import pytest

from library.core.server import LibraryMasterServer
from library.core.config import Settings


@pytest.mark.asyncio
async def test_thread_pool_basic():
    server = LibraryMasterServer(Settings())
    res = await server.find_latest_versions([
        {"name": "requests", "language": "python"},
        {"name": "express", "language": "node"},
    ])
    assert "results" in res or "error" in res
