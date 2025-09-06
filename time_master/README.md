# TimeMaster v0.1.3

[中文文档](README_ZH.md) | [API Reference](API_REFERENCE.md) | [Release Notes](Release.md)

A powerful MCP (Model Context Protocol) service for time management with unified Chinese calendar interface and comprehensive timezone operations.

## Project Overview

TimeMaster is a time management service designed for AI applications, providing through standardized MCP interface:

- **Unified Chinese Calendar Interface** - Get complete lunar calendar, stem-branch, solar terms, zodiac, and almanac information through a single method
- **Smart Time Management** - Timezone conversion, time calculation, and holiday queries
- **AI-Ready Integration** - Standardized MCP protocol for seamless AI application integration
- **Multi-language Support** - Bilingual Chinese-English interface and documentation

## v0.1.3 Features

### 🎯 Chinese Calendar Functions
- **Unified Interface** - `get_chinese_calendar_info()` gets all Chinese calendar information in one call
- **Lunar Conversion** - Bi-directional conversion between Gregorian and lunar calendars with leap month support
- **Stem-Branch System** - Complete four-pillar Bazi calculation
- **24 Solar Terms** - Precise solar term timing queries
- **Zodiac Queries** - Twelve Chinese zodiac animals and related information
- **Almanac Information** - Traditional suitable/unsuitable activities, auspicious levels, etc.

### 🌐 Time Management Functions
- **Unified Time Interface** - `get_time` tool supports current time retrieval and timezone conversion
- **Smart Timezone Management** - Automatic detection, search, and conversion capabilities
- **Holiday Queries** - Search holidays by name, country, and date ranges
- **Offline Mode Support** - Works without internet connection using system data

## Installation

```bash
pip install time-master
```

## Usage

### MCP Service Setup

```bash
# Start MCP service
python -m time_master.mcp_service

# Use offline mode
TIMEMASTER_OFFLINE_MODE=true python -m time_master.mcp_service
```

### Main MCP Tools

**Chinese Calendar Tools**
- `get_chinese_calendar_info` - Get complete Chinese calendar information

**Time Management Tools**
- `get_time` - Unified time interface for current time retrieval or timezone conversion
- `search_timezones` - Search timezones
- `search_holiday` - Search holidays
- `list_holidays` - List holidays
- `calculate_time_difference` - Calculate time differences

### MCP Client Integration

```json
{
  "mcpServers": {
    "time-master": {
      "command": "uv",
      "args": [
        "run",
        "-m",
        "time_master.mcp_service"
      ],
      "cwd": "/path/to/time-master"
    }
  }
}
```

## Configuration

### Environment Variables

```bash
# Offline mode
export TIMEMASTER_OFFLINE_MODE=true

# Default timezone
export TIMEMASTER_DEFAULT_TIMEZONE="Asia/Shanghai"

# Default country
export TIMEMASTER_DEFAULT_COUNTRY="CN"
```

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest

# Start service
python -m time_master.mcp_service
```

## Documentation

- [API Reference](API_REFERENCE.md) - Detailed interface documentation
- [Release Notes](Release.md) - Version history and compatibility information
- [中文文档](README_ZH.md) - Chinese documentation

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](../../LICENSE) .

Note: This project is part of a monorepo, and the license file is located in the repository root directory.