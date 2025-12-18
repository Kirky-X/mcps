from types import SimpleNamespace
from pathlib import Path
from fastapi.testclient import TestClient


def test_env_cache_flow_http(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.toml"
    db_path = tmp_path / "prompts.db"
    cache_dir = tmp_path / "cache"

    monkeypatch.setenv("PROMPT_MANAGER_CONFIG_PATH", str(cfg_path))
    monkeypatch.setenv("PROMPT_MANAGER_DB_PATH", str(db_path))
    monkeypatch.setenv("PROMPT_MANAGER_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    monkeypatch.setenv("PROMPT_MANAGER_PROMPT", "integration demo")

    # Import app after env is set so lifespan uses our config
    from prompt_manager.api.http_server import app, current_active_user

    # Reset app state to ensure clean test environment
    app.state.db_initialized = False
    if hasattr(app.state, 'vector_index'):
        delattr(app.state, 'vector_index')
    if hasattr(app.state, 'manager'):
        delattr(app.state, 'manager')

    # Override auth dependency
    app.dependency_overrides[current_active_user] = lambda: SimpleNamespace(id="u1")

    with TestClient(app) as client:
        # Create prompt
        payload = {
            "name": "demo",
            "description": "Demo prompt",
            "roles": [
                {"role_type": "system", "content": "sys", "order": 0},
                {"role_type": "user", "content": "hi", "order": 1}
            ],
            "version_type": "minor",
            "tags": ["t1"]
        }
        r = client.post("/prompts", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        version = data["version"]

        # Read prompt via API to ensure flow works and warms filesystem cache
        req = {"name": "demo", "version": version, "output_format": "formatted"}
        r2 = client.post("/prompts/get", json=req)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["code"] == 200
        assert "data" in body

        # After get, cache file should exist
        key = f"prompt:demo:v{version}"
        fp = Path(cache_dir) / f"{key}.json"
        assert fp.exists()
