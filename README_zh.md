# MCP 服务单仓库

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![MCP Git 打包](https://github.com/Kirky-X/mcps/actions/workflows/package-git.yml/badge.svg)](https://github.com/Kirky-X/mcps/actions/workflows/package-git.yml)

一个包含多种 Model Context Protocol（MCP）服务的单仓库。

## 服务列表

此单仓库当前包含以下 MCP 服务：

### 📚 MCP Git 模块

[![MCP Git](https://img.shields.io/badge/MCP-Git-blue)](services/git/README.md)

基于 `pygit2`（libgit2 绑定）构建的 Git 操作 MCP 服务器实现，为 AI 代理提供安全高效的 Git 交互能力。

**关键特性：**

- 标准化接口：通过 MCP 协议提供统一的 Git 操作能力
- 依赖智能安装：针对多平台的 `libgit2` 安装策略
- 生产级质量：完善的错误处理、日志与可观测性

📖 [文档](services/git/README.md) | 📚 [API 参考](services/git/API.md)

## 快速开始

### 环境要求

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)（推荐用于依赖管理）

### 安装

克隆仓库：

```bash
git clone https://github.com/Kirky-X/mcps
cd mcps
```

各服务可独立安装：

**MCP Git：**

```bash
cd services/git
# 安装项目依赖
uv sync
```

## 使用方法

### 运行 MCP Git 服务

```bash
cd services/git
uv run mcp-git --debug
```

## 开发

### 运行测试

各服务包含各自的测试套件：

**MCP Git：**

```bash
cd services/git
pytest tests/
```

### 代码格式化

**MCP Git：**

```bash
# 格式化代码
black services/git/src/
ruff check services/git/src/ --fix
```

## 许可协议

本项目遵循 Apache 2.0 许可证，详见 [LICENSE](LICENSE)。

单仓库中的各服务均遵循与主项目一致的许可条款。
