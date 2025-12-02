# LibraryMaster MCP

[中文文档](README_ZH.md) | [API Reference](API_REFERENCE.md) | [Release Notes](Release.md)

A powerful MCP (Model Context Protocol) service for library management and dependency operations across Python, Node.js,
Java, Rust, Go, and C++ ecosystems, integrated with Context7 API for intelligent library search and documentation
queries.

> ⚠️ **Notice**: Java interfaces may occasionally fail to retrieve due to network or API limitations.

## Version Features (v0.1.4)

### 🧹 Project Optimization & Cleanup

- 🗂️ **Code Structure Optimization**: Removed debug scripts and redundant files, streamlined project structure
- 🧽 **Cache Cleanup**: Comprehensive cleanup of temporary files and compilation cache, improved performance
- ✅ **Quality Verification**: All 69 test cases passed, ensuring functional integrity
- 📁 **Directory Organization**: Optimized project directory structure, enhanced code maintainability
- 🚀 **Performance Enhancement**: Reduced disk usage, optimized loading speed

### 🌟 Core Features (Inherited from v0.1.3)

- 🌐 **Mirror Source Configuration & Failover**: Support for multiple mirror sources with automatic failover
- 🔄 **Enhanced Network Retry Mechanism**: Intelligent retry strategies and timeout optimization
- 🛡️ **Circuit Breaker Pattern**: Protection against cascading failures
- 📊 **Real-time Health Monitoring**: Mirror source status monitoring and automatic recovery
- 🌍 **Extended Language Support**: Added Go and C++ language support

### 🚀 Core Features

- ✨ **Context7 API Integration**: Intelligent library search and documentation queries
- 🔧 **Cache System Refactor**: Enhanced performance with cacheout library
- 🛡️ **Full Backward Compatibility**: No breaking changes to existing features
- 📚 **Enhanced Documentation**: Complete API reference and usage guides

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Kirky-X/mcps.git
cd services/library

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### Environment Configuration

Configure necessary environment variables before starting the service:

```bash
# Context7 API configuration (optional, for document search features)
export LIBRARYMASTER_CONTEXT7_API_KEY="your_context7_api_key"

# Mirror source configuration (v0.1.3 new)
export LIBRARYMASTER_RUST_MIRRORS="https://rsproxy.cn/crates.io-index,https://mirrors.ustc.edu.cn/crates.io-index"
export LIBRARYMASTER_PYTHON_MIRRORS="https://pypi.tuna.tsinghua.edu.cn/simple,https://mirrors.aliyun.com/pypi/simple"
export LIBRARYMASTER_JAVA_MIRRORS="https://maven.aliyun.com/repository/central,https://repo.huaweicloud.com/repository/maven"
export LIBRARYMASTER_NODE_MIRRORS="https://registry.npmmirror.com,https://registry.npm.taobao.org"
export LIBRARYMASTER_GO_MIRRORS="https://goproxy.cn,https://goproxy.io"
export LIBRARYMASTER_CPP_MIRRORS="https://mirrors.tuna.tsinghua.edu.cn/vcpkg-ports.git"

# Network enhancement configuration (v0.1.3 new)
export LIBRARYMASTER_ENABLE_MIRROR_FALLBACK=true
export LIBRARYMASTER_MAX_RETRIES=3
export LIBRARYMASTER_CIRCUIT_BREAKER_THRESHOLD=5

# Cache configuration (optional)
export LIBRARYMASTER_CACHE_TTL=3600
export LIBRARYMASTER_CACHE_MAX_SIZE=1000
```

### MCP Service Setup

```bash
# Start MCP service
uv run -m library.mcp_service

# Or with custom configuration
LIBRARYMASTER_CONTEXT7_API_KEY=your_key uv run -m library.mcp_service
```

## Available MCP Tools

### Core Library Management Tools

- **`find_latest_versions`** - Find the latest versions of libraries
- **`check_versions_exist`** - Verify if specific library versions exist
- **`find_library_docs`** - Get official documentation URLs
- **`find_library_dependencies`** - Retrieve dependency information
- **`get_cache_stats`** - Get cache statistics
- **`clear_cache`** - Clear cache data

### Context7 Intelligent Search Tools

- **`search_libraries`** - Use Context7 API to intelligently search for relevant libraries and code examples
- **`get_library_docs`** - Use Context7 API to get detailed documentation for specified libraries
- **`context7_health_check`** - Check Context7 API service status

For detailed API documentation, please refer to [API Reference](API_REFERENCE.md).

## ⚙️ Configuration

### MCP Client Config

```json
{
  "mcpServers": {
    "mcp-library": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "git+https://github.com/Kirky-X/mcps.git#subdirectory=services/library",
        "library-mcp"
      ]
    }
  }
}
```

## Testing

LibraryMaster has been moved to `services/library`. Please run tests there:

```bash
cd ../../services/library
uv run -m pytest -q -s
```

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](../../LICENSE) .

Note: This project is part of a monorepo, and the license file is located in the repository root directory.
