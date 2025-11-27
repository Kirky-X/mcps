import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import pygit2
from mcp_git.branch_ops import git_branch, git_create_branch, git_checkout
from mcp_git.stash_ops import git_stash, git_stash_pop, git_stash_list
from mcp_git.remote_ops import git_remote, git_pull, git_push
from mcp_git.advanced_ops import git_merge, git_cherry_pick
from mcp_git.errors import GitError, GitErrorCode

@pytest.fixture
def mock_repo():
    with patch('mcp_git.branch_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        mock.return_value = repo
        yield repo

@pytest.fixture
def mock_repo_stash():
    with patch('mcp_git.stash_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        mock.return_value = repo
        yield repo

@pytest.fixture
def mock_repo_remote():
    with patch('mcp_git.remote_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        mock.return_value = repo
        yield repo

@pytest.fixture
def mock_repo_adv():
    with patch('mcp_git.advanced_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        mock.return_value = repo
        yield repo

# TC-BRANCH-001
def test_git_branch_list(mock_repo):
    # Mocking pygit2.Repository.branches.local and .remote
    # The property access needs to be mocked correctly on the instance
    
    # We need to mock the iterator behavior for branches.local/remote
    # pygit2.Branches behaves like a dict-like object
    
    mock_repo.branches = MagicMock()
    mock_repo.branches.local = ["main", "dev"]
    mock_repo.branches.remote = ["origin/main"]
    
    result = git_branch("path", branch_type="local")
    assert "main" in result
    assert "dev" in result

# TC-CREATE-001
def test_git_create_branch(mock_repo):
    mock_repo.head.peel.return_value = "commit"
    result = git_create_branch("path", "dev")
    mock_repo.create_branch.assert_called_with("dev", "commit")
    assert "created" in result

# TC-CREATE-002
def test_git_create_branch_exists(mock_repo):
    mock_repo.create_branch.side_effect = ValueError
    with pytest.raises(GitError) as exc:
        git_create_branch("path", "dev")
    assert exc.value.code == GitErrorCode.OPERATION_FAILED

# TC-CHECKOUT-001
def test_git_checkout(mock_repo):
    mock_repo.lookup_branch.return_value = "branch_obj"
    result = git_checkout("path", "dev")
    mock_repo.checkout.assert_called_with("branch_obj")
    assert "Switched" in result

# TC-CHECKOUT-002
def test_git_checkout_conflict(mock_repo):
    mock_repo.lookup_branch.return_value = "branch_obj"
    mock_repo.checkout.side_effect = pygit2.GitError("Conflict")
    with pytest.raises(GitError) as exc:
        git_checkout("path", "dev")
    assert exc.value.code == GitErrorCode.OPERATION_FAILED

# TC-STASH-001
def test_git_stash(mock_repo_stash):
    mock_repo_stash.stash.return_value = "stash_oid"
    result = git_stash("path", "wip")
    assert result == "stash_oid"

# TC-STASH-002
def test_git_stash_pop(mock_repo_stash):
    result = git_stash_pop("path")
    mock_repo_stash.stash_pop.assert_called()
    assert "popped" in result

# TC-STASH-003
def test_git_stash_list(mock_repo_stash):
    # stash_foreach is a method on Repository
    # It takes a callback
    
    # We just want to verify it's called. The actual list population happens in the callback
    # which we can't easily trigger here without implementing stash_foreach logic in mock
    # So we'll just check the call.
    
    # Updated logic: tries listall_stashes, then lookup_reference("refs/stash")
    
    # Let's mock lookup_reference to return something with a log()
    mock_ref = MagicMock()
    mock_log_entry = MagicMock()
    mock_log_entry.message = "WIP on master: 12345 msg"
    mock_ref.log.return_value = [mock_log_entry]
    
    mock_repo_stash.lookup_reference.return_value = mock_ref
    
    result = git_stash_list("path")
    
    # It should look up refs/stash
    mock_repo_stash.lookup_reference.assert_called_with("refs/stash")
    
    # And return formatted string
    assert len(result) == 1
    assert "stash@{0}" in result[0]

# TC-REMOTE-001
def test_git_remote_add(mock_repo_remote):
    # remotes is a property of Repository that returns a RemoteCollection
    # We need to mock the behavior of repo.remotes.create
    
    mock_remotes_collection = MagicMock()
    # Configure the property on the instance
    type(mock_repo_remote).remotes = PropertyMock(return_value=mock_remotes_collection)
    # But wait, MagicMock usually handles property access automatically unless specs are involved
    # Since we used spec=pygit2.Repository, accessing 'remotes' might fail if not in spec or if spec=True
    
    # Let's simplify: the error was AttributeError: Mock object has no attribute 'remotes'
    # This implies 'remotes' attribute is missing on the mock object.
    # We can attach it manually.
    
    mock_repo_remote.remotes = MagicMock()
    
    result = git_remote("path", "add", "origin", "url")
    mock_repo_remote.remotes.create.assert_called_with("origin", "url")
    assert "added" in result

# TC-PULL-001
def test_git_pull(mock_repo_remote):
    mock_repo_remote.remotes = MagicMock()
    mock_remote = MagicMock()
    mock_repo_remote.remotes.__getitem__.return_value = mock_remote
    
    # Mock lookup branch for remote ref
    mock_repo_remote.lookup_branch.return_value = MagicMock()
    
    # Mock merge analysis - Fast forward
    mock_repo_remote.merge_analysis.return_value = (pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD, None)
    
    result = git_pull("path", "origin")
    assert result["status"] == "Fast-forward"

# TC-PUSH-001
def test_git_push(mock_repo_remote):
    mock_repo_remote.remotes = MagicMock()
    mock_remote = MagicMock()
    mock_repo_remote.remotes.__getitem__.return_value = mock_remote
    
    result = git_push("path", "origin")
    mock_remote.push.assert_called()
    assert "successful" in result

# TC-PUSH-002
def test_git_push_rejected(mock_repo_remote):
    mock_repo_remote.remotes = MagicMock()
    mock_remote = MagicMock()
    mock_remote.push.side_effect = pygit2.GitError("Rejected")
    mock_repo_remote.remotes.__getitem__.return_value = mock_remote
    
    with pytest.raises(GitError) as exc:
        git_push("path", "origin")
    assert exc.value.code == GitErrorCode.NETWORK_ERROR

# TC-MERGE-001
def test_git_merge_success(mock_repo_adv):
    # Mock lookup
    mock_branch = MagicMock()
    mock_branch.target = "commit_id"
    mock_repo_adv.lookup_branch.return_value = mock_branch
    
    # Mock analysis - Normal merge
    mock_repo_adv.merge_analysis.return_value = (pygit2.GIT_MERGE_ANALYSIS_NORMAL, None)
    mock_repo_adv.index.conflicts = None
    
    result = git_merge("path", "feature")
    mock_repo_adv.merge.assert_called()
    mock_repo_adv.create_commit.assert_called()
    assert result["status"] == "Merge committed"

# TC-MERGE-002
def test_git_merge_conflict(mock_repo_adv):
    mock_branch = MagicMock()
    mock_branch.target = "commit_id"
    mock_repo_adv.lookup_branch.return_value = mock_branch
    
    mock_repo_adv.merge_analysis.return_value = (pygit2.GIT_MERGE_ANALYSIS_NORMAL, None)
    mock_repo_adv.index.conflicts = True # Conflict
    
    with pytest.raises(GitError) as exc:
        git_merge("path", "feature")
    assert exc.value.code == GitErrorCode.MERGE_CONFLICT

# TC-CHERRY-001
def test_git_cherry_pick(mock_repo_adv):
    mock_commit = MagicMock(spec=pygit2.Commit)
    mock_commit.id = "hash"
    mock_commit.message = "msg"
    mock_repo_adv.get.return_value = mock_commit
    
    mock_repo_adv.index.conflicts = None
    
    result = git_cherry_pick("path", "hash")
    mock_repo_adv.cherrypick.assert_called()
    mock_repo_adv.create_commit.assert_called()
    assert "successful" in result
