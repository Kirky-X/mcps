# Copyright (c) Kirky.X. 2025. All rights reserved.
class PromptManagerError(Exception):
    """提示管理器基础异常类型

    作为所有提示管理器相关异常的基类，便于统一捕获与处理。

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    pass


class PromptNotFoundError(PromptManagerError):
    """当提示或指定版本未找到时抛出异常

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    pass


class ValidationError(PromptManagerError):
    """输入校验失败异常

    当请求参数或模板变量等校验失败时抛出。

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    pass


class OptimisticLockError(PromptManagerError):
    """更新时发生版本冲突异常

    在乐观锁机制下，当前版本号与最新版本不一致时抛出。

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    pass


class QueueFullError(PromptManagerError):
    """更新队列已满异常

    当尝试入队更新任务时队列已达最大容量抛出。

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    pass


class TemplateRenderError(PromptManagerError):
    """模板渲染失败异常

    当 Jinja2 模板解析或渲染过程出现错误时抛出。

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    pass


class DatabaseError(PromptManagerError):
    """数据库操作异常
    
    当数据库操作失败（如连接失败、查询错误）时抛出。
    """
    pass


class VectorIndexError(PromptManagerError):
    """向量操作失败异常

    当嵌入生成或向量索引相关操作失败时抛出。

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    pass


class DatabaseError(PromptManagerError):
    """数据库操作失败异常

    当数据库连接、查询、更新等操作失败时抛出。

    Args:
        None

    Returns:
        None

    Raises:
        None
    """
    pass
