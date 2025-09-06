"""TimeMaster配置测试模块

测试TimeMaster配置类和环境变量处理。
"""

import os
import unittest
from unittest.mock import patch

import pytest
from time_master.config import TimeMasterConfig


class TestTimeMasterConfig(unittest.TestCase):
    """TimeMaster配置测试类"""

    def setUp(self):
        """测试前设置"""
        # 保存原始环境变量
        self.original_env = {}
        for env_var in TimeMasterConfig.ENV_MAPPING.keys():
            self.original_env[env_var] = os.getenv(env_var)

    def tearDown(self):
        """测试后清理"""
        # 恢复原始环境变量
        for env_var, original_value in self.original_env.items():
            if original_value is None:
                os.environ.pop(env_var, None)
            else:
                os.environ[env_var] = original_value

    def test_default_configuration(self):
        """测试默认配置"""
        config = TimeMasterConfig()

        # 测试默认值
        self.assertEqual(config.api_endpoint, TimeMasterConfig.DEFAULT_API_ENDPOINT)
        self.assertEqual(config.timeout, TimeMasterConfig.DEFAULT_TIMEOUT)
        self.assertEqual(config.cache_ttl, TimeMasterConfig.DEFAULT_CACHE_TTL)
        self.assertEqual(config.log_level, TimeMasterConfig.DEFAULT_LOG_LEVEL)
        self.assertEqual(config.offline_mode, TimeMasterConfig.DEFAULT_OFFLINE_MODE)
        self.assertEqual(config.auto_timezone, TimeMasterConfig.DEFAULT_AUTO_TIMEZONE)
        self.assertEqual(config.default_timezone, TimeMasterConfig.DEFAULT_TIMEZONE)
        self.assertEqual(config.timezone_cache_ttl, TimeMasterConfig.DEFAULT_TIMEZONE_CACHE_TTL)
        self.assertEqual(config.holiday_cache_ttl, TimeMasterConfig.DEFAULT_HOLIDAY_CACHE_TTL)
        self.assertEqual(config.network_timeout, TimeMasterConfig.DEFAULT_NETWORK_TIMEOUT)
        self.assertEqual(config.cache_size, TimeMasterConfig.DEFAULT_CACHE_SIZE)
        self.assertEqual(config.file_cache_enabled, TimeMasterConfig.DEFAULT_FILE_CACHE_ENABLED)

    def test_environment_variable_loading_boolean(self):
        """测试布尔类型环境变量加载"""
        # 测试 offline_mode
        test_cases = [
            ('true', True),
            ('True', True),
            ('1', True),
            ('yes', True),
            ('on', True),
            ('false', False),
            ('False', False),
            ('0', False),
            ('no', False),
            ('off', False)
        ]

        for env_value, expected in test_cases:
            with self.subTest(env_value=env_value, expected=expected):
                os.environ['TIMEMASTER_OFFLINE_MODE'] = env_value
                config = TimeMasterConfig()
                self.assertEqual(config.offline_mode, expected)

    def test_environment_variable_loading_integer(self):
        """测试整数类型环境变量加载"""
        os.environ['TIMEMASTER_TIMEZONE_CACHE_TTL'] = '3600'
        os.environ['TIMEMASTER_HOLIDAY_CACHE_TTL'] = '7200'
        os.environ['TIMEMASTER_NETWORK_TIMEOUT'] = '10'
        os.environ['TIMEMASTER_CACHE_SIZE'] = '5000'

        config = TimeMasterConfig()

        self.assertEqual(config.timezone_cache_ttl, 3600)
        self.assertEqual(config.holiday_cache_ttl, 7200)
        self.assertEqual(config.network_timeout, 10)
        self.assertEqual(config.cache_size, 5000)

    def test_environment_variable_loading_string(self):
        """测试字符串类型环境变量加载"""
        os.environ['TIMEMASTER_DEFAULT_TIMEZONE'] = 'Asia/Shanghai'
        os.environ['TIMEMASTER_LOG_LEVEL'] = 'DEBUG'

        config = TimeMasterConfig()

        self.assertEqual(config.default_timezone, 'Asia/Shanghai')
        self.assertEqual(config.log_level, 'DEBUG')

    def test_environment_variable_loading_list(self):
        """测试列表类型环境变量加载"""
        os.environ['TIMEMASTER_API_ENDPOINTS'] = 'http://api1.com, http://api2.com, http://api3.com'

        config = TimeMasterConfig()

        expected_endpoints = ['http://api1.com', 'http://api2.com', 'http://api3.com']
        self.assertEqual(config.api_endpoints, expected_endpoints)

    def test_invalid_environment_variables(self):
        """测试无效环境变量处理"""
        # 测试无效整数值
        os.environ['TIMEMASTER_TIMEZONE_CACHE_TTL'] = 'invalid_number'

        with patch('builtins.print') as mock_print:
            config = TimeMasterConfig()
            # 应该使用默认值
            self.assertEqual(config.timezone_cache_ttl, TimeMasterConfig.DEFAULT_TIMEZONE_CACHE_TTL)
            # 应该打印警告
            mock_print.assert_called()

    def test_update_method(self):
        """测试配置更新方法"""
        config = TimeMasterConfig()

        # 更新配置
        config.update(
            offline_mode=True,
            default_timezone='Europe/London',
            cache_size=20000
        )

        self.assertTrue(config.offline_mode)
        self.assertEqual(config.default_timezone, 'Europe/London')
        self.assertEqual(config.cache_size, 20000)

    def test_update_method_invalid_attribute(self):
        """测试更新不存在的属性"""
        config = TimeMasterConfig()

        # 尝试更新不存在的属性（应该被忽略）
        config.update(non_existent_attribute='value')

        # 不应该添加新属性
        self.assertFalse(hasattr(config, 'non_existent_attribute'))

    def test_is_offline_mode(self):
        """测试离线模式检查"""
        config = TimeMasterConfig()

        # 默认应该是在线模式
        self.assertFalse(config.is_offline_mode())

        # 设置为离线模式
        config.offline_mode = True
        self.assertTrue(config.is_offline_mode())

    def test_should_auto_detect_timezone(self):
        """测试自动时区检测设置"""
        config = TimeMasterConfig()

        # 默认应该启用自动检测
        self.assertTrue(config.should_auto_detect_timezone())

        # 禁用自动检测
        config.auto_timezone = False
        self.assertFalse(config.should_auto_detect_timezone())

    def test_get_timezone_cache_ttl(self):
        """测试时区缓存TTL获取"""
        config = TimeMasterConfig()

        self.assertEqual(config.get_timezone_cache_ttl(), TimeMasterConfig.DEFAULT_TIMEZONE_CACHE_TTL)

        # 更新TTL
        config.timezone_cache_ttl = 7200
        self.assertEqual(config.get_timezone_cache_ttl(), 7200)

    def test_get_holiday_cache_ttl(self):
        """测试假期缓存TTL获取"""
        config = TimeMasterConfig()

        self.assertEqual(config.get_holiday_cache_ttl(), TimeMasterConfig.DEFAULT_HOLIDAY_CACHE_TTL)

        # 更新TTL
        config.holiday_cache_ttl = 3600
        self.assertEqual(config.get_holiday_cache_ttl(), 3600)

    def test_runtime_state_attributes(self):
        """测试运行时状态属性"""
        config = TimeMasterConfig()

        # 检查运行时状态属性的初始值
        self.assertIsNone(config.detected_timezone)
        self.assertTrue(config.network_available)
        self.assertIsNone(config.last_network_check)

        # 更新运行时状态
        config.detected_timezone = 'America/New_York'
        config.network_available = False

        self.assertEqual(config.detected_timezone, 'America/New_York')
        self.assertFalse(config.network_available)


class TestTimeMasterConfigIntegration(unittest.TestCase):
    """TimeMaster配置集成测试类"""

    def test_full_environment_configuration(self):
        """测试完整环境变量配置"""
        # 设置所有环境变量
        env_vars = {
            'TIMEMASTER_OFFLINE_MODE': 'true',
            'TIMEMASTER_AUTO_TIMEZONE': 'false',
            'TIMEMASTER_DEFAULT_TIMEZONE': 'Asia/Tokyo',
            'TIMEMASTER_TIMEZONE_CACHE_TTL': '1800',
            'TIMEMASTER_HOLIDAY_CACHE_TTL': '3600',
            'TIMEMASTER_NETWORK_TIMEOUT': '15',
            'TIMEMASTER_LOG_LEVEL': 'WARNING',
            'TIMEMASTER_CACHE_SIZE': '15000',
            'TIMEMASTER_FILE_CACHE_ENABLED': 'true',
            'TIMEMASTER_API_ENDPOINTS': 'http://api1.test, http://api2.test'
        }

        # 保存原始环境变量
        original_env = {}
        for key in env_vars.keys():
            original_env[key] = os.getenv(key)

        try:
            # 设置测试环境变量
            for key, value in env_vars.items():
                os.environ[key] = value

            # 创建配置实例
            config = TimeMasterConfig()

            # 验证所有配置都正确加载
            self.assertTrue(config.offline_mode)
            self.assertFalse(config.auto_timezone)
            self.assertEqual(config.default_timezone, 'Asia/Tokyo')
            self.assertEqual(config.timezone_cache_ttl, 1800)
            self.assertEqual(config.holiday_cache_ttl, 3600)
            self.assertEqual(config.network_timeout, 15)
            self.assertEqual(config.log_level, 'WARNING')
            self.assertEqual(config.cache_size, 15000)
            self.assertTrue(config.file_cache_enabled)
            self.assertEqual(config.api_endpoints, ['http://api1.test', 'http://api2.test'])

        finally:
            # 恢复原始环境变量
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value


if __name__ == '__main__':
    unittest.main()
