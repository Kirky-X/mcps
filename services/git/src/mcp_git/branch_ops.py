try:
    from typing import List, Optional, Literal
except ImportError:
    from typing import List, Optional
    from typing_extensions import Literal
import pygit2
from .errors import GitError, GitErrorCode
from .read_ops import _get_repo

def git_branch(
    repo_path: str,
    branch_type: Literal["local", "remote", "all"] = "local",
    contains: Optional[str] = None,
    not_contains: Optional[str] = None
) -> List[str]:
    repo = _get_repo(repo_path)
    branches = []
    
    # Pre-resolve commit OIDs for filtering if needed
    contains_oid = None
    not_contains_oid = None
    
    if contains:
        try:
            contains_oid = repo.revparse_single(contains).id
        except (KeyError, ValueError):
            raise GitError(GitErrorCode.INVALID_PARAMETER, f"Invalid 'contains' reference: {contains}")
            
    if not_contains:
        try:
            not_contains_oid = repo.revparse_single(not_contains).id
        except (KeyError, ValueError):
            raise GitError(GitErrorCode.INVALID_PARAMETER, f"Invalid 'not_contains' reference: {not_contains}")

    def should_include_branch(branch_name: str, is_remote: bool = False) -> bool:
        if not contains_oid and not not_contains_oid:
            return True
            
        try:
            # Get branch target commit
            branch_ref_name = branch_name if not is_remote else f"refs/remotes/{branch_name}"
            # For local branches, repo.lookup_branch returns branch object, but we iterate names
            # Using lookup_branch with appropriate type
            branch_type_flag = pygit2.GIT_BRANCH_REMOTE if is_remote else pygit2.GIT_BRANCH_LOCAL
            branch = repo.lookup_branch(branch_name, branch_type_flag)
            
            if not branch:
                return False
                
            branch_target_oid = branch.target
            
            # Check 'contains': branch tip must reach contains_oid
            if contains_oid:
                # If contains_oid is reachable from branch_target_oid
                # pygit2.Repository.descendant_of(commit, ancestor) -> bool
                # Note: descendant_of checks if first arg is descendant of second arg
                # i.e., is branch_target_oid a descendant of contains_oid?
                is_descendant = repo.descendant_of(branch_target_oid, contains_oid)
                # Also check equality
                if branch_target_oid != contains_oid and not is_descendant:
                    return False
            
            # Check 'not_contains': not_contains_oid must NOT be reachable from branch tip
            if not_contains_oid:
                is_descendant = repo.descendant_of(branch_target_oid, not_contains_oid)
                if branch_target_oid == not_contains_oid or is_descendant:
                    return False
                    
            return True
        except Exception:
            # If any error occurs during reachability check, exclude branch
            return False

    try:
        if branch_type in ["local", "all"]:
            for branch_name in repo.branches.local:
                if should_include_branch(branch_name, is_remote=False):
                    branches.append(branch_name)
            
        if branch_type in ["remote", "all"]:
             for branch_name in repo.branches.remote:
                 if should_include_branch(branch_name, is_remote=True):
                    branches.append(branch_name)
                 
    except Exception as e:
        # If we fail to iterate, we might want to return what we have or raise
        # For now, matching original "pass" but with logging if we had it
        pass
        
    return branches

def git_create_branch(
    repo_path: str,
    branch_name: str,
    base_branch: Optional[str] = None
) -> str:
    repo = _get_repo(repo_path)
    
    try:
        # Determine target commit
        if base_branch:
            # Look up base branch
            branch = repo.lookup_branch(base_branch)
            if not branch:
                 raise GitError(GitErrorCode.INVALID_BRANCH, f"Base branch not found: {base_branch}")
            commit = branch.peel()
        else:
            # Use HEAD
            commit = repo.head.peel()
            
        repo.create_branch(branch_name, commit)
        return f"Branch {branch_name} created"
        
    except ValueError: # Branch exists
        raise GitError(GitErrorCode.OPERATION_FAILED, f"Branch {branch_name} already exists")
    except Exception as e:
        raise GitError(GitErrorCode.OPERATION_FAILED, str(e))

def git_checkout(repo_path: str, branch_name: str) -> str:
    repo = _get_repo(repo_path)
    
    try:
        # Check if branch exists
        branch = repo.lookup_branch(branch_name)
        if not branch:
             raise GitError(GitErrorCode.INVALID_BRANCH, f"Branch not found: {branch_name}")
             
        # Checkout
        repo.checkout(branch)
        return f"Switched to branch {branch_name}"
        
    except pygit2.GitError as e:
        # Could be conflict
        raise GitError(GitErrorCode.OPERATION_FAILED, f"Checkout failed: {str(e)}")
