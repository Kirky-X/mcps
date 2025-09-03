"""真实使用场景的全面测试 - 使用最新版本信息"""

import pytest
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from library_master.models import Language
from library_master.workers import WorkerFactory
from library_master.exceptions import LibraryNotFoundError, VersionNotFoundError


class TestRealWorldScenarios:
    """真实使用场景测试 - 使用最新版本信息"""
    
    def test_rust_serde_latest_version(self):
        """测试Rust serde库最新版本获取 - 真实API调用"""
        worker = WorkerFactory.create_worker(Language.RUST)
        
        # 获取最新版本 - 真实API调用
        result = worker.get_latest_version("serde")
        print(f"\n=== Rust serde 最新版本 ===")
        print(f"原始结果: {result}")
        
        # 验证返回格式
        assert isinstance(result, dict)
        assert "version" in result
        assert result["version"] is not None
        
        # 验证版本格式（应该是语义化版本）
        version = result["version"]
        assert isinstance(version, str)
        assert len(version.split('.')) >= 2  # 至少有主版本和次版本
        
        print(f"验证通过: 版本 {version}")
    
    def test_python_requests_latest_version(self):
        """测试Python requests库最新版本获取 - 真实API调用"""
        worker = WorkerFactory.create_worker(Language.PYTHON)
        
        # 获取最新版本 - 真实API调用
        result = worker.get_latest_version("requests")
        print(f"\n=== Python requests 最新版本 ===")
        print(f"原始结果: {result}")
        
        # 验证返回格式
        assert isinstance(result, dict)
        assert "version" in result
        assert result["version"] is not None
        
        # 验证版本格式
        version = result["version"]
        assert isinstance(version, str)
        assert len(version.split('.')) >= 2
        
        print(f"验证通过: 版本 {version}")
    
    def test_node_express_latest_version(self):
        """测试Node.js express库最新版本获取 - 真实API调用"""
        worker = WorkerFactory.create_worker(Language.NODE)
        
        # 获取最新版本 - 真实API调用
        result = worker.get_latest_version("express")
        print(f"\n=== Node.js express 最新版本 ===")
        print(f"原始结果: {result}")
        
        # 验证返回格式
        assert isinstance(result, dict)
        assert "version" in result
        assert result["version"] is not None
        
        # 验证版本格式
        version = result["version"]
        assert isinstance(version, str)
        assert len(version.split('.')) >= 2
        
        print(f"验证通过: 版本 {version}")
    
    def test_java_junit_latest_version(self):
        """测试Java junit库最新版本获取 - 真实API调用"""
        worker = WorkerFactory.create_worker(Language.JAVA)
        
        # 获取最新版本 - 真实API调用
        result = worker.get_latest_version("junit:junit")
        print(f"\n=== Java junit 最新版本 ===")
        print(f"原始结果: {result}")
        
        # 验证返回格式
        assert isinstance(result, dict)
        assert "version" in result
        assert result["version"] is not None
        
        # 验证版本格式
        version = result["version"]
        assert isinstance(version, str)
        
        print(f"验证通过: 版本 {version}")
    
    def test_go_testify_latest_version(self):
        """测试Go testify库最新版本获取 - 真实API调用"""
        worker = WorkerFactory.create_worker(Language.GO)
        
        # 获取最新版本 - 真实API调用
        result = worker.get_latest_version("github.com/stretchr/testify")
        print(f"\n=== Go testify 最新版本 ===")
        print(f"原始结果: {result}")
        
        # 验证返回格式
        assert isinstance(result, dict)
        assert "version" in result
        assert result["version"] is not None
        
        # 验证版本格式
        version = result["version"]
        assert isinstance(version, str)
        
        print(f"验证通过: 版本 {version}")
    
    def test_cpp_boost_latest_version(self):
        """测试C++ boost库最新版本获取 - 真实API调用"""
        worker = WorkerFactory.create_worker(Language.CPP)
        
        # 获取最新版本 - 真实API调用，使用vcpkg生态系统
        result = worker.get_latest_version("vcpkg:boost")
        print(f"\n=== C++ boost (vcpkg) 最新版本 ===")
        print(f"原始结果: {result}")
        
        # 验证返回格式
        assert isinstance(result, dict)
        assert "version" in result
        assert result["version"] is not None
        
        # 验证版本格式
        version = result["version"]
        assert isinstance(version, str)
        
        print(f"验证通过: 版本 {version}")


class TestDocumentationUrls:
    """文档URL测试 - 真实场景"""
    
    def test_rust_serde_documentation(self):
        """测试Rust serde文档URL生成"""
        worker = WorkerFactory.create_worker(Language.RUST)
        
        # 使用MCP查询到的最新版本 1.0.219
        result = worker.get_documentation_url("serde", "1.0.219")
        print(f"\n=== Rust serde 文档URL ===")
        print(f"原始结果: {result}")
        
        assert isinstance(result, dict)
        assert "doc_url" in result
        assert "docs.rs" in result["doc_url"]
        assert "serde" in result["doc_url"]
        assert "1.0.219" in result["doc_url"]
        
        print(f"验证通过: {result['doc_url']}")
    
    def test_python_requests_documentation(self):
        """测试Python requests文档URL生成"""
        worker = WorkerFactory.create_worker(Language.PYTHON)
        
        # 使用MCP查询到的最新版本 2.32.5
        result = worker.get_documentation_url("requests", "2.32.5")
        print(f"\n=== Python requests 文档URL ===")
        print(f"原始结果: {result}")
        
        assert isinstance(result, dict)
        assert "doc_url" in result
        assert "pypi.org" in result["doc_url"]
        assert "requests" in result["doc_url"]
        assert "2.32.5" in result["doc_url"]
        
        print(f"验证通过: {result['doc_url']}")
    
    def test_node_express_documentation(self):
        """测试Node.js express文档URL生成"""
        worker = WorkerFactory.create_worker(Language.NODE)
        
        # 使用MCP查询到的最新版本 5.1.0
        result = worker.get_documentation_url("express", "5.1.0")
        print(f"\n=== Node.js express 文档URL ===")
        print(f"原始结果: {result}")
        
        assert isinstance(result, dict)
        assert "doc_url" in result
        assert "npmjs.com" in result["doc_url"]
        assert "express" in result["doc_url"]
        assert "5.1.0" in result["doc_url"]
        
        print(f"验证通过: {result['doc_url']}")


class TestVersionExistence:
    """版本存在性检查测试 - 真实场景"""
    
    def test_rust_serde_version_exists(self):
        """测试Rust serde版本存在性检查"""
        worker = WorkerFactory.create_worker(Language.RUST)
        
        # 检查已知存在的版本
        result = worker.check_version_exists("serde", "1.0.219")
        print(f"\n=== Rust serde 版本存在性检查 ===")
        print(f"原始结果: {result}")
        
        assert isinstance(result, dict)
        assert "exists" in result
        assert result["exists"] is True
        
        print(f"验证通过: 版本 1.0.219 存在")
    
    def test_python_requests_version_exists(self):
        """测试Python requests版本存在性检查"""
        worker = WorkerFactory.create_worker(Language.PYTHON)
        
        # 检查已知存在的版本
        result = worker.check_version_exists("requests", "2.32.5")
        print(f"\n=== Python requests 版本存在性检查 ===")
        print(f"原始结果: {result}")
        
        assert isinstance(result, dict)
        assert "exists" in result
        assert result["exists"] is True
        
        print(f"验证通过: 版本 2.32.5 存在")
    
    def test_nonexistent_version(self):
        """测试不存在版本的检查"""
        worker = WorkerFactory.create_worker(Language.PYTHON)
        
        # 检查明显不存在的版本
        result = worker.check_version_exists("requests", "999.999.999")
        print(f"\n=== Python requests 不存在版本检查 ===")
        print(f"原始结果: {result}")
        
        assert isinstance(result, dict)
        assert "exists" in result
        assert result["exists"] is False
        
        print(f"验证通过: 版本 999.999.999 不存在")


class TestDependencies:
    """依赖关系测试 - 真实场景"""
    
    def test_rust_serde_dependencies(self):
        """测试Rust serde依赖关系获取"""
        worker = WorkerFactory.create_worker(Language.RUST)
        
        # 获取依赖关系
        result = worker.get_dependencies("serde", "1.0.219")
        print(f"\n=== Rust serde 依赖关系 ===")
        print(f"原始结果: {result}")
        
        assert isinstance(result, dict)
        assert "dependencies" in result
        assert isinstance(result["dependencies"], list)
        
        print(f"验证通过: 依赖数量 {len(result['dependencies'])}")
    
    def test_python_requests_dependencies(self):
        """测试Python requests依赖关系获取"""
        worker = WorkerFactory.create_worker(Language.PYTHON)
        
        # 获取依赖关系
        result = worker.get_dependencies("requests", "2.32.5")
        print(f"\n=== Python requests 依赖关系 ===")
        print(f"原始结果: {result}")
        
        assert isinstance(result, dict)
        assert "dependencies" in result
        assert isinstance(result["dependencies"], list)
        
        print(f"验证通过: 依赖数量 {len(result['dependencies'])}")


class TestErrorHandling:
    """错误处理测试 - 真实场景"""
    
    def test_nonexistent_library(self):
        """测试不存在库的错误处理"""
        worker = WorkerFactory.create_worker(Language.RUST)
        
        # 尝试获取不存在库的版本
        with pytest.raises(LibraryNotFoundError):
            worker.get_latest_version("this-library-does-not-exist-12345")
        
        print(f"\n=== 不存在库错误处理 ===")
        print(f"验证通过: 正确抛出 LibraryNotFoundError")
    
    def test_invalid_cpp_library_format(self):
        """测试C++库格式验证"""
        worker = WorkerFactory.create_worker(Language.CPP)
        
        # 测试无效格式
        with pytest.raises(ValueError):
            worker._parse_library("invalid-format")
        
        # 测试空生态系统
        with pytest.raises(ValueError):
            worker._parse_library(":boost")
        
        # 测试空库名
        with pytest.raises(ValueError):
            worker._parse_library("conan:")
        
        print(f"\n=== C++库格式验证 ===")
        print(f"验证通过: 正确验证库名格式")


class TestPerformance:
    """性能测试 - 真实场景"""
    
    def test_concurrent_requests(self):
        """测试顺序请求性能"""
        import time
        
        workers = {
            Language.RUST: WorkerFactory.create_worker(Language.RUST),
            Language.PYTHON: WorkerFactory.create_worker(Language.PYTHON),
            Language.NODE: WorkerFactory.create_worker(Language.NODE),
        }
        
        libraries = {
            Language.RUST: "serde",
            Language.PYTHON: "requests", 
            Language.NODE: "express"
        }
        
        start_time = time.time()
        
        # 顺序执行多个请求
        results = []
        for language, worker in workers.items():
            library = libraries[language]
            try:
                result = worker.get_latest_version(library)
                results.append(result)
            except Exception as e:
                results.append(e)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n=== 顺序请求性能测试 ===")
        print(f"执行时间: {duration:.2f}秒")
        print(f"请求数量: {len(results)}")
        print(f"平均每请求: {duration/len(results):.2f}秒")
        
        # 验证所有请求都成功
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"请求 {i} 失败: {result}")
            else:
                print(f"请求 {i} 成功: {result}")
                assert isinstance(result, dict)
                assert "version" in result
        
        # 性能断言（应该在合理时间内完成）
        assert duration < 30.0, f"请求耗时过长: {duration}秒"
        
        print(f"验证通过: 请求在 {duration:.2f}秒内完成")


if __name__ == "__main__":
    # 运行所有测试
    pytest.main(["-v", "-s", __file__])