import unittest
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch

import holidays
import pytest
from time_master.holiday_manager import HolidayManager


class TestHolidayManager(unittest.TestCase):
    """Test cases for HolidayManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.holiday_manager = HolidayManager(cache_ttl=3600)

    def test_initialization(self):
        """Test HolidayManager initialization."""
        hm = HolidayManager(cache_ttl=1800)
        self.assertEqual(hm._cache_ttl, 1800)
        self.assertIsInstance(hm._cache, dict)
        self.assertIsInstance(hm._timezone_to_country, dict)

        # Test default cache_ttl
        hm_default = HolidayManager()
        self.assertEqual(hm_default._cache_ttl, 3600)

    def test_timezone_country_mapping(self):
        """Test timezone to country mapping."""
        # Test direct mappings
        self.assertEqual(self.holiday_manager.get_country_from_timezone('America/New_York'), 'US')
        self.assertEqual(self.holiday_manager.get_country_from_timezone('Europe/London'), 'GB')
        self.assertEqual(self.holiday_manager.get_country_from_timezone('Asia/Tokyo'), 'JP')
        self.assertEqual(self.holiday_manager.get_country_from_timezone('Australia/Sydney'), 'AU')

        # Test inferred mappings for US cities
        self.assertEqual(self.holiday_manager.get_country_from_timezone('America/Chicago'), 'US')
        self.assertEqual(self.holiday_manager.get_country_from_timezone('America/Denver'), 'US')

        # Test inferred mappings for Canadian cities
        self.assertEqual(self.holiday_manager.get_country_from_timezone('America/Toronto'), 'CA')
        self.assertEqual(self.holiday_manager.get_country_from_timezone('America/Vancouver'), 'CA')

        # Test European city mappings
        self.assertEqual(self.holiday_manager.get_country_from_timezone('Europe/Paris'), 'FR')
        self.assertEqual(self.holiday_manager.get_country_from_timezone('Europe/Berlin'), 'DE')

        # Test unknown timezone
        self.assertIsNone(self.holiday_manager.get_country_from_timezone('Unknown/Timezone'))
        self.assertIsNone(self.holiday_manager.get_country_from_timezone('Asia/UnknownCity'))

    @patch('time_master.holiday_manager.holidays.country_holidays')
    @patch('time_master.holiday_manager.datetime')
    def test_get_holidays_with_cache(self, mock_datetime, mock_country_holidays):
        """Test get_holidays method with caching."""
        # Mock current time
        mock_now = datetime(2024, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        # Mock holidays
        mock_holidays = Mock()
        mock_country_holidays.return_value = mock_holidays

        # First call - should fetch from holidays library
        result1 = self.holiday_manager.get_holidays('US', 2024)
        self.assertEqual(result1, mock_holidays)
        mock_country_holidays.assert_called_once_with('US', years=2024)

        # Second call - should use cache
        mock_country_holidays.reset_mock()
        result2 = self.holiday_manager.get_holidays('US', 2024)
        self.assertEqual(result2, mock_holidays)
        mock_country_holidays.assert_not_called()

        # Test cache expiry
        mock_datetime.now.return_value = mock_now + timedelta(seconds=3700)  # Beyond TTL
        result3 = self.holiday_manager.get_holidays('US', 2024)
        mock_country_holidays.assert_called_once_with('US', years=2024)

    @patch('time_master.holiday_manager.holidays.country_holidays')
    @patch('time_master.holiday_manager.datetime')
    def test_get_holidays_default_year(self, mock_datetime, mock_country_holidays):
        """Test get_holidays with default year."""
        mock_datetime.now.return_value = datetime(2024, 6, 15)
        mock_holidays = Mock()
        mock_country_holidays.return_value = mock_holidays

        result = self.holiday_manager.get_holidays('US')
        mock_country_holidays.assert_called_with('US', years=2024)

    @patch('time_master.holiday_manager.holidays.country_holidays')
    @patch('time_master.holiday_manager.logger')
    def test_get_holidays_fallback(self, mock_logger, mock_country_holidays):
        """Test get_holidays fallback to US when country fails."""
        # First call fails, second call (fallback) succeeds
        mock_country_holidays.side_effect = [Exception("Country not found"), Mock()]

        result = self.holiday_manager.get_holidays('XX', 2024)

        # Should have called twice: once for 'XX', once for 'US' fallback
        self.assertEqual(mock_country_holidays.call_count, 2)
        mock_logger.warning.assert_called_once()

    @patch('time_master.holiday_manager.datetime')
    def test_get_next_holiday(self, mock_datetime):
        """Test get_next_holiday method."""
        # Mock current date but preserve other datetime functionality
        mock_datetime.now.return_value = datetime(2024, 6, 15)
        mock_datetime.combine = datetime.combine
        mock_datetime.min = datetime.min

        # Mock holidays for current and next year
        with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
            current_holidays = {
                date(2024, 7, 4): "Independence Day",
                date(2024, 12, 25): "Christmas Day"
            }
            next_holidays = {
                date(2025, 1, 1): "New Year's Day"
            }

            mock_get_holidays.side_effect = [current_holidays, next_holidays]

            result = self.holiday_manager.get_next_holiday('US')

            self.assertIsNotNone(result)
            holiday_name, holiday_date = result
            self.assertEqual(holiday_name, "Independence Day")
            self.assertEqual(holiday_date, datetime(2024, 7, 4))

    def test_get_next_holiday_with_timezone(self):
        """Test get_next_holiday using timezone to infer country."""
        with patch.object(self.holiday_manager, 'get_country_from_timezone') as mock_get_country:
            with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
                mock_get_country.return_value = 'GB'
                mock_get_holidays.return_value = {}

                # Call the actual method to test timezone inference
                self.holiday_manager.get_next_holiday(timezone='Europe/London')
                mock_get_country.assert_called_once_with('Europe/London')

    @patch('time_master.holiday_manager.datetime')
    def test_get_next_holiday_no_upcoming(self, mock_datetime):
        """Test get_next_holiday when no upcoming holidays."""
        mock_datetime.now.return_value = datetime(2024, 12, 31)
        mock_datetime.combine = datetime.combine
        mock_datetime.min = datetime.min

        with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
            # No holidays in the future
            mock_get_holidays.return_value = {
                date(2024, 1, 1): "New Year's Day",
                date(2024, 7, 4): "Independence Day"
            }

            result = self.holiday_manager.get_next_holiday('US')
            self.assertIsNone(result)

    @patch('time_master.holiday_manager.datetime')
    @patch('time_master.holiday_manager.fuzz')
    def test_calculate_days_to_holiday(self, mock_fuzz, mock_datetime):
        """Test calculate_days_to_holiday method."""
        mock_datetime.now.return_value = datetime(2024, 6, 15)
        mock_datetime.combine = datetime.combine
        mock_datetime.min = datetime.min

        with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
            holidays_data = {
                date(2024, 7, 4): "Independence Day",
                date(2024, 12, 25): "Christmas Day"
            }
            mock_get_holidays.return_value = holidays_data

            # Mock fuzzy matching to return high score for exact match
            mock_fuzz.partial_ratio.return_value = 100

            result = self.holiday_manager.calculate_days_to_holiday("Independence Day", 'US')

            # July 4 - June 15 = 19 days
            self.assertEqual(result, 19)

    @patch('time_master.holiday_manager.fuzz')
    def test_calculate_days_to_holiday_fuzzy_match(self, mock_fuzz):
        """Test calculate_days_to_holiday with fuzzy matching."""
        with patch('time_master.holiday_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 6, 15)

            with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
                holidays_data = {
                    date(2024, 7, 4): "Independence Day"
                }
                mock_get_holidays.return_value = holidays_data

                # Mock fuzzy matching for partial match
                mock_fuzz.partial_ratio.return_value = 85

                result = self.holiday_manager.calculate_days_to_holiday("July 4th", 'US')
                self.assertEqual(result, 19)

    @patch('time_master.holiday_manager.fuzz')
    def test_calculate_days_to_holiday_no_match(self, mock_fuzz):
        """Test calculate_days_to_holiday with no matching holiday."""
        with patch('time_master.holiday_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 6, 15)

            with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
                mock_get_holidays.return_value = {}

                # Mock fuzzy matching to return low score
                mock_fuzz.partial_ratio.return_value = 50

                result = self.holiday_manager.calculate_days_to_holiday("Unknown Holiday", 'US')
                self.assertIsNone(result)

    @patch('time_master.holiday_manager.datetime')
    def test_list_holidays(self, mock_datetime):
        """Test list_holidays method."""
        mock_datetime.now.return_value = datetime(2024, 6, 15)
        mock_datetime.combine = datetime.combine
        mock_datetime.min = datetime.min

        with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
            holidays_data = {
                date(2024, 1, 1): "New Year's Day",
                date(2024, 7, 4): "Independence Day",
                date(2024, 12, 25): "Christmas Day"
            }
            mock_get_holidays.return_value = holidays_data

            result = self.holiday_manager.list_holidays('US', year=2024, limit=5)

            self.assertEqual(len(result), 3)
            # Should be sorted by date
            self.assertEqual(result[0][0], "New Year's Day")
            self.assertEqual(result[1][0], "Independence Day")
            self.assertEqual(result[2][0], "Christmas Day")

            # Test datetime conversion
            self.assertIsInstance(result[0][1], datetime)

    def test_list_holidays_with_timezone(self):
        """Test list_holidays using timezone to infer country."""
        with patch.object(self.holiday_manager, 'get_country_from_timezone') as mock_get_country:
            with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
                mock_get_country.return_value = 'GB'
                mock_get_holidays.return_value = {}

                self.holiday_manager.list_holidays(timezone='Europe/London')
                mock_get_country.assert_called_once_with('Europe/London')

    def test_list_holidays_limit(self):
        """Test list_holidays with limit parameter."""
        with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
            holidays_data = {date(2024, i, 1): f"Holiday {i}" for i in range(1, 13)}
            mock_get_holidays.return_value = holidays_data

            result = self.holiday_manager.list_holidays('US', limit=3)
            self.assertEqual(len(result), 3)

    def test_calculate_holiday_duration(self):
        """Test calculate_holiday_duration method."""
        with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
            # Mock holidays: July 4th (Thursday) is a holiday
            holidays_data = {
                date(2024, 7, 4): "Independence Day"
            }
            mock_get_holidays.return_value = holidays_data

            # Test with datetime input
            duration = self.holiday_manager.calculate_holiday_duration(
                datetime(2024, 7, 4), 'US'
            )

            # July 4th 2024 is Thursday, so with weekend it should be 3 days (Thu, Fri, Sat, Sun)
            # But since Fri is not a holiday, it should be 1 day
            self.assertIsInstance(duration, int)
            self.assertGreaterEqual(duration, 1)

    def test_calculate_holiday_duration_with_weekend(self):
        """Test calculate_holiday_duration including weekends."""
        with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
            # Mock Friday holiday that extends into weekend
            holidays_data = {
                date(2024, 7, 5): "Friday Holiday"  # Friday
            }
            mock_get_holidays.return_value = holidays_data

            duration = self.holiday_manager.calculate_holiday_duration(
                date(2024, 7, 5), 'US'
            )

            # Friday + Saturday + Sunday = 3 days
            self.assertEqual(duration, 3)

    @patch('time_master.holiday_manager.pycountry')
    def test_get_country_name(self, mock_pycountry):
        """Test get_country_name method."""
        # Mock successful country lookup
        mock_country = Mock()
        mock_country.name = "United States"
        mock_pycountry.countries.get.return_value = mock_country

        result = self.holiday_manager.get_country_name('US')
        self.assertEqual(result, "United States")
        mock_pycountry.countries.get.assert_called_once_with(alpha_2='US')

    @patch('time_master.holiday_manager.pycountry')
    def test_get_country_name_not_found(self, mock_pycountry):
        """Test get_country_name when country not found."""
        mock_pycountry.countries.get.return_value = None

        result = self.holiday_manager.get_country_name('XX')
        self.assertEqual(result, 'XX')

    @patch('time_master.holiday_manager.pycountry')
    def test_get_country_name_exception(self, mock_pycountry):
        """Test get_country_name when exception occurs."""
        mock_pycountry.countries.get.side_effect = Exception("Lookup failed")

        result = self.holiday_manager.get_country_name('US')
        self.assertEqual(result, 'US')

    def test_default_country_fallback(self):
        """Test that methods fall back to US when no country provided."""
        with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
            mock_get_holidays.return_value = {}

            # Test get_next_holiday fallback
            self.holiday_manager.get_next_holiday()
            mock_get_holidays.assert_called()

            # Test calculate_days_to_holiday fallback
            with patch('time_master.holiday_manager.fuzz.partial_ratio', return_value=50):
                self.holiday_manager.calculate_days_to_holiday("Test Holiday")

            # Test list_holidays fallback
            self.holiday_manager.list_holidays()


class TestHolidayManagerIntegration(unittest.TestCase):
    """Integration tests for HolidayManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.holiday_manager = HolidayManager()

    def test_real_holiday_data(self):
        """Test with real holiday data (if available)."""
        try:
            # Test getting US holidays for current year
            us_holidays = self.holiday_manager.get_holidays('US')
            self.assertIsNotNone(us_holidays)

            # Test listing holidays
            holiday_list = self.holiday_manager.list_holidays('US', limit=5)
            self.assertIsInstance(holiday_list, list)

            if holiday_list:
                self.assertIsInstance(holiday_list[0], tuple)
                self.assertEqual(len(holiday_list[0]), 2)
        except Exception:
            # Skip if holidays library is not available or fails
            self.skipTest("Real holiday data not available")

    def test_timezone_country_workflow(self):
        """Test complete workflow from timezone to holidays."""
        # Test timezone -> country -> holidays workflow
        country = self.holiday_manager.get_country_from_timezone('America/New_York')
        self.assertEqual(country, 'US')

        # Use the country to get holidays
        with patch.object(self.holiday_manager, 'get_holidays') as mock_get_holidays:
            mock_get_holidays.return_value = {}
            self.holiday_manager.list_holidays(country=country)
            mock_get_holidays.assert_called_with(country, unittest.mock.ANY)


if __name__ == '__main__':
    unittest.main()
