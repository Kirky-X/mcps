import pytest
from unittest.mock import patch, MagicMock
import subprocess
import shutil
from mcp_git.dependencies import SystemInstaller, SourceInstaller, DependencyManager


def test_system_install_apt_success():
    inst = SystemInstaller()
    with patch('mcp_git.dependencies.platform.system', return_value='Linux'), \
         patch('shutil.which', side_effect=['/usr/bin/apt-get', None]), \
         patch('mcp_git.dependencies.subprocess.run') as mock_run:
        assert inst.install() is True
        # apt-get update and install should be called
        mock_run.assert_any_call(['sudo', 'apt-get', 'update'], check=True)
        mock_run.assert_any_call(['sudo', 'apt-get', 'install', '-y', 'libgit2-dev'], check=True)


def test_system_install_dnf_success():
    inst = SystemInstaller()
    with patch('mcp_git.dependencies.platform.system', return_value='Linux'), \
         patch('shutil.which', side_effect=[None, '/usr/bin/dnf']), \
         patch('mcp_git.dependencies.subprocess.run') as mock_run:
        assert inst.install() is True
        mock_run.assert_any_call(['sudo', 'dnf', 'install', '-y', 'libgit2-devel'], check=True)


def test_system_install_brew_success():
    inst = SystemInstaller()
    with patch('mcp_git.dependencies.platform.system', return_value='Darwin'), \
         patch('shutil.which', return_value='/usr/local/bin/brew'), \
         patch('mcp_git.dependencies.subprocess.run') as mock_run:
        assert inst.install() is True
        mock_run.assert_any_call(['brew', 'install', 'libgit2'], check=True)


def test_system_install_vcpkg_success():
    inst = SystemInstaller()
    with patch('mcp_git.dependencies.platform.system', return_value='Windows'), \
         patch('shutil.which', return_value='C:/vcpkg.exe'), \
         patch('mcp_git.dependencies.subprocess.run') as mock_run:
        assert inst.install() is True
        mock_run.assert_any_call(['vcpkg', 'install', 'libgit2'], check=True)


def test_source_install_missing_cmake_returns_false():
    src = SourceInstaller()
    # cmake --version raises FileNotFoundError
    with patch('mcp_git.dependencies.subprocess.run', side_effect=FileNotFoundError()):
        assert src.install() is False


def test_dependency_manager_uv_chain_success():
    dm = DependencyManager()
    with patch('mcp_git.dependencies.DependencyManager._check_import', side_effect=[False, False, True]), \
         patch('shutil.which', return_value='/usr/bin/uv'), \
         patch('mcp_git.dependencies.subprocess.run') as mock_run:
        dm.ensure_libgit2()
        # uv pip install pygit2 should be attempted
        mock_run.assert_any_call(['uv', 'pip', 'install', 'pygit2'], check=True)
