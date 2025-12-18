# Copyright (c) Kirky.X. 2025. All rights reserved.
import datetime
from typing import List, Dict, Any, Optional, Union

from supabase._async.client import AsyncClient
from supabase.lib.client_options import ClientOptions
from supabase_auth._async.storage import AsyncMemoryStorage

from ..utils.config import SupabaseConfig
from ..utils.exceptions import DatabaseError
from ..utils.logger import logger


class SupabaseService:
    """Supabase 数据库服务封装
    
    提供对 Supabase 的异步 CRUD 操作封装，包含连接管理、错误处理与通用查询构建。
    """

    def __init__(self, config: SupabaseConfig):
        """初始化 Supabase 服务

        Args:
            config (SupabaseConfig): Supabase 配置对象。
        """
        self.config = config
        self.client: Optional[AsyncClient] = None
        self._initialized = False

    async def initialize(self):
        """初始化 Supabase 客户端连接

        创建异步客户端实例并进行连通性测试。

        Raises:
            DatabaseError: 当连接测试失败或配置无效时抛出。
        """
        if self._initialized:
            return

        try:
            # Use default ClientOptions and let Supabase handle the initialization
            self.client = await AsyncClient.create(
                self.config.url, 
                self.config.key
            )
            await self.check_connection()
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise self._handle_supabase_error(e)

    async def check_connection(self):
        """测试数据库连接

        通过执行一个简单的操作来验证连接是否正常。

        Raises:
            DatabaseError: 当查询失败时抛出。
        """
        if not self.client:
            raise DatabaseError("Client not initialized")
        
        try:
            # Execute a simple query to test the connection
            await self.client.table("prompts").select("*").limit(1).execute()
            logger.info("Supabase connection check successful")
        except Exception as e:
            logger.error(f"Supabase connection check failed: {str(e)}")
            raise self._handle_supabase_error(e)

    async def select(
        self, 
        table: str, 
        columns: str = "*", 
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        desc: bool = False
    ) -> List[Dict[str, Any]]:
        """执行查询操作

        Args:
            table (str): 表名。
            columns (str): 选择列，默认为 "*"。
            filters (Optional[Dict[str, Any]]): 简单的等值过滤条件字典。
            limit (Optional[int]): 限制返回行数。
            offset (Optional[int]): 分页偏移。
            order_by (Optional[str]): 排序字段。
            desc (bool): 是否降序。

        Returns:
            List[Dict[str, Any]]: 查询结果列表。

        Raises:
            DatabaseError: 当查询执行失败时抛出。
        """
        if not self.client:
            await self.initialize()

        try:
            query = self.client.table(table).select(columns)
            
            if filters:
                for k, v in filters.items():
                    query = query.eq(k, v)
            
            if order_by:
                query = query.order(order_by, desc=desc)
                
            if limit is not None:
                # Note: supabase-py/postgrest uses range(start, end) inclusive?
                # Or limit(). range() is usually for pagination.
                # .limit() exists in the builder.
                query = query.limit(limit)
                
            if offset is not None:
                query = query.range(offset, offset + (limit or 10) - 1)

            response = await query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Supabase select failed on {table}: {str(e)}")
            raise self._handle_supabase_error(e)

    async def insert(self, table: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """执行插入操作

        Args:
            table (str): 表名。
            data (Union[Dict, List[Dict]]): 单条或多条数据。

        Returns:
            List[Dict[str, Any]]: 插入后的数据（包含生成的主键等）。

        Raises:
            DatabaseError: 当插入失败时抛出。
        """
        if not self.client:
            await self.initialize()

        try:
            response = await self.client.table(table).insert(data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Supabase insert failed on {table}: {str(e)}")
            raise self._handle_supabase_error(e)

    async def update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行更新操作

        Args:
            table (str): 表名。
            data (Dict[str, Any]): 更新的数据。
            filters (Dict[str, Any]): 更新条件（必须提供以防止全表更新）。

        Returns:
            List[Dict[str, Any]]: 更新后的数据。

        Raises:
            DatabaseError: 当更新失败或未提供过滤条件时抛出。
        """
        if not self.client:
            await self.initialize()

        if not filters:
            raise DatabaseError("Update requires filters to prevent accidental bulk updates")

        try:
            query = self.client.table(table).update(data)
            for k, v in filters.items():
                query = query.eq(k, v)
            
            response = await query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Supabase update failed on {table}: {str(e)}")
            raise self._handle_supabase_error(e)

    async def delete(self, table: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行删除操作

        Args:
            table (str): 表名。
            filters (Dict[str, Any]): 删除条件（必须提供）。

        Returns:
            List[Dict[str, Any]]: 被删除的数据。

        Raises:
            DatabaseError: 当删除失败或未提供过滤条件时抛出。
        """
        if not self.client:
            await self.initialize()

        if not filters:
            raise DatabaseError("Delete requires filters")

        try:
            query = self.client.table(table).delete()
            for k, v in filters.items():
                query = query.eq(k, v)
            
            response = await query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Supabase delete failed on {table}: {str(e)}")
            raise self._handle_supabase_error(e)

    async def search_vectors(self, embedding: List[float], match_threshold: float = 0.7, k: int = 10) -> List[tuple]:
        """执行向量相似度搜索

        调用数据库 RPC 函数 `match_prompt_versions` 进行向量检索。

        Args:
            embedding (List[float]): 查询向量。
            match_threshold (float): 相似度阈值。
            k (int): 返回结果数量。

        Returns:
            List[tuple]: (id, similarity) 元组列表。

        Raises:
            DatabaseError: 当 RPC 调用失败时抛出。
        """
        if not self.client:
            await self.initialize()

        try:
            # Assuming 'match_prompt_versions' RPC function exists in Supabase
            # create or replace function match_prompt_versions (
            #   query_embedding vector(1536),
            #   match_threshold float,
            #   match_count int
            # )
            # returns table (
            #   id uuid,
            #   similarity float
            # )
            # language plpgsql stable
            # as $$
            # begin
            #   return query
            #   select
            #     prompt_versions.id,
            #     1 - (prompt_versions.description_vector <=> query_embedding) as similarity
            #   from prompt_versions
            #   where 1 - (prompt_versions.description_vector <=> query_embedding) > match_threshold
            #   order by prompt_versions.description_vector <=> query_embedding
            #   limit match_count;
            # end;
            # $$;

            params = {
                "query_embedding": embedding,
                "match_threshold": match_threshold,
                "match_count": k
            }
            response = await self.client.rpc("match_prompt_versions", params).execute()
            return [(row["id"], row["similarity"]) for row in response.data]
        except Exception as e:
            logger.error(f"Supabase vector search failed: {str(e)}")
            raise self._handle_supabase_error(e)

    async def rpc(self, function_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """执行 RPC 存储过程调用

        Args:
            function_name (str): 存储过程名称。
            params (Optional[Dict[str, Any]]): 参数字典。

        Returns:
            Any: RPC 调用结果。

        Raises:
            DatabaseError: 当调用失败时抛出。
        """
        if not self.client:
            await self.initialize()

        try:
            response = await self.client.rpc(function_name, params or {}).execute()
            return response.data
        except Exception as e:
            logger.error(f"Supabase RPC failed on {function_name}: {str(e)}")
            raise self._handle_supabase_error(e)

    def _handle_supabase_error(self, error: Exception) -> DatabaseError:
        """将 Supabase 错误转换为应用内部异常
        
        Args:
            error (Exception): 原始异常
            
        Returns:
            DatabaseError: 转换后的数据库异常
        """
        msg = str(error)
        # Here we could parse specific Supabase/Postgrest error codes if available
        # For now, wrap generally
        return DatabaseError(f"Supabase operation failed: {msg}")
