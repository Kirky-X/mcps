import asyncio
import os
import pytest

from prompt_manager.services.embedding import EmbeddingService
from prompt_manager.utils.config import VectorConfig


if os.getenv("RUN_BENCH") != "1":
    pytest.skip("Benchmarks disabled", allow_module_level=True)


@pytest.mark.benchmark(group="embedding")
def test_local_batch_perf(benchmark):
    cfg = VectorConfig(
        dimension=1024,
        enabled=False,
        embedding_model="text-embedding-3-small",
        provider_priority="local_first",
        max_length=128,
        batch_size=8,
    )
    service = EmbeddingService(cfg)
    texts = [f"text {i}" for i in range(32)]

    def run_sync():
        return asyncio.run(service.generate_batch(texts))

    result = benchmark(run_sync)
    assert len(result) == len(texts)
    assert len(result[0]) == cfg.dimension
