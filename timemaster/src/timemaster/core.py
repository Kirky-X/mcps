"""
TimeMaster Core Implementation
"""
import datetime
import logging
import socket
import time
from typing import Optional, Union, List
import requests
import pytz
import holidays
from tzlocal import get_localzone
from thefuzz import process
from requests.exceptions import RequestException, Timeout
from .config import TimeMasterConfig
from .exceptions import TimeMasterError
from .holiday_manager import HolidayManager

# Configure logging
logger = logging.getLogger(__name__)


class TimeMaster:
    """
    A canonical, high-reliability, developer-first modular common component 
    for handling timezones and time in Python.
    """
    
    # Predefined format constants
    FORMAT_ISO = "iso"
    FORMAT_FRIENDLY_CN = "friendly_cn"
    
    def __init__(self, api_endpoint: Optional[str] = None, timeout: Optional[int] = None, 
                 cache_ttl: Optional[int] = None, config: Optional[TimeMasterConfig] = None,
                 auto_local_timezone: Optional[bool] = None):
        """
        Initialize TimeMaster with configurable parameters.
        
        Args:
            api_endpoint: The World Time API endpoint to use
            timeout: Timeout for API requests in seconds
            cache_ttl: Cache time-to-live in seconds
            config: TimeMasterConfig instance for centralized configuration
            auto_local_timezone: Whether to automatically use local timezone as default (overrides config)
        """
        # Use provided config or create default one
        self._config = config or TimeMasterConfig()
        
        # Override config with explicit parameters if provided
        self.api_endpoint = api_endpoint or self._config.api_endpoint
        self.timeout = timeout or self._config.timeout
        self.cache_ttl = cache_ttl or self._config.cache_ttl
        
        # Cache storage: {timezone: (timestamp, data)}
        self._cache = {}
        
        # Online/offline mode state - read from config
        self._force_offline = self._config.is_offline_mode()
        self._is_online = self._check_network_connectivity()
        
        # Auto timezone detection - use parameter if provided, otherwise use config
        if auto_local_timezone is not None:
            self._auto_local_timezone = auto_local_timezone
        else:
            self._auto_local_timezone = self._config.should_auto_detect_timezone()
            
        self._holiday_manager = HolidayManager(cache_ttl=self._config.cache_ttl)
        
        # Auto-detect local timezone if enabled
        if self._auto_local_timezone:
            self._detected_local_timezone = self._auto_detect_local_timezone()
        else:
            self._detected_local_timezone = None
        
        logger.info(f"TimeMaster initialized. Online mode: {self._is_online}, Auto timezone: {self._auto_local_timezone}")
    
    def _check_network_connectivity(self) -> bool:
        """
        Check network connectivity by attempting to connect to a reliable endpoint.
        
        Returns:
            bool: True if network is available, False otherwise
        """
        if self._force_offline:
            return False
            
        try:
            # Try to connect to Google DNS
            socket.create_connection(("8.8.8.8", 53), timeout=self.timeout)
            return True
        except OSError:
            return False
    

    
    def _get_online_time(self, timezone: str) -> datetime.datetime:
        """
        Get current time for a timezone using the online API.
        
        Args:
            timezone: IANA timezone string
            
        Returns:
            datetime: Current time in the specified timezone
            
        Raises:
            RequestException: If API request fails
            ValueError: If timezone is invalid
        """
        # Check cache first
        current_time = time.time()
        if timezone in self._cache:
            cache_time, cached_data = self._cache[timezone]
            if current_time - cache_time < self.cache_ttl:
                logger.debug(f"Cache hit for timezone: {timezone}")
                return cached_data
        
        # Make API request
        url = f"{self.api_endpoint}/timezone/{timezone}"
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # Parse datetime from API response
            dt_str = data['datetime']
            # Handle the timezone offset format from World Time API
            if '+' in dt_str:
                dt_part, _ = dt_str.rsplit('+', 1)
            elif '-' in dt_str[10:]:  # After the date part
                dt_part, _ = dt_str.rsplit('-', 1)
            else:
                dt_part = dt_str
            
            # Create datetime object
            dt = datetime.datetime.fromisoformat(dt_part)
            
            # Apply timezone info
            tz = pytz.timezone(timezone)
            aware_dt = tz.localize(dt)
            
            # Cache the result
            self._cache[timezone] = (current_time, aware_dt)
            
            logger.debug(f"Retrieved time for {timezone} from online API")
            return aware_dt
            
        except (RequestException, Timeout, KeyError) as e:
            logger.warning(f"Failed to get time from API for timezone {timezone}: {e}")
            raise
    
    def _get_offline_time(self, timezone: str) -> datetime.datetime:
        """
        Get current time for a timezone using the local system.
        
        Args:
            timezone: IANA timezone string
            
        Returns:
            datetime: Current time in the specified timezone
        """
        try:
            tz = pytz.timezone(timezone)
            local_dt = datetime.datetime.now(tz)
            logger.debug(f"Retrieved time for {timezone} from local system")
            return local_dt
        except Exception as e:
            logger.error(f"Failed to get time locally for timezone {timezone}: {e}")
            # Fallback to UTC
            return datetime.datetime.now(pytz.UTC)
    
    def get_time(self, timezone: str = None, time_str: str = None, from_tz: str = None, format: str = FORMAT_ISO) -> str:
        """
        Unified time interface that can get current time or convert existing time.
        
        Args:
            timezone: Target timezone (default: local timezone if auto_local_timezone is True, otherwise UTC)
            time_str: Time string to convert (if None, gets current time)
            from_tz: Source timezone for conversion (required if time_str is provided)
            format: Output format (iso, friendly_cn)
            
        Returns:
            Formatted time string
        """
        # Determine the timezone to use
        if timezone is None:
            if self._auto_local_timezone:
                timezone = self.get_local_timezone()
            else:
                timezone = "UTC"
        
        if time_str is not None:
            # Convert existing time
            if from_tz is None:
                raise ValueError("from_tz is required when converting existing time")
            
            import datetime
            import pytz
            
            # Parse the input time string
            dt = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            
            # If datetime is naive, localize it to the source timezone
            if dt.tzinfo is None:
                from_timezone = pytz.timezone(from_tz)
                dt = from_timezone.localize(dt)
            
            # Convert to target timezone
            converted_time = self.convert(dt, timezone)
            return self._format_time(converted_time, format)
        else:
            # Get current time
            if self._is_online and not self._force_offline:
                try:
                    current_time = self._get_online_time(timezone)
                except Exception as e:
                    # Network failure - auto-degrade to offline mode
                    logger.warning(f"Network request failed, auto-degrading to offline mode: {e}")
                    self._is_online = False
                    current_time = self._get_offline_time(timezone)
            else:
                current_time = self._get_offline_time(timezone)
            
            return self._format_time(current_time, format)
    
    def now(self, timezone: str = None, format: str = FORMAT_ISO) -> str:
        """
        Get current time in specified timezone with specified format.
        
        Args:
            timezone: Target timezone (default: local timezone if auto_local_timezone is True, otherwise UTC)
            format: Output format (iso, friendly_cn)
            
        Returns:
            Formatted time string
        """
        return self.get_time(timezone=timezone, format=format)
    
    def _format_time(self, dt: datetime.datetime, format: str) -> str:
        """
        Format datetime object according to specified format.
        
        Args:
            dt: Datetime object to format
            format: Format type (iso, friendly_cn)
            
        Returns:
            Formatted time string
        """
        if format == self.FORMAT_ISO:
            return dt.isoformat()
        elif format == self.FORMAT_FRIENDLY_CN:
            # Chinese friendly format
            return dt.strftime("%Y年%m月%d日 %H:%M:%S %Z")
        else:
            # Default to ISO format
            return dt.isoformat()
    
    def convert(self, dt: datetime.datetime, target_timezone: str) -> datetime.datetime:
        """
        Convert a datetime object to a target timezone.
        
        Args:
            dt: Datetime object (naive or timezone-aware)
            target_timezone: Target IANA timezone string
            
        Returns:
            datetime: Converted datetime in target timezone
        """
        # Validate target timezone
        if target_timezone not in pytz.all_timezones:
            raise ValueError(f"Invalid target timezone: {target_timezone}")
        
        target_tz = pytz.timezone(target_timezone)
        
        # Handle naive datetime
        if dt.tzinfo is None:
            # Assume it's in local timezone
            local_tz = get_localzone()
            # Check if local_tz is a pytz timezone or zoneinfo
            if hasattr(local_tz, 'localize'):
                # pytz timezone
                dt = local_tz.localize(dt)
            else:
                # zoneinfo timezone
                dt = dt.replace(tzinfo=local_tz)
        
        # Convert to target timezone
        converted_dt = dt.astimezone(target_tz)
        return converted_dt
    
    def difference(self, tz1: str, tz2: str) -> datetime.timedelta:
        """
        Calculate the time difference between two timezones.
        
        Args:
            tz1: First IANA timezone string
            tz2: Second IANA timezone string
            
        Returns:
            timedelta: Time difference between the two timezones
        """
        # Validate timezones
        if tz1 not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {tz1}")
        if tz2 not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {tz2}")
        
        # Get current time in both timezones
        try:
            if self._is_online and not self._force_offline:
                dt1 = self._get_online_time(tz1)
                dt2 = self._get_online_time(tz2)
            else:
                dt1 = self._get_offline_time(tz1)
                dt2 = self._get_offline_time(tz2)
        except Exception as e:
            logger.warning(f"Error getting timezone times: {e}")
            logger.warning("Falling back to offline mode")
            dt1 = self._get_offline_time(tz1)
            dt2 = self._get_offline_time(tz2)
        
        # Convert both to UTC for accurate difference calculation
        utc1 = dt1.astimezone(pytz.UTC)
        utc2 = dt2.astimezone(pytz.UTC)
        
        # Calculate difference
        return utc1 - utc2
    
    def find_timezones(self, query: str, limit: int = 20) -> List[str]:
        """
        Find timezones matching the query using fuzzy search.
        If query is empty or whitespace, return all timezones.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of matching timezone names
        """
        if not query or query.strip() == "":
            # Return all timezones if query is empty
            all_timezones = sorted(list(pytz.all_timezones))
            return all_timezones[:limit]
        
        query_lower = query.lower()
        # Also create a version with spaces replaced by underscores for better matching
        query_underscore = query_lower.replace(" ", "_")
        matches = []
        
        for tz in pytz.all_timezones:
            tz_lower = tz.lower()
            # Check both original query and underscore version
            if (query_lower in tz_lower or 
                query_underscore in tz_lower or
                query_lower in tz_lower.replace("_", " ")):
                matches.append(tz)
                if len(matches) >= limit:
                    break
        
        return sorted(matches)
    
    def list_timezones(self, region: str = "") -> List[str]:
        """
        List all available timezones, optionally filtered by region.
        
        Args:
            region: Optional region filter (e.g., 'America', 'Europe')
            
        Returns:
            List of timezone names
        """
        all_timezones = list(pytz.all_timezones)
        
        if region:
            filtered = [tz for tz in all_timezones if tz.startswith(region)]
            return sorted(filtered)
        
        return sorted(all_timezones)
    
    def _auto_detect_local_timezone(self) -> str:
        """
        Auto-detect local timezone with network fallback.
        
        Returns:
            Detected local timezone name
        """
        # Try network-based detection first if online
        if self._is_online and not self._force_offline:
            try:
                # Try to get timezone from IP geolocation
                response = requests.get("http://worldtimeapi.org/api/ip", timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    timezone = data.get('timezone')
                    if timezone:
                        logger.info(f"Auto-detected timezone from network: {timezone}")
                        return timezone
            except Exception as e:
                logger.warning(f"Network timezone detection failed: {e}")
        
        # Fallback to local system detection
        try:
            import tzlocal
            local_tz = tzlocal.get_localzone()
            timezone = str(local_tz)
            logger.info(f"Auto-detected timezone from system: {timezone}")
            return timezone
        except Exception as e:
            logger.warning(f"System timezone detection failed: {e}")
            return "UTC"
    
    def get_local_timezone(self) -> str:
        """
        Get the local system timezone.
        
        Returns:
            Local timezone name (e.g., 'America/New_York')
        """
        # Use auto-detected timezone if available
        if self._detected_local_timezone:
            return self._detected_local_timezone
        
        # Fallback to system detection
        try:
            import tzlocal
            local_tz = tzlocal.get_localzone()
            return str(local_tz)
        except Exception as e:
            logger.warning(f"Failed to get local timezone: {e}")
            return "UTC"
    
    def get_next_holiday(self, country: str = None, timezone: str = None):
        """
        Get the next upcoming holiday.
        
        Args:
            country: ISO country code
            timezone: Timezone to infer country from (defaults to local timezone)
            
        Returns:
            Dictionary with holiday information including days_until or None if no upcoming holidays
        """
        if not timezone and not country:
            timezone = self.get_local_timezone()
        
        if not country:
            country = self.get_country_from_timezone(timezone)
        
        try:
            holidays_data = holidays.country_holidays(country, years=datetime.datetime.now().year)
            today = datetime.datetime.now().date()
            
            upcoming_holidays = []
            for date, name in holidays_data.items():
                if date >= today:
                    days_until = (date - today).days
                    
                    # Calculate holiday duration
                    holiday_duration = self._holiday_manager.calculate_holiday_duration(
                        datetime.datetime.combine(date, datetime.datetime.min.time()),
                        country
                    )
                    
                    upcoming_holidays.append({
                        "name": name,
                        "date": date.strftime("%Y-%m-%d"),
                        "country": country,
                        "year": date.year,
                        "days_until": days_until,
                        "holiday_duration": holiday_duration
                    })
            
            if upcoming_holidays:
                # Sort by date and return the earliest one
                upcoming_holidays.sort(key=lambda x: x["date"])
                return upcoming_holidays[0]
            else:
                return None
        except Exception as e:
            logger.error(f"Error getting next holiday: {e}")
            return None
    
    def calculate_days_to_holiday(self, holiday_name: str, country: str = None, timezone: str = None):
        """
        Calculate days until a specific holiday.
        
        Args:
            holiday_name: Name of the holiday to search for
            country: ISO country code
            timezone: Timezone to infer country from (defaults to local timezone)
            
        Returns:
            Number of days until the holiday, or None if not found
        """
        if not timezone and not country:
            timezone = self.get_local_timezone()
        
        return self._holiday_manager.calculate_days_to_holiday(holiday_name, country=country, timezone=timezone)
    
    def list_holidays(self, country: str = None, timezone: str = None, year: int = None):
        """
        List all holidays for a specific country and year.
        
        Args:
            country: ISO country code
            timezone: Timezone to infer country from (defaults to local timezone)
            year: Year (default: current year)
            
        Returns:
            List of holiday dictionaries for the entire year
        """
        if not timezone and not country:
            timezone = self.get_local_timezone()
        
        if not country:
            country = self.get_country_from_timezone(timezone)
        
        if not year:
            year = datetime.datetime.now().year
        
        try:
            holidays_data = holidays.country_holidays(country, years=year)
            holidays_list = []
            
            for date, name in holidays_data.items():
                # Calculate holiday duration
                holiday_duration = self._holiday_manager.calculate_holiday_duration(
                    datetime.datetime.combine(date, datetime.datetime.min.time()),
                    country
                )
                
                holidays_list.append({
                    "name": name,
                    "date": date.strftime("%Y-%m-%d"),
                    "country": country,
                    "year": year,
                    "holiday_duration": holiday_duration
                })
            
            # Sort by date
            holidays_list.sort(key=lambda x: x["date"])
            
            return holidays_list
        except Exception as e:
            logger.error(f"Error listing holidays: {e}")
            return []
    
    def search_holiday(self, query: str = "", country: str = None, timezone: str = None, year: int = None, limit: int = 10):
        """
        Search for holidays by name. If query is empty, returns the next upcoming holiday.
        
        Args:
            query: Search query for holiday names (empty string returns next holiday)
            country: ISO country code
            timezone: Timezone to infer country from (defaults to local timezone)
            year: Year (default: current year)
            limit: Maximum number of results to return
            
        Returns:
            List of matching holiday dictionaries with days_until field
        """
        if not timezone and not country:
            timezone = self.get_local_timezone()
        
        # If query is empty, return next upcoming holiday
        if not query or query.strip() == "":
            next_holiday = self.get_next_holiday(country=country, timezone=timezone)
            if next_holiday:
                return [next_holiday]
            else:
                return []
        
        # Get all holidays for the year
        all_holidays = self.list_holidays(country=country, timezone=timezone, year=year)
        
        # Filter holidays by query and add days_until
        query_lower = query.lower()
        matching_holidays = []
        today = datetime.datetime.now().date()
        
        for holiday in all_holidays:
            if query_lower in holiday["name"].lower():
                # Add days_until calculation
                holiday_date = datetime.datetime.strptime(holiday["date"], "%Y-%m-%d").date()
                days_until = (holiday_date - today).days
                holiday["days_until"] = days_until
                
                # Add holiday duration calculation
                holiday_duration = self._holiday_manager.calculate_holiday_duration(
                    datetime.datetime.combine(holiday_date, datetime.datetime.min.time()),
                    holiday["country"]
                )
                holiday["holiday_duration"] = holiday_duration
                
                matching_holidays.append(holiday)
                if len(matching_holidays) >= limit:
                    break
        
        return matching_holidays
    
    def get_country_from_timezone(self, timezone: str = None):
        """
        Get country code from timezone.
        
        Args:
            timezone: Timezone name (defaults to local timezone)
            
        Returns:
            ISO country code or None if not found
        """
        if not timezone:
            timezone = self.get_local_timezone()
        
        return self._holiday_manager.get_country_from_timezone(timezone)