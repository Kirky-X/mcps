import pytest
from unittest.mock import MagicMock, patch
import pygit2
from mcp_git.read_ops import git_diff, git_show
from mcp_git.errors import GitError, GitErrorCode


@pytest.fixture
def mock_repo():
    with patch('mcp_git.read_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        mock.return_value = repo
        yield repo


def test_git_diff_unstaged_fallback(mock_repo):
    # Make diff_to_workdir raise TypeError to hit fallback branch
    mock_repo.index.diff_to_workdir.side_effect = TypeError()
    mock_repo.index.diff_to_workdir.return_value = MagicMock(patch="diff")
    # Because side_effect overrides return_value, provide second call via side_effect list
    mock_repo.index.diff_to_workdir.side_effect = [TypeError(), MagicMock(patch="diff")]
    res = git_diff("/repo", mode="unstaged", context_lines=5)
    assert res == "diff"


def test_git_diff_staged_empty_head(mock_repo):
    # First path raises GitError (no HEAD), then fallback diff_to_tree(None)
    mock_repo.head.peel.side_effect = pygit2.GitError()
    mock_repo.index.diff_to_tree.return_value = MagicMock(patch="diff")
    res = git_diff("/repo", mode="staged")
    assert res == "diff"


def test_git_diff_all_fallback(mock_repo):
    # tree.diff_to_workdir raises TypeError -> fallback call without context_lines
    mock_tree = MagicMock()
    mock_tree.diff_to_workdir.side_effect = [TypeError(), MagicMock(patch="diff")]
    mock_repo.head.peel.return_value = MagicMock(tree=mock_tree)
    res = git_diff("/repo", mode="all")
    assert res == "diff"


def test_git_diff_commit_uses_show(mock_repo):
    with patch('mcp_git.read_ops.git_show', return_value={"diff": "commitdiff"}):
        res = git_diff("/repo", mode="commit", target="abc")
        assert res == "commitdiff"


def test_git_show_invalid_type(mock_repo):
    obj = MagicMock()
    obj.type = 0  # Not commit
    mock_repo.revparse_single.return_value = obj
    with pytest.raises(GitError) as exc:
        git_show("/repo", "abc")
    assert exc.value.code == GitErrorCode.INVALID_PARAMETER

