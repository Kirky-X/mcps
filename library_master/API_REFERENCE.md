# LibraryMaster MCP API Reference

## Overview

LibraryMaster MCP 服务提供了一套完整的多语言库管理工具，支持 Rust、Python、Java、Node.js、Go 和 C++
六种编程语言的库版本查询、文档获取、版本验证和依赖分析功能。同时集成 Context7 API，提供智能库搜索和文档查询功能。

**版本 0.1.3 新特性**:

- 🌐 **镜像源配置与故障转移**: 支持多镜像源配置和自动故障转移
- 🔄 **增强网络重试机制**: 智能重试策略和超时优化
- 🛡️ **熔断器模式**: 防止级联故障的保护机制
- 📊 **实时健康监控**: 镜像源状态监控和自动恢复
- ⚡ **性能优化**: 并发处理和资源管理优化

## Supported Languages

- **Rust**: 通过 crates.io API 和镜像源
- **Python**: 通过 PyPI API 和镜像源
- **Java**: 通过 Maven Central API 和镜像源
- **Node.js**: 通过 npm API 和镜像源
- **Go**: 通过 Go Proxy API 和镜像源
- **C++**: 通过 vcpkg 和 Conan 镜像源

## Core Tools

### 1. find_latest_versions

查找指定库的最新版本信息。

#### Parameters

| Parameter            | Type   | Required | Description                         |
|----------------------|--------|----------|-------------------------------------|
| libraries            | Array  | Yes      | 库信息数组                               |
| libraries[].name     | String | Yes      | 库名称                                 |
| libraries[].language | String | Yes      | 编程语言 (rust/python/java/node/go/cpp) |

#### Request Example

```json
{
  "libraries": [
    {"name": "serde", "language": "rust"},
    {"name": "requests", "language": "python"},
    {"name": "jackson-core", "language": "java"},
    {"name": "express", "language": "node"}
  ]
}
```

#### Response Format

```json
{
  "results": [
    {
      "name": "serde",
      "language": "rust",
      "latest_version": "1.0.193",
      "description": "A generic serialization/deserialization framework",
      "homepage": "https://serde.rs",
      "repository": "https://github.com/serde-rs/serde",
      "license": "MIT OR Apache-2.0",
      "downloads": 500000000,
      "last_updated": "2023-12-01T10:30:00Z"
    }
  ],
  "errors": []
}
```

### 2. find_library_docs

获取指定库的文档链接和相关信息。

#### Parameters

| Parameter            | Type   | Required | Description                         |
|----------------------|--------|----------|-------------------------------------|
| libraries            | Array  | Yes      | 库信息数组                               |
| libraries[].name     | String | Yes      | 库名称                                 |
| libraries[].language | String | Yes      | 编程语言 (rust/python/java/node/go/cpp) |
| libraries[].version  | String | No       | 指定版本（可选）                            |

#### Request Example

```json
{
  "libraries": [
    {"name": "tokio", "language": "rust"},
    {"name": "django", "language": "python", "version": "4.2.0"},
    {"name": "spring-boot", "language": "java"},
    {"name": "react", "language": "node"}
  ]
}
```

#### Response Format

```json
{
  "results": [
    {
      "name": "tokio",
      "language": "rust",
      "version": "1.35.1",
      "docs_url": "https://docs.rs/tokio/1.35.1/tokio/",
      "api_docs": "https://docs.rs/tokio/1.35.1/tokio/",
      "homepage": "https://tokio.rs",
      "repository": "https://github.com/tokio-rs/tokio",
      "readme_url": "https://raw.githubusercontent.com/tokio-rs/tokio/master/README.md",
      "examples_url": "https://github.com/tokio-rs/tokio/tree/master/examples"
    }
  ],
  "errors": []
}
```

### 3. check_versions_exist

验证指定版本的库是否存在。

#### Parameters

| Parameter            | Type   | Required | Description                         |
|----------------------|--------|----------|-------------------------------------|
| libraries            | Array  | Yes      | 库信息数组                               |
| libraries[].name     | String | Yes      | 库名称                                 |
| libraries[].language | String | Yes      | 编程语言 (rust/python/java/node/go/cpp) |
| libraries[].version  | String | Yes      | 要验证的版本号                             |

#### Request Example

```json
{
  "libraries": [
    {"name": "serde", "language": "rust", "version": "1.0.193"},
    {"name": "requests", "language": "python", "version": "2.31.0"},
    {"name": "jackson-core", "language": "java", "version": "2.15.2"},
    {"name": "express", "language": "node", "version": "4.18.2"}
  ]
}
```

#### Response Format

```json
{
  "results": [
    {
      "name": "serde",
      "language": "rust",
      "version": "1.0.193",
      "exists": true,
      "release_date": "2023-12-01T10:30:00Z",
      "download_url": "https://crates.io/api/v1/crates/serde/1.0.193/download",
      "checksum": "abc123..."
    }
  ],
  "errors": []
}
```

### 4. find_library_dependencies

获取指定库的依赖关系信息。

#### Parameters

| Parameter            | Type   | Required | Description                         |
|----------------------|--------|----------|-------------------------------------|
| libraries            | Array  | Yes      | 库信息数组                               |
| libraries[].name     | String | Yes      | 库名称                                 |
| libraries[].language | String | Yes      | 编程语言 (rust/python/java/node/go/cpp) |
| libraries[].version  | String | No       | 指定版本（可选，默认最新版本）                     |

#### Request Example

```json
{
  "libraries": [
    {"name": "tokio", "language": "rust"},
    {"name": "flask", "language": "python"},
    {"name": "spring-boot", "language": "java"},
    {"name": "express", "language": "node", "version": "4.18.2"}
  ]
}
```

#### Response Format

```json
{
  "results": [
    {
      "name": "tokio",
      "language": "rust",
      "version": "1.35.1",
      "dependencies": [
        {
          "name": "pin-project-lite",
          "version_requirement": "^0.2.0",
          "optional": false,
          "features": []
        },
        {
          "name": "bytes",
          "version_requirement": "^1.0.0",
          "optional": true,
          "features": ["serde"]
        }
      ],
      "dev_dependencies": [
        {
          "name": "tokio-test",
          "version_requirement": "^0.4.0"
        }
      ],
      "total_dependencies": 15
    }
  ],
  "errors": []
}
```

## Context7 Intelligent Search Tools

### search_libraries

使用 Context7 API 智能搜索相关库和代码示例。

#### Parameters

| Parameter | Type    | Required | Description                           |
|-----------|---------|----------|---------------------------------------|
| query     | String  | Yes      | 搜索查询字符串                               |
| language  | String  | No       | 编程语言过滤 (rust/python/java/node/go/cpp) |
| limit     | Integer | No       | 返回结果数量限制（1-50，默认10）                   |

#### Request Example

```json
{
  "query": "http client library",
  "language": "python",
  "limit": 10
}
```

#### Response Format

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "library": "requests",
        "description": "HTTP library for Python",
        "score": 0.95,
        "repository": "https://github.com/psf/requests",
        "documentation": "https://docs.python-requests.org"
      }
    ]
  },
  "message": "Found 1 results for query: http client library"
}
```

### get_library_docs

使用 Context7 API 获取指定库的详细文档。

#### Parameters

| Parameter    | Type    | Required | Description                         |
|--------------|---------|----------|-------------------------------------|
| library_path | String  | Yes      | 库路径，格式为 username/library 或 library  |
| doc_type     | String  | No       | 文档类型 (readme/api/tutorial/examples) |
| topic        | String  | No       | 特定主题过滤                              |
| tokens       | Integer | No       | 返回的 token 数量限制（100-10000）           |

#### Request Example

```json
{
  "library_path": "tiangolo/fastapi",
  "doc_type": "api",
  "topic": "authentication",
  "tokens": 5000
}
```

#### Response Format

```json
{
  "success": true,
  "data": "FastAPI authentication documentation content...",
  "message": "Successfully retrieved documentation for tiangolo/fastapi"
}
```

## Cache Management Tools

### get_cache_stats

获取缓存统计信息。

#### Parameters

无参数。

#### Response Format

```json
{
  "cache_stats": {
    "total_entries": 150,
    "hit_rate": 0.85,
    "memory_usage": "2.5MB",
    "last_cleanup": "2023-12-01T10:30:00Z"
  }
}
```

### clear_cache

清空所有缓存数据。

#### Parameters

无参数。

#### Response Format

```json
{
  "message": "Cache cleared successfully",
  "cleared_entries": 150
}
```

## Language-Specific Features

### Rust (crates.io)

- **库名格式**: 标准 crate 名称（如 `serde`, `tokio`）
- **版本格式**: SemVer（如 `1.0.193`）
- **特殊功能**: 支持 features 查询
- **文档**: 自动链接到 docs.rs

### Python (PyPI)

- **库名格式**: 包名称（如 `requests`, `django`）
- **版本格式**: PEP 440（如 `2.31.0`, `4.2.0`）
- **特殊功能**: 支持 wheel 和 source 分发
- **文档**: 链接到 PyPI 和项目主页

### Java (Maven Central)

- **库名格式**:
    - 简单名称（如 `jackson-core`, `spring-boot`）
    - 完整坐标（如 `com.fasterxml.jackson.core:jackson-core`）
- **版本格式**: Maven 版本（如 `2.15.2`）
- **特殊功能**: 支持 POM 依赖解析
- **文档**: 链接到 Maven Central 和 Javadoc

### Node.js (npm)

- **库名格式**: 包名称（如 `express`, `react`）
- **版本格式**: SemVer（如 `4.18.2`）
- **特殊功能**: 支持 scoped packages（如 `@types/node`）
- **文档**: 链接到 npm 和项目主页

### Go (Go Proxy)

- **库名格式**: 模块路径（如 `github.com/gin-gonic/gin`, `golang.org/x/crypto`）
- **版本格式**: SemVer 或 pseudo-version（如 `v1.9.1`, `v0.0.0-20231201120000-abcdef123456`）
- **特殊功能**: 支持 Go modules 和 replace 指令
- **文档**: 链接到 pkg.go.dev 和项目仓库

### C++ (vcpkg/Conan)

- **库名格式**: 包名称（如 `boost`, `opencv`, `fmt`）
- **版本格式**: SemVer 或自定义版本（如 `1.82.0`, `4.8.0`）
- **特殊功能**: 支持 vcpkg 和 Conan 包管理器
- **文档**: 链接到官方文档和 GitHub 仓库

## Error Handling

所有 API 调用都遵循统一的错误处理格式：

```json
{
  "results": [],
  "errors": [
    {
      "library": "nonexistent-lib",
      "language": "rust",
      "error_type": "NOT_FOUND",
      "message": "Library not found in crates.io",
      "details": "The specified library does not exist or is not publicly available"
    }
  ]
}
```

### Common Error Types

- **NOT_FOUND**: 库不存在
- **VERSION_NOT_FOUND**: 指定版本不存在
- **INVALID_LANGUAGE**: 不支持的编程语言
- **API_ERROR**: 外部 API 调用失败
- **NETWORK_ERROR**: 网络连接问题
- **RATE_LIMIT**: API 调用频率限制

## Performance Considerations

### Caching Strategy

- **版本信息**: 缓存 1 小时
- **文档链接**: 缓存 24 小时
- **依赖信息**: 缓存 6 小时
- **错误结果**: 缓存 15 分钟

### Batch Operations

- **推荐批量大小**: 10-20 个库
- **最大批量大小**: 50 个库
- **并发处理**: 每种语言最多 5 个并发请求

### Rate Limiting

- **crates.io**: 10 requests/second
- **PyPI**: 10 requests/second
- **Maven Central**: 5 requests/second
- **npm**: 10 requests/second

## Test Coverage

### Comprehensive Test Cases

测试文件 `test/test_mcp_tools.py` 包含以下测试场景：

1. **基础功能测试**
    - 单个库查询
    - 批量库查询
    - 跨语言混合查询

2. **版本测试**
    - 最新版本查询
    - 指定版本验证
    - 历史版本查询

3. **错误处理测试**
    - 不存在的库
    - 无效的版本
    - 网络错误模拟

4. **性能测试**
    - 大批量查询（20+ 库）
    - 缓存效果验证
    - 并发请求测试

5. **语言特定测试**
    - Rust features 支持
    - Python wheel 格式
    - Java Maven 坐标
    - Node.js scoped packages

### Running Tests

```bash
# 运行完整测试套件
python test/test_mcp_tools.py

# 运行 Java 专项测试
python -c "import asyncio; from test.test_mcp_tools import MCPToolTester; asyncio.run(MCPToolTester().test_java_only())"
```

## Integration Examples

### Environment Variables

配置环境变量以启用所有功能：

```bash
# Context7 API 配置（用于文档搜索功能）
export LIBRARYMASTER_CONTEXT7_API_KEY="your_context7_api_key"
export LIBRARYMASTER_CONTEXT7_BASE_URL="https://context7.com/api/v1"  # 可选

# 镜像源配置（0.1.3 新增）
export LIBRARYMASTER_RUST_MIRRORS="https://rsproxy.cn/crates.io-index,https://mirrors.ustc.edu.cn/crates.io-index"
export LIBRARYMASTER_PYTHON_MIRRORS="https://pypi.tuna.tsinghua.edu.cn/simple,https://mirrors.aliyun.com/pypi/simple"
export LIBRARYMASTER_JAVA_MIRRORS="https://maven.aliyun.com/repository/central,https://repo.huaweicloud.com/repository/maven"
export LIBRARYMASTER_NODE_MIRRORS="https://registry.npmmirror.com,https://registry.npm.taobao.org"
export LIBRARYMASTER_GO_MIRRORS="https://goproxy.cn,https://goproxy.io"
export LIBRARYMASTER_CPP_MIRRORS="https://mirrors.tuna.tsinghua.edu.cn/vcpkg-ports.git"

# 网络配置（0.1.3 增强）
export LIBRARYMASTER_ENABLE_MIRROR_FALLBACK=true
export LIBRARYMASTER_MIRROR_HEALTH_CHECK_INTERVAL=300
export LIBRARYMASTER_MAX_RETRIES=3
export LIBRARYMASTER_RETRY_BACKOFF_FACTOR=2.0
export LIBRARYMASTER_CIRCUIT_BREAKER_THRESHOLD=5
export LIBRARYMASTER_CIRCUIT_BREAKER_TIMEOUT=60

# 缓存配置
export LIBRARYMASTER_CACHE_TTL=3600
export LIBRARYMASTER_CACHE_MAX_SIZE=1000
export LIBRARYMASTER_CACHE_TYPE="cacheout"

# 服务器配置
export LIBRARYMASTER_LOG_LEVEL="INFO"
export LIBRARYMASTER_MAX_WORKERS=10
export LIBRARYMASTER_REQUEST_TIMEOUT=30.0
```

### Claude Desktop Integration

```json
{
  "mcpServers": {
    "library-master": {
      "command": "uv",
      "args": ["run", "-m", "librarymaster.mcp_service"],
      "cwd": "/path/to/LibraryMaster",
      "env": {
        "LIBRARYMASTER_CONTEXT7_API_KEY": "your_context7_api_key"
      }
    }
  }
}
```

### Usage in Claude

```
请帮我查找以下库的最新版本：
- Rust: serde, tokio
- Python: requests, django
- Java: jackson-core, spring-boot
- Node.js: express, react
```

### Programmatic Usage

```python
import asyncio
from main import LibraryMasterServer

async def example():
    server = LibraryMasterServer()
    
    # 查找最新版本
    result = await server.find_latest_versions([
        {"name": "serde", "language": "rust"},
        {"name": "requests", "language": "python"}
    ])
    
    print(result)

asyncio.run(example())
```

## Changelog

### Version 0.1.3 (Latest)

- 🌐 **新增镜像源支持**: 支持多镜像源配置和自动故障转移
- 🔄 **增强网络重试机制**: 智能重试策略，指数退避算法
- 🛡️ **熔断器模式**: 防止级联故障，自动恢复机制
- 📊 **实时健康监控**: 镜像源状态监控和自动切换
- ⚡ **性能优化**: 并发处理优化，资源管理改进
- 🧪 **测试增强**: 网络连接测试和异步测试优化
- 📝 **文档完善**: API 参考文档和使用指南更新

### Version 0.1.2

- 🌍 **新增 C++ 语言支持**: 通过 vcpkg 和 Conan 包管理器支持
- 🔧 **C++ Worker 实现**: 添加专用的 C++ 库查询和管理功能
- 📚 **C++ 文档集成**: 链接到官方文档和 GitHub 仓库
- 🧪 **C++ 测试覆盖**: 完整的 C++ 库测试用例

### Version 0.1.1

- 🌍 **新增 Go 语言支持**: 通过 Go Proxy API 和镜像源支持
- 🔧 **Go Worker 实现**: 添加专用的 Go 模块查询和管理功能
- 📚 **Go 文档集成**: 链接到 pkg.go.dev 和项目仓库
- 🧪 **Go 测试覆盖**: 完整的 Go 模块测试用例

### Version 0.1.0

- 初始版本发布
- 支持 Rust、Python、Java、Node.js 四种语言
- 实现核心四个工具功能
- 添加缓存机制
- 完整的错误处理
- 全面的测试覆盖

## License

Apache 2.0 License - 详见 [LICENSE](../../LICENSE) 文件。

注：本项目是 monorepo 仓库的一部分，许可证文件位于仓库根目录。
