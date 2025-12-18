import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, ANY, call
from datetime import datetime
from prompt_manager.core.manager import PromptManager, PromptNotFoundError, ValidationError, OptimisticLockError
from prompt_manager.models.schemas import CreatePromptRequest, RoleConfig, LLMConfigModel, PrincipleRefModel
from prompt_manager.models.orm import PromptVersion, Prompt, PromptRole, LLMConfig, Tag, PromptTag, PrinciplePrompt, LLMClient, ClientMapping

@pytest.fixture
def mock_deps():
    db = MagicMock()
    session = AsyncMock()
    
    # Correctly mock session context manager
    # session.begin() needs to return an async context manager
    begin_cm = AsyncMock()
    begin_cm.__aenter__.return_value = session
    # session.begin must NOT be an AsyncMock itself if we want to call it directly as a function that returns a CM
    # BUT in the code it's `async with session.begin():` which means session.begin() is a coroutine OR returns an async CM.
    # SQLAlchemy's session.begin() is an async method that returns an AsyncSessionTransaction.
    
    # session.begin = MagicMock(return_value=begin_cm)
    # The real session.begin is an async method. We should mock it as an AsyncMock if it's awaited,
    # OR if it returns a context manager that is used in `async with`.
    # `async with session.begin():` means `session.begin()` returns an object with `__aenter__`.
    # If session is an AsyncMock, calling a method on it returns a new AsyncMock by default.
    # The default AsyncMock when awaited returns itself. But we need it to be an async context manager.
    
    # Let's set session.begin to be a function that returns the CM directly?
    # No, it's called as `session.begin()`.
    
    session.begin = MagicMock(return_value=begin_cm)
    
    # db.get_session() returns an async context manager that yields session
    get_session_cm = AsyncMock()
    get_session_cm.__aenter__.return_value = session
    db.get_session.return_value = get_session_cm
    
    cache = MagicMock()
    queue = MagicMock()
    queue.enqueue = AsyncMock()
    
    embedding = AsyncMock()
    embedding.generate.return_value = [0.1, 0.2, 0.3]
    
    template = MagicMock()
    # Simple pass-through for render
    template.render.side_effect = lambda t, v, tv: t.format(**(v or {})) if v else t
    
    vector_index = AsyncMock()
    vector_index._serialize_vector.return_value = b"vector_bytes"
    
    return db, session, cache, queue, embedding, template, vector_index

@pytest.fixture
def manager(mock_deps):
    db, _, cache, queue, embedding, template, vector_index = mock_deps
    return PromptManager(db, cache, queue, embedding, template, vector_index)

@pytest.mark.asyncio
async def test_create_full_flow(manager, mock_deps):
    """Test create() calling _create_on_session with full data"""
    _, session, cache, _, embedding, _, vector_index = mock_deps
    
    # Mock existing prompt check (None = new prompt)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    # Mock calculate_version query (None = first version)
    mock_ver_result = MagicMock()
    # Fix: Return empty list for .scalars().all() call
    mock_ver_result.scalars.return_value.all.return_value = []
    # Mock prev_max query
    mock_max_result = MagicMock()
    mock_max_result.scalar.return_value = 0
    
    # Setup execute side effects for sequence of queries
    # 1. select Prompt (None)
    # 2. select PromptVersion for version calc (Empty list)
    # 3. select func.max (0)
    # 4. update is_latest (executed via session.execute)
    # 5. additional execute calls if any
    
    # We need to ensure side_effect has enough items or loop it.
    # If we add a MagicMock at the end that handles everything else, it might work.
    # But session.execute is an AsyncMock, so side_effect must be an iterable of return values (or exceptions).
    
    # Let's make the last item repeat or be a default mock
    default_mock = MagicMock()
    # We need to mock what `session.execute` returns when selecting the NEWLY CREATED version at the end of _create_on_session
    # manager.py: stmt = select(PromptVersion).where(PromptVersion.id == version_id).options(...)
    #             return (await session.execute(stmt)).scalar_one()
    
    mock_created_version = MagicMock(spec=PromptVersion)
    mock_created_version.version = "1.0"
    mock_created_version.is_active = True
    mock_created_version.is_latest = True
    
    mock_final_result = MagicMock()
    mock_final_result.scalar_one.return_value = mock_created_version
    
    session.execute.side_effect = [mock_result, mock_ver_result, mock_max_result, default_mock, mock_final_result]
    
    req = CreatePromptRequest(
        name="test_prompt", # Must match regex ^[a-zA-Z0-9_]+$
        description="A test prompt",
        roles=[
            RoleConfig(role_type="system", content="You are a bot", order=0),
            RoleConfig(role_type="user", content="Hello", order=1)
        ],
        llm_config=LLMConfigModel(model="gpt-4"),
        tags=["t1", "t2"],
        client_type="web"
    )
    
    # Mock helpers
    manager._associate_tags = AsyncMock()
    manager._associate_principles = AsyncMock()
    manager._associate_client = AsyncMock()
    manager._load_client_principles = AsyncMock()
    
    # Setup vector_index.insert to be awaited
    vector_index.insert.return_value = None
    
    # Mock session.add to be a simple callable, NOT an AsyncMock/MagicMock that needs awaiting
    # session.add is a synchronous method in SQLAlchemy's AsyncSession (it adds to the session, flush is async)
    # BUT if we mocked session as AsyncMock, all its methods are AsyncMocks by default.
    # We need to set session.add to be a standard MagicMock (not AsyncMock) because it's not awaited.
    session.add = MagicMock()
    
    version = await manager.create(req)
    
    assert version.version == "1.0"
    assert version.is_active is True
    assert version.is_latest is True
    
    # Verify DB interactions
    assert session.add.call_count >= 3 # Prompt, Version, Role(s), Config...
    embedding.generate.assert_awaited_once_with("A test prompt")
    vector_index.insert.assert_awaited_once()
    cache.invalidate.assert_called()
    cache.invalidate_pattern.assert_called_with("test_prompt")

@pytest.mark.asyncio
async def test_get_full_flow_cache_miss(manager, mock_deps):
    """Test get() with cache miss, loading from DB"""
    _, session, cache, _, _, _, _ = mock_deps
    
    # Cache miss
    cache.get.return_value = None
    
    # Mock DB return
    mock_ver = MagicMock(spec=PromptVersion)
    mock_ver.id = "v1"
    mock_ver.version = "1.0"
    mock_ver.prompt = MagicMock(name="test_prompt")
    mock_ver.roles = [
        MagicMock(role_type="system", content="Sys", template_variables=None),
        MagicMock(role_type="user", content="Hi", template_variables=None)
    ]
    # Create a proper mock for llm_config with string attributes
    mock_llm_config = MagicMock()
    mock_llm_config.model = "gpt-4"
    mock_llm_config.temperature = 0.7
    mock_llm_config.max_tokens = 1000
    mock_llm_config.top_p = 1.0
    mock_llm_config.frequency_penalty = 0.0
    mock_llm_config.presence_penalty = 0.0
    mock_llm_config.stop_sequences = None
    mock_ver.llm_config = mock_llm_config
    mock_ver.principle_refs = []
    mock_ver.client_mappings = []
    
    # Mock the result to have scalars().first() method
    mock_scalars = MagicMock()
    mock_scalars.first.return_value = mock_ver
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    session.execute.return_value = mock_result
    
    # Mock _load_principles to return empty list
    manager._load_principles = AsyncMock(return_value=[])
    
    result = await manager.get("test_prompt", output_format="openai")
    
    assert result.model == "gpt-4"
    assert len(result.messages) == 2
    assert result.messages[0]["role"] == "system"
    
    # Verify cache population
    cache.insert.assert_called_once()

@pytest.mark.asyncio
async def test_search_vector_and_tags(manager, mock_deps):
    """Test search() with both vector and tag query"""
    _, session, _, _, embedding, _, vector_index = mock_deps
    
    # Mock vector index dimension for compatibility check
    vector_index.dimension = 3
    # Mock embedding generation to return compatible dimension
    embedding.generate.return_value = [0.1, 0.2, 0.3]
    
    # Mock vector search results
    vector_index.search.return_value = [("v1", 0.1), ("v2", 0.2)]
    
    # Mock tag search results
    mock_tag_result = MagicMock()
    mock_tag_result.fetchall.return_value = [("v1",)] # Only v1 matches tags
    
    # Mock final fetch results
    mock_v1 = MagicMock(spec=PromptVersion)
    mock_v1.id = "v1"
    mock_v1.prompt_id = "p1"
    mock_v1.prompt = MagicMock(name="p1")
    # Correctly mock properties for SearchResultItem validation
    mock_v1.prompt.name = "p1" 
    mock_v1.version = "1.0"
    mock_v1.description = "desc"
    mock_v1.created_at = datetime.now()
    
    # Mock tags to be compatible with list comprehension in manager.py
    # manager.py: tags = [t.name for t in v.tags]
    t1 = MagicMock()
    t1.name = "t1"
    mock_v1.tags = [t1]
    
    mock_final_result = MagicMock()
    mock_final_result.scalars.return_value.all.return_value = [mock_v1]
    
    # Configure session.execute to return tag results then final results
    session.execute.side_effect = [mock_tag_result, mock_final_result]
    
    result = await manager.search(query="search", tags=["t1"], logic="AND")
    
    assert result.total == 1
    assert result.results[0].prompt_id == "p1"
    # Similarity score should be calculated from distance 0.1 -> 1/(1+0.1) = ~0.909
    assert result.results[0].similarity_score > 0.9

@pytest.mark.asyncio
async def test_update_execution(manager, mock_deps):
    """Test _execute_update flow"""
    _, session, cache, _, _, _, _ = mock_deps
    
    # Mock finding current latest version
    mock_current = MagicMock(spec=PromptVersion)
    mock_current.version_number = 1
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_current
    
    session.execute.return_value = mock_result
    
    # Mock _create_on_session
    mock_new_ver = MagicMock(spec=PromptVersion)
    manager._create_on_session = AsyncMock(return_value=mock_new_ver)
    
    # Need to pass required fields for CreatePromptRequest
    # The manager calls CreatePromptRequest(name=name, **update_data)
    # roles is required in CreatePromptRequest
    
    # We update update_data to include roles
    version = await manager._execute_update("p1", 1, {
        "description": "new",
        "roles": [
            RoleConfig(role_type="system", content="sys", order=0)
        ]
    })
    
    assert version == mock_new_ver
    manager._create_on_session.assert_awaited_once()
    cache.invalidate.assert_called()

@pytest.mark.asyncio
async def test_update_optimistic_lock_error(manager, mock_deps):
    """Test _execute_update raises OptimisticLockError"""
    _, session, _, _, _, _, _ = mock_deps
    
    # Mock current version number mismatch
    mock_current = MagicMock(spec=PromptVersion)
    mock_current.version_number = 2 # Expected 1
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_current
    session.execute.return_value = mock_result
    
    with pytest.raises(OptimisticLockError):
        await manager._execute_update("p1", 1, {})

@pytest.mark.asyncio
async def test_delete_specific_version(manager, mock_deps):
    """Test delete() of a specific version"""
    _, session, cache, _, _, _, vector_index = mock_deps
    
    # Mock fetching active versions
    v1 = MagicMock(spec=PromptVersion, id="v1", version="1.0", is_active=True)
    v2 = MagicMock(spec=PromptVersion, id="v2", version="1.1", is_active=True)
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [v1, v2]
    session.execute.return_value = mock_result
    
    success = await manager.delete("p1", version="1.0")
    
    assert success is True
    assert v1.is_active is False # Should be soft deleted
    assert v2.is_active is True # Should remain active
    vector_index.delete.assert_awaited_once_with(session, "v1")
    cache.invalidate.assert_called()

@pytest.mark.asyncio
async def test_delete_all_versions_keep_latest(manager, mock_deps):
    """Test delete() without version keeps one active"""
    _, session, cache, _, _, _, vector_index = mock_deps
    
    v1 = MagicMock(spec=PromptVersion, id="v1", version="1.0", is_active=True, is_latest=False, created_at=1)
    v2 = MagicMock(spec=PromptVersion, id="v2", version="1.1", is_active=True, is_latest=True, created_at=2)
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [v1, v2]
    session.execute.return_value = mock_result
    
    success = await manager.delete("p1")
    
    assert success is True
    assert v1.is_active is False
    assert v2.is_active is True # Latest kept
    vector_index.delete.assert_awaited_once_with(session, "v1")

@pytest.mark.asyncio
async def test_activate_set_latest(manager, mock_deps):
    """Test activate() with set_as_latest=True"""
    _, session, cache, _, _, _, _ = mock_deps
    
    mock_ver = MagicMock(spec=PromptVersion, id="v1", prompt_id="p1", is_active=False)
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_ver
    session.execute.return_value = mock_result
    
    success = await manager.activate("p1", "1.0", set_as_latest=True)
    
    assert success is True
    assert mock_ver.is_active is True
    assert mock_ver.is_latest is True
    # Should execute update to unset other latest
    assert session.execute.call_count >= 2

@pytest.mark.asyncio
async def test_create_principle_new(manager, mock_deps):
    """Test create_principle() creating new principle"""
    _, session, _, _, _, _, _ = mock_deps
    
    # Mock existing check (None)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    
    p = await manager.create_principle("prin1", "1.0", "content")
    
    assert p.name == "prin1"
    assert p.content == "content"
    session.add.assert_called_once()

@pytest.mark.asyncio
async def test_load_principles_logic(manager, mock_deps):
    """Test _load_principles merging refs and defaults"""
    _, session, _, _, _, _, _ = mock_deps
    
    # Setup version obj with 1 ref and 1 client default
    mock_ver = MagicMock(spec=PromptVersion)
    mock_ref = MagicMock(principle_id="pid1", order=0)
    mock_ver.principle_refs = [mock_ref]
    
    mock_client = MagicMock(default_principles=[
        {"principle_name": "p2", "version": "latest"}
    ])
    mock_mapping = MagicMock(client=mock_client)
    mock_ver.client_mappings = [mock_mapping]
    
    # Mock principle queries
    # 1. Fetch ref principle p1
    # 2. Fetch default principle p2
    p1 = MagicMock(spec=PrinciplePrompt, id="pid1", name="p1")
    p2 = MagicMock(spec=PrinciplePrompt, id="pid2", name="p2")
    
    mock_res_p1 = MagicMock()
    mock_res_p1.scalar_one_or_none.return_value = p1
    
    mock_res_p2 = MagicMock()
    mock_res_p2.scalar_one_or_none.return_value = p2
    
    session.execute.side_effect = [mock_res_p1, mock_res_p2]
    
    principles = await manager._load_principles(session, mock_ver)
    
    assert len(principles) == 2
    assert principles[0] == p1
    assert principles[1] == p2

@pytest.mark.asyncio
async def test_process_queue_handling(manager, mock_deps):
    """Test process_update_queue handles tasks"""
    _, _, _, queue, _, _, _ = mock_deps
    
    # Setup queue to yield one task then cancel
    future = MagicMock()
    task = ("p1", 1, {}, future)
    
    queue.get = AsyncMock(side_effect=[task, asyncio.CancelledError])
    
    manager._execute_update = AsyncMock(return_value="success")
    
    await manager.process_update_queue()
    
    manager._execute_update.assert_awaited_once()
    future.set_result.assert_called_with("success")
