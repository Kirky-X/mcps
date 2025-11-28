import pytest
from unittest.mock import MagicMock, patch
import pygit2
from mcp_git.advanced_ops import git_merge, git_cherry_pick
from mcp_git.errors import GitError, GitErrorCode


@pytest.fixture
def mock_repo():
    with patch('mcp_git.advanced_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        mock.return_value = repo
        yield repo


def test_git_merge_up_to_date(mock_repo):
    mock_repo.merge_analysis.return_value = (pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE, None)
    # Mock lookup_branch to return an object with target attribute
    branch_obj = MagicMock()
    branch_obj.target = "abc1234"
    mock_repo.lookup_branch.return_value = branch_obj
    result = git_merge("path", "feature")
    assert result["status"] == "Up to date"


def test_git_merge_fast_forward(mock_repo):
    mock_repo.merge_analysis.return_value = (pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD, None)
    # repo.get(commit_id) called; return a dummy commit object
    dummy_commit = MagicMock()
    mock_repo.get.return_value = dummy_commit
    branch_obj = MagicMock()
    branch_obj.target = "abc1234"
    mock_repo.lookup_branch.return_value = branch_obj
    result = git_merge("path", "feature")
    assert result["status"] == "Fast-forward"


def test_git_merge_invalid_source(mock_repo):
    # lookup_branch/lookup_reference raise -> Oid(hex=source) ValueError
    mock_repo.lookup_branch.side_effect = (None)
    mock_repo.lookup_reference.side_effect = ValueError
    with pytest.raises(GitError) as exc:
        git_merge("path", "not-a-oid")
    # invalid source should be INVALID_PARAMETER by design
    assert exc.value.code == GitErrorCode.INVALID_PARAMETER


def test_git_cherry_pick_conflict(mock_repo):
    commit = MagicMock(spec=pygit2.Commit)
    commit.id = "hash"
    commit.message = "msg"
    mock_repo.get.return_value = commit
    mock_repo.index.conflicts = True
    with pytest.raises(GitError) as exc:
        git_cherry_pick("path", "hash")
    assert exc.value.code == GitErrorCode.MERGE_CONFLICT


def test_git_cherry_pick_invalid_hash(mock_repo):
    mock_repo.get.side_effect = ValueError
    with pytest.raises(GitError) as exc:
        git_cherry_pick("path", "bad")
    assert exc.value.code == GitErrorCode.INVALID_PARAMETER
