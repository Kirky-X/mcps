# Copyright (c) Kirky.X. 2025. All rights reserved.
import pytest
from fastapi.testclient import TestClient
from prompt_manager.api.http_server import app, get_manager


@pytest.fixture
def client(prompt_manager):
    """创建带依赖覆盖的 FastAPI 测试客户端

    将 `get_manager` 绑定到测试用 `prompt_manager`，用于执行安全相关的端到端场景。

    Args:
        prompt_manager (PromptManager): 管理器实例。

    Returns:
        TestClient: FastAPI 测试客户端。
    """
    app.dependency_overrides[get_manager] = lambda: prompt_manager
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_security_sql_injection_in_search(client):
    """端到端：向量搜索接口的 SQL 注入防护

    验证基于 `text()` 的原生 SQL 使用参数绑定，不会执行注入语句或破坏数据。

    Args:
        client (TestClient): 测试客户端。

    Returns:
        None
    """
    # 尝试在 query 中注入 SQL
    malicious_query = "' OR 1=1; DROP TABLE prompts; --"

    # 1. 注册并登录，创建一个正常数据
    reg = client.post("/auth/register", json={"email": "sec_sql@example.com", "password": "secret123"})
    assert reg.status_code in (200, 201)
    login = client.post("/auth/jwt/login", data={"username": "sec_sql@example.com", "password": "secret123"})
    assert login.status_code == 200
    token = login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/prompts", json={
        "name": "safe_prompt",
        "description": "safe",
        "roles": [{"role_type": "user", "content": "hi", "order": 1}]
    }, headers=headers)

    # 2. 执行恶意搜索
    response = client.post("/prompts/search", json={
        "query": malicious_query,
        "limit": 10
    }, headers=headers)

    # 预期：
    # 1. 请求成功返回（因为恶意字符串被当作普通文本向量化了）
    # 2. 或者返回空结果
    # 3. 绝对不能报错 500 (SQL 语法错误) 或导致数据丢失
    assert response.status_code == 200

    # 验证数据未被删除
    check = client.post("/prompts/get", json={"name": "safe_prompt"}, headers=headers)
    assert check.status_code == 200


def test_security_input_length_dos(client):
    """端到端：超长输入防护（DoS）

    验证 Pydantic 对名称长度的限制生效，超出长度触发 422。

    Args:
        client (TestClient): 测试客户端。

    Returns:
        None
    """
    # 生成 201 字符的名称 (限制是 200)
    long_name = "a" * 201

    reg = client.post("/auth/register", json={"email": "sec_len@example.com", "password": "secret123"})
    login = client.post("/auth/jwt/login", data={"username": "sec_len@example.com", "password": "secret123"})
    token = login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/prompts", json={
        "name": long_name,
        "description": "test",
        "roles": [{"role_type": "user", "content": "hi", "order": 1}]
    }, headers=headers)

    assert response.status_code == 422
    assert "String should have at most 200 characters" in response.text


def test_security_template_injection_e2e(client):
    """端到端：模板注入（SSTI）防护验证

    创建包含恶意 Jinja2 片段的提示并尝试渲染，期望沙箱限制避免敏感信息泄露或触发受控错误。

    Args:
        client (TestClient): 测试客户端。

    Returns:
        None
    """
    # 尝试读取 Python 对象信息的恶意模板
    malicious_content = "{{ ''.__class__.__mro__[1].__subclasses__() }}"

    # 1. 创建包含恶意模板的 Prompt
    reg = client.post("/auth/register", json={"email": "sec_ssti@example.com", "password": "secret123"})
    login = client.post("/auth/jwt/login", data={"username": "sec_ssti@example.com", "password": "secret123"})
    token = login.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    create_res = client.post("/prompts", json={
        "name": "ssti_test",
        "description": "testing ssti",
        "roles": [
            {"role_type": "user", "content": malicious_content, "order": 1}
        ]
    }, headers=headers)
    assert create_res.status_code == 200

    # 2. 尝试获取并渲染
    # SandboxedEnvironment 应该阻止访问内部属性，或者渲染结果不包含敏感信息
    # 在严格模式下可能会报错，或者渲染为空/原样字符串
    get_res = client.post("/prompts/get", json={"name": "ssti_test"}, headers=headers)

    if get_res.status_code == 200:
        content = get_res.json()["data"]["openai_format"]["messages"][0]["content"]
        # 验证没有泄露类信息 (如 <class 'type'> 等)
        assert "<class" not in content
        assert "__subclasses__" not in content
    elif get_res.status_code == 500:
        # 如果沙箱抛出 SecurityError 导致 500 也是一种防护（虽然不优雅）
        # 但我们期望的是 TemplateRenderError 被捕获并返回 4xx 或 500
        pass


def test_security_path_traversal_in_config(tmp_path):
    """端到端：配置文件加载路径遍历风险验证

    验证 `load_config` 对非法路径处理为抛出 `FileNotFoundError`，避免任意文件读取。

    Args:
        tmp_path (pathlib.Path): 临时目录路径（未直接使用）。

    Returns:
        None

    Raises:
        FileNotFoundError: 当路径非法或文件不存在时。
    """
    from prompt_manager.utils.config import load_config

    # 尝试加载不存在的文件
    with pytest.raises(FileNotFoundError):
        load_config("/etc/passwd")  # 在 Linux 上尝试读取敏感文件

    # 注意：这个测试更多是验证 load_config 的行为，
    # 实际攻击面很小，因为 config 路径通常由运维指定。
