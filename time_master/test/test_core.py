"""TimeMaster核心功能测试模块

测试TimeMaster类的所有核心功能，包括时间获取、时区转换、假期管理等。
"""

import datetime
import unittest
from unittest.mock import patch, Mock

import pytest
import pytz
from requests.exceptions import RequestException, Timeout
from time_master.config import TimeMasterConfig
from time_master.core import TimeMaster
from time_master.exceptions import TimeMasterError, NetworkError, TimezoneError


class TestTimeMasterInitialization(unittest.TestCase):
    """TimeMaster初始化测试类"""

    def test_default_initialization(self):
        """测试默认初始化"""
        tm = TimeMaster()

        self.assertIsNotNone(tm._config)
        self.assertEqual(tm.api_endpoint, tm._config.api_endpoint)
        self.assertEqual(tm.timeout, tm._config.timeout)
        self.assertEqual(tm.cache_ttl, tm._config.cache_ttl)
        self.assertIsInstance(tm._cache, dict)
        self.assertIsNotNone(tm._holiday_manager)

    def test_initialization_with_parameters(self):
        """测试带参数的初始化"""
        api_endpoint = "http://custom-api.com"
        timeout = 15
        cache_ttl = 7200

        tm = TimeMaster(
            api_endpoint=api_endpoint,
            timeout=timeout,
            cache_ttl=cache_ttl,
            auto_local_timezone=False
        )

        self.assertEqual(tm.api_endpoint, api_endpoint)
        self.assertEqual(tm.timeout, timeout)
        self.assertEqual(tm.cache_ttl, cache_ttl)
        self.assertFalse(tm._auto_local_timezone)

    def test_initialization_with_config(self):
        """测试使用配置对象初始化"""
        config = TimeMasterConfig()
        config.offline_mode = True
        config.auto_timezone = False

        tm = TimeMaster(config=config)

        self.assertEqual(tm._config, config)
        self.assertTrue(tm._force_offline)
        self.assertFalse(tm._auto_local_timezone)

    @patch('time_master.core.socket.create_connection')
    def test_network_connectivity_check_online(self, mock_socket):
        """测试网络连接检查 - 在线状态"""
        mock_socket.return_value = Mock()

        tm = TimeMaster()

        self.assertTrue(tm._is_online)
        mock_socket.assert_called_with(("8.8.8.8", 53), timeout=tm.timeout)

    @patch('time_master.core.socket.create_connection')
    def test_network_connectivity_check_offline(self, mock_socket):
        """测试网络连接检查 - 离线状态"""
        mock_socket.side_effect = OSError("Network unreachable")

        tm = TimeMaster()

        self.assertFalse(tm._is_online)

    def test_force_offline_mode(self):
        """测试强制离线模式"""
        config = TimeMasterConfig()
        config.offline_mode = True

        tm = TimeMaster(config=config)

        self.assertTrue(tm._force_offline)
        self.assertFalse(tm._is_online)


class TestTimeMasterTimeOperations(unittest.TestCase):
    """TimeMaster时间操作测试类"""

    def setUp(self):
        """测试前设置"""
        self.tm = TimeMaster(auto_local_timezone=False)

    @patch('time_master.core.requests.get')
    def test_get_online_time_success(self, mock_get):
        """测试在线获取时间成功"""
        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {
            'datetime': '2023-12-25T10:30:00.123456+00:00',
            'timezone': 'UTC'
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # 设置为在线模式
        self.tm._is_online = True
        self.tm._force_offline = False

        result = self.tm._get_online_time('UTC')

        self.assertIsInstance(result, datetime.datetime)
        self.assertEqual(result.tzinfo.zone, 'UTC')
        mock_get.assert_called_once()

    @patch('time_master.core.requests.get')
    def test_get_online_time_api_failure(self, mock_get):
        """测试在线获取时间API失败"""
        mock_get.side_effect = RequestException("API Error")

        self.tm._is_online = True
        self.tm._force_offline = False

        with self.assertRaises(RequestException):
            self.tm._get_online_time('UTC')

    def test_get_offline_time(self):
        """测试离线获取时间"""
        result = self.tm._get_offline_time('UTC')

        self.assertIsInstance(result, datetime.datetime)
        self.assertEqual(result.tzinfo.zone, 'UTC')

    def test_get_offline_time_invalid_timezone(self):
        """测试离线获取时间 - 无效时区"""
        # 应该回退到UTC
        result = self.tm._get_offline_time('Invalid/Timezone')

        self.assertIsInstance(result, datetime.datetime)
        self.assertEqual(result.tzinfo.zone, 'UTC')

    @patch.object(TimeMaster, '_get_offline_time')
    def test_get_time_current_default_timezone(self, mock_offline):
        """测试获取当前时间 - 默认时区"""
        mock_dt = datetime.datetime.now(pytz.UTC)
        mock_offline.return_value = mock_dt

        self.tm._is_online = False

        result = self.tm.get_time()

        mock_offline.assert_called_with('UTC')
        self.assertIn('T', result)  # ISO format

    @patch.object(TimeMaster, '_get_offline_time')
    def test_get_time_with_timezone(self, mock_offline):
        """测试获取指定时区的时间"""
        mock_dt = datetime.datetime.now(pytz.timezone('America/New_York'))
        mock_offline.return_value = mock_dt

        self.tm._is_online = False

        result = self.tm.get_time(timezone='America/New_York')

        mock_offline.assert_called_with('America/New_York')
        self.assertIsInstance(result, str)

    def test_get_time_conversion(self):
        """测试时间转换"""
        time_str = '2023-12-25T10:30:00'

        result = self.tm.get_time(
            timezone='America/New_York',
            time_str=time_str,
            from_tz='UTC'
        )

        self.assertIsInstance(result, str)
        self.assertIn('T', result)

    def test_get_time_conversion_missing_from_tz(self):
        """测试时间转换 - 缺少源时区"""
        with self.assertRaises(ValueError):
            self.tm.get_time(
                timezone='America/New_York',
                time_str='2023-12-25T10:30:00'
            )

    @patch.object(TimeMaster, 'get_time')
    def test_now_method(self, mock_get_time):
        """测试now方法"""
        mock_get_time.return_value = '2023-12-25T10:30:00+00:00'

        result = self.tm.now(timezone='UTC')

        mock_get_time.assert_called_with(timezone='UTC', format=TimeMaster.FORMAT_ISO)
        self.assertEqual(result, '2023-12-25T10:30:00+00:00')

    def test_format_time_iso(self):
        """测试ISO格式化"""
        dt = datetime.datetime(2023, 12, 25, 10, 30, 0, tzinfo=pytz.UTC)

        result = self.tm._format_time(dt, TimeMaster.FORMAT_ISO)

        self.assertIn('2023-12-25T10:30:00', result)

    def test_format_time_friendly_cn(self):
        """测试中文友好格式化"""
        dt = datetime.datetime(2023, 12, 25, 10, 30, 0, tzinfo=pytz.UTC)

        result = self.tm._format_time(dt, TimeMaster.FORMAT_FRIENDLY_CN)

        self.assertIn('2023年12月25日', result)
        self.assertIn('10:30:00', result)

    def test_format_time_default(self):
        """测试默认格式化"""
        dt = datetime.datetime(2023, 12, 25, 10, 30, 0, tzinfo=pytz.UTC)

        result = self.tm._format_time(dt, 'unknown_format')

        # 应该回退到ISO格式
        self.assertIn('2023-12-25T10:30:00', result)


class TestTimeMasterTimezoneOperations(unittest.TestCase):
    """TimeMaster时区操作测试类"""

    def setUp(self):
        """测试前设置"""
        self.tm = TimeMaster()

    def test_convert_aware_datetime(self):
        """测试转换时区感知的datetime"""
        dt = datetime.datetime(2023, 12, 25, 10, 30, 0, tzinfo=pytz.UTC)

        result = self.tm.convert(dt, 'America/New_York')

        self.assertIsInstance(result, datetime.datetime)
        self.assertEqual(result.tzinfo.zone, 'America/New_York')

    @patch('time_master.core.get_localzone')
    def test_convert_naive_datetime(self, mock_get_localzone):
        """测试转换朴素datetime"""
        mock_tz = Mock()
        mock_tz.localize.return_value = datetime.datetime(2023, 12, 25, 10, 30, 0, tzinfo=pytz.UTC)
        mock_get_localzone.return_value = mock_tz

        dt = datetime.datetime(2023, 12, 25, 10, 30, 0)  # naive datetime

        result = self.tm.convert(dt, 'America/New_York')

        self.assertIsInstance(result, datetime.datetime)
        mock_tz.localize.assert_called_once_with(dt)

    def test_convert_invalid_timezone(self):
        """测试转换到无效时区"""
        dt = datetime.datetime(2023, 12, 25, 10, 30, 0, tzinfo=pytz.UTC)

        with self.assertRaises(ValueError):
            self.tm.convert(dt, 'Invalid/Timezone')

    @patch.object(TimeMaster, '_get_offline_time')
    def test_difference_offline_mode(self, mock_offline):
        """测试时区差异计算 - 离线模式"""
        dt1 = datetime.datetime(2023, 12, 25, 10, 0, 0, tzinfo=pytz.UTC)
        dt2 = datetime.datetime(2023, 12, 25, 15, 0, 0, tzinfo=pytz.timezone('America/New_York'))

        mock_offline.side_effect = [dt1, dt2]
        self.tm._is_online = False

        result = self.tm.difference('UTC', 'America/New_York')

        self.assertIsInstance(result, datetime.timedelta)

    def test_difference_invalid_timezone(self):
        """测试时区差异计算 - 无效时区"""
        with self.assertRaises(ValueError):
            self.tm.difference('UTC', 'Invalid/Timezone')

        with self.assertRaises(ValueError):
            self.tm.difference('Invalid/Timezone', 'UTC')

    def test_find_timezones_empty_query(self):
        """测试查找时区 - 空查询"""
        result = self.tm.find_timezones('', limit=5)

        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 5)
        self.assertTrue(all(isinstance(tz, str) for tz in result))

    def test_find_timezones_with_query(self):
        """测试查找时区 - 带查询"""
        result = self.tm.find_timezones('America', limit=10)

        self.assertIsInstance(result, list)
        self.assertLessEqual(len(result), 10)
        self.assertTrue(all('america' in tz.lower() for tz in result))

    def test_find_timezones_underscore_replacement(self):
        """测试查找时区 - 下划线替换"""
        result = self.tm.find_timezones('New York', limit=5)

        self.assertIsInstance(result, list)
        # 应该找到包含New_York的时区
        matching = [tz for tz in result if 'new_york' in tz.lower()]
        self.assertGreater(len(matching), 0)

    def test_list_timezones_all(self):
        """测试列出所有时区"""
        result = self.tm.list_timezones()

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertTrue(all(isinstance(tz, str) for tz in result))
        # 应该是排序的
        self.assertEqual(result, sorted(result))

    def test_list_timezones_with_region(self):
        """测试列出指定地区的时区"""
        result = self.tm.list_timezones('Europe')

        self.assertIsInstance(result, list)
        self.assertTrue(all(tz.startswith('Europe') for tz in result))
        self.assertEqual(result, sorted(result))

    @patch('time_master.core.requests.get')
    @patch('tzlocal.get_localzone')
    def test_auto_detect_local_timezone_network(self, mock_tzlocal, mock_get):
        """测试自动检测本地时区 - 网络方式"""
        # 模拟网络API响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'timezone': 'America/New_York'}
        mock_get.return_value = mock_response

        self.tm._is_online = True
        self.tm._force_offline = False

        result = self.tm._auto_detect_local_timezone()

        self.assertEqual(result, 'America/New_York')
        mock_get.assert_called_once()
        mock_tzlocal.assert_not_called()

    @patch('time_master.core.requests.get')
    @patch('tzlocal.get_localzone')
    def test_auto_detect_local_timezone_fallback(self, mock_tzlocal, mock_get):
        """测试自动检测本地时区 - 系统回退"""
        # 模拟网络失败
        mock_get.side_effect = RequestException("Network error")

        # 模拟系统时区
        mock_tz = Mock()
        mock_tz.__str__ = Mock(return_value='Europe/London')
        mock_tzlocal.return_value = mock_tz

        self.tm._is_online = True
        self.tm._force_offline = False

        result = self.tm._auto_detect_local_timezone()

        self.assertEqual(result, 'Europe/London')
        mock_tzlocal.assert_called_once()

    @patch('tzlocal.get_localzone')
    def test_get_local_timezone_with_detected(self, mock_tzlocal):
        """测试获取本地时区 - 已检测"""
        self.tm._detected_local_timezone = 'Asia/Shanghai'

        result = self.tm.get_local_timezone()

        self.assertEqual(result, 'Asia/Shanghai')
        mock_tzlocal.assert_not_called()

    @patch('tzlocal.get_localzone')
    def test_get_local_timezone_system_fallback(self, mock_tzlocal):
        """测试获取本地时区 - 系统回退"""
        self.tm._detected_local_timezone = None

        mock_tz = Mock()
        mock_tz.__str__ = Mock(return_value='Australia/Sydney')
        mock_tzlocal.return_value = mock_tz

        result = self.tm.get_local_timezone()

        self.assertEqual(result, 'Australia/Sydney')
        mock_tzlocal.assert_called_once()


class TestTimeMasterHolidayOperations(unittest.TestCase):
    """TimeMaster假期操作测试类"""

    def setUp(self):
        """测试前设置"""
        self.tm = TimeMaster()

    @patch('time_master.core.holidays.country_holidays')
    @patch.object(TimeMaster, 'get_country_from_timezone')
    def test_get_next_holiday_success(self, mock_get_country, mock_holidays):
        """测试获取下一个假期成功"""
        mock_get_country.return_value = 'US'

        # 模拟假期数据
        future_date = datetime.date.today() + datetime.timedelta(days=30)
        mock_holidays_data = {future_date: 'Test Holiday'}
        mock_holidays.return_value = mock_holidays_data

        # 模拟假期管理器
        with patch.object(self.tm._holiday_manager, 'calculate_holiday_duration', return_value=1):
            result = self.tm.get_next_holiday(country='US')

            self.assertIsNotNone(result)
            self.assertEqual(result['name'], 'Test Holiday')
            self.assertEqual(result['country'], 'US')
            self.assertIn('days_until', result)
            self.assertIn('holiday_duration', result)

    @patch('time_master.core.holidays.country_holidays')
    def test_get_next_holiday_no_upcoming(self, mock_holidays):
        """测试获取下一个假期 - 无即将到来的假期"""
        # 模拟过去的假期
        past_date = datetime.date.today() - datetime.timedelta(days=30)
        mock_holidays_data = {past_date: 'Past Holiday'}
        mock_holidays.return_value = mock_holidays_data

        result = self.tm.get_next_holiday(country='US')

        self.assertIsNone(result)

    @patch.object(TimeMaster, 'get_local_timezone')
    def test_get_next_holiday_default_timezone(self, mock_get_local):
        """测试获取下一个假期 - 默认时区"""
        mock_get_local.return_value = 'America/New_York'

        with patch.object(self.tm, 'get_country_from_timezone') as mock_get_country:
            mock_get_country.return_value = 'US'

            with patch('time_master.core.holidays.country_holidays') as mock_holidays:
                mock_holidays.return_value = {}

                result = self.tm.get_next_holiday()

                mock_get_local.assert_called_once()
                mock_get_country.assert_called_with('America/New_York')

    def test_calculate_days_to_holiday(self):
        """测试计算到假期的天数"""
        with patch.object(self.tm._holiday_manager, 'calculate_days_to_holiday', return_value=15) as mock_method:
            result = self.tm.calculate_days_to_holiday('Christmas', country='US')

            self.assertEqual(result, 15)
            mock_method.assert_called_with(
                'Christmas', country='US', timezone=None
            )

    @patch('time_master.core.holidays.country_holidays')
    @patch.object(TimeMaster, 'get_country_from_timezone')
    def test_list_holidays(self, mock_get_country, mock_holidays):
        """测试列出假期"""
        mock_get_country.return_value = 'US'

        # 模拟假期数据
        test_date = datetime.date(2023, 12, 25)
        mock_holidays_data = {test_date: 'Christmas'}
        mock_holidays.return_value = mock_holidays_data

        # 模拟假期管理器
        with patch.object(self.tm._holiday_manager, 'calculate_holiday_duration', return_value=1):
            result = self.tm.list_holidays(country='US', year=2023)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['name'], 'Christmas')
            self.assertEqual(result[0]['date'], '2023-12-25')
            self.assertEqual(result[0]['country'], 'US')
            self.assertEqual(result[0]['year'], 2023)

    @patch.object(TimeMaster, 'get_next_holiday')
    def test_search_holiday_empty_query(self, mock_get_next):
        """测试搜索假期 - 空查询"""
        mock_next_holiday = {
            'name': 'Next Holiday',
            'date': '2023-12-25',
            'days_until': 30
        }
        mock_get_next.return_value = mock_next_holiday

        result = self.tm.search_holiday('', country='US')

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], mock_next_holiday)

    @patch.object(TimeMaster, 'list_holidays')
    def test_search_holiday_with_query(self, mock_list_holidays):
        """测试搜索假期 - 带查询"""
        mock_holidays = [
            {'name': 'Christmas Day', 'date': '2023-12-25', 'country': 'US', 'year': 2023},
            {'name': 'New Year Day', 'date': '2023-01-01', 'country': 'US', 'year': 2023}
        ]
        mock_list_holidays.return_value = mock_holidays

        # 模拟假期管理器
        with patch.object(self.tm._holiday_manager, 'calculate_holiday_duration', return_value=1):
            result = self.tm.search_holiday('Christmas', country='US', year=2023)

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]['name'], 'Christmas Day')
            self.assertIn('days_until', result[0])
            self.assertIn('holiday_duration', result[0])

    def test_get_country_from_timezone(self):
        """测试从时区获取国家代码"""
        with patch.object(self.tm._holiday_manager, 'get_country_from_timezone', return_value='US') as mock_method:
            result = self.tm.get_country_from_timezone('America/New_York')

            self.assertEqual(result, 'US')
            mock_method.assert_called_with('America/New_York')


class TestTimeMasterCaching(unittest.TestCase):
    """TimeMaster缓存测试类"""

    def setUp(self):
        """测试前设置"""
        self.tm = TimeMaster(cache_ttl=3600)

    @patch('time_master.core.requests.get')
    @patch('time_master.core.time.time')
    def test_cache_hit(self, mock_time, mock_get):
        """测试缓存命中"""
        # 设置时间
        mock_time.return_value = 1000

        # 预填充缓存
        cached_dt = datetime.datetime.now(pytz.UTC)
        self.tm._cache['UTC'] = (1000, cached_dt)

        self.tm._is_online = True
        self.tm._force_offline = False

        result = self.tm._get_online_time('UTC')

        self.assertEqual(result, cached_dt)
        mock_get.assert_not_called()

    @patch('time_master.core.requests.get')
    @patch('time_master.core.time.time')
    def test_cache_miss_expired(self, mock_time, mock_get):
        """测试缓存过期"""
        # 设置时间
        mock_time.return_value = 5000  # 缓存已过期

        # 预填充过期缓存
        cached_dt = datetime.datetime.now(pytz.UTC)
        self.tm._cache['UTC'] = (1000, cached_dt)  # 4000秒前的缓存

        # 模拟API响应
        mock_response = Mock()
        mock_response.json.return_value = {
            'datetime': '2023-12-25T10:30:00.123456+00:00'
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        self.tm._is_online = True
        self.tm._force_offline = False

        result = self.tm._get_online_time('UTC')

        self.assertNotEqual(result, cached_dt)
        mock_get.assert_called_once()


class TestTimeMasterErrorHandling(unittest.TestCase):
    """TimeMaster错误处理测试类"""

    def setUp(self):
        """测试前设置"""
        self.tm = TimeMaster()

    @patch('time_master.core.requests.get')
    def test_network_degradation(self, mock_get):
        """测试网络降级"""
        # 第一次调用失败，触发降级
        mock_get.side_effect = RequestException("Network error")

        self.tm._is_online = True
        self.tm._force_offline = False

        # 应该自动降级到离线模式
        result = self.tm.get_time('UTC')

        self.assertIsInstance(result, str)
        self.assertFalse(self.tm._is_online)  # 应该被设置为离线

    @patch('time_master.core.holidays.country_holidays')
    def test_holiday_error_handling(self, mock_holidays):
        """测试假期错误处理"""
        mock_holidays.side_effect = Exception("Holiday API error")

        result = self.tm.get_next_holiday(country='US')

        self.assertIsNone(result)

    @patch('time_master.core.holidays.country_holidays')
    def test_list_holidays_error_handling(self, mock_holidays):
        """测试列出假期错误处理"""
        mock_holidays.side_effect = Exception("Holiday API error")

        result = self.tm.list_holidays(country='US')

        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
