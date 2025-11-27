import pytest
import tempfile
import shutil
import pygit2
import os

@pytest.fixture
def temp_git_repo():
    """Creates a temporary directory and initializes a git repository."""
    temp_dir = tempfile.mkdtemp()
    try:
        repo = pygit2.init_repository(temp_dir)
        
        # Configure user for commits
        repo.config["user.name"] = "Test User"
        repo.config["user.email"] = "test@example.com"
        
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)

@pytest.fixture
def temp_dir():
    """Creates a temporary directory without a git repo."""
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)
