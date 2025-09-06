#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chinese Calendar Manager for TimeMaster.

Provides a unified interface for Chinese calendar functionality including:
- Gregorian to Lunar date conversion
- Lunar to Gregorian date conversion
- Ganzhi (Heavenly Stems and Earthly Branches) calculation
- Solar terms information
- Chinese zodiac
- Traditional Chinese holidays
- Almanac information (Yi/Ji - suitable/unsuitable activities)
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Union

try:
    import cnlunar
except ImportError:
    cnlunar = None
    logging.warning("cnlunar library not available. Chinese calendar features will be disabled.")


class ChineseCalendarManager:
    """Unified Chinese Calendar Manager with simplified interface."""

    def __init__(self):
        """Initialize the Chinese Calendar Manager."""
        self.logger = logging.getLogger(__name__)
        self._cnlunar_available = cnlunar is not None

        if not self._cnlunar_available:
            self.logger.warning("cnlunar library not available. Chinese calendar features disabled.")

    def _ensure_datetime(self, date_input: Union[str, datetime, date]) -> datetime:
        """Convert various date inputs to datetime object."""
        if isinstance(date_input, str):
            return datetime.strptime(date_input, '%Y-%m-%d')
        elif isinstance(date_input, datetime):
            return date_input
        else:
            # Convert date to datetime
            return datetime.combine(date_input, datetime.min.time())

    def _check_availability(self) -> bool:
        """Check if cnlunar is available."""
        if not self._cnlunar_available:
            return False
        return True

    def get_chinese_calendar_info(self, date_input: Union[str, datetime, date]) -> Dict:
        """Get comprehensive Chinese calendar information for a given date.

        This is the main unified interface that provides all Chinese calendar data.

        Args:
            date_input: Date string (YYYY-MM-DD), datetime object, or date object

        Returns:
            dict: Complete Chinese calendar information including:
                - Basic lunar date info
                - Ganzhi (Four Pillars)
                - Zodiac information
                - Solar terms
                - Almanac info (Yi/Ji)
                - Holiday information
        """
        if not self._check_availability():
            return {'error': 'cnlunar library not available'}

        try:
            date_obj = self._ensure_datetime(date_input)

            # Check date range (cnlunar supports 1900-2100)
            if date_obj.year < 1900 or date_obj.year > 2100:
                return {'error': f'Date {date_obj.year} is outside supported range (1900-2100)'}

            lunar = cnlunar.Lunar(date_obj)

            # Get solar terms for the year
            solar_terms = lunar.thisYearSolarTermsDic if hasattr(lunar, 'thisYearSolarTermsDic') else {}

            # Get today's solar term if any
            today_solar_term = getattr(lunar, 'todaySolarTerms', None)

            # Get almanac information
            good_things = getattr(lunar, 'goodThing', [])
            bad_things = getattr(lunar, 'badThing', [])

            return {
                # Basic date information
                'gregorian_date': date_obj.strftime('%Y-%m-%d'),
                'weekday': date_obj.strftime('%A'),
                'weekday_cn': getattr(lunar, 'weekDayCn', ''),

                # Lunar date information
                'lunar': {
                    'year': lunar.lunarYear,
                    'month': lunar.lunarMonth,
                    'day': lunar.lunarDay,
                    'year_cn': lunar.lunarYearCn,
                    'month_cn': lunar.lunarMonthCn,
                    'day_cn': lunar.lunarDayCn,
                    'is_leap_month': lunar.isLunarLeapMonth,
                    'lunar_date_str': f"{lunar.lunarYearCn}年{lunar.lunarMonthCn}{lunar.lunarDayCn}"
                },

                # Ganzhi (Four Pillars) information
                'ganzhi': {
                    'year': getattr(lunar, 'year8Char', ''),
                    'month': getattr(lunar, 'month8Char', ''),
                    'day': getattr(lunar, 'day8Char', ''),
                    'hour': getattr(lunar, 'twohour8Char', ''),
                    'full_bazi': getattr(lunar, 'get_the8char', lambda: '')() if hasattr(lunar, 'get_the8char') else ''
                },

                # Zodiac information
                'zodiac': {
                    'chinese_zodiac': lunar.chineseYearZodiac,
                    'zodiac_clash': getattr(lunar, 'chineseZodiacClash', ''),
                    'star_zodiac': getattr(lunar, 'starZodiac', ''),
                    'east_zodiac': getattr(lunar, 'todayEastZodiac', '')
                },

                # Solar terms information
                'solar_terms': {
                    'today_solar_term': today_solar_term,
                    'next_solar_term': getattr(lunar, 'nextSolarTerm', ''),
                    'next_solar_term_date': getattr(lunar, 'nextSolarTermDate', ''),
                    'year_solar_terms': solar_terms
                },

                # Almanac information (Yi/Ji - suitable/unsuitable activities)
                'almanac': {
                    'suitable_activities': (
                        good_things if isinstance(good_things, list)
                        else [good_things] if good_things else []
                    ),
                    'unsuitable_activities': (
                        bad_things if isinstance(bad_things, list)
                        else [bad_things] if bad_things else []
                    ),
                    'level': getattr(lunar, 'todayLevelName', ''),
                    'god_type': getattr(lunar, 'godType', ''),
                    'angel_demon': getattr(lunar, 'angelDemon', '')
                },

                # Additional traditional information
                'traditional': {
                    'twenty_eight_stars': getattr(lunar, 'today28Star', ''),
                    'twelve_day_officer': getattr(lunar, 'today12DayOfficer', ''),
                    'five_elements': (
                        getattr(lunar, 'get_today5Elements', lambda: '')()
                        if hasattr(lunar, 'get_today5Elements') else ''
                    ),
                    'nayin': (
                        getattr(lunar, 'get_nayin', lambda: '')()
                        if hasattr(lunar, 'get_nayin') else ''
                    ),
                    'fetal_god': (
                        getattr(lunar, 'get_fetalGod', lambda: '')()
                        if hasattr(lunar, 'get_fetalGod') else ''
                    )
                },

                # Holiday information
                'holidays': {
                    'legal_holidays': (
                        getattr(lunar, 'get_legalHolidays', lambda: [])()
                        if hasattr(lunar, 'get_legalHolidays') else []
                    ),
                    'other_holidays': (
                        getattr(lunar, 'get_otherHolidays', lambda: [])()
                        if hasattr(lunar, 'get_otherHolidays') else []
                    ),
                    'lunar_holidays': (
                        getattr(lunar, 'get_otherLunarHolidays', lambda: [])()
                        if hasattr(lunar, 'get_otherLunarHolidays') else []
                    )
                }
            }

        except Exception as e:
            self.logger.error(f"Error getting Chinese calendar info: {e}")
            return {'error': str(e)}

    def gregorian_to_lunar(self, date_input: Union[str, datetime, date]) -> Dict:
        """Convert Gregorian date to Lunar date (simplified interface)."""
        info = self.get_chinese_calendar_info(date_input)
        if 'error' in info:
            return info

        return {
            'gregorian_date': info['gregorian_date'],
            'lunar_year': info['lunar']['year'],
            'lunar_month': info['lunar']['month'],
            'lunar_day': info['lunar']['day'],
            'lunar_year_cn': info['lunar']['year_cn'],
            'lunar_month_cn': info['lunar']['month_cn'],
            'lunar_day_cn': info['lunar']['day_cn'],
            'is_leap_month': info['lunar']['is_leap_month'],
            'lunar_date_str': info['lunar']['lunar_date_str']
        }

    def lunar_to_gregorian(
            self,
            lunar_year: int,
            lunar_month: int,
            lunar_day: int,
            is_leap_month: bool = False) -> Dict:
        """Convert Lunar date to Gregorian date (simplified interface)."""
        if not self._check_availability():
            return {'error': 'cnlunar library not available'}

        try:
            # Search for the corresponding Gregorian date
            start_date = date(lunar_year, 1, 1)
            end_date = date(lunar_year + 1, 12, 31)

            current_date = start_date
            while current_date <= end_date:
                try:
                    test_datetime = datetime.combine(current_date, datetime.min.time())
                    lunar_check = cnlunar.Lunar(test_datetime)

                    if (lunar_check.lunarYear == lunar_year
                        and lunar_check.lunarMonth == lunar_month
                        and lunar_check.lunarDay == lunar_day
                            and lunar_check.isLunarLeapMonth == is_leap_month):

                        return {
                            'gregorian_date': current_date.strftime('%Y-%m-%d'),
                            'lunar_year': lunar_year,
                            'lunar_month': lunar_month,
                            'lunar_day': lunar_day,
                            'is_leap_month': is_leap_month,
                            'weekday': current_date.strftime('%A'),
                            'zodiac': lunar_check.chineseYearZodiac
                        }
                except BaseException:
                    pass

                current_date += timedelta(days=1)

            return {'error': f'Could not find Gregorian date for lunar {lunar_year}-{lunar_month}-{lunar_day}'}

        except Exception as e:
            self.logger.error(f"Error converting lunar to gregorian date: {e}")
            return {'error': str(e)}

    def get_solar_terms(self, year: int) -> Dict:
        """Get solar terms for a specific year (simplified interface)."""
        if not self._check_availability():
            return {'error': 'cnlunar library not available'}

        try:
            # Create a lunar object for the year
            test_date = datetime(year, 6, 1)  # Use mid-year date
            lunar = cnlunar.Lunar(test_date)

            solar_terms = getattr(lunar, 'thisYearSolarTermsDic', {})

            return {
                'year': year,
                'solar_terms': solar_terms,
                'count': len(solar_terms)
            }

        except Exception as e:
            self.logger.error(f"Error getting solar terms: {e}")
            return {'error': str(e)}

    def get_zodiac(self, year: int) -> Dict:
        """Get Chinese zodiac for a specific year (simplified interface)."""
        if not self._check_availability():
            return {'error': 'cnlunar library not available'}

        try:
            # Use mid-year date to ensure we get the correct lunar year
            # since Chinese New Year can fall in January or February
            test_date = datetime(year, 6, 1)
            lunar = cnlunar.Lunar(test_date)

            return {
                'year': year,
                'zodiac': lunar.chineseYearZodiac,
                'zodiac_clash': getattr(lunar, 'chineseZodiacClash', ''),
                'year_ganzhi': getattr(lunar, 'year8Char', '')
            }

        except Exception as e:
            self.logger.error(f"Error getting zodiac: {e}")
            return {'error': str(e)}
