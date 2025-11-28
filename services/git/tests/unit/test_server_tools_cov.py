import pytest
from unittest.mock import patch
from mcp_git.errors import GitError, GitErrorCode
import mcp_git.server as srv


def make_error(code=GitErrorCode.OPERATION_FAILED):
    return GitError(code, "err", suggestion="sug", details={"k": "v"})


@pytest.mark.parametrize("tool_name, args, ok_value", [
    ("git_status", ("/repo",), ["Clean working tree"]),
    ("git_log", ("/repo", 5, None, None), [{"hash": "h"}]),
    ("git_log_recent", ("/repo", "24h"), [{"hash": "h"}]),
    ("git_show", ("/repo", "HEAD"), {"hash": "h"}),
    ("git_diff", ("/repo", None, "all", 3), "diff"),
    ("git_add", ("/repo", ["a.txt"]), ["a.txt"]),
    ("git_reset", ("/repo",), "All changes unstaged"),
    ("git_commit", ("/repo", "msg"), "abcd"),
    ("git_restore", ("/repo", ["a.txt"], False), "Files restored"),
    ("git_branch", ("/repo", "local", None, None), ["main"]),
    ("git_create_branch", ("/repo", "dev", None), "ok"),
    ("git_checkout", ("/repo", "dev"), "ok"),
    ("git_stash", ("/repo", "wip", False), "oid"),
    ("git_stash_pop", ("/repo", None), "popped"),
    ("git_stash_list", ("/repo",), ["stash@{0}: msg"]),
    ("git_remote", ("/repo", "list", None, None), ["origin\turl"]),
    ("git_pull", ("/repo", "origin", None), {"status": "Up to date"}),
    ("git_push", ("/repo", "origin", None, False), "Push successful"),
    ("git_merge", ("/repo", "feature", None), {"status": "Up to date"}),
    ("git_cherry_pick", ("/repo", "abcd"), "Cherry-pick of abcd successful"),
])
def test_server_tools_success(tool_name, args, ok_value):
    target_name = f"_{tool_name}"
    with patch.object(srv, target_name, return_value=ok_value):
        func = getattr(srv, tool_name)
        res = func(*args)
        assert res == ok_value


@pytest.mark.parametrize("tool_name, args", [
    ("git_status", ("/repo",)),
    ("git_log", ("/repo", 5, None, None)),
    ("git_log_recent", ("/repo", "24h")),
    ("git_show", ("/repo", "HEAD")),
    ("git_diff", ("/repo", None, "all", 3)),
    ("git_add", ("/repo", ["a.txt"])),
    ("git_reset", ("/repo",)),
    ("git_commit", ("/repo", "msg")),
    ("git_restore", ("/repo", ["a.txt"], False)),
    ("git_branch", ("/repo", "local", None, None)),
    ("git_create_branch", ("/repo", "dev", None)),
    ("git_checkout", ("/repo", "dev")),
    ("git_stash", ("/repo", "wip", False)),
    ("git_stash_pop", ("/repo", None)),
    ("git_stash_list", ("/repo",)),
    ("git_remote", ("/repo", "list", None, None)),
    ("git_pull", ("/repo", "origin", None)),
    ("git_push", ("/repo", "origin", None, False)),
    ("git_merge", ("/repo", "feature", None)),
    ("git_cherry_pick", ("/repo", "abcd")),
])
def test_server_tools_error(tool_name, args):
    target_name = f"_{tool_name}"
    with patch.object(srv, target_name, side_effect=make_error()):
        func = getattr(srv, tool_name)
        res = func(*args)
        assert isinstance(res, dict)
        assert res.get("success") is False
        assert "error" in res

