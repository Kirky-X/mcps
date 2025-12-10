import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from prompt_manager.core.manager import PromptManager, ValidationError
from prompt_manager.models.orm import PromptVersion, Tag, PrinciplePrompt, LLMClient

@pytest.fixture
def mock_session():
    return AsyncMock()

@pytest.fixture
def manager():
    # Minimal mock manager for helper testing
    m = MagicMock(spec=PromptManager)
    # Restore the methods we want to test
    m._calculate_version = PromptManager._calculate_version
    m._associate_tags = PromptManager._associate_tags
    m._associate_principles = PromptManager._associate_principles
    m._associate_client = PromptManager._associate_client
    return m

@pytest.mark.asyncio
async def test_calculate_version_initial(manager, mock_session):
    """Test initial version calculation"""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    
    version = await manager._calculate_version(manager, mock_session, "p1", "minor")
    assert version == "1.0"

@pytest.mark.asyncio
async def test_calculate_version_minor(manager, mock_session):
    """Test minor version increment"""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = ["1.5"]
    mock_session.execute.return_value = mock_result
    
    version = await manager._calculate_version(manager, mock_session, "p1", "minor")
    assert version == "1.6"

@pytest.mark.asyncio
async def test_calculate_version_major(manager, mock_session):
    """Test major version increment"""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = ["1.5"]
    mock_session.execute.return_value = mock_result
    
    version = await manager._calculate_version(manager, mock_session, "p1", "major")
    assert version == "2.0"

@pytest.mark.asyncio
async def test_associate_tags_new_tag(manager, mock_session):
    """Test associating new tags creates them"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None # Tag not found
    mock_session.execute.return_value = mock_result
    
    await manager._associate_tags(manager, mock_session, "v1", ["new_tag"])
    
    # Check if new tag was added
    assert mock_session.add.call_count == 2 # 1 for Tag, 1 for PromptTag
    args, _ = mock_session.add.call_args_list[0]
    assert isinstance(args[0], Tag)
    assert args[0].name == "new_tag"

@pytest.mark.asyncio
async def test_associate_principles_not_found(manager, mock_session):
    """Test error when principle not found"""
    mock_ref = MagicMock()
    mock_ref.principle_name = "missing"
    mock_ref.version = "latest"
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    with pytest.raises(ValidationError, match="Principle missing not found"):
        await manager._associate_principles(manager, mock_session, "v1", [mock_ref])

@pytest.mark.asyncio
async def test_associate_client_creates_default(manager, mock_session):
    """Test associating non-existent client creates default one"""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    
    await manager._associate_client(manager, mock_session, "v1", "unknown_client")
    
    # Verify client creation
    assert mock_session.add.call_count >= 1
    args, _ = mock_session.add.call_args_list[0]
    assert isinstance(args[0], LLMClient)
    assert args[0].name == "unknown_client"
