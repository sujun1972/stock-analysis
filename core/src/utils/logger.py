"""
统一的日志系统

基于 loguru 提供结构化、可配置的日志功能
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional


# 移除默认的 logger
logger.remove()


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True,
    rotation: str = "100 MB",
    retention: str = "30 days",
    compression: str = "zip"
):
    """
    配置日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径（None 则使用默认路径）
        enable_console: 是否输出到控制台
        enable_file: 是否输出到文件
        rotation: 日志轮转大小
        retention: 日志保留时间
        compression: 压缩格式
    """

    # 控制台输出
    if enable_console:
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            colorize=True,
        )

    # 文件输出
    if enable_file:
        if log_file is None:
            log_file = "logs/stock_analysis_{time:YYYY-MM-DD}.log"

        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation=rotation,
            retention=retention,
            compression=compression,
            encoding="utf-8",
        )


# 默认配置
setup_logger()


def get_logger(name: str = __name__):
    """
    获取 logger 实例

    Args:
        name: logger 名称（通常使用 __name__）

    Returns:
        配置好的 logger 实例

    Example:
        from utils.logger import get_logger

        logger = get_logger(__name__)
        logger.info("Processing data...")
    """
    return logger.bind(name=name)


# 导出默认 logger
__all__ = ["logger", "get_logger", "setup_logger"]
