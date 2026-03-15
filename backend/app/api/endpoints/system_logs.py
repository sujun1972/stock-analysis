"""
系统日志API端点

提供系统日志文件的读取、查询和统计功能。
日志文件格式为Loguru生成的JSON格式，存储在backend/logs目录。

功能：
- 查询系统日志文件列表
- 读取和过滤日志内容（支持分页、级别、模块、关键词过滤）
- 日志统计分析

权限：
- 仅管理员可访问

技术要点：
- 使用分页避免大文件读取OOM
- 支持3种日志类型：app（应用）、errors（错误）、performance（性能）
"""
import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from loguru import logger

from app.schemas.system_logs import (
    SystemLogRecord,
    LogFileInfo,
    LogType,
    LogLevel,
    LogStatistics
)
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter(prefix="/system-logs", tags=["System Logs"])


def get_log_directory() -> Path:
    """获取日志目录路径"""
    # 从当前文件向上找到项目根目录，然后定位logs目录
    # 文件路径: /app/app/api/endpoints/system_logs.py
    # 项目根目录: /app
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent  # 向上4级
    log_dir = project_root / "logs"

    if not log_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"日志目录不存在: {log_dir}"
        )
    return log_dir


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def parse_log_record(line: str) -> Optional[SystemLogRecord]:
    """
    解析单条JSON日志记录

    Args:
        line: JSON格式的日志行

    Returns:
        SystemLogRecord或None(如果解析失败)
    """
    try:
        data = json.loads(line.strip())
        record = data.get("record", {})

        # 提取时间戳
        time_info = record.get("time", {})
        timestamp_value = time_info.get("timestamp")
        if timestamp_value:
            timestamp = datetime.fromtimestamp(timestamp_value)
        else:
            timestamp = datetime.now()

        # 提取文件路径
        file_info = record.get("file", {})
        file_path = file_info.get("path", "")

        # 提取级别信息
        level_info = record.get("level", {})
        level = level_info.get("name", "INFO")

        return SystemLogRecord(
            text=data.get("text", ""),
            timestamp=timestamp,
            level=level,
            module=record.get("module"),
            function=record.get("function"),
            line=record.get("line"),
            message=record.get("message", ""),
            file_path=file_path,
            extra=record.get("extra", {})
        )
    except Exception as e:
        logger.warning(f"解析日志记录失败: {e}, line: {line[:100]}")
        return None


@router.get("/files", response_model=dict, summary="获取日志文件列表")
async def get_log_files(
    log_type: Optional[LogType] = Query(None, description="日志类型过滤"),
    current_user: User = Depends(require_admin)
):
    """
    获取所有可用的日志文件列表

    - 仅管理员可访问
    - 返回文件名、类型、日期、大小等信息
    - 可按日志类型过滤
    """
    try:
        log_dir = get_log_directory()
        files_info: List[LogFileInfo] = []

        # 遍历日志文件
        for file_path in log_dir.glob("*.json"):
            filename = file_path.name

            # 解析文件名: app_2026-02-09.json
            parts = filename.replace(".json", "").split("_")
            if len(parts) < 2:
                continue

            file_type = parts[0]
            file_date = parts[1]

            # 类型过滤
            if log_type and file_type != log_type.value:
                continue

            # 获取文件大小
            size = file_path.stat().st_size

            files_info.append(LogFileInfo(
                filename=filename,
                type=file_type,
                date=file_date,
                size=size,
                size_human=format_size(size),
                path=str(file_path.relative_to(settings.BASE_DIR))
            ))

        # 按日期降序排序
        files_info.sort(key=lambda x: x.date, reverse=True)

        logger.bind(count=len(files_info)).info("查询日志文件列表成功")

        return {
            "success": True,
            "data": {
                "files": [f.model_dump() for f in files_info]
            }
        }
    except Exception as e:
        logger.error(f"获取日志文件列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/query", response_model=dict, summary="查询系统日志")
async def query_system_logs(
    log_type: LogType = Query(LogType.APP, description="日志类型"),
    log_date: Optional[date] = Query(None, description="日志日期 (格式: YYYY-MM-DD)"),
    level: Optional[LogLevel] = Query(None, description="日志级别过滤"),
    module: Optional[str] = Query(None, description="模块名称过滤"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页大小"),
    current_user: User = Depends(require_admin)
):
    """
    查询系统日志内容

    - 仅管理员可访问
    - 支持按类型、日期、级别、模块过滤
    - 支持关键词搜索
    - 自动分页

    参数说明：
    - log_type: app(应用日志), errors(错误日志), performance(性能日志)
    - log_date: 不指定则读取最新的日志文件
    - level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - module: 模块名称，如 "api", "core", "services"
    - search: 在日志消息中搜索关键词
    """
    try:
        log_dir = get_log_directory()

        # 确定要读取的日志文件
        if log_date:
            filename = f"{log_type.value}_{log_date.strftime('%Y-%m-%d')}.json"
        else:
            # 获取最新的日志文件
            files = sorted(
                log_dir.glob(f"{log_type.value}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not files:
                return {
                    "success": True,
                    "data": {
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "logs": []
                    }
                }
            filename = files[0].name

        log_file = log_dir / filename
        if not log_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"日志文件不存在: {filename}"
            )

        logger.bind(file=filename, page=page).info("开始读取日志文件")

        # 读取并解析日志
        all_logs: List[SystemLogRecord] = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                record = parse_log_record(line)
                if not record:
                    continue

                # 应用过滤条件
                if level and record.level != level.value:
                    continue

                if module and record.module != module:
                    continue

                if search and search.lower() not in record.message.lower():
                    continue

                all_logs.append(record)

        # 分页
        total = len(all_logs)
        start = (page - 1) * page_size
        end = start + page_size
        page_logs = all_logs[start:end]

        logger.bind(
            total=total,
            page=page,
            returned=len(page_logs)
        ).info("查询系统日志成功")

        return {
            "success": True,
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "logs": [log.model_dump() for log in page_logs]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询系统日志失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询日志失败: {str(e)}"
        )


@router.get("/statistics", response_model=dict, summary="获取日志统计信息")
async def get_log_statistics(
    log_type: LogType = Query(LogType.APP, description="日志类型"),
    log_date: Optional[date] = Query(None, description="日志日期"),
    current_user: User = Depends(require_admin)
):
    """
    获取日志统计信息

    - 仅管理员可访问
    - 统计日志总数、各级别分布、模块分布等
    """
    try:
        log_dir = get_log_directory()

        # 确定要读取的日志文件
        if log_date:
            filename = f"{log_type.value}_{log_date.strftime('%Y-%m-%d')}.json"
        else:
            files = sorted(
                log_dir.glob(f"{log_type.value}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not files:
                return {
                    "success": True,
                    "data": {
                        "total_logs": 0,
                        "by_level": {},
                        "by_module": {},
                        "error_count": 0,
                        "warning_count": 0
                    }
                }
            filename = files[0].name

        log_file = log_dir / filename
        if not log_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"日志文件不存在: {filename}"
            )

        # 统计数据
        total_logs = 0
        by_level: dict = {}
        by_module: dict = {}
        error_count = 0
        warning_count = 0

        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue

                record = parse_log_record(line)
                if not record:
                    continue

                total_logs += 1

                # 按级别统计
                by_level[record.level] = by_level.get(record.level, 0) + 1

                # 按模块统计
                if record.module:
                    by_module[record.module] = by_module.get(record.module, 0) + 1

                # 错误和警告计数
                if record.level == "ERROR" or record.level == "CRITICAL":
                    error_count += 1
                elif record.level == "WARNING":
                    warning_count += 1

        logger.bind(total=total_logs).info("生成日志统计信息成功")

        return {
            "success": True,
            "data": {
                "total_logs": total_logs,
                "by_level": by_level,
                "by_module": dict(sorted(by_module.items(), key=lambda x: x[1], reverse=True)[:10]),  # Top 10模块
                "error_count": error_count,
                "warning_count": warning_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取日志统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"统计失败: {str(e)}"
        )
