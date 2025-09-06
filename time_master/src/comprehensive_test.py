#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive Test Suite for Chinese Calendar Interface

This test suite provides extensive testing coverage including:
- Data accuracy validation
- Performance benchmarking
- Boundary condition testing
- Concurrency testing
- Error handling validation
"""

from time_master.core import TimeMaster
import sys
import os
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class ComprehensiveTestSuite:
    """Comprehensive test suite for Chinese Calendar functionality."""

    def __init__(self):
        self.tm = TimeMaster()
        self.test_results = {
            'accuracy': [],
            'performance': [],
            'boundary': [],
            'concurrency': [],
            'error_handling': []
        }

        # Known accurate data for validation
        self.known_data = [
            # Format: (gregorian_date, expected_lunar_year, expected_lunar_month, expected_lunar_day)
            ('2024-02-10', 2024, 1, 1),  # 2024年春节 (龙年正月初一)
            ('2023-01-22', 2023, 1, 1),  # 2023年春节 (兔年正月初一)
            ('2025-01-29', 2025, 1, 1),  # 2025年春节 (蛇年正月初一)
            ('2024-06-10', 2024, 5, 5),  # 2024年端午节 (五月初五)
            ('2024-09-17', 2024, 8, 15),  # 2024年中秋节 (八月十五)
        ]

    def test_data_accuracy(self):
        """Test data accuracy against known historical dates."""
        print("\n=== 数据准确性测试 ===")

        passed = 0
        total = len(self.known_data)

        for gregorian_date, expected_year, expected_month, expected_day in self.known_data:
            try:
                result = self.tm.get_chinese_calendar_info(gregorian_date)

                if 'error' in result:
                    print(f"✗ {gregorian_date}: {result['error']}")
                    self.test_results['accuracy'].append(False)
                    continue

                lunar_info = result['lunar']
                actual_year = lunar_info['year']
                actual_month = lunar_info['month']
                actual_day = lunar_info['day']

                if (actual_year == expected_year
                    and actual_month == expected_month
                        and actual_day == expected_day):
                    print(f"✓ {gregorian_date} -> 农历{actual_year}年{actual_month}月{actual_day}日")
                    passed += 1
                    self.test_results['accuracy'].append(True)
                else:
                    print(
                        f"✗ {gregorian_date}: 期望{expected_year}-{expected_month}-{expected_day}, 实际{actual_year}-{actual_month}-{actual_day}")
                    self.test_results['accuracy'].append(False)

            except Exception as e:
                print(f"✗ {gregorian_date}: 异常 {e}")
                self.test_results['accuracy'].append(False)

        accuracy_rate = (passed / total) * 100
        print(f"\n数据准确性: {passed}/{total} ({accuracy_rate:.1f}%)")
        return accuracy_rate >= 95.0

    def test_performance_benchmark(self):
        """Test performance with batch operations."""
        print("\n=== 性能基准测试 ===")

        # Generate random test dates
        test_dates = []
        for _ in range(1000):
            year = random.randint(1900, 2100)
            month = random.randint(1, 12)
            day = random.randint(1, 28)  # Safe day range
            test_dates.append(f"{year:04d}-{month:02d}-{day:02d}")

        # Test unified interface performance
        start_time = time.time()
        successful_calls = 0

        for test_date in test_dates:
            try:
                result = self.tm.get_chinese_calendar_info(test_date)
                if 'error' not in result:
                    successful_calls += 1
            except BaseException:
                pass

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = (total_time / len(test_dates)) * 1000  # Convert to milliseconds

        print(f"批量转换测试:")
        print(f"  总请求数: {len(test_dates)}")
        print(f"  成功请求数: {successful_calls}")
        print(f"  总耗时: {total_time:.2f}秒")
        print(f"  平均响应时间: {avg_time:.2f}毫秒")
        print(f"  吞吐量: {successful_calls / total_time:.1f} 请求/秒")

        # Performance criteria: average response time < 10ms
        performance_ok = avg_time < 10.0
        self.test_results['performance'].append(performance_ok)

        return performance_ok

    def test_boundary_conditions(self):
        """Test boundary conditions and edge cases."""
        print("\n=== 边界条件测试 ===")

        boundary_dates = [
            '1900-01-01',  # Early boundary
            '1900-12-31',  # End of early year
            '2000-01-01',  # Millennium
            '2000-02-29',  # Leap year
            '2100-01-01',  # Future boundary
            '2100-12-31',  # Late boundary
        ]

        passed = 0
        total = len(boundary_dates)

        for test_date in boundary_dates:
            try:
                result = self.tm.get_chinese_calendar_info(test_date)

                if 'error' not in result:
                    print(f"✓ {test_date}: 成功处理")
                    passed += 1
                    self.test_results['boundary'].append(True)
                else:
                    print(f"✗ {test_date}: {result['error']}")
                    self.test_results['boundary'].append(False)

            except Exception as e:
                print(f"✗ {test_date}: 异常 {e}")
                self.test_results['boundary'].append(False)

        boundary_success_rate = (passed / total) * 100
        print(f"\n边界条件测试: {passed}/{total} ({boundary_success_rate:.1f}%)")

        return boundary_success_rate >= 80.0

    def test_concurrency(self):
        """Test thread safety and concurrency."""
        print("\n=== 并发测试 ===")

        def worker_function(thread_id, num_calls=50):
            """Worker function for concurrent testing."""
            results = []
            for i in range(num_calls):
                try:
                    test_date = f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
                    result = self.tm.get_chinese_calendar_info(test_date)
                    results.append('error' not in result)
                except BaseException:
                    results.append(False)
            return thread_id, results

        # Run concurrent tests
        num_threads = 10
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_function, i) for i in range(num_threads)]

            total_calls = 0
            successful_calls = 0

            for future in as_completed(futures):
                thread_id, results = future.result()
                thread_success = sum(results)
                total_calls += len(results)
                successful_calls += thread_success
                print(f"线程 {thread_id}: {thread_success}/{len(results)} 成功")

        concurrency_success_rate = (successful_calls / total_calls) * 100
        print(f"\n并发测试总计: {successful_calls}/{total_calls} ({concurrency_success_rate:.1f}%)")

        concurrency_ok = concurrency_success_rate >= 95.0
        self.test_results['concurrency'].append(concurrency_ok)

        return concurrency_ok

    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        print("\n=== 错误处理测试 ===")

        invalid_inputs = [
            '2024-13-01',    # Invalid month
            '2024-02-30',    # Invalid day
            '2024-00-01',    # Invalid month (zero)
            '2024-01-00',    # Invalid day (zero)
            'invalid-date',  # Invalid format
            '2024/01/01',    # Wrong format
            '',              # Empty string
            '1899-12-31',    # Before supported range
            '2101-01-01',    # After supported range
        ]

        passed = 0
        total = len(invalid_inputs)

        for invalid_input in invalid_inputs:
            try:
                result = self.tm.get_chinese_calendar_info(invalid_input)

                if 'error' in result:
                    print(f"✓ '{invalid_input}': 正确处理错误 - {result['error']}")
                    passed += 1
                    self.test_results['error_handling'].append(True)
                else:
                    print(f"✗ '{invalid_input}': 未能检测到错误")
                    self.test_results['error_handling'].append(False)

            except Exception as e:
                print(f"✓ '{invalid_input}': 正确抛出异常 - {e}")
                passed += 1
                self.test_results['error_handling'].append(True)

        error_handling_rate = (passed / total) * 100
        print(f"\n错误处理测试: {passed}/{total} ({error_handling_rate:.1f}%)")

        return error_handling_rate >= 90.0

    def test_interface_consistency(self):
        """Test consistency between different interfaces."""
        print("\n=== 接口一致性测试 ===")

        # Use dates after Chinese New Year to avoid year mismatch
        test_dates = ['2024-03-01', '2024-06-15', '2024-12-31']
        passed = 0
        total = len(test_dates)

        for test_date in test_dates:
            try:
                # Get data from unified interface
                unified_result = self.tm.get_chinese_calendar_info(test_date)

                if 'error' in unified_result:
                    print(f"✗ {test_date}: 统一接口返回错误")
                    continue

                # Get data from simplified interfaces
                lunar_result = self.tm.gregorian_to_lunar(test_date)

                # For zodiac comparison, use the lunar year from unified interface
                lunar_year = unified_result['lunar']['year']
                zodiac_result = self.tm.get_zodiac(lunar_year)

                if 'error' not in lunar_result and 'error' not in zodiac_result:
                    # Check consistency
                    unified_lunar = unified_result['lunar']['lunar_date_str']
                    simple_lunar = lunar_result['lunar_date_str']

                    unified_zodiac = unified_result['zodiac']['chinese_zodiac']
                    simple_zodiac = zodiac_result['zodiac']

                    if unified_lunar == simple_lunar and unified_zodiac == simple_zodiac:
                        print(f"✓ {test_date}: 接口数据一致")
                        passed += 1
                    else:
                        print(f"✗ {test_date}: 接口数据不一致")
                        print(f"  统一接口农历: {unified_lunar}")
                        print(f"  简化接口农历: {simple_lunar}")
                        print(f"  农历年份: {lunar_year}")
                        print(f"  统一接口生肖: {unified_zodiac}")
                        print(f"  简化接口生肖: {simple_zodiac}")
                else:
                    print(f"✗ {test_date}: 简化接口调用失败")

            except Exception as e:
                print(f"✗ {test_date}: 异常 {e}")

        consistency_rate = (passed / total) * 100
        print(f"\n接口一致性测试: {passed}/{total} ({consistency_rate:.1f}%)")

        return consistency_rate >= 95.0

    def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 60)
        print("综合测试报告")
        print("=" * 60)

        # Calculate overall statistics
        all_results = []
        for category_results in self.test_results.values():
            all_results.extend(category_results)

        if all_results:
            overall_success_rate = (sum(all_results) / len(all_results)) * 100
            print(f"\n总体成功率: {sum(all_results)}/{len(all_results)} ({overall_success_rate:.1f}%)")

        # Category breakdown
        print("\n分类测试结果:")
        for category, results in self.test_results.items():
            if results:
                success_rate = (sum(results) / len(results)) * 100
                print(f"  {category}: {sum(results)}/{len(results)} ({success_rate:.1f}%)")

        # Recommendations
        print("\n建议:")
        if overall_success_rate >= 95:
            print("  ✓ 所有测试表现优秀，可以发布")
        elif overall_success_rate >= 90:
            print("  ⚠ 测试表现良好，建议修复少数问题后发布")
        else:
            print("  ✗ 存在较多问题，建议修复后重新测试")

        return overall_success_rate

    def run_all_tests(self):
        """Run all comprehensive tests."""
        print("中国历法接口综合测试套件")
        print("=" * 60)

        test_functions = [
            self.test_data_accuracy,
            self.test_performance_benchmark,
            self.test_boundary_conditions,
            self.test_concurrency,
            self.test_error_handling,
            self.test_interface_consistency,
        ]

        start_time = time.time()

        for test_func in test_functions:
            try:
                test_func()
            except Exception as e:
                print(f"\n测试 {test_func.__name__} 失败: {e}")

        end_time = time.time()
        total_test_time = end_time - start_time

        print(f"\n总测试时间: {total_test_time:.2f}秒")

        # Generate final report
        overall_success_rate = self.generate_test_report()

        return overall_success_rate >= 90.0


def main():
    """Main test execution function."""
    test_suite = ComprehensiveTestSuite()

    try:
        success = test_suite.run_all_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"\n测试套件执行失败: {e}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
