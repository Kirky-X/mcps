# Copyright (c) Kirky.X. 2025. All rights reserved.
import struct
import json
from typing import List, Tuple, Any

from sqlalchemy import text, Table, Column, String, MetaData, select, delete as sa_delete, literal_column, bindparam
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.logger import get_logger
from .types import PGVector

logger = get_logger(__name__)


class VectorIndex:
    def __init__(self, dimension: int = 1536):
        """初始化向量索引工具

        记录向量维度信息用于创建虚拟表和序列化向量写入/查询。
        支持 SQLite (via sqlite-vec) 和 PostgreSQL (via pgvector)。

        Args:
            dimension (int): 向量维度，需与嵌入模型输出一致，默认 1536。

        Returns:
            None

        Raises:
            ValueError: 当维度小于等于 0 时抛出。
        """
        # 如果传入 None，则暂时使用默认值 1536 避免报错，或者允许动态（后续逻辑需兼容）
        # 但现有逻辑大量依赖 self.dimension，因此这里还是强制一个默认值
        # 如果上层配置是 None，这里会接收到默认值 1536（见调用处），或者我们需要允许 None
        # 但 sqlite-vec 需要固定维度建表，所以这里还是保留 dimension 字段
        # 只是在使用时，如果是动态维度，可能需要重新建表或使用 fallback
        
        if dimension is None:
            self.dimension = 1536
        else:
            self.dimension = dimension

        if self.dimension <= 0:
            raise ValueError("dimension must be positive")
            
        self.use_virtual = True  # For SQLite

    def _serialize_vector(self, embedding: List[float]) -> bytes:
        """Deprecated alias for _serialize_vector_sqlite. Kept for backward compatibility with tests."""
        return self._serialize_vector_sqlite(embedding)

    def _serialize_vector_sqlite(self, embedding: List[float]) -> bytes:
        """序列化浮点向量为字节流 (SQLite)"""
        if not embedding:
            raise ValueError("embedding must not be empty")
        return struct.pack(f'{len(embedding)}f', *embedding)
    
    def _format_vector_postgres(self, embedding: List[float]) -> str:
        """格式化向量为字符串 (PostgreSQL pgvector)"""
        if not embedding:
            raise ValueError("embedding must not be empty")
        return json.dumps(embedding)

    async def create_index(self, session: AsyncSession):
        """创建用于向量检索的表

        - SQLite: 创建 `vec_prompts` 虚拟表 (sqlite-vec)
        - PostgreSQL: 启用 `vector` 扩展并创建表 (pgvector)

        Args:
            session (AsyncSession): 异步数据库会话。
        """
        bind = session.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", "")

        try:
            if dialect_name == "postgresql":
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await session.execute(text(f"""
                    CREATE TABLE IF NOT EXISTS vec_prompts (
                        version_id TEXT PRIMARY KEY,
                        description_vector vector({self.dimension})
                    )
                """))
            else:
                async_conn = await session.connection()
                def _load_ext(sync_conn):
                    raw = getattr(sync_conn, "connection", sync_conn)
                    try:
                        import sqlite3
                        if isinstance(raw, sqlite3.Connection):
                            try:
                                raw.enable_load_extension(True)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        import sqlite_vec
                        sqlite_vec.load(raw)
                    except Exception:
                        pass
                    try:
                        import sqlite3
                        if isinstance(raw, sqlite3.Connection):
                            try:
                                raw.enable_load_extension(False)
                            except Exception:
                                pass
                    except Exception:
                        pass
                await async_conn.run_sync(_load_ext)
                await session.execute(text(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS vec_prompts USING vec0(
                        version_id TEXT PRIMARY KEY,
                        description_vector FLOAT[{self.dimension}]
                    )
                """))
                try:
                    # Verify sqlite-vec by issuing a simple MATCH that returns distance
                    zero_json = json.dumps([0.0] * self.dimension)
                    await session.execute(
                        text("SELECT version_id, distance FROM vec_prompts WHERE description_vector MATCH :query LIMIT 1"),
                        {"query": zero_json}
                    )
                    self.use_virtual = True
                except Exception as e:
                    err_msg = str(e).lower()
                    if "dimension mismatch" in err_msg or "size mismatch" in err_msg:
                        logger.warning(f"Vector dimension mismatch detected (expected {self.dimension}). Recreating table 'vec_prompts'...")
                        # Drop and recreate
                        await session.execute(text("DROP TABLE IF EXISTS vec_prompts"))
                        await session.execute(text(f"""
                            CREATE VIRTUAL TABLE IF NOT EXISTS vec_prompts USING vec0(
                                version_id TEXT PRIMARY KEY,
                                description_vector FLOAT[{self.dimension}]
                            )
                        """))
                        self.use_virtual = True
                        logger.info("Table 'vec_prompts' recreated successfully with correct dimension.")
                    else:
                        logger.info(f"sqlite-vec extension verification failed: {e}")
                        raise Exception(f"sqlite-vec extension check failed: {e}")

        except Exception as e:
            if dialect_name != "postgresql":
                logger.info(f"SQLite vector search init failed, falling back to basic table: {e}")
                self.use_virtual = False
                await session.execute(text(
                    "CREATE TABLE IF NOT EXISTS vec_prompts (version_id TEXT PRIMARY KEY, description_vector BLOB)"
                ))
            else:
                # PostgreSQL should ideally not fail here if configured correctly
                logger.error(f"PostgreSQL vector setup failed: {e}")
                raise e

    async def insert(self, session: AsyncSession, version_id: str, embedding: List[float]):
        """插入或更新版本的向量索引"""
        if len(embedding) != self.dimension:
            raise ValueError(f"Embedding dimension mismatch: expected {self.dimension}, got {len(embedding)}")

        bind = session.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", "")

        if dialect_name == "postgresql":
            md = MetaData()
            table = Table(
                "vec_prompts",
                md,
                Column("version_id", String, primary_key=True),
                Column("description_vector", PGVector(self.dimension)),
            )
            stmt = pg_insert(table).values(
                version_id=bindparam("id"),
                description_vector=bindparam("vec")
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[table.c.version_id],
                set_={"description_vector": bindparam("vec")}
            )
            await session.execute(stmt, {"id": version_id, "vec": json.dumps(embedding)})
        else:
            vec_bytes = self._serialize_vector_sqlite(embedding)
            md = MetaData()
            table = Table(
                "vec_prompts",
                md,
                Column("version_id", String, primary_key=True),
                Column("description_vector"),
            )
            if self.use_virtual:
                stmt = table.insert().prefix_with("OR REPLACE").values(
                    version_id=bindparam("id"),
                    description_vector=bindparam("vec")
                )
                await session.execute(stmt, {"id": version_id, "vec": vec_bytes})
            else:
                stmt = sqlite_insert(table).values(
                    version_id=bindparam("id"),
                    description_vector=bindparam("vec")
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=[table.c.version_id],
                    set_={"description_vector": bindparam("vec")}
                )
                await session.execute(stmt, {"id": version_id, "vec": vec_bytes})

    async def search(self, session: AsyncSession, query_embedding: List[float], k: int = 10) -> List[Tuple[str, float]]:
        """基于查询向量执行相似检索"""
        if len(query_embedding) != self.dimension:
            raise ValueError(f"Query embedding dimension mismatch: expected {self.dimension}, got {len(query_embedding)}")

        bind = session.get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", "")

        if dialect_name == "postgresql":
            md = MetaData()
            table = Table(
                "vec_prompts",
                md,
                Column("version_id", String, primary_key=True),
                Column("description_vector", PGVector(self.dimension)),
            )
            q = bindparam("query")
            stmt = (
                select(
                    table.c.version_id,
                    table.c.description_vector.op("<=>")(q).label("distance"),
                )
                .order_by(literal_column("distance").asc())
                .limit(k)
            )
            vec_str = self._format_vector_postgres(query_embedding)
            result = await session.execute(stmt, {"query": vec_str})
            rows = result.fetchall()
            return [(row[0], float(row[1])) for row in rows]

        elif self.use_virtual:
            try:
                result = await session.execute(
                    text(
                        """
                        SELECT version_id, distance
                        FROM vec_prompts
                        WHERE description_vector MATCH :query
                        ORDER BY distance LIMIT :k
                        """
                    ),
                    {"query": json.dumps(query_embedding), "k": k}
                )
                return result.fetchall()
            except Exception as e:
                logger.error(f"SQLite vector search failed: {e}")
                return []
        else:
            # Fallback client-side calculation for SQLite without extension
            md = MetaData()
            table = Table(
                "vec_prompts",
                md,
                Column("version_id", String, primary_key=True),
                Column("description_vector"),
            )
            rows = (await session.execute(select(table.c.version_id, table.c.description_vector))).fetchall()
            
            import math
            def _dist(a: List[float], b: List[float]) -> float:
                return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
            
            q = query_embedding
            results = []
            for vid, vec_bytes in rows:
                vec = list(struct.unpack(f'{self.dimension}f', vec_bytes))
                d = _dist(q, vec)
                results.append((vid, d))
            results.sort(key=lambda x: x[1])
            return results[:k]

    async def delete(self, session: AsyncSession, version_id: str):
        md = MetaData()
        table = Table(
            "vec_prompts",
            md,
            Column("version_id", String, primary_key=True),
            Column("description_vector"),
        )
        stmt = sa_delete(table).where(table.c.version_id == bindparam("id"))
        await session.execute(stmt, {"id": version_id})
