"""
数据同步 API（重构版）
使用专门的服务类处理同步逻辑
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.error_handler import handle_api_errors
from app.services.config_service import ConfigService
from app.services.daily_sync_service import DailySyncService
from app.services.realtime_sync_service import RealtimeSyncService
from app.services.stock_list_sync_service import StockListSyncService

router = APIRouter()


# ==================== Request Models ====================


class SyncDailyBatchRequest(BaseModel):
    """批量同步日线数据请求"""

    codes: Optional[List[str]] = None
    start_date: Optional[str] = None  # 开始日期，格式: YYYYMMDD 或 YYYY-MM-DD
    end_date: Optional[str] = None  # 结束日期，格式: YYYYMMDD 或 YYYY-MM-DD
    years: Optional[int] = None  # 兼容旧参数：历史年数


class SyncMinuteRequest(BaseModel):
    """同步分时数据请求"""

    period: Optional[str] = "5"
    days: Optional[int] = 5


class SyncRealtimeRequest(BaseModel):
    """同步实时行情请求"""

    codes: Optional[List[str]] = None
    batch_size: Optional[int] = 100
    update_oldest: Optional[bool] = False


class SyncNewStocksRequest(BaseModel):
    """同步新股列表请求"""

    days: Optional[int] = 30


# ==================== Status Endpoints ====================


@router.get("/status")
@handle_api_errors
async def get_sync_status():
    """
    获取同步状态（全局）

    Returns:
        当前同步状态信息
    """
    config_service = ConfigService()
    status = await config_service.get_sync_status()

    return {"code": 200, "message": "success", "data": status}


@router.get("/status/{module}")
@handle_api_errors
async def get_module_sync_status(module: str):
    """
    获取特定模块的同步状态

    Args:
        module: 模块名称 (stock_list, new_stocks, delisted_stocks, daily, minute, realtime)

    Returns:
        模块同步状态信息
    """
    # 验证模块名称
    valid_modules = ["stock_list", "new_stocks", "delisted_stocks", "daily", "minute", "realtime"]
    if module not in valid_modules:
        raise HTTPException(
            status_code=400, detail=f"无效的模块名称，支持: {', '.join(valid_modules)}"
        )

    config_service = ConfigService()
    status = await config_service.get_module_sync_status(module)

    return {"code": 200, "message": "success", "data": status}


@router.post("/abort")
@handle_api_errors
async def abort_sync():
    """
    中止当前正在运行的同步任务

    Returns:
        中止请求结果
    """
    config_service = ConfigService()

    # 检查当前是否有正在运行的同步
    status = await config_service.get_sync_status()
    if status.get("status") != "running":
        return {"code": 400, "message": "没有正在运行的同步任务", "data": None}

    # 设置中止标志
    await config_service.set_sync_abort_flag(True)

    return {"code": 200, "message": "中止请求已发送，同步将在当前股票完成后停止", "data": None}


# ==================== Stock List Sync Endpoints ====================


@router.post("/stock-list")
@handle_api_errors
async def sync_stock_list():
    """
    同步股票列表

    Returns:
        同步结果，包含获取的股票总数
    """
    service = StockListSyncService()
    result = await service.sync_stock_list()

    return {"code": 200, "message": "success", "data": result}


@router.post("/new-stocks")
@handle_api_errors
async def sync_new_stocks(request: SyncNewStocksRequest):
    """
    同步新股列表

    Args:
        request: 新股同步请求
            - days: 最近天数 (默认 30 天)

    Returns:
        同步结果，包含获取的新股总数
    """
    service = StockListSyncService()
    result = await service.sync_new_stocks(days=request.days)

    return {"code": 200, "message": "success", "data": result}


@router.post("/delisted-stocks")
@handle_api_errors
async def sync_delisted_stocks():
    """
    同步退市股票列表

    Returns:
        同步结果，包含退市股票总数
    """
    service = StockListSyncService()
    result = await service.sync_delisted_stocks()

    return {"code": 200, "message": "success", "data": result}


# ==================== Daily Data Sync Endpoints ====================


@router.post("/daily/batch")
@handle_api_errors
async def sync_daily_batch(request: SyncDailyBatchRequest):
    """
    批量同步日线数据

    Args:
        request: 批量同步请求
            - codes: 股票代码列表 (None 表示全部)
            - start_date: 开始日期 (优先使用)
            - end_date: 结束日期 (默认今天)
            - years: 历史年数 (仅在未提供start_date时使用)

    Returns:
        同步结果统计
    """
    service = DailySyncService()
    result = await service.sync_batch(
        codes=request.codes,
        start_date=request.start_date,
        end_date=request.end_date,
        years=request.years,
    )

    if result["aborted"]:
        return {"code": 200, "message": "同步已中止", "data": result}
    else:
        return {"code": 200, "message": "success", "data": result}


@router.post("/daily/{code}")
@handle_api_errors
async def sync_daily_stock(code: str, years: int = 5):
    """
    同步单只股票日线数据

    Args:
        code: 股票代码
        years: 历史年数

    Returns:
        同步结果
    """
    service = DailySyncService()
    result = await service.sync_single_stock(code=code, years=years)

    return {"code": 200, "message": "success", "data": result}


# ==================== Realtime Sync Endpoints ====================


@router.post("/minute/{code}")
@handle_api_errors
async def sync_minute_data(code: str, request: SyncMinuteRequest):
    """
    同步分时数据

    Args:
        code: 股票代码
        request: 分时同步请求
            - period: 分时周期 ('1', '5', '15', '30', '60')
            - days: 同步天数

    Returns:
        同步结果
    """
    service = RealtimeSyncService()
    result = await service.sync_minute_data(code=code, period=request.period, days=request.days)

    return {"code": 200, "message": "success", "data": result}


@router.post("/realtime")
@handle_api_errors
async def sync_realtime_quotes(request: SyncRealtimeRequest):
    """
    更新实时行情

    Args:
        request: 实时行情请求
            - codes: 股票代码列表 (None 表示全部)
            - batch_size: 每批次更新的股票数量
            - update_oldest: 是否优先更新最旧的数据

    Returns:
        更新结果
    """
    service = RealtimeSyncService()
    result = await service.sync_realtime_quotes(
        codes=request.codes, batch_size=request.batch_size, update_oldest=request.update_oldest
    )

    # 检查是否为部分成功（超时但有部分数据保存）
    if result.get("partial_success"):
        return {"code": 206, "message": "partial_success", "data": result}  # 206 Partial Content
    else:
        return {"code": 200, "message": "success", "data": result}


# ==================== History Endpoint ====================


@router.get("/history")
@handle_api_errors
async def get_sync_history(limit: int = 20, offset: int = 0):
    """
    获取同步历史记录

    Args:
        limit: 返回记录数
        offset: 跳过记录数

    Returns:
        同步历史记录列表
    """
    # TODO: 从 sync_log 表查询历史记录
    history = []

    return {"code": 200, "message": "success", "data": history}
