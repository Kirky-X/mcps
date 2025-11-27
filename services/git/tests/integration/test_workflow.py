import pytest
import os
import pygit2
from mcp_git.read_ops import git_status, git_log
from mcp_git.write_ops import git_add, git_commit
from mcp_git.branch_ops import git_branch, git_create_branch, git_checkout
from mcp_git.errors import GitError, GitErrorCode

def test_workflow_init_commit_branch(temp_git_repo):
    """
    Integration test for a common workflow:
    1. Create a file
    2. Add and commit it
    3. Create a new branch
    4. Switch to the new branch
    5. Verify status
    """
    repo_path = temp_git_repo
    
    # 1. Create a file
    file_path = os.path.join(repo_path, "test.txt")
    with open(file_path, "w") as f:
        f.write("Hello World")
        
    # Verify status - untracked
    status = git_status(repo_path)
    # git_status returns a list of strings like "filename: status"
    assert any("test.txt" in s and "untracked" in s for s in status)
    
    # 2. Add and commit
    git_add(repo_path, ["test.txt"])
    
    # Verify status - staged (added)
    status = git_status(repo_path)
    # pygit2 status might return 'added' or 'new' depending on version/mapping
    # Our implementation maps it to 'staged' or 'added'
    assert any("test.txt" in s and ("staged" in s or "added" in s or "new" in s) for s in status)
    
    commit_result = git_commit(repo_path, "Initial commit")
    # git_commit returns the hash string directly
    assert isinstance(commit_result, str)
    assert len(commit_result) == 40
    
    # Verify log
    log = git_log(repo_path)
    assert len(log) == 1
    assert log[0]["message"] == "Initial commit"
    
    # 3. Create a new branch
    git_create_branch(repo_path, "feature-branch")
    
    # Verify branch list
    branches = git_branch(repo_path)
    assert "feature-branch" in branches
    
    # 4. Switch to the new branch
    git_checkout(repo_path, "feature-branch")
    
    # Verify current branch (this requires checking HEAD or using git_branch output)
    branches = git_branch(repo_path)
    # Assuming our git_branch returns a list of strings, checking current branch might need parsing
    # But checking HEAD directly via pygit2 is reliable for test verification
    repo = pygit2.Repository(repo_path)
    assert repo.head.shorthand == "feature-branch"
    
    # 5. Verify status is clean
    status = git_status(repo_path)
    # Status should be empty or indicate clean
    # Our git_status implementation might return empty list for clean or ['Clean working tree']
    assert not status or (len(status) == 1 and "Clean" in status[0])

def test_error_handling_invalid_repo(temp_dir):
    """Integration test for error handling on non-git directory."""
    with pytest.raises(GitError) as exc:
        git_status(temp_dir)
    assert exc.value.code == GitErrorCode.NOT_A_REPOSITORY

def test_commit_empty_error(temp_git_repo):
    """Integration test for committing without changes."""
    repo_path = temp_git_repo
    with pytest.raises(GitError) as exc:
        git_commit(repo_path, "Empty commit")
    assert exc.value.code == GitErrorCode.NOTHING_TO_COMMIT
