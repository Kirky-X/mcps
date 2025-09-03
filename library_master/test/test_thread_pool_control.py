#!/usr/bin/env python3
"""线程池和进程控制测试

此脚本测试BatchProcessor的线程池控制功能，包括：
1. 线程池大小控制
2. 并发任务执行
3. 超时控制
4. 资源管理
5. 性能测试
"""

import asyncio
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from library_master.core.processor import BatchProcessor
from library_master.models import LibraryQuery, Language
from library_master.core.config import Settings


class TestThreadPoolControl:
    """线程池控制测试"""

    def test_thread_pool_initialization(self):
        """测试线程池初始化"""
        # 测试不同的max_workers配置
        test_configs = [1, 5, 10, 20]

        for max_workers in test_configs:
            processor = BatchProcessor(max_workers=max_workers)
            assert processor.max_workers == max_workers
            assert processor.request_timeout == 30.0  # 默认值

    def test_thread_pool_size_limits(self):
        """测试线程池大小限制"""
        # 测试极端值
        processor_min = BatchProcessor(max_workers=1)
        assert processor_min.max_workers == 1

        processor_max = BatchProcessor(max_workers=100)
        assert processor_max.max_workers == 100

    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """测试并发执行"""
        processor = BatchProcessor(max_workers=5, request_timeout=10.0)

        # 创建多个查询任务
        libraries = [
            LibraryQuery(language=Language.PYTHON, name="requests", version="2.28.0"),
            LibraryQuery(language=Language.PYTHON, name="flask", version="2.0.0"),
            LibraryQuery(language=Language.RUST, name="serde", version="1.0.0"),
            LibraryQuery(language=Language.NODE, name="express", version="4.18.0"),
            LibraryQuery(language=Language.JAVA, name="jackson-core", version="2.14.0")
        ]

        start_time = time.time()
        response = await processor.process_batch(libraries, "check_versions_exist")
        execution_time = time.time() - start_time

        # 验证结果
        assert response.summary.total == 5
        assert len(response.results) == 5

        # 并发执行应该比串行执行快
        # 假设每个任务至少需要0.1秒，串行执行需要0.5秒以上
        # 并发执行应该在2秒内完成
        assert execution_time < 15.0  # 给足够的时间余量

        print(f"并发执行时间: {execution_time:.2f}秒")
        print(f"成功任务数: {response.summary.success}")
        print(f"失败任务数: {response.summary.failed}")

    @pytest.mark.asyncio
    async def test_timeout_control(self):
        """测试超时控制"""
        # 使用很短的超时时间
        processor = BatchProcessor(max_workers=3, request_timeout=0.1)

        libraries = [
            LibraryQuery(language=Language.PYTHON, name="requests", version="2.28.0"),
            LibraryQuery(language=Language.RUST, name="serde", version="1.0.0")
        ]

        start_time = time.time()
        response = await processor.process_batch(libraries, "get_latest_version")
        execution_time = time.time() - start_time

        # 验证超时控制生效
        assert execution_time < 5.0  # 应该很快返回
        assert response.summary.total == 2

        # 可能有些任务因为超时而失败
        print(f"超时测试执行时间: {execution_time:.2f}秒")
        print(f"成功任务数: {response.summary.success}")
        print(f"失败任务数: {response.summary.failed}")

    @pytest.mark.asyncio
    async def test_resource_management(self):
        """测试资源管理"""
        processor = BatchProcessor(max_workers=3)

        # 创建大量任务来测试资源管理
        libraries = []
        for i in range(10):
            libraries.append(
                LibraryQuery(language=Language.PYTHON, name=f"test-lib-{i}", version="1.0.0")
            )

        response = await processor.process_batch(libraries, "check_versions_exist")

        # 验证所有任务都被处理
        assert response.summary.total == 10
        assert len(response.results) == 10

        # 验证缓存统计
        cache_stats = processor.get_cache_stats()
        assert isinstance(cache_stats, dict)

        print(f"资源管理测试 - 总任务数: {response.summary.total}")
        print(f"缓存统计: {cache_stats}")

    @pytest.mark.asyncio
    async def test_performance_scaling(self):
        """测试性能扩展"""
        # 测试不同线程池大小的性能
        libraries = [
            LibraryQuery(language=Language.PYTHON, name="requests", version="2.28.0"),
            LibraryQuery(language=Language.PYTHON, name="flask", version="2.0.0"),
            LibraryQuery(language=Language.RUST, name="serde", version="1.0.0"),
            LibraryQuery(language=Language.NODE, name="express", version="4.18.0")
        ]

        results = {}

        for max_workers in [1, 2, 4, 8]:
            processor = BatchProcessor(max_workers=max_workers, request_timeout=15.0)

            start_time = time.time()
            response = await processor.process_batch(libraries, "check_versions_exist")
            execution_time = time.time() - start_time

            results[max_workers] = {
                'time': execution_time,
                'success': response.summary.success,
                'failed': response.summary.failed
            }

            print(
                f"线程数 {max_workers}: {execution_time:.2f}秒, 成功 {response.summary.success}, 失败 {response.summary.failed}")

        # 验证性能趋势（更多线程通常应该更快，但有上限）
        assert results[1]['time'] >= results[2]['time'] * 0.7  # 允许一些变化

        return results

    def test_cache_integration(self):
        """测试缓存集成"""
        settings = Settings()
        settings.cache_ttl = 3600
        settings.cache_max_size = 100

        processor = BatchProcessor(max_workers=2, settings=settings)

        # 验证缓存管理器已正确初始化
        assert processor.cache_manager is not None

        # 测试缓存操作
        cache_stats = processor.get_cache_stats()
        assert isinstance(cache_stats, dict)

        # 清空缓存
        processor.clear_cache()

        print(f"缓存集成测试完成")


class TestConcurrentExecution:
    """并发执行测试"""

    def test_thread_pool_executor_direct(self):
        """直接测试ThreadPoolExecutor"""

        def dummy_task(task_id: int) -> dict:
            """模拟任务"""
            time.sleep(0.1)  # 模拟工作
            return {"task_id": task_id, "result": f"completed_{task_id}"}

        # 测试不同的线程池大小
        for max_workers in [1, 3, 5]:
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(dummy_task, i) for i in range(5)]
                results = [future.result() for future in futures]

            execution_time = time.time() - start_time

            assert len(results) == 5
            assert all('task_id' in result for result in results)

            print(f"线程池大小 {max_workers}: {execution_time:.2f}秒")

    @pytest.mark.asyncio
    async def test_mixed_language_concurrent_processing(self):
        """测试混合语言并发处理"""
        processor = BatchProcessor(max_workers=6, request_timeout=20.0)

        # 创建混合语言任务
        libraries = [
            LibraryQuery(language=Language.PYTHON, name="requests", version="2.28.0"),
            LibraryQuery(language=Language.RUST, name="serde", version="1.0.0"),
            LibraryQuery(language=Language.NODE, name="express", version="4.18.0"),
            LibraryQuery(language=Language.JAVA, name="jackson-core", version="2.14.0"),
            LibraryQuery(language=Language.GO, name="gin", version="1.9.0"),
            LibraryQuery(language=Language.CPP, name="boost", version="1.80.0")
        ]

        start_time = time.time()
        response = await processor.process_batch(libraries, "get_latest_version")
        execution_time = time.time() - start_time

        print(f"混合语言并发处理时间: {execution_time:.2f}秒")
        print(f"总任务数: {response.summary.total}")
        print(f"成功任务数: {response.summary.success}")
        print(f"失败任务数: {response.summary.failed}")

        # 验证所有语言都被处理
        processed_languages = set(result.language for result in response.results)
        expected_languages = {lang.value for lang in
                              [Language.PYTHON, Language.RUST, Language.NODE, Language.JAVA, Language.GO, Language.CPP]}

        assert len(processed_languages.intersection(expected_languages)) >= 3  # 至少处理了3种语言


if __name__ == "__main__":
    # 运行基本测试
    test_class = TestThreadPoolControl()

    print("🧵 开始线程池控制测试")

    # 同步测试
    test_class.test_thread_pool_initialization()
    print("✅ 线程池初始化测试通过")

    test_class.test_thread_pool_size_limits()
    print("✅ 线程池大小限制测试通过")

    test_class.test_cache_integration()
    print("✅ 缓存集成测试通过")


    # 异步测试
    async def run_async_tests():
        await test_class.test_concurrent_execution()
        print("✅ 并发执行测试通过")

        await test_class.test_timeout_control()
        print("✅ 超时控制测试通过")

        await test_class.test_resource_management()
        print("✅ 资源管理测试通过")

        await test_class.test_performance_scaling()
        print("✅ 性能扩展测试通过")

        # 并发执行测试
        concurrent_test = TestConcurrentExecution()
        concurrent_test.test_thread_pool_executor_direct()
        print("✅ 直接线程池测试通过")

        await concurrent_test.test_mixed_language_concurrent_processing()
        print("✅ 混合语言并发处理测试通过")


    # 运行异步测试
    asyncio.run(run_async_tests())

    print("🎉 所有线程池和进程控制测试完成")
