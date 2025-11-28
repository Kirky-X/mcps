# 安装指南

支持平台：Ubuntu/Debian、Fedora/RHEL、macOS、Windows。

## 通用步骤（推荐）
```bash
uv pip install mcp-git
```
运行时模块会优先尝试：`uv pip install pygit2`。

## Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y libgit2-dev
```

## Fedora/RHEL
```bash
sudo dnf install -y libgit2-devel
```

## macOS
```bash
brew install libgit2
```

## Windows
```powershell
vcpkg install libgit2
```

## 源码编译（备用）
```bash
git clone --depth 1 -b v1.7.2 https://github.com/libgit2/libgit2.git
cd libgit2 && mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local -DBUILD_SHARED_LIBS=ON
cmake --build .
sudo cmake --install .
```

如非 root，可将 `CMAKE_INSTALL_PREFIX` 设置为 `~/.local` 并确保 `LD_LIBRARY_PATH` 包含 `~/.local/lib`。

