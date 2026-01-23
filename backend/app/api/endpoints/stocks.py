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


@router.get("/{code}/minute")
async def get_minute_data(
    code: str,
    date: Optional[str] = Query(None, description="交易日期 (YYYY-MM-DD)，默认今天"),
    force_refresh: bool = Query(False, description="强制刷新数据")
):
    """
    获取股票1分钟K线数据（按需加载 + 智能缓存）

    优化策略：
    - 只从数据源获取和存储1分钟数据（最细粒度）
    - 前端根据需要聚合为5/15/30/60分钟数据
    - 减少存储空间（不存储冗余的多周期数据）
    - 减少API调用（每天每只股票只调用1次）

    工作流程：
    1. 检查数据库是否有完整的1分钟缓存数据
    2. 如果有且完整 -> 直接返回（from_cache=true）
    3. 如果没有或不完整 -> 从数据源获取1分钟数据 -> 保存 -> 返回（from_cache=false）

    参数：
    - code: 股票代码
    - date: 交易日期（默认今天）
    - force_refresh: 是否强制刷新（忽略缓存）

    返回：
    {
        "code": 200,
        "message": "success",
        "data": {
            "code": "000001",
            "date": "2026-01-21",
            "records": [...],  // 1分钟K线数据（240条左右）
            "from_cache": true,
            "completeness": 98.5,
            "record_count": 240
        }
    }
    """
    try:
        from datetime import datetime
        import asyncio
        from app.services.config_service import ConfigService
        from src.providers import DataProviderFactory

        # 默认日期为今天
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        db_service = DatabaseService()

        # 1. 检查是否为交易日
        if not db_service.is_trading_day(date):
            return {
                "code": 200,
                "message": "非交易日",
                "data": {
                    "code": code,
                    "date": date,
                    "records": [],
                    "from_cache": False,
                    "is_trading_day": False
                }
            }

        # 固定使用1分钟周期
        period = '1'

        # 2. 检查数据完整性
        if not force_refresh:
            completeness_info = db_service.check_minute_data_complete(code, period, date)

            # 如果数据完整（≥95%），直接从缓存返回
            if completeness_info['is_complete']:
                df = db_service.load_minute_data(code, period, date)

                if not df.empty:
                    logger.info(f"✓ 从缓存返回 {code} 1分钟数据 (完整度: {completeness_info['completeness']}%)")

                    return {
                        "code": 200,
                        "message": "success",
                        "data": {
                            "code": code,
                            "date": date,
                            "records": df.to_dict('records'),
                            "from_cache": True,
                            "completeness": completeness_info['completeness'],
                            "record_count": len(df)
                        }
                    }

        # 3. 数据不完整或强制刷新，从数据源获取1分钟数据
        logger.info(f"从数据源获取 {code} 1分钟数据: {date}")

        config_service = ConfigService()
        config = await config_service.get_data_source_config()

        # 创建数据提供者（使用分时数据源配置）
        provider = DataProviderFactory.create_provider(
            source=config['minute_data_source'],
            token=config.get('tushare_token', '')
        )

        # 获取1分钟数据
        df = await asyncio.to_thread(
            provider.get_minute_data,
            code=code,
            period='1',  # 固定获取1分钟数据
            start_date=date,
            end_date=date
        )

        if df.empty:
            raise HTTPException(status_code=404, detail=f"{code} {date} 无分时数据")

        # 4. 保存到数据库
        count = await asyncio.to_thread(
            db_service.save_minute_data,
            df,
            code,
            period,
            date
        )

        logger.info(f"✓ 保存并返回 {code} 1分钟数据: {count} 条记录")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "code": code,
                "date": date,
                "records": df.to_dict('records'),
                "from_cache": False,
                "record_count": len(df),
                "cache_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分时数据失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{code}/minute/range")
async def get_minute_data_range(
    code: str,
    period: str = Query('5', description="分时周期 (1/5/15/30/60)"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    limit: int = Query(1000, description="最大记录数")
):
    """
    获取股票分时数据（日期范围）

    用于多日分时数据查询，自动处理缓存逻辑

    参数：
    - code: 股票代码
    - period: 分时周期
    - start_date: 开始日期（默认最近5个交易日）
    - end_date: 结束日期（默认今天）
    - limit: 最大记录数
    """
    try:
        from datetime import datetime, timedelta
        import pandas as pd

        # 默认查询最近5个交易日
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if not start_date:
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

        db_service = DatabaseService()
        conn = db_service.get_connection()

        # 查询范围内的分时数据
        query = """
            SELECT trade_time, open, high, low, close, volume, amount,
                   pct_change, change_amount
            FROM stock_minute
            WHERE code = %s
                AND period = %s
                AND trade_time >= %s
                AND trade_time <= %s
            ORDER BY trade_time ASC
            LIMIT %s
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(code, period, f"{start_date} 09:30:00", f"{end_date} 15:00:00", limit)
        )

        db_service.release_connection(conn)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "code": code,
                "period": period,
                "start_date": start_date,
                "end_date": end_date,
                "records": df.to_dict('records'),
                "record_count": len(df)
            }
        }

    except Exception as e:
        logger.error(f"获取分时数据范围失败 {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
