# TimeMaster Python API Reference

[English Documentation](README.md) | [中文文档](README_ZH.md)

## Overview

TimeMaster provides a comprehensive Python API for time and holiday operations. This document covers all available
Python interfaces with detailed examples and usage patterns.

## Installation

```bash
pip install time-master
```

## Quick Start

```python
from time-master.core import TimeMaster

# Initialize with default configuration
tm = TimeMaster()

# Get current time
current_time = tm.get_time()
print(current_time)  # "2025-01-27T13:01:00+08:00"

# Search for holidays
holidays = tm.search_holiday("Christmas", country="US")
print(holidays[0]['date'])  # "2025-12-25"
```

## Core Interfaces

### 1. get_time - Unified Time Interface

**Function**: Get current time or convert existing time

**Parameters**:

- `timezone` (optional): Target timezone, defaults to local timezone
- `time_str` (optional): Time string to convert
- `from_tz` (optional): Source timezone, required when `time_str` is provided
- `format` (optional): Output format, 'iso' or 'friendly_cn', defaults to 'iso'

**Returns**: Formatted time string

**Examples**:

```python
# Get current time (local timezone)
current_time = tm.get_time()
# -> "2025-01-27T13:01:00+08:00"

# Get current time in specified timezone
nyc_time = tm.get_time(timezone="America/New_York")
# -> "2025-01-27T00:01:00-05:00"

# Convert existing time
converted = tm.get_time(
    time_str="2024-01-15T12:00:00",
    from_tz="UTC",
    timezone="Asia/Tokyo"
)
# -> "2024-01-15T21:00:00+09:00"

# Friendly format output
friendly = tm.get_time(timezone="Asia/Shanghai", format="friendly_cn")
# -> "2025年01月27日 13:01:00 CST"
```

### 2. get_local_timezone - Get Local Timezone

**Function**: Get system local timezone

**Parameters**: None

**Returns**: Local timezone string

**Examples**:

```python
local_tz = tm.get_local_timezone()
# -> "Asia/Shanghai"
```

### 3. search_timezones - Timezone Search

**Function**: Search for matching timezones

**Parameters**:

- `query`: Search query string, empty string returns all timezones
- `limit` (optional): Limit on number of results returned, defaults to 20

**Returns**: List of matching timezones

**Examples**:

```python
# Search for specific timezone
tokyo_tzs = tm.search_timezones("tokyo")
# -> ['Asia/Tokyo']

# Fuzzy search
china_tzs = tm.search_timezones("china")
# -> ['Asia/Shanghai', 'Asia/Urumqi']

# List all timezones (with limit)
all_tzs = tm.search_timezones("", limit=5)
# -> ['Africa/Abidjan', 'Africa/Accra', ...]
```

### 4. calculate_time_difference - Time Difference Calculation

**Function**: Calculate the difference between two times

**Parameters**:

- `time1`: First time string
- `tz1`: Timezone for the first time
- `time2`: Second time string
- `tz2`: Timezone for the second time

**Returns**: Time difference string

**Examples**:

```python
time_diff = tm.calculate_time_difference(
    time1="2024-01-15T12:00:00",
    tz1="America/New_York",
    time2="2024-01-15T18:00:00",
    tz2="Europe/London"
)
# -> "-1 day, 23:00:00"
```

## Holiday Interfaces

### 5. search_holiday - Holiday Search

**Function**: Search for holiday information

**Parameters**:

- `query` (optional): Holiday name search, empty string returns next holiday
- `country` (optional): Country code (e.g., 'US', 'CN')
- `timezone` (optional): Timezone (for automatic country inference)
- `year` (optional): Year, defaults to current year
- `limit` (optional): Limit on number of results returned, defaults to 10

**Returns**: List of holiday information containing the following fields:

- `name`: Holiday name
- `date`: Date (YYYY-MM-DD)
- `country`: Country code
- `year`: Year
- `days_until`: Days until the holiday
- `holiday_duration`: Holiday duration in days

**Examples**:

```python
# Search for specific holiday
christmas = tm.search_holiday("Christmas", country="US")
# -> [{'name': 'Christmas Day', 'date': '2025-12-25', 'country': 'US', 'year': 2025, 'days_until': 332, 'holiday_duration': 1}]

# Get next holiday
next_holiday = tm.search_holiday("")
# -> [{'name': '春节', 'date': '2025-01-29', 'country': 'CN', 'year': 2025, 'days_until': 2, 'holiday_duration': 7}]

# Automatically infer country through timezone
jp_new_year = tm.search_holiday("New Year", timezone="Asia/Tokyo")
# -> [{'name': '元日', 'date': '2025-01-01', 'country': 'JP', 'year': 2025, 'days_until': -26, 'holiday_duration': 1}]
```

### 6. list_holidays - Holiday List

**Function**: List all holidays for specified country and year

**Parameters**:

- `country` (optional): Country code
- `timezone` (optional): Timezone (for automatic country inference)
- `year` (optional): Year, defaults to current year

**Returns**: List of holiday information

**Examples**:

```python
# List US holidays for 2025
us_holidays = tm.list_holidays(country="US", year=2025)
# -> [{'name': 'New Year\'s Day', 'date': '2025-01-01', 'country': 'US', 'year': 2025, 'holiday_duration': 1}, ...]

# Automatically infer through timezone
jp_holidays = tm.list_holidays(timezone="Asia/Tokyo", year=2025)
# -> [{'name': '元日', 'date': '2025-01-01', 'country': 'JP', 'year': 2025, 'holiday_duration': 1}, ...]

# List local country holidays
local_holidays = tm.list_holidays()
# -> [{'name': '元旦', 'date': '2025-01-01', 'country': 'CN', 'year': 2025, 'holiday_duration': 3}, ...]
```

## Configuration

TimeMaster supports flexible configuration through multiple methods:

### Environment Variables

```bash
# Core configuration
export TIMEMASTER_API_ENDPOINT="https://worldtimeapi.org/api"
export TIMEMASTER_TIMEOUT="10"
export TIMEMASTER_DEFAULT_TIMEZONE="UTC"
export TIMEMASTER_CACHE_DURATION="300"
export TIMEMASTER_OFFLINE_MODE="true"  # Force offline mode
export TIMEMASTER_AUTO_TIMEZONE="true"  # Enable auto-detection
```

### Configuration File

Create a `config.json` file:

```json
{
  "api_endpoint": "https://worldtimeapi.org/api",
  "timeout": 10,
  "default_timezone": "UTC",
  "cache_duration": 300,
  "offline_mode": false,
  "auto_timezone": true
}
```

### Direct Initialization

```python
from time-master.core import TimeMaster
from time-master.config import TimeMasterConfig

# Using configuration object
config = TimeMasterConfig()
config.update({'api_endpoint': 'https://custom-api.example.com/api'})
tm = TimeMaster(config=config)

# Using direct parameters
tm = TimeMaster(
    api_endpoint="https://worldtimeapi.org/api",
    timeout=10,
    default_timezone="UTC",
    cache_duration=300,
    offline_mode=False,
    auto_timezone=True
)
```

## Advanced Usage

### Working with Different Time Formats

```python
# ISO format (default)
iso_time = tm.get_time(timezone="Asia/Tokyo")
# -> "2025-01-27T22:01:00+09:00"

# Friendly Chinese format
friendly_time = tm.get_time(timezone="Asia/Shanghai", format="friendly_cn")
# -> "2025年01月27日 21:01:00 CST"

# Converting existing timestamps
converted = tm.get_time(
    time_str="2024-12-25T00:00:00",
    from_tz="UTC",
    timezone="America/New_York"
)
# -> "2024-12-24T19:00:00-05:00"
```

### Timezone Operations

```python
# Get local system timezone
local_tz = tm.get_local_timezone()
# -> "Asia/Shanghai"

# Search for timezones
tokyo_zones = tm.search_timezones("tokyo")
# -> ['Asia/Tokyo']

# List all available timezones
all_zones = tm.search_timezones("", limit=10)
# -> ['Africa/Abidjan', 'Africa/Accra', ...]

# Fuzzy search
china_zones = tm.search_timezones("china")
# -> ['Asia/Shanghai', 'Asia/Urumqi']
```

### Holiday Data Analysis

```python
# Get comprehensive holiday information
christmas = tm.search_holiday("Christmas", country="US")
holiday_info = christmas[0]
print(f"Holiday: {holiday_info['name']}")
print(f"Date: {holiday_info['date']}")
print(f"Days until: {holiday_info['days_until']}")
print(f"Duration: {holiday_info['holiday_duration']} days")

# Analyze holiday patterns
us_holidays = tm.list_holidays(country="US", year=2025)
long_holidays = [h for h in us_holidays if h['holiday_duration'] > 1]
print(f"Long holidays in US: {len(long_holidays)}")

# Cross-country holiday comparison
us_new_year = tm.search_holiday("New Year", country="US")
jp_new_year = tm.search_holiday("New Year", country="JP")
print(f"US New Year duration: {us_new_year[0]['holiday_duration']} days")
print(f"JP New Year duration: {jp_new_year[0]['holiday_duration']} days")
```

## Error Handling

All interfaces provide appropriate error handling:

- **Invalid timezone**: Returns error message or uses default timezone
- **Network errors**: Automatically degrades to offline mode
- **Invalid parameters**: Returns detailed error descriptions
- **Data unavailable**: Provides alternative solutions or default values

## Performance Optimization

- **Caching mechanism**: Holiday data is automatically cached to reduce duplicate queries
- **Offline mode**: Automatically switches to local time when network is unavailable
- **Smart inference**: Automatically infers country and region based on timezone
- **Batch queries**: Supports querying multiple holidays at once

## Best Practices

### Error Handling

```python
from time-master.core import TimeMaster
from time-master.exceptions import TimeMasterError

tm = TimeMaster()

try:
    # Handle timezone errors gracefully
    time_result = tm.get_time(timezone="Invalid/Timezone")
except TimeMasterError as e:
    print(f"TimeMaster error: {e}")
    # Fallback to local time
    time_result = tm.get_time()

try:
    # Handle network issues for holiday queries
    holidays = tm.search_holiday("Christmas", country="US")
except Exception as e:
    print(f"Holiday query failed: {e}")
    # Use cached data or provide default response
    holidays = []
```

### Performance Optimization

```python
# Use caching for repeated queries
tm = TimeMaster(cache_duration=600)  # 10 minutes cache

# Batch holiday queries for better performance
countries = ["US", "GB", "FR", "DE"]
all_holidays = {}
for country in countries:
    all_holidays[country] = tm.list_holidays(country=country, year=2025)

# Use offline mode for better reliability
import os
os.environ['TIMEMASTER_OFFLINE_MODE'] = 'true'
tm = TimeMaster()  # Will use system timezone and cached holiday data
```

### Integration Patterns

```python
# Logging with timezone conversion
import logging
from datetime import datetime, timezone

def log_with_timezone(message, target_tz="Asia/Shanghai"):
    utc_time = datetime.now(timezone.utc)
    local_time = tm.convert(utc_time, target_timezone=target_tz)
    logging.info(f"[{local_time}] {message}")

# Scheduling with holiday awareness
def is_business_day(date_str, country="US"):
    holidays = tm.list_holidays(country=country)
    holiday_dates = [h['date'] for h in holidays]
    return date_str not in holiday_dates

# Multi-timezone application support
def get_user_local_time(user_timezone):
    return tm.get_time(timezone=user_timezone, format="friendly_cn")
```