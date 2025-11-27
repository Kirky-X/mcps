from typing import List
import pygit2
import os
from .errors import GitError, GitErrorCode
from .read_ops import _get_repo

def git_add(repo_path: str, files: List[str]) -> List[str]:
    repo = _get_repo(repo_path)
    added_files = []
    
    try:
        # Prepare list of relative paths
        rel_files = []
        for file_path in files:
            # Handle absolute paths by making them relative to repo root
            rel_path = file_path
            if os.path.isabs(file_path):
                rel_path = os.path.relpath(file_path, repo.workdir)
            rel_files.append(rel_path)

        # Optimization: Use add_all if available (pygit2 >= 0.26.0)
        # This is much faster for directories and respects .gitignore
        if hasattr(repo.index, 'add_all'):
            repo.index.add_all(rel_files)
            repo.index.write()
            # With add_all we don't get the list of individual files expanded from dirs
            # but returning the requested pathspecs is usually sufficient and correct
            return rel_files

        # Fallback for older versions or explicit file adding
        for rel_path in rel_files:
            full_path = os.path.join(repo.workdir, rel_path)
            
            if os.path.isdir(full_path):
                # If directory, add all files recursively
                for root, dirs, filenames in os.walk(full_path):
                    if '.git' in dirs:
                        dirs.remove('.git')
                        
                    for filename in filenames:
                        file_abs_path = os.path.join(root, filename)
                        file_rel_path = os.path.relpath(file_abs_path, repo.workdir)
                        repo.index.add(file_rel_path)
                        added_files.append(file_rel_path)
            else:
                repo.index.add(rel_path)
                added_files.append(rel_path)
            
        repo.index.write()
    except OSError as e:
        raise GitError(
            code=GitErrorCode.REPO_NOT_FOUND, # Or file not found
            message=f"File error: {e}"
        )
    except Exception as e:
        raise GitError(
            code=GitErrorCode.OPERATION_FAILED,
            message=f"Failed to add files: {e}"
        )
        
    return added_files

def git_reset(repo_path: str) -> str:
    repo = _get_repo(repo_path)
    
    # Unstage all changes (reset index to HEAD)
    try:
        head = repo.head.peel()
        repo.reset(head.id, pygit2.GIT_RESET_MIXED)
    except pygit2.GitError:
        # If no HEAD (empty repo), clear index
        repo.index.clear()
        repo.index.write()
        
    return "All changes unstaged"

def git_commit(repo_path: str, message: str) -> str:
    repo = _get_repo(repo_path)
    
    # Check if index has changes
    try:
        # If we have a HEAD, check diff between HEAD and Index
        head = repo.head.peel()
        diff = repo.diff(head.tree, cached=True)
        # Optimization: Check number of deltas instead of generating patch
        if len(diff) == 0:
            raise GitError(GitErrorCode.NOTHING_TO_COMMIT, "Nothing to commit")
    except pygit2.GitError:
        # Initial commit - check if index has any entries
        if not repo.index:
             raise GitError(GitErrorCode.NOTHING_TO_COMMIT, "Nothing to commit")
            
    try:
        # Use existing config or default
        try:
            author = repo.default_signature
            committer = repo.default_signature
        except KeyError:
             author = pygit2.Signature("MCP Git", "mcp@example.com")
             committer = author
        
        tree = repo.index.write_tree()
        
        parents = []
        try:
            parents = [repo.head.target]
        except pygit2.GitError:
            pass
            
        commit_oid = repo.create_commit(
            "HEAD",
            author,
            committer,
            message,
            tree,
            parents
        )
        
        return str(commit_oid)
    except GitError:
        raise
    except Exception as e:
        raise GitError(GitErrorCode.OPERATION_FAILED, str(e))

def git_restore(repo_path: str, files: List[str], staged: bool = False) -> str:
    repo = _get_repo(repo_path)
    
    try:
        for file_path in files:
             # Handle absolute paths by making them relative to repo root
             rel_path = file_path
             if os.path.isabs(file_path):
                 rel_path = os.path.relpath(file_path, repo.workdir)

             if staged:
                 # Unstage specific file (reset index entry from HEAD)
                 try:
                     # Get the HEAD commit
                     head = repo.head.peel()
                     # Get the tree entry for the file from HEAD
                     try:
                         # This retrieves the tree entry (Blob)
                         entry = head.tree[rel_path]
                         # To add to index, we need to create an IndexEntry
                         # IndexEntry(path, oid, mode)
                         # entry.id is the OID, entry.filemode is the mode
                         index_entry = pygit2.IndexEntry(rel_path, entry.id, entry.filemode)
                         repo.index.add(index_entry)
                     except KeyError:
                         # File not in HEAD, so remove it from index (it's a new file)
                         try:
                             repo.index.remove(rel_path)
                         except OSError:
                             # File might not be in index either
                             pass
                 except pygit2.GitError:
                     # No HEAD? Clear index for this file if possible or just remove
                     try:
                         repo.index.remove(rel_path)
                     except OSError:
                         pass
                 
                 repo.index.write()
             else:
                 # Restore workdir from index (checkout)
                 # Note: checkout with paths updates workdir to match index
                 repo.checkout(
                     strategy=pygit2.GIT_CHECKOUT_FORCE, 
                     paths=[rel_path]
                 )
                 
        return "Files restored"
    except Exception as e:
        raise GitError(GitErrorCode.OPERATION_FAILED, str(e))
