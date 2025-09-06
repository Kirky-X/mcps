"""Embedding Service tests for MCP DevAgent.

Tests embedding generation, multi-provider support, and intelligent routing.
"""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from src.mcp_devagent.services.embedding_service import (
    EmbeddingService, EmbeddingProvider, OpenAIEmbeddingProvider, 
    HuggingFaceEmbeddingProvider
)


class TestEmbeddingProvider(unittest.TestCase):
    """Test base EmbeddingProvider functionality."""
    
    def test_provider_initialization_and_metrics(self):
        """Test provider initialization and metrics updating."""
        provider = EmbeddingProvider("test_provider", "test_model", 384, 0.001)
        
        # Test initialization
        self.assertEqual(provider.name, "test_provider")
        self.assertEqual(provider.model, "test_model")
        self.assertEqual(provider.dimensions, 384)
        self.assertEqual(provider.cost_per_token, 0.001)
        self.assertIsNone(provider.embeddings)
        self.assertEqual(provider.performance_metrics["total_requests"], 0)
        self.assertEqual(provider.performance_metrics["total_tokens"], 0)
        self.assertEqual(provider.performance_metrics["avg_latency"], 0.0)
        
        # Test metrics update
        provider.update_metrics(100, 0.5, True)  # 100 tokens, 0.5s latency, success
        
        self.assertEqual(provider.performance_metrics["total_requests"], 1)
        self.assertEqual(provider.performance_metrics["total_tokens"], 100)
        self.assertEqual(provider.performance_metrics["avg_latency"], 0.5)
        self.assertEqual(provider.performance_metrics["error_count"], 0)
        
        # Update again with failure
        provider.update_metrics(200, 1.0, False)  # 200 tokens, 1.0s latency, failure
        
        self.assertEqual(provider.performance_metrics["total_requests"], 2)
        self.assertEqual(provider.performance_metrics["total_tokens"], 300)
        self.assertEqual(provider.performance_metrics["avg_latency"], 0.75)  # (0.5 + 1.0) / 2
        self.assertEqual(provider.performance_metrics["error_count"], 1)
    
    def test_provider_metrics(self):
        """Test provider metrics reporting."""
        provider = EmbeddingProvider("test_provider", "test_model", 384, 0.001)
        provider.update_metrics(100, 0.5, True)
        
        metrics = provider.get_metrics()
        
        self.assertEqual(metrics["total_requests"], 1)
        self.assertEqual(metrics["total_tokens"], 100)
        self.assertEqual(metrics["avg_latency"], 0.5)
        self.assertEqual(metrics["error_rate"], 0.0)
        self.assertEqual(metrics["cost_estimate"], 0.1)  # 100 * 0.001


class TestOpenAIEmbeddingProvider(unittest.TestCase):
    """Test OpenAI embedding provider."""
    
    def setUp(self):
        """Set up OpenAI provider for testing."""
        self.provider = OpenAIEmbeddingProvider(
            api_key="test_openai_key",
            model="text-embedding-3-small"
        )
    
    def test_openai_provider_initialization(self):
        """Test OpenAI provider initialization."""
        self.assertEqual(self.provider.name, "openai")
        self.assertEqual(self.provider.model, "text-embedding-3-small")
        self.assertEqual(self.provider.dimensions, 1536)
        self.assertEqual(self.provider.api_key, "test_openai_key")
    
    @patch('src.mcp_devagent.services.embedding_service.OpenAIEmbeddings')
    async def test_openai_initialize_success(self, mock_openai_embeddings):
        """Test successful OpenAI provider initialization."""
        # Mock OpenAI embeddings
        mock_embeddings = MagicMock()
        mock_openai_embeddings.return_value = mock_embeddings
        mock_embeddings.aembed_query = AsyncMock(return_value=[0.1] * 1536)
        
        result = await self.provider.initialize()
        
        self.assertTrue(result)
        self.assertIsNotNone(self.provider.embeddings)
        mock_openai_embeddings.assert_called_once_with(
            openai_api_key="test_openai_key",
            model="text-embedding-3-small"
        )
    
    @patch('src.mcp_devagent.services.embedding_service.OpenAIEmbeddings')
    async def test_openai_initialize_failure(self, mock_openai_embeddings):
        """Test failed OpenAI provider initialization."""
        mock_openai_embeddings.side_effect = Exception("API Error")
        
        result = await self.provider.initialize()
        
        self.assertFalse(result)
        self.assertIsNone(self.provider.embeddings)
    
    @patch('src.mcp_devagent.services.embedding_service.OpenAIEmbeddings')
    async def test_openai_generate_embedding(self, mock_openai_embeddings):
        """Test OpenAI embedding generation."""
        # Mock embeddings
        mock_embeddings = MagicMock()
        mock_openai_embeddings.return_value = mock_embeddings
        mock_embeddings.aembed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])
        
        await self.provider.initialize()
        result = await self.provider.generate_embedding("test text")
        
        self.assertEqual(result, [0.1, 0.2, 0.3])
        mock_embeddings.aembed_query.assert_called_with("test text")


class TestHuggingFaceEmbeddingProvider(unittest.TestCase):
    """Test HuggingFace embedding provider."""
    
    def setUp(self):
        """Set up HuggingFace provider for testing."""
        self.provider = HuggingFaceEmbeddingProvider(
            model="sentence-transformers/all-MiniLM-L6-v2"
        )
    
    def test_huggingface_provider_initialization(self):
        """Test HuggingFace provider initialization."""
        self.assertEqual(self.provider.name, "huggingface")
        self.assertEqual(self.provider.model, "sentence-transformers/all-MiniLM-L6-v2")
        self.assertEqual(self.provider.dimensions, 384)
        self.assertEqual(self.provider.cost_per_token, 0.0)
    
    @patch('src.mcp_devagent.services.embedding_service.HuggingFaceEmbeddings')
    async def test_huggingface_initialize_success(self, mock_hf_embeddings):
        """Test successful HuggingFace provider initialization."""
        # Mock HuggingFace embeddings
        mock_embeddings = MagicMock()
        mock_hf_embeddings.return_value = mock_embeddings
        mock_embeddings.embed_query.return_value = [0.1] * 384
        
        result = await self.provider.initialize()
        
        self.assertTrue(result)
        self.assertIsNotNone(self.provider.embeddings)
        mock_hf_embeddings.assert_called_once_with(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    
    @patch('src.mcp_devagent.services.embedding_service.HuggingFaceEmbeddings')
    async def test_huggingface_generate_embedding(self, mock_hf_embeddings):
        """Test HuggingFace embedding generation."""
        # Mock embeddings
        mock_embeddings = MagicMock()
        mock_hf_embeddings.return_value = mock_embeddings
        mock_embeddings.embed_query.return_value = [0.1, 0.2, 0.3]
        
        await self.provider.initialize()
        
        # Mock asyncio.get_event_loop().run_in_executor
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor = AsyncMock(return_value=[0.1, 0.2, 0.3])
            
            result = await self.provider.generate_embedding("test text")
            
            self.assertEqual(result, [0.1, 0.2, 0.3])
            mock_loop.run_in_executor.assert_called_once()


class TestEmbeddingService(unittest.TestCase):
    """Test EmbeddingService functionality."""
    
    def setUp(self):
        """Set up embedding service for testing."""
        self.service = EmbeddingService()
        
        # Mock configuration
        self.config = {
            "providers": {
                "openai": {
                    "api_key": "test_openai_key",
                    "model": "text-embedding-3-small"
                },
                "huggingface": {
                    "model": "sentence-transformers/all-MiniLM-L6-v2"
                }
            },
            "default_provider": "huggingface",
            "routing_rules": {
                "code": "openai",
                "documentation": "huggingface"
            }
        }
    
    def test_service_initialization(self):
        """Test embedding service initialization."""
        self.assertEqual(len(self.service.providers), 0)
        self.assertIsNone(self.service.default_provider)
        self.assertIn("code", self.service.routing_rules)
        self.assertIn("documentation", self.service.routing_rules)
    
    @patch('src.mcp_devagent.services.embedding_service.OpenAIEmbeddingProvider')
    @patch('src.mcp_devagent.services.embedding_service.HuggingFaceEmbeddingProvider')
    def test_service_initialize_success(self, mock_hf_provider, mock_openai_provider):
        """Test successful service initialization."""
        # Mock providers
        mock_openai = MagicMock()
        mock_openai.initialize = AsyncMock(return_value=True)
        mock_openai.model = "text-embedding-3-small"
        mock_openai_provider.return_value = mock_openai
        
        mock_hf = MagicMock()
        mock_hf.initialize = AsyncMock(return_value=True)
        mock_hf.model = "sentence-transformers/all-MiniLM-L6-v2"
        mock_hf_provider.return_value = mock_hf
        
        result = asyncio.run(self.service.initialize(self.config))
        
        self.assertTrue(result)
        self.assertEqual(len(self.service.providers), 2)
        self.assertIn("openai", self.service.providers)
        self.assertIn("huggingface", self.service.providers)
        self.assertEqual(self.service.default_provider, mock_hf)  # huggingface is default
    
    @patch('src.mcp_devagent.services.embedding_service.LocalEmbeddingProvider')
    def test_service_initialize_no_providers(self, mock_local_provider):
        """Test service initialization with no providers configured but local provider fails."""
        # Mock local provider to fail initialization
        mock_provider = MagicMock()
        mock_provider.initialize = AsyncMock(return_value=False)
        mock_local_provider.return_value = mock_provider
        
        empty_config = {"providers": {}}
        
        result = asyncio.run(self.service.initialize(empty_config))
        
        self.assertFalse(result)
        self.assertEqual(len(self.service.providers), 0)
    
    def test_get_provider_for_content(self):
        """Test provider selection based on content type."""
        # Mock providers
        mock_local = MagicMock()
        mock_local.get_metrics.return_value = {"error_rate": 0.02}
        mock_hf = MagicMock()
        mock_hf.get_metrics.return_value = {"error_rate": 0.03}
        
        self.service.providers = {"local": mock_local, "huggingface": mock_hf}
        self.service.default_provider = mock_local
        
        # Test routing rules (default routing rules route code to local)
        provider = self.service.get_provider_for_content("code")
        self.assertEqual(provider, mock_local)
        
        provider = self.service.get_provider_for_content("documentation")
        self.assertEqual(provider, mock_local)
        
        provider = self.service.get_provider_for_content("unknown")
        self.assertEqual(provider, mock_local)  # Falls back to default
    
    @patch('src.mcp_devagent.services.embedding_service.OpenAIEmbeddingProvider')
    def test_generate_embedding_success(self, mock_openai_provider):
        """Test successful embedding generation."""
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.generate_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_provider.model = "test-model"
        mock_provider.name = "openai"
        mock_openai_provider.return_value = mock_provider
        
        self.service.providers = {"openai": mock_provider}
        self.service.default_provider = mock_provider
        
        result = asyncio.run(self.service.generate_embedding("test text"))
        
        self.assertIsNotNone(result)
        self.assertEqual(result["embedding"], [0.1, 0.2, 0.3])
        self.assertEqual(result["model"], "test-model")
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["dimensions"], 3)
        self.assertIn("generation_time", result)
    
    def test_generate_embedding_no_provider(self):
        """Test embedding generation with no available provider."""
        result = asyncio.run(self.service.generate_embedding("test text"))
        
        self.assertIsNone(result)
    
    def test_generate_embedding_empty_text(self):
        """Test embedding generation with empty text."""
        result = asyncio.run(self.service.generate_embedding(""))
        
        self.assertIsNone(result)
    
    def test_get_status(self):
        """Test service status reporting."""
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.name = "test"
        mock_provider.model = "test-model"
        mock_provider.dimensions = 384
        mock_provider.get_metrics.return_value = {
            "total_requests": 10,
            "avg_latency": 0.5,
            "error_rate": 0.1
        }
        
        self.service.providers = {"test": mock_provider}
        self.service.default_provider = mock_provider
        
        status = asyncio.run(self.service.get_status())
        
        self.assertEqual(status["total_providers"], 1)
        self.assertEqual(status["default_provider"], "test")
        self.assertIn("test", status["providers"])
        self.assertEqual(status["providers"]["test"]["model"], "test-model")
    
    def test_get_available_models(self):
        """Test getting available models."""
        # Mock providers
        mock_openai = MagicMock()
        mock_openai.name = "openai"
        mock_openai.model = "text-embedding-3-small"
        mock_openai.dimensions = 1536
        mock_openai.cost_per_token = 0.00002
        
        mock_hf = MagicMock()
        mock_hf.name = "huggingface"
        mock_hf.model = "sentence-transformers/all-MiniLM-L6-v2"
        mock_hf.dimensions = 384
        mock_hf.cost_per_token = 0.0
        
        self.service.providers = {"openai": mock_openai, "huggingface": mock_hf}
        
        models = self.service.get_available_models()
        
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["provider"], "openai")
        self.assertEqual(models[0]["model"], "text-embedding-3-small")
        self.assertEqual(models[1]["provider"], "huggingface")
        self.assertEqual(models[1]["cost_per_token"], 0.0)


if __name__ == '__main__':
    unittest.main()