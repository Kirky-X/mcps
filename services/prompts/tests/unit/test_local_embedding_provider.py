import pytest
from unittest.mock import patch

from prompt_manager.services.local_embedding import LocalEmbeddingProvider


class TestLocalEmbeddingProvider:
    def test_device_detection_cpu(self):
        prov = LocalEmbeddingProvider()
        # ensure we don't actually load
        with patch("prompt_manager.services.local_embedding._load_bgem3", side_effect=RuntimeError("x")):
            with pytest.raises(RuntimeError):
                prov.ensure_loaded()

    def test_encode_calls_model(self):
        prov = LocalEmbeddingProvider()
        # The lambda must accept **kwargs because the real code now passes verbose=False
        fake_model = type("M", (), {"encode": lambda self, s, batch_size=12, max_length=8192, **kwargs: {"dense_vecs": [[1.0,2.0],[3.0,4.0]]}})()
        with patch("prompt_manager.services.local_embedding._load_bgem3", return_value=fake_model):
            out = prov.encode(["a","b"], batch_size=2, max_length=16)
            assert out == [[1.0,2.0],[3.0,4.0]]

