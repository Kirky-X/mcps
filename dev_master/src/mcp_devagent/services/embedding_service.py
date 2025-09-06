"""Embedding Service

Manages embedding generation using LangChain with multi-provider support
and intelligent routing based on content type and performance metrics.
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_core.embeddings import Embeddings
    import sentence_transformers
except ImportError:
    # Fallback for development without LangChain
    OpenAIEmbeddings = None
    HuggingFaceEmbeddings = None
    Embeddings = None
    sentence_transformers = None


class EmbeddingProvider:
    """Base class for embedding providers."""
    
    def __init__(self, name: str, model: str, dimensions: int, 
                 cost_per_token: float = 0.0):
        self.name = name
        self.model = model
        self.dimensions = dimensions
        self.cost_per_token = cost_per_token
        self.embeddings = None
        self.performance_metrics = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_time": 0.0,
            "error_count": 0,
            "avg_latency": 0.0
        }
    
    async def initialize(self) -> bool:
        """Initialize the embedding provider."""
        raise NotImplementedError
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text."""
        raise NotImplementedError
    
    async def generate_batch_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate embeddings for multiple texts."""
        raise NotImplementedError
    
    def update_metrics(self, tokens: int, latency: float, success: bool):
        """Update performance metrics."""
        self.performance_metrics["total_requests"] += 1
        self.performance_metrics["total_tokens"] += tokens
        self.performance_metrics["total_time"] += latency
        
        if not success:
            self.performance_metrics["error_count"] += 1
        
        # Update average latency
        if self.performance_metrics["total_requests"] > 0:
            self.performance_metrics["avg_latency"] = (
                self.performance_metrics["total_time"] / 
                self.performance_metrics["total_requests"]
            )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        return {
            **self.performance_metrics,
            "error_rate": (
                self.performance_metrics["error_count"] / 
                max(self.performance_metrics["total_requests"], 1)
            ),
            "cost_estimate": (
                self.performance_metrics["total_tokens"] * self.cost_per_token
            )
        }


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider."""
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        dimensions_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        
        cost_map = {
            "text-embedding-3-small": 0.00002,  # $0.02 per 1M tokens
            "text-embedding-3-large": 0.00013,  # $0.13 per 1M tokens
            "text-embedding-ada-002": 0.0001    # $0.10 per 1M tokens
        }
        
        super().__init__(
            name="openai",
            model=model,
            dimensions=dimensions_map.get(model, 1536),
            cost_per_token=cost_map.get(model, 0.0001)
        )
        self.api_key = api_key
    
    async def initialize(self) -> bool:
        """Initialize OpenAI embeddings."""
        try:
            if OpenAIEmbeddings is None:
                raise ImportError("LangChain OpenAI not available")
            
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.api_key,
                model=self.model
            )
            
            # Test with a simple embedding
            test_embedding = await self.embeddings.aembed_query("test")
            if test_embedding and len(test_embedding) == self.dimensions:
                return True
            
            return False
        except Exception as e:
            logging.error(f"Failed to initialize OpenAI embeddings: {e}")
            return False
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using OpenAI."""
        if not self.embeddings:
            return None
        
        start_time = time.time()
        try:
            embedding = await self.embeddings.aembed_query(text)
            latency = time.time() - start_time
            
            # Estimate tokens (rough approximation)
            tokens = len(text.split()) * 1.3
            self.update_metrics(int(tokens), latency, True)
            
            return embedding
        except Exception as e:
            latency = time.time() - start_time
            self.update_metrics(0, latency, False)
            logging.error(f"OpenAI embedding generation failed: {e}")
            return None
    
    async def generate_batch_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate batch embeddings using OpenAI."""
        if not self.embeddings:
            return None
        
        start_time = time.time()
        try:
            embeddings = await self.embeddings.aembed_documents(texts)
            latency = time.time() - start_time
            
            # Estimate total tokens
            total_tokens = sum(len(text.split()) * 1.3 for text in texts)
            self.update_metrics(int(total_tokens), latency, True)
            
            return embeddings
        except Exception as e:
            latency = time.time() - start_time
            self.update_metrics(0, latency, False)
            logging.error(f"OpenAI batch embedding generation failed: {e}")
            return None


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embedding provider using sentence-transformers directly."""
    
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2", 
                 cache_dir: Optional[str] = None):
        dimensions_map = {
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "sentence-transformers/all-distilroberta-v1": 768,
            "sentence-transformers/paraphrase-MiniLM-L6-v2": 384,
            "sentence-transformers/multi-qa-MiniLM-L6-cos-v1": 384
        }
        
        super().__init__(
            name="local",
            model=model,
            dimensions=dimensions_map.get(model, 384),
            cost_per_token=0.0  # Free for local models
        )
        self.cache_dir = cache_dir or os.path.join(os.getcwd(), ".embedding_cache")
        self.model_instance = None
        
    async def initialize(self) -> bool:
        """Initialize local sentence-transformers model."""
        try:
            if sentence_transformers is None:
                raise ImportError("sentence-transformers not available")
            
            # Create cache directory
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Load model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self.model_instance = await loop.run_in_executor(
                None, 
                lambda: sentence_transformers.SentenceTransformer(self.model)
            )
            
            # Test embedding generation
            test_embedding = await self.generate_embedding("test")
            if test_embedding and len(test_embedding) == self.dimensions:
                return True
            
            return False
        except Exception as e:
            logging.error(f"Failed to initialize local embedding model: {e}")
            return False
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        return hashlib.md5(f"{self.model}:{text}".encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path."""
        return Path(self.cache_dir) / f"{cache_key}.pkl"
    
    async def _load_from_cache(self, text: str) -> Optional[List[float]]:
        """Load embedding from cache."""
        try:
            cache_key = self._get_cache_key(text)
            cache_path = self._get_cache_path(cache_key)
            
            if cache_path.exists():
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: pickle.load(open(cache_path, 'rb'))
                )
        except Exception:
            pass
        return None
    
    async def _save_to_cache(self, text: str, embedding: List[float]):
        """Save embedding to cache."""
        try:
            cache_key = self._get_cache_key(text)
            cache_path = self._get_cache_path(cache_key)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: pickle.dump(embedding, open(cache_path, 'wb'))
            )
        except Exception as e:
            logging.warning(f"Failed to cache embedding: {e}")
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using local model with caching."""
        if not self.model_instance:
            return None
        
        # Try cache first
        cached_embedding = await self._load_from_cache(text)
        if cached_embedding is not None:
            return cached_embedding
        
        start_time = time.time()
        try:
            # Generate embedding in thread pool
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None,
                lambda: self.model_instance.encode([text], convert_to_tensor=False)[0].tolist()
            )
            
            latency = time.time() - start_time
            
            # Estimate tokens (rough approximation)
            tokens = len(text.split()) * 1.3
            self.update_metrics(int(tokens), latency, True)
            
            # Cache the result
            await self._save_to_cache(text, embedding)
            
            return embedding
        except Exception as e:
            latency = time.time() - start_time
            self.update_metrics(0, latency, False)
            logging.error(f"Local embedding generation failed: {e}")
            return None
    
    async def generate_batch_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate batch embeddings using local model with caching."""
        if not self.model_instance:
            return None
        
        # Check cache for each text
        results = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cached = await self._load_from_cache(text)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            start_time = time.time()
            try:
                loop = asyncio.get_event_loop()
                uncached_embeddings = await loop.run_in_executor(
                    None,
                    lambda: self.model_instance.encode(uncached_texts, convert_to_tensor=False).tolist()
                )
                
                latency = time.time() - start_time
                
                # Update results and cache
                for i, embedding in enumerate(uncached_embeddings):
                    idx = uncached_indices[i]
                    results[idx] = embedding
                    
                    # Cache the result
                    await self._save_to_cache(uncached_texts[i], embedding)
                
                # Update metrics
                total_tokens = sum(len(text.split()) * 1.3 for text in uncached_texts)
                self.update_metrics(int(total_tokens), latency, True)
                
            except Exception as e:
                latency = time.time() - start_time
                self.update_metrics(0, latency, False)
                logging.error(f"Local batch embedding generation failed: {e}")
                return None
        
        return results


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """HuggingFace embedding provider via LangChain."""
    
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        dimensions_map = {
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "sentence-transformers/all-distilroberta-v1": 768
        }
        
        super().__init__(
            name="huggingface",
            model=model,
            dimensions=dimensions_map.get(model, 384),
            cost_per_token=0.0  # Free for local models
        )
    
    async def initialize(self) -> bool:
        """Initialize HuggingFace embeddings."""
        try:
            if HuggingFaceEmbeddings is None:
                raise ImportError("LangChain HuggingFace not available")
            
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.model,
                model_kwargs={'device': 'cpu'},  # Use CPU for compatibility
                encode_kwargs={'normalize_embeddings': True}
            )
            
            # Test with a simple embedding
            test_embedding = self.embeddings.embed_query("test")
            if test_embedding and len(test_embedding) == self.dimensions:
                return True
            
            return False
        except Exception as e:
            logging.error(f"Failed to initialize HuggingFace embeddings: {e}")
            return False
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using HuggingFace."""
        if not self.embeddings:
            return None
        
        start_time = time.time()
        try:
            # Run in thread pool since HuggingFace is synchronous
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, self.embeddings.embed_query, text
            )
            
            latency = time.time() - start_time
            tokens = len(text.split())
            self.update_metrics(tokens, latency, True)
            
            return embedding
        except Exception as e:
            latency = time.time() - start_time
            self.update_metrics(0, latency, False)
            logging.error(f"HuggingFace embedding generation failed: {e}")
            return None
    
    async def generate_batch_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Generate batch embeddings using HuggingFace."""
        if not self.embeddings:
            return None
        
        start_time = time.time()
        try:
            # Run in thread pool since HuggingFace is synchronous
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None, self.embeddings.embed_documents, texts
            )
            
            latency = time.time() - start_time
            total_tokens = sum(len(text.split()) for text in texts)
            self.update_metrics(total_tokens, latency, True)
            
            return embeddings
        except Exception as e:
            latency = time.time() - start_time
            self.update_metrics(0, latency, False)
            logging.error(f"HuggingFace batch embedding generation failed: {e}")
            return None


class EmbeddingService:
    """Main embedding service with multi-provider support and intelligent routing."""
    
    def __init__(self):
        self.providers: Dict[str, EmbeddingProvider] = {}
        self.default_provider = None
        self.routing_rules = {
            "code": "local",  # Local model for code (fast)
            "documentation": "local",  # Local model for docs
            "comment": "local",  # Local model for comments
            "query": "local",  # Local model for search queries
            "default": "local"  # Default to local model
        }
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize embedding service with configuration.
        
        Args:
            config: {
                "providers": {
                    "openai": {"api_key": "...", "model": "..."},
                    "huggingface": {"model": "..."}
                },
                "default_provider": "huggingface",
                "routing_rules": {...}
            }
        """
        try:
            providers_config = config.get("providers", {})
            
            # Initialize OpenAI provider if configured
            if "openai" in providers_config:
                openai_config = providers_config["openai"]
                if "api_key" in openai_config:
                    provider = OpenAIEmbeddingProvider(
                        api_key=openai_config["api_key"],
                        model=openai_config.get("model", "text-embedding-3-small")
                    )
                    
                    if await provider.initialize():
                        self.providers["openai"] = provider
                        self.logger.info(f"OpenAI embedding provider initialized: {provider.model}")
                    else:
                        self.logger.error("Failed to initialize OpenAI embedding provider")
            
            # Initialize Local provider if configured (default)
            if "local" in providers_config or not providers_config:
                local_config = providers_config.get("local", {})
                provider = LocalEmbeddingProvider(
                    model=local_config.get("model", "sentence-transformers/all-MiniLM-L6-v2"),
                    cache_dir=local_config.get("cache_dir")
                )
                
                if await provider.initialize():
                    self.providers["local"] = provider
                    self.logger.info(f"Local embedding provider initialized: {provider.model}")
                else:
                    self.logger.error("Failed to initialize local embedding provider")
            
            # Initialize HuggingFace provider if configured
            if "huggingface" in providers_config:
                hf_config = providers_config["huggingface"]
                provider = HuggingFaceEmbeddingProvider(
                    model=hf_config.get("model", "sentence-transformers/all-MiniLM-L6-v2")
                )
                
                if await provider.initialize():
                    self.providers["huggingface"] = provider
                    self.logger.info(f"HuggingFace embedding provider initialized: {provider.model}")
                else:
                    self.logger.error("Failed to initialize HuggingFace embedding provider")
            
            # Set default provider
            default_name = config.get("default_provider", "local")
            if default_name in self.providers:
                self.default_provider = self.providers[default_name]
            elif self.providers:
                self.default_provider = list(self.providers.values())[0]
            
            # Update routing rules
            if "routing_rules" in config:
                self.routing_rules.update(config["routing_rules"])
            
            if not self.providers:
                self.logger.error("No embedding providers initialized")
                return False
            
            self.logger.info(f"Embedding service initialized with {len(self.providers)} providers")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize embedding service: {e}")
            return False
    
    def get_provider_for_content(self, content_type: str) -> Optional[EmbeddingProvider]:
        """Get the best provider for given content type."""
        # Check routing rules
        provider_name = self.routing_rules.get(content_type, self.routing_rules.get("default"))
        
        if provider_name in self.providers:
            provider = self.providers[provider_name]
            
            # Check if provider is healthy (low error rate)
            metrics = provider.get_metrics()
            if metrics["error_rate"] < 0.1:  # Less than 10% error rate
                return provider
        
        # Fallback to default provider
        return self.default_provider
    
    async def generate_embedding(self, text: str, model: Optional[str] = None, 
                               content_type: str = "default") -> Optional[Dict[str, Any]]:
        """Generate embedding for text.
        
        Args:
            text: Text to embed
            model: Specific model to use (optional)
            content_type: Type of content for routing
        
        Returns:
            {
                "embedding": List[float],
                "model": str,
                "provider": str,
                "dimensions": int,
                "generation_time": float
            }
        """
        if not text.strip():
            return None
        
        # Select provider
        provider = None
        if model:
            # Find provider with specific model
            for p in self.providers.values():
                if p.model == model:
                    provider = p
                    break
        
        if not provider:
            provider = self.get_provider_for_content(content_type)
        
        if not provider:
            self.logger.error("No suitable embedding provider available")
            return None
        
        start_time = time.time()
        embedding = await provider.generate_embedding(text)
        generation_time = time.time() - start_time
        
        if embedding:
            return {
                "embedding": embedding,
                "model": provider.model,
                "provider": provider.name,
                "dimensions": len(embedding),
                "generation_time": generation_time
            }
        
        return None
    
    async def generate_batch_embeddings(self, texts: List[str], 
                                      model: Optional[str] = None,
                                      content_type: str = "default") -> Optional[Dict[str, Any]]:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            model: Specific model to use (optional)
            content_type: Type of content for routing
        
        Returns:
            {
                "embeddings": List[List[float]],
                "model": str,
                "provider": str,
                "success": bool,
                "generation_time": float
            }
        """
        if not texts:
            return None
        
        # Select provider
        provider = None
        if model:
            for p in self.providers.values():
                if p.model == model:
                    provider = p
                    break
        
        if not provider:
            provider = self.get_provider_for_content(content_type)
        
        if not provider:
            return None
        
        start_time = time.time()
        embeddings = await provider.generate_batch_embeddings(texts)
        generation_time = time.time() - start_time
        
        if embeddings:
            return {
                "embeddings": embeddings,
                "model": provider.model,
                "provider": provider.name,
                "success": True,
                "generation_time": generation_time
            }
        
        return {
            "success": False,
            "error": "Failed to generate batch embeddings"
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get service status and metrics."""
        status = {
            "providers": {},
            "default_provider": self.default_provider.name if self.default_provider else None,
            "routing_rules": self.routing_rules,
            "total_providers": len(self.providers)
        }
        
        for name, provider in self.providers.items():
            status["providers"][name] = {
                "model": provider.model,
                "dimensions": provider.dimensions,
                "metrics": provider.get_metrics()
            }
        
        return status
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models."""
        models = []
        for provider in self.providers.values():
            models.append({
                "provider": provider.name,
                "model": provider.model,
                "dimensions": provider.dimensions,
                "cost_per_token": provider.cost_per_token
            })
        return models