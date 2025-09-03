"""Context7 MCP 工具定义

提供基于 Context7 API 的库搜索和文档查询工具。
"""

from mcp.types import Tool
from typing import List, Dict, Any
import logging
from ..clients.context7_client import Context7Client
from ..core.config import Settings


class Context7Tools:
    """Context7 工具集
    
    提供库搜索、文档查询和示例获取功能。
    """
    
    def __init__(self, settings: Settings = None):
        """初始化 Context7 工具集
        
        Args:
            settings: 配置对象
        """
        self.settings = settings or Settings()
        self.client = Context7Client(self.settings)
        self.logger = logging.getLogger(__name__)
    
    def get_tool_definitions(self) -> List[Tool]:
        """获取 Context7 工具定义
        
        Returns:
            Context7 MCP 工具列表
        """
        return [
            Tool(
                name="search_libraries",
                description="使用 Context7 API 搜索相关的库和代码示例",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索查询字符串"
                        },
                        "language": {
                            "type": "string",
                            "enum": ["rust", "python", "java", "node", "go", "cpp"],
                            "description": "编程语言（可选）"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回结果数量限制（可选，默认10）",
                            "minimum": 1,
                            "maximum": 50
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="get_library_docs",
                description="使用 Context7 API 获取指定库的文档",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "library_path": {
                            "type": "string",
                            "description": "库路径，格式为 username/library 或 library"
                        },
                        "doc_type": {
                            "type": "string",
                            "description": "文档类型（可选）",
                            "enum": ["readme", "api", "tutorial", "examples"]
                        },
                        "topic": {
                            "type": "string",
                            "description": "特定主题（可选）"
                        },
                        "tokens": {
                            "type": "integer",
                            "description": "返回的 token 数量限制（可选）",
                            "minimum": 100,
                            "maximum": 10000
                        }
                    },
                    "required": ["library_path"]
                }
            ),

            Tool(
                name="context7_health_check",
                description="检查 Context7 API 服务状态",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False
                }
            )
        ]
    
    async def search_libraries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """搜索库和代码示例
        
        Args:
            arguments: 工具参数
            
        Returns:
            搜索结果
        """
        try:
            query = arguments["query"]
            language = arguments.get("language")
            limit = arguments.get("limit", 10)
            
            self.logger.info(f"Searching libraries with query: {query}")
            
            result = await self.client.search(
                query=query,
                language=language
            )
            
            return {
                "success": True,
                "data": result,
                "message": f"Found {len(result.get('results', []))} results for query: {query}"
            }
            
        except Exception as e:
            self.logger.error(f"Error searching libraries: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to search libraries"
            }
    
    async def get_library_docs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """获取库文档
        
        Args:
            arguments: 工具参数
            
        Returns:
            文档内容
        """
        try:
            library_path = arguments["library_path"]
            doc_type = arguments.get("doc_type")
            topic = arguments.get("topic")
            tokens = arguments.get("tokens")
            
            self.logger.info(f"Getting documentation for {library_path}")
            
            result = await self.client.get_docs(
                library_path=library_path,
                doc_type=doc_type,
                topic=topic,
                tokens=tokens
            )
            
            return {
                "success": True,
                "data": result,
                "message": f"Successfully retrieved documentation for {library_path}"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting documentation: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to get documentation"
            }
    

    
    async def context7_health_check(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """检查 Context7 API 健康状态
        
        Args:
            arguments: 工具参数（空）
            
        Returns:
            健康检查结果
        """
        try:
            self.logger.info("Checking Context7 API health")
            
            is_healthy = await self.client.health_check()
            
            return {
                "success": True,
                "data": {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "api_url": self.client.base_url,
                    "timestamp": self._get_current_timestamp()
                },
                "message": f"Context7 API is {'healthy' if is_healthy else 'unhealthy'}"
            }
            
        except Exception as e:
            self.logger.error(f"Error checking Context7 health: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to check Context7 API health"
            }
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳
        
        Returns:
            ISO 格式的时间戳
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def __repr__(self) -> str:
        return f"Context7Tools(api_url='{self.client.base_url}')"


# 工具实例化函数
def create_context7_tools(settings: Settings = None) -> Context7Tools:
    """创建 Context7 工具实例
    
    Args:
        settings: 配置对象
        
    Returns:
        Context7Tools 实例
        
    Raises:
        ValueError: 当没有提供 Context7 API 密钥时
    """
    if settings is None:
        settings = Settings()
    
    # 检查是否提供了 API 密钥
    if not settings.context7_api_key:
        raise ValueError("Context7 API key is required but not provided in settings")
    
    return Context7Tools(settings)