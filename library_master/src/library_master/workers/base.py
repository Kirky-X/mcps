"""Worker基类"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx
import time
import logging

from ..models import Task
from ..exceptions import LibraryNotFoundError, UpstreamError, TimeoutError


class BaseWorker(ABC):
    """语言Worker基类 - 由通用工作线程启动的特定语言查询执行器"""
    
    def __init__(self, timeout: float = 30.0):
        self.client = httpx.Client(timeout=timeout)  # 同步客户端，适合线程环境
        self.base_url = self._get_base_url()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def _get_base_url(self) -> str:
        """获取API基础URL"""
        pass
    
    def execute_query(self, task: Task) -> Dict[str, Any]:
        """执行查询任务"""
        operation = task.operation
        
        if operation == "get_latest_version":
            result = self.get_latest_version(task.library)
            return result if isinstance(result, dict) else {"version": result}
        elif operation == "get_documentation_url":
            if task.version:
                version = task.version
            else:
                # 如果没有指定版本，先获取最新版本
                latest_result = self.get_latest_version(task.library)
                version = latest_result.get("version") if isinstance(latest_result, dict) else latest_result
            result = self.get_documentation_url(task.library, version)
            return result if isinstance(result, dict) else {"doc_url": result}
        elif operation == "check_version_exists":
            if not task.version:
                raise ValueError("Version is required for check_version_exists operation")
            result = self.check_version_exists(task.library, task.version)
            return result if isinstance(result, dict) else {"exists": result}
        elif operation == "get_dependencies":
            if task.version:
                version = task.version
            else:
                # 如果没有指定版本，先获取最新版本
                latest_result = self.get_latest_version(task.library)
                version = latest_result.get("version") if isinstance(latest_result, dict) else latest_result
            result = self.get_dependencies(task.library, version)
            return result if isinstance(result, dict) else {"dependencies": result}
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    @abstractmethod
    def get_latest_version(self, library: str) -> Dict[str, Any]:
        """获取最新版本"""
        pass
    
    @abstractmethod
    def get_documentation_url(self, library: str, version: str) -> Dict[str, Any]:
        """获取文档URL"""
        pass
    
    @abstractmethod
    def check_version_exists(self, library: str, version: str) -> Dict[str, Any]:
        """检查版本是否存在"""
        pass
    
    @abstractmethod
    def get_dependencies(self, library: str, version: str) -> Dict[str, Any]:
        """获取依赖关系"""
        pass
    
    def _make_request(self, url: str, **kwargs) -> httpx.Response:
        """发起HTTP请求"""
        self.logger.debug(f"Making request to: {url}")
        try:
            response = self.client.get(url, **kwargs)
            response.raise_for_status()
            self.logger.debug(f"Request successful: {url} -> {response.status_code}")
            return response
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"HTTP error for {url}: {e.response.status_code}")
            if e.response.status_code == 404:
                raise LibraryNotFoundError(f"Resource not found: {url}")
            else:
                raise UpstreamError(f"HTTP {e.response.status_code}: {e.response.text}")
        except httpx.TimeoutException:
            self.logger.error(f"Request timeout: {url}")
            raise TimeoutError(f"Request timeout: {url}")
        except Exception as e:
            self.logger.error(f"Request failed for {url}: {str(e)}")
            raise UpstreamError(f"Request failed: {str(e)}")
    
    def close(self) -> None:
        """关闭HTTP客户端"""
        if hasattr(self, 'client'):
            self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()