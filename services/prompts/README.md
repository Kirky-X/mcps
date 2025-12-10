# Prompt Manager MCP

[中文文档](README_ZH.md) | [API Reference](docs/API_REFERENCE.md) | [Release Notes](docs/RELEASE.md)

An enterprise-grade prompt version management system built on SQLite, providing comprehensive CRUD interfaces, semantic search, version control, and multi-client adaptation capabilities, integrated with various LLM clients (OpenAI, Anthropic, etc.).

> ⚠️ **Notice**: Semantic search features require proper API key configuration for embedding generation.

## Version Features (v1.0.0)

### 🧹 Project Optimization & Cleanup

- 🗂️ **Code Structure Optimization**: Modularized architecture with clear separation of concerns (Invocation, Business Logic, Cache, DAL, Storage)
- 🧽 **Cache Management**: Intelligent in-process cache (moka-py) with 1-hour TTL for optimal performance
- ✅ **Quality Verification**: Comprehensive test suite covering unit, integration, and end-to-end scenarios
- 📁 **Directory Organization**: Standardized project layout following Python best practices
- 🚀 **Performance Enhancement**: SQLite-based core with <500ms query response time

### 🌟 Core Features

- 📦 **Version Management**: Complete prompt version control with history tracking and multi-version coexistence
- 🔍 **Semantic Search**: Vector-based semantic search powered by sqlite-vec for rapid prompt discovery
- 🔄 **Client Adaptation**: Automatic adaptation to different LLM clients (OpenAI, Anthropic, etc.)
- 🧩 **Dynamic Assembly**: Support for placeholder replacement and dynamic principle injection
- 📊 **Standard Output**: OpenAI-compatible format for reduced integration costs

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://gitee.com/kirky-x/prompts.git
cd prompts

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync

# Initialize database
uv run python init_db.py
```

### Environment Configuration

Configure necessary environment variables before starting the service:

```bash
# Database configuration
export PROMPT_MANAGER_DB_PATH="./data/prompts.db"

# Authentication secrets (for HTTP Server)
export FASTAPI_USERS_JWT_SECRET="your_jwt_secret"
export FASTAPI_USERS_RESET_SECRET="your_reset_secret"
export FASTAPI_USERS_VERIFY_SECRET="your_verify_secret"

# Embedding configuration (optional, for semantic search)
export OPENAI_API_KEY="your_openai_api_key"

# Cache configuration (optional)
export PROMPT_MANAGER_CACHE_ENABLED=true
export PROMPT_MANAGER_CACHE_TTL=3600
```

### MCP Service Setup

```bash
# Start MCP service (Claude)
uv run -m prompt_manager.mcp_server

# Or with custom configuration
PROMPT_MANAGER_DB_PATH=./custom.db uv run -m prompt_manager.mcp_server
```

## Available MCP Tools

### Core Prompt Management Tools

- **`create_prompt`** - Create new prompts or versions
- **`search_prompts`** - Search prompts by query or tags
- **`get_prompt`** - Retrieve specific prompt by name and version
- **`update_prompt`** - Update existing prompt metadata or content

### Prompt Operation Tools

- **`delete_prompt`** - Soft delete prompt versions
- **`activate_prompt`** - Activate inactive prompt versions
- **`manage_principles`** - Create and manage prompt principles

For detailed API documentation, please refer to [API Reference](docs/API_REFERENCE.md).

## ⚙️ Configuration

### MCP Client Config

```json
{
  "mcpServers": {
    "prompt-manager": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "git+https://gitee.com/kirky-x/prompts.git",
        "prompt-manager"
      ]
    }
  }
}
```

## Testing

Prompt Manager uses pytest for testing. Please run tests in the project root:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/prompt_manager
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) .

Note: This project is part of a monorepo, and the license file is located in the repository root directory.
