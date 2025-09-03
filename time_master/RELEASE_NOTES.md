# TimeMaster Release Notes

[English Documentation](README.md) | [中文文档](README_ZH.md) | [API Reference](API_REFERENCE.md)

## Version History

### v0.1.2 (Latest)

#### 🔄 Major API Changes

**Unified Time Interface**

- **NEW**: `get_time()` method replaces `get_current_time()` and `convert_time()`
- Supports optional parameters for flexible time operations
- Backward compatible with existing code

**Enhanced Timezone Features**

- **NEW**: Automatic timezone detection in MCP service
- Network-first detection with system fallback
- **IMPROVED**: `search_timezones()` now supports empty queries to list all timezones

**Environment Variable Control**

- **NEW**: `TIMEMASTER_OFFLINE_MODE=true` environment variable
- **DEPRECATED**: `force_offline()` method (still functional)
- Better configuration management through environment variables

**Holiday Search Enhancement**

- **NEW**: `search_holiday()` method for finding holidays by name
- Returns comprehensive holiday information including duration
- **IMPROVED**: Unified holiday format across all methods

#### 🔧 Configuration Improvements

```python
# New environment variable approach (v0.1.2+)
import os
os.environ['TIMEMASTER_OFFLINE_MODE'] = 'true'
tm = TimeMaster()

# Old method (deprecated but still works)
tm = TimeMaster()
tm.force_offline()  # ⚠️ Shows deprecation warning
```

#### 📋 API Format Standardization

**Before v0.1.2:**

```python
# Different return formats
next_holiday = tm.get_next_holiday()  # Returns dict
days_count = tm.calculate_days_to_holiday("Christmas")  # Returns int
```

**v0.1.2+:**

```python
# Unified format
holidays = tm.search_holiday("Christmas", country="US")
# Returns: [{'name': 'Christmas Day', 'date': '2025-12-25', 
#           'country': 'US', 'year': 2025, 'days_until': 332, 
#           'holiday_duration': 1}]
```

#### ⚠️ Deprecation Warnings

The following methods are deprecated but still functional:

| Deprecated Method                 | Replacement            | Migration Example                                                                               |
|-----------------------------------|------------------------|-------------------------------------------------------------------------------------------------|
| `now()`                           | `get_time()`           | `tm.now()` → `tm.get_time()`                                                                    |
| `get_next_holiday()`              | `search_holiday("")`   | `tm.get_next_holiday()` → `tm.search_holiday("")[0]`                                            |
| `calculate_days_to_holiday(name)` | `search_holiday(name)` | `tm.calculate_days_to_holiday("Christmas")` → `tm.search_holiday("Christmas")[0]['days_until']` |
| `force_offline()`                 | Environment variable   | `tm.force_offline()` → `os.environ['TIMEMASTER_OFFLINE_MODE'] = 'true'`                         |

---

### v0.1.1

#### 🎯 Smart Timezone Detection

- **NEW**: Automatic local timezone detection and usage as default
- Eliminates need for manual timezone configuration in most cases
- Fallback mechanisms for reliable timezone detection

#### 🎉 Holiday Query System

- **NEW**: `get_next_holiday()` - Get upcoming holidays
- **NEW**: `calculate_days_to_holiday(holiday_name)` - Calculate days until specific holiday
- **NEW**: `list_holidays(country, year)` - List all holidays for country/year
- Support for multiple countries and regions

#### 🌍 Intelligent Region Matching

- **NEW**: Automatic country/region inference from timezone
- Smart mapping between timezones and holiday calendars
- Reduces configuration overhead for international applications

#### 🔧 Enhanced MCP Tools

- **NEW**: `get_local_timezone` MCP tool
- **NEW**: `get_next_holiday` MCP tool
- **NEW**: `calculate_days_to_holiday` MCP tool
- **NEW**: `list_holidays` MCP tool
- Consistent API between Python and MCP interfaces

#### 📦 New Dependencies

- **ADDED**: `holidays` library for comprehensive holiday data
- **ADDED**: `pycountry` for country code handling and validation
- Enhanced data accuracy and coverage

#### 🔄 API Additions

```python
# New in v0.1.1
tm = TimeMaster()  # Now auto-detects local timezone

# Holiday operations
next_holiday = tm.get_next_holiday()
days_to_christmas = tm.calculate_days_to_holiday("Christmas")
us_holidays = tm.list_holidays(country="US", year=2025)

# Timezone operations
local_tz = tm.get_local_timezone()
```

---

### v0.1.0 (Initial Release)

#### 🚀 Core Time Functionality

- **NEW**: Basic time conversion between timezones
- **NEW**: Current time retrieval with timezone support
- **NEW**: MCP service integration for AI applications
- **NEW**: Command-line interface for time operations

#### 🔧 Configuration System

- **NEW**: JSON-based configuration files
- **NEW**: Environment variable support
- **NEW**: Programmatic configuration options

#### 📡 Network Integration

- **NEW**: WorldTimeAPI integration for accurate time data
- **NEW**: Automatic online/offline mode switching
- **NEW**: Caching mechanism for improved performance

#### 🛠️ Developer Tools

- **NEW**: Comprehensive Python API
- **NEW**: MCP protocol implementation
- **NEW**: Error handling and logging

---

## Migration Guide

### From v0.1.1 to v0.1.2

**Recommended Actions:**

1. Replace deprecated method calls with new unified interfaces
2. Update configuration to use environment variables
3. Test holiday query format changes if using raw return values

**Breaking Changes:**

- None (fully backward compatible)

**New Features to Adopt:**

- Use `get_time()` for all time operations
- Use `search_holiday()` for holiday queries
- Configure via environment variables

### From v0.1.0 to v0.1.1

**Recommended Actions:**

1. Remove manual timezone configuration (now auto-detected)
2. Adopt new holiday query methods
3. Update MCP client configurations for new tools

**Breaking Changes:**

- None (fully backward compatible)

**New Features to Adopt:**

- Holiday query system
- Automatic timezone detection
- Enhanced MCP tools

---

## Compatibility Matrix

| Feature                 | v0.1.0 | v0.1.1 | v0.1.2 |
|-------------------------|--------|--------|--------|
| Basic time operations   | ✅      | ✅      | ✅      |
| Timezone conversion     | ✅      | ✅      | ✅      |
| Auto timezone detection | ❌      | ✅      | ✅      |
| Holiday queries         | ❌      | ✅      | ✅      |
| Unified time interface  | ❌      | ❌      | ✅      |
| Environment config      | ❌      | ❌      | ✅      |
| Holiday search          | ❌      | ❌      | ✅      |
| MCP service             | ✅      | ✅      | ✅      |
| Command line            | ✅      | ✅      | ✅      |

---

## Support Policy

- **Current Version (v0.1.2)**: Full support and active development
- **Previous Version (v0.1.1)**: Security updates only
- **Legacy Version (v0.1.0)**: End of life, upgrade recommended

**Deprecation Timeline:**

- Deprecated methods in v0.1.2 will be removed in v0.2.0
- Migration warnings will be shown for 2 major versions
- Breaking changes will be clearly documented and communicated