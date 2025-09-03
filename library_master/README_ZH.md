# LibraryMaster MCP

[English Documentation](README.md) | [API 参考文档](API_REFERENCE.md) | [版本发布记录](Release.md)

一个强大的 MCP (Model Context Protocol) 服务，用于跨 Python、Node.js、Java、Rust、Go 和 C++ 生态系统的库管理和依赖操作，集成 Context7 API 提供智能库搜索和文档查询功能。

> ⚠️ **注意**: 由于网络或 API 限制，Java 接口偶尔可能无法获取。

## 版本特性 (v0.1.3)

### 🌟 新增功能
- 🌐 **镜像源配置与故障转移**: 支持多镜像源配置和自动故障转移
- 🔄 **增强网络重试机制**: 智能重试策略和超时优化
- 🛡️ **熔断器模式**: 防止级联故障的保护机制
- 📊 **实时健康监控**: 镜像源状态监控和自动恢复
- 🌍 **扩展语言支持**: 新增 Go 和 C++ 语言支持

### 🚀 核心功能
- ✨ **Context7 API 集成**: 智能库搜索和文档查询
- 🔧 **缓存系统重构**: 使用 cacheout 库提升性能
- 🛡️ **完全向后兼容**: 现有功能无变化
- 📚 **增强文档**: 完整的 API 参考和使用指南
- 🚀 **核心功能**: 多语言库版本查询、文档获取、依赖分析
- 🌐 **多语言支持**: Rust、Python、Java、Node.js、Go、C++
- ⚡ **高性能**: 异步批量处理和智能缓存
- 🔌 **MCP 协议**: 无缝集成 Claude Desktop

## 快速开始

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd LibraryMaster

# 安装 uv（如果尚未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装项目依赖
uv sync
```

### 环境变量配置

在启动服务前，请配置必要的环境变量：

```bash
# Context7 API 配置（可选，用于文档搜索功能）
export LIBRARY_MASTER_CONTEXT7_API_KEY="your_context7_api_key"

# 镜像源配置（v0.1.3 新增）
export LIBRARYMASTER_RUST_MIRRORS="https://rsproxy.cn/crates.io-index,https://mirrors.ustc.edu.cn/crates.io-index"
export LIBRARYMASTER_PYTHON_MIRRORS="https://pypi.tuna.tsinghua.edu.cn/simple,https://mirrors.aliyun.com/pypi/simple"
export LIBRARYMASTER_JAVA_MIRRORS="https://maven.aliyun.com/repository/central,https://repo.huaweicloud.com/repository/maven"
export LIBRARYMASTER_NODE_MIRRORS="https://registry.npmmirror.com,https://registry.npm.taobao.org"
export LIBRARYMASTER_GO_MIRRORS="https://goproxy.cn,https://goproxy.io"
export LIBRARYMASTER_CPP_MIRRORS="https://mirrors.tuna.tsinghua.edu.cn/vcpkg-ports.git"

# 网络增强配置（v0.1.3 新增）
export LIBRARYMASTER_ENABLE_MIRROR_FALLBACK=true
export LIBRARYMASTER_MAX_RETRIES=3
export LIBRARYMASTER_CIRCUIT_BREAKER_THRESHOLD=5

# 缓存配置（可选）
export LIBRARY_MASTER_CACHE_TTL=3600
export LIBRARY_MASTER_CACHE_MAX_SIZE=1000
```

### MCP 服务设置

```bash
# 启动 MCP 服务
uv run -m library_master.mcp_service

# 或使用自定义配置
LIBRARY_MASTER_CONTEXT7_API_KEY=your_key uv run -m library_master.mcp_service
```

## 可用的 MCP 工具

### 核心库管理工具
- **`find_latest_versions`** - 查找库的最新版本
- **`check_versions_exist`** - 验证特定库版本是否存在
- **`find_library_docs`** - 获取官方文档 URL
- **`find_library_dependencies`** - 检索依赖信息
- **`get_cache_stats`** - 获取缓存统计信息
- **`clear_cache`** - 清空缓存数据

### Context7 智能搜索工具
- **`search_libraries`** - 使用 Context7 API 智能搜索相关库和代码示例
- **`get_library_docs`** - 使用 Context7 API 获取指定库的详细文档

详细的 API 文档请参考 [API 参考文档](API_REFERENCE.md)。

### 与 MCP 客户端集成

```json
{
  "mcpServers": {
    "library_master": {
      "command": "uv",
      "args": ["run", "-m", "library_master.mcp_service"],
      "cwd": "/path/to/LibraryMaster"
    }
  }
}
```

## 测试

运行测试套件：

```bash
# 运行所有测试
uv run python test/test_mcp_tools.py
```

## 许可证

本项目采用 Apache 2.0 许可证 - 详情请参阅 [LICENSE](../../LICENSE) 。

注：本项目是 mcps monorepo 仓库的一部分，许可证文件位于仓库根目录。