import pytest
from unittest.mock import MagicMock, patch
import pygit2
from mcp_git.branch_ops import git_branch


@pytest.fixture
def mock_repo():
    with patch('mcp_git.branch_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        mock.return_value = repo
        yield repo


def test_git_branch_local_and_remote(mock_repo):
    mock_repo.branches = MagicMock()
    mock_repo.branches.local = ["main", "dev"]
    mock_repo.branches.remote = ["origin/main"]

    # lookup works for contains filters
    mock_branch_obj = MagicMock()
    mock_branch_obj.target = "abc"
    mock_repo.lookup_branch.return_value = mock_branch_obj

    res_local = git_branch("/repo", branch_type="local")
    assert "main" in res_local

    res_all = git_branch("/repo", branch_type="all")
    assert "origin/main" in res_all

