"""批量处理器"""

from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import time
import logging

from ..models import Task, TaskResult, BatchRequest, BatchResponse, BatchSummary, LibraryQuery
from ..cache import create_cache_manager
from ..core.config import Settings
from ..workers import WorkerFactory


class BatchProcessor:
    """批量处理器 - 负责任务分发和结果聚合"""
    
    def __init__(self, max_workers: int = 10, request_timeout: float = 30.0, 
                 cache_ttl: int = 3600, cache_max_size: int = 1000, settings: Settings = None):
        self.max_workers = max_workers
        self.request_timeout = request_timeout
        self.task_queue: Queue[Task] = Queue()
        
        # 使用缓存管理器工厂函数
        if settings is None:
            settings = Settings()
            settings.cache_ttl = cache_ttl
            settings.cache_max_size = cache_max_size
        
        self.cache_manager = create_cache_manager(settings)
        self.worker_factory = WorkerFactory()
    
    async def process_batch(self, 
                          libraries: List[LibraryQuery], 
                          operation: str) -> BatchResponse:
        """批量处理查询请求"""
        start_time = time.time()
        
        # 操作名称映射
        operation_mapping = {
            "find_latest_versions": "get_latest_version",
            "find_library_docs": "get_documentation_url", 
            "check_versions_exist": "check_version_exists",
            "find_library_dependencies": "get_dependencies"
        }
        
        # 转换操作名称
        worker_operation = operation_mapping.get(operation, operation)
        
        # 1. 任务分解
        tasks = self._create_tasks(libraries, worker_operation)
        
        # 2. 并发执行
        results = await self._execute_tasks(tasks)
        
        # 3. 结果聚合
        total_time = time.time() - start_time
        return self._aggregate_results(results, total_time)
    
    def _create_tasks(self, libraries: List[LibraryQuery], operation: str) -> List[Task]:
        """将批量请求分解为单个任务"""
        tasks = []
        for lib in libraries:
            task = Task(
                language=lib.language,
                library=lib.name,
                version=lib.version,
                operation=operation
            )
            tasks.append(task)
        return tasks
    
    async def _execute_tasks(self, tasks: List[Task]) -> List[TaskResult]:
        """使用通用线程池并发执行任务"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务到通用工作线程
            future_to_task = {
                executor.submit(self._execute_task_with_worker, task): task 
                for task in tasks
            }
            
            # 收集结果
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result(timeout=self.request_timeout)
                    results.append(result)
                except Exception as e:
                    error_result = TaskResult(
                        language=task.language.value,
                        library=task.library,
                        version=task.version,
                        status="error",
                        data=None,
                        error=f"EXECUTION_ERROR: {str(e)}",
                        execution_time=0.0
                    )
                    results.append(error_result)
        
        return results
    
    def _execute_task_with_worker(self, task: Task) -> TaskResult:
        """通用工作线程执行任务，启动特定语言的Worker"""
        start_time = time.time()
        
        try:
            # 1. 检查缓存
            cache_key = self.cache_manager.generate_key(
                task.language.value, task.library, task.operation, task.version
            )
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                # 对于find_latest_versions操作，需要从缓存结果中提取版本信息
                cached_version = task.version
                if task.operation == "get_latest_version" and cached_result and isinstance(cached_result, dict):
                    cached_version = cached_result.get("version", task.version)
                
                return TaskResult(
                    language=task.language.value,
                    library=task.library,
                    version=cached_version,
                    status="success",
                    data=cached_result,
                    error=None,
                    execution_time=0.0
                )
        except Exception as e:
            # 缓存错误不应该阻止任务执行
            logging.warning(f"Cache error for task {task.library}: {e}")
        
        # 获取Worker
        worker = self.worker_factory.create_worker(task.language, self.request_timeout)
        if not worker:
            return TaskResult(
                language=task.language.value,
                library=task.library,
                version=task.version,
                status="error",
                data=None,
                error="WorkerError: Worker creation failed",
                execution_time=0.0
            )
        
        try:
            # 使用Worker执行任务
            result = worker.execute_query(task)
            execution_time = time.time() - start_time
            
            # 尝试缓存结果
            try:
                self.cache_manager.set(cache_key, result)
            except Exception as cache_error:
                logging.warning(f"Failed to cache result for {task.library}: {cache_error}")
            
            # 对于find_latest_versions操作，需要从result中提取版本信息
            result_version = task.version
            if task.operation == "get_latest_version" and result and isinstance(result, dict):
                result_version = result.get("version", task.version)
            
            # 对于check_version_exists操作，按照PRD规范处理输出格式
            if task.operation == "check_version_exists":
                # 从worker结果中提取exists字段，直接构造符合PRD规范的输出
                exists_value = False
                if result and isinstance(result, dict):
                    exists_value = result.get("exists", False)
                
                # 构造符合PRD规范的TaskResult，包含exists字段
                return TaskResult(
                    language=task.language.value,
                    library=task.library,
                    version=task.version,
                    status="success",
                    data={"exists": exists_value},
                    error=None,
                    execution_time=execution_time,
                    exists=exists_value
                )
            
            return TaskResult(
                language=task.language.value,
                library=task.library,
                version=result_version,
                status="success",
                data=result,
                error=None,
                execution_time=execution_time
            )
            
        except Exception as e:
            return TaskResult(
                language=task.language.value,
                library=task.library,
                version=task.version,
                status="error",
                data=None,
                error=f"{type(e).__name__}: {str(e)}",
                execution_time=time.time() - start_time
            )
        finally:
            # 确保Worker资源被正确释放
            if hasattr(worker, 'cleanup'):
                try:
                    worker.cleanup()
                except Exception as cleanup_error:
                    logging.warning(f"Worker cleanup failed: {cleanup_error}")

    
    def _aggregate_results(self, results: List[TaskResult], total_time: float) -> BatchResponse:
        """聚合处理结果"""
        success_count = sum(1 for r in results if r.status == "success")
        failed_count = len(results) - success_count
        
        summary = BatchSummary(
            total=len(results),
            success=success_count,
            failed=failed_count
        )
        
        return BatchResponse(
            results=results,
            summary=summary
        )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.cache_manager.get_stats()
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache_manager.clear()