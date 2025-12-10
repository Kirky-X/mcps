# Copyright (c) Kirky.X. 2025. All rights reserved.
import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    """拦截并转发标准库日志到 Loguru

    通过自定义 `logging.Handler` 将 Python 标准库 `logging` 产出的日志事件转发至 Loguru，实现统一的日志收集与格式化，便于与第三方库（如 SQLAlchemy、Uvicorn）日志整合。

    Args:
        None

    Returns:
        None

    Raises:
        Exception: 处理过程中如底层记录不兼容可能抛出异常。
    """

    def emit(self, record):
        """处理一条标准库日志记录并转发到 Loguru

        Args:
            record (logging.LogRecord): 标准库日志记录对象。

        Returns:
            None

        Raises:
            Exception: 当日志级别映射或帧查找失败时可能抛出异常。
        """
        # 获取对应的 Loguru 日志级别
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 查找调用日志的原始帧
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(config: dict):
    """配置并初始化 Loguru 日志系统

    根据提供的配置移除默认 handler，设置控制台及文件输出目标，并拦截标准库 `logging`。该函数确保 `extra["name"]` 始终存在以统一模块名展示。

    Args:
        config (dict): 日志配置字典，包括 `level`、`console_output`、`file_path` 等键。

    Returns:
        None

    Raises:
        Exception: 当日志目标配置无效或写入失败时可能抛出异常。
    """
    # 1. 移除默认的 handler
    logger.remove()

    # 2. 获取日志级别
    log_level = config.get("level", "INFO").upper()

    # 3. 定义 patcher 以确保 extra["name"] 始终可用
    # 这样我们在 format 中可以使用 {extra[name]} 来统一显示模块名或自定义名称
    def patcher(record):
        if "name" not in record["extra"]:
            record["extra"]["name"] = record["name"]

    logger.configure(patcher=patcher)

    # 4. 配置控制台输出 (Console)
    if config.get("console_output", True):
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{extra[name]}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>",
            enqueue=True  # 异步安全
        )

    # 5. 配置文件输出 (File)
    file_path = config.get("file_path")
    if file_path:
        max_size_mb = config.get("max_size_mb", 10)
        backup_count = config.get("backup_count", 5)

        logger.add(
            file_path,
            level=log_level,
            rotation=f"{max_size_mb} MB",  # 自动轮转
            retention=backup_count,  # 保留文件数
            compression="zip",  # 自动压缩旧日志
            serialize=True,  # 输出为 JSON 格式 (结构化日志)
            enqueue=True,  # 异步安全
            backtrace=True,  # 详细的错误回溯
            diagnose=True  # 详细的变量诊断
        )

    # 6. 拦截标准库 logging (如 SQLAlchemy, Uvicorn 等)
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # 可以选择性地设置某些嘈杂库的日志级别
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str):
    """获取绑定特定名称的 Loguru 记录器

    使用 `logger.bind(name=name)` 绑定名称，以便在格式中通过 `{extra[name]}` 展示统一模块名或自定义名称。

    Args:
        name (str): 记录器名称，通常为模块名或业务子系统名。

    Returns:
        loguru.Logger: 绑定了 `extra.name` 的记录器实例。

    Raises:
        Exception: 当绑定过程失败时可能抛出异常。
    """
    return logger.bind(name=name)
