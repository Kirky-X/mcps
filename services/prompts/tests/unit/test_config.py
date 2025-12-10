"""
# Copyright (c) Kirky.X. 2025. All rights reserved.
"""
import os

from prompt_manager.utils.config import load_config


def test_load_toml_config(tmp_path):
    """验证加载 TOML 配置并替换环境变量占位符

    Args:
        tmp_path (pathlib.Path): pytest 提供的临时目录路径。

    Returns:
        None

    Raises:
        AssertionError: 当解析结果与预期不符时抛出。
    """
    config_content = """
    [database]
    type = "sqlite"
    path = "test.db"

    [vector]
    enabled = true
    dimension = 1536
    embedding_model = "ada"
    embedding_api_key = "${TEST_API_KEY}"

    [cache]
    enabled = false

    [concurrency]
    queue_enabled = false

    [logging]
    level = "DEBUG"

    [api.http]
    enabled = true
    """

    d = tmp_path / "config.toml"
    d.write_text(config_content, encoding="utf-8")

    # Set env var
    os.environ["TEST_API_KEY"] = "secret-key-123"

    config = load_config(str(d))

    assert config.database.type == "sqlite"
    assert config.vector.embedding_api_key == "secret-key-123"
    assert config.cache["enabled"] is False
