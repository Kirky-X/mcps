import pytest
from unittest.mock import patch
from mcp_git.dependencies import DependencyManager


def test_uv_install_attempt(monkeypatch):
    dm = DependencyManager()
    # Simulate pygit2 not installed initially
    monkeypatch.setenv("PYTHONPATH", "")
    with patch("mcp_git.dependencies.DependencyManager._check_import", side_effect=[False, True]):
        with patch("mcp_git.dependencies.subprocess.run") as mock_run:
            with patch("shutil.which", return_value="/usr/bin/uv"):
                dm.ensure_libgit2()
                mock_run.assert_called()

