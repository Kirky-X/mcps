# MCP Services Monorepo

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![LibraryMaster Build](https://github.com/Kirky-X/mcps/actions/workflows/build-check-library_master.yml/badge.svg)](https://github.com/Kirky-X/mcps/actions/workflows/build-check-library_master.yml)
[![TimeMaster Build](https://github.com/Kirky-X/mcps/actions/workflows/build-check-time_master.yml/badge.svg)](https://github.com/Kirky-X/mcps/actions/workflows/build-check-time_master.yml)

A monorepo containing multiple Model Context Protocol (MCP) services for various functionalities.

## Services

This monorepo contains the following MCP services:

### 📚 LibraryMaster MCP

[![LibraryMaster](https://img.shields.io/badge/Library-Master-blue)](library_master/README.md)

A powerful MCP service for library management and dependency operations across Python, Node.js, Java, and Rust
ecosystems, integrated with Context7 API for intelligent library search and documentation queries.

**Key Features:**

- Multi-language library version querying (Python, Node.js, Java, Rust)
- Official documentation retrieval
- Dependency analysis
- Intelligent search via Context7 API integration
- High-performance caching system

📖 [Documentation](library_master/README.md) | 📚 [API Reference](library_master/API_REFERENCE.md) |
📝 [Release Notes](library_master/Release.md)

### ⏰ TimeMaster MCP

[![TimeMaster](https://img.shields.io/badge/Time-Master-green)](time_master/README.md)

A powerful MCP service for time management and timezone operations. TimeMaster provides AI applications with
comprehensive time, timezone, and holiday query capabilities through a standardized MCP interface.

**Key Features:**

- Unified time operations (current time, timezone conversion)
- Smart timezone management and search
- Comprehensive holiday support by country and date ranges
- Offline mode support
- Multi-language support

📖 [Documentation](time_master/README.md) | 📚 [API Reference](time_master/API_REFERENCE.md) |
📝 [Release Notes](time_master/Release.md)

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended for dependency management)

### Installation

Clone the repository:

```bash
git clone https://github.com/Kirky-X/mcps
cd mcps
```

Each service can be installed independently:

**LibraryMaster:**

```bash
cd library_master
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install project dependencies
uv sync
```

**TimeMaster:**

```bash
cd time_master
pip install -e ".[dev]"
```

## Usage

### LibraryMaster MCP Service

```bash
cd library_master
uv run -m library_master.mcp_service
```

### TimeMaster MCP Service

```bash
cd time_master
uv run -m time_master.mcp_service
```

## Development

### Running Tests

Each service has its own test suite:

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

### Code Formatting

**LibraryMaster:**

```bash
# Format code
black src/
ruff check src/ --fix
```

**TimeMaster:**

```bash
# Format code
black src/
ruff check src/ --fix
```

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

Each service in this monorepo is independently licensed under the same terms as the main project.