import pytest
from unittest.mock import MagicMock, patch
import pygit2
from mcp_git.remote_ops import git_remote, git_pull, git_push
from mcp_git.errors import GitError, GitErrorCode


@pytest.fixture
def mock_repo():
    with patch('mcp_git.remote_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        mock.return_value = repo
        yield repo


def test_git_remote_list(mock_repo):
    remote1 = MagicMock()
    remote1.name = "origin"
    remote1.url = "git@example.com:repo.git"
    mock_repo.remotes = [remote1]
    res = git_remote("path", "list")
    assert "origin" in res[0]


def test_git_pull_up_to_date(mock_repo):
    mock_remote = MagicMock()
    mock_repo.remotes = {"origin": mock_remote}
    mock_repo.head.shorthand = "main"
    # remote ref
    mock_branch = MagicMock()
    mock_branch.target = "target"
    mock_repo.lookup_branch.return_value = mock_branch
    mock_repo.merge_analysis.return_value = (pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE, None)
    result = git_pull("path", "origin")
    assert result["status"] == "Up to date"


def test_git_pull_merge_conflict(mock_repo):
    mock_remote = MagicMock()
    mock_repo.remotes = {"origin": mock_remote}
    mock_repo.head.shorthand = "main"
    mock_branch = MagicMock()
    mock_branch.target = "t"
    mock_repo.lookup_branch.return_value = mock_branch
    mock_repo.merge_analysis.return_value = (pygit2.GIT_MERGE_ANALYSIS_NORMAL, None)
    mock_repo.index.conflicts = True
    with pytest.raises(GitError) as exc:
        git_pull("path", "origin")
    assert exc.value.code == GitErrorCode.MERGE_CONFLICT


def test_git_push_invalid_remote(mock_repo):
    mock_repo.remotes = {}
    with pytest.raises(GitError) as exc:
        git_push("path", "nope")
    assert exc.value.code == GitErrorCode.INVALID_PARAMETER

