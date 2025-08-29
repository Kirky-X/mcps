#!/usr/bin/env python3
"""
MCP LibraryMaster - 多语言代码包查询服务主入口
"""

import asyncio
import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .core.server import LibraryMasterServer
from .core.config import Settings


def setup_logging(level: str = "INFO") -> None:
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def main() -> None:
    """主函数"""
    # 加载配置
    settings = Settings()
    
    # 设置日志
    setup_logging(settings.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting MCP LibraryMaster Server...")
    
    try:
        # 创建并启动服务器
        server = LibraryMasterServer(settings)
        server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())