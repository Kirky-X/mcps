import pytest
from unittest.mock import MagicMock, patch, ANY, PropertyMock
import pygit2
from mcp_git.read_ops import git_status, git_log, git_log_recent, git_show, git_diff, git_health_check
from mcp_git.write_ops import git_add, git_reset, git_commit, git_restore
from mcp_git.errors import GitError, GitErrorCode
import datetime

@pytest.fixture
def mock_repo():
    with patch('mcp_git.read_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        mock.return_value = repo
        yield repo

@pytest.fixture
def mock_repo_write():
    with patch('mcp_git.write_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        repo.workdir = "/mock/path" # Fix for os.path operations
        mock.return_value = repo
        yield repo

# TC-HEALTH-001
def test_git_health_check_healthy(mock_repo):
    mock_repo.is_empty = False
    result = git_health_check("path")
    assert result["status"] == "healthy"
    assert result["head_reachable"] is True

# TC-HEALTH-002
def test_git_health_check_empty(mock_repo):
    mock_repo.is_empty = True
    type(mock_repo).head = PropertyMock(side_effect=pygit2.GitError)
    result = git_health_check("path")
    assert result["status"] == "healthy"
    assert result["head_reachable"] is False
    assert result["is_empty"] is True

# TC-HEALTH-003
def test_git_health_check_unhealthy():
    with patch('mcp_git.read_ops._get_repo', side_effect=GitError(GitErrorCode.NOT_A_REPOSITORY, "Not a repo")):
        result = git_health_check("path")
        assert result["status"] == "unhealthy"
        assert result["error_code"] == GitErrorCode.NOT_A_REPOSITORY.value

# TC-STATUS-001
def test_git_status_clean(mock_repo):
    mock_repo.status.return_value = {}
    result = git_status("path")
    assert result == ["Clean working tree"]

# TC-STATUS-002
def test_git_status_modified(mock_repo):
    mock_repo.status.return_value = {"a.txt": pygit2.GIT_STATUS_WT_MODIFIED}
    result = git_status("path")
    assert result == ["a.txt: modified"]

# TC-STATUS-003
def test_git_status_staged(mock_repo):
    mock_repo.status.return_value = {"a.txt": pygit2.GIT_STATUS_INDEX_MODIFIED}
    result = git_status("path")
    assert result == ["a.txt: staged (modified)"]

# TC-STATUS-004
def test_git_status_untracked(mock_repo):
    mock_repo.status.return_value = {"new.txt": pygit2.GIT_STATUS_WT_NEW}
    result = git_status("path")
    assert result == ["new.txt: untracked"]

# TC-STATUS-005
def test_git_status_not_repo():
    with patch('mcp_git.read_ops._get_repo', side_effect=GitError(GitErrorCode.NOT_A_REPOSITORY, "Not a git repository")):
        with pytest.raises(GitError) as exc:
            git_status("/tmp/not-git")
        assert exc.value.code == GitErrorCode.NOT_A_REPOSITORY

# TC-LOG-001
def test_git_log_basic(mock_repo):
    mock_commit = MagicMock()
    mock_commit.id = "hash123"
    mock_commit.author.name = "Author"
    mock_commit.commit_time = 1609459200
    mock_commit.message = "message"
    
    mock_walker = MagicMock()
    mock_walker.__iter__.return_value = [mock_commit]
    mock_repo.walk.return_value = mock_walker
    
    result = git_log("path", max_count=5)
    assert len(result) == 1
    assert result[0]["hash"] == "hash123"

# TC-LOG-002
def test_git_log_time_range(mock_repo):
    c1 = MagicMock(commit_time=1000)
    c2 = MagicMock(commit_time=2000)
    c3 = MagicMock(commit_time=3000)
    
    # Walker yields in reverse time order by default (newest first)
    # The read_ops.py implementation assumes walker is sorted by time
    mock_walker = MagicMock()
    mock_walker.__iter__.return_value = [c3, c2, c1]
    mock_repo.walk.return_value = mock_walker
    
    # 1500 to 2500 should only match c2 (2000)
    start = datetime.datetime.fromtimestamp(1500).isoformat()
    end = datetime.datetime.fromtimestamp(2500).isoformat()
    
    result = git_log("path", start_timestamp=start, end_timestamp=end)
    assert len(result) == 1
    # Should match c2
    assert result[0]["date"] == datetime.datetime.fromtimestamp(2000).isoformat()

# TC-LOG-003
def test_git_log_recent(mock_repo):
    # This just wraps git_log, mainly testing parameter passing
    with patch('mcp_git.read_ops.git_log') as mock_log:
        git_log_recent("path", period="24h")
        mock_log.assert_called_once()
        _, kwargs = mock_log.call_args
        assert kwargs['start_timestamp'] is not None

# TC-LOG-004
def test_git_log_invalid_time(mock_repo):
    # Should ignore invalid time and return results
    mock_repo.walk.return_value = []
    git_log("path", start_timestamp="invalid")
    mock_repo.walk.assert_called()

# TC-LOG-005
def test_git_log_empty_repo(mock_repo):
    mock_repo.walk.side_effect = pygit2.GitError("Empty")
    result = git_log("path")
    assert result == []

# TC-SHOW-001
def test_git_show_commit(mock_repo):
    mock_obj = MagicMock()
    mock_obj.type = pygit2.GIT_OBJ_COMMIT
    mock_obj.id = "hash"
    mock_repo.revparse_single.return_value = mock_obj
    
    mock_commit = MagicMock()
    mock_commit.id = "hash"
    mock_commit.parents = [MagicMock()]
    mock_repo.get.return_value = mock_commit
    
    result = git_show("path", "hash")
    assert result["hash"] == "hash"

# TC-SHOW-002
def test_git_show_invalid(mock_repo):
    mock_repo.revparse_single.side_effect = KeyError
    with pytest.raises(GitError) as exc:
        git_show("path", "invalid")
    assert exc.value.code == GitErrorCode.INVALID_PARAMETER

# TC-DIFF-001
def test_git_diff_unstaged(mock_repo):
    mock_diff = MagicMock()
    mock_diff.patch = "diff content"
    mock_repo.index.diff_to_workdir.return_value = mock_diff
    
    result = git_diff("path", mode="unstaged")
    assert result == "diff content"

# TC-DIFF-002
def test_git_diff_staged(mock_repo):
    mock_diff = MagicMock()
    mock_diff.patch = "diff content"
    mock_repo.head.peel().tree.diff_to_index.return_value = mock_diff
    
    result = git_diff("path", mode="staged")
    assert result == "diff content"

# TC-DIFF-003
def test_git_diff_all(mock_repo):
    mock_diff = MagicMock()
    mock_diff.patch = "diff content"
    mock_repo.head.peel().tree.diff_to_workdir.return_value = mock_diff
    
    result = git_diff("path", mode="all")
    assert result == "diff content"

# TC-ADD-001
def test_git_add(mock_repo_write):
    # Mock os.path behavior for valid paths
    with patch('os.path.isabs', return_value=False), \
         patch('os.path.isdir', return_value=False):
        
        # Ensure add_all is not present to force the fallback loop
        del mock_repo_write.index.add_all
        
        result = git_add("path", ["a.txt"])
        mock_repo_write.index.add.assert_called_with("a.txt")
        mock_repo_write.index.write.assert_called()
        assert "a.txt" in result

# TC-ADD-002
def test_git_add_missing(mock_repo_write):
    # Mocking os.path.relpath and os.path.isabs behavior for valid paths
    # But here we want to trigger OSError during repo.index.add
    
    # We need to ensure os.path calls don't fail before index.add
    with patch('os.path.isabs', return_value=False), \
         patch('os.path.isdir', return_value=False):
         
        # Ensure add_all is not present
        del mock_repo_write.index.add_all
        
        mock_repo_write.index.add.side_effect = OSError
        
        # We also need to mock workdir since git_add uses it
        mock_repo_write.workdir = "/mock/path"
        
        with pytest.raises(GitError) as exc:
            git_add("path", ["missing.txt"])
        assert exc.value.code == GitErrorCode.REPO_NOT_FOUND

# TC-RESET-001
def test_git_reset(mock_repo_write):
    result = git_reset("path")
    mock_repo_write.reset.assert_called()
    assert "All changes unstaged" in result

# TC-COMMIT-001
def test_git_commit(mock_repo_write):
    # Mock index has entries
    mock_repo_write.index.__bool__.return_value = True 
    # Mock index has length > 0
    mock_repo_write.index.__len__.return_value = 1
    
    # Mock diff has changes
    mock_diff = MagicMock()
    mock_diff.__bool__.return_value = True
    # In new implementation, it checks len(diff)
    mock_diff.__len__.return_value = 1
    mock_repo_write.diff.return_value = mock_diff # Mock repo.diff() call
    
    mock_repo_write.create_commit.return_value = "new_hash"
    
    result = git_commit("path", "feat: test")
    assert result == "new_hash"

# TC-COMMIT-002
def test_git_commit_empty(mock_repo_write):
    # Case 1: Index is empty (len=0) -> should trigger "Nothing to commit" check?
    # Actually code says: if not repo.index: (checks if empty container)
    # If empty, it checks diff to HEAD.
    
    # Let's verify the logic in write_ops.py:
    # if not repo.index:
    #    diff = ...diff_to_index...
    #    if not diff: raise NOTHING_TO_COMMIT
    
    # So to trigger error, we need index to be empty AND diff to be empty.
    
    # Mock index is empty
    mock_repo_write.index.__bool__.return_value = False
    mock_repo_write.index.__len__.return_value = 0
    
    # Mock diff is empty - fix for updated implementation using diff.patch
    mock_diff = MagicMock()
    mock_diff.patch = "" # patch is empty string
    # Mock len(diff) == 0 for updated implementation
    mock_diff.__len__.return_value = 0
    mock_repo_write.diff.return_value = mock_diff # Mock repo.diff() call
    
    # Also need to ensure we don't fall into the except pygit2.GitError block unless intended
    # The new implementation calls repo.diff(head.tree, cached=True)
    
    with pytest.raises(GitError) as exc:
        git_commit("path", "empty")
    assert exc.value.code == GitErrorCode.NOTHING_TO_COMMIT

# TC-RESTORE-001
def test_git_restore(mock_repo_write):
    result = git_restore("path", ["a.txt"])
    mock_repo_write.checkout.assert_called()
    assert "Files restored" in result
