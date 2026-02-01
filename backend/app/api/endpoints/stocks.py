"""
股票列表相关API (重构版本)

✅ 任务 0.3: 重写 Stocks API
- 使用 Core Adapters 代替 DatabaseService
- Backend 只负责：参数验证、分页、响应格式化
- 业务逻辑全部由 Core 处理

作者: Backend Team
创建日期: 2026-02-01
版本: 2.0.0 (架构修正版)
"""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime
from loguru import logger

from app.core_adapters.data_adapter import DataAdapter
from app.models.api_response import ApiResponse

router = APIRouter()

# 全局 Data Adapter 实例
data_adapter = DataAdapter()


@router.get("/list")
async def get_stock_list(
    market: Optional[str] = Query(None, description="市场类型"),
    status_filter: str = Query("正常", description="股票状态", alias="status"),
    search: Optional[str] = Query(None, description="搜索关键词（股票代码或名称）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页记录数")
):
    """
    获取股票列表

    ✅ 架构修正版：
    - Backend 只负责：参数验证（Pydantic 自动）、调用 Core Adapter、分页、响应格式化
    - Core 负责：数据库查询、业务逻辑

    参数:
    - market: 市场类型（主板/创业板/科创板/北交所）
    - status: 股票状态（正常、退市等）
    - search: 搜索关键词（支持股票代码或名称模糊搜索）
    - page: 当前页码（从 1 开始）
    - page_size: 每页记录数（1-100）

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "items": [...],
            "total": 5000,
            "page": 1,
            "page_size": 20,
            "total_pages": 250
        }
    }
    """
    try:
        # 1. 调用 Core Adapter（业务逻辑在 Core）
        stocks = await data_adapter.get_stock_list(
            market=market,
            status=status_filter
        )

        # 2. Backend 职责：搜索过滤（前端功能）
        if search:
            search_lower = search.lower()
            stocks = [
                stock for stock in stocks
                if search_lower in stock.get('code', '').lower()
                or search_lower in stock.get('name', '').lower()
            ]

        # 3. Backend 职责：分页
        total = len(stocks)
        start = (page - 1) * page_size
        end = start + page_size
        items = stocks[start:end]

        # 4. Backend 职责：响应格式化
        return ApiResponse.paginated(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            message="获取股票列表成功"
        ).to_dict()

    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        return ApiResponse.internal_error(
            message=f"获取股票列表失败: {str(e)}"
        ).to_dict()


@router.get("/{code}")
async def get_stock_info(code: str):
    """
    获取单只股票信息

    ✅ 架构修正版：调用 Core Adapter 的 get_stock_info 方法

    参数:
    - code: 股票代码

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "code": "000001",
            "name": "平安银行",
            "market": "主板",
            "industry": "银行",
            ...
        }
    }
    """
    try:
        # 调用 Core Adapter
        stock_info = await data_adapter.get_stock_info(code)

        if stock_info is None:
            return ApiResponse.not_found(
                message=f"股票 {code} 不存在"
            ).to_dict()

        return ApiResponse.success(
            data=stock_info,
            message="获取股票信息成功"
        ).to_dict()

    except Exception as e:
        logger.error(f"获取股票信息失败 {code}: {e}")
        return ApiResponse.internal_error(
            message=f"获取股票信息失败: {str(e)}"
        ).to_dict()


@router.get("/{code}/daily")
async def get_stock_daily_data(
    code: str,
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="最大记录数")
):
    """
    获取股票日线数据

    ✅ 架构修正版：调用 Core Adapter 的 get_daily_data 方法

    参数:
    - code: 股票代码
    - start_date: 开始日期（默认最近 100 天）
    - end_date: 结束日期（默认今天）
    - limit: 最大记录数

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "code": "000001",
            "records": [...],
            "record_count": 100
        }
    }
    """
    try:
        # 1. 参数转换
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

        # 2. 调用 Core Adapter
        df = await data_adapter.get_daily_data(
            code=code,
            start_date=start_dt,
            end_date=end_dt
        )

        if df.empty:
            return ApiResponse.not_found(
                message=f"股票 {code} 无日线数据"
            ).to_dict()

        # 3. 限制返回记录数
        if len(df) > limit:
            df = df.tail(limit)

        # 4. 转换为响应格式
        records = df.to_dict('records')

        return ApiResponse.success(
            data={
                "code": code,
                "records": records,
                "record_count": len(records)
            },
            message="获取日线数据成功"
        ).to_dict()

    except ValueError as e:
        return ApiResponse.bad_request(
            message=f"日期格式错误: {str(e)}"
        ).to_dict()
    except Exception as e:
        logger.error(f"获取日线数据失败 {code}: {e}")
        return ApiResponse.internal_error(
            message=f"获取日线数据失败: {str(e)}"
        ).to_dict()


@router.post("/update")
async def update_stock_list():
    """
    更新股票列表（从数据源获取最新列表）

    ⚠️ 注意：此功能暂不支持，需要配合 Core 的数据下载功能
    未来版本将集成 Core 的 DataDownloadManager

    返回:
    {
        "code": 501,
        "message": "此功能暂未实现，请使用 Core 的数据下载功能"
    }
    """
    return ApiResponse.error(
        message="此功能暂未实现，请使用 Core 的数据下载功能",
        code=501
    ).to_dict()


@router.get("/{code}/minute")
async def get_minute_data(
    code: str,
    trade_date: Optional[str] = Query(None, description="交易日期 (YYYY-MM-DD)，默认今天"),
    period: str = Query("1min", description="分钟周期 (1min/5min/15min/30min/60min)")
):
    """
    获取股票分时数据

    ✅ 架构修正版：调用 Core Adapter 的 get_minute_data 方法

    参数:
    - code: 股票代码
    - trade_date: 交易日期（默认今天）
    - period: 分钟周期

    返回:
    {
        "code": 200,
        "message": "success",
        "data": {
            "code": "000001",
            "date": "2026-02-01",
            "period": "1min",
            "records": [...],
            "record_count": 240
        }
    }
    """
    try:
        # 1. 默认日期为今天
        if not trade_date:
            trade_date_dt = datetime.now().date()
        else:
            trade_date_dt = datetime.strptime(trade_date, "%Y-%m-%d").date()

        # 2. 检查是否为交易日
        is_trading = await data_adapter.is_trading_day(trade_date_dt)
        if not is_trading:
            return ApiResponse.success(
                data={
                    "code": code,
                    "date": trade_date_dt.strftime("%Y-%m-%d"),
                    "records": [],
                    "is_trading_day": False
                },
                message="非交易日"
            ).to_dict()

        # 3. 调用 Core Adapter 获取分时数据
        df = await data_adapter.get_minute_data(
            code=code,
            period=period,
            trade_date=trade_date_dt
        )

        if df.empty:
            return ApiResponse.not_found(
                message=f"{code} {trade_date_dt} 无分时数据"
            ).to_dict()

        # 4. 转换为响应格式
        records = df.to_dict('records')

        return ApiResponse.success(
            data={
                "code": code,
                "date": trade_date_dt.strftime("%Y-%m-%d"),
                "period": period,
                "records": records,
                "record_count": len(records)
            },
            message="获取分时数据成功"
        ).to_dict()

    except ValueError as e:
        return ApiResponse.bad_request(
            message=f"日期格式错误: {str(e)}"
        ).to_dict()
    except Exception as e:
        logger.error(f"获取分时数据失败 {code}: {e}")
        return ApiResponse.internal_error(
            message=f"获取分时数据失败: {str(e)}"
        ).to_dict()
