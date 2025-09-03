#!/usr/bin/env python3
"""TimeMaster MCP工具全面功能测试

此脚本测试所有MCP工具的功能，输出原始接口结果，不进行任何包装。
测试包括：
1. get_time - 获取时间
2. get_local_timezone - 获取本地时区
3. search_timezones - 搜索时区
4. calculate_time_difference - 计算时间差
5. search_holiday - 搜索节假日
6. list_holidays - 列出节假日
"""

import asyncio
import json
import sys
from typing import List, Dict, Any

from time_master.core import TimeMaster
from time_master.config import TimeMasterConfig


class MCPToolTester:
    """MCP工具测试器"""
    
    def __init__(self):
        """初始化测试器"""
        config = TimeMasterConfig()
        self.timemaster = TimeMaster(config=config)
    
    def print_raw_result(self, tool_name: str, params: Dict[str, Any], result: Any):
        """打印原始接口结果"""
        print(f"\n{'='*60}")
        print(f"工具: {tool_name}")
        print(f"参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
        print(f"原始结果:")
        if isinstance(result, str):
            print(result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"{'='*60}")
    
    async def test_get_time(self):
        """测试get_time工具"""
        print("\n🕐 测试 get_time 工具")
        
        test_cases = [
            # 获取当前时间
            {"timezone": "UTC", "format": "iso"},
            {"timezone": "Asia/Shanghai", "format": "iso"},
            {"timezone": "America/New_York", "format": "friendly_cn"},
            {"timezone": "Europe/London", "format": "iso"},
            # 时间转换
            {
                "timezone": "Asia/Tokyo",
                "time_str": "2024-01-15 10:30:00",
                "from_tz": "UTC",
                "format": "iso"
            },
            {
                "timezone": "America/Los_Angeles",
                "time_str": "2024-06-15 15:45:00",
                "from_tz": "Asia/Shanghai",
                "format": "friendly_cn"
            }
        ]
        
        for i, params in enumerate(test_cases, 1):
            print(f"\n--- 测试用例 {i} ---")
            try:
                result = self.timemaster.get_time(**params)
                self.print_raw_result("get_time", params, result)
            except Exception as e:
                print(f"错误: {e}")
    
    async def test_get_local_timezone(self):
        """测试get_local_timezone工具"""
        print("\n🌍 测试 get_local_timezone 工具")
        
        try:
            result = self.timemaster.get_local_timezone()
            self.print_raw_result("get_local_timezone", {}, result)
        except Exception as e:
            print(f"错误: {e}")
    
    async def test_search_timezones(self):
        """测试search_timezones工具"""
        print("\n🔍 测试 search_timezones 工具")
        
        test_cases = [
            {"query": "Shanghai", "limit": 5},
            {"query": "New_York", "limit": 3},
            {"query": "London", "limit": 5},
            {"query": "Tokyo", "limit": 3},
            {"query": "", "limit": 10}  # 列出所有时区（限制10个）
        ]
        
        for i, params in enumerate(test_cases, 1):
            print(f"\n--- 测试用例 {i} ---")
            try:
                result = self.timemaster.search_timezones(**params)
                self.print_raw_result("search_timezones", params, result)
            except Exception as e:
                print(f"错误: {e}")
    
    async def test_calculate_time_difference(self):
        """测试calculate_time_difference工具"""
        print("\n⏰ 测试 calculate_time_difference 工具")
        
        test_cases = [
            {
                "time1": "2024-01-15 10:00:00",
                "tz1": "UTC",
                "time2": "2024-01-15 18:00:00",
                "tz2": "Asia/Shanghai"
            },
            {
                "time1": "2024-06-15 09:00:00",
                "tz1": "America/New_York",
                "time2": "2024-06-15 15:00:00",
                "tz2": "Europe/London"
            },
            {
                "time1": "2024-12-25 12:00:00",
                "tz1": "Asia/Tokyo",
                "time2": "2024-12-25 20:00:00",
                "tz2": "America/Los_Angeles"
            }
        ]
        
        for i, params in enumerate(test_cases, 1):
            print(f"\n--- 测试用例 {i} ---")
            try:
                result = self.timemaster.calculate_time_difference(**params)
                self.print_raw_result("calculate_time_difference", params, result)
            except Exception as e:
                print(f"错误: {e}")
    
    async def test_search_holiday(self):
        """测试search_holiday工具"""
        print("\n🎉 测试 search_holiday 工具")
        
        test_cases = [
            {"query": "Christmas", "country": "US", "limit": 3},
            {"query": "New Year", "country": "GB", "limit": 2},
            {"query": "Independence", "country": "US", "limit": 5},
            {"query": "", "timezone": "Asia/Shanghai", "limit": 5},  # 下一个节假日
            {"query": "", "country": "US", "limit": 3}  # 下一个节假日
        ]
        
        for i, params in enumerate(test_cases, 1):
            print(f"\n--- 测试用例 {i} ---")
            try:
                result = self.timemaster.search_holiday(**params)
                self.print_raw_result("search_holiday", params, result)
            except Exception as e:
                print(f"错误: {e}")
    
    async def test_list_holidays(self):
        """测试list_holidays工具"""
        print("\n📅 测试 list_holidays 工具")
        
        test_cases = [
            {"country": "US", "year": 2024},
            {"country": "GB", "year": 2024},
            {"timezone": "Asia/Shanghai", "year": 2024},
            {"country": "FR", "year": 2025}
        ]
        
        for i, params in enumerate(test_cases, 1):
            print(f"\n--- 测试用例 {i} ---")
            try:
                result = self.timemaster.list_holidays(**params)
                self.print_raw_result("list_holidays", params, result)
            except Exception as e:
                print(f"错误: {e}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始TimeMaster MCP工具全面测试")
        print(f"TimeMaster在线模式: {self.timemaster._is_online}")
        
        await self.test_get_time()
        await self.test_get_local_timezone()
        await self.test_search_timezones()
        await self.test_calculate_time_difference()
        await self.test_search_holiday()
        await self.test_list_holidays()
        
        print("\n✅ 所有测试完成")


async def main():
    """主函数"""
    tester = MCPToolTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())