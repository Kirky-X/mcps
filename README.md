# MCP Services Monorepo

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![MCP Git Package](https://github.com/Kirky-X/mcps/actions/workflows/package-git.yml/badge.svg)](https://github.com/Kirky-X/mcps/actions/workflows/package-git.yml)

A monorepo containing multiple Model Context Protocol (MCP) services for various functionalities.

## Services

This monorepo contains the following MCP services:

### 📚 MCP Git Module

[![MCP Git](https://img.shields.io/badge/MCP-Git-blue)](services/git/README.md)

A robust Model Context Protocol (MCP) server implementation for Git operations, built on top of `pygit2` (libgit2 bindings). This module provides AI agents with comprehensive capabilities to interact with Git repositories safely and efficiently.

**Key Features:**

- Standardized Interface: Provides unified Git operation capabilities via the MCP protocol.
- Zero Dependency Hassle: Intelligent `libgit2` installation strategy adapting to multiple platforms.
- Production-Grade Quality: Comprehensive error handling, logging, and observability.

📖 [Documentation](services/git/README.md) | 📚 [API Reference](services/git/API.md)

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended for dependency management)

### Installation

Clone the repository:

```bash
git clone https://github.com/Kirky-X/mcps
cd mcps
```

Each service can be installed independently:

**MCP Git:**

```bash
cd services/git
# Install project dependencies
uv sync
```

## Usage

### MCP Git Service

```bash
cd services/git
uv run mcp-git --debug
```

## Development

### Running Tests

Each service has its own test suite:

**MCP Git:**

```bash
cd services/git
pytest tests/
```

### Code Formatting

**MCP Git:**

```bash
# Format code
black services/git/src/
ruff check services/git/src/ --fix
```

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

Each service in this monorepo is independently licensed under the same terms as the main project.
