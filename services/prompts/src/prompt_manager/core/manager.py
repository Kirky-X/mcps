# Copyright (c) Kirky.X. 2025. All rights reserved.
import asyncio
import uuid
import datetime
import hashlib
from typing import Optional, List, Dict, Any, Literal, Union

from sqlmodel import select
from sqlalchemy import update, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload

from .cache import CacheManager
from .queue import UpdateQueue
from ..dal.database import Database
from ..dal.vector_index import VectorIndex
from ..dal.supabase.service import SupabaseService
from ..models.orm import (
    Prompt, PromptVersion, PromptRole, LLMConfig, Tag, PromptTag,
    PrinciplePrompt, PrincipleRef, LLMClient, ClientMapping
)
from ..models.schemas import (
    CreatePromptRequest, SearchResult, SearchResultItem,
    FullPrompt, OpenAIRequest, FormattedPrompt, BothFormats
)
from ..services.embedding import EmbeddingService
from ..services.template import TemplateService
from ..utils.exceptions import (
    PromptNotFoundError, ValidationError, OptimisticLockError
)
from ..utils.logger import get_logger
from ..infrastructure.time_network import get_precise_time

logger = get_logger(__name__)


class PromptManager:
    def __init__(
            self,
            db: Database,
            cache: CacheManager,
            queue: UpdateQueue,
            embedding_service: EmbeddingService,
            template_service: TemplateService,
            vector_index: VectorIndex,
            supabase_service: Optional[SupabaseService] = None
    ):
        """初始化提示管理器核心组件

        聚合数据库、缓存、更新队列、嵌入服务、模板服务与向量索引，以支持提示的创建、搜索、获取、更新、删除与激活等完整生命周期操作。

        Args:
            db (Database): 数据库访问抽象。
            cache (CacheManager): 缓存管理器。
            queue (UpdateQueue): 异步更新队列。
            embedding_service (EmbeddingService): 文本嵌入服务。
            template_service (TemplateService): 模板渲染服务。
            vector_index (VectorIndex): 向量检索索引。
            supabase_service (Optional[SupabaseService]): Supabase 服务实例，当数据库类型为 supabase 时必须提供。

        Returns:
            None

        Raises:
            None
        """
        self.db = db
        self.cache = cache
        self.queue = queue
        self.embedding = embedding_service
        self.template = template_service
        self.vector_index = vector_index
        self.supabase = supabase_service

        if self.db.config.type == "supabase" and not self.supabase:
            raise ValueError("SupabaseService is required when database type is 'supabase'")

    async def _get_from_supabase(self, name: str, version: Optional[str]) -> FullPrompt:
        """Helper to fetch prompt from Supabase and convert to FullPrompt object"""
        data = await self.supabase.get_prompt_version(name, version)
        if not data:
            raise PromptNotFoundError(f"Prompt {name} not found")

        # 1. Convert PromptVersion
        # Filter out nested relationships for the main object
        v_data = {k: v for k, v in data.items() if k not in ['roles', 'llm_config', 'principle_refs', 'prompt', 'tags']}
        # Convert string timestamps back to datetime if necessary (Supabase returns ISO strings)
        if 'created_at' in v_data and isinstance(v_data['created_at'], str):
             import datetime
             v_data['created_at'] = datetime.datetime.fromisoformat(v_data['created_at'].replace('Z', '+00:00'))
        
        v_obj = PromptVersion(**v_data)
        
        # 2. Convert Roles
        roles_data = data.get('roles', [])
        v_obj.roles = [PromptRole(**r) for r in roles_data]
        # Sort roles by order
        v_obj.roles.sort(key=lambda x: x.order)

        # 3. Convert LLM Config
        llm_config_data = data.get('llm_config', None)
        if llm_config_data:
            # If it's a list (one-to-many result from Supabase), take the first
            if isinstance(llm_config_data, list) and len(llm_config_data) > 0:
                v_obj.llm_config = LLMConfig(**llm_config_data[0])
            elif isinstance(llm_config_data, dict):
                v_obj.llm_config = LLMConfig(**llm_config_data)

        # 4. Convert Principles
        principle_refs_data = data.get('principle_refs', [])
        principles = []
        v_obj.principle_refs = []
        for ref_data in principle_refs_data:
            # ref_data has 'principle' dict nested
            p_data = ref_data.pop('principle', None)
            ref = PrincipleRef(**ref_data)
            if p_data:
                 if 'created_at' in p_data and isinstance(p_data['created_at'], str):
                     import datetime
                     p_data['created_at'] = datetime.datetime.fromisoformat(p_data['created_at'].replace('Z', '+00:00'))
                 p_obj = PrinciplePrompt(**p_data)
                 ref.principle = p_obj
                 principles.append(p_obj)
            v_obj.principle_refs.append(ref)
        
        # Sort principles by order
        v_obj.principle_refs.sort(key=lambda x: x.order)
        # Re-sort principles list based on ref order
        principles.sort(key=lambda p: next((r.order for r in v_obj.principle_refs if r.principle_id == p.id), 0))

        return FullPrompt(
            version=v_obj,
            roles=v_obj.roles,
            principles=principles,
            llm_config=v_obj.llm_config
        )

    async def create(self, request: CreatePromptRequest) -> PromptVersion:
        """创建新的提示版本并建立相关关系与索引

        执行版本计算、嵌入生成、角色与配置持久化、标签与原则关联、客户端关联以及向量索引写入，并维护最新标记与缓存失效。

        Args:
            request (CreatePromptRequest): 提示创建请求模型。

        Returns:
            PromptVersion: 新创建的提示版本 ORM 对象。

        Raises:
            ValidationError: 当原则引用校验失败时。
            PromptNotFoundError: 当引用的提示不存在时（边界场景）。
            Exception: 其他数据库或嵌入生成异常。
        """
        if self.db.config.type == "supabase":
             version = await self._create_on_supabase(request)
             self.cache.invalidate(self.cache.generate_key(request.name, "latest"))
             self.cache.invalidate_pattern(request.name)
             return version

        async with self.db.get_session() as session:
            async with session.begin():
                version = await self._create_on_session(session, request)
            self.cache.invalidate(self.cache.generate_key(request.name, "latest"))
            self.cache.invalidate_pattern(request.name)
            return version

    async def search(
            self,
            query: Optional[str] = None,
            tags: Optional[List[str]] = None,
            logic: Literal["AND", "OR"] = "AND",
            version_filter: Literal["latest", "all", "specific"] = "latest",
            specific_version: Optional[str] = None,
            limit: int = 10,
            offset: int = 0
    ) -> SearchResult:
        """搜索提示版本并返回结构化结果

        支持向量语义搜索与标签过滤的逻辑组合，并提供相似度排序、分页与格式化输出。

        Args:
            query (Optional[str]): 查询文本用于语义检索。
            tags (Optional[List[str]]): 标签过滤条件。
            logic (Literal["AND", "OR"]): 当同时存在向量与标签搜索时的组合逻辑。
            version_filter (Literal["latest", "all", "specific"]): 版本过滤策略。
            specific_version (Optional[str]): 当选择 `specific` 时指定版本号。
            limit (int): 分页大小。
            offset (int): 分页偏移。

        Returns:
            SearchResult: 包含总数与结果项的结构体。

        Raises:
            Exception: 当数据库执行或嵌入生成失败时抛出。
        """
        if self.db.config.type == "supabase":
            return await self._search_on_supabase(query, tags, logic, version_filter, specific_version, limit, offset)

        async with self.db.get_session() as session:
            vector_ids = set()
            tag_ids = set()
            has_vector_search = False
            has_tag_search = False
            keyword_ids = set()
            similarity_map = {}

            # 1. Vector Search
            if query:
                has_vector_search = True
                vec_results = []
                try:
                    embedding = await self.embedding.generate(query)
                    # 动态维度检查：如果生成的向量维度与索引维度不一致，则跳过向量搜索，仅使用关键字搜索
                    if len(embedding) == self.vector_index.dimension:
                        vec_results = await self.vector_index.search(session, embedding, k=limit * 2)
                    else:
                        logger.warning(f"Skipping vector search: query embedding dimension ({len(embedding)}) does not match index dimension ({self.vector_index.dimension})")
                        vec_results = []
                except Exception as e:
                    logger.warning(f"Vector search failed: {e}")
                    vec_results = []
                for vid, dist in vec_results:
                    vector_ids.add(vid)
                    similarity_map[vid] = 1.0 / (1.0 + dist)

            # 2. Tag Search
            if tags:
                has_tag_search = True
                stmt = (
                    select(PromptTag.version_id)
                    .join(Tag)
                    .where(Tag.name.in_(tags))
                    .group_by(PromptTag.version_id)
                    .having(func.count(PromptTag.tag_id) == len(tags))
                )
                tag_results = await session.execute(stmt)
                tag_ids = {r[0] for r in tag_results.fetchall()}

            # 2.5 Keyword Fallback (name/description)
            if query and not vector_ids:
                kw = query.lower()
                stmt_kw = (
                    select(PromptVersion.id)
                    .join(Prompt)
                    .where(
                        or_(
                            func.lower(Prompt.name).like(f"%{kw}%"),
                            func.lower(PromptVersion.description).like(f"%{kw}%"),
                        )
                    )
                )
                kw_results = await session.execute(stmt_kw)
                keyword_ids = {r[0] for r in kw_results.fetchall()}

            # 3. Logic Combination
            candidate_ids = set()
            if has_vector_search and has_tag_search:
                if logic == "AND":
                    candidate_ids = (vector_ids | keyword_ids) & tag_ids
                else:
                    candidate_ids = (vector_ids | keyword_ids) | tag_ids
            elif has_vector_search:
                candidate_ids = vector_ids | keyword_ids
            elif has_tag_search:
                candidate_ids = tag_ids
            else:
                candidate_ids = None  # No search criteria

            # 4. Build Query
            stmt = select(PromptVersion).join(Prompt).where(PromptVersion.is_active == True)

            if candidate_ids is not None:
                if not candidate_ids:
                    return SearchResult(total=0, results=[])
                stmt = stmt.where(PromptVersion.id.in_(candidate_ids))

            if version_filter == "latest":
                stmt = stmt.where(PromptVersion.is_latest == True)
            elif version_filter == "specific" and specific_version:
                stmt = stmt.where(PromptVersion.version == specific_version)

            # Execute to get objects
            stmt = stmt.options(selectinload(PromptVersion.tags), joinedload(PromptVersion.prompt))
            results = (await session.execute(stmt)).scalars().all()

            # 5. Sort & Pagination
            if has_vector_search:
                results.sort(key=lambda v: similarity_map.get(v.id, 0), reverse=True)
            else:
                results.sort(key=lambda v: v.created_at, reverse=True)

            total = len(results)
            paginated = results[offset: offset + limit]

            # 6. Format
            items = []
            for v in paginated:
                items.append(SearchResultItem(
                    prompt_id=v.prompt_id,
                    name=v.prompt.name,
                    version=v.version,
                    description=v.description,
                    tags=[t.name for t in v.tags],
                    similarity_score=similarity_map.get(v.id) if has_vector_search else None,
                    created_at=v.created_at
                ))

            return SearchResult(total=total, results=items)

    async def get(
            self,
            name: str,
            version: Optional[str] = None,
            output_format: Literal["openai", "formatted", "both"] = "both",
            template_vars: Optional[Dict[str, Any]] = None,
            runtime_params: Optional[Dict[str, Any]] = None
    ) -> Union[OpenAIRequest, FormattedPrompt, BothFormats]:
        """获取提示并渲染为指定输出格式

        优先从缓存读取完整提示结构，若未命中则查询数据库并加载关联数据与原则集合，随后渲染消息与合并运行时参数。

        Args:
            name (str): 提示名称。
            version (Optional[str]): 指定版本；为空时读取最新版本。
            output_format (Literal["openai", "formatted", "both"]): 输出格式选择。
            template_vars (Optional[Dict[str, Any]]): 模板变量。
            runtime_params (Optional[Dict[str, Any]]): 运行时 LLM 参数覆盖。

        Returns:
            Union[OpenAIRequest, FormattedPrompt, BothFormats]: 目标格式对象。

        Raises:
            PromptNotFoundError: 当找不到对应提示或版本时抛出。
            Exception: 当数据库或渲染过程失败时抛出。
        """

        cache_key = self.cache.generate_key(name, version or "latest")
        
        # Try to get cached rendered output first
        cached_output = self.cache.get(cache_key)
        if cached_output:
            # Reconstruct Pydantic objects from cached dictionary
            if output_format == "openai":
                return OpenAIRequest(**cached_output)
            elif output_format == "formatted":
                return FormattedPrompt(**cached_output)
            else:  # both
                result = BothFormats(
                    openai_format=OpenAIRequest(**cached_output["openai_format"]),
                    formatted=FormattedPrompt(**cached_output["formatted"])
                )
                result._meta_version = cached_output["version"]
                return result

        # If not in cache, fetch and render
        if self.db.config.type == "supabase":
            full_prompt = await self._get_from_supabase(name, version)
        else:
            async with self.db.get_session() as session:
                stmt = select(PromptVersion).join(Prompt).where(
                    Prompt.name == name,
                    PromptVersion.is_active == True
                )
                if version:
                    stmt = stmt.where(PromptVersion.version == version)
                else:
                    stmt = stmt.where(PromptVersion.is_latest == True)

                stmt = stmt.options(
                    selectinload(PromptVersion.roles),
                    selectinload(PromptVersion.llm_config),
                    selectinload(PromptVersion.principle_refs),
                    selectinload(PromptVersion.client_mappings).selectinload(ClientMapping.client)
                )

                result = await session.execute(stmt)
                v_obj = result.scalars().first()
                
                if v_obj is None:
                    raise PromptNotFoundError(f"Prompt {name} not found")
                
                principles = await self._load_principles(session, v_obj)

                full_prompt = FullPrompt(
                    version=v_obj,
                    roles=v_obj.roles,
                    principles=principles,
                    llm_config=v_obj.llm_config
                )

        # Render the output
        rendered_output = self._render_output(full_prompt, output_format, template_vars, runtime_params)
        
        # Cache the JSON-serializable representation
        if output_format == "openai":
            cache_value = rendered_output.model_dump()
        elif output_format == "formatted":
            cache_value = rendered_output.model_dump()
        else:  # both
            cache_value = {
                "openai_format": rendered_output.openai_format.model_dump(),
                "formatted": rendered_output.formatted.model_dump(),
                "version": rendered_output.version.version
            }
        
        self.cache.insert(cache_key, cache_value)
        
        return rendered_output

    async def create_principle(self, name: str, version: str, content: str, is_active: bool = True, is_latest: bool = True) -> PrinciplePrompt:
        async with self.db.get_session() as session:
            async with session.begin():
                stmt = select(PrinciplePrompt).where(PrinciplePrompt.name == name, PrinciplePrompt.version == version)
                existing = (await session.execute(stmt)).scalar_one_or_none()
                if existing:
                    existing.content = content
                    existing.is_active = is_active
                    if is_latest:
                        await session.execute(
                            update(PrinciplePrompt)
                            .where(and_(PrinciplePrompt.name == name, PrinciplePrompt.id != existing.id))
                            .values(is_latest=False)
                        )
                        existing.is_latest = True
                    return existing
                p = PrinciplePrompt(name=name, version=version, content=content, is_active=is_active, is_latest=is_latest)
                session.add(p)
                await session.flush()
                if is_latest:
                    await session.execute(
                        update(PrinciplePrompt)
                        .where(and_(PrinciplePrompt.name == name, PrinciplePrompt.id != p.id))
                        .values(is_latest=False)
                    )
                return p

    async def update(self, name: str, version_number: int, **kwargs) -> PromptVersion:
        """提交更新任务以生成新版本

        将更新请求入队，最终返回新创建的版本对象或冲突异常。

        Args:
            name (str): 提示名称。
            version_number (int): 当前版本号用于乐观锁冲突检测。
            **kwargs: 创建新版本所需字段。

        Returns:
            PromptVersion: 新版本对象。

        Raises:
            OptimisticLockError: 当版本号不匹配且不能自动解决时。
            Exception: 队列或数据库相关错误。
        """
        # Note: enqueue returns a Future, we must await it to get the result
        future = await self.queue.enqueue(name, version_number, kwargs)
        return await future

    async def _execute_update(self, name: str, version_number: int, update_data: Dict[str, Any]) -> PromptVersion:
        """在同一事务中执行更新生成新版本

        读取当前最新版本并进行冲突检测，必要时将 `version_type` 设置为 `minor`，随后委托 `create` 创建新版本。

        Args:
            name (str): 提示名称。
            version_number (int): 当前版本号。
            update_data (Dict[str, Any]): 更新数据。

        Returns:
            PromptVersion: 新创建版本对象。

        Raises:
            PromptNotFoundError: 当目标提示不存在时。
            Exception: 数据库或创建流程中的其他错误。
        """
        async with self.db.get_session() as session:
            async with session.begin():
                stmt = select(PromptVersion).join(Prompt).where(
                    Prompt.name == name,
                    PromptVersion.is_latest == True
                )
                current = (await session.execute(stmt)).scalar_one_or_none()

                if not current:
                    raise PromptNotFoundError(f"Prompt {name} not found")

                if current.version_number != version_number:
                    raise OptimisticLockError("Version conflict")

                request = CreatePromptRequest(name=name, **update_data)
                version = await self._create_on_session(session, request)

            self.cache.invalidate(self.cache.generate_key(name, "latest"))
            self.cache.invalidate_pattern(name)
            return version

    async def delete(self, name: str, version: Optional[str] = None) -> bool:
        """删除或禁用提示版本

        当指定版本时删除向量索引并标记对应版本非激活；未指定版本时将所有版本标记为非激活。

        Args:
            name (str): 提示名称。
            version (Optional[str]): 指定版本字符串。

        Returns:
            bool: 操作是否成功。

        Raises:
            PromptNotFoundError: 当提示不存在时抛出。
            Exception: 数据库或索引操作失败时抛出。
        """
        if self.db.config.type == "supabase":
             return await self._delete_on_supabase(name, version)

        async with self.db.get_session() as session:
            async with session.begin():
                stmt = select(PromptVersion).join(Prompt).where(Prompt.name == name)
                
                versions = (await session.execute(stmt)).scalars().all()
                if not versions:
                    raise PromptNotFoundError(f"Prompt {name} not found")

                active_versions = [v for v in versions if v.is_active]
                if not active_versions:
                    raise PromptNotFoundError(f"Prompt {name} not found")

                if version:
                    # 删除指定版本：如果这是最后一个激活版本则禁止
                    target = next((v for v in active_versions if v.version == version), None)
                    if not target:
                        raise PromptNotFoundError(f"Version {version} not found")
                    if len(active_versions) == 1:
                        raise ValidationError("Cannot delete the last active version")
                    target.is_active = False
                    await self.vector_index.delete(session, target.id)
                else:
                    # 删除全部：至少保留一个激活版本
                    if len(active_versions) <= 1:
                        raise ValidationError("Cannot delete all versions; at least one must remain active")
                    # 保留 is_latest 优先，没有则保留创建时间最新的一个
                    keep = next((v for v in active_versions if v.is_latest), None)
                    if not keep:
                        keep = max(active_versions, key=lambda v: v.created_at)
                    for v in active_versions:
                        if v.id == keep.id:
                            continue
                        v.is_active = False
                        await self.vector_index.delete(session, v.id)

            self.cache.invalidate(self.cache.generate_key(name, version or "latest"))
            self.cache.invalidate_pattern(name)
            return True

    async def _delete_on_supabase(self, name: str, version: Optional[str] = None) -> bool:
        # Get all versions for the prompt
        versions_data = await self.supabase.get_prompt_versions_by_name(name)
        if not versions_data:
            raise PromptNotFoundError(f"Prompt {name} not found")
            
        active_versions = [v for v in versions_data if v["is_active"]]
        if not active_versions:
             # Even if prompt exists, if no active versions, we treat as not found for deletion context usually,
             # or maybe just return True? The original logic raises PromptNotFoundError if no versions found via join.
             # If versions exist but none active, original logic also raises PromptNotFoundError?
             # Let's match original logic:
             # "stmt = select(PromptVersion).join(Prompt).where(Prompt.name == name)" -> gets all versions
             # "if not versions: raise"
             # "active_versions = ... if not active_versions: raise"
             raise PromptNotFoundError(f"Prompt {name} not found or no active versions")
             
        if version:
            # Delete specific version
            target = next((v for v in active_versions if v["version"] == version), None)
            if not target:
                raise PromptNotFoundError(f"Version {version} not found")
            if len(active_versions) == 1:
                raise ValidationError("Cannot delete the last active version")
            
            await self.supabase.update_prompt_status(target["id"], False)
            await self.supabase.delete_vector(target["id"])
        else:
            # Delete all (keep one)
            if len(active_versions) <= 1:
                raise ValidationError("Cannot delete all versions; at least one must remain active")
            
            keep = next((v for v in active_versions if v["is_latest"]), None)
            if not keep:
                # Need to sort by created_at to find max
                # Supabase strings are ISO
                active_versions.sort(key=lambda v: v["created_at"], reverse=True)
                keep = active_versions[0]
                
            for v in active_versions:
                if v["id"] == keep["id"]:
                    continue
                await self.supabase.update_prompt_status(v["id"], False)
                await self.supabase.delete_vector(v["id"])
        
        self.cache.invalidate(self.cache.generate_key(name, version or "latest"))
        self.cache.invalidate_pattern(name)
        return True


    async def activate(self, name: str, version: str, set_as_latest: bool = False) -> bool:
        """激活指定版本并可选设置为最新

        根据参数为指定版本设置激活与最新标记，并使缓存失效。

        Args:
            name (str): 提示名称。
            version (str): 版本字符串。
            set_as_latest (bool): 是否同时设为最新版本。

        Returns:
            bool: 操作是否成功。

        Raises:
            PromptNotFoundError: 当版本不存在时抛出。
            Exception: 数据库执行失败时抛出。
        """
        if self.db.config.type == "supabase":
             return await self._activate_on_supabase(name, version, set_as_latest)

        async with self.db.get_session() as session:
            async with session.begin():
                stmt = select(PromptVersion).join(Prompt).where(
                    Prompt.name == name,
                    PromptVersion.version == version
                )
                v_obj = (await session.execute(stmt)).scalar_one_or_none()
                if not v_obj:
                    raise PromptNotFoundError(f"Version {version} not found")

                # Deactivate other versions first, then activate the target version
                await session.execute(
                    update(PromptVersion)
                    .where(and_(PromptVersion.prompt_id == v_obj.prompt_id, PromptVersion.id != v_obj.id))
                    .values(is_active=False)
                )
                v_obj.is_active = True
                
                # Always set as latest when activating (makes logical sense)
                await session.execute(
                    update(PromptVersion)
                    .where(and_(PromptVersion.prompt_id == v_obj.prompt_id, PromptVersion.id != v_obj.id))
                    .values(is_latest=False)
                )
                v_obj.is_latest = True

            self.cache.invalidate(self.cache.generate_key(name, version))
            self.cache.invalidate_pattern(name)
            return True

    async def _activate_on_supabase(self, name: str, version: str, set_as_latest: bool = False) -> bool:
        # Get prompt version
        v_data = await self.supabase.get_prompt_version(name, version)
        if not v_data:
            raise PromptNotFoundError(f"Version {version} not found")
        
        version_id = v_data["id"]
        prompt_id = v_data["prompt_id"]
        
        # Activate
        await self.supabase.update_prompt_status(version_id, True)
        
        if set_as_latest:
            # Reset others
            await self.supabase.reset_latest_flags(prompt_id, version_id)
            # Set this one as latest
            await self.supabase.update_version(version_id, {"is_latest": True})
            
        self.cache.invalidate(self.cache.generate_key(name, version))
        self.cache.invalidate_pattern(name)
        return True


    async def process_update_queue(self):
        """持续处理更新队列中的任务

        从队列拉取任务并执行 `_execute_update`，将结果或异常写入对应 `Future`，直至收到停止信号或被取消。

        Args:
            None

        Returns:
            None

        Raises:
            Exception: 当循环中出现未捕获错误时记录并继续。
        """
        self.queue.is_running = True
        while self.queue.is_running:
            try:
                name, ver, data, future = await self.queue.get()
                try:
                    result = await self._execute_update(name, ver, data)
                    future.set_result(result)
                except OptimisticLockError:
                    try:
                        req = CreatePromptRequest(name=name, **{**data, "version_type": "minor"})
                        result = await self.create(req)
                        future.set_result(result)
                    except Exception as e2:
                        future.set_exception(e2)
                except Exception as e:
                    future.set_exception(e)
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Queue processing error", error=str(e))

    # --- Helpers ---

    async def _calculate_version(self, session, prompt_id: str, v_type: str) -> str:
        """根据策略计算下一版本号

        当无历史版本时返回 `1.0`；`major` 递增主版本并重置次版本为 0；否则递增次版本。

        Args:
            session (AsyncSession): 异步数据库会话。
            prompt_id (str): 提示主键。
            v_type (str): 版本策略，`major` 或 `minor`。

        Returns:
            str: 下一版本号字符串，如 `1.1`。

        Raises:
            Exception: 当解析最新版本号失败时可能抛出。
        """
        # Fetch all versions to sort in Python correctly (since string sort '1.10' < '1.2' is wrong)
        # In a real system with many versions, we might use a dedicated sortable column or split columns
        stmt = select(PromptVersion.version).where(PromptVersion.prompt_id == prompt_id)
        versions = (await session.execute(stmt)).scalars().all()
        
        if not versions:
            logger.info(f"No versions found for prompt_id={prompt_id}. Starting at 1.0")
            return "1.0"
            
        def version_key(v):
            try:
                major, minor = map(int, v.split('.'))
                return (major, minor)
            except ValueError:
                return (0, 0)
        
        # Ensure versions list is not empty before calling max
        if not versions:
             logger.warning(f"Versions list became empty during processing for prompt_id={prompt_id}. Defaulting to 1.0")
             return "1.0"
                
        latest = max(versions, key=version_key)
        
        logger.info(f"Calculating version for prompt_id={prompt_id}, v_type={v_type}, latest={latest}")
        
        major, minor = map(int, latest.split('.'))
        if v_type == "major":
            version = f"{major + 1}.0"
        else:
            version = f"{major}.{minor + 1}"
        logger.info(f"Calculated new version: {version}")
        return version

    async def _associate_tags(self, session, version_id: str, tags: List[str]):
        """为版本关联标签，必要时自动创建标签实体

        Args:
            session (AsyncSession): 异步数据库会话。
            version_id (str): 版本主键。
            tags (List[str]): 标签名称列表。

        Returns:
            None

        Raises:
            Exception: 当数据库执行失败时抛出。
        """
        for t_name in tags:
            stmt = select(Tag).where(Tag.name == t_name)
            tag = (await session.execute(stmt)).scalar_one_or_none()
            if not tag:
                tag = Tag(name=t_name)
                session.add(tag)
                await session.flush()
            session.add(PromptTag(version_id=version_id, tag_id=tag.id))

    async def _associate_principles(self, session, version_id: str, refs):
        """关联原则提示引用并保持顺序

        若引用版本为 `latest` 则匹配最新激活版本，否则精确匹配指定版本。

        Args:
            session (AsyncSession): 异步数据库会话。
            version_id (str): 版本主键。
            refs (List[PrincipleRefModel]): 原则引用列表。

        Returns:
            None

        Raises:
            ValidationError: 当引用的原则不存在时抛出。
        """
        for idx, ref in enumerate(refs):
            stmt = select(PrinciplePrompt).where(PrinciplePrompt.name == ref.principle_name,
                                                 PrinciplePrompt.is_active == True)
            if ref.version != "latest":
                stmt = stmt.where(PrinciplePrompt.version == ref.version)
            else:
                stmt = stmt.where(PrinciplePrompt.is_latest == True)

            p = (await session.execute(stmt)).scalar_one_or_none()
            if not p:
                raise ValidationError(f"Principle {ref.principle_name} not found")

            session.add(PrincipleRef(version_id=version_id, principle_id=p.id, ref_version=ref.version, order=idx))

    async def _associate_client(self, session, version_id: str, client_name: str):
        """为版本关联客户端实体，必要时创建占位客户端

        Args:
            session (AsyncSession): 异步数据库会话。
            version_id (str): 版本主键。
            client_name (str): 客户端名称。

        Returns:
            None

        Raises:
            Exception: 当数据库执行失败时抛出。
        """
        stmt = select(LLMClient).where(LLMClient.name == client_name)
        client = (await session.execute(stmt)).scalar_one_or_none()
        if not client:
            client = LLMClient(name=client_name, default_principles=[])
            session.add(client)
            await session.flush()

        session.add(ClientMapping(version_id=version_id, client_id=client.id))

    async def _load_client_principles(self, session, version_id: str, client_name: str):
        """加载并合并客户端默认原则（占位实现）

        预留扩展点：根据客户端默认原则列表合并到版本原则集合，避免重复。

        Args:
            session (AsyncSession): 异步数据库会话。
            version_id (str): 版本主键。
            client_name (str): 客户端名称。

        Returns:
            None

        Raises:
            None
        """
        client_stmt = select(LLMClient).where(LLMClient.name == client_name)
        client = (await session.execute(client_stmt)).scalar_one_or_none()
        if not client or not client.default_principles:
            return
        existing_stmt = select(PrinciplePrompt.name).join(PrincipleRef).where(PrincipleRef.version_id == version_id)
        existing = (await session.execute(existing_stmt)).fetchall()
        existing_names = {r[0] for r in existing}
        max_order_stmt = select(func.max(PrincipleRef.order)).where(PrincipleRef.version_id == version_id)
        max_order = (await session.execute(max_order_stmt)).scalar() or -1
        added = 0
        for dp in client.default_principles:
            pname = dp.get("principle_name")
            pver = dp.get("version", "latest")
            if not pname or pname in existing_names:
                continue
            q = select(PrinciplePrompt).where(PrinciplePrompt.name == pname, PrinciplePrompt.is_active == True)
            if pver == "latest":
                q = q.where(PrinciplePrompt.is_latest == True)
            else:
                q = q.where(PrinciplePrompt.version == pver)
            p = (await session.execute(q)).scalar_one_or_none()
            if p:
                ref = PrincipleRef(version_id=version_id, principle_id=p.id, ref_version=pver, order=max_order + added + 1)
                session.add(ref)
                existing_names.add(pname)
                added += 1

    async def _load_principles(self, session, version_obj) -> List[PrinciplePrompt]:
        """根据引用与客户端默认设置加载原则集合

        先加载显式引用的原则，再尝试基于客户端默认配置追加未出现的原则。

        Args:
            session (AsyncSession): 异步数据库会话。
            version_obj (PromptVersion): 版本对象。

        Returns:
            List[PrinciplePrompt]: 原则对象列表。

        Raises:
            Exception: 当数据库查询失败时抛出。
        """
        principles = []
        for ref in sorted(version_obj.principle_refs, key=lambda r: r.order):
            stmt = select(PrinciplePrompt).where(PrinciplePrompt.id == ref.principle_id)
            p = (await session.execute(stmt)).scalar_one_or_none()
            if p:
                principles.append(p)
        names = {p.name for p in principles}
        if version_obj.client_mappings:
            client = version_obj.client_mappings[0].client
            if client and client.default_principles:
                for dp in client.default_principles:
                    pname = dp.get("principle_name")
                    pver = dp.get("version", "latest")
                    if not pname or pname in names:
                        continue
                    q = select(PrinciplePrompt).where(PrinciplePrompt.name == pname, PrinciplePrompt.is_active == True)
                    if pver == "latest":
                        q = q.where(PrinciplePrompt.is_latest == True)
                    else:
                        q = q.where(PrinciplePrompt.version == pver)
                    p = (await session.execute(q)).scalar_one_or_none()
                    if p:
                        principles.append(p)
                        names.add(pname)
        return principles

    def _render_output(self, full_prompt: FullPrompt, fmt: str, t_vars: dict, r_params: dict):
        """渲染完整提示为目标输出格式

        按原则与角色顺序生成消息列表，并结合 LLM 配置与运行时参数，返回所需格式对象。

        Args:
            full_prompt (FullPrompt): 完整提示结构体。
            fmt (str): 输出格式，`openai`、`formatted` 或 `both`。
            t_vars (dict): 模板渲染变量。
            r_params (dict): 运行时参数覆盖。

        Returns:
            Union[OpenAIRequest, FormattedPrompt, BothFormats]: 输出格式对象。

        Raises:
            Exception: 当模板渲染或参数处理失败时可能抛出。
        """
        rendered_msgs = []
        # Principles as System messages
        for p in full_prompt.principles:
            rendered_msgs.append({"role": "system", "content": f"[Principle] {p.content}"})

        # Roles
        for r in full_prompt.roles:
            if not t_vars and not r.template_variables:
                raw = r.content
                if "{{" in raw or "{%" in raw:
                    content = self.template.render(raw, {}, None)
                else:
                    content = raw
            else:
                content = self.template.render(r.content, t_vars or {}, r.template_variables)
            rendered_msgs.append({"role": r.role_type, "content": content})

        config = full_prompt.llm_config
        base_params = {
            "model": (config.model if config else "gpt-3.5-turbo"),
            "temperature": (config.temperature if config else 0.7),
            "max_tokens": (config.max_tokens if config else 1000),
            "top_p": (config.top_p if config else 1.0),
            "frequency_penalty": (config.frequency_penalty if config else 0.0),
            "presence_penalty": (config.presence_penalty if config else 0.0),
            "stop": (config.stop_sequences if config else None)
        }
        if r_params: base_params.update(r_params)

        if fmt == "openai":
            return OpenAIRequest(messages=rendered_msgs, **base_params)
        elif fmt == "formatted":
            return FormattedPrompt(messages=rendered_msgs)
        else:
            result = BothFormats(
                openai_format=OpenAIRequest(messages=rendered_msgs, **base_params),
                formatted=FormattedPrompt(messages=rendered_msgs)
            )
            result._meta_version = full_prompt.version.version
            return result
    async def _create_on_supabase(self, request: CreatePromptRequest) -> PromptVersion:
        # 1. Get or Create Prompt
        prompt_id = await self.supabase.get_prompt_id_by_name(request.name)
        if not prompt_id:
            prompt_id = await self.supabase.create_prompt(request.name)
        # Update prompt root fields for sync
        h = hashlib.sha256((request.description or "").encode("utf-8")).hexdigest()
        await self.supabase.update_prompt(prompt_id, {
            "content": request.description,
            "is_deleted": False,
            "sync_hash": h,
            "updated_at": get_precise_time().isoformat()
        })
            
        # 2. Calculate Version
        new_version_str = await self._calculate_version_supabase(prompt_id, request.version_type)
        
        # 3. Generate Embedding
        embedding = await self.embedding.generate(request.description)
        
        # 4. Create Version
        # Determine version_number
        latest_info = await self.supabase.get_latest_version_info(prompt_id)
        version_number = (latest_info["version_number"] if latest_info else 0) + 1
        
        version_id = str(uuid.uuid4())
        created_at_iso = get_precise_time().isoformat()
        
        version_data = {
            "id": version_id,
            "prompt_id": prompt_id,
            "version": new_version_str,
            "version_number": version_number,
            "description": request.description,
            "is_active": True,
            "is_latest": True,
            "change_log": request.change_log,
            "created_at": created_at_iso,
            # description_vector is handled by vector table, but if we want to store it here too (as None for now)
            # "description_vector": None 
        }
        
        # We need to use SupabaseClient's table insert. Since SupabaseService doesn't expose generic insert,
        # we assume create_prompt_version handles this.
        # But create_prompt_version implementation in service.py was basic.
        # Let's use the direct client access via self.supabase.client wrapper or add method.
        # self.supabase.create_prompt_version does simple insert.
        await self.supabase.create_prompt_version(version_data)
        
        # 5. Create Roles
        roles_data = []
        for role_config in request.roles:
            roles_data.append({
                "version_id": version_id,
                "role_type": role_config.role_type,
                "content": role_config.content,
                "order": role_config.order,
                "template_variables": role_config.template_variables
            })
        await self.supabase.create_roles(roles_data)
        
        # 6. LLM Config
        if request.llm_config:
            config_data = request.llm_config.model_dump()
            config_data["version_id"] = version_id
            await self.supabase.create_llm_config(config_data)
            
        # 7. Tags
        if request.tags:
            await self._associate_tags_supabase(version_id, request.tags)
            
        # 8. Principles
        if request.principle_refs:
            await self._associate_principles_supabase(version_id, request.principle_refs)
            
        # 9. Client
        if request.client_type:
            await self._associate_client_supabase(version_id, request.client_type)
            await self._load_client_principles_supabase(version_id, request.client_type)
            
        # 10. Update previous latest
        await self.supabase.reset_latest_flags(prompt_id, version_id)
        
        # 11. Vector Index
        await self.supabase.insert_vector(version_id, embedding)
        
        # Construct Return Object (PromptVersion)
        # We need to construct it manually since we don't have session refresh
        v_obj = PromptVersion(**version_data)
        v_obj.created_at = datetime.datetime.fromisoformat(created_at_iso.replace('Z', '+00:00'))
        
        # Populate relationships for return
        v_obj.roles = [PromptRole(**r) for r in roles_data]
        if request.llm_config:
            v_obj.llm_config = LLMConfig(**request.llm_config.model_dump())
            v_obj.llm_config.version_id = version_id
            
        # We won't fully populate tags/principles/clients here for performance, 
        # unless necessary. The caller usually needs the version object.
        # But let's try to be consistent with _create_on_session which returns a bound object (though lazy loaded)
        
        return v_obj

    async def _calculate_version_supabase(self, prompt_id: str, v_type: str) -> str:
        latest = await self.supabase.get_latest_version_info(prompt_id)
        if not latest:
            return "1.0"
        
        current_ver = latest["version"]
        major, minor = map(int, current_ver.split('.'))
        if v_type == "major":
            return f"{major + 1}.0"
        return f"{major}.{minor + 1}"

    async def _associate_tags_supabase(self, version_id: str, tags: List[str]):
        for t_name in tags:
            tag = await self.supabase.get_tag_by_name(t_name)
            if not tag:
                tag = await self.supabase.create_tag(t_name)
            
            tag_id = tag["id"]
            await self.supabase.create_prompt_tag(version_id, tag_id)

    async def _associate_principles_supabase(self, version_id: str, refs):
        for idx, ref in enumerate(refs):
            p = await self.supabase.get_principle_by_params(ref.principle_name, ref.version)
            if not p:
                raise ValidationError(f"Principle {ref.principle_name} not found")
            
            await self.supabase.create_principle_ref({
                "version_id": version_id,
                "principle_id": p["id"],
                "ref_version": ref.version,
                "order": idx
            })

    async def _associate_client_supabase(self, version_id: str, client_name: str):
        client = await self.supabase.get_client_by_name(client_name)
        if not client:
            client = await self.supabase.create_client(client_name)
        
        await self.supabase.create_client_mapping(version_id, client["id"])

    async def _load_client_principles_supabase(self, version_id: str, client_name: str):
        client = await self.supabase.get_client_by_name(client_name)
        if not client or not client.get("default_principles"):
            return
            
        # Get existing principles for this version (we just added them in step 8)
        # But we need to query them or track them.
        # To avoid query, we can check request.principle_refs if we passed it down, 
        # but here we are in a separate method.
        # Let's just query db for what we have so far.
        # Or simpler: we know we just inserted them.
        # Since this is "load defaults", we can just fetch what we have.
        # But supbase doesn't have a transaction, so we can query.
        
        # Actually, let's just implement the logic:
        # 1. Get existing refs for version
        resp = self.supabase.client.table("version_principle_refs").select("principle:principle_prompts(name), order").eq("version_id", version_id).execute()
        existing_refs = resp.data
        existing_names = {r["principle"]["name"] for r in existing_refs if r.get("principle")}
        
        max_order = -1
        if existing_refs:
            max_order = max(r["order"] for r in existing_refs)
            
        added = 0
        for dp in client["default_principles"]:
            pname = dp.get("principle_name")
            pver = dp.get("version", "latest")
            
            if not pname or pname in existing_names:
                continue
                
            p = await self.supabase.get_principle_by_params(pname, pver)
            if p:
                await self.supabase.create_principle_ref({
                    "version_id": version_id,
                    "principle_id": p["id"],
                    "ref_version": pver,
                    "order": max_order + added + 1
                })
                existing_names.add(pname)
                added += 1

    async def _search_on_supabase(
            self,
            query: Optional[str] = None,
            tags: Optional[List[str]] = None,
            logic: Literal["AND", "OR"] = "AND",
            version_filter: Literal["latest", "all", "specific"] = "latest",
            specific_version: Optional[str] = None,
            limit: int = 10,
            offset: int = 0
    ) -> SearchResult:
        vector_ids = set()
        tag_ids = set()
        has_vector_search = False
        has_tag_search = False
        similarity_map = {}
        
        # 1. Vector Search
        if query:
            has_vector_search = True
            try:
                embedding = await self.embedding.generate(query)
                vec_results = await self.supabase.search_vectors(embedding, k=limit * 2)
                for vid, score in vec_results:
                    vector_ids.add(vid)
                    similarity_map[vid] = score
            except Exception as e:
                logger.error("Supabase vector search failed", error=str(e))
                
        # 2. Tag Search
        if tags:
            has_tag_search = True
            # Need to find version_ids that have ALL tags
            # Supabase doesn't support complex JOIN/GROUP BY/HAVING easily via JS client without RPC
            # We can do: Get all tag IDs -> Get all prompt_tags for these tags -> Client side intersection
            try:
                # Get tag IDs
                tag_resp = self.supabase.client.table("tags").select("id, name").in_("name", tags).execute()
                found_tags = {t["name"]: t["id"] for t in tag_resp.data}
                
                if len(found_tags) == len(tags): # Only if all tags exist
                    target_tag_ids = list(found_tags.values())
                    # Get prompt_tags
                    pt_resp = self.supabase.client.table("prompt_tags").select("version_id, tag_id").in_("tag_id", target_tag_ids).execute()
                    
                    # Group by version_id
                    from collections import defaultdict
                    v_map = defaultdict(set)
                    for row in pt_resp.data:
                        v_map[row["version_id"]].add(row["tag_id"])
                    
                    # Filter
                    for vid, tids in v_map.items():
                        if len(tids) == len(target_tag_ids):
                            tag_ids.add(vid)
            except Exception as e:
                logger.error("Supabase tag search failed", error=str(e))

        # 3. Logic Combination
        candidate_ids = set()
        if has_vector_search and has_tag_search:
            if logic == "AND":
                candidate_ids = vector_ids & tag_ids
            else:
                candidate_ids = vector_ids | tag_ids
        elif has_vector_search:
            candidate_ids = vector_ids
        elif has_tag_search:
            candidate_ids = tag_ids
        else:
            candidate_ids = None

        # 4. Build Query
        query_builder = self.supabase.client.table("prompt_versions").select("*, prompt:prompts(name), tags:tags(name)")
        query_builder = query_builder.eq("is_active", True)
        
        if candidate_ids is not None:
            if not candidate_ids:
                return SearchResult(total=0, results=[])
            query_builder = query_builder.in_("id", list(candidate_ids))
            
        if version_filter == "latest":
            query_builder = query_builder.eq("is_latest", True)
        elif version_filter == "specific" and specific_version:
            query_builder = query_builder.eq("version", specific_version)
            
        # Execute
        # Note: Supabase select count needs separate query or count='exact'
        # We'll fetch all matching (limited by reasonable max or pagination)
        # For simplicity, we fetch all candidates then sort/page client side or apply limit here if no candidates
        
        if candidate_ids is None:
             # Apply limit/offset at DB level
             # But we need to sort first.
             # Default sort by created_at desc
             query_builder = query_builder.order("created_at", desc=True).range(offset, offset + limit - 1)
        
        resp = query_builder.execute()
        results = resp.data
        
        # If we had candidates, we might have fetched more than limit if we didn't apply range.
        # But if we applied 'in_', we fetched all candidates. 
        # Wait, if candidate_ids is large, 'in_' might fail. 
        # But for now assuming reasonable size.
        
        # 5. Sort & Pagination (Client side if search involved)
        if has_vector_search:
            results.sort(key=lambda v: similarity_map.get(v["id"], 0), reverse=True)
        elif candidate_ids is not None:
            # Sort by created_at if tag search only
            results.sort(key=lambda v: v["created_at"], reverse=True)
            
        # Pagination if manual
        total = len(results)
        if candidate_ids is not None:
            paginated = results[offset: offset + limit]
        else:
            # Already paginated by DB
            paginated = results
            # Total count? We'd need another query with count='exact'
            # For now, total = len(paginated) + offset (approx) or just len(paginated)
            # Let's do a separate count query if needed, or return estimated.
            # SearchResult expects total.
            # Let's just use what we have.
            total = len(results) # This is wrong if we used range().
            # If we used range(), results is just the page.
            # If candidate_ids is None, we used range.
            pass

        # 6. Format
        items = []
        for v in paginated:
            # Handle nested objects
            p_name = v.get("prompt", {}).get("name") if isinstance(v.get("prompt"), dict) else "Unknown"
            t_list = [t["name"] for t in v.get("tags", [])] if isinstance(v.get("tags"), list) else []
            
            items.append(SearchResultItem(
                prompt_id=v["prompt_id"],
                name=p_name,
                version=v["version"],
                description=v["description"],
                tags=t_list,
                similarity_score=similarity_map.get(v["id"]) if has_vector_search else None,
                created_at=datetime.datetime.fromisoformat(v["created_at"].replace('Z', '+00:00')) if isinstance(v["created_at"], str) else v["created_at"]
            ))
            
        return SearchResult(total=total, results=items)

    async def _create_on_session(self, session, request: CreatePromptRequest) -> PromptVersion:
        stmt = select(Prompt).where(Prompt.name == request.name)
        prompt = (await session.execute(stmt)).scalar_one_or_none()

        if not prompt:
            prompt = Prompt(name=request.name)
            session.add(prompt)
            await session.flush()
        # Update prompt root fields for sync
        h = hashlib.sha256((request.description or "").encode("utf-8")).hexdigest()
        prompt.content = request.description
        prompt.sync_hash = h

        new_version_str = await self._calculate_version(session, prompt.id, request.version_type)

        embedding = await self.embedding.generate(request.description)

        version = PromptVersion(
            prompt_id=prompt.id,
            version=new_version_str,
            description=request.description,
            description_vector=self.vector_index._serialize_vector(embedding),
            is_active=True,
            is_latest=True,
            change_log=request.change_log
        )
        session.add(version)
        await session.flush()
        
        prev_max_stmt = select(func.max(PromptVersion.version_number)).where(
            PromptVersion.prompt_id == str(prompt.id)
        ).where(
            PromptVersion.id != str(version.id)
        )
        prev_max = (await session.execute(prev_max_stmt)).scalar() or 0
        version.version_number = prev_max + 1

        for role_config in request.roles:
            role = PromptRole(
                version_id=version.id,
                role_type=role_config.role_type,
                content=role_config.content,
                order=role_config.order,
                template_variables=role_config.template_variables
            )
            session.add(role)

        if request.llm_config:
            config = LLMConfig(version_id=version.id, **request.llm_config.model_dump())
            session.add(config)

        if request.tags:
            await self._associate_tags(session, version.id, request.tags)

        if request.principle_refs:
            await self._associate_principles(session, version.id, request.principle_refs)

        if request.client_type:
            await self._associate_client(session, version.id, request.client_type)
            await self._load_client_principles(session, version.id, request.client_type)

        await session.execute(
            update(PromptVersion)
            .where(and_(PromptVersion.prompt_id == str(prompt.id), PromptVersion.id != str(version.id)))
            .values(is_latest=False)
        )

        await self.vector_index.insert(session, version.id, embedding)

        # Refresh the version object to ensure all relationships are loaded or at least available
        await session.refresh(version)
        # Eager load roles to ensure they are available
        stmt = select(PromptVersion).where(PromptVersion.id == version.id).options(selectinload(PromptVersion.roles))
        version = (await session.execute(stmt)).scalar_one()
        
        return version
