# Copyright (c) Kirky.X. 2025. All rights reserved.
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from prompt_manager.services.embedding import EmbeddingService
from prompt_manager.services.local_embedding import LocalEmbeddingProvider
from prompt_manager.utils.config import VectorConfig
from prompt_manager.utils.exceptions import VectorIndexError


class TestEmbeddingService:
    def test_init_without_key(self):
        """Test initialization without API key (default disabled)."""
        config = VectorConfig(
            dimension=1536,
            enabled=False,
            embedding_model="text-embedding-3-small",
            embedding_api_key=None
        )
        service = EmbeddingService(config)
        assert service.client is None

    def test_init_with_key_and_enabled(self):
        """Test initialization with API key and enabled."""
        config = VectorConfig(
            dimension=1536,
            enabled=True,
            embedding_model="text-embedding-3-small",
            embedding_api_key="sk-test"
        )
        service = EmbeddingService(config)
        assert service.client is not None
        assert service.client.api_key == "sk-test"

    @pytest.mark.asyncio
    async def test_generate_local_fallback(self):
        """Test local fallback generation (zero vector)."""
        config = VectorConfig(
            dimension=4,
            enabled=False,
            embedding_model="text-embedding-3-small",
            embedding_api_key=None
        )
        service = EmbeddingService(config)
        
        vector = await service.generate("test")
        assert len(vector) == 4
        # Now local provider is used when remote disabled; dimension align pads/truncates
        assert isinstance(vector, list)

    @pytest.mark.asyncio
    async def test_generate_api_success(self):
        """Test successful API generation."""
        config = VectorConfig(
            dimension=4,
            enabled=True,
            embedding_model="text-embedding-3-small",
            embedding_api_key="sk-test"
        )
        service = EmbeddingService(config)
        
        # Mock OpenAI client response
        mock_response = MagicMock()
        mock_data = MagicMock()
        mock_data.embedding = [0.1, 0.2, 0.3, 0.4]
        mock_response.data = [mock_data]
        
        service.client.embeddings.create = AsyncMock(return_value=mock_response)
        
        vector = await service.generate("test")
        assert vector == [0.1, 0.2, 0.3, 0.4]
        service.client.embeddings.create.assert_awaited_once_with(
            model="text-embedding-3-small",
            input="test"
        )

    @pytest.mark.asyncio
    async def test_generate_api_failure(self):
        """Test API failure handling."""
        config = VectorConfig(
            dimension=4,
            enabled=True,
            embedding_model="text-embedding-3-small",
            embedding_api_key="sk-test"
        )
        service = EmbeddingService(config)
        
        service.client.embeddings.create = AsyncMock(side_effect=Exception("API Error"))
        
        # Should fallback to local provider instead of raising
        with patch.object(LocalEmbeddingProvider, "encode", return_value=[[0.3,0.4,0.5,0.6]]):
            vec = await service.generate("test")
            assert vec == [0.3,0.4,0.5,0.6]

    @pytest.mark.asyncio
    async def test_generate_batch_local(self):
        config = VectorConfig(
            dimension=4,
            enabled=False,
            embedding_model="text-embedding-3-small",
            embedding_api_key=None,
            provider_priority="local_first"
        )
        service = EmbeddingService(config)
        with patch.object(LocalEmbeddingProvider, "encode", return_value=[[1,2,3,4],[2,3,4,5]]):
            out = await service.generate_batch(["a","b"])
            assert out == [[1,2,3,4],[2,3,4,5]]
