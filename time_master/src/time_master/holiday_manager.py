import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import holidays
import pycountry
from thefuzz import fuzz

logger = logging.getLogger(__name__)

class HolidayManager:
    """
    Manages holiday data and queries for different countries and regions.
    """
    
    def __init__(self, cache_ttl: int = 3600):
        """
        Initialize HolidayManager.
        
        Args:
            cache_ttl: Cache time-to-live in seconds
        """
        self._cache = {}
        self._cache_ttl = cache_ttl
        self._timezone_to_country = self._build_timezone_country_mapping()
    
    def _build_timezone_country_mapping(self) -> Dict[str, str]:
        """
        Build a mapping from timezone to country code.
        
        Returns:
            Dictionary mapping timezone names to ISO country codes
        """
        mapping = {
            # Major timezone to country mappings
            'America/New_York': 'US',
            'America/Los_Angeles': 'US',
            'America/Chicago': 'US',
            'America/Denver': 'US',
            'America/Toronto': 'CA',
            'America/Vancouver': 'CA',
            'Europe/London': 'GB',
            'Europe/Paris': 'FR',
            'Europe/Berlin': 'DE',
            'Europe/Rome': 'IT',
            'Europe/Madrid': 'ES',
            'Europe/Amsterdam': 'NL',
            'Europe/Brussels': 'BE',
            'Europe/Vienna': 'AT',
            'Europe/Zurich': 'CH',
            'Europe/Stockholm': 'SE',
            'Europe/Oslo': 'NO',
            'Europe/Copenhagen': 'DK',
            'Europe/Helsinki': 'FI',
            'Europe/Warsaw': 'PL',
            'Europe/Prague': 'CZ',
            'Europe/Budapest': 'HU',
            'Europe/Bucharest': 'RO',
            'Europe/Sofia': 'BG',
            'Europe/Athens': 'GR',
            'Europe/Istanbul': 'TR',
            'Europe/Moscow': 'RU',
            'Asia/Tokyo': 'JP',
            'Asia/Shanghai': 'CN',
            'Asia/Hong_Kong': 'HK',
            'Asia/Singapore': 'SG',
            'Asia/Seoul': 'KR',
            'Asia/Kolkata': 'IN',
            'Asia/Dubai': 'AE',
            'Asia/Bangkok': 'TH',
            'Asia/Jakarta': 'ID',
            'Asia/Manila': 'PH',
            'Australia/Sydney': 'AU',
            'Australia/Melbourne': 'AU',
            'Australia/Perth': 'AU',
            'Pacific/Auckland': 'NZ',
            'Africa/Cairo': 'EG',
            'Africa/Johannesburg': 'ZA',
            'America/Sao_Paulo': 'BR',
            'America/Buenos_Aires': 'AR',
            'America/Mexico_City': 'MX',
        }
        return mapping
    
    def get_country_from_timezone(self, timezone: str) -> Optional[str]:
        """
        Get country code from timezone.
        
        Args:
            timezone: Timezone name (e.g., 'America/New_York')
            
        Returns:
            ISO country code or None if not found
        """
        # Direct mapping
        if timezone in self._timezone_to_country:
            return self._timezone_to_country[timezone]
        
        # Try to infer from timezone name
        if timezone.startswith('America/'):
            city = timezone.split('/')[-1]
            # Common US cities
            us_cities = ['New_York', 'Los_Angeles', 'Chicago', 'Denver', 'Phoenix', 'Detroit', 'Boston']
            if city in us_cities:
                return 'US'
            # Canadian cities
            ca_cities = ['Toronto', 'Vancouver', 'Montreal', 'Calgary', 'Edmonton']
            if city in ca_cities:
                return 'CA'
        elif timezone.startswith('Europe/'):
            city = timezone.split('/')[-1]
            # Try to match city to country
            city_country_map = {
                'London': 'GB', 'Paris': 'FR', 'Berlin': 'DE', 'Rome': 'IT',
                'Madrid': 'ES', 'Amsterdam': 'NL', 'Brussels': 'BE', 'Vienna': 'AT',
                'Zurich': 'CH', 'Stockholm': 'SE', 'Oslo': 'NO', 'Copenhagen': 'DK',
                'Helsinki': 'FI', 'Warsaw': 'PL', 'Prague': 'CZ', 'Budapest': 'HU'
            }
            if city in city_country_map:
                return city_country_map[city]
        
        return None
    
    def get_holidays(self, country: str, year: int = None) -> holidays.HolidayBase:
        """
        Get holidays for a specific country and year.
        
        Args:
            country: ISO country code
            year: Year (default: current year)
            
        Returns:
            Holidays object for the country
        """
        if year is None:
            year = datetime.now().year
        
        cache_key = f"{country}_{year}"
        
        # Check cache
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if datetime.now().timestamp() - cache_entry['timestamp'] < self._cache_ttl:
                return cache_entry['data']
        
        try:
            # Get holidays for the country
            country_holidays = holidays.country_holidays(country, years=year)
            
            # Cache the result
            self._cache[cache_key] = {
                'data': country_holidays,
                'timestamp': datetime.now().timestamp()
            }
            
            return country_holidays
        except Exception as e:
            logger.warning(f"Failed to get holidays for country {country}: {e}")
            return holidays.country_holidays('US', years=year)  # Fallback to US
    
    def get_next_holiday(self, country: str = None, timezone: str = None) -> Optional[Tuple[str, datetime]]:
        """
        Get the next upcoming holiday.
        
        Args:
            country: ISO country code
            timezone: Timezone to infer country from
            
        Returns:
            Tuple of (holiday_name, holiday_date) or None
        """
        if not country and timezone:
            country = self.get_country_from_timezone(timezone)
        
        if not country:
            country = 'US'  # Default fallback
        
        today = datetime.now().date()
        current_year = today.year
        
        # Get holidays for current and next year
        current_holidays = self.get_holidays(country, current_year)
        next_holidays = self.get_holidays(country, current_year + 1)
        
        # Combine holidays
        all_holidays = dict(current_holidays)
        all_holidays.update(dict(next_holidays))
        
        # Find next holiday
        upcoming_holidays = [(date, name) for date, name in all_holidays.items() if date > today]
        
        if upcoming_holidays:
            upcoming_holidays.sort(key=lambda x: x[0])
            next_date, next_name = upcoming_holidays[0]
            return next_name, datetime.combine(next_date, datetime.min.time())
        
        return None
    
    def calculate_days_to_holiday(self, holiday_name: str, country: str = None, timezone: str = None) -> Optional[int]:
        """
        Calculate days until a specific holiday.
        
        Args:
            holiday_name: Name of the holiday to search for
            country: ISO country code
            timezone: Timezone to infer country from
            
        Returns:
            Number of days until the holiday, or None if not found
        """
        if not country and timezone:
            country = self.get_country_from_timezone(timezone)
        
        if not country:
            country = 'US'  # Default fallback
        
        today = datetime.now().date()
        current_year = today.year
        
        # Get holidays for current and next year
        current_holidays = self.get_holidays(country, current_year)
        next_holidays = self.get_holidays(country, current_year + 1)
        
        # Combine holidays
        all_holidays = dict(current_holidays)
        all_holidays.update(dict(next_holidays))
        
        # Find matching holiday using fuzzy matching
        best_match = None
        best_score = 0
        
        for date, name in all_holidays.items():
            if date > today:
                score = fuzz.partial_ratio(holiday_name.lower(), name.lower())
                if score > best_score and score > 70:  # Threshold for matching
                    best_score = score
                    best_match = date
        
        if best_match:
            return (best_match - today).days
        
        return None
    
    def list_holidays(self, country: str = None, timezone: str = None, year: int = None, limit: int = 10) -> List[Tuple[str, datetime]]:
        """
        List holidays for a country.
        
        Args:
            country: ISO country code
            timezone: Timezone to infer country from
            year: Year (default: current year)
            limit: Maximum number of holidays to return
            
        Returns:
            List of (holiday_name, holiday_date) tuples
        """
        if not country and timezone:
            country = self.get_country_from_timezone(timezone)
        
        if not country:
            country = 'US'  # Default fallback
        
        if year is None:
            year = datetime.now().year
        
        country_holidays = self.get_holidays(country, year)
        
        # Convert to list and sort by date
        holiday_list = [(name, datetime.combine(date, datetime.min.time())) 
                       for date, name in country_holidays.items()]
        holiday_list.sort(key=lambda x: x[1])
        
        return holiday_list[:limit]
    
    def calculate_holiday_duration(self, holiday_date: datetime, country: str) -> int:
        """
        Calculate the duration of consecutive holiday days including weekends.
        
        Args:
            holiday_date: The holiday date
            country: ISO country code
            
        Returns:
            Number of consecutive holiday days (including weekends)
        """
        if isinstance(holiday_date, datetime):
            target_date = holiday_date.date()
        else:
            target_date = holiday_date
            
        year = target_date.year
        country_holidays = self.get_holidays(country, year)
        
        # Convert holidays to set of dates for faster lookup
        holiday_dates = set(country_holidays.keys())
        
        # Function to check if a date is a holiday or weekend
        def is_non_working_day(date):
            return date in holiday_dates or date.weekday() >= 5  # Saturday=5, Sunday=6
        
        # Find the start of the consecutive holiday period
        start_date = target_date
        while start_date > datetime(year, 1, 1).date():
            prev_date = start_date - timedelta(days=1)
            if not is_non_working_day(prev_date):
                break
            start_date = prev_date
        
        # Find the end of the consecutive holiday period
        end_date = target_date
        while end_date < datetime(year, 12, 31).date():
            next_date = end_date + timedelta(days=1)
            if not is_non_working_day(next_date):
                break
            end_date = next_date
        
        # Calculate duration
        duration = (end_date - start_date).days + 1
        return duration

    def get_country_name(self, country_code: str) -> str:
        """
        Get country name from country code.
        
        Args:
            country_code: ISO country code
            
        Returns:
            Country name
        """
        try:
            country = pycountry.countries.get(alpha_2=country_code)
            return country.name if country else country_code
        except Exception:
            return country_code