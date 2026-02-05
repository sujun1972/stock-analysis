"""
结构化日志配置模块
使用 Loguru 实现 JSON 格式日志、日志轮转和压缩
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from app.core.config import settings


def json_serializer(record: Dict[str, Any]) -> str:
    """
    自定义JSON序列化器
    将日志记录转换为JSON格式
    """
    # 提取核心字段
    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }

    # 添加上下文数据（使用 logger.bind() 添加的额外字段）
    if record["extra"]:
        log_entry["context"] = record["extra"]

    # 添加异常信息
    if record["exception"]:
        log_entry["exception"] = {
            "type": record["exception"].type.__name__,
            "value": str(record["exception"].value),
            "traceback": record["exception"].traceback,
        }

    return json.dumps(log_entry, ensure_ascii=False) + "\n"


def setup_logging():
    """
    配置结构化日志系统

    特性：
    - JSON格式输出（便于日志分析工具解析）
    - 日志轮转（每天00:00创建新文件）
    - 日志压缩（自动压缩旧日志为.gz格式）
    - 日志保留（保留30天）
    - 错误日志单独记录
    - 开发环境同时输出到控制台
    """
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 移除默认的控制台处理器
    logger.remove()

    # 1. 控制台输出（开发环境）- 彩色格式
    if settings.ENVIRONMENT == "development":
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>",
            level=settings.LOG_LEVEL,
            colorize=True,
        )

    # 2. 主日志文件 - JSON格式，包含所有日志
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.json",
        serialize=True,  # 使用 Loguru 内置的 JSON 序列化
        rotation="00:00",  # 每天午夜轮转
        retention="30 days",  # 保留30天
        compression="gz",  # 压缩旧日志
        level=settings.LOG_LEVEL,
        encoding="utf-8",
        enqueue=True,  # 异步写入，避免阻塞
    )

    # 3. 错误日志文件 - 仅记录 WARNING 及以上级别
    logger.add(
        log_dir / "errors_{time:YYYY-MM-DD}.json",
        serialize=True,
        rotation="00:00",
        retention="30 days",
        compression="gz",
        level="WARNING",
        encoding="utf-8",
        enqueue=True,
    )

    # 4. 性能日志文件 - 可选，记录性能相关日志
    logger.add(
        log_dir / "performance_{time:YYYY-MM-DD}.json",
        serialize=True,
        rotation="00:00",
        retention="7 days",  # 性能日志保留7天
        compression="gz",
        level="INFO",
        filter=lambda record: "performance" in record["extra"],
        encoding="utf-8",
        enqueue=True,
    )

    logger.info(
        f"日志系统已初始化 - 环境: {settings.ENVIRONMENT}, 级别: {settings.LOG_LEVEL}"
    )


def get_logger():
    """
    获取配置好的 logger 实例

    Returns:
        logger: Loguru logger 实例
    """
    return logger


# 使用示例：
# from app.core.logging_config import get_logger
# logger = get_logger()
#
# # 基础日志
# logger.info("Stock data fetched successfully")
#
# # 带上下文的结构化日志
# logger.bind(code="000001", rows=1000).info("Stock data fetched")
#
# # 性能日志（会单独记录到 performance_*.json）
# logger.bind(performance=True, duration_ms=150).info("API request completed")
#
# # 错误日志（会同时记录到 app_*.json 和 errors_*.json）
# logger.error("Database connection failed")
