"""
股票列表相关API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from loguru import logger

from app.services import DatabaseService, DataDownloadService

router = APIRouter()


@router.get("/list")
async def get_stock_list(
    market: Optional[str] = Query(None, description="市场类型"),
    status: str = Query("正常", description="股票状态"),
    search: Optional[str] = Query(None, description="搜索关键词（股票代码或名称）"),
    sort_by: str = Query("pct_change", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向(asc/desc)"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回记录数")
):
    """
    获取股票列表

    参数:
    - market: 市场类型（上海主板、深圳主板、创业板、科创板等）
    - status: 股票状态（正常、退市等）
    - search: 搜索关键词（支持股票代码或名称模糊搜索）
    - sort_by: 排序字段（code, name, latest_price, pct_change等）
    - sort_order: 排序方向（asc升序/desc降序）
    - skip: 分页-跳过记录数
    - limit: 分页-每页记录数

    返回:
    - 股票列表
    """
    try:
        db_service = DatabaseService()
        result = db_service.get_stock_list(
            market=market,
            status=status,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{code}")
async def get_stock_info(code: str):
    """
    获取单只股票信息

    参数:
    - code: 股票代码

    返回:
    - 股票详细信息
    """
    try:
        db_service = DatabaseService()
        stock_info = db_service.get_stock_info(code)

        if stock_info is None:
            raise HTTPException(status_code=404, detail=f"股票 {code} 不存在")

        return stock_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票信息失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update")
async def update_stock_list():
    """
    更新股票列表（从数据源获取最新列表）

    返回:
    - 更新结果
    """
    try:
        data_service = DataDownloadService()
        result = await data_service.download_stock_list()
        return result
    except Exception as e:
        logger.error(f"更新股票列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
