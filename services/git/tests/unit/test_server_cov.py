from unittest.mock import patch, MagicMock
import logging
from mcp_git.server import main


def test_server_main_args(monkeypatch, caplog):
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    test_argv = ["mcp-git", "--debug", "--skip-libgit2-install", "--log-file", "./tmp.log"]
    monkeypatch.setattr("sys.argv", test_argv)

    with patch("mcp_git.server.dep_manager.ensure_libgit2") as mock_dep:
        with patch("mcp_git.server.mcp.run") as mock_run:
            caplog.set_level(logging.INFO)
            main()
            mock_dep.assert_not_called()
            mock_run.assert_called()
