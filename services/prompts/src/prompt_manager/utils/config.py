# Copyright (c) Kirky.X. 2025. All rights reserved.
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

import tomli


@dataclass
class SupabaseConfig:
    url: str
    key: str

    def __repr__(self):
        return f"SupabaseConfig(url='{self.url}', key='***')"

@dataclass
class DatabaseConfig:
    type: str
    path: Optional[str] = None
    pool_size: int = 10
    max_overflow: int = 20
    # Supabase configuration
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None
    # Optional direct connection string for DDL operations in Supabase mode
    connection_string: Optional[str] = None

    def __post_init__(self):
        if self.type == "supabase":
            if not self.supabase_url:
                raise ValueError("Supabase URL is required when database type is 'supabase'")
            if not self.supabase_key:
                raise ValueError("Supabase Key is required when database type is 'supabase'")
            if not self.supabase_url.startswith("https://"):
                raise ValueError("Supabase URL must start with 'https://'")

    def __repr__(self):
        return (
            f"DatabaseConfig(type='{self.type}', path={self.path}, "
            f"pool_size={self.pool_size}, max_overflow={self.max_overflow}, "
            f"supabase_url='{self.supabase_url}', supabase_key='***', "
            f"connection_string='***')"
        )


@dataclass
class VectorConfig:
    dimension: Optional[int] = None
    enabled: bool = False
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: Optional[str] = None
    provider_priority: str = "remote_first"
    local_model_id: Optional[str] = "BAAI/bge-m3"
    use_modelscope: bool = True
    batch_size: int = 12
    max_length: int = 8192


@dataclass
class Config:
    database: DatabaseConfig
    vector: VectorConfig
    cache: Dict[str, Any]
    concurrency: Dict[str, Any]
    logging: Dict[str, Any]
    api: Dict[str, Any]


def _replace_env_vars(config: Any) -> Any:
    """递归替换配置中的环境变量占位符

    将字典、列表及字符串中的 `${VAR}` 形式占位符替换为对应环境变量值，不存在时返回空字符串。

    Args:
        config (Any): 原始配置对象，可以是 `dict`、`list` 或 `str` 等类型。

    Returns:
        Any: 处理后的配置对象，结构与输入一致但变量已替换。

    Raises:
        None
    """
    if isinstance(config, dict):
        return {k: _replace_env_vars(v) for k, v in config.items()}
    if isinstance(config, list):
        return [_replace_env_vars(i) for i in config]
    if isinstance(config, str) and config.startswith("${") and config.endswith("}"):
        env_var = config[2:-1]
        return os.getenv(env_var, "")
    return config


def load_config(path: str = "config.toml") -> Config:
    """加载并解析项目配置文件

    从给定路径读取 TOML 配置文件，支持 `${ENV}` 环境变量占位符替换，并构造强类型配置对象。

    Args:
        path (str): 配置文件路径，默认为项目根目录的 `config.toml`。

    Returns:
        Config: 完整的项目配置对象，包含数据库、向量、缓存、并发、日志与 API 配置。

    Raises:
        FileNotFoundError: 当配置文件路径不存在时抛出。
        tomli.TOMLDecodeError: 当 TOML 内容解析失败时抛出。
        KeyError: 当必需的配置段缺失时抛出。
    """
    if not path.endswith(".toml"):
        raise FileNotFoundError(f"Config file not found at {path}")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found at {path}")

    with open(path, "rb") as f:
        raw = tomli.load(f)

    processed = _replace_env_vars(raw)

    return Config(
        database=DatabaseConfig(**processed["database"]),
        vector=VectorConfig(**processed["vector"]),
        cache=processed["cache"],
        concurrency=processed["concurrency"],
        logging=processed["logging"],
        api=processed["api"]
    )
