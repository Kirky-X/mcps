try:
    from typing import List, Optional, Literal, Dict, Any
except ImportError:
    from typing import List, Optional, Dict, Any
    from typing_extensions import Literal
import os
import subprocess
import pygit2
from .errors import GitError, GitErrorCode
from .read_ops import _get_repo

def _build_callbacks(remote_url: str) -> Optional[pygit2.RemoteCallbacks]:
    if remote_url.startswith("ssh://") or remote_url.startswith("git@"):
        try:
            creds = pygit2.KeypairFromAgent("git")
            return pygit2.RemoteCallbacks(credentials=creds)
        except Exception:
            pass
        # Fallback to explicit key files if agent is unavailable
        try:
            key_path = os.getenv("SSH_KEY_PATH") or os.getenv("GIT_SSH_KEY_PATH")
            passphrase = os.getenv("SSH_KEY_PASSPHRASE") or None
            candidate_priv = []
            if key_path:
                candidate_priv.append(os.path.expanduser(key_path))
            # Common defaults
            candidate_priv += [
                os.path.expanduser("~/.ssh/id_ed25519"),
                os.path.expanduser("~/.ssh/id_rsa"),
            ]
            for priv in candidate_priv:
                pub = priv + ".pub"
                if os.path.exists(priv) and os.path.exists(pub):
                    creds = pygit2.Keypair("git", pub, priv, passphrase)
                    return pygit2.RemoteCallbacks(credentials=creds)
        except Exception:
            return None
        # Fallback to in-memory keys via environment variables
        try:
            pub_mem = os.getenv("GIT_SSH_PUBLIC_KEY")
            priv_mem = os.getenv("GIT_SSH_PRIVATE_KEY")
            passphrase = os.getenv("SSH_KEY_PASSPHRASE") or None
            if priv_mem and pub_mem:
                creds = pygit2.KeypairFromMemory("git", pub_mem, priv_mem, passphrase)
                return pygit2.RemoteCallbacks(credentials=creds)
        except Exception:
            return None
    if remote_url.startswith("https://") or remote_url.startswith("http://"):
        try:
            username = os.getenv("GIT_HTTP_USERNAME")
            password = os.getenv("GIT_HTTP_PASSWORD")
            token = os.getenv("GITHUB_TOKEN") or os.getenv("GIT_PAT") or os.getenv("GH_TOKEN")
            creds = None
            if username and password:
                creds = pygit2.UserPass(username, password)
            elif token:
                creds = pygit2.UserPass(token, "x-oauth-basic")
            if not creds:
                try:
                    proc = subprocess.run(
                        ["git", "credential", "fill"],
                        input=f"url={remote_url}\n\n".encode(),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        check=False
                    )
                    out = proc.stdout.decode()
                    u = None
                    p = None
                    for line in out.splitlines():
                        if line.startswith("username="):
                            u = line.split("=", 1)[1]
                        elif line.startswith("password="):
                            p = line.split("=", 1)[1]
                    if u and p:
                        creds = pygit2.UserPass(u, p)
                except Exception:
                    pass
            if creds:
                def _cert_check(certificate, valid, host):
                    if host and ("github.com" in host or "gitlab.com" in host or "bitbucket.org" in host):
                        return True
                    return bool(valid)
                return pygit2.RemoteCallbacks(credentials=creds, certificate_check=_cert_check)
        except Exception:
            return None
    return None

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
        
        callbacks = _build_callbacks(remote_obj.url)
        remote_obj.fetch(callbacks=callbacks)
        
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
            
        callbacks = _build_callbacks(remote_obj.url)
        remote_obj.push([refspec], callbacks=callbacks)
        return "Push successful"
        
    except KeyError:
         raise GitError(GitErrorCode.INVALID_PARAMETER, f"Remote {remote} not found")
    except pygit2.GitError as e:
         raise GitError(GitErrorCode.NETWORK_ERROR, str(e))
