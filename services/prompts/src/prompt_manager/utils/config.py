# Copyright (c) Kirky.X. 2025. All rights reserved.
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json
import pathlib

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
    prompt: Optional[Dict[str, Any]] = None


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


def _bootstrap_config(path: str) -> Dict[str, Any]:
    p = pathlib.Path(path)
    d = {
        "database": {
            "type": "sqlite",
            "path": "${PROMPT_MANAGER_DB_PATH}",
            "pool_size": 10,
            "max_overflow": 20,
        },
        "cache": {
            "enabled": True,
            "type": "filesystem",
            "max_capacity": 1000,
            "ttl_seconds": 3600,
            "idle_timeout_seconds": 1800,
            "dir": "${PROMPT_MANAGER_CACHE_DIR}",
        },
        "concurrency": {
            "queue_enabled": True,
            "queue_max_size": 100,
            "optimistic_lock_enabled": True,
        },
        "vector": {
            "enabled": True,
            "embedding_model": "text-embedding-3-small",
            "embedding_api_key": "${OPENAI_API_KEY}",
            "provider_priority": "remote_first",
            "local_model_id": "BAAI/bge-m3",
            "use_modelscope": True,
            "batch_size": 12,
            "max_length": 8192,
        },
        "logging": {
            "level": "INFO",
            "file_path": "./prompt_manager.log",
            "max_size_mb": 10,
            "backup_count": 5,
            "console_output": True,
        },
        "api": {
            "http": {
                "enabled": True,
                "host": "0.0.0.0",
                "port": 8000,
            }
        },
        "prompt": {
            "text": "${PROMPT_MANAGER_PROMPT}",
            "namespace": "default",
            "tags": [],
        }
    }
    import tomli_w
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        f.write(tomli_w.dumps(d).encode("utf-8"))
    return d


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
    if path == "config.toml":
        env_path = os.getenv("PROMPT_MANAGER_CONFIG_PATH")
        if env_path:
            path = env_path
    if not path.endswith(".toml"):
        raise FileNotFoundError(f"Config file not found at {path}")
    if not os.path.exists(path):
        if os.getenv("PROMPT_MANAGER_PROMPT"):
            _bootstrap_config(path)
        else:
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
        api=processed["api"],
        prompt=processed.get("prompt")
    )
