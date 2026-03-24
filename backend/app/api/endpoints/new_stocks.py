"""
新股列表 API
提供新股查询、统计和同步功能
"""

from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from app.api.error_handler import handle_api_errors
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
from app.repositories.stock_basic_repository import StockBasicRepository

router = APIRouter()


@router.get("")
@handle_api_errors
async def get_new_stocks(
    days: Optional[int] = Query(None, description="最近N天上市的股票"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    market: Optional[str] = Query(None, description="市场类型筛选"),
    limit: int = Query(30, ge=1, le=1000, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(require_admin)
):
    """
    查询新股列表

    Args:
        days: 最近N天上市的股票（优先使用）
        start_date: 开始日期
        end_date: 结束日期
        market: 市场类型（如：上海主板、科创板、创业板等）
        limit: 返回记录数
        offset: 偏移量

    Returns:
        新股列表数据
    """
    repo = StockBasicRepository()

    # 计算日期范围
    if days:
        # 使用days参数
        end_date_obj = datetime.now().date()
        start_date_obj = end_date_obj - timedelta(days=days)
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')
    elif start_date and end_date:
        # 使用日期范围
        start_date_str = start_date
        end_date_str = end_date
    elif start_date:
        # 只有开始日期，结束日期为今天
        start_date_str = start_date
        end_date_str = datetime.now().date().strftime('%Y-%m-%d')
    else:
        # 默认最近30天
        end_date_obj = datetime.now().date()
        start_date_obj = end_date_obj - timedelta(days=30)
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')

    # 查询新股列表
    items = repo.get_new_stocks(
        start_date=start_date_str,
        end_date=end_date_str,
        market=market,
        limit=limit,
        offset=offset
    )

    # 获取总数
    total = repo.count_new_stocks(
        start_date=start_date_str,
        end_date=end_date_str,
        market=market
    )

    return ApiResponse.success(data={
        "items": items,
        "total": total
    })


@router.get("/statistics")
@handle_api_errors
async def get_new_stocks_statistics(
    days: Optional[int] = Query(None, description="最近N天上市的股票"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    获取新股统计信息

    Returns:
        统计信息（总数、市场分布、行业分布等）
    """
    repo = StockBasicRepository()

    # 计算日期范围
    if days:
        end_date_obj = datetime.now().date()
        start_date_obj = end_date_obj - timedelta(days=days)
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')
    elif start_date and end_date:
        start_date_str = start_date
        end_date_str = end_date
    elif start_date:
        start_date_str = start_date
        end_date_str = datetime.now().date().strftime('%Y-%m-%d')
    else:
        # 默认最近90天用于统计
        end_date_obj = datetime.now().date()
        start_date_obj = end_date_obj - timedelta(days=90)
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')

    # 获取统计信息
    stats = repo.get_new_stocks_statistics(
        start_date=start_date_str,
        end_date=end_date_str
    )

    return ApiResponse.success(data=stats)
