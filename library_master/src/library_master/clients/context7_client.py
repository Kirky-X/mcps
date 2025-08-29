"""Context7 API 客户端

提供与 Context7 API 的集成，支持库搜索和文档查询功能。
基于 Context7 API 文档实现：https://context7.com/api/v1
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode
from ..core.config import Settings


class Context7Client:
    """Context7 API 客户端
    
    提供库搜索和文档查询功能的接口。
    严格按照 Context7 API 文档实现。
    """
    
    def __init__(self, settings: Settings = None):
        """初始化 Context7 客户端
        
        Args:
            settings: 配置对象
        """
        if settings is None:
            settings = Settings()
            
        self.api_key = settings.context7_api_key
        self.base_url = settings.context7_base_url
        self.timeout = settings.request_timeout
        
        if not self.api_key:
            raise ValueError("Context7 API key is required")
            
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "LibraryMaster/0.1.1"
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def search(self, query: str, language: str = None, limit: int = 10) -> dict:
        """搜索库
        
        Args:
            query: 搜索查询字符串
            language: 编程语言过滤（可选）
            limit: 返回结果数量限制
            
        Returns:
            搜索结果字典
        """
        params = {"query": query}
        if language:
            params["language"] = language
        if limit:
            params["limit"] = limit
            
        url = f"{self.base_url}/search?{urlencode(params)}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            self.logger.error(f"Context7 search API error: {e}")
            raise
    
    async def get_docs(self, library_path: str, doc_type: str = "txt", topic: str = None, tokens: int = 5000) -> str:
        """获取库文档
        
        Args:
            library_path: 库路径，格式为 username/library 或 library
            doc_type: 文档类型，默认为 "txt"
            topic: 主题过滤（可选）
            tokens: 返回的 token 数量限制
            
        Returns:
            文档内容字符串
        """
        params = {"type": doc_type}
        if topic:
            params["topic"] = topic
        if tokens:
            params["tokens"] = tokens
            
        url = f"{self.base_url}/{library_path}?{urlencode(params)}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.text
        except Exception as e:
            self.logger.error(f"Context7 docs API error: {e}")
            raise
    

    
    async def health_check(self) -> dict:
        """健康检查
        
        通过执行一个简单的搜索请求来检查 API 是否可用。
        
        Returns:
            健康状态信息
        """
        try:
            result = await self.search(query="test", limit=1)
            return {
                "status": "healthy",
                "api_accessible": True,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "api_accessible": False,
                "error": str(e),
                "timestamp": "2024-01-01T00:00:00Z"
            }
    
    def __repr__(self) -> str:
        return f"Context7Client(base_url='{self.base_url}')"