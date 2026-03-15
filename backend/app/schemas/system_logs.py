"""
系统日志相关的Pydantic模型

用于读取和展示backend/logs目录下的JSON格式日志文件
"""
from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field
from enum import Enum


class LogLevel(str, Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogType(str, Enum):
    """日志文件类型枚举"""
    APP = "app"  # 应用日志
    ERROR = "errors"  # 错误日志
    PERFORMANCE = "performance"  # 性能日志


class SystemLogRecord(BaseModel):
    """单条系统日志记录"""
    text: str = Field(..., description="日志文本内容")
    timestamp: datetime = Field(..., description="日志时间戳")
    level: str = Field(..., description="日志级别")
    module: Optional[str] = Field(None, description="模块名称")
    function: Optional[str] = Field(None, description="函数名称")
    line: Optional[int] = Field(None, description="行号")
    message: str = Field(..., description="日志消息")
    file_path: Optional[str] = Field(None, description="源文件路径")
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外信息")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "2026-02-09 08:40:01.332 | INFO | app.core.logging_config:setup_logging:115 - 日志系统已初始化",
                "timestamp": "2026-02-09T08:40:01.332469",
                "level": "INFO",
                "module": "logging_config",
                "function": "setup_logging",
                "line": 115,
                "message": "日志系统已初始化 - 环境: development, 级别: INFO",
                "file_path": "/app/core/logging_config.py",
                "extra": {}
            }
        }


class SystemLogResponse(BaseModel):
    """系统日志查询响应"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    logs: List[SystemLogRecord] = Field(..., description="日志记录列表")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "page": 1,
                "page_size": 20,
                "logs": []
            }
        }


class LogFileInfo(BaseModel):
    """日志文件信息"""
    filename: str = Field(..., description="文件名")
    type: LogType = Field(..., description="日志类型")
    date: str = Field(..., description="日志日期")
    size: int = Field(..., description="文件大小(字节)")
    size_human: str = Field(..., description="文件大小(可读格式)")
    path: str = Field(..., description="文件路径")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "app_2026-02-09.json",
                "type": "app",
                "date": "2026-02-09",
                "size": 17825792,
                "size_human": "17.0 MB",
                "path": "/logs/app_2026-02-09.json"
            }
        }


class LogFilesResponse(BaseModel):
    """日志文件列表响应"""
    files: List[LogFileInfo] = Field(..., description="日志文件列表")

    class Config:
        json_schema_extra = {
            "example": {
                "files": []
            }
        }


class LogStatistics(BaseModel):
    """日志统计信息"""
    total_logs: int = Field(..., description="总日志条数")
    by_level: Dict[str, int] = Field(..., description="按级别统计")
    by_module: Dict[str, int] = Field(..., description="按模块统计")
    error_count: int = Field(..., description="错误数量")
    warning_count: int = Field(..., description="警告数量")

    class Config:
        json_schema_extra = {
            "example": {
                "total_logs": 1000,
                "by_level": {
                    "INFO": 800,
                    "WARNING": 150,
                    "ERROR": 50
                },
                "by_module": {
                    "api": 500,
                    "core": 300,
                    "services": 200
                },
                "error_count": 50,
                "warning_count": 150
            }
        }
