from unittest.mock import patch
import logging
from mcp_git.server import main


def test_server_logging_file(monkeypatch, tmp_path):
    log_file = tmp_path / "mcp-git.log"
    monkeypatch.setattr("sys.argv", ["mcp-git", "--log-file", str(log_file), "--skip-libgit2-install"])
    with patch("mcp_git.server.mcp.run"):
        main()
    assert log_file.exists()

