"""Context7 客户端

提供与 Context7 MCP 服务器的集成，支持库搜索和文档查询功能。
注意：Context7 是一个 MCP 服务器，不是 REST API。
这个实现提供了一个兼容的接口用于测试和开发。
"""

import asyncio
import logging
from typing import Optional
from urllib.parse import urlencode
import httpx

from ..core.config import Settings


class Context7Client:
    """Context7 客户端
    
    提供库搜索和文档查询功能的接口。
    注意：这是一个兼容实现，因为 Context7 实际上是 MCP 服务器。
    """
    
    def __init__(self, settings: Settings = None):
        """初始化 Context7 客户端
        
        Args:
            settings: 配置对象
        """
        if settings is None:
            settings = Settings()
            
        self.api_key = settings.context7_api_key
        self.base_url = settings.context7_base_url or "https://context7.com/api/v1"
        self.timeout = settings.request_timeout
        
        # HTTP客户端配置
        self.max_retries = 3
        self.retry_delay = 1.0
        self.backoff_factor = 2.0
        
        # 设置请求头
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            
        self.logger = logging.getLogger(__name__)
        
        # Mock数据用于测试
        self._mock_libraries = {
            "requests": {
                "name": "requests",
                "description": "Python HTTP library",
                "language": "python",
                "version": "2.31.0",
                "docs": "Requests is a simple, yet elegant HTTP library for Python."
            },
            "express": {
                "name": "express",
                "description": "Fast, unopinionated, minimalist web framework for Node.js",
                "language": "javascript",
                "version": "4.18.2",
                "docs": "Express is a minimal and flexible Node.js web application framework."
            },
            "tokio": {
                "name": "tokio",
                "description": "A runtime for writing reliable asynchronous applications with Rust",
                "language": "rust",
                "version": "1.35.0",
                "docs": "Tokio is an asynchronous runtime for the Rust programming language."
            }
        }
    
    async def _make_request_with_retry(self, url: str, method: str = "GET") -> httpx.Response:
        """带重试机制的HTTP请求
        
        Args:
            url: 请求URL
            method: HTTP方法
            
        Returns:
            HTTP响应对象
            
        Raises:
            httpx.HTTPStatusError: 最终请求失败
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method.upper() == "GET":
                        response = await client.get(url, headers=self.headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    response.raise_for_status()
                    return response
                    
            except httpx.HTTPStatusError as e:
                last_exception = e
                
                # 对于某些错误码，不进行重试
                if e.response.status_code in [400, 401, 403, 404]:
                    self.logger.error(f"Non-retryable error {e.response.status_code}: {e}")
                    raise
                
                # 对于429 (Too Many Requests) 和 5xx 错误，进行重试
                if e.response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (self.backoff_factor ** attempt)
                        self.logger.warning(
                            f"Request failed with {e.response.status_code}, retrying in {delay:.1f}s "
                            f"(attempt {attempt + 1}/{self.max_retries + 1})"
                        )
                        await asyncio.sleep(delay)
                        continue
                
                # 其他HTTP错误直接抛出
                raise
                
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (self.backoff_factor ** attempt)
                    self.logger.warning(
                        f"Network error: {e}, retrying in {delay:.1f}s "
                        f"(attempt {attempt + 1}/{self.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue
                
                # 最后一次尝试失败，抛出异常
                self.logger.error(f"Request failed after {self.max_retries + 1} attempts: {e}")
                raise
        
        # 如果所有重试都失败了，抛出最后一个异常
        if last_exception:
            raise last_exception
    
    async def _simulate_delay(self):
        """模拟网络延迟"""
        await asyncio.sleep(0.1)  # 100ms 延迟模拟网络请求
    
    async def search(self, query: str, language: Optional[str] = None) -> dict:
        """搜索库
        
        Args:
            query: 搜索查询
            language: 编程语言过滤
            
        Returns:
            搜索结果字典
        """
        # 如果没有API key，使用mock数据
        if not self.api_key:
            await self._simulate_delay()
            
            # 模拟搜索逻辑
            results = []
            query_lower = query.lower()
            
            for lib_name, lib_info in self._mock_libraries.items():
                # 检查查询是否匹配库名或描述
                if (query_lower in lib_name.lower() or 
                    query_lower in lib_info["description"].lower()):
                    
                    # 如果指定了语言，进行过滤
                    if language is None or lib_info["language"].lower() == language.lower():
                        results.append({
                            "name": lib_info["name"],
                            "description": lib_info["description"],
                            "language": lib_info["language"],
                            "version": lib_info["version"]
                        })
            
            return {
                "results": results,
                "total": len(results),
                "query": query,
                "language": language
            }
        
        # 使用真实API
        try:
            # 构建查询参数 - 根据文档，只需要query参数
            params = {"query": query}
            
            # 构建URL
            url = f"{self.base_url}/search?{urlencode(params)}"
            
            # 发送请求
            response = await self._make_request_with_retry(url)
            result = response.json()
            
            # 如果指定了语言过滤，在客户端进行过滤
            if language and "results" in result:
                filtered_results = []
                for item in result["results"]:
                    # 根据查询内容判断语言匹配
                    if self._matches_language(item, language):
                        filtered_results.append(item)
                result["results"] = filtered_results
            
            return result
            
        except Exception as e:
            self.logger.error(f"Search request failed: {e}")
            # 如果API请求失败，回退到mock数据
            # 临时设置api_key为None以使用mock逻辑
            original_api_key = self.api_key
            self.api_key = None
            try:
                result = await self.search(query, language)
                return result
            finally:
                self.api_key = original_api_key
    
    def _matches_language(self, item: dict, language: str) -> bool:
        """检查搜索结果项是否匹配指定语言"""
        # 简单的语言匹配逻辑，可以根据需要扩展
        title = item.get("title", "").lower()
        description = item.get("description", "").lower()
        
        language_keywords = {
            "python": ["python", "py", "pip"],
            "javascript": ["javascript", "js", "node", "npm"],
            "typescript": ["typescript", "ts"],
            "rust": ["rust", "cargo"],
            "go": ["go", "golang"],
            "java": ["java", "maven"],
            "cpp": ["c++", "cpp", "cmake"],
            "c": ["c", "gcc"]
        }
        
        keywords = language_keywords.get(language.lower(), [language.lower()])
        return any(keyword in title or keyword in description for keyword in keywords)
    
    async def get_docs(self, library_path: str, doc_type: str = "txt", topic: str = None, tokens: int = 5000) -> str:
        """获取库文档
        
        Args:
            library_path: 库路径
            doc_type: 文档类型
            topic: 主题
            tokens: 令牌数量
            
        Returns:
            文档内容字符串
        """
        # 如果没有API key，使用mock数据
        if not self.api_key:
            await self._simulate_delay()
            
            # 检查库是否存在
            if library_path not in self._mock_libraries:
                return f"Library '{library_path}' not found."
            
            lib_info = self._mock_libraries[library_path]
            
            # 生成mock文档内容
            docs = f"# {lib_info['name']} Documentation\n\n"
            docs += f"## Overview\n{lib_info['description']}\n\n"
            docs += f"## Installation\n{self._get_install_command(lib_info['language'], lib_info['name'])}\n\n"
            docs += f"## Basic Usage\n{self._get_usage_example(lib_info['name'], lib_info['language'])}\n\n"
            docs += f"## Version\n{lib_info['version']}\n\n"
            
            if topic:
                docs += f"## {topic.title()}\nSpecific documentation for {topic} topic.\n\n"
            
            # 根据tokens参数调整内容长度
            if tokens < 1000:
                docs = docs[:tokens]
            elif tokens > 5000:
                docs += "## Advanced Features\nDetailed advanced features and examples...\n\n"
                docs += "## API Reference\nComplete API reference documentation...\n\n"
            
            return docs
        
        # 使用真实API
        try:
            # 构建查询参数
            params = {}
            if doc_type:
                params["type"] = doc_type
            if topic:
                params["topic"] = topic
            if tokens:
                params["tokens"] = tokens
            
            # 对于简单的库名，我们需要找到对应的完整路径
            # 首先尝试通过搜索找到正确的ID
            if "/" not in library_path:
                try:
                    # 先搜索这个库来获取正确的ID
                    search_result = await self.search(library_path)
                    if search_result.get("results"):
                        # 使用第一个搜索结果的ID
                        library_id = search_result["results"][0].get("id", "")
                        if library_id.startswith("/"):
                            library_path = library_id[1:]  # 去掉开头的斜杠
                        else:
                            library_path = library_id
                    else:
                        # 如果搜索没有结果，使用默认格式
                        library_path = f"websites/pypi_org_project_{library_path}"
                except:
                    # 如果搜索失败，使用默认格式
                    library_path = f"websites/pypi_org_project_{library_path}"
            
            # URL编码路径中的特殊字符
            library_path = library_path.replace("/", "%2F")
            
            # 构建URL - 库名作为路径的一部分，按照文档格式
            url = f"{self.base_url}/{library_path}?{urlencode(params)}"
            
            # 发送请求
            response = await self._make_request_with_retry(url)
            return response.text
            
        except Exception as e:
            self.logger.error(f"Get docs request failed: {e}")
            # 如果API请求失败，回退到mock数据
            # 临时设置api_key为None以使用mock逻辑
            original_api_key = self.api_key
            self.api_key = None
            try:
                result = await self.get_docs(library_path, doc_type, topic, tokens)
                return result
            finally:
                self.api_key = original_api_key
    

    
    def _get_install_command(self, language: str, library_name: str) -> str:
        """获取安装命令"""
        commands = {
            "python": f"pip install {library_name}",
            "javascript": f"npm install {library_name}",
            "rust": f"cargo add {library_name}"
        }
        return commands.get(language, f"# Install {library_name}")
    
    def _get_usage_example(self, language: str, library_name: str) -> str:
        """获取使用示例"""
        examples = {
            "python": f"import {library_name}\n# Use {library_name} here",
            "javascript": f"const {library_name} = require('{library_name}');\n// Use {library_name} here",
            "rust": f"use {library_name};\n// Use {library_name} here"
        }
        return examples.get(language, f"// Use {library_name}")
    
    async def health_check(self) -> dict:
        """健康检查
        
        Returns:
            健康状态字典
        """
        # 如果没有API key，使用mock数据
        if not self.api_key:
            await self._simulate_delay()
            
            return {
                "status": "healthy",
                "service": "context7",
                "version": "1.0.0",
                "timestamp": "2024-01-01T00:00:00Z",
                "available_libraries": len(self._mock_libraries)
            }
        
        # 使用真实API - 尝试调用search端点来检查服务状态
        try:
            # 使用一个简单的搜索请求来检查API是否可用
            url = f"{self.base_url}/search?{urlencode({'query': 'test'})}"
            
            # 发送请求
            response = await self._make_request_with_retry(url)
            result = response.json()
            
            return {
                "status": "healthy",
                "service": "context7",
                "version": "1.0.0",
                "timestamp": "2024-01-01T00:00:00Z",
                "api_available": True,
                "results_count": len(result.get("results", []))
            }
            
        except Exception as e:
            self.logger.error(f"Health check request failed: {e}")
            # 如果API请求失败，回退到mock数据
            await self._simulate_delay()
            return {
                "status": "degraded",
                "service": "context7",
                "version": "1.0.0",
                "timestamp": "2024-01-01T00:00:00Z",
                "error": str(e),
                "fallback": True
            }
    
    def __repr__(self) -> str:
        return f"Context7Client(base_url='{self.base_url}')"