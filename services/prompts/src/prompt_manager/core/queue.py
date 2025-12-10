# Copyright (c) Kirky.X. 2025. All rights reserved.
import asyncio
from typing import Any, Tuple, Dict

from ..utils.exceptions import QueueFullError


class UpdateQueue:
    def __init__(self, max_size: int = 100):
        """初始化异步更新队列

        创建带最大容量的 `asyncio.Queue` 存放更新任务，并标记运行状态。

        Args:
            max_size (int): 队列最大长度，默认 100。

        Returns:
            None

        Raises:
            ValueError: 当 `max_size` 小于等于 0 时抛出。
        """
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self.queue = asyncio.Queue(maxsize=max_size)
        self.is_running = False

    async def enqueue(self, name: str, version_number: int, update_data: Dict[str, Any]) -> asyncio.Future:
        """入队一个更新任务并返回结果 Future

        若队列已满则抛出 `QueueFullError`；成功入队后返回等待结果的 `Future`。

        Args:
            name (str): 提示名称。
            version_number (int): 用于冲突检测的版本号。
            update_data (Dict[str, Any]): 更新字段数据。

        Returns:
            asyncio.Future: 任务的 Future 对象，await 该对象可获取结果。

        Raises:
            QueueFullError: 当队列满时抛出。
        """
        if self.queue.full():
            raise QueueFullError("Update queue is full")

        future = asyncio.Future()
        try:
            self.queue.put_nowait((name, version_number, update_data, future))
        except asyncio.QueueFull:
            raise QueueFullError("Update queue is full")
        
        return future

    async def get(self) -> Tuple[str, int, Dict[str, Any], asyncio.Future]:
        """从队列中获取一个待处理任务

        Returns:
            Tuple[str, int, Dict[str, Any], asyncio.Future]: 包含名称、版本号、更新数据与结果 Future。

        Raises:
            Exception: 当队列获取操作失败时可能抛出。
        """
        return await self.queue.get()

    def task_done(self):
        """标记当前任务处理完成"""
        self.queue.task_done()

    async def stop(self):
        """停止队列处理并等待剩余任务完成

        将运行状态置为 False，并在队列非空时等待所有任务完成。

        Args:
            None

        Returns:
            None

        Raises:
            None
        """
        self.is_running = False
        while not self.queue.empty():
            try:
                name, ver, data, future = self.queue.get_nowait()
                if not future.done():
                    future.set_exception(asyncio.CancelledError())
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break
