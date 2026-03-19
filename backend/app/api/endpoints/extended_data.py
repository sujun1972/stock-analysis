"""
扩展数据API端点
提供Tushare扩展数据的查询和同步接口
"""

from fastapi import APIRouter, Query, Depends, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import date, datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.api_response import ApiResponse
from app.repositories import (
    DailyBasicRepository,
    HkHoldRepository,
    StkLimitRepository,
    BlockTradeRepository,
    MoneyflowRepository,
    MarginDetailRepository
)
from loguru import logger
from app.tasks.extended_sync_tasks import (
    sync_daily_basic_task,
    sync_moneyflow_task,
    sync_hk_hold_task,
    sync_margin_task,
    sync_stk_limit_task,
    sync_block_trade_task
)

router = APIRouter(tags=["extended_data"])


@router.get("/daily-basic/{ts_code}")
def get_daily_basic(
    ts_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, le=1000, description="返回记录数")
):
    """
    获取股票每日指标
    - 换手率、市盈率、市净率等
    - 用于短线选股和风险评估
    """
    try:
        # 使用 Repository 层
        repo = DailyBasicRepository()

        # 转换日期格式 (date -> YYYYMMDD)
        start_date_str = start_date.strftime("%Y%m%d") if start_date else None
        end_date_str = end_date.strftime("%Y%m%d") if end_date else None

        # 调用 Repository 查询
        items = repo.get_by_code_and_date_range(
            ts_code=ts_code,
            start_date=start_date_str,
            end_date=end_date_str,
            limit=limit
        )

        return ApiResponse.success(data={"items": items, "count": len(items)})

    except Exception as e:
        logger.error(f"获取每日指标失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/moneyflow/{ts_code}")
def get_moneyflow(
    ts_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, le=500, description="返回记录数"),
    db: Session = Depends(get_db)
):
    """
    获取个股资金流向
    - 大单、中单、小单资金流向
    - 判断主力资金动向
    """
    try:
        query_str = """
            SELECT
                ts_code, trade_date,
                buy_sm_vol, buy_sm_amount, sell_sm_vol, sell_sm_amount,
                buy_md_vol, buy_md_amount, sell_md_vol, sell_md_amount,
                buy_lg_vol, buy_lg_amount, sell_lg_vol, sell_lg_amount,
                buy_elg_vol, buy_elg_amount, sell_elg_vol, sell_elg_amount,
                net_mf_vol, net_mf_amount, trade_count
            FROM moneyflow
            WHERE ts_code = :ts_code
        """

        params = {"ts_code": ts_code}

        if start_date:
            query_str += " AND trade_date >= :start_date"
            params["start_date"] = start_date

        if end_date:
            query_str += " AND trade_date <= :end_date"
            params["end_date"] = end_date

        query_str += " ORDER BY trade_date DESC LIMIT :limit"
        params["limit"] = limit

        result = db.execute(text(query_str), params)
        rows = result.fetchall()

        data = []
        for row in rows:
            data.append({
                "ts_code": row.ts_code,
                "trade_date": row.trade_date.strftime("%Y-%m-%d") if row.trade_date else None,
                "buy_sm_vol": int(row.buy_sm_vol) if row.buy_sm_vol else None,
                "buy_sm_amount": float(row.buy_sm_amount) if row.buy_sm_amount else None,
                "sell_sm_vol": int(row.sell_sm_vol) if row.sell_sm_vol else None,
                "sell_sm_amount": float(row.sell_sm_amount) if row.sell_sm_amount else None,
                "buy_md_vol": int(row.buy_md_vol) if row.buy_md_vol else None,
                "buy_md_amount": float(row.buy_md_amount) if row.buy_md_amount else None,
                "sell_md_vol": int(row.sell_md_vol) if row.sell_md_vol else None,
                "sell_md_amount": float(row.sell_md_amount) if row.sell_md_amount else None,
                "buy_lg_vol": int(row.buy_lg_vol) if row.buy_lg_vol else None,
                "buy_lg_amount": float(row.buy_lg_amount) if row.buy_lg_amount else None,
                "sell_lg_vol": int(row.sell_lg_vol) if row.sell_lg_vol else None,
                "sell_lg_amount": float(row.sell_lg_amount) if row.sell_lg_amount else None,
                "buy_elg_vol": int(row.buy_elg_vol) if row.buy_elg_vol else None,
                "buy_elg_amount": float(row.buy_elg_amount) if row.buy_elg_amount else None,
                "sell_elg_vol": int(row.sell_elg_vol) if row.sell_elg_vol else None,
                "sell_elg_amount": float(row.sell_elg_amount) if row.sell_elg_amount else None,
                "net_mf_vol": int(row.net_mf_vol) if row.net_mf_vol else None,
                "net_mf_amount": float(row.net_mf_amount) if row.net_mf_amount else None,
                "trade_count": int(row.trade_count) if row.trade_count else None
            })

        return {
            "code": 0,
            "data": data,
            "count": len(data),
            "msg": "success"
        }

    except Exception as e:
        logger.error(f"获取资金流向失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hk-hold")
def get_hk_hold(
    trade_date: Optional[date] = Query(None, description="交易日期"),
    exchange: Optional[str] = Query(None, description="交易所：SH/SZ"),
    top: int = Query(50, le=200, description="返回前N条")
):
    """
    获取北向资金持股数据
    - 沪股通、深股通持股
    - 外资动向重要参考
    """
    try:
        # 使用 Repository 层
        repo = HkHoldRepository()

        # 转换日期格式 (date -> YYYYMMDD)
        trade_date_str = trade_date.strftime("%Y%m%d") if trade_date else None

        # 调用 Repository 查询
        items = repo.get_by_date(
            trade_date=trade_date_str,
            exchange=exchange,
            limit=top
        )

        return ApiResponse.success(data={"items": items, "count": len(items)})

    except Exception as e:
        logger.error(f"获取北向资金失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/margin/{ts_code}")
def get_margin_detail(
    ts_code: str,
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, le=500, description="返回记录数"),
    db: Session = Depends(get_db)
):
    """
    获取融资融券数据
    - 两融余额变化
    - 市场情绪指标
    """
    try:
        query_str = """
            SELECT
                ts_code, trade_date, rzye, rqye, rzmre, rqyl,
                rzche, rqchl, rqmcl, rzrqye
            FROM margin_detail
            WHERE ts_code = :ts_code
        """

        params = {"ts_code": ts_code}

        if start_date:
            query_str += " AND trade_date >= :start_date"
            params["start_date"] = start_date

        if end_date:
            query_str += " AND trade_date <= :end_date"
            params["end_date"] = end_date

        query_str += " ORDER BY trade_date DESC LIMIT :limit"
        params["limit"] = limit

        result = db.execute(text(query_str), params)
        rows = result.fetchall()

        data = []
        for row in rows:
            data.append({
                "ts_code": row.ts_code,
                "trade_date": row.trade_date.strftime("%Y-%m-%d") if row.trade_date else None,
                "rzye": float(row.rzye) if row.rzye else None,
                "rqye": float(row.rqye) if row.rqye else None,
                "rzmre": float(row.rzmre) if row.rzmre else None,
                "rqyl": int(row.rqyl) if row.rqyl else None,
                "rzche": float(row.rzche) if row.rzche else None,
                "rqchl": int(row.rqchl) if row.rqchl else None,
                "rqmcl": int(row.rqmcl) if row.rqmcl else None,
                "rzrqye": float(row.rzrqye) if row.rzrqye else None
            })

        return {
            "code": 0,
            "data": data,
            "count": len(data),
            "msg": "success"
        }

    except Exception as e:
        logger.error(f"获取融资融券数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/limit-prices")
def get_limit_prices(
    trade_date: date = Query(..., description="交易日期"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(100, le=5000, description="返回记录数")
):
    """
    获取涨跌停价格
    - 当日所有股票的涨跌停价格
    - 用于交易参考
    """
    try:
        # 使用 Repository 层
        repo = StkLimitRepository()

        # 转换日期格式 (date -> YYYYMMDD)
        trade_date_str = trade_date.strftime("%Y%m%d")

        # 调用 Repository 查询
        items = repo.get_by_date(
            trade_date=trade_date_str,
            ts_code=ts_code,
            limit=limit
        )

        return ApiResponse.success(data={"items": items, "count": len(items)})

    except Exception as e:
        logger.error(f"获取涨跌停价格失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/block-trade")
def get_block_trade(
    trade_date: Optional[date] = Query(None, description="交易日期"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(100, le=500, description="返回记录数")
):
    """
    获取大宗交易数据
    - 机构大额交易
    - 判断机构动向
    """
    try:
        # 使用 Repository 层
        repo = BlockTradeRepository()

        # 转换日期格式 (date -> YYYYMMDD)
        trade_date_str = trade_date.strftime("%Y%m%d") if trade_date else None

        # 调用 Repository 查询
        items = repo.get_by_date(
            trade_date=trade_date_str,
            ts_code=ts_code,
            limit=limit
        )

        return ApiResponse.success(data={"items": items, "count": len(items)})

    except Exception as e:
        logger.error(f"获取大宗交易数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/trigger")
def trigger_sync(
    data_type: str = Query(..., description="数据类型：daily_basic|moneyflow|hk_hold|margin|stk_limit|block_trade"),
    trade_date: Optional[str] = Query(None, description="交易日期 YYYYMMDD"),
    _: dict = Depends(get_current_user)
):
    """
    手动触发数据同步
    需要管理员权限
    """

    task_map = {
        "daily_basic": sync_daily_basic_task,
        "moneyflow": sync_moneyflow_task,
        "hk_hold": sync_hk_hold_task,
        "margin": sync_margin_task,
        "stk_limit": sync_stk_limit_task,
        "block_trade": sync_block_trade_task
    }

    if data_type not in task_map:
        raise HTTPException(status_code=400, detail="不支持的数据类型")

    task = task_map[data_type]
    result = task.delay(trade_date=trade_date)

    return {
        "code": 0,
        "data": {
            "task_id": result.id,
            "data_type": data_type,
            "trade_date": trade_date
        },
        "msg": "同步任务已提交"
    }


@router.get("/sync/status/{task_id}")
def get_sync_status(task_id: str):
    """
    获取同步任务状态
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    return {
        "code": 0,
        "data": {
            "task_id": task_id,
            "state": result.state,
            "result": result.result if result.state == "SUCCESS" else None,
            "info": result.info if result.state == "PENDING" else None
        },
        "msg": "success"
    }


@router.get("/stats/summary")
def get_data_summary():
    """
    获取扩展数据统计摘要
    """
    try:
        # 使用 Repository 层获取统计信息
        daily_basic_repo = DailyBasicRepository()
        moneyflow_repo = MoneyflowRepository()
        hk_hold_repo = HkHoldRepository()
        margin_detail_repo = MarginDetailRepository()

        stats = {
            'daily_basic': daily_basic_repo.get_statistics(),
            'moneyflow': moneyflow_repo.get_statistics(),
            'hk_hold': hk_hold_repo.get_statistics(),
            'margin_detail': margin_detail_repo.get_statistics()
        }

        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取数据统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))