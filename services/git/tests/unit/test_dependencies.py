import unittest
from unittest.mock import patch, MagicMock, ANY
import sys
import os
import platform
from mcp_git.dependencies import DependencyManager, SourceInstaller, SystemInstaller, GitErrorCode

class TestDependencyManager(unittest.TestCase):
    @patch('mcp_git.dependencies.SystemInstaller.install')
    @patch('mcp_git.dependencies.SourceInstaller.install')
    @patch('mcp_git.dependencies.DependencyManager._check_import')
    def test_ensure_libgit2_priority(self, mock_check_import, mock_source_install, mock_system_install):
        # Case 1: Already installed
        mock_check_import.return_value = True
        manager = DependencyManager()
        manager.ensure_libgit2()
        mock_system_install.assert_not_called()
        mock_source_install.assert_not_called()

        # Case 2: System install works
        mock_check_import.side_effect = [False, True] # First check fails, second (after sys install) passes
        mock_system_install.return_value = True
        manager = DependencyManager()
        manager.ensure_libgit2()
        mock_system_install.assert_called()
        mock_source_install.assert_not_called()

        # Reset mocks
        mock_check_import.reset_mock()
        mock_system_install.reset_mock()
        mock_source_install.reset_mock()
        mock_check_import.side_effect = None

        # Case 3: System install fails, Source install works
        mock_check_import.side_effect = [False, False, True] # Initial, After Sys, After Source
        mock_system_install.return_value = False
        mock_source_install.return_value = True
        
        # We need to recreate the manager because the side_effect iterator might be exhausted or shared unexpectedly if not careful,
        # but here we are resetting mocks so it should be fine.
        # However, the ensure_libgit2 implementation calls _check_import multiple times.
        # Let's trace:
        # 1. _check_import() -> False (from side_effect[0])
        # 2. system_installer.install() -> False
        # 3. source_installer.install() -> True
        # 4. _check_import() -> True (from side_effect[2])
        # WAIT: logic is:
        # if _check_import(): return
        # if system.install(): if _check_import(): return
        # if source.install(): if _check_import(): return
        
        # If system.install() returns False, the inner _check_import() is skipped.
        # So the sequence of calls to _check_import is:
        # 1. Initial check -> False
        # 2. System install -> False (inner check skipped)
        # 3. Source install -> True
        # 4. Final check -> True
        
        # So side_effect should be [False, True] ? No, because we want to simulate it failing initially.
        
        # Let's look at the code again:
        # if self._check_import(): return  <-- Call 1
        # if self.system_installer.install(): ... <-- returns False
        # if self.source_installer.install(): ... <-- returns True
        #     if self._check_import(): return <-- Call 2
        
        # So we only need 2 return values for _check_import: [False, True]
        mock_check_import.side_effect = [False, True]
        
        manager.ensure_libgit2()
        mock_system_install.assert_called()
        mock_source_install.assert_called()

class TestSourceInstaller(unittest.TestCase):
    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.geteuid')
    @patch('tempfile.TemporaryDirectory')
    def test_install_non_root(self, mock_temp_dir, mock_geteuid, mock_makedirs, mock_subprocess):
        # Setup mocks
        mock_geteuid.return_value = 1000 # Non-root
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/build"
        
        installer = SourceInstaller()
        result = installer.install()
        
        self.assertTrue(result)
        
        # Verify calls
        # 1. Check cmake
        mock_subprocess.assert_any_call(["cmake", "--version"], check=True, capture_output=True)
        
        # 2. Clone
        mock_subprocess.assert_any_call(
            ["git", "clone", "--depth", "1", "-b", "v1.7.2", "https://github.com/libgit2/libgit2.git"],
            cwd="/tmp/build",
            check=True,
            capture_output=True
        )
        
        # 3. Configure (cmake ..)
        # Verify it uses local prefix
        args_list = mock_subprocess.call_args_list
        cmake_configure_found = False
        for args, kwargs in args_list:
            if len(args) > 0 and len(args[0]) > 0 and args[0][0] == "cmake" and ".." in args[0]:
                # args[0] is the command list
                cmd = args[0]
                local_prefix = os.path.expanduser("~/.local")
                if f"-DCMAKE_INSTALL_PREFIX={local_prefix}" in cmd:
                    cmake_configure_found = True
        
        self.assertTrue(cmake_configure_found, "CMake configure command with local prefix not found")

    @patch('subprocess.run')
    @patch('os.makedirs')
    @patch('os.geteuid')
    @patch('tempfile.TemporaryDirectory')
    def test_install_root(self, mock_temp_dir, mock_geteuid, mock_makedirs, mock_subprocess):
        # Setup mocks
        mock_geteuid.return_value = 0 # Root
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/build"
        
        installer = SourceInstaller()
        result = installer.install()
        
        self.assertTrue(result)
        
        # Verify calls
        # Check for system prefix
        args_list = mock_subprocess.call_args_list
        cmake_configure_found = False
        for args, kwargs in args_list:
            if len(args) > 0 and len(args[0]) > 0 and args[0][0] == "cmake" and ".." in args[0]:
                cmd = args[0]
                if "-DCMAKE_INSTALL_PREFIX=/usr/local" in cmd:
                    cmake_configure_found = True
        
        self.assertTrue(cmake_configure_found, "CMake configure command with system prefix not found")

    @patch('subprocess.run')
    def test_missing_cmake(self, mock_subprocess):
        mock_subprocess.side_effect = FileNotFoundError("No cmake")
        
        installer = SourceInstaller()
        result = installer.install()
        
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
