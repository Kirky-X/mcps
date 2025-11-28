from typing import Dict, Any, Optional
import pygit2
from .errors import GitError, GitErrorCode
from .read_ops import _get_repo
import re

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
        strategy: Merge strategy (currently unused, kept for interface compatibility)
        
    Returns:
        Dict containing merge result status
    """
    repo = _get_repo(repo_path)
    
    if strategy:
        # TODO: Implement specific merge strategies if needed/possible with pygit2
        # For now, we just log/warn or ignore, but since we don't have a logger here easily 
        # without importing, we'll just proceed with default behavior.
        pass
    
    try:
        commit_id = None
        try:
            branch = repo.lookup_branch(source)
            if branch:
                commit_id = branch.target
            else:
                ref = repo.lookup_reference(source)
                commit_id = ref.target
        except (KeyError, ValueError):
            # Validate hex before attempting Oid to avoid unexpected behavior
            if not re.fullmatch(r"[0-9a-fA-F]{7,40}", source or ""):
                raise GitError(GitErrorCode.INVALID_PARAMETER, f"Invalid source reference: {source}")
            try:
                commit_id = pygit2.Oid(hex=source)
            except ValueError:
                raise GitError(GitErrorCode.INVALID_PARAMETER, f"Invalid source reference: {source}")

        if commit_id is None:
            raise GitError(GitErrorCode.INVALID_PARAMETER, f"Invalid source reference: {source}")

        # Perform merge analysis (accept commit_id as returned by repo APIs)
        analysis, _ = repo.merge_analysis(commit_id)
        
        if analysis & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
            return {"status": "Up to date", "files_changed": 0}
            
        elif analysis & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
            # Fast-forward
            repo.checkout_tree(repo.get(commit_id))
            repo.head.set_target(commit_id)
            return {"status": "Fast-forward", "files_changed": 0}
            
        elif analysis & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
            # Normal merge
            repo.merge(commit_id)
            
            if repo.index.conflicts:
                raise GitError(GitErrorCode.MERGE_CONFLICT, "Merge conflict detected. Please resolve conflicts manually.")
            
            # Create merge commit
            user = repo.default_signature
            tree = repo.index.write_tree()
            repo.create_commit("HEAD", user, user, f"Merge {source}", tree, [repo.head.target, commit_id])
            repo.state_cleanup()
            
            return {"status": "Merge committed", "files_changed": 0}
            
        else:
            raise GitError(GitErrorCode.OPERATION_FAILED, "Unknown merge analysis result or merge not possible")

    except pygit2.GitError as e:
        raise GitError(GitErrorCode.OPERATION_FAILED, str(e))
    except GitError:
        raise
    except Exception as e:
        # Classify pre-merge resolution problems as invalid parameter when applicable
        raise GitError(GitErrorCode.INVALID_PARAMETER, f"Invalid input or merge state: {str(e)}")


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
    repo = _get_repo(repo_path)
    
    try:
        # Get the commit to cherry-pick
        try:
            commit = repo.get(commit_hash)
            if not isinstance(commit, pygit2.Commit):
                raise GitError(GitErrorCode.INVALID_PARAMETER, f"Object {commit_hash} is not a commit")
        except ValueError:
            raise GitError(GitErrorCode.INVALID_PARAMETER, f"Invalid commit hash: {commit_hash}")
            
        # Perform cherry-pick
        repo.cherrypick(commit.id)
        
        if repo.index.conflicts:
            raise GitError(GitErrorCode.MERGE_CONFLICT, "Cherry-pick resulted in conflicts. Please resolve manually.")
            
        # Commit the changes
        user = repo.default_signature
        tree = repo.index.write_tree()
        
        # Original commit message
        message = commit.message
        
        repo.create_commit("HEAD", user, user, message, tree, [repo.head.target])
        repo.state_cleanup()
        
        return f"Cherry-pick of {commit_hash[:7]} successful"

    except pygit2.GitError as e:
        raise GitError(GitErrorCode.OPERATION_FAILED, str(e))
    except GitError:
        raise
    except Exception as e:
        raise GitError(GitErrorCode.OPERATION_FAILED, f"Unexpected error during cherry-pick: {str(e)}")
