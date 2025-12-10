import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from sqlmodel.ext.asyncio.session import AsyncSession
from prompt_manager.core.manager import PromptManager, PromptNotFoundError, ValidationError, OptimisticLockError
from prompt_manager.models.schemas import CreatePromptRequest, SearchResult, SearchResultItem
from prompt_manager.models.orm import Prompt, PromptVersion, Tag, PromptTag

@pytest.fixture
def mock_db():
    db = MagicMock()
    session = AsyncMock(spec=AsyncSession)
    # Correctly mock the async context manager for db.get_session()
    # It needs to return an async context manager whose __aenter__ returns the session
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    db.get_session.return_value = cm
    return db, session

@pytest.fixture
def mock_components():
    return {
        "cache": MagicMock(),
        "queue": AsyncMock(),
        "embedding": AsyncMock(),
        "template": AsyncMock(),
        "vector_index": AsyncMock()
    }

@pytest.fixture
def manager(mock_db, mock_components):
    db, _ = mock_db
    return PromptManager(
        db=db,
        cache=mock_components["cache"],
        queue=mock_components["queue"],
        embedding_service=mock_components["embedding"],
        template_service=mock_components["template"],
        vector_index=mock_components["vector_index"]
    )

@pytest.mark.asyncio
async def test_search_vector_error_handling(manager, mock_db):
    """Test search handles vector service failure gracefully"""
    _, session = mock_db
    manager.embedding.generate.side_effect = Exception("Embedding service down")
    
    # Mock DB results for fallback query
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    
    result = await manager.search(query="test query")
    
    assert result.total == 0
    assert result.results == []
    # If vector search fails, we catch the exception and proceed with empty vec_results.
    # However, since has_vector_search becomes True, candidate_ids becomes empty set (from vec_results=[]).
    # Then `if not candidate_ids: return SearchResult(total=0, results=[])` is hit.
    # So session.execute(stmt) for fetching prompts is NOT called.
    # We should assert that session.execute was called at least once (for potential tag search or just skipped)
    # But in this specific flow:
    # 1. vector search fails -> vec_results = []
    # 2. vector_ids = set()
    # 3. has_vector_search = True
    # 4. candidate_ids = vector_ids (empty set)
    # 5. if not candidate_ids: return empty
    # So the main query is skipped.
    assert result.total == 0

@pytest.mark.asyncio
async def test_delete_last_active_version_failure(manager, mock_db):
    """Test prevention of deleting the last active version"""
    _, session = mock_db
    
    # Mock active versions
    v1 = PromptVersion(id="1", version="1.0", is_active=True, prompt_id="p1", is_latest=True)
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [v1]
    session.execute.return_value = mock_result
    
    with pytest.raises(ValidationError, match="Cannot delete the last active version"):
        await manager.delete("test_prompt", version="1.0")

@pytest.mark.asyncio
async def test_delete_all_versions_failure(manager, mock_db):
    """Test prevention of deleting all versions"""
    _, session = mock_db
    
    # Mock active versions - only one left
    v1 = PromptVersion(id="1", version="1.0", is_active=True, prompt_id="p1", is_latest=True)
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [v1]
    session.execute.return_value = mock_result
    
    with pytest.raises(ValidationError, match="Cannot delete all versions"):
        await manager.delete("test_prompt")

@pytest.mark.asyncio
async def test_get_not_found(manager, mock_db):
    """Test get raises PromptNotFoundError when prompt doesn't exist"""
    _, session = mock_db
    
    # Mock cache miss
    manager.cache.get.return_value = None
    
    # Mock DB miss
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    
    with pytest.raises(PromptNotFoundError):
        await manager.get("nonexistent_prompt")

@pytest.mark.asyncio
async def test_activate_not_found(manager, mock_db):
    """Test activate raises error for nonexistent version"""
    _, session = mock_db
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    
    with pytest.raises(PromptNotFoundError):
        await manager.activate("test_prompt", "1.0")
