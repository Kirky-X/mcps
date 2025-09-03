# MCP 服务聚合仓库

[![LibraryMaster Build](https://github.com/Kirky-X/mcps/actions/workflows/build-check-library_master.yml/badge.svg)](https://github.com/Kirky-X/mcps/actions/workflows/build-check-library_master.yml)
[![TimeMaster Build](https://github.com/Kirky-X/mcps/actions/workflows/build-check-time_master.yml/badge.svg)](https://github.com/Kirky-X/mcps/actions/workflows/build-check-time_master.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

一个包含多个模型上下文协议（MCP）服务的聚合仓库，提供各种功能。

## 服务

该聚合仓库包含以下 MCP 服务：

### 📚 LibraryMaster MCP
[![LibraryMaster](https://img.shields.io/badge/Library-Master-blue)](library_master/README_ZH.md)

一个强大的 MCP 服务，用于跨 Python、Node.js、Java 和 Rust 生态系统的库管理和依赖操作，集成 Context7 API 提供智能库搜索和文档查询功能。

**主要特性：**
- 多语言库版本查询（Python、Node.js、Java、Rust）
- 官方文档检索
- 依赖分析
- 通过 Context7 API 集成实现智能搜索
- 高性能缓存系统

📖 [文档](library_master/README_ZH.md) | 📚 [API 参考](library_master/API_REFERENCE.md) | 📝 [版本发布记录](library_master/Release.md)

### ⏰ TimeMaster MCP
[![TimeMaster](https://img.shields.io/badge/Time-Master-green)](time_master/README_ZH.md)

一个强大的 MCP 服务，用于时间管理和时区操作。TimeMaster 通过标准化的 MCP 接口为 AI 应用程序提供全面的时间、时区和节假日查询功能。

**主要特性：**
- 统一时间操作（当前时间、时区转换）
- 智能时区管理和搜索
- 按国家和日期范围的全面节假日支持
- 离线模式支持
- 多语言支持

📖 [文档](time_master/README_ZH.md) | 📚 [API 参考](time_master/API_REFERENCE.md) | 📝 [版本说明](time_master/Release.md)

## 快速开始

### 先决条件

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)（推荐用于依赖管理）

### 安装

克隆仓库：
```bash
git clone https://github.com/Kirky-X/mcps
cd mcps
```

每个服务可以独立安装：

**LibraryMaster:**
```bash
cd library_master
# 安装 uv (如果尚未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync
```

**TimeMaster:**
```bash
cd time_master
pip install -e ".[dev]"
```

## 使用方法

### LibraryMaster MCP 服务
```bash
cd library_master
uv run -m library_master.mcp_service
```

### TimeMaster MCP 服务
```bash
cd time_master
uv run -m time_master.mcp_service
```

## 开发

### 运行测试

每个服务都有自己的测试套件：

**LibraryMaster:**
```bash
cd library_master
uv run python test/test_mcp_tools.py
```

**TimeMaster:**
```bash
cd time_master
pytest test/ -v
```

### 代码格式化

**LibraryMaster:**
```bash
# 格式化代码
black src/
ruff check src/ --fix
```

**TimeMaster:**
```bash
# 格式化代码
black src/
ruff check src/ --fix
```

## 许可证

本项目采用 Apache 2.0 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。

该聚合仓库中的每个服务都独立地以与主项目相同的条款获得许可。