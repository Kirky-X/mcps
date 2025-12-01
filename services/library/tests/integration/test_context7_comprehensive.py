import os
import pytest

from library.tools.context7_tools import create_context7_tools
from library.core.config import Settings


@pytest.mark.asyncio
async def test_context7_search_docs_health():
    if not (os.getenv("LIBRARYMASTER_CONTEXT7_API_KEY") or os.getenv("CONTEXT7_KEY") or os.getenv("mcp-library_CONTEXT7_API_KEY")):
        pytest.skip("Context7 API key not provided")
    tools = create_context7_tools(Settings())
    res = await tools.search_libraries({"query": "http client", "language": "python"})
    assert isinstance(res, dict)
