# Copyright (c) Kirky.X. 2025. All rights reserved.
import pytest
from unittest.mock import MagicMock, patch
from prompt_manager.utils.config import DatabaseConfig
from prompt_manager.dal.supabase.client import SupabaseClient

@pytest.fixture
def mock_supabase_config():
    return DatabaseConfig(
        type="supabase",
        supabase_url="https://example.supabase.co",
        supabase_key="valid-key"
    )

@pytest.fixture
def mock_create_client():
    with patch("prompt_manager.dal.supabase.client.create_client") as mock:
        yield mock

class TestSupabaseClient:
    def test_init_success(self, mock_supabase_config, mock_create_client):
        """测试客户端初始化成功"""
        client = SupabaseClient(mock_supabase_config)
        
        mock_create_client.assert_called_once_with(
            "https://example.supabase.co",
            "valid-key"
        )
        assert client.client is not None

    def test_init_missing_credentials(self):
        """测试缺失凭证时初始化失败"""
        # 由于我们在 config.py 中添加了验证，这里直接验证 DatabaseConfig 的实例化是否会抛出异常
        with pytest.raises(ValueError, match="Supabase URL is required"):
            DatabaseConfig(
                type="supabase",
                supabase_url=None,
                supabase_key=None
            )

    def test_verify_connection_success(self, mock_supabase_config, mock_create_client):
        """删除：同步版本的连接验证（由异步版本覆盖）"""
        pass
    
    @pytest.mark.asyncio
    async def test_verify_connection_async_success(self, mock_supabase_config, mock_create_client):
        """异步测试连接验证成功"""
        mock_client_instance = MagicMock()
        mock_create_client.return_value = mock_client_instance
        
        # Chain mocks
        mock_client_instance.table("prompt_versions").select("id", count="exact").limit(1).execute.return_value = MagicMock()
        
        client = SupabaseClient(mock_supabase_config)
        result = await client.verify_connection()
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_connection_async_failure(self, mock_supabase_config, mock_create_client):
        """异步测试连接验证失败"""
        mock_client_instance = MagicMock()
        mock_create_client.return_value = mock_client_instance
        
        # Chain mocks to raise exception
        mock_client_instance.table("prompt_versions").select("id", count="exact").limit(1).execute.side_effect = Exception("Connection error")
        
        client = SupabaseClient(mock_supabase_config)
        result = await client.verify_connection()
        assert result is False
