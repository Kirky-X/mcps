# TimeMaster Release Notes

[English Documentation](README.md) | [中文文档](README_ZH.md) | [API Reference](API_REFERENCE.md)

## Version History

### v2.0.0 (Latest)

#### 🏮 Chinese Calendar Integration

**Complete Chinese Lunar Calendar System**
- **NEW**: `get_chinese_calendar_info()` - Unified interface for comprehensive Chinese calendar data
- **NEW**: `gregorian_to_lunar()` and `lunar_to_gregorian()` - Bi-directional calendar conversion
- **NEW**: `get_ganzhi()` - Traditional Chinese stem-branch (天干地支) chronology system
- **NEW**: `get_solar_terms()` - 24 solar terms query for any year
- **NEW**: `get_zodiac()` - Chinese zodiac animal calculation
- **NEW**: `get_almanac()` - Traditional Chinese almanac (黄历) information

**Enhanced Cultural Features**
- **NEW**: Complete lunar calendar support with leap month handling
- **NEW**: Traditional Chinese festivals and solar terms
- **NEW**: Ganzhi (stem-branch) system for years, months, days, and hours
- **NEW**: Chinese zodiac animals with clash information
- **NEW**: Traditional almanac with suitable/unsuitable activities

**Technical Improvements**
- **NEW**: Integration with cnlunar library for accurate calculations
- **NEW**: Support for date range 1900-2100
- **NEW**: High-performance caching and optimization
- **NEW**: Thread-safe operations for concurrent usage
- **NEW**: Comprehensive error handling and validation

#### 🔄 Unified API Enhancement

**Unified Time Interface (Enhanced)**
- **IMPROVED**: `get_time()` method with enhanced Chinese calendar support
- **NEW**: Chinese calendar format options in time operations
- Backward compatible with existing code

### v0.1.2

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
#           'country': 'US', 'year': 2025, 'days_until': 113, 
#           'holiday_duration': 1}]
```

#### ⚠️ Deprecation Warnings

The following methods are deprecated but still functional:

| Deprecated Method | Replacement | Migration Example |
|-------------------|-------------|-------------------|
| `now()` | `get_time()` | `tm.now()` → `tm.get_time()` |
| `get_next_holiday()` | `search_holiday("")` | `tm.get_next_holiday()` → `tm.search_holiday("")[0]` |
| `calculate_days_to_holiday(name)` | `search_holiday(name)` | `tm.calculate_days_to_holiday("Christmas")` → `tm.search_holiday("Christmas")[0]['days_until']` |
| `force_offline()` | Environment variable | `tm.force_offline()` → `os.environ['TIMEMASTER_OFFLINE_MODE'] = 'true'` |

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

| Feature | v0.1.0 | v0.1.1 | v0.1.2 | v2.0.0 |
|---------|--------|--------|--------|--------|
| Basic time operations | ✅ | ✅ | ✅ | ✅ |
| Timezone conversion | ✅ | ✅ | ✅ | ✅ |
| Auto timezone detection | ❌ | ✅ | ✅ | ✅ |
| Holiday queries | ❌ | ✅ | ✅ | ✅ |
| Unified time interface | ❌ | ❌ | ✅ | ✅ |
| Environment config | ❌ | ❌ | ✅ | ✅ |
| Holiday search | ❌ | ❌ | ✅ | ✅ |
| Chinese calendar system | ❌ | ❌ | ❌ | ✅ |
| Lunar calendar conversion | ❌ | ❌ | ❌ | ✅ |
| Ganzhi (stem-branch) | ❌ | ❌ | ❌ | ✅ |
| Solar terms | ❌ | ❌ | ❌ | ✅ |
| Chinese zodiac | ❌ | ❌ | ❌ | ✅ |
| Traditional almanac | ❌ | ❌ | ❌ | ✅ |
| MCP service | ✅ | ✅ | ✅ | ✅ |
| Command line | ✅ | ✅ | ✅ | ✅ |

---

## Support Policy

- **Current Version (v2.0.0)**: Full support and active development
- **Previous Version (v0.1.2)**: Security updates only
- **Legacy Versions (v0.1.1, v0.1.0)**: End of life, upgrade recommended

**Deprecation Timeline:**
- Deprecated methods in v0.1.2 will be removed in v3.0.0
- Migration warnings will be shown for 2 major versions
- Breaking changes will be clearly documented and communicated
- Chinese calendar features are stable and will maintain backward compatibility