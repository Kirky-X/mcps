import os
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from prompt_manager.api.http_server import app, get_manager


@pytest_asyncio.fixture
async def client(prompt_manager):
    app.dependency_overrides[get_manager] = lambda: prompt_manager
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_local_switch_and_response_time(client):
    os.environ["OPENAI_API_KEY"] = ""  # 模拟未配置
    # 创建一个 prompt，确保后续搜索有数据
    reg = await client.post("/auth/register", json={"email": "embed_local@example.com", "password": "secret123"})
    assert reg.status_code in (200, 201)
    login = await client.post("/auth/jwt/login", data={"username": "embed_local@example.com", "password": "secret123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post("/prompts", json={
        "name": "e2e_local_emb_case",
        "description": "Embedding local switch case",
        "roles": [
            {"role_type": "system", "content": "sys", "order": 1},
            {"role_type": "user", "content": "hi", "order": 2}
        ],
        "tags": ["e2e", "embedding"],
        "llm_config": {"model": "gpt-3.5-turbo"}
    }, headers=headers)
    assert r.status_code == 200

    # 搜索接口，测量响应时间
    t0 = asyncio.get_event_loop().time()
    r2 = await client.post("/prompts/search", json={
        "query": "embedding",
        "limit": 3
    }, headers=headers)
    latency_ms = int((asyncio.get_event_loop().time() - t0)*1000)
    assert r2.status_code == 200
    data = r2.json()["data"]
    assert "results" in data
    # 指标要求可通过环境变量传入，这里简单校验不超过默认阈值
    max_ms = int(os.getenv("MAX_RESPONSE_MS", "2000"))
    assert latency_ms <= max_ms
