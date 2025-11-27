import os
import shutil
import time
import unittest
import pygit2
from mcp_git.read_ops import git_log_recent
from mcp_git.server import health_check
from mcp_git.branch_ops import git_branch, git_create_branch
from mcp_git.write_ops import git_add, git_commit, git_restore
from mcp_git.stash_ops import git_stash, git_stash_pop, git_stash_list
from mcp_git.errors import GitError

class TestVerification(unittest.TestCase):
    def setUp(self):
        self.test_dir = "/tmp/mcp_git_verification_test"
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir)
        
        # Init repo
        self.repo = pygit2.init_repository(self.test_dir)
        
        # Create initial commit
        index = self.repo.index
        author = pygit2.Signature("Test User", "test@example.com")
        committer = pygit2.Signature("Test User", "test@example.com")
        
        # Create file1
        with open(os.path.join(self.test_dir, "file1.txt"), "w") as f:
            f.write("content1")
        index.add("file1.txt")
        index.write()
        tree = index.write_tree()
        self.c1_oid = self.repo.create_commit("HEAD", author, committer, "Initial commit", tree, [])
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_log_recent(self):
        print("\nTesting git_log_recent...")
        # Create another commit
        with open(os.path.join(self.test_dir, "file2.txt"), "w") as f:
            f.write("content2")
        self.repo.index.add("file2.txt")
        self.repo.index.write()
        tree = self.repo.index.write_tree()
        author = pygit2.Signature("Test User", "test@example.com")
        self.repo.create_commit("HEAD", author, author, "Second commit", tree, [self.c1_oid])
        
        logs = git_log_recent(self.test_dir, "1h")
        self.assertEqual(len(logs), 2)
        print("✓ git_log_recent returned correct number of commits")

    def test_health_check(self):
        print("\nTesting health_check...")
        result = health_check(self.test_dir)
        self.assertEqual(result["status"], "healthy")
        self.assertIn("libgit2_version", result)
        self.assertIn("repo_stats", result)
        print("✓ health_check returned healthy status and stats")

    def test_branch_filtering(self):
        print("\nTesting git_branch filtering...")
        # Create feature branch from c1
        git_create_branch(self.test_dir, "feature", "master")
        
        # Create c2 on master
        with open(os.path.join(self.test_dir, "file3.txt"), "w") as f:
            f.write("content3")
        self.repo.index.add("file3.txt")
        self.repo.index.write()
        tree = self.repo.index.write_tree()
        author = pygit2.Signature("Test User", "test@example.com")
        c2_oid = self.repo.create_commit("HEAD", author, author, "Master commit 2", tree, [self.c1_oid])
        
        # Master contains c2, Feature does not
        branches_with_c2 = git_branch(self.test_dir, contains=str(c2_oid))
        self.assertIn("master", branches_with_c2)
        self.assertNotIn("feature", branches_with_c2)
        print("✓ git_branch contains filter works")
        
        branches_without_c2 = git_branch(self.test_dir, not_contains=str(c2_oid))
        self.assertIn("feature", branches_without_c2)
        self.assertNotIn("master", branches_without_c2)
        print("✓ git_branch not_contains filter works")

    def test_restore_staged(self):
        print("\nTesting git_restore staged=True...")
        # Modify file1 and stage it
        with open(os.path.join(self.test_dir, "file1.txt"), "w") as f:
            f.write("modified content")
        git_add(self.test_dir, ["file1.txt"])
        
        # Verify it is staged
        status = self.repo.status()
        self.assertTrue(status["file1.txt"] & pygit2.GIT_STATUS_INDEX_MODIFIED)
        
        # Restore --staged (unstage)
        git_restore(self.test_dir, ["file1.txt"], staged=True)
        
        # Verify it is no longer staged but modified in working tree
        status = self.repo.status()
        self.assertFalse(status["file1.txt"] & pygit2.GIT_STATUS_INDEX_MODIFIED)
        self.assertTrue(status["file1.txt"] & pygit2.GIT_STATUS_WT_MODIFIED)
        print("✓ git_restore staged=True unstages file correctly")

    def test_stash_pop_specific(self):
        print("\nTesting git_stash_pop with stash_id...")
        # Stash 1
        with open(os.path.join(self.test_dir, "stash1.txt"), "w") as f:
            f.write("stash1")
        git_add(self.test_dir, ["stash1.txt"])
        git_stash(self.test_dir, "Stash One")
        
        # Stash 2
        with open(os.path.join(self.test_dir, "stash2.txt"), "w") as f:
            f.write("stash2")
        git_add(self.test_dir, ["stash2.txt"])
        git_stash(self.test_dir, "Stash Two")
        
        stashes = git_stash_list(self.test_dir)
        self.assertEqual(len(stashes), 2)
        # stashes[0] is Stash Two (latest), stashes[1] is Stash One
        
        # Pop stash@{1} (Stash One)
        git_stash_pop(self.test_dir, "stash@{1}")
        
        stashes_after = git_stash_list(self.test_dir)
        self.assertEqual(len(stashes_after), 1)
        self.assertIn("Stash Two", stashes_after[0]) # Remaining stash should be Stash Two
        print("✓ git_stash_pop with stash_id pops correct stash")

if __name__ == "__main__":
    unittest.main()
