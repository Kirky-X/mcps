try:
    from typing import List, Optional, Literal, Dict, Any
except ImportError:
    from typing import List, Optional, Dict, Any
    from typing_extensions import Literal
import pygit2
from .errors import GitError, GitErrorCode
from .read_ops import _get_repo

def git_remote(
    repo_path: str,
    action: Literal["list", "add", "remove"],
    name: Optional[str] = None,
    url: Optional[str] = None
) -> Any:
    repo = _get_repo(repo_path)
    
    if action == "list":
        remotes = []
        for remote in repo.remotes:
            remotes.append(f"{remote.name}\t{remote.url}")
        return remotes
        
    elif action == "add":
        if not name or not url:
             raise GitError(GitErrorCode.INVALID_PARAMETER, "Name and URL required for add")
        repo.remotes.create(name, url)
        return f"Remote {name} added"
        
    elif action == "remove":
        if not name:
             raise GitError(GitErrorCode.INVALID_PARAMETER, "Name required for remove")
        repo.remotes.delete(name)
        return f"Remote {name} removed"
        
    return None

def git_pull(
    repo_path: str,
    remote: str = "origin",
    branch: Optional[str] = None
) -> Dict[str, Any]:
    repo = _get_repo(repo_path)
    
    try:
        # Get remote
        remote_obj = repo.remotes[remote]
        
        # Fetch
        remote_obj.fetch()
        
        # Determine branch to merge
        if not branch:
             branch = repo.head.shorthand
             
        # Find remote ref
        remote_ref_name = f"{remote}/{branch}"
        remote_ref = repo.lookup_branch(remote_ref_name, pygit2.GIT_BRANCH_REMOTE)
        if not remote_ref:
             raise GitError(GitErrorCode.INVALID_BRANCH, f"Remote branch {remote_ref_name} not found")
             
        # Merge analysis
        analysis, _ = repo.merge_analysis(remote_ref.target)
        
        if analysis & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
            return {"status": "Up to date", "files_changed": 0}
            
        elif analysis & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
            # Calculate stats before moving HEAD
            head_commit = repo.head.peel()
            remote_commit = repo.get(remote_ref.target)
            diff = repo.diff(head_commit, remote_commit)
            files_changed = diff.stats.files_changed
            
            repo.checkout_tree(repo.get(remote_ref.target))
            master_ref = repo.lookup_reference(f"refs/heads/{branch}")
            master_ref.set_target(remote_ref.target)
            repo.head.set_target(remote_ref.target)
            
            return {"status": "Fast-forward", "files_changed": files_changed}
            
        elif analysis & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
            repo.merge(remote_ref.target)
            
            if repo.index.conflicts:
                 raise GitError(GitErrorCode.MERGE_CONFLICT, "Merge conflict detected")
                 
            # Commit merge
            user = repo.default_signature
            tree = repo.index.write_tree()
            repo.create_commit("HEAD", user, user, "Merge", tree, [repo.head.target, remote_ref.target])
            repo.state_cleanup()
            
            return {"status": "Merge committed", "files_changed": 0}
            
        else:
            raise GitError(GitErrorCode.OPERATION_FAILED, "Unknown merge analysis result")
            
    except KeyError:
        raise GitError(GitErrorCode.INVALID_PARAMETER, f"Remote {remote} not found")
    except pygit2.GitError as e:
        raise GitError(GitErrorCode.NETWORK_ERROR, str(e))

def git_push(
    repo_path: str,
    remote: str = "origin",
    branch: Optional[str] = None,
    force: bool = False
) -> str:
    repo = _get_repo(repo_path)
    
    try:
        remote_obj = repo.remotes[remote]
        
        if not branch:
            branch = repo.head.shorthand
            
        refspec = f"refs/heads/{branch}:refs/heads/{branch}"
        if force:
            refspec = f"+{refspec}"
            
        remote_obj.push([refspec])
        return "Push successful"
        
    except KeyError:
         raise GitError(GitErrorCode.INVALID_PARAMETER, f"Remote {remote} not found")
    except pygit2.GitError as e:
         raise GitError(GitErrorCode.NETWORK_ERROR, str(e))
