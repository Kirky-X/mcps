#!/usr/bin/env python3
"""LibraryMaster MCP工具全面功能测试

此脚本测试所有MCP工具的功能，输出原始接口结果，不进行任何包装。
测试包括：
1. find_latest_versions - 查找最新版本
2. find_library_docs - 查找文档
3. check_versions_exist - 检查版本是否存在
4. find_library_dependencies - 查找依赖
"""

import asyncio
import json
from typing import Dict, Any

from library_master.core.config import Settings
from library_master.core.server import LibraryMasterServer
from library_master.models import Language, LibraryQuery


class MCPToolTester:
    """MCP工具测试器"""

    def __init__(self):
        """初始化测试器"""
        settings = Settings()
        self.server = LibraryMasterServer(settings)

    def print_raw_result(self, tool_name: str, params: Dict[str, Any], result: Any):
        """打印原始接口结果"""
        print(f"\n{'=' * 60}")
        print(f"工具: {tool_name}")
        print(f"参数: {json.dumps(params, ensure_ascii=False, indent=2)}")
        print(f"原始结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"{'=' * 60}")

    async def test_find_latest_versions(self):
        """测试find_latest_versions工具"""
        print("\n🔍 测试 find_latest_versions 工具")

        test_cases = [
            # Rust库测试
            {
                "libraries": [
                    {"name": "serde", "language": "rust"},
                    {"name": "tokio", "language": "rust"},
                    {"name": "clap", "language": "rust"}
                ]
            },
            # Python库测试
            {
                "libraries": [
                    {"name": "requests", "language": "python"},
                    {"name": "numpy", "language": "python"},
                    {"name": "django", "language": "python"}
                ]
            },
            # Java库测试
            {
                "libraries": [
                    {"name": "jackson-core", "language": "java"},
                    {"name": "spring-boot", "language": "java"},
                    {"name": "junit", "language": "java"}
                ]
            },
            # Node.js库测试
            {
                "libraries": [
                    {"name": "express", "language": "node"},
                    {"name": "lodash", "language": "node"},
                    {"name": "axios", "language": "node"}
                ]
            },
            # 混合语言批量测试
            {
                "libraries": [
                    {"name": "serde", "language": "rust"},
                    {"name": "requests", "language": "python"},
                    {"name": "jackson-core", "language": "java"},
                    {"name": "express", "language": "node"}
                ]
            }
        ]

        for i, params in enumerate(test_cases, 1):
            print(f"\n--- 测试用例 {i} ---")
            try:
                result = await self.server.find_latest_versions(params["libraries"])
                self.print_raw_result("find_latest_versions", params, result)
            except Exception as e:
                print(f"错误: {e}")

    async def test_find_library_docs(self):
        """测试find_library_docs工具"""
        print("\n📚 测试 find_library_docs 工具")

        test_cases = [
            # Rust库文档
            {
                "libraries": [
                    {"name": "serde", "language": "rust"},
                    {"name": "tokio", "language": "rust"}
                ]
            },
            # Python库文档
            {
                "libraries": [
                    {"name": "requests", "language": "python"},
                    {"name": "flask", "language": "python"}
                ]
            },
            # Java库文档
            {
                "libraries": [
                    {"name": "jackson-core", "language": "java"},
                    {"name": "spring-boot", "language": "java"}
                ]
            },
            # Node.js库文档
            {
                "libraries": [
                    {"name": "express", "language": "node"},
                    {"name": "react", "language": "node"}
                ]
            },
            # 单个库测试
            {
                "libraries": [
                    {"name": "serde", "language": "rust"}
                ]
            }
        ]

        for i, params in enumerate(test_cases, 1):
            print(f"\n--- 测试用例 {i} ---")
            try:
                result = await self.server.find_library_docs(params["libraries"])
                self.print_raw_result("find_library_docs", params, result)
            except Exception as e:
                print(f"错误: {e}")

    async def test_check_versions_exist(self):
        """测试check_versions_exist工具"""
        print("\n✅ 测试 check_versions_exist 工具")

        test_cases = [
            # Rust库版本检查
            {
                "libraries": [
                    {"name": "serde", "language": "rust", "version": "1.0.210"},
                    {"name": "tokio", "language": "rust", "version": "1.40.0"},
                    {"name": "clap", "language": "rust", "version": "4.5.20"}
                ]
            },
            # Python库版本检查
            {
                "libraries": [
                    {"name": "requests", "language": "python", "version": "2.31.0"},
                    {"name": "numpy", "language": "python", "version": "1.24.3"},
                    {"name": "django", "language": "python", "version": "4.2.7"}
                ]
            },
            # Java库版本检查
            {
                "libraries": [
                    {"name": "jackson-core", "language": "java", "version": "2.15.2"},
                    {"name": "spring-boot", "language": "java", "version": "3.1.5"},
                    {"name": "junit", "language": "java", "version": "5.10.0"}
                ]
            },
            # Node.js库版本检查
            {
                "libraries": [
                    {"name": "express", "language": "node", "version": "4.18.2"},
                    {"name": "lodash", "language": "node", "version": "4.17.21"},
                    {"name": "axios", "language": "node", "version": "1.6.0"}
                ]
            },
            # 不存在的版本测试
            {
                "libraries": [
                    {"name": "serde", "language": "rust", "version": "999.999.999"},
                    {"name": "requests", "language": "python", "version": "999.999.999"}
                ]
            }
        ]

        for i, params in enumerate(test_cases, 1):
            print(f"\n--- 测试用例 {i} ---")
            try:
                result = await self.server.check_versions_exist(params["libraries"])
                self.print_raw_result("check_versions_exist", params, result)
            except Exception as e:
                print(f"错误: {e}")

    async def test_find_library_dependencies(self):
        """测试find_library_dependencies工具"""
        print("\n🔗 测试 find_library_dependencies 工具")

        test_cases = [
            # Rust依赖查找
            {
                "libraries": [
                    {"name": "serde", "language": "rust"},
                    {"name": "tokio", "language": "rust"}
                ]
            },
            # Python依赖查找
            {
                "libraries": [
                    {"name": "requests", "language": "python"},
                    {"name": "flask", "language": "python"}
                ]
            },
            # Java依赖查找
            {
                "libraries": [
                    {"name": "spring-boot", "language": "java"}
                ]
            },
            # Node.js依赖查找
            {
                "libraries": [
                    {"name": "express", "language": "node"},
                    {"name": "react", "language": "node"}
                ]
            },
            # 指定版本的依赖查找
            {
                "libraries": [
                    {"name": "serde", "language": "rust", "version": "1.0.0"}
                ]
            }
        ]

        for i, params in enumerate(test_cases, 1):
            print(f"\n--- 测试用例 {i} ---")
            try:
                result = await self.server.find_library_dependencies(params["libraries"])
                self.print_raw_result("find_library_dependencies", params, result)
            except Exception as e:
                print(f"错误: {e}")

    async def test_cache_operations(self):
        """测试缓存操作工具"""
        print("\n💾 测试缓存操作工具")

        # 测试缓存统计
        print("\n--- 缓存统计 ---")
        try:
            result = await self.server.get_cache_stats()
            self.print_raw_result("get_cache_stats", {}, result)
        except Exception as e:
            print(f"错误: {e}")

        # 先执行一些查询以填充缓存
        print("\n--- 执行查询以填充缓存 ---")
        await self.server.find_latest_versions([{"name": "serde", "language": "rust"}])

        # 再次查看缓存统计
        print("\n--- 填充后的缓存统计 ---")
        try:
            result = await self.server.get_cache_stats()
            self.print_raw_result("get_cache_stats", {}, result)
        except Exception as e:
            print(f"错误: {e}")

        # 测试清空缓存
        print("\n--- 清空缓存 ---")
        try:
            result = await self.server.clear_cache()
            self.print_raw_result("clear_cache", {}, result)
        except Exception as e:
            print(f"错误: {e}")

        # 清空后的缓存统计
        print("\n--- 清空后的缓存统计 ---")
        try:
            result = await self.server.get_cache_stats()
            self.print_raw_result("get_cache_stats", {}, result)
        except Exception as e:
            print(f"错误: {e}")

    async def test_batch_operations(self):
        """测试批量操作"""
        print("\n📦 测试批量操作")

        # 大批量测试
        large_batch_libraries = [
            {"name": "serde", "language": "rust"},
            {"name": "tokio", "language": "rust"},
            {"name": "clap", "language": "rust"},
            {"name": "anyhow", "language": "rust"},
            {"name": "thiserror", "language": "rust"},
            {"name": "requests", "language": "python"},
            {"name": "numpy", "language": "python"},
            {"name": "django", "language": "python"},
            {"name": "flask", "language": "python"},
            {"name": "fastapi", "language": "python"},
            {"name": "jackson-core", "language": "java"},
            {"name": "spring-boot", "language": "java"},
            {"name": "junit", "language": "java"},
            {"name": "mockito", "language": "java"},
            {"name": "slf4j", "language": "java"},
            {"name": "express", "language": "node"},
            {"name": "react", "language": "node"},
            {"name": "lodash", "language": "node"},
            {"name": "axios", "language": "node"},
            {"name": "moment", "language": "node"}
        ]

        print("\n--- 大批量版本查询 (20个库) ---")
        try:
            result = await self.server.find_latest_versions(large_batch_libraries)
            self.print_raw_result("find_latest_versions (大批量)", {"libraries": large_batch_libraries}, result)
        except Exception as e:
            print(f"错误: {e}")

    async def test_error_cases(self):
        """测试错误情况"""
        print("\n❌ 测试错误情况")

        error_test_cases = [
            # 不存在的库
            {
                "tool": "find_latest_versions",
                "params": [
                    {"name": "nonexistent-library-12345", "language": "rust"}
                ]
            },
            # 无效的语言
            {
                "tool": "find_latest_versions",
                "params": [
                    {"name": "serde", "language": "invalid-language"}
                ]
            },
            # 空库名
            {
                "tool": "find_latest_versions",
                "params": [
                    {"name": "", "language": "rust"}
                ]
            },
            # 版本不存在
            {
                "tool": "check_versions_exist",
                "params": [
                    {"name": "serde", "language": "rust", "version": "999.999.999"}
                ]
            }
        ]

        for i, test_case in enumerate(error_test_cases, 1):
            print(f"\n--- 错误测试用例 {i} ---")
            tool_name = test_case["tool"]
            params = test_case["params"]

            try:
                if tool_name == "find_latest_versions":
                    result = await self.server.find_latest_versions(params)
                elif tool_name == "check_versions_exist":
                    result = await self.server.check_versions_exist(params)
                else:
                    result = "未知工具"

                self.print_raw_result(f"{tool_name} (错误测试)", {"libraries": params}, result)
            except Exception as e:
                print(f"预期错误: {e}")
                self.print_raw_result(f"{tool_name} (错误测试)", {"libraries": params}, {"error": str(e)})

    async def test_java_only(self):
        """只测试Java相关功能"""
        print("☕ 开始Java Worker专项测试")
        print("📋 测试Java混合方案：Maven Central搜索API + 直接POM访问")
        print("⏰ 测试可能需要几分钟时间，请耐心等待...")

        try:
            # 1. 测试find_latest_versions - Java库
            print("\n🔍 测试 find_latest_versions (Java)")
            java_latest_test_cases = [
                {
                    "libraries": [
                        {"name": "jackson-core", "language": "java"},
                        {"name": "spring-boot", "language": "java"},
                        {"name": "junit", "language": "java"}
                    ]
                },
                {
                    "libraries": [
                        {"name": "com.fasterxml.jackson.core:jackson-core", "language": "java"},
                        {"name": "org.springframework.boot:spring-boot-starter", "language": "java"}
                    ]
                }
            ]

            for i, params in enumerate(java_latest_test_cases, 1):
                print(f"\n--- Java版本查询测试用例 {i} ---")
                try:
                    result = await self.server.find_latest_versions(params["libraries"])
                    self.print_raw_result("find_latest_versions (Java)", params, result)
                except Exception as e:
                    print(f"错误: {e}")

            # 2. 测试find_library_docs - Java库
            print("\n📚 测试 find_library_docs (Java)")
            java_docs_test_cases = [
                {
                    "libraries": [
                        {"name": "jackson-core", "language": "java"},
                        {"name": "spring-boot", "language": "java"}
                    ]
                },
                {
                    "libraries": [
                        {"name": "org.junit.jupiter:junit-jupiter", "language": "java"}
                    ]
                }
            ]

            for i, params in enumerate(java_docs_test_cases, 1):
                print(f"\n--- Java文档查询测试用例 {i} ---")
                try:
                    result = await self.server.find_library_docs(params["libraries"])
                    self.print_raw_result("find_library_docs (Java)", params, result)
                except Exception as e:
                    print(f"错误: {e}")

            # 3. 测试check_versions_exist - Java库
            print("\n✅ 测试 check_versions_exist (Java)")
            java_version_test_cases = [
                {
                    "libraries": [
                        {"name": "jackson-core", "language": "java", "version": "2.15.2"},
                        {"name": "spring-boot", "language": "java", "version": "3.1.5"},
                        {"name": "junit", "language": "java", "version": "5.10.0"}
                    ]
                },
                {
                    "libraries": [
                        {"name": "com.fasterxml.jackson.core:jackson-core", "language": "java", "version": "2.15.2"}
                    ]
                },
                # 测试不存在的版本
                {
                    "libraries": [
                        {"name": "jackson-core", "language": "java", "version": "999.999.999"}
                    ]
                }
            ]

            for i, params in enumerate(java_version_test_cases, 1):
                print(f"\n--- Java版本存在性测试用例 {i} ---")
                try:
                    result = await self.server.check_versions_exist(params["libraries"])
                    self.print_raw_result("check_versions_exist (Java)", params, result)
                except Exception as e:
                    print(f"错误: {e}")

            # 4. 测试find_library_dependencies - Java库
            print("\n🔗 测试 find_library_dependencies (Java)")
            java_deps_test_cases = [
                {
                    "libraries": [
                        {"name": "spring-boot", "language": "java"}
                    ]
                },
                {
                    "libraries": [
                        {"name": "jackson-core", "language": "java"}
                    ]
                },
                {
                    "libraries": [
                        {"name": "org.springframework.boot:spring-boot-starter-web", "language": "java"}
                    ]
                },
                # 指定版本的依赖查找
                {
                    "libraries": [
                        {"name": "jackson-core", "language": "java", "version": "2.15.2"}
                    ]
                }
            ]

            for i, params in enumerate(java_deps_test_cases, 1):
                print(f"\n--- Java依赖查询测试用例 {i} ---")
                try:
                    result = await self.server.find_library_dependencies(params["libraries"])
                    self.print_raw_result("find_library_dependencies (Java)", params, result)
                except Exception as e:
                    print(f"错误: {e}")

            print("\n✅ Java专项测试完成！")
            print("📊 测试总结:")
            print("   - find_latest_versions: 测试了Maven Central搜索API获取最新版本")
            print("   - find_library_docs: 测试了文档URL生成")
            print("   - check_versions_exist: 测试了版本存在性检查")
            print("   - find_library_dependencies: 测试了直接POM访问获取依赖信息")

        except Exception as e:
            print(f"\n❌ Java测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始LibraryMaster MCP工具全面功能测试")
        print("📋 测试将输出原始接口结果，不进行任何包装")
        print("⏰ 测试可能需要几分钟时间，请耐心等待...")

        try:
            # 测试所有核心工具
            await self.test_find_latest_versions()
            await self.test_find_library_docs()
            await self.test_check_versions_exist()
            await self.test_find_library_dependencies()

            # 测试缓存操作
            await self.test_cache_operations()

            # 测试批量操作
            await self.test_batch_operations()

            # 测试错误情况
            await self.test_error_cases()

            print("\n✅ 所有测试完成！")

        except Exception as e:
            print(f"\n❌ 测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    tester = MCPToolTester()
    # 运行所有测试，包括4个开发语言的全量接口测试
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
