"""
# Copyright (c) Kirky.X. 2025. All rights reserved.
"""
"""Prompt Manager 包

提供提示版本管理、向量索引检索、模板渲染与 API 服务的模块化能力。
"""

__all__ = [
    "load_config",
    "setup_logging",
    "get_logger",
]

from .utils.config import load_config
from .utils.logger import setup_logging, get_logger
