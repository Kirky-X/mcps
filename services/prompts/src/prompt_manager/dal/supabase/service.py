# Copyright (c) Kirky.X. 2025. All rights reserved.
from typing import Dict, List, Optional, Any
from ...utils.logger import get_logger
from ...services.supabase_service import SupabaseService as GenericSupabaseService
from ...infrastructure.time_network import get_precise_time

logger = get_logger(__name__)

class SupabaseService:
    def __init__(self, service: GenericSupabaseService):
        """初始化 Supabase 服务封装

        Args:
            service (GenericSupabaseService): 通用 Supabase 服务实例
        """
        self.service = service
        self.logger = logger

    @property
    def client(self):
        return self.service.client

    async def get_prompt_version(self, prompt_name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取指定版本的提示信息

        Args:
            prompt_name (str): 提示名称
            version (Optional[str]): 版本号，如果为 None 则获取最新版本

        Returns:
            Optional[Dict[str, Any]]: 提示版本详情，包含关联的角色和原则
        """
        try:
            # 1. 获取 Prompt ID
            prompts = await self.service.select("prompts", columns="id", filters={"name": prompt_name})
            if not prompts:
                return None
            prompt_id = prompts[0]["id"]

            # 2. 构建版本查询
            # Query related tables: roles, llm_config, and principles via the join table version_principle_refs
            query = self.client.table("prompt_versions").select(
                "*, roles:prompt_roles(*), llm_config:llm_configs(*), principle_refs:version_principle_refs(*, principle:principle_prompts(*))"
            ).eq("prompt_id", prompt_id).eq("is_active", True)

            if version:
                query = query.eq("version", version)
            else:
                query = query.eq("is_latest", True)

            response = await query.execute()
            
            if not response.data:
                return None
                
            return response.data[0]

        except Exception as e:
            self.logger.error(
                "Failed to fetch prompt version", 
                prompt_name=prompt_name, 
                version=version, 
                error=str(e)
            )
            # Generic service handles error wrapping, but we are doing custom complex query here
            # So we re-wrap or just log and raise
            raise self.service._handle_supabase_error(e)

    async def create_prompt_version(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的提示版本

        Args:
            prompt_data (Dict[str, Any]): 包含版本信息的字典

        Returns:
            Dict[str, Any]: 创建成功的版本记录
        """
        try:
            return (await self.service.insert("prompt_versions", prompt_data))[0]
        except Exception as e:
            self.logger.error("Failed to create prompt version", error=str(e))
            raise

    # --- CRUD Helpers for Complex Object Graph ---

    async def get_prompt_id_by_name(self, name: str) -> Optional[str]:
        prompts = await self.service.select("prompts", columns="id", filters={"name": name})
        if prompts:
            return prompts[0]["id"]
        return None

    async def create_prompt(self, name: str) -> str:
        data = await self.service.insert("prompts", {"name": name, "created_at": get_precise_time().isoformat()})
        return data[0]["id"]

    async def get_latest_version_info(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        # Complex query with order/limit not fully supported by simple select helper yet
        # Using raw client or extending helper. Let's use raw client for complex queries for now
        # or add more params to select helper. The select helper has order_by/limit.
        versions = await self.service.select(
            "prompt_versions", 
            columns="version, version_number", 
            filters={"prompt_id": prompt_id},
            order_by="created_at",
            desc=True,
            limit=1
        )
        if versions:
            return versions[0]
        return None

    async def create_roles(self, roles_data: List[Dict[str, Any]]):
        if not roles_data:
            return
        await self.service.insert("prompt_roles", roles_data)

    async def create_llm_config(self, config_data: Dict[str, Any]):
        await self.service.insert("llm_configs", config_data)

    async def get_tag_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        tags = await self.service.select("tags", filters={"name": name})
        if tags:
            return tags[0]
        return None

    async def create_tag(self, name: str) -> Dict[str, Any]:
        tags = await self.service.insert("tags", {"name": name})
        return tags[0]

    async def create_prompt_tag(self, version_id: str, tag_id: str):
        await self.service.insert("prompt_tags", {"version_id": version_id, "tag_id": tag_id})

    async def get_principle_by_params(self, name: str, version: str = "latest", is_latest: bool = True) -> Optional[Dict[str, Any]]:
        filters = {"name": name, "is_active": True}
        if version == "latest":
            filters["is_latest"] = True
        else:
            filters["version"] = version
            
        principles = await self.service.select("principle_prompts", filters=filters)
        if principles:
            return principles[0]
        return None

    async def create_principle_ref(self, ref_data: Dict[str, Any]):
        await self.service.insert("version_principle_refs", ref_data)

    async def get_client_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        clients = await self.service.select("llm_clients", filters={"name": name})
        if clients:
            return clients[0]
        return None

    async def create_client(self, name: str) -> Dict[str, Any]:
        # Create with empty default_principles
        clients = await self.service.insert("llm_clients", {"name": name, "default_principles": []})
        return clients[0]

    async def create_client_mapping(self, version_id: str, client_id: str):
        await self.service.insert("client_mappings", {"version_id": version_id, "client_id": client_id})

    async def reset_latest_flags(self, prompt_id: str, exclude_version_id: str):
        # Complex update with neq filter not supported by simple helper
        try:
            self.client.table("prompt_versions").update({"is_latest": False}).eq("prompt_id", prompt_id).neq("id", exclude_version_id).execute()
        except Exception as e:
             raise self.service._handle_supabase_error(e)

    async def update_prompt_status(self, version_id: str, is_active: bool) -> bool:
        """更新提示版本的激活状态

        Args:
            version_id (str): 版本 ID
            is_active (bool): 新的状态

        Returns:
            bool: 更新是否成功
        """
        try:
            await self.service.update("prompt_versions", {"is_active": is_active}, filters={"id": version_id})
            return True
        except Exception as e:
            self.logger.error(
                "Failed to update prompt status", 
                version_id=version_id, 
                is_active=is_active, 
                error=str(e)
            )
            raise

    async def delete_prompt_version(self, version_id: str) -> bool:
        """软删除提示版本

        Args:
            version_id (str): 版本 ID

        Returns:
            bool: 删除是否成功
        """
        return await self.update_prompt_status(version_id, False)

    async def get_prompt_versions_by_name(self, prompt_name: str) -> List[Dict[str, Any]]:
        """获取指定提示的所有版本

        Args:
            prompt_name (str): 提示名称

        Returns:
            List[Dict[str, Any]]: 版本列表
        """
        try:
            # 1. Get Prompt ID
            prompts = await self.service.select("prompts", columns="id", filters={"name": prompt_name})
            if not prompts:
                return []
            prompt_id = prompts[0]["id"]

            # 2. Get Versions
            return await self.service.select("prompt_versions", filters={"prompt_id": prompt_id})
        except Exception as e:
            self.logger.error("Failed to get prompt versions", prompt_name=prompt_name, error=str(e))
            raise

    async def update_version(self, version_id: str, data: Dict[str, Any]):
        """更新版本信息

        Args:
            version_id (str): 版本 ID
            data (Dict[str, Any]): 更新数据
        """
        await self.service.update("prompt_versions", data, filters={"id": version_id})

    async def update_prompt(self, prompt_id: str, data: Dict[str, Any]):
        """更新 Prompt 根实体

        Args:
            prompt_id (str): Prompt ID
            data (Dict[str, Any]): 更新字段
        """
        await self.service.update("prompts", data, filters={"id": prompt_id})

    # --- AppConfig Helpers ---
    async def get_app_config(self, key: str) -> List[Dict[str, Any]]:
        return await self.service.select("app_config", filters={"key": key})

    async def set_app_config(self, key: str, value: str) -> None:
        # Upsert behavior: try update, if not exists then insert
        rows = await self.service.select("app_config", filters={"key": key}, limit=1)
        if rows:
            await self.service.update("app_config", {"value": value}, filters={"key": key})
        else:
            await self.service.insert("app_config", {"key": key, "value": value})

    async def delete_vector(self, version_id: str):
        """删除向量索引

        Args:
            version_id (str): 版本 ID
        """
        try:
            await self.service.delete("vec_prompts", filters={"version_id": version_id})
        except Exception as e:
            self.logger.error("Failed to delete vector", version_id=version_id, error=str(e))
            # Don't raise, just log

    # --- Vector Search Support ---

    async def insert_vector(self, version_id: str, embedding: List[float]):
        """插入或更新向量索引

        Args:
            version_id (str): 版本 ID
            embedding (List[float]): 向量数据
        """
        # Upsert into vec_prompts
        try:
            self.client.table("vec_prompts").upsert({
                "version_id": version_id,
                "description_vector": embedding
            }).execute()
        except Exception as e:
            self.logger.error("Failed to insert vector", version_id=version_id, error=str(e))
            raise self.service._handle_supabase_error(e)

    async def search_vectors(self, query_embedding: List[float], k: int = 10) -> List[tuple[str, float]]:
        """搜索相似向量

        Args:
            query_embedding (List[float]): 查询向量
            k (int): 返回数量

        Returns:
            List[tuple[str, float]]: (version_id, similarity_score)
        """
        try:
            return await self.service.search_vectors(query_embedding, k=k)
        except Exception as e:
             self.logger.error(f"Vector search failed: {str(e)}")
             # Generic service handles fallback if configured, or raises
             raise
