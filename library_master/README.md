# LibraryMaster MCP

[中文文档](README_zh.md) | [API Reference](API_REFERENCE.md) | [Release Notes](Release.md)

A powerful MCP (Model Context Protocol) service for library management and dependency operations across Python, Node.js, Java, and Rust ecosystems, integrated with Context7 API for intelligent library search and documentation queries.

> ⚠️ **Notice**: Java interfaces may occasionally fail to retrieve due to network or API limitations.

## Version Features (v0.1.1)

- ✨ **Context7 API Integration**: Intelligent library search and documentation queries
- 🔧 **Cache System Refactor**: Enhanced performance with cacheout library
- 🛡️ **Full Backward Compatibility**: No breaking changes to existing features
- 📚 **Enhanced Documentation**: Complete API reference and usage guides

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd LibraryMaster

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

### Environment Configuration

Configure necessary environment variables before starting the service:

```bash
# Context7 API configuration (optional, for intelligent search features)
export LIBRARY_MASTER_CONTEXT7_API_KEY="your_context7_api_key"

# Cache configuration (optional)
export LIBRARY_MASTER_CACHE_TTL=3600
export LIBRARY_MASTER_CACHE_MAX_SIZE=1000
```

### MCP Service Setup

```bash
# Start MCP service
uv run -m library_master.mcp_service

# Or with custom configuration
LIBRARY_MASTER_CONTEXT7_API_KEY=your_key uv run -m library_master.mcp_service
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

### Integration with MCP Clients

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

## Testing

Run the test suite:

```bash
# Run all tests
uv run python test/test_mcp_tools.py
```

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](../../LICENSE) .

Note: This project is part of a monorepo, and the license file is located in the repository root directory.