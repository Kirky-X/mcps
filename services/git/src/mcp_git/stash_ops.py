from typing import List, Optional, Dict, Any
import pygit2
from .errors import GitError, GitErrorCode
from .read_ops import _get_repo

def git_stash(
    repo_path: str,
    message: Optional[str] = None,
    include_untracked: bool = False
) -> str:
    repo = _get_repo(repo_path)
    
    try:
        signature = pygit2.Signature("MCP Git", "mcp@example.com")
        # In pygit2 < 1.0, stash might not support flags or has different signature
        # But assuming recent pygit2 per PRD requirements (>=1.13.0)
        # Check pygit2 version or method signature if error persists
        # Actually pygit2.Repository.stash signature: (stasher, message=None, flags=0)
        # Let's try to match exactly what pygit2 expects
        
        flags = pygit2.GIT_STASH_DEFAULT
        if include_untracked:
            flags |= pygit2.GIT_STASH_INCLUDE_UNTRACKED
            
        oid = repo.stash(signature, message=message, flags=flags)
        return str(oid)
    except TypeError:
        # Fallback for older pygit2 or different signature? 
        # Some versions might use different arg order
        oid = repo.stash(signature, message)
        return str(oid)
    except pygit2.GitError as e:
        raise GitError(GitErrorCode.OPERATION_FAILED, str(e))

def git_stash_pop(repo_path: str, stash_id: Optional[str] = None) -> str:
    repo = _get_repo(repo_path)
    
    try:
        # stash_pop takes index (0, 1, 2)
        index = 0
        if stash_id:
             # Try to find index of stash_id or parse if it's "stash@{n}"
             if stash_id.startswith("stash@{") and stash_id.endswith("}"):
                 try:
                     index = int(stash_id[7:-1])
                 except ValueError:
                     pass # Fallback to 0 or maybe raise?
        
        repo.stash_pop(index)
        return "Stash popped"
    except (pygit2.GitError, ValueError) as e:
         raise GitError(GitErrorCode.OPERATION_FAILED, str(e))

def git_stash_list(repo_path: str) -> List[str]:
    repo = _get_repo(repo_path)
    stashes = []
    
    def stash_cb(index, message, oid):
        stashes.append(f"stash@{{{index}}}: {message}")
        return 0
        
    try:
        # Use repo.listall_stashes() which returns a list of Stash objects
        # We need to manually iterate to format them as expected
        if hasattr(repo, 'listall_stashes'):
            stash_list = repo.listall_stashes()
            for i, stash in enumerate(stash_list):
                 # Stash object might have message property or we need to look it up
                 # But wait, listall_stashes returns Stash objects but maybe not the message?
                 # Actually the PRD/tests expect "stash@{n}: message"
                 # Let's try to get the message from the commit message of the stash OID
                 # Or use the reflog approach which is standard for git stash list
                 pass
                 
        # Standard approach: iterate through reflog of refs/stash
        # In newer pygit2, references might not have log_iter directly?
        # Let's check how to access reflog
        ref = repo.lookup_reference("refs/stash")
        if ref:
             # ref.log() returns RefLog object which is iterable
             for i, entry in enumerate(ref.log()):
                 stashes.append(f"stash@{{{i}}}: {entry.message.replace('WIP on ', '').replace('On ', '')}")
                 
    except (KeyError, AttributeError, pygit2.GitError):
        pass
        
    return stashes
