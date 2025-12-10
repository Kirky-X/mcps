# Copyright (c) Kirky.X. 2025. All rights reserved.
import os
import sys


def test_package_exports_importable():
    """验证包根导出函数可成功导入

    Args:
        None

    Returns:
        None
    """
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
    import prompt_manager as pm

    assert hasattr(pm, "__all__")
    for name in pm.__all__:
        assert hasattr(pm, name)


def test_logger_setup_and_get():
    """验证日志系统配置与获取记录器成功

    Args:
        None

    Returns:
        None
    """
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
    import prompt_manager as pm

    pm.setup_logging({"level": "INFO", "console_output": True})
    logger = pm.get_logger("test")
    logger.info("logger ok")


def test_load_config_missing_file_raises():
    """验证加载不存在的配置文件时抛出 FileNotFoundError

    Args:
        None

    Returns:
        None

    Raises:
        FileNotFoundError: 当路径不存在。
    """
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
    import prompt_manager as pm
    import pytest

    with pytest.raises(FileNotFoundError):
        pm.load_config("nonexistent.toml")
