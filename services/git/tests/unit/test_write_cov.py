import pytest
from unittest.mock import MagicMock, patch
import pygit2
from mcp_git.write_ops import git_add, git_commit, git_reset, git_restore
from mcp_git.errors import GitError, GitErrorCode


@pytest.fixture
def mock_repo():
    with patch('mcp_git.write_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        repo.workdir = "/repo"
        mock.return_value = repo
        yield repo


def test_git_add_basic(mock_repo):
    # Ensure hasattr(repo.index, 'add_all') is False
    try:
        del mock_repo.index.add_all
    except Exception:
        pass
    res = git_add("/repo", ["a.txt"]) 
    assert "a.txt" in res


def test_git_commit_nothing(mock_repo):
    head = MagicMock()
    mock_repo.head.peel.return_value = head
    diff = MagicMock()
    diff.__len__.return_value = 0
    mock_repo.diff.return_value = diff
    with pytest.raises(GitError) as exc:
        git_commit("/repo", "msg")
    assert exc.value.code == GitErrorCode.NOTHING_TO_COMMIT


def test_git_reset_empty_repo(mock_repo):
    mock_repo.head.peel.side_effect = pygit2.GitError()
    msg = git_reset("/repo")
    assert "unstaged" in msg


def test_git_restore_workdir(mock_repo):
    msg = git_restore("/repo", ["a.txt"], staged=False)
    assert "Files restored" in msg
