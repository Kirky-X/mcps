import logging
import time
import argparse
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP
from mcp.types import Tool
from .errors import GitError, GitErrorCode
from .dependencies import DependencyManager
from .read_ops import git_status as _git_status, git_log as _git_log, git_log_recent as _git_log_recent, git_show as _git_show, git_diff as _git_diff, git_health_check as _git_health_check
from .write_ops import git_add as _git_add, git_reset as _git_reset, git_commit as _git_commit, git_restore as _git_restore
from .branch_ops import git_branch as _git_branch, git_create_branch as _git_create_branch, git_checkout as _git_checkout
from .stash_ops import git_stash as _git_stash, git_stash_pop as _git_stash_pop, git_stash_list as _git_stash_list
from .remote_ops import git_remote as _git_remote, git_pull as _git_pull, git_push as _git_push
from .advanced_ops import git_merge as _git_merge, git_cherry_pick as _git_cherry_pick

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_git")

# Initialize MCP server
mcp = FastMCP("mcp-git")

# Initialize dependency manager
dep_manager = DependencyManager()

@mcp.tool()
def git_health_check(repo_path: str) -> Dict[str, Any]:
    """
    Check the health of the git system and repository.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Dictionary with health status and system info
    """
    try:
        return _git_health_check(repo_path)
    except GitError as e:
        # Don't raise RuntimeError here, return unhealthy status
        return {
            "status": "unhealthy",
            "error_code": e.code.value,
            "message": e.message
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@mcp.tool()
def git_status(repo_path: str) -> List[str]:
    """
    Get the status of the repository.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        List of status strings
    """
    try:
        return _git_status(repo_path)
    except GitError as e:
        logger.error(f"Error in git_status: {e}")
        return e.to_dict()

@mcp.tool()
def git_log(
    repo_path: str,
    max_count: int = 10,
    start_timestamp: str = None,
    end_timestamp: str = None
) -> List[Dict[str, Any]]:
    """
    Get the commit log of the repository.
    
    Args:
        repo_path: Path to the git repository
        max_count: Maximum number of commits to return
        start_timestamp: Only return commits after this timestamp (ISO format)
        end_timestamp: Only return commits before this timestamp (ISO format)
        
    Returns:
        List of commit dictionaries
    """
    try:
        return _git_log(repo_path, max_count, start_timestamp, end_timestamp)
    except GitError as e:
        logger.error(f"Error in git_log: {e}")
        return e.to_dict()

@mcp.tool()
def git_log_recent(
    repo_path: str,
    period: str = "24h"
) -> List[Dict[str, Any]]:
    """
    Get recent commits within a specified time period.
    
    Args:
        repo_path: Path to the git repository
        period: Time period (e.g., "24h", "7d")
        
    Returns:
        List of recent commit dictionaries
    """
    try:
        return _git_log_recent(repo_path, period)
    except GitError as e:
        logger.error(f"Error in git_log_recent: {e}")
        return e.to_dict()

@mcp.tool()
def git_show(
    repo_path: str,
    revision: str = "HEAD"
) -> Dict[str, Any]:
    """
    Show details of a commit or object.
    
    Args:
        repo_path: Path to the git repository
        revision: Hash of the object to show (default: HEAD)
        
    Returns:
        Dictionary with object details
    """
    try:
        return _git_show(repo_path, revision)
    except GitError as e:
        logger.error(f"Error in git_show: {e}")
        return e.to_dict()

@mcp.tool()
def git_diff(
    repo_path: str,
    target: str = None,
    mode: str = "all",
    context_lines: int = 3
) -> str:
    """
    Show changes between commits, commit and working tree, etc.
    
    Args:
        repo_path: Path to the git repository
        target: Target commit or branch (optional, used for commit diff)
        mode: Diff mode ('staged', 'unstaged', 'all', 'commit')
        context_lines: Number of context lines (default: 3)
        
    Returns:
        Diff output string
    """
    start_time = time.time()
    try:
        result = _git_diff(repo_path, mode, target, context_lines)
        duration = (time.time() - start_time) * 1000
        logger.debug(f"git_diff executed in {duration:.2f}ms for repo {repo_path}")
        return result
    except GitError as e:
        logger.error(f"Error in git_diff: {e}")
        return e.to_dict()

@mcp.tool()
def git_add(repo_path: str, files: List[str]) -> List[str]:
    """
    Add file contents to the index.
    
    Args:
        repo_path: Path to the git repository
        files: List of file paths to add
        
    Returns:
        List of added files
    """
    try:
        return _git_add(repo_path, files)
    except GitError as e:
        logger.error(f"Error in git_add: {e}")
        return e.to_dict()

@mcp.tool()
def git_reset(repo_path: str) -> str:
    """
    Reset current HEAD to the specified state.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        Status message
    """
    try:
        return _git_reset(repo_path)
    except GitError as e:
        logger.error(f"Error in git_reset: {e}")
        return e.to_dict()

@mcp.tool()
def git_commit(repo_path: str, message: str) -> str:
    """
    Record changes to the repository.
    
    Args:
        repo_path: Path to the git repository
        message: Commit message
        
    Returns:
        Commit hash
    """
    try:
        return _git_commit(repo_path, message)
    except GitError as e:
        logger.error(f"Error in git_commit: {e}")
        return e.to_dict()

@mcp.tool()
def git_restore(repo_path: str, files: List[str], staged: bool = False) -> str:
    """
    Restore working tree files.
    
    Args:
        repo_path: Path to the git repository
        files: List of files to restore
        staged: If true, restore the index (unstage)
        
    Returns:
        Status message
    """
    try:
        return _git_restore(repo_path, files, staged)
    except GitError as e:
        logger.error(f"Error in git_restore: {e}")
        return e.to_dict()

@mcp.tool()
def git_branch(
    repo_path: str,
    branch_type: str = "local",
    contains: str = None,
    not_contains: str = None
) -> List[str]:
    """
    List branches.
    
    Args:
        repo_path: Path to the git repository
        branch_type: 'local', 'remote', or 'all'
        contains: Filter by commit contained
        not_contains: Filter by commit not contained
        
    Returns:
        List of branch names
    """
    try:
        # Cast string to Literal manually if needed, but python is dynamic
        return _git_branch(repo_path, branch_type, contains, not_contains)
    except GitError as e:
        logger.error(f"Error in git_branch: {e}")
        return e.to_dict()

@mcp.tool()
def git_create_branch(
    repo_path: str,
    branch_name: str,
    base_branch: str = None
) -> str:
    """
    Create a new branch.
    
    Args:
        repo_path: Path to the git repository
        branch_name: Name of the new branch
        base_branch: Base branch to start from (optional)
        
    Returns:
        Status message
    """
    try:
        return _git_create_branch(repo_path, branch_name, base_branch)
    except GitError as e:
        logger.error(f"Error in git_create_branch: {e}")
        return e.to_dict()

@mcp.tool()
def git_checkout(repo_path: str, branch_name: str) -> str:
    """
    Switch branches or restore working tree files.
    
    Args:
        repo_path: Path to the git repository
        branch_name: Branch name to checkout
        
    Returns:
        Status message
    """
    try:
        return _git_checkout(repo_path, branch_name)
    except GitError as e:
        logger.error(f"Error in git_checkout: {e}")
        return e.to_dict()

@mcp.tool()
def git_stash(
    repo_path: str,
    message: str = None,
    include_untracked: bool = False
) -> str:
    """
    Stash the changes in a dirty working directory away.
    
    Args:
        repo_path: Path to the git repository
        message: Stash message (optional)
        include_untracked: Whether to stash untracked files
        
    Returns:
        Stash commit hash
    """
    try:
        return _git_stash(repo_path, message, include_untracked)
    except GitError as e:
        logger.error(f"Error in git_stash: {e}")
        return e.to_dict()

@mcp.tool()
def git_stash_pop(repo_path: str, stash_id: str = None) -> str:
    """
    Remove a single stashed state from the stash list and apply it.
    
    Args:
        repo_path: Path to the git repository
        stash_id: Stash ID (optional)
        
    Returns:
        Status message
    """
    try:
        return _git_stash_pop(repo_path, stash_id)
    except GitError as e:
        logger.error(f"Error in git_stash_pop: {e}")
        return e.to_dict()

@mcp.tool()
def git_stash_list(repo_path: str) -> List[str]:
    """
    List the stash entries that you currently have.
    
    Args:
        repo_path: Path to the git repository
        
    Returns:
        List of stash entries
    """
    try:
        return _git_stash_list(repo_path)
    except GitError as e:
        logger.error(f"Error in git_stash_list: {e}")
        return e.to_dict()

@mcp.tool()
def git_remote(
    repo_path: str,
    action: str,
    name: str = None,
    url: str = None
) -> Any:
    """
    Manage set of tracked repositories.
    
    Args:
        repo_path: Path to the git repository
        action: 'list', 'add', or 'remove'
        name: Remote name (required for add/remove)
        url: Remote URL (required for add)
        
    Returns:
        Result of the operation
    """
    try:
        # Cast string to Literal manually if needed
        return _git_remote(repo_path, action, name, url)
    except GitError as e:
        logger.error(f"Error in git_remote: {e}")
        return e.to_dict()

@mcp.tool()
def git_pull(
    repo_path: str,
    remote: str = "origin",
    branch: str = None
) -> Dict[str, Any]:
    """
    Fetch from and integrate with another repository or a local branch.
    
    Args:
        repo_path: Path to the git repository
        remote: Remote name (default: origin)
        branch: Branch to pull (optional)
        
    Returns:
        Pull result dictionary
    """
    try:
        return _git_pull(repo_path, remote, branch)
    except GitError as e:
        logger.error(f"Error in git_pull: {e}")
        return e.to_dict()

@mcp.tool()
def git_push(
    repo_path: str,
    remote: str = "origin",
    branch: str = None,
    force: bool = False
) -> Any:
    """
    Update remote refs along with associated objects.
    
    Args:
        repo_path: Path to the git repository
        remote: Remote name (default: origin)
        branch: Branch to push (optional)
        force: Force push (default: False)
        
    Returns:
        Status message or error dictionary
    """
    try:
        return _git_push(repo_path, remote, branch, force)
    except GitError as e:
        logger.error(f"Error in git_push: {e}")
        return e.to_dict()

@mcp.tool()
def git_merge(
    repo_path: str,
    source: str,
    strategy: str = None
) -> Dict[str, Any]:
    """
    Merge a branch or commit into the current HEAD.
    
    Args:
        repo_path: Path to the git repository
        source: Branch name or commit hash to merge from
        strategy: Merge strategy (optional)
        
    Returns:
        Merge result dictionary
    """
    start_time = time.time()
    try:
        result = _git_merge(repo_path, source, strategy)
        duration = (time.time() - start_time) * 1000
        logger.debug(f"git_merge executed in {duration:.2f}ms for repo {repo_path}")
        return result
    except GitError as e:
        logger.error(f"Error in git_merge: {e}")
        return e.to_dict()

@mcp.tool()
def git_cherry_pick(
    repo_path: str,
    commit_hash: str
) -> str:
    """
    Cherry-pick a commit onto the current HEAD.
    
    Args:
        repo_path: Path to the git repository
        commit_hash: Hash of the commit to cherry-pick
        
    Returns:
        Status message
    """
    try:
        return _git_cherry_pick(repo_path, commit_hash)
    except GitError as e:
        logger.error(f"Error in git_cherry_pick: {e}")
        return e.to_dict()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP Git Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--skip-libgit2-install", action="store_true", help="Skip libgit2 installer chain")
    parser.add_argument("--log-file", type=str, default=None, help="Write logs to the specified file")
    args = parser.parse_args()

    # Configure logging level based on arguments
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger().setLevel(logging.DEBUG)
    if args.log_file:
        fh = logging.FileHandler(args.log_file)
        fh.setLevel(logging.DEBUG if args.debug else logging.INFO)
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        fh.setFormatter(fmt)
        logging.getLogger().addHandler(fh)
    
    # Ensure dependencies are met unless skipped
    if not args.skip_libgit2_install:
        try:
            dep_manager.ensure_libgit2()
        except Exception as e:
            logger.warning(f"Failed to ensure libgit2 dependencies: {e}")
    
    mcp.run()

# Backward-compatible alias for tests expecting health_check
def health_check(repo_path: str) -> Dict[str, Any]:
    return _git_health_check(repo_path)

if __name__ == "__main__":
    main()
