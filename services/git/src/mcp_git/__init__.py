from .errors import GitError, GitErrorCode
from .dependencies import LibGit2Installer
from .read_ops import git_status, git_log, git_show, git_diff
from .write_ops import git_add, git_reset, git_commit, git_restore
from .branch_ops import git_branch, git_create_branch, git_checkout
from .stash_ops import git_stash, git_stash_pop, git_stash_list
from .remote_ops import git_remote, git_pull, git_push
from .advanced_ops import git_merge, git_cherry_pick

__all__ = [
    # Errors
    "GitError",
    "GitErrorCode",
    
    # Dependencies
    "LibGit2Installer",
    
    # Core Ops - Read
    "git_status",
    "git_log",
    "git_show",
    "git_diff",
    
    # Core Ops - Write
    "git_add",
    "git_reset",
    "git_commit",
    "git_restore",
    
    # Branch Ops
    "git_branch",
    "git_create_branch",
    "git_checkout",
    
    # Stash Ops
    "git_stash",
    "git_stash_pop",
    "git_stash_list",
    
    # Remote Ops
    "git_remote",
    "git_pull",
    "git_push",
    
    # Advanced Ops
    "git_merge",
    "git_cherry_pick"
]

__version__ = "0.1.0"
