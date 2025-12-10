# Copyright (c) Kirky.X. 2025. All rights reserved.
from typing import Optional
from supabase import create_client, Client
from ...utils.config import DatabaseConfig
from ...utils.logger import get_logger

logger = get_logger(__name__)

class SupabaseClient:
    def __init__(self, config: DatabaseConfig):
        """初始化 Supabase 客户端

        Args:
            config (DatabaseConfig): 数据库配置对象
        """
        self.config = config
        self._client: Optional[Client] = None
        self._init_client()

    def _init_client(self):
        """创建 Supabase 客户端实例"""
        if self.config.type != "supabase":
            return

        try:
            if not self.config.supabase_url or not self.config.supabase_key:
                raise ValueError("Missing Supabase credentials")
                
            self._client = create_client(
                self.config.supabase_url,
                self.config.supabase_key
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize Supabase client", error=str(e))
            raise

    @property
    def client(self) -> Client:
        """获取 Supabase 客户端实例

        Returns:
            Client: Supabase 客户端实例

        Raises:
            RuntimeError: 如果客户端未初始化
        """
        if not self._client:
            raise RuntimeError("Supabase client is not initialized")
        return self._client

    async def verify_connection(self) -> bool:
        """验证与 Supabase 的连接

        尝试执行一个简单的查询来验证连接状态。

        Returns:
            bool: 连接正常返回 True，否则返回 False
        """
        if not self._client:
            return False

        try:
            # 尝试查询 prompt_versions 表的一条记录作为心跳检测
            # 使用 count 操作开销最小
            response = self._client.table("prompt_versions").select("id", count="exact").limit(1).execute()
            return True
        except Exception as e:
            logger.error("Supabase connection verification failed", error=str(e))
            return False
