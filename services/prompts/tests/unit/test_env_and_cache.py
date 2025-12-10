import os
from pathlib import Path
from unittest.mock import patch
from prompt_manager.utils.config import load_config
from prompt_manager.core.cache import CacheManager


def test_env_injection_bootstrap(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setenv("PROMPT_MANAGER_CONFIG_PATH", str(cfg_path))
    monkeypatch.setenv("PROMPT_MANAGER_DB_PATH", str(tmp_path / "prompts.db"))
    monkeypatch.setenv("PROMPT_MANAGER_PROMPT", "Hello from env")
    monkeypatch.setenv("PROMPT_MANAGER_CACHE_DIR", str(tmp_path / "cache"))

    cfg = load_config()
    assert cfg.prompt
    assert cfg.prompt["text"] == "Hello from env"
    assert cfg.cache.get("dir") == str(tmp_path / "cache")


def test_filesystem_cache_write(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setenv("PROMPT_MANAGER_CONFIG_PATH", str(cfg_path))
    monkeypatch.setenv("PROMPT_MANAGER_DB_PATH", str(tmp_path / "prompts.db"))
    monkeypatch.setenv("PROMPT_MANAGER_PROMPT", "X")
    monkeypatch.setenv("PROMPT_MANAGER_CACHE_DIR", str(tmp_path / "cache"))

    cfg = load_config()
    cm = CacheManager(cfg)
    cm.insert("prompt:demo:v1", {"a": 1})
    fp = Path(cfg.cache.get("dir")) / "prompt:demo:v1.json"
    assert fp.exists()
    cm.invalidate("prompt:demo:v1")
    assert not fp.exists()

