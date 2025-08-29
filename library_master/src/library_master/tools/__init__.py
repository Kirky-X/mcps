"""MCP工具定义模块"""

from mcp.types import Tool
from typing import List
from .context7_tools import create_context7_tools
from ..core.config import Settings


def get_tool_definitions(settings: Settings = None) -> List[Tool]:
    """获取所有工具定义
    
    Args:
        settings: 配置对象
        
    Returns:
        所有 MCP 工具定义列表
    """
    tools = [
        Tool(
            name="find_latest_versions",
            description="批量查询多个库的最新版本信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "libraries": {
                        "type": "array",
                        "description": "库列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "库名称"
                                },
                                "language": {
                                    "type": "string",
                                    "enum": ["rust", "python", "java", "node"],
                                    "description": "编程语言"
                                }
                            },
                            "required": ["name", "language"]
                        }
                    }
                },
                "required": ["libraries"]
            }
        ),
        Tool(
            name="find_library_docs",
            description="批量查询多个库的文档链接",
            inputSchema={
                "type": "object",
                "properties": {
                    "libraries": {
                        "type": "array",
                        "description": "库列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "库名称"
                                },
                                "language": {
                                    "type": "string",
                                    "enum": ["rust", "python", "java", "node"],
                                    "description": "编程语言"
                                },
                                "version": {
                                    "type": "string",
                                    "description": "版本号（可选）"
                                }
                            },
                            "required": ["name", "language"]
                        }
                    }
                },
                "required": ["libraries"]
            }
        ),
        Tool(
            name="check_versions_exist",
            description="批量检查指定版本的库是否存在",
            inputSchema={
                "type": "object",
                "properties": {
                    "libraries": {
                        "type": "array",
                        "description": "库列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "库名称"
                                },
                                "language": {
                                    "type": "string",
                                    "enum": ["rust", "python", "java", "node"],
                                    "description": "编程语言"
                                },
                                "version": {
                                    "type": "string",
                                    "description": "版本号"
                                }
                            },
                            "required": ["name", "language", "version"]
                        }
                    }
                },
                "required": ["libraries"]
            }
        ),
        Tool(
            name="find_library_dependencies",
            description="批量查询多个库的依赖关系",
            inputSchema={
                "type": "object",
                "properties": {
                    "libraries": {
                        "type": "array",
                        "description": "库列表",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "库名称"
                                },
                                "language": {
                                    "type": "string",
                                    "enum": ["rust", "python", "java", "node"],
                                    "description": "编程语言"
                                },
                                "version": {
                                    "type": "string",
                                    "description": "版本号（可选）"
                                }
                            },
                            "required": ["name", "language"]
                        }
                    }
                },
                "required": ["libraries"]
            }
        ),
        Tool(
            name="get_cache_stats",
            description="获取缓存统计信息",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="clear_cache",
            description="清空所有缓存",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        )
    ]
    
    # 添加 Context7 工具（如果配置了 API 密钥）
    if settings and getattr(settings, 'context7_api_key', None):
        try:
            context7_tools = create_context7_tools(settings)
            tools.extend(context7_tools.get_tool_definitions())
        except Exception as e:
            # 如果 Context7 工具初始化失败，记录警告但不影响其他工具
            import logging
            logging.warning(f"Failed to initialize Context7 tools: {e}")
    
    return tools