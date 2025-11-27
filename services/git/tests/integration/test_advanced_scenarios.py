import pytest
import os
import shutil
import tempfile
import pygit2
from mcp_git.advanced_ops import git_merge
from mcp_git.remote_ops import git_pull, git_push
from mcp_git.branch_ops import git_create_branch, git_checkout
from mcp_git.write_ops import git_add, git_commit
from mcp_git.errors import GitError, GitErrorCode
from mcp_git.read_ops import git_status

def test_merge_conflict(temp_git_repo):
    """
    Test merge conflict scenario:
    1. Create a file in main branch
    2. Create a feature branch
    3. Modify file in main branch
    4. Modify same file in feature branch (same lines)
    5. Attempt merge -> should fail with conflict
    """
    repo_path = temp_git_repo
    file_path = os.path.join(repo_path, "conflict.txt")
    
    # 1. Create file in main
    with open(file_path, "w") as f:
        f.write("Line 1\nLine 2\nLine 3\n")
    git_add(repo_path, ["conflict.txt"])
    git_commit(repo_path, "Initial commit")
    
    # 2. Create feature branch
    git_create_branch(repo_path, "feature")
    
    # 3. Modify in main
    with open(file_path, "w") as f:
        f.write("Line 1\nLine 2 changed in main\nLine 3\n")
    git_add(repo_path, ["conflict.txt"])
    git_commit(repo_path, "Main change")
    
    # 4. Modify in feature
    git_checkout(repo_path, "feature")
    with open(file_path, "w") as f:
        f.write("Line 1\nLine 2 changed in feature\nLine 3\n")
    git_add(repo_path, ["conflict.txt"])
    git_commit(repo_path, "Feature change")
    
    # 5. Attempt merge (should fail)
    # Switch back to main to merge feature into main
    git_checkout(repo_path, "master" if "master" in pygit2.Repository(repo_path).branches else "main")
    
    with pytest.raises(GitError) as exc:
        git_merge(repo_path, "feature")
    
    assert exc.value.code == GitErrorCode.MERGE_CONFLICT
    assert "conflict" in exc.value.message.lower()
    
    # Verify repository is in conflict state
    repo = pygit2.Repository(repo_path)
    assert repo.index.conflicts is not None

def test_network_error_invalid_remote(temp_git_repo):
    """
    Test network error scenario:
    1. Add an invalid remote
    2. Attempt to pull -> should fail with network error
    """
    repo_path = temp_git_repo
    repo = pygit2.Repository(repo_path)
    
    # Add invalid remote
    repo.remotes.create("invalid-remote", "https://invalid.example.com/repo.git")
    
    with pytest.raises(GitError) as exc:
        git_pull(repo_path, "invalid-remote", "master")
    
    # pygit2 might raise NETWORK_ERROR or just fail to resolve
    # Our wrapper converts pygit2.GitError to GitErrorCode.NETWORK_ERROR for pull/push
    assert exc.value.code == GitErrorCode.NETWORK_ERROR

def test_push_network_error(temp_git_repo):
    """
    Test push network error:
    1. Add invalid remote
    2. Attempt push -> should fail
    """
    repo_path = temp_git_repo
    repo = pygit2.Repository(repo_path)
    
    # Add invalid remote
    repo.remotes.create("invalid-remote", "https://invalid.example.com/repo.git")
    
    with pytest.raises(GitError) as exc:
        git_push(repo_path, "invalid-remote", "master")
        
    assert exc.value.code == GitErrorCode.NETWORK_ERROR
