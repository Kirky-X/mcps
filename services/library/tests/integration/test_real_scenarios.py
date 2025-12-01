import pytest

from library.core.server import LibraryMasterServer
from library.core.config import Settings


@pytest.mark.asyncio
async def test_real_versions_docs_deps():
    server = LibraryMasterServer(Settings())
    res = await server.find_latest_versions([
        {"name": "serde", "language": "rust"},
        {"name": "requests", "language": "python"},
    ])
    assert isinstance(res, dict)
