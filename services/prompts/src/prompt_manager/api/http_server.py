# Copyright (c) Kirky.X. 2025. All rights reserved.
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ..core.cache import CacheManager
from ..core.manager import PromptManager
from ..core.queue import UpdateQueue
from ..dal.database import Database
from ..dal.vector_index import VectorIndex
from sqlmodel import SQLModel
from ..models.schemas import CreatePromptRequest, SearchRequest, GetRequest, CreatePrincipleRequest, UpdatePromptRequest
from ..services.embedding import EmbeddingService
from ..services.template import TemplateService
from ..services.supabase_service import SupabaseService as GenericSupabaseService
from ..dal.supabase.service import SupabaseService as DomainSupabaseService
from ..services.config_service import ConfigService
from ..services.sync_engine import SyncEngine
from ..utils.config import load_config, SupabaseConfig
from ..utils.exceptions import PromptManagerError, OptimisticLockError, ValidationError, PromptNotFoundError
from ..utils.logger import setup_logging, get_logger
from ..infrastructure.time_network import (
    start_background_monitor,
    stop_background_monitor,
    start_supabase_time_task,
    stop_supabase_time_task,
)

# Import models to ensure SQLModel knows about them for create_all
from ..models import orm
from ..auth.models import Base as AuthBase
from ..auth.router import router as auth_router, current_active_user

logger = get_logger(__name__)


async def _init_supabase_schema(connection_string: str, dimension: int = 1536):
    """Initialize database schema for Supabase using direct connection"""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        # Create temporary engine for DDL
        engine = create_async_engine(connection_string, echo=False)
        
        logger.info("Checking and creating tables for Supabase...")
        async with engine.begin() as conn:
            # 1. Create standard tables via SQLModel
            await conn.run_sync(SQLModel.metadata.create_all)
            
            # 2. Enable pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            
            # 3. Create vec_prompts table for vector storage (not managed by SQLModel)
            # We use the detected dimension for the vector column
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS vec_prompts (
                    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
                    version_id varchar NOT NULL REFERENCES prompt_versions(id) ON DELETE CASCADE,
                    description_vector vector({dimension}),
                    created_at timestamptz DEFAULT now()
                );
                CREATE INDEX IF NOT EXISTS idx_vec_prompts_version_id ON vec_prompts(version_id);
            """))
            
            # 4. Create match_prompt_versions RPC function for similarity search
            # Note: We use dynamic SQL to inject dimension if needed, though vector ops work with matching dims
            await conn.execute(text(f"""
                CREATE OR REPLACE FUNCTION match_prompt_versions (
                    query_embedding vector({dimension}),
                    match_threshold float,
                    match_count int
                )
                RETURNS TABLE (
                    id varchar,
                    similarity float
                )
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RETURN QUERY
                    SELECT
                        v.version_id as id,
                        1 - (v.description_vector <=> query_embedding) as similarity
                    FROM vec_prompts v
                    WHERE 1 - (v.description_vector <=> query_embedding) > match_threshold
                    ORDER BY v.description_vector <=> query_embedding
                    LIMIT match_count;
                END;
                $$;
            """))
        
        await engine.dispose()
        logger.info("Supabase tables and vector functions verification/creation completed")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase schema: {e}")
        raise e


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 应用生命周期管理器

    在应用启动阶段完成配置加载、日志初始化、核心组件构建与更新队列启动；在关闭阶段有序终止队列、释放数据库资源。

    Args:
        app (FastAPI): 当前 FastAPI 应用实例。

    Returns:
        AsyncIterator[None]: 上下文管理的异步迭代器。

    Raises:
        Exception: 当启动或关闭过程中的任意步骤失败时可能抛出异常。
    """
    # Startup
    config = load_config()
    setup_logging(config.logging)
    start_background_monitor()

    # Initialize Embedding Service early to detect dimension
    embedding = EmbeddingService(config.vector)
    dim = await embedding.get_dimension()
    logger.info(f"Detected embedding dimension: {dim}")
    
    # Update config if needed, or just use dim
    if config.vector.dimension is None:
        config.vector.dimension = dim

    db = Database(config.database)
    supabase_service = None
    supabase_time_task = None

    if config.database.type == "supabase":
        try:
            if config.database.connection_string:
                await _init_supabase_schema(config.database.connection_string, dim)

            supabase_config = SupabaseConfig(
                url=config.database.supabase_url or "",
                key=config.database.supabase_key or ""
            )
            generic_service = GenericSupabaseService(supabase_config)
            await generic_service.initialize()
            supabase_service = DomainSupabaseService(generic_service)
            app.state.supabase_service = supabase_service
            app.state.db_initialized = True
            logger.info("Supabase initialized successfully")

            app.state.vector_index = VectorIndex(config.vector.dimension)
            supabase_time_task = start_supabase_time_task(generic_service, interval_seconds=60)
        except Exception as e:
            logger.error("Supabase initialization failed", error=str(e))
            raise
    else:
        if not getattr(app.state, "db_initialized", False):
            try:
                async with db.engine.begin() as conn:
                    await conn.run_sync(SQLModel.metadata.create_all)
                    await conn.run_sync(AuthBase.metadata.create_all)

                async with db.get_session() as session:
                    idx = VectorIndex(config.vector.dimension)
                    await idx.create_index(session)
                    await session.commit()
                    app.state.vector_index = idx

                app.state.db_initialized = True
                logger.info("database initialized successfully")
            except Exception as e:
                logger.error("database initialization failed", error=str(e))
                raise
        else:
            if not hasattr(app.state, "vector_index"):
                try:
                    async with db.get_session() as session:
                        idx = VectorIndex(config.vector.dimension)
                        await idx.create_index(session)
                        app.state.vector_index = idx
                except Exception as e:
                    logger.error("Vector index init failed during startup check", error=str(e))
                    app.state.vector_index = VectorIndex(config.vector.dimension)

    cache = CacheManager(config)
    queue = UpdateQueue(config.concurrency.get("queue_max_size", 100))
    # embedding = EmbeddingService(config.vector) # Moved up
    template = TemplateService()
    
    # Initialize Vector Index
    # Use detected dimension
    vector_index = VectorIndex(dim)

    # Initialize DB tables (Simulated here, usually done via Alembic)
    # In a real run, we assume init_db.py was run.

    manager = PromptManager(db, cache, queue, embedding, template, vector_index, supabase_service)
    # Initialize ConfigService and attach to app state
    app.state.config_service = ConfigService(db, supabase_service)
    app.state.manager = manager

    # Initialize SyncEngine only when Supabase is configured as primary DB
    if supabase_service:
        app.state.sync_engine = SyncEngine(db, supabase_service, app.state.config_service)

    # Start Queue Processor
    queue_task = asyncio.create_task(manager.process_update_queue())

    yield

    # Shutdown
    queue_task.cancel()
    try:
        await queue.stop()
    finally:
        if db.engine:
            await db.engine.dispose()
        stop_background_monitor()
        stop_supabase_time_task(supabase_time_task)


app = FastAPI(title="Prompt Manager API", lifespan=lifespan)
app.include_router(auth_router)


def get_manager(request: Request) -> PromptManager:
    """获取全局 PromptManager 实例

    从应用状态中检索在生命周期启动阶段创建的 `PromptManager`，用于依赖注入。

    Args:
        request (Request): 当前请求对象。

    Returns:
        PromptManager: 管理器实例。

    Raises:
        AttributeError: 当应用状态未初始化管理器时可能抛出。
    """
    return request.app.state.manager


def get_sync_engine(request: Request) -> SyncEngine:
    se = getattr(request.app.state, "sync_engine", None)
    if not se:
        raise HTTPException(status_code=503, detail="Sync engine unavailable")
    return se


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.status_code, "message": exc.detail or "Error"})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"code": 422, "message": "Unprocessable Entity", "errors": exc.errors()})

@app.post("/prompts")
async def create_prompt(request: CreatePromptRequest, manager: PromptManager = Depends(get_manager), user=Depends(current_active_user)):
    """创建新的提示版本

    根据请求体创建或追加提示版本，返回关键标识信息。

    Args:
        request (CreatePromptRequest): 创建请求载荷。
        manager (PromptManager): 依赖注入的提示管理器。

    Returns:
        dict: 包含 `prompt_id`、`version` 与 `version_id` 的响应数据。

    Raises:
        HTTPException: 当业务错误或内部异常发生时抛出相应状态码。
    """
    try:
        result = await manager.create(request)
        return {
            "code": 200,
            "message": "success",
            "data": {
                "prompt_id": result.prompt_id,
                "version": result.version,
                "version_id": result.id
            }
        }
    except PromptManagerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Create failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/prompts/search")
async def search_prompts(request: SearchRequest, manager: PromptManager = Depends(get_manager), user=Depends(current_active_user)):
    """搜索提示版本

    支持基于向量语义与标签的组合搜索，并返回分页与相似度信息。

    Args:
        request (SearchRequest): 搜索条件载荷。
        manager (PromptManager): 依赖注入的提示管理器。

    Returns:
        dict: 标准响应，`data` 为搜索结果结构体。

    Raises:
        HTTPException: 当内部错误发生时抛出 500。
    """
    try:
        result = await manager.search(**request.model_dump())
        return {"code": 200, "message": "success", "data": result.model_dump()}
    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/prompts/get")
async def get_prompt(request: GetRequest, manager: PromptManager = Depends(get_manager), user=Depends(current_active_user)):
    """获取提示并按指定格式输出

    根据名称与可选版本返回 OpenAI 或格式化消息结构，支持同时返回两种格式。

    Args:
        request (GetRequest): 获取请求载荷。
        manager (PromptManager): 依赖注入的提示管理器。

    Returns:
        dict: 标准响应，`data` 为所选输出格式的模型字典。

    Raises:
        HTTPException: 当业务错误或内部异常发生时抛出相应状态码。
    """
    try:
        result = await manager.get(**request.model_dump())
        return {"code": 200, "message": "success", "data": result}
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PromptManagerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Get prompt failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/principles")
async def create_principle(request: CreatePrincipleRequest, manager: PromptManager = Depends(get_manager), user=Depends(current_active_user)):
    try:
        result = await manager.create_principle(
            request.name,
            request.version,
            request.content,
            request.is_active,
            request.is_latest,
        )
        return {
            "code": 200,
            "message": "success",
            "data": {
                "id": result.id,
                "name": result.name,
                "version": result.version,
                "is_active": result.is_active,
                "is_latest": result.is_latest,
            },
        }
    except PromptManagerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Create principle failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.put("/prompts/{name}")
async def update_prompt(
    name: str,
    version_number: int,
    request: CreatePromptRequest,
    manager: PromptManager = Depends(get_manager),
    user=Depends(current_active_user)
):
    """更新提示版本

    Args:
        name (str): 提示名称。
        version_number (int): 乐观锁版本号。
        request (CreatePromptRequest): 更新请求载荷。
        manager (PromptManager): 依赖注入的提示管理器。

    Returns:
        dict: 包含新版本信息的响应数据。

    Raises:
        HTTPException: 当业务错误或内部异常发生时抛出相应状态码。
    """
    try:
        # The request body has 'name' but we also have path param 'name'.
        # Usually path param overrides or must match.
        # manager.update takes **kwargs for CreatePromptRequest fields.
        update_data = request.model_dump(exclude={"name"}) # name is in path, or we trust path
        
        result = await manager.update(name, version_number, **update_data)
        return {
            "code": 200,
            "message": "success",
            "data": {
                "prompt_id": result.prompt_id,
                "version": result.version,
                "version_id": result.id
            }
        }
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except OptimisticLockError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PromptManagerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Update failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.delete("/prompts/{name}")
async def delete_prompt(
    name: str,
    version: Optional[str] = None,
    manager: PromptManager = Depends(get_manager),
    user=Depends(current_active_user)
):
    """删除提示版本

    Args:
        name (str): 提示名称。
        version (Optional[str]): 版本号，为空时删除所有版本。
        manager (PromptManager): 依赖注入的提示管理器。

    Returns:
        dict: 操作状态。

    Raises:
        HTTPException: 当业务错误或内部异常发生时抛出相应状态码。
    """
    try:
        await manager.delete(name, version)
        return {"code": 200, "message": "success"}
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PromptManagerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Delete failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/prompts/{name}/versions/{version}/activate")
async def activate_prompt_version(
    name: str,
    version: str,
    set_as_latest: bool = False,
    manager: PromptManager = Depends(get_manager),
    user=Depends(current_active_user)
):
    """激活指定提示版本

    Args:
        name (str): 提示名称。
        version (str): 版本号。
        set_as_latest (bool): 是否同时设为最新版本。
        manager (PromptManager): 依赖注入的提示管理器。

    Returns:
        dict: 操作状态。

    Raises:
        HTTPException: 当业务错误或内部异常发生时抛出相应状态码。
    """
    try:
        await manager.activate(name, version, set_as_latest)
        return {"code": 200, "message": "success"}
    except PromptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PromptManagerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Activate failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/sync")
async def run_sync(engine: SyncEngine = Depends(get_sync_engine), user=Depends(current_active_user)):
    try:
        result = await engine.sync()
        return {"code": 200, "message": "success", "data": result}
    except Exception as e:
        logger.error("Sync failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")
@app.get("/protected/ping")
async def protected_ping(user=Depends(current_active_user)):
    return {"code": 200, "message": "success", "data": {"user_id": str(user.id)}}
