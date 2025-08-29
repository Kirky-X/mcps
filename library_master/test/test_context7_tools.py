"""Context7 工具测试模块

测试 Context7 API 集成和工具功能。
"""

import unittest
import pytest
from unittest.mock import Mock, AsyncMock, patch

from librarymaster.tools.context7_tools import Context7Tools, create_context7_tools
from librarymaster.clients.context7_client import Context7Client
from librarymaster.core.config import Settings


class TestContext7Tools(unittest.TestCase):
    """Context7 工具测试类"""
    
    def setUp(self):
        """测试前设置"""
        # 创建模拟的设置对象
        self.mock_settings = Mock()
        self.mock_settings.context7_api_key = "test_api_key"
        self.mock_settings.context7_base_url = "https://api.context7.test"
        
        # 启动 patch
        self.client_patcher = patch('librarymaster.tools.context7_tools.Context7Client')
        self.mock_client_class = self.client_patcher.start()
        self.mock_client = Mock(spec=Context7Client)
        self.mock_client_class.return_value = self.mock_client
        
        self.context7_tools = Context7Tools(self.mock_settings)
    
    def tearDown(self):
        """测试后清理"""
        self.client_patcher.stop()
    
    @pytest.mark.asyncio
    async def test_search_libraries_success(self):
        """测试成功搜索库"""
        # 设置模拟返回值
        expected_response = {
            "results": [
                {
                    "library": "requests",
                    "description": "HTTP library for Python",
                    "score": 0.95
                }
            ]
        }
        self.mock_client.search = AsyncMock(return_value=expected_response)
        
        # 调用方法
        result = await self.context7_tools.search_libraries({
            "query": "http client python",
            "language": "python",
            "limit": 10
        })
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], expected_response)
        self.mock_client.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_libraries_error(self):
        """测试库搜索错误处理"""
        # 设置模拟异常
        self.mock_client.search = AsyncMock(side_effect=Exception("API Error"))
        
        # 调用方法
        result = await self.context7_tools.search_libraries({
            "query": "http client python",
            "language": "python",
            "limit": 10
        })
        
        # 验证错误处理
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error"], "API Error")
    
    @pytest.mark.asyncio
    async def test_get_library_docs_success(self):
        """测试成功获取库文档"""
        # 设置模拟返回值
        expected_response = "Requests library documentation for authentication..."
        self.mock_client.get_docs = AsyncMock(return_value=expected_response)
        
        # 调用方法
        result = await self.context7_tools.get_library_docs({
            "library_path": "requests",
            "doc_type": "api",
            "topic": "authentication",
            "tokens": 1000
        })
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], expected_response)
        self.mock_client.get_docs.assert_called_once()
    

    
    @pytest.mark.asyncio
    async def test_context7_health_check_success(self):
        """测试健康检查"""
        # 设置模拟返回值
        expected_response = {
            "status": "healthy",
            "version": "1.0.0",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        self.mock_client.health_check = AsyncMock(return_value=expected_response)
        
        # 调用方法
        result = await self.context7_tools.context7_health_check({})
        
        # 验证结果
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], expected_response)
        self.mock_client.health_check.assert_called_once()
    
    def test_get_tool_definitions(self):
        """测试获取工具定义"""
        tools = self.context7_tools.get_tool_definitions()
        
        # 验证工具数量和名称
        self.assertEqual(len(tools), 3)
        tool_names = [tool.name for tool in tools]
        expected_names = [
            "search_libraries",
            "get_library_docs", 
            "context7_health_check"
        ]
        self.assertEqual(tool_names, expected_names)


class TestContext7ToolsFactory(unittest.TestCase):
    """Context7 工具工厂函数测试类"""
    
    @patch('librarymaster.tools.context7_tools.Context7Client')
    def test_create_context7_tools_success(self, mock_client_class):
        """测试工厂函数成功创建工具"""
        settings = Settings(
            context7_api_key="test_api_key",
            context7_base_url="https://api.context7.test"
        )
        
        # 创建工具实例
        tools = create_context7_tools(settings)
        
        # 验证实例类型
        self.assertIsInstance(tools, Context7Tools)
        self.assertEqual(tools.settings, settings)
        
        # 验证客户端被正确初始化
        mock_client_class.assert_called_once_with(settings)
    
    def test_create_context7_tools_no_api_key(self):
        """测试没有 API 密钥时的处理"""
        settings = Settings()  # 没有 context7_api_key
        
        # 应该抛出异常或返回 None
        with self.assertRaises((ValueError, AttributeError)):
            create_context7_tools(settings)


class TestContext7ToolsIntegration(unittest.TestCase):
    """Context7 工具集成测试类"""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_full_workflow(self, mock_httpx_client):
        """测试完整工作流程"""
        # 设置模拟 HTTP 响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "library": "requests",
                    "description": "HTTP library for Python",
                    "score": 0.95
                }
            ]
        }
        mock_httpx_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        # 创建设置和工具
        settings = Settings(
            context7_api_key="test_api_key",
            context7_base_url="https://api.context7.test"
        )
        tools = create_context7_tools(settings)
        
        # 测试库搜索
        result = await tools.search_libraries({
            "query": "http client",
            "language": "python",
            "limit": 10
        })
        
        self.assertIn("success", result)


if __name__ == "__main__":
    unittest.main()