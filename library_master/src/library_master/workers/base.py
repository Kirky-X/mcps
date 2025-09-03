"""Worker基类"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import httpx
import time
import logging
from urllib.parse import urljoin

from ..models import Task
from ..exceptions import LibraryNotFoundError, UpstreamError, TimeoutError
from ..core.mirror_config import MCPMirrorConfig, MCPFailoverManager, Language


class BaseWorker(ABC):
    """语言Worker基类 - 由通用工作线程启动的特定语言查询执行器"""
    
    def __init__(self, language: Language, timeout: float = 60.0):
        self.language = language
        # 增加超时时间和重试配置
        self.client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=30.0, read=30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            transport=httpx.HTTPTransport(retries=3)
        )
        self.base_url = self._get_base_url()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 镜像源配置和故障转移管理
        self.mirror_config = MCPMirrorConfig()
        self.failover_manager = MCPFailoverManager()
        
        # 获取有效的URL列表
        self.effective_urls = self.mirror_config.get_effective_urls(language)
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 1.0
    
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
    
    def _make_request(self, endpoint: str, **kwargs) -> httpx.Response:
        """发起带故障转移和重试的HTTP请求"""
        last_exception = None
        
        for base_url in self.effective_urls:
            # 检查URL是否可用（熔断器模式）
            if not self._is_url_available(base_url):
                self.logger.debug(f"Skipping unavailable URL: {base_url}")
                continue
            
            full_url = self._build_url(base_url, endpoint)
            
            # 对每个URL进行重试
            for retry_count in range(self.max_retries):
                self.logger.debug(f"Making request to: {full_url} (attempt {retry_count + 1}/{self.max_retries})")
                
                try:
                    response = self.client.get(full_url, **kwargs)
                    response.raise_for_status()
                    
                    # 记录成功
                    self._record_success(base_url)
                    self.logger.debug(f"Request successful: {full_url} -> {response.status_code}")
                    return response
                    
                except httpx.HTTPStatusError as e:
                    self.logger.warning(f"HTTP error for {full_url}: {e.response.status_code} (attempt {retry_count + 1})")
                    
                    if e.response.status_code == 404:
                        # 404错误不重试，直接抛出
                        raise LibraryNotFoundError(f"Resource not found: {full_url}")
                    elif e.response.status_code >= 500:
                        # 服务器错误，可以重试
                        last_exception = UpstreamError(f"HTTP {e.response.status_code}: {e.response.text}")
                        if retry_count < self.max_retries - 1:
                            time.sleep(self.retry_delay * (retry_count + 1))  # 指数退避
                            continue
                    else:
                        # 客户端错误，不重试
                        self._record_failure(base_url)
                        last_exception = UpstreamError(f"HTTP {e.response.status_code}: {e.response.text}")
                        break
                        
                except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                    self.logger.warning(f"Network error for {full_url}: {str(e)} (attempt {retry_count + 1})")
                    last_exception = TimeoutError(f"Network error: {str(e)}")
                    if retry_count < self.max_retries - 1:
                        time.sleep(self.retry_delay * (retry_count + 1))  # 指数退避
                        continue
                    
                except Exception as e:
                    self.logger.error(f"Unexpected error for {full_url}: {str(e)} (attempt {retry_count + 1})")
                    last_exception = UpstreamError(f"Unexpected error: {str(e)}")
                    if retry_count < self.max_retries - 1:
                        time.sleep(self.retry_delay * (retry_count + 1))
                        continue
            
            # 所有重试都失败了，记录故障
            self._record_failure(base_url)
        
        # 所有URL都失败了
        if last_exception:
            raise last_exception
        else:
            raise UpstreamError("All mirror sources are unavailable")
    
    def _build_url(self, base_url: str, endpoint: str) -> str:
        """构建完整的URL"""
        # 确保endpoint以/开头
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        return urljoin(base_url.rstrip('/') + '/', endpoint.lstrip('/'))
    
    def _is_url_available(self, url: str) -> bool:
        """检查URL是否可用（同步版本）"""
        # 这里使用简化的检查逻辑，实际应用中可以实现更复杂的熔断器
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，使用简化的检查
            return True  # 简化处理，假设URL可用
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.failover_manager.is_url_available(url))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
    
    def _record_success(self, url: str) -> None:
        """记录成功请求（同步版本）"""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，跳过记录
            return
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.failover_manager.record_success(url))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
    
    def _record_failure(self, url: str) -> None:
        """记录失败请求（同步版本）"""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，跳过记录
            return
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.failover_manager.record_failure(url))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
    
    def get_failure_stats(self) -> Dict[str, Any]:
        """获取故障统计信息"""
        return self.failover_manager.get_failure_stats()
    
    def close(self) -> None:
        """关闭HTTP客户端"""
        if hasattr(self, 'client'):
            self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()