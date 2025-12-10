import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from prompt_manager.services.embedding import EmbeddingService
from prompt_manager.services.local_embedding import LocalEmbeddingProvider
from prompt_manager.utils.config import VectorConfig
from prompt_manager.utils.exceptions import VectorIndexError


class TestEmbeddingServiceDynamic:
    @pytest.mark.asyncio
    async def test_dynamic_dimension_from_local(self):
        """Test that dynamic dimension (None) preserves local provider output dimension."""
        # dimension=None means dynamic
        config = VectorConfig(
            dimension=None,
            enabled=False,
            embedding_model="text-embedding-3-small",
            embedding_api_key=None,
            provider_priority="local_first"
        )
        service = EmbeddingService(config)
        
        # Mock local provider returning 1024-dim vector
        # For test simplicity, use small dim
        fake_vec = [0.1] * 10
        with patch.object(LocalEmbeddingProvider, "encode", return_value=[fake_vec]):
            vec = await service.generate("test")
            assert len(vec) == 10
            assert vec == fake_vec

    @pytest.mark.asyncio
    async def test_dynamic_dimension_from_remote(self):
        """Test that dynamic dimension (None) preserves remote provider output dimension."""
        config = VectorConfig(
            dimension=None,
            enabled=True,
            embedding_model="text-embedding-3-small",
            embedding_api_key="sk-test"
        )
        service = EmbeddingService(config)
        
        # Mock OpenAI client response with arbitrary dimension
        mock_response = MagicMock()
        mock_data = MagicMock()
        # suppose remote model returns 7-dim vector
        fake_vec = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        mock_data.embedding = fake_vec
        mock_response.data = [mock_data]
        
        service.client.embeddings.create = AsyncMock(return_value=mock_response)
        
        vec = await service.generate("test")
        assert len(vec) == 7
        assert vec == fake_vec

    @pytest.mark.asyncio
    async def test_mixed_dimensions_in_batch(self):
        """Test batch generation with dynamic dimension."""
        config = VectorConfig(
            dimension=None,
            enabled=False,
            provider_priority="local_first"
        )
        service = EmbeddingService(config)
        
        # Mock local provider returning vectors
        vecs = [[1.0, 2.0], [3.0, 4.0, 5.0]]
        with patch.object(LocalEmbeddingProvider, "encode", return_value=vecs):
            out = await service.generate_batch(["a", "b"])
            assert len(out) == 2
            assert len(out[0]) == 2
            assert len(out[1]) == 3
