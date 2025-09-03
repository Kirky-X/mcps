"""Workers模块"""

from typing import Optional, TYPE_CHECKING
from .rust_worker import RustWorker
from .python_worker import PythonWorker
from .java_worker import JavaWorker
from .node_worker import NodeWorker
from .go_worker import GoWorker
from .cpp_worker import CppWorker
from ..models import Language

if TYPE_CHECKING:
    from .base import BaseWorker


class WorkerFactory:
    """Worker工厂类 - 负责创建语言特定的Worker实例"""
    
    _workers = {
        Language.RUST: RustWorker,
        Language.PYTHON: PythonWorker,
        Language.JAVA: JavaWorker,
        Language.NODE: NodeWorker,
        Language.GO: GoWorker,
        Language.CPP: CppWorker,
    }
    
    @classmethod
    def create_worker(cls, language: Language, timeout: float = 30.0) -> Optional['BaseWorker']:
        """创建特定语言的Worker实例"""
        worker_class = cls._workers.get(language)
        if not worker_class:
            return None
        
        return worker_class(timeout=timeout)  # type: ignore


# 导出所有Worker类
__all__ = [
    "BaseWorker",
    "RustWorker", 
    "PythonWorker",
    "JavaWorker",
    "NodeWorker",
    "GoWorker",
    "CppWorker",
    "WorkerFactory"
]