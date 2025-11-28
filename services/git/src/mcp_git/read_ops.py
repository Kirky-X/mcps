import datetime
try:
    from typing import List, Optional, Literal, Dict, Any
except ImportError:
    from typing import List, Optional, Dict, Any
    from typing_extensions import Literal
import logging
import pygit2
logger = logging.getLogger("mcp_git.read_ops")

# Compatibility alias for constant naming differences across pygit2 versions
if not hasattr(pygit2, "GIT_OBJ_COMMIT") and hasattr(pygit2, "GIT_OBJECT_COMMIT"):
    pygit2.GIT_OBJ_COMMIT = pygit2.GIT_OBJECT_COMMIT
from .errors import GitError, GitErrorCode

def _get_repo(repo_path: str) -> pygit2.Repository:
    try:
        return pygit2.Repository(repo_path)
    except pygit2.GitError:
        raise GitError(
            code=GitErrorCode.NOT_A_REPOSITORY,
            message=f"Not a git repository: {repo_path}",
            suggestion="Run 'git init' or check the repo_path parameter"
        )
    except KeyError:
         # pygit2 raises KeyError sometimes for path issues
        raise GitError(
            code=GitErrorCode.REPO_NOT_FOUND,
            message=f"Repository path not found: {repo_path}"
        )

def git_health_check(repo_path: str) -> Dict[str, Any]:
    """
    Check if the git repository is healthy and accessible.
    Also verifies that the underlying git library (libgit2) is working correctly.
    """
    try:
        # 1. Check if we can load the repo
        repo = _get_repo(repo_path)
        
        # 2. Basic check: Try to access HEAD or common files
        head_reachable = False
        try:
            repo.head
            head_reachable = True
        except pygit2.GitError:
            # Empty repo has no HEAD, which is technically "healthy" but empty
            pass
            
        # Repository statistics
        commits_count = 0
        try:
            if not repo.is_empty:
                walker = repo.walk(repo.head.target, pygit2.GIT_SORT_TIME)
                for _ in walker:
                    commits_count += 1
        except Exception:
            commits_count = 0

        try:
            local_branches = list(repo.branches.local)
            branches_count = len(local_branches)
        except Exception:
            branches_count = 0

        try:
            remotes_count = len(list(repo.remotes))
        except Exception:
            remotes_count = 0

        # Versions
        py_version = getattr(pygit2, "__version__", None)
        libgit2_ver = getattr(pygit2, "libgit2_version", None)
        if callable(libgit2_ver):
            try:
                libgit2_ver = libgit2_ver()
            except Exception:
                libgit2_ver = None

        return {
            "status": "healthy",
            "repo_path": repo_path,
            "head_reachable": head_reachable,
            "is_empty": repo.is_empty,
            "libgit2_version": libgit2_ver,
            "pygit2_version": py_version,
            "repo_stats": {
                "commits": commits_count,
                "branches": branches_count,
                "remotes": remotes_count,
            },
        }
    except GitError as e:
        return {
            "status": "unhealthy",
            "error_code": e.code.value,
            "message": e.message
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error_code": GitErrorCode.OPERATION_FAILED.value,
            "message": str(e)
        }

def git_status(repo_path: str) -> List[str]:
    repo = _get_repo(repo_path)
    status_list = []
    
    try:
        for filepath, flags in repo.status().items():
            status_str = ""
            if flags & pygit2.GIT_STATUS_INDEX_NEW:
                status_str = "staged (new)"
            elif flags & pygit2.GIT_STATUS_INDEX_MODIFIED:
                status_str = "staged (modified)"
            elif flags & pygit2.GIT_STATUS_INDEX_DELETED:
                status_str = "staged (deleted)"
            elif flags & pygit2.GIT_STATUS_WT_NEW:
                status_str = "untracked"
            elif flags & pygit2.GIT_STATUS_WT_MODIFIED:
                status_str = "modified"
            elif flags & pygit2.GIT_STATUS_WT_DELETED:
                status_str = "deleted"
                
            if status_str:
                status_list.append(f"{filepath}: {status_str}")
                
        if not status_list:
            return ["Clean working tree"]
            
        return status_list
    except pygit2.GitError as e:
        raise GitError(GitErrorCode.OPERATION_FAILED, f"Failed to get status: {str(e)}")
    except Exception as e:
        raise GitError(GitErrorCode.OPERATION_FAILED, f"Unexpected error in git_status: {str(e)}")

def git_log(
    repo_path: str, 
    max_count: int = 10, 
    start_timestamp: Optional[str] = None, 
    end_timestamp: Optional[str] = None
) -> List[Dict[str, Any]]:
    repo = _get_repo(repo_path)
    
    # Improved timestamp parsing
    start_time = None
    end_time = None
    
    if start_timestamp:
        try:
            # Handle Z suffix for UTC
            ts = start_timestamp.replace('Z', '+00:00')
            start_time = datetime.datetime.fromisoformat(ts).timestamp()
        except ValueError:
            # Try basic date format YYYY-MM-DD
            try:
                start_time = datetime.datetime.strptime(start_timestamp, "%Y-%m-%d").timestamp()
            except ValueError:
                pass
            
    if end_timestamp:
        try:
            ts = end_timestamp.replace('Z', '+00:00')
            end_time = datetime.datetime.fromisoformat(ts).timestamp()
        except ValueError:
            try:
                end_time = datetime.datetime.strptime(end_timestamp, "%Y-%m-%d").timestamp()
            except ValueError:
                pass

    commits = []
    try:
        # Walk from HEAD
        walker = repo.walk(repo.head.target, pygit2.GIT_SORT_TIME)
        
        count = 0
        for commit in walker:
            # Check count first to avoid unnecessary processing
            if count >= max_count:
                break
                
            commit_time = commit.commit_time
            
            # Optimization: Since walker is sorted by time (descending),
            # if we encounter a commit older than start_time, we can stop early
            # because all subsequent commits will be even older.
            if start_time and commit_time < start_time:
                break

            if end_time and commit_time > end_time:
                continue
                
            commits.append({
                "hash": str(commit.id),
                "author": commit.author.name,
                "date": datetime.datetime.fromtimestamp(commit_time).isoformat(),
                "message": commit.message.strip()
            })
            count += 1
            
    except pygit2.GitError:
        # HEAD might not exist (empty repo)
        return []
        
    return commits

def git_log_recent(repo_path: str, period: str = "24h") -> List[Dict[str, Any]]:
    # Parse period simple implementation
    hours = 24
    if period.endswith("h"):
        try:
            hours = int(period[:-1])
        except ValueError:
            pass
            
    start_dt = datetime.datetime.now() - datetime.timedelta(hours=hours)
    return git_log(repo_path, max_count=1000, start_timestamp=start_dt.isoformat())

def git_show(repo_path: str, revision: str) -> Dict[str, Any]:
    repo = _get_repo(repo_path)
    
    try:
        obj = repo.revparse_single(revision)
        if obj.type != getattr(pygit2, "GIT_OBJ_COMMIT", getattr(pygit2, "GIT_OBJECT_COMMIT", None)):
            raise GitError(
                code=GitErrorCode.INVALID_PARAMETER,
                message=f"Revision {revision} is not a commit"
            )
            
        commit = repo.get(obj.id)
        
        # Get diff with parent (or empty if initial commit)
        if commit.parents:
            diff = repo.diff(commit.parents[0], commit)
        else:
            diff = commit.tree.diff_to_tree()
            
        return {
            "hash": str(commit.id),
            "author": commit.author.name,
            "date": datetime.datetime.fromtimestamp(commit.commit_time).isoformat(),
            "message": commit.message,
            "diff": diff.patch
        }
    except KeyError:
        raise GitError(
            code=GitErrorCode.INVALID_PARAMETER,
            message=f"Revision not found: {revision}"
        )

def git_diff(
    repo_path: str,
    mode: Literal["unstaged", "staged", "all", "commit"] = "all",
    target: Optional[str] = None,
    context_lines: int = 3
) -> str:
    repo = _get_repo(repo_path)
    
    diff = None
    
    # Common kwargs for diff functions
    diff_kwargs = {}
    # Check if pygit2 version supports context_lines in diff functions
    # Note: older versions might not, but we assume a reasonably recent version
    # If not supported, we might need to rely on default (usually 3)
    # or handle TypeError as done below.
    diff_kwargs["context_lines"] = context_lines
    
    if mode == "unstaged":
        # Diff index to workdir
        try:
            diff = repo.index.diff_to_workdir(**diff_kwargs)
        except TypeError:
            logger.warning("context_lines argument not supported by pygit2.index.diff_to_workdir in this version")
            diff = repo.index.diff_to_workdir()
    elif mode == "staged":
        # Diff HEAD to index
        try:
            diff = repo.head.peel().tree.diff_to_index(repo.index, **diff_kwargs)
        except pygit2.GitError:
            # Empty repo or no HEAD - treat as diff against empty tree
            try:
                # diff_to_tree with None means empty tree
                diff = repo.index.diff_to_tree(None, **diff_kwargs)
            except TypeError:
                logger.warning("context_lines argument not supported by pygit2.index.diff_to_tree in this version")
                diff = repo.index.diff_to_tree(None)
        except TypeError:
            logger.warning("context_lines argument not supported by pygit2.tree.diff_to_index in this version")
            diff = repo.head.peel().tree.diff_to_index(repo.index)
            
    elif mode == "all":
        # HEAD to workdir (staged + unstaged)
        try:
            # diff_to_workdir on tree compares tree -> workdir
            diff = repo.head.peel().tree.diff_to_workdir(**diff_kwargs)
        except pygit2.GitError:
            # No HEAD -> just workdir content
            try:
                diff = repo.index.diff_to_workdir(**diff_kwargs)
            except TypeError:
                logger.warning("context_lines argument not supported by pygit2.index.diff_to_workdir in this version")
                diff = repo.index.diff_to_workdir()
        except TypeError:
             # Fallback if context_lines is not supported as kwarg
             logger.warning("context_lines argument not supported by pygit2.tree.diff_to_workdir in this version")
             diff = repo.head.peel().tree.diff_to_workdir()
             
    elif mode == "commit":
        if not target:
             raise GitError(GitErrorCode.INVALID_PARAMETER, "Target required for commit diff")
        # Simple implementation: diff target vs its parent
        return git_show(repo_path, target)["diff"] or ""
        
    return diff.patch if diff else ""
