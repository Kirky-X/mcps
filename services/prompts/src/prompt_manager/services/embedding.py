# Copyright (c) Kirky.X. 2025. All rights reserved.
from typing import List, Optional, Sequence

from openai import AsyncOpenAI
from .local_embedding import LocalEmbeddingProvider
from ..core.local_cache import Cache
from datetime import timedelta

from ..utils.config import VectorConfig
from ..utils.exceptions import VectorIndexError
from ..utils.logger import get_logger


class EmbeddingService:
    def __init__(self, config: VectorConfig):
        """初始化嵌入服务客户端

        根据配置启用异步 OpenAI 客户端，若未启用或无密钥则保持 `client=None` 并返回零向量用于开发/测试。

        Args:
            config (VectorConfig): 向量配置，包含维度、模型与 API 密钥等。

        Returns:
            None

        Raises:
            Exception: 当客户端初始化失败时可能抛出异常。
        """
        self.config = config
        self.logger = get_logger(__name__)
        self.client = None
        self.local_provider = LocalEmbeddingProvider(
            model_id=config.local_model_id or "BAAI/bge-m3",
            use_modelscope=config.use_modelscope,
            use_fp16=True,
        )
        if config.enabled and config.embedding_api_key:
            self.client = AsyncOpenAI(api_key=config.embedding_api_key)
        self.result_cache = None
        if getattr(config, "result_cache_enabled", True):
            ttl = timedelta(seconds=getattr(config, "result_cache_ttl_seconds", 3600))
            self.result_cache = Cache.builder() \
                .max_capacity(getattr(config, "result_cache_capacity", 1000)) \
                .time_to_live(ttl) \
                .build()

    async def generate(self, text: str) -> List[float]:
        """生成文本向量嵌入

        当客户端可用时调用 OpenAI Embeddings 接口获取向量；否则返回维度一致的零向量以便在本地开发与测试场景中使用。

        Args:
            text (str): 待生成嵌入的文本内容。

        Returns:
            List[float]: 浮点向量列表，长度为配置中的维度。

        Raises:
            VectorIndexError: 当远端嵌入生成失败时抛出。
        """
        cached = self._cache_get(text)
        if cached is not None:
            return cached
        if self._should_use_local():
            try:
                vecs = self.local_provider.encode([text], batch_size=self.config.batch_size, max_length=self.config.max_length)
                aligned = self._align_dim(vecs[0])
                self._cache_put(text, aligned)
                self._record_usage(local=True, batch_size=1)
                return aligned
            except Exception as le:
                self.logger.error("Local embedding failed", error=str(le))
                aligned = self._align_dim(self._zero_vec())
                self._cache_put(text, aligned)
                return aligned

        try:
            response = await self.client.embeddings.create(
                model=self.config.embedding_model,
                input=text
            )
            vec = list(map(float, response.data[0].embedding))
            aligned = self._align_dim(vec)
            self._cache_put(text, aligned)
            return aligned
        except Exception as e:
            self.logger.error("Remote embedding failed, switching to local", error=str(e))
            try:
                vecs = self.local_provider.encode([text], batch_size=self.config.batch_size, max_length=self.config.max_length)
                aligned = self._align_dim(vecs[0])
            except Exception as le:
                self.logger.error("Local embedding failed after remote error", error=str(le))
                aligned = self._align_dim(self._zero_vec())
            self._cache_put(text, aligned)
            self._record_usage(local=True, batch_size=1)
            return aligned

    def _should_use_local(self, force: bool = False) -> bool:
        pri = (self.config.provider_priority or "remote_first").lower()
        if force:
            return True
        if pri == "local_first":
            return True
        if pri == "remote_first":
            return not self.client
        return not self.client

    async def generate_batch(self, texts: Sequence[str]) -> List[List[float]]:
        if self._should_use_local():
            try:
                vecs = self.local_provider.encode(list(texts), batch_size=self.config.batch_size, max_length=self.config.max_length)
                aligned = [self._align_dim(v) for v in vecs]
            except Exception as le:
                self.logger.error("Local batch embedding failed", error=str(le))
                aligned = [self._align_dim(self._zero_vec()) for _ in texts]
            for t, v in zip(texts, aligned):
                self._cache_put(t, v)
            self._record_usage(local=True, batch_size=len(texts))
            return aligned
        try:
            response = await self.client.embeddings.create(
                model=self.config.embedding_model,
                input=list(texts)
            )
            out = [self._align_dim(list(map(float, d.embedding))) for d in response.data]
            for t, v in zip(texts, out):
                self._cache_put(t, v)
            return out
        except Exception as e:
            self.logger.error("Remote batch embedding failed, switching to local", error=str(e))
            if not self._should_use_local(force=True):
                raise VectorIndexError(f"Embedding batch generation failed: {str(e)}")
            try:
                vecs = self.local_provider.encode(list(texts), batch_size=self.config.batch_size, max_length=self.config.max_length)
                aligned = [self._align_dim(v) for v in vecs]
            except Exception as le:
                self.logger.error("Local batch embedding failed after remote error", error=str(le))
                aligned = [self._align_dim(self._zero_vec()) for _ in texts]
            for t, v in zip(texts, aligned):
                self._cache_put(t, v)
            self._record_usage(local=True, batch_size=len(texts))
            return aligned

    def _align_dim(self, vec: List[float]) -> List[float]:
        target = self.config.dimension
        if target is None:
            return vec
        n = len(vec)
        if n == target:
            return vec
        if n > target:
            return vec[:target]
        return vec + [0.0] * (target - n)

    def _cache_get(self, key: str) -> Optional[List[float]]:
        if self.result_cache:
            v = self.result_cache.get(f"emb:{self.config.embedding_model}:{key}")
            if v is not None:
                return v
        return None

    def _cache_put(self, key: str, value: List[float]) -> None:
        if self.result_cache:
            self.result_cache.insert(f"emb:{self.config.embedding_model}:{key}", value)

    def _record_usage(self, local: bool, batch_size: int):
        try:
            import psutil  # type: ignore
            import os
            mem = psutil.Process(os.getpid()).memory_info().rss
            info = {"rss_mb": round(mem / (1024*1024), 2), "batch": batch_size, "local": local}
            # Try GPU if available
            try:
                import torch  # type: ignore
                if torch.cuda.is_available():
                    info["cuda_alloc_mb"] = round(torch.cuda.memory_allocated() / (1024*1024), 2)
            except Exception:
                pass
            self.logger.info("Embedding usage", **info)
        except Exception:
            pass

    async def get_dimension(self) -> int:
        """获取当前生效的向量维度
        
        如果配置中明确指定了 dimension，直接返回。
        否则尝试探测模型维度（优先探测本地模型，其次根据远端模型名称推断）。
        
        Returns:
            int: 向量维度
        """
        if self.config.dimension:
            return self.config.dimension
            
        # 1. If using local provider, ask it
        if self._should_use_local():
            try:
                return self.local_provider.get_dimension()
            except Exception as e:
                self.logger.warning(f"Failed to get dimension from local provider: {e}")
                
        # 2. If remote, infer from model name
        model_name = self.config.embedding_model.lower()
        if "text-embedding-3-large" in model_name:
            return 3072
        if "text-embedding-3-small" in model_name or "ada-002" in model_name:
            return 1536
            
        # 3. Probe by generating a dummy embedding
        try:
            vec = await self.generate("test")
            return len(vec)
        except Exception as e:
            self.logger.warning(f"Failed to probe embedding dimension: {e}")
            
        # 4. Ultimate fallback
        return 1536

    def _zero_vec(self) -> List[float]:
        return [0.0] * max(1, self.config.dimension or 1536)
