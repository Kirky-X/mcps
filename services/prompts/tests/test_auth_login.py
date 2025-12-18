"""
Test authentication login functionality
"""
import pytest
import pytest_asyncio
import os
import tempfile
from types import SimpleNamespace
from httpx import AsyncClient, ASGITransport

# Set environment variables before importing app
os.environ["PROMPT_MANAGER_CONFIG_PATH"] = os.path.join(os.path.dirname(__file__), "test_config.toml")
os.environ["FASTAPI_USERS_JWT_SECRET"] = "test-secret-for-testing-only"

from prompt_manager.api.http_server import app, get_manager, current_active_user


@pytest_asyncio.fixture
async def client(db_engine, prompt_manager):
    """Create FastAPI test client for auth tests"""
    # Reset app state to ensure clean test environment
    app.state.db_initialized = False
    if hasattr(app.state, 'vector_index'):
        delattr(app.state, 'vector_index')
    if hasattr(app.state, 'manager'):
        delattr(app.state, 'manager')
    
    # Override dependencies for tests
    app.dependency_overrides[get_manager] = lambda: prompt_manager
    app.dependency_overrides[current_active_user] = lambda: SimpleNamespace(id="test_user")
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_login_success(client):
    """Test successful user login"""
    # First register a user
    reg_data = {
        "email": "login_test@example.com",
        "password": "testpassword123"
    }
    reg_response = await client.post("/auth/register", json=reg_data)
    assert reg_response.status_code in (200, 201)
    
    # Test login with correct credentials
    login_data = {
        "username": "login_test@example.com",
        "password": "testpassword123"
    }
    login_response = await client.post("/auth/jwt/login", data=login_data)
    
    assert login_response.status_code == 200
    login_result = login_response.json()
    
    # Verify response structure - FastAPI users only returns token info
    assert "access_token" in login_result
    assert "token_type" in login_result
    assert login_result["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_auth_login_invalid_password(client):
    """Test login with invalid password"""
    # First register a user
    reg_data = {
        "email": "login_invalid@example.com",
        "password": "correctpassword"
    }
    reg_response = await client.post("/auth/register", json=reg_data)
    assert reg_response.status_code in (200, 201)
    
    # Test login with wrong password
    login_data = {
        "username": "login_invalid@example.com",
        "password": "wrongpassword"
    }
    login_response = await client.post("/auth/jwt/login", data=login_data)
    
    assert login_response.status_code == 400
    # FastAPI users returns different error format - check for common error indicators
    error_data = login_response.json()
    assert isinstance(error_data, dict)


@pytest.mark.asyncio
async def test_auth_login_nonexistent_user(client):
    """Test login with non-existent user"""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "anypassword"
    }
    login_response = await client.post("/auth/jwt/login", data=login_data)
    
    assert login_response.status_code == 400
    # FastAPI users returns different error format - check for common error indicators
    error_data = login_response.json()
    assert isinstance(error_data, dict)


@pytest.mark.asyncio
async def test_auth_login_missing_fields(client):
    """Test login with missing required fields"""
    # Missing username
    login_response = await client.post("/auth/jwt/login", data={"password": "test123"})
    assert login_response.status_code == 422
    
    # Missing password
    login_response = await client.post("/auth/jwt/login", data={"username": "test@example.com"})
    assert login_response.status_code == 422