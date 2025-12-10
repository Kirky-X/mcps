from __future__ import annotations

import threading
import contextlib
from typing import List, Optional, Dict, Any

_bgem3_singleton_lock = threading.Lock()
_bgem3_singleton: Dict[str, Any] = {}


@contextlib.contextmanager
def _suppress_model_logs():
    """Context manager to suppress logging and progress bars from transformers and tqdm."""
    # Lazy import to avoid overhead if not used
    try:
        from transformers import logging as hf_logging
    except ImportError:
        hf_logging = None

    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = None

    # Suppress HF logging
    prev_verbosity = None
    if hf_logging:
        prev_verbosity = hf_logging.get_verbosity()
        hf_logging.set_verbosity_error()

    # Suppress Python standard logging for specific loggers that might leak through
    # FlagEmbedding uses standard logging
    loggers_to_suppress = ["FlagEmbedding", "transformers", "modelscope"]
    prev_log_levels = {}
    import logging
    for logger_name in loggers_to_suppress:
        logger = logging.getLogger(logger_name)
        prev_log_levels[logger_name] = logger.level
        logger.setLevel(logging.ERROR)

    # Suppress tqdm
    original_tqdm_init = None
    if tqdm:
        original_tqdm_init = tqdm.__init__
        def nop_tqdm_init(self, *args, **kwargs):
            kwargs['disable'] = True
            original_tqdm_init(self, *args, **kwargs)
        tqdm.__init__ = nop_tqdm_init

    try:
        yield
    finally:
        if hf_logging and prev_verbosity is not None:
            hf_logging.set_verbosity(prev_verbosity)
        
        for logger_name, level in prev_log_levels.items():
            logging.getLogger(logger_name).setLevel(level)

        if tqdm and original_tqdm_init:
            tqdm.__init__ = original_tqdm_init


def _detect_device() -> str:
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    try:
        import torch_directml as _tdml  # type: ignore
        return "directml"
    except Exception:
        pass
    return "cpu"


def _download_with_modelscope(model_id: str) -> str:
    try:
        from modelscope.hub.snapshot_download import snapshot_download  # type: ignore
        local_dir = snapshot_download(model_id)
        return local_dir
    except Exception as e:
        raise RuntimeError(f"ModelScope download failed: {e}")


def _load_bgem3(model_id: str, use_modelscope: bool, use_fp16: bool, device: Optional[str] = None):
    global _bgem3_singleton
    key = f"{model_id}|fp16={use_fp16}|ms={use_modelscope}"
    with _bgem3_singleton_lock:
        if key in _bgem3_singleton:
            return _bgem3_singleton[key]
            
        with _suppress_model_logs():
            # Prefer to import model class first to avoid unnecessary network during tests
            from FlagEmbedding import BGEM3FlagModel  # type: ignore
            local_dir = None
            if use_modelscope:
                try:
                    local_dir = _download_with_modelscope(model_id)
                except Exception:
                    local_dir = None
            if device is None:
                device = _detect_device()
            model = BGEM3FlagModel(local_dir or model_id, use_fp16=use_fp16, device=device)
            _bgem3_singleton[key] = model
            return model


class LocalEmbeddingProvider:
    def __init__(self, model_id: str = "BAAI/bge-m3", use_modelscope: bool = True, use_fp16: bool = True):
        self.model_id = model_id
        self.use_modelscope = use_modelscope
        self.use_fp16 = use_fp16
        self.model = None

    def ensure_loaded(self):
        if self.model is None:
            try:
                with _suppress_model_logs():
                    self.model = _load_bgem3(self.model_id, self.use_modelscope, self.use_fp16)
            except Exception as e:
                raise RuntimeError(f"Local model load failed: {e}")

    def encode(self, sentences: List[str], batch_size: int = 12, max_length: int = 8192) -> List[List[float]]:
        self.ensure_loaded()
        
        with _suppress_model_logs():
            # Pass verbose=False to suppress progress bar if supported by kwargs
            # Based on BGE-M3 implementation, it might use tqdm internally
            out = self.model.encode(
                sentences,
                batch_size=batch_size,
                max_length=max_length,
                verbose=False
            )["dense_vecs"]
            
            return [list(map(float, vec)) for vec in out]

    def get_dimension(self) -> int:
        """Get the dimension of the embedding model.
        
        Returns:
            int: The dimension size (e.g. 1024 for BGE-M3).
        """
        self.ensure_loaded()
        # BGE-M3 typically outputs 1024 dim dense vectors
        # We can probe it by encoding a dummy string
        try:
            with _suppress_model_logs():
                vecs = self.encode(["test"], batch_size=1, max_length=32)
                if vecs and len(vecs) > 0:
                    return len(vecs[0])
        except Exception:
            pass
        return 1024  # Fallback default for BGE-M3
