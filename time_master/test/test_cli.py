"""TimeMaster CLI功能测试模块

测试命令行界面的所有功能，包括参数解析、命令执行和错误处理。
"""

import datetime
import io
import sys
import unittest
from unittest.mock import patch, Mock

import pytest
from time_master.cli import main
from time_master.core import TimeMaster


class TestCLIArgumentParsing(unittest.TestCase):
    """CLI参数解析测试类"""

    def setUp(self):
        """测试前设置"""
        # 保存原始的sys.argv
        self.original_argv = sys.argv.copy()

    def tearDown(self):
        """测试后清理"""
        # 恢复原始的sys.argv
        sys.argv = self.original_argv

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_timezone_argument(self, mock_stdout, mock_timemaster_class):
        """测试时区参数"""
        mock_tm = Mock()
        mock_tm.now.return_value = '2023-12-25T10:30:00+08:00'
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--timezone', 'Asia/Shanghai']

        main()

        mock_tm.now.assert_called_once_with('Asia/Shanghai', format=None)
        output = mock_stdout.getvalue().strip()
        self.assertEqual(output, '2023-12-25T10:30:00+08:00')

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_timezone_with_iso_format(self, mock_stdout, mock_timemaster_class):
        """测试时区参数与ISO格式"""
        mock_tm = Mock()
        mock_tm.now.return_value = '2023-12-25T10:30:00+08:00'
        mock_timemaster_class.return_value = mock_tm
        mock_timemaster_class.FORMAT_ISO = 'iso'

        sys.argv = ['cli.py', '--timezone', 'Asia/Shanghai', '--format', 'iso']

        main()

        mock_tm.now.assert_called_once_with('Asia/Shanghai', format='iso')
        output = mock_stdout.getvalue().strip()
        self.assertEqual(output, '2023-12-25T10:30:00+08:00')

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_timezone_with_friendly_format(self, mock_stdout, mock_timemaster_class):
        """测试时区参数与友好格式"""
        mock_tm = Mock()
        mock_tm.now.return_value = '2023年12月25日 10:30:00 (Asia/Shanghai)'
        mock_timemaster_class.return_value = mock_tm
        mock_timemaster_class.FORMAT_FRIENDLY_CN = 'friendly_cn'

        sys.argv = ['cli.py', '-tz', 'Asia/Shanghai', '-f', 'friendly']

        main()

        mock_tm.now.assert_called_once_with('Asia/Shanghai', format='friendly_cn')
        output = mock_stdout.getvalue().strip()
        self.assertEqual(output, '2023年12月25日 10:30:00 (Asia/Shanghai)')

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_search_timezones(self, mock_stdout, mock_timemaster_class):
        """测试搜索时区"""
        mock_tm = Mock()
        mock_tm.find_timezones.return_value = ['America/New_York', 'America/Chicago', 'America/Los_Angeles']
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--search', 'America']

        main()

        mock_tm.find_timezones.assert_called_once_with('America')
        output = mock_stdout.getvalue()
        self.assertIn("Timezones matching 'America':", output)
        self.assertIn('America/New_York', output)
        self.assertIn('America/Chicago', output)
        self.assertIn('America/Los_Angeles', output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_search_timezones_short_option(self, mock_stdout, mock_timemaster_class):
        """测试搜索时区短选项"""
        mock_tm = Mock()
        mock_tm.find_timezones.return_value = ['Europe/London', 'Europe/Paris']
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '-s', 'Europe']

        main()

        mock_tm.find_timezones.assert_called_once_with('Europe')
        output = mock_stdout.getvalue()
        self.assertIn("Timezones matching 'Europe':", output)
        self.assertIn('Europe/London', output)
        self.assertIn('Europe/Paris', output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_list_all_timezones(self, mock_stdout, mock_timemaster_class):
        """测试列出所有时区"""
        mock_tm = Mock()
        # 模拟大量时区数据
        mock_timezones = [f'Zone_{i}' for i in range(25)]
        mock_tm.list_timezones.return_value = mock_timezones
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--list']

        main()

        mock_tm.list_timezones.assert_called_once_with()
        output = mock_stdout.getvalue()
        self.assertIn('All timezones:', output)
        # 应该只显示前20个
        self.assertIn('Zone_0', output)
        self.assertIn('Zone_19', output)
        self.assertIn('... and 5 more', output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_list_timezones_by_region(self, mock_stdout, mock_timemaster_class):
        """测试按地区列出时区"""
        mock_tm = Mock()
        mock_tm.list_timezones.return_value = ['Asia/Shanghai', 'Asia/Tokyo', 'Asia/Seoul']
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--list', 'Asia']

        main()

        mock_tm.list_timezones.assert_called_once_with(region='Asia')
        output = mock_stdout.getvalue()
        self.assertIn("Timezones in region 'Asia':", output)
        self.assertIn('Asia/Shanghai', output)
        self.assertIn('Asia/Tokyo', output)
        self.assertIn('Asia/Seoul', output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_list_timezones_short_option(self, mock_stdout, mock_timemaster_class):
        """测试列出时区短选项"""
        mock_tm = Mock()
        mock_tm.list_timezones.return_value = ['Europe/London', 'Europe/Paris']
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '-l', 'Europe']

        main()

        mock_tm.list_timezones.assert_called_once_with(region='Europe')
        output = mock_stdout.getvalue()
        self.assertIn("Timezones in region 'Europe':", output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    @patch('datetime.datetime')
    def test_convert_datetime(self, mock_datetime, mock_stdout, mock_timemaster_class):
        """测试时间转换"""
        mock_tm = Mock()
        mock_now = Mock()
        mock_datetime.now.return_value = mock_now

        converted_dt = datetime.datetime(2023, 12, 25, 15, 30, 0)
        mock_tm.convert.return_value = converted_dt
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--convert', '2023-12-25T10:30:00', 'America/New_York']

        main()

        mock_tm.convert.assert_called_once_with(mock_now, 'America/New_York')
        output = mock_stdout.getvalue()
        self.assertIn('Converting 2023-12-25T10:30:00 to America/New_York', output)
        self.assertIn('Result:', output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_convert_datetime_short_option(self, mock_stdout, mock_timemaster_class):
        """测试时间转换短选项"""
        mock_tm = Mock()
        mock_tm.convert.return_value = datetime.datetime(2023, 12, 25, 15, 30, 0)
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '-c', '2023-12-25T10:30:00', 'Europe/London']

        main()

        output = mock_stdout.getvalue()
        self.assertIn('Converting 2023-12-25T10:30:00 to Europe/London', output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_time_difference(self, mock_stdout, mock_timemaster_class):
        """测试时区差异计算"""
        mock_tm = Mock()
        mock_tm.difference.return_value = datetime.timedelta(hours=13)
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--difference', 'UTC', 'Asia/Shanghai']

        main()

        mock_tm.difference.assert_called_once_with('UTC', 'Asia/Shanghai')
        output = mock_stdout.getvalue()
        self.assertIn('Time difference between UTC and Asia/Shanghai:', output)
        self.assertIn('13:00:00', output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_time_difference_short_option(self, mock_stdout, mock_timemaster_class):
        """测试时区差异计算短选项"""
        mock_tm = Mock()
        mock_tm.difference.return_value = datetime.timedelta(hours=-5)
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '-d', 'America/New_York', 'UTC']

        main()

        mock_tm.difference.assert_called_once_with('America/New_York', 'UTC')
        output = mock_stdout.getvalue()
        self.assertIn('Time difference between America/New_York and UTC:', output)

    @patch('time_master.cli.TimeMaster')
    def test_offline_mode(self, mock_timemaster_class):
        """测试离线模式"""
        mock_tm = Mock()
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--offline', '--timezone', 'UTC']

        main()

        mock_tm.force_offline.assert_called_once_with(True)

    @patch('time_master.cli.argparse.ArgumentParser.print_help')
    def test_no_arguments_shows_help(self, mock_print_help):
        """测试无参数时显示帮助"""
        sys.argv = ['cli.py']

        main()

        mock_print_help.assert_called_once()


class TestCLIErrorHandling(unittest.TestCase):
    """CLI错误处理测试类"""

    def setUp(self):
        """测试前设置"""
        self.original_argv = sys.argv.copy()

    def tearDown(self):
        """测试后清理"""
        sys.argv = self.original_argv

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_exception_handling(self, mock_stderr, mock_timemaster_class):
        """测试异常处理"""
        mock_tm = Mock()
        mock_tm.now.side_effect = Exception("Test error")
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--timezone', 'Invalid/Timezone']

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn('Error: Test error', error_output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_search_exception_handling(self, mock_stderr, mock_timemaster_class):
        """测试搜索异常处理"""
        mock_tm = Mock()
        mock_tm.find_timezones.side_effect = ValueError("Invalid search query")
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--search', 'invalid']

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn('Error: Invalid search query', error_output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_list_exception_handling(self, mock_stderr, mock_timemaster_class):
        """测试列表异常处理"""
        mock_tm = Mock()
        mock_tm.list_timezones.side_effect = RuntimeError("Failed to list timezones")
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--list', 'invalid_region']

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn('Error: Failed to list timezones', error_output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_convert_exception_handling(self, mock_stderr, mock_timemaster_class):
        """测试转换异常处理"""
        mock_tm = Mock()
        mock_tm.convert.side_effect = ValueError("Invalid timezone")
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--convert', '2023-12-25T10:30:00', 'Invalid/Timezone']

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn('Error: Invalid timezone', error_output)

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stderr', new_callable=io.StringIO)
    def test_difference_exception_handling(self, mock_stderr, mock_timemaster_class):
        """测试差异计算异常处理"""
        mock_tm = Mock()
        mock_tm.difference.side_effect = ValueError("Invalid timezone comparison")
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--difference', 'Invalid/TZ1', 'Invalid/TZ2']

        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 1)
        error_output = mock_stderr.getvalue()
        self.assertIn('Error: Invalid timezone comparison', error_output)


class TestCLIIntegration(unittest.TestCase):
    """CLI集成测试类"""

    def setUp(self):
        """测试前设置"""
        self.original_argv = sys.argv.copy()

    def tearDown(self):
        """测试后清理"""
        sys.argv = self.original_argv

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_multiple_operations_workflow(self, mock_stdout, mock_timemaster_class):
        """测试多操作工作流"""
        mock_tm = Mock()
        mock_timemaster_class.return_value = mock_tm

        # 测试搜索 -> 选择时区 -> 获取时间的工作流
        test_cases = [
            (['cli.py', '--search', 'Asia'], 'find_timezones', ['Asia/Shanghai', 'Asia/Tokyo']),
            (['cli.py', '--timezone', 'Asia/Shanghai'], 'now', '2023-12-25T10:30:00+08:00'),
            (['cli.py', '--list', 'Europe'], 'list_timezones', ['Europe/London', 'Europe/Paris'])
        ]

        for argv, method_name, return_value in test_cases:
            with self.subTest(argv=argv):
                sys.argv = argv
                mock_tm.reset_mock()

                if method_name == 'find_timezones':
                    mock_tm.find_timezones.return_value = return_value
                elif method_name == 'now':
                    mock_tm.now.return_value = return_value
                elif method_name == 'list_timezones':
                    mock_tm.list_timezones.return_value = return_value

                main()

                if method_name == 'find_timezones':
                    mock_tm.find_timezones.assert_called_once()
                elif method_name == 'now':
                    mock_tm.now.assert_called_once()
                elif method_name == 'list_timezones':
                    mock_tm.list_timezones.assert_called_once()

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_complex_command_combinations(self, mock_stdout, mock_timemaster_class):
        """测试复杂命令组合"""
        mock_tm = Mock()
        mock_tm.now.return_value = '2023-12-25T10:30:00+08:00'
        mock_timemaster_class.return_value = mock_tm
        mock_timemaster_class.FORMAT_ISO = 'iso'

        # 测试离线模式 + 时区 + 格式
        sys.argv = ['cli.py', '--offline', '--timezone', 'Asia/Shanghai', '--format', 'iso']

        main()

        mock_tm.force_offline.assert_called_once_with(True)
        mock_tm.now.assert_called_once_with('Asia/Shanghai', format='iso')

        output = mock_stdout.getvalue().strip()
        self.assertEqual(output, '2023-12-25T10:30:00+08:00')


class TestCLIOutputFormatting(unittest.TestCase):
    """CLI输出格式测试类"""

    def setUp(self):
        """测试前设置"""
        self.original_argv = sys.argv.copy()

    def tearDown(self):
        """测试后清理"""
        sys.argv = self.original_argv

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_search_output_formatting(self, mock_stdout, mock_timemaster_class):
        """测试搜索输出格式"""
        mock_tm = Mock()
        mock_tm.find_timezones.return_value = ['America/New_York', 'America/Chicago']
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--search', 'America']

        main()

        output = mock_stdout.getvalue()
        lines = output.strip().split('\n')

        self.assertEqual(lines[0], "Timezones matching 'America':")
        self.assertEqual(lines[1], "  America/New_York")
        self.assertEqual(lines[2], "  America/Chicago")

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_list_output_formatting_with_truncation(self, mock_stdout, mock_timemaster_class):
        """测试列表输出格式与截断"""
        mock_tm = Mock()
        # 创建超过20个时区的列表
        mock_timezones = [f'Zone_{i:02d}' for i in range(25)]
        mock_tm.list_timezones.return_value = mock_timezones
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--list']

        main()

        output = mock_stdout.getvalue()
        lines = output.strip().split('\n')

        self.assertEqual(lines[0], "All timezones:")
        # 应该有20个时区 + 标题 + 截断信息 = 22行
        self.assertEqual(len(lines), 22)
        self.assertTrue(lines[-1].startswith("  ... and"))
        self.assertIn("5 more", lines[-1])

    @patch('time_master.cli.TimeMaster')
    @patch('sys.stdout', new_callable=io.StringIO)
    def test_difference_output_formatting(self, mock_stdout, mock_timemaster_class):
        """测试差异输出格式"""
        mock_tm = Mock()
        mock_tm.difference.return_value = datetime.timedelta(hours=8, minutes=30)
        mock_timemaster_class.return_value = mock_tm

        sys.argv = ['cli.py', '--difference', 'UTC', 'Asia/Shanghai']

        main()

        output = mock_stdout.getvalue().strip()
        self.assertIn('Time difference between UTC and Asia/Shanghai:', output)
        self.assertIn('8:30:00', output)


if __name__ == '__main__':
    unittest.main()
