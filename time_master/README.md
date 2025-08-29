# TimeMaster MCP

[中文文档](README_ZH.md) | [API Reference](API_REFERENCE.md) | [Release Notes](RELEASE_NOTES.md)

A powerful MCP (Model Context Protocol) service for time management and timezone operations. TimeMaster provides AI applications with comprehensive time, timezone, and holiday query capabilities through a standardized MCP interface.

## Core MCP Features

- **Unified Time Operations** - Get current time, convert between timezones with single interface
- **Smart Timezone Management** - Automatic detection, search, and conversion capabilities
- **Comprehensive Holiday Support** - Query holidays by name, country, and date ranges
- **AI-Ready Integration** - Standardized MCP protocol for seamless AI application integration
- **Flexible Configuration** - Environment variables and configuration files support
- **Offline Mode Support** - Works without internet connection using system data
- **Multi-language Support** - Consistent functionality across different locales

## Quick Start

### Installation

```bash
pip install time-master
```

### MCP Service Setup

```bash
# Start MCP service
uv run -m time_master.mcp_service

# Or with custom configuration
TIMEMASTER_OFFLINE_MODE=true uv run -m time_master.mcp_service
```

## What's New in v0.1.2

- **🔄 Unified Time Interface**: New `get_time` MCP tool replaces `get_current_time` and `convert_time` with optional parameters
- **🌐 Auto Timezone Detection**: MCP service automatically detects timezone (network-first, system fallback)
- **🔧 Environment Variable Control**: Use `TIMEMASTER_OFFLINE_MODE=true` for offline mode configuration
- **🔍 Enhanced Search**: `search_timezones` tool now supports empty queries to list all timezones
- **🎉 Holiday Search**: New `search_holiday` tool for finding holidays by name
- **📋 Unified Holiday Format**: All holiday tools now return consistent dictionary format
- **⚠️ Backward Compatibility**: Deprecated tools still work but show migration warnings

## Usage

### MCP Service for AI Integration

TimeMaster provides an [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) service for AI integration using the standard STDIO transport.

```bash
# Start MCP service
uv run -m time_master.mcp_service

# Or with custom configuration
TIMEMASTER_OFFLINE_MODE=true uv run -m time_master.mcp_service
```

### Available MCP Tools

**Core Time Tools (v0.1.2+)**

- **`get_time`** - Unified time interface for getting current time or timezone conversion
- **`get_local_timezone`** - Get local system timezone
- **`search_timezones`** - Search for matching timezones, supports empty query to list all timezones
- **`calculate_time_difference`** - Calculate time difference between two times in different timezones

**Holiday Tools (v0.1.2+)**

- **`search_holiday`** - Search holidays by name, returns date, days until, and holiday duration
- **`list_holidays`** - List all holidays for a specific country and year

**Deprecated Tools**
- `get_next_holiday` - ⚠️ Use `search_holiday("")` instead
- `calculate_days_to_holiday` - ⚠️ Use `search_holiday(holiday_name)` instead
- `get_current_time` - ⚠️ Use `get_time()` instead
- `convert_time` - ⚠️ Use `get_time()` with parameters instead

### MCP Tool Parameters

**`get_time`**
- `timezone` (optional): Target timezone, defaults to local timezone
- `time_str` (optional): Time string to convert, if not provided gets current time
- `from_tz` (optional): Source timezone, required when time_str is provided
- `format` (optional): Output format, 'iso' or 'friendly_cn', defaults to 'iso'

**`search_timezones`**
- `query` (optional): Timezone name search query, empty string returns all timezones
- `limit` (optional): Maximum number of results to return, defaults to 20

**`search_holiday`**
- `query` (optional): Holiday name search query, empty string returns next holiday
- `country` (optional): ISO country code (e.g. 'US', 'GB', 'FR')
- `timezone` (optional): Timezone to infer country from
- `year` (optional): Year, defaults to current year
- `limit` (optional): Maximum number of results to return, defaults to 10

**`list_holidays`**
- `country` (optional): ISO country code
- `timezone` (optional): Timezone to infer country from
- `year` (optional): Year, defaults to current year

**`calculate_time_difference`**
- `time1` (required): First time string
- `tz1` (required): Timezone for first time
- `time2` (required): Second time string
- `tz2` (required): Timezone for second time

### Integration with MCP Clients

```json
{
  "mcpServers": {
    "time-master": {
      "command": "uv",
      "args": ["run", "-m", "time_master.mcp_service"],
      "cwd": "/path/to/time-master"
    }
  }
}
```

### Example MCP Tool Usage

```json
{
  "method": "tools/call",
  "params": {
    "name": "get_time",
    "arguments": {
      "timezone": "America/New_York",
      "format": "iso"
    }
  }
}
```

## Configuration

TimeMaster MCP service supports flexible configuration through environment variables:

### Environment Variables

```bash
# Force offline mode
export TIMEMASTER_OFFLINE_MODE=true

# Custom API endpoint
export TIMEMASTER_API_ENDPOINT="https://custom-api.example.com/api"

# Request timeout in seconds
export TIMEMASTER_TIMEOUT=10

# Enable debug logging
export TIMEMASTER_DEBUG=true
```

### MCP Service Configuration

```bash
# Start with offline mode
TIMEMASTER_OFFLINE_MODE=true uv run -m time_master.mcp_service

# Start with custom timeout
TIMEMASTER_TIMEOUT=15 uv run -m time_master.mcp_service

# Start with debug logging
TIMEMASTER_DEBUG=true uv run -m time_master.mcp_service
```

### Migration from v0.1.1

**Environment Variable Configuration**
```bash
# Old way: force_offline() method (deprecated)
# New way: Environment variable
export TIMEMASTER_OFFLINE_MODE=true
```

**MCP Tool Migration**
- `get_current_time` → `get_time`
- `convert_time` → `get_time` with parameters
- `get_next_holiday` → `search_holiday` with empty query
- `calculate_days_to_holiday` → `search_holiday` with holiday name

## Development Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Format code
black time-master/
ruff check time-master/

# Run MCP service for testing
uv run -m time_master.mcp_service
```

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](../../LICENSE) .

Note: This project is part of a monorepo, and the license file is located in the repository root directory.