import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from prompt_manager.services.embedding import EmbeddingService
from prompt_manager.utils.config import VectorConfig
from prompt_manager.dal.vector_index import VectorIndex

class TestDynamicStartup:
    
    @pytest.mark.asyncio
    async def test_embedding_service_get_dimension(self):
        """Test get_dimension logic in EmbeddingService."""
        # Case 1: Config has dimension
        config = VectorConfig(dimension=768, enabled=True)
        service = EmbeddingService(config)
        assert await service.get_dimension() == 768
        
        # Case 2: Config is None, remote infer
        config = VectorConfig(dimension=None, enabled=True, embedding_model="text-embedding-3-small")
        service = EmbeddingService(config)
        # If client is None (no api key), _should_use_local() returns True
        # If it uses local provider, it might return 1024 (BGE-M3) instead of 1536
        # So we mock _should_use_local to return False to test remote inference logic
        with patch.object(service, "_should_use_local", return_value=False):
             assert await service.get_dimension() == 1536
        
        # Case 3: Config is None, local provider
        config = VectorConfig(dimension=None, enabled=True, provider_priority="local_first", local_model_id="test/model")
        service = EmbeddingService(config)
        with patch.object(service.local_provider, "get_dimension", return_value=128):
            assert await service.get_dimension() == 128
            
        # Case 4: Probe
        config = VectorConfig(dimension=None, enabled=True, provider_priority="remote_first", embedding_model="unknown-model")
        service = EmbeddingService(config)
        # Mock generate
        service.generate = AsyncMock(return_value=[0.0] * 64)
        # Again, mock _should_use_local to False to force probing logic (step 3)
        with patch.object(service, "_should_use_local", return_value=False):
            assert await service.get_dimension() == 64

    @pytest.mark.asyncio
    async def test_vector_index_init_with_detected_dim(self):
        """Test that VectorIndex accepts dynamic dimension."""
        idx = VectorIndex(dimension=1024)
        assert idx.dimension == 1024
        
        idx2 = VectorIndex(dimension=None)
        assert idx2.dimension == 1536 # Default fallback
