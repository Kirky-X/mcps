import abc
import platform
import subprocess
import sys
import logging
from typing import Optional

from .errors import GitError, GitErrorCode

logger = logging.getLogger(__name__)

class LibGit2Installer(abc.ABC):
    @abc.abstractmethod
    def install(self) -> bool:
        pass

    def check_installed(self) -> bool:
        try:
            import pygit2
            return True
        except ImportError:
            return False

class SystemInstaller(LibGit2Installer):
    def install(self) -> bool:
        import shutil
        system = platform.system().lower()
        if system == "linux":
            # Simple check for apt/dnf
            if shutil.which("apt-get"):
                return self._install_apt()
            
            if shutil.which("dnf"):
                return self._install_dnf()
                
        elif system == "darwin":
            if shutil.which("brew"):
                return self._install_brew()
        elif system == "windows":
            if shutil.which("vcpkg"):
                return self._install_vcpkg()
            
        return False

    def _install_apt(self) -> bool:
        try:
            subprocess.run(["sudo", "apt-get", "update"], check=True)
            subprocess.run(["sudo", "apt-get", "install", "-y", "libgit2-dev"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _install_dnf(self) -> bool:
        try:
            subprocess.run(["sudo", "dnf", "install", "-y", "libgit2-devel"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _install_brew(self) -> bool:
        try:
            subprocess.run(["brew", "install", "libgit2"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _install_vcpkg(self) -> bool:
        try:
            subprocess.run(["vcpkg", "install", "libgit2"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False

class SourceInstaller(LibGit2Installer):
    def install(self) -> bool:
        """
        Install libgit2 from source.
        Steps:
        1. Clone libgit2 repository
        2. Create build directory
        3. Run cmake
        4. Run make install
        """
        import tempfile
        import os
        import shutil

        try:
            # Check for cmake
            subprocess.run(["cmake", "--version"], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("cmake is required for source installation but not found.")
            return False

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info(f"Building libgit2 in {temp_dir}")
                
                # Clone libgit2
                # We use a specific version known to work with pygit2 1.13.0 (libgit2 1.7.x)
                # But for now, let's try the stable release tag if possible, or just latest.
                # Pygit2 1.13.0 requires Libgit2 v1.7.
                subprocess.run(
                    ["git", "clone", "--depth", "1", "-b", "v1.7.2", "https://github.com/libgit2/libgit2.git"],
                    cwd=temp_dir,
                    check=True,
                    capture_output=True
                )
                
                source_dir = os.path.join(temp_dir, "libgit2")
                build_dir = os.path.join(source_dir, "build")
                os.makedirs(build_dir, exist_ok=True)
                
                # Configure
                install_prefix = "/usr/local"
                if os.geteuid() != 0:
                    # User space installation fallback
                    install_prefix = os.path.expanduser("~/.local")
                    logger.info(f"Not root, installing to {install_prefix}")
                    
                    # Ensure lib and include dirs exist and are in path
                    os.makedirs(os.path.join(install_prefix, "lib"), exist_ok=True)
                    os.makedirs(os.path.join(install_prefix, "include"), exist_ok=True)
                    
                    # Update environment variables for build
                    env = os.environ.copy()
                    pkg_config_path = os.path.join(install_prefix, "lib", "pkgconfig")
                    env["PKG_CONFIG_PATH"] = f"{pkg_config_path}:{env.get('PKG_CONFIG_PATH', '')}"
                    env["LD_LIBRARY_PATH"] = f"{os.path.join(install_prefix, 'lib')}:{env.get('LD_LIBRARY_PATH', '')}"
                else:
                    env = os.environ.copy()

                subprocess.run(
                    ["cmake", "..", f"-DCMAKE_INSTALL_PREFIX={install_prefix}", "-DBUILD_SHARED_LIBS=ON"],
                    cwd=build_dir,
                    check=True,
                    capture_output=True,
                    env=env
                )
                
                # Build
                subprocess.run(
                    ["cmake", "--build", "."],
                    cwd=build_dir,
                    check=True,
                    capture_output=True
                )
                
                # Install
                cmd = ["cmake", "--install", "."]
                if os.geteuid() == 0:
                    # Only use sudo if we are root (which is weird but logic-wise means system install)
                    # Actually if we are root we don't need sudo.
                    # If we are NOT root and installing to /usr/local, we need sudo.
                    # But here we switched to ~/.local if not root.
                    # So we only need sudo if we are not root AND trying to install to system location.
                    # With the logic above:
                    # If root: prefix=/usr/local, cmd=cmake --install .
                    # If not root: prefix=~/.local, cmd=cmake --install .
                    pass
                else:
                    # Just in case we revert logic or something, but with ~/.local we don't need sudo
                    pass
                
                subprocess.run(
                    cmd,
                    cwd=build_dir,
                    check=True,
                    capture_output=True
                )
                
                # Update ldconfig only if root/linux
                if platform.system().lower() == "linux" and os.geteuid() == 0:
                    subprocess.run(["ldconfig"], check=False)
                
                # If installed to ~/.local, we need to tell the user or set env vars for pygit2 to find it
                if install_prefix != "/usr/local":
                    logger.warning(f"Libgit2 installed to {install_prefix}. You may need to set LIBGIT2_LIB and LIBGIT2_INC environment variables.")
                    os.environ["LIBGIT2"] = install_prefix
                    os.environ["LIBGIT2_LIB"] = os.path.join(install_prefix, "lib")
                    os.environ["LIBGIT2_INC"] = os.path.join(install_prefix, "include")
                    # Also need to add to LD_LIBRARY_PATH for runtime
                    os.environ["LD_LIBRARY_PATH"] = f"{os.path.join(install_prefix, 'lib')}:{os.environ.get('LD_LIBRARY_PATH', '')}"

                return True
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Source installation failed: {e}")
            if e.stderr:
                logger.error(f"Error output: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during source installation: {e}")
            return False

class DependencyManager:
    def __init__(self):
        self.system_installer = SystemInstaller()
        self.source_installer = SourceInstaller()

    def ensure_libgit2(self):
        # Priority 1: Try uv pip install pygit2
        if not self._check_import():
            logger.info("Attempting UV installation of pygit2...")
            if self._install_via_uv():
                if self._check_import():
                    return
        else:
            return

        # Priority 2: System Package Manager
        logger.info("Attempting system installation...")
        if self.system_installer.install():
            if self._check_import():
                return

        # Priority 3: Source Compilation
        logger.info("Attempting source installation...")
        if self.source_installer.install():
            if self._check_import():
                return

        # Failure
        raise GitError(
            code=GitErrorCode.LIBGIT2_MISSING,
            message="Failed to install libgit2 dependency.",
            suggestion="Please install libgit2 manually for your system.",
            details={
                "os": platform.system(),
                "python": sys.version
            }
        )

    def _check_import(self) -> bool:
        try:
            import pygit2
            return True
        except ImportError:
            return False

    def _install_via_uv(self) -> bool:
        try:
            import shutil
            if not shutil.which("uv"):
                return False
            subprocess.run(["uv", "pip", "install", "pygit2"], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
        except Exception:
            return False
