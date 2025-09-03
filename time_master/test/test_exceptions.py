"""TimeMaster异常测试模块

测试TimeMaster自定义异常类。
"""

import unittest

import pytest
from time_master.exceptions import (
    TimeMasterError,
    NetworkError,
    TimezoneError,
    APIError
)


class TestTimeMasterExceptions(unittest.TestCase):
    """TimeMaster异常测试类"""

    def test_timemaster_error_base_exception(self):
        """测试TimeMasterError基础异常"""
        error_message = "This is a test error"
        error = TimeMasterError(error_message)

        self.assertEqual(str(error), error_message)
        self.assertIsInstance(error, Exception)

    def test_network_error_inheritance(self):
        """测试NetworkError继承关系"""
        error_message = "Network connection failed"
        error = NetworkError(error_message)

        self.assertEqual(str(error), error_message)
        self.assertIsInstance(error, TimeMasterError)
        self.assertIsInstance(error, Exception)

    def test_timezone_error_inheritance(self):
        """测试TimezoneError继承关系"""
        error_message = "Invalid timezone specified"
        error = TimezoneError(error_message)

        self.assertEqual(str(error), error_message)
        self.assertIsInstance(error, TimeMasterError)
        self.assertIsInstance(error, Exception)

    def test_api_error_inheritance(self):
        """测试APIError继承关系"""
        error_message = "API request failed"
        error = APIError(error_message)

        self.assertEqual(str(error), error_message)
        self.assertIsInstance(error, TimeMasterError)
        self.assertIsInstance(error, Exception)

    def test_exception_with_no_message(self):
        """测试无消息的异常"""
        error = TimeMasterError()
        self.assertEqual(str(error), "")

    def test_exception_with_multiple_args(self):
        """测试多参数异常"""
        error = NetworkError("Connection failed", 404, "Not Found")
        self.assertIn("Connection failed", str(error))

    def test_exception_raising(self):
        """测试异常抛出"""
        with self.assertRaises(TimeMasterError):
            raise TimeMasterError("Test error")

        with self.assertRaises(NetworkError):
            raise NetworkError("Network error")

        with self.assertRaises(TimezoneError):
            raise TimezoneError("Timezone error")

        with self.assertRaises(APIError):
            raise APIError("API error")

    def test_exception_catching_hierarchy(self):
        """测试异常捕获层次结构"""
        # NetworkError应该能被TimeMasterError捕获
        try:
            raise NetworkError("Network issue")
        except TimeMasterError as e:
            self.assertIsInstance(e, NetworkError)

        # TimezoneError应该能被TimeMasterError捕获
        try:
            raise TimezoneError("Timezone issue")
        except TimeMasterError as e:
            self.assertIsInstance(e, TimezoneError)

        # APIError应该能被TimeMasterError捕获
        try:
            raise APIError("API issue")
        except TimeMasterError as e:
            self.assertIsInstance(e, APIError)


class TestExceptionUsageScenarios(unittest.TestCase):
    """异常使用场景测试类"""

    def test_network_error_scenarios(self):
        """测试网络错误场景"""
        scenarios = [
            "Connection timeout",
            "DNS resolution failed",
            "Host unreachable",
            "Connection refused"
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                error = NetworkError(scenario)
                self.assertEqual(str(error), scenario)
                self.assertIsInstance(error, NetworkError)

    def test_timezone_error_scenarios(self):
        """测试时区错误场景"""
        scenarios = [
            "Invalid timezone: 'Invalid/Timezone'",
            "Timezone not found",
            "Ambiguous timezone",
            "Timezone conversion failed"
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                error = TimezoneError(scenario)
                self.assertEqual(str(error), scenario)
                self.assertIsInstance(error, TimezoneError)

    def test_api_error_scenarios(self):
        """测试API错误场景"""
        scenarios = [
            "HTTP 404: Not Found",
            "HTTP 500: Internal Server Error",
            "Rate limit exceeded",
            "Invalid API response format"
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                error = APIError(scenario)
                self.assertEqual(str(error), scenario)
                self.assertIsInstance(error, APIError)


if __name__ == '__main__':
    unittest.main()
