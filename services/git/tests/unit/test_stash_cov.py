import pytest
from unittest.mock import MagicMock, patch
import pygit2
from mcp_git.stash_ops import git_stash_list, git_stash_pop, git_stash


@pytest.fixture
def mock_repo():
    with patch('mcp_git.stash_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        mock.return_value = repo
        yield repo


def test_stash_list_reflog(mock_repo):
    ref = MagicMock()
    entry = MagicMock()
    entry.message = "WIP on main: 123 msg"
    ref.log.return_value = [entry]
    mock_repo.lookup_reference.return_value = ref
    res = git_stash_list("/repo")
    assert res and "stash@{0}" in res[0]


def test_stash_list_fallback_listall(mock_repo):
    mock_repo.lookup_reference.side_effect = KeyError
    # Provide listall_stashes with objects having oid
    stash_obj = MagicMock()
    stash_obj.oid = "abc"
    mock_repo.listall_stashes = MagicMock(return_value=[stash_obj])
    commit = MagicMock()
    commit.message = "stash message"
    mock_repo.get.return_value = commit
    res = git_stash_list("/repo")
    assert res and "stash@{0}" in res[0]


def test_stash_pop_index(mock_repo):
    msg = git_stash_pop("/repo", "stash@{1}")
    mock_repo.stash_pop.assert_called_with(1)
    assert "popped" in msg.lower()


def test_stash_include_untracked(mock_repo):
    # ensure flags path executes
    oid = "oid123"
    mock_repo.stash.return_value = oid
    res = git_stash("/repo", message="wip", include_untracked=True)
    assert res == oid

