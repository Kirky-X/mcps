"""MCP LibraryMaster服务器"""

import logging
from typing import List, Dict, Any

from mcp.server.fastmcp import FastMCP
from mcp.types import Tool

from .config import Settings
from .processor import BatchProcessor
from ..models import LibraryQuery, BatchRequest, Language
from ..tools import get_tool_definitions
from ..tools.context7_tools import create_context7_tools


class LibraryMasterServer:
    """MCP LibraryMaster服务器主类"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        self.mcp = FastMCP(settings.server_name)
        self.batch_processor = BatchProcessor(
            max_workers=settings.max_workers,
            request_timeout=settings.request_timeout,
            cache_ttl=settings.cache_ttl,
            cache_max_size=settings.cache_max_size
        )
        
        # 初始化 Context7 工具（如果配置了 API 密钥）
        self.context7_tools = None
        if getattr(settings, 'context7_api_key', None):
            try:
                self.context7_tools = create_context7_tools(settings)
                self.logger.info("Context7 tools initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Context7 tools: {e}")
        
        self._register_tools()
    
    def _register_tools(self):
        """注册MCP工具"""
        # 直接使用装饰器注册工具
        
        @self.mcp.tool()
        async def find_latest_versions(libraries: List[Dict[str, str]]) -> Dict[str, Any]:
            """批量查询最新版本"""
            return await self.find_latest_versions(libraries)
        
        @self.mcp.tool()
        async def find_library_docs(libraries: List[Dict[str, str]]) -> Dict[str, Any]:
            """批量查询文档链接"""
            return await self.find_library_docs(libraries)
        
        @self.mcp.tool()
        async def check_versions_exist(libraries: List[Dict[str, str]]) -> Dict[str, Any]:
            """批量检查版本存在性"""
            return await self.check_versions_exist(libraries)
        
        @self.mcp.tool()
        async def find_library_dependencies(libraries: List[Dict[str, str]]) -> Dict[str, Any]:
            """批量查询依赖关系"""
            return await self.find_library_dependencies(libraries)
        
        @self.mcp.tool()
        async def get_cache_stats() -> Dict[str, Any]:
            """获取缓存统计信息"""
            return await self.get_cache_stats()
        
        @self.mcp.tool()
        async def clear_cache() -> Dict[str, Any]:
            """清空缓存"""
            return await self.clear_cache()
        
        # 注册 Context7 工具（如果已初始化）
        if self.context7_tools:
            self._register_context7_tools()
    
    def _register_context7_tools(self):
        """注册 Context7 MCP 工具"""
        
        @self.mcp.tool()
        async def generate_code_example(library_name: str, language: str, description: str = "") -> Dict[str, Any]:
            """生成代码示例"""
            return await self.context7_tools.generate_code_example(library_name, language, description)
        
        @self.mcp.tool()
        async def query_library_documentation(library_name: str, language: str, query: str) -> Dict[str, Any]:
            """查询库文档"""
            return await self.context7_tools.query_library_documentation(library_name, language, query)
        
        @self.mcp.tool()
        async def get_library_examples(library_name: str, language: str, example_type: str = "basic") -> Dict[str, Any]:
            """获取库示例"""
            return await self.context7_tools.get_library_examples(library_name, language, example_type)
        
        @self.mcp.tool()
        async def context7_health_check() -> Dict[str, Any]:
            """Context7 健康检查"""
            return await self.context7_tools.context7_health_check()
    
    async def find_latest_versions(self, libraries: List[Dict[str, str]]) -> Dict[str, Any]:
        """批量查询最新版本
        
        Args:
            libraries: 库列表，格式: [{"name": "库名", "language": "语言"}]
        
        Returns:
            批量查询结果
        """
        try:
            library_queries = [
                LibraryQuery(name=lib["name"], language=Language(lib["language"]), version=None)
                for lib in libraries
            ]
            
            response = await self.batch_processor.process_batch(
                library_queries, "find_latest_versions"
            )
            
            return response.model_dump()
            
        except Exception as e:
            self.logger.error(f"Error in find_latest_versions: {e}")
            return {"error": str(e)}
    
    async def find_library_docs(self, libraries: List[Dict[str, str]]) -> Dict[str, Any]:
        """批量查询文档链接
        
        Args:
            libraries: 库列表，格式: [{"name": "库名", "language": "语言", "version": "版本"}]
        
        Returns:
            批量查询结果
        """
        try:
            library_queries = [
                LibraryQuery(
                    name=lib["name"], 
                    language=Language(lib["language"]),
                    version=lib.get("version")
                )
                for lib in libraries
            ]
            
            response = await self.batch_processor.process_batch(
                library_queries, "find_library_docs"
            )
            
            return response.model_dump()
            
        except Exception as e:
            self.logger.error(f"Error in find_library_docs: {e}")
            return {"error": str(e)}
    
    async def check_versions_exist(self, libraries: List[Dict[str, str]]) -> Dict[str, Any]:
        """批量检查版本存在性
        
        Args:
            libraries: 库列表，格式: [{"name": "库名", "language": "语言", "version": "版本"}]
        
        Returns:
            批量查询结果
        """
        try:
            library_queries = [
                LibraryQuery(
                    name=lib["name"], 
                    language=Language(lib["language"]),
                    version=lib["version"]
                )
                for lib in libraries
            ]
            
            response = await self.batch_processor.process_batch(
                library_queries, "check_versions_exist"
            )
            
            return response.model_dump()
            
        except Exception as e:
            self.logger.error(f"Error in check_versions_exist: {e}")
            return {"error": str(e)}
    
    async def find_library_dependencies(self, libraries: List[Dict[str, str]]) -> Dict[str, Any]:
        """批量查询依赖关系
        
        Args:
            libraries: 库列表，格式: [{"name": "库名", "language": "语言", "version": "版本"}]
        
        Returns:
            批量查询结果
        """
        try:
            library_queries = [
                LibraryQuery(
                    name=lib["name"], 
                    language=Language(lib["language"]),
                    version=lib.get("version")
                )
                for lib in libraries
            ]
            
            response = await self.batch_processor.process_batch(
                library_queries, "find_library_dependencies"
            )
            
            return response.model_dump()
            
        except Exception as e:
            self.logger.error(f"Error in find_library_dependencies: {e}")
            return {"error": str(e)}
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        try:
            return self.batch_processor.get_cache_stats()
        except Exception as e:
            self.logger.error(f"Error in get_cache_stats: {e}")
            return {"error": str(e)}
    
    async def clear_cache(self) -> Dict[str, Any]:
        """清空缓存
        
        Returns:
            操作结果
        """
        try:
            self.batch_processor.clear_cache()
            return {"success": True, "message": "Cache cleared successfully"}
        except Exception as e:
            self.logger.error(f"Error in clear_cache: {e}")
            return {"error": str(e)}
    
    def run(self, shutdown_event=None):
        """运行服务器"""
        self.logger.info(f"Starting {self.settings.server_name} server...")
        if shutdown_event:
            # 如果提供了shutdown_event，等待它被设置
            import asyncio
            try:
                asyncio.run(shutdown_event.wait())
            except Exception:
                pass
            finally:
                self.logger.info("Server shutdown initiated")
        else:
            # FastMCP的run方法是同步的，直接调用
            try:
                self.mcp.run(transport="stdio")
            except KeyboardInterrupt:
                self.logger.info("Server stopped by user")
            except Exception as e:
                self.logger.error(f"Server error: {e}")
                raise