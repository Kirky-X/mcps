import time
from unittest.mock import MagicMock, patch
import pygit2
from mcp_git.read_ops import git_status, git_diff
from mcp_git.branch_ops import git_branch


def test_perf_status_branch_small_repo():
    with patch('mcp_git.read_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        repo.status.return_value = {}
        repo.branches = MagicMock()
        repo.branches.local = ["main"]
        mock.return_value = repo
        t0 = time.time()
        assert git_status('/repo') == ["Clean working tree"]
        with patch('mcp_git.branch_ops._get_repo') as mock_b:
            mock_b.return_value = repo
            assert git_branch('/repo', branch_type='local') == ["main"]
        elapsed = (time.time() - t0) * 1000
        assert elapsed < 1000  # synthetic bound to detect pathological slowness


def test_perf_diff_small_patch():
    with patch('mcp_git.read_ops._get_repo') as mock:
        repo = MagicMock(spec=pygit2.Repository)
        diff = MagicMock()
        diff.patch = "d" * 1024  # 1KB
        tree = MagicMock()
        tree.diff_to_workdir.return_value = diff
        repo.head.peel.return_value = MagicMock(tree=tree)
        mock.return_value = repo
        t0 = time.time()
        res = git_diff('/repo', mode='all')
        elapsed = (time.time() - t0) * 1000
        assert res
        assert elapsed < 2000
