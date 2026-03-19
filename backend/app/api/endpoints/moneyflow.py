"""
个股资金流向API（Tushare标准接口）

提供基于主动买卖单统计的资金流向数据接口，包含小单、中单、大单、特大单的买卖量和买卖额，
支持查询历史数据、同步最新数据、获取资金流入排名等功能。

数据源：Tushare pro.moneyflow()
积分消耗：2000积分/次
单次限制：最大6000行
"""

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
async def get_moneyflow(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, ge=1, le=1000, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取个股资金流向数据（Tushare标准接口）

    基于主动买卖单统计，包含小单/中单/大单/特大单的买卖量和买卖额

    Returns:
        包含资金流向数据的响应
    """
    try:
        conditions = []
        params = {}

        # 处理股票代码过滤
        if ts_code:
            conditions.append("ts_code = :ts_code")
            params['ts_code'] = ts_code

        # 处理日期过滤
        if start_date:
            # 将YYYY-MM-DD格式转换为YYYYMMDD
            start_date_formatted = start_date.replace('-', '')
            conditions.append("trade_date >= :start_date")
            params['start_date'] = start_date_formatted

        if end_date:
            end_date_formatted = end_date.replace('-', '')
            conditions.append("trade_date <= :end_date")
            params['end_date'] = end_date_formatted

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 先获取总数
        count_query = text(f"""
            SELECT COUNT(*)
            FROM moneyflow
            WHERE {where_clause}
        """)

        count_result = db.execute(count_query, params)
        total_count = count_result.scalar() or 0

        # 查询数据
        query = text(f"""
            SELECT
                trade_date,
                ts_code,
                buy_sm_vol,
                buy_sm_amount,
                sell_sm_vol,
                sell_sm_amount,
                buy_md_vol,
                buy_md_amount,
                sell_md_vol,
                sell_md_amount,
                buy_lg_vol,
                buy_lg_amount,
                sell_lg_vol,
                sell_lg_amount,
                buy_elg_vol,
                buy_elg_amount,
                sell_elg_vol,
                sell_elg_amount,
                net_mf_vol,
                net_mf_amount,
                created_at,
                updated_at
            FROM moneyflow
            WHERE {where_clause}
            ORDER BY trade_date DESC, net_mf_amount DESC
            LIMIT :limit OFFSET :offset
        """)

        params['limit'] = limit
        params['offset'] = offset

        result = db.execute(query, params)

        items = []
        for row in result:
            items.append({
                "trade_date": row[0],
                "ts_code": row[1],
                "buy_sm_vol": int(row[2]) if row[2] else 0,
                "buy_sm_amount": float(row[3]) if row[3] else 0,
                "sell_sm_vol": int(row[4]) if row[4] else 0,
                "sell_sm_amount": float(row[5]) if row[5] else 0,
                "buy_md_vol": int(row[6]) if row[6] else 0,
                "buy_md_amount": float(row[7]) if row[7] else 0,
                "sell_md_vol": int(row[8]) if row[8] else 0,
                "sell_md_amount": float(row[9]) if row[9] else 0,
                "buy_lg_vol": int(row[10]) if row[10] else 0,
                "buy_lg_amount": float(row[11]) if row[11] else 0,
                "sell_lg_vol": int(row[12]) if row[12] else 0,
                "sell_lg_amount": float(row[13]) if row[13] else 0,
                "buy_elg_vol": int(row[14]) if row[14] else 0,
                "buy_elg_amount": float(row[15]) if row[15] else 0,
                "sell_elg_vol": int(row[16]) if row[16] else 0,
                "sell_elg_amount": float(row[17]) if row[17] else 0,
                "net_mf_vol": int(row[18]) if row[18] else 0,
                "net_mf_amount": float(row[19]) if row[19] else 0,
                "created_at": row[20].isoformat() if row[20] else None,
                "updated_at": row[21].isoformat() if row[21] else None
            })

        # 获取汇总统计
        stats_query = text(f"""
            SELECT
                AVG(net_mf_amount) as avg_net,
                MAX(net_mf_amount) as max_net,
                MIN(net_mf_amount) as min_net,
                SUM(net_mf_amount) as total_net,
                AVG(buy_elg_amount) as avg_elg,
                MAX(buy_elg_amount) as max_elg,
                AVG(buy_lg_amount) as avg_lg,
                MAX(buy_lg_amount) as max_lg,
                MAX(trade_date) as latest_date,
                MIN(trade_date) as earliest_date,
                COUNT(*) as count,
                COUNT(DISTINCT ts_code) as stock_count
            FROM moneyflow
            WHERE {where_clause}
        """)

        stats_result = db.execute(stats_query, params)
        stats_row = stats_result.fetchone()

        statistics = None
        if stats_row:
            statistics = {
                "avg_net": float(stats_row[0]) if stats_row[0] else 0,
                "max_net": float(stats_row[1]) if stats_row[1] else 0,
                "min_net": float(stats_row[2]) if stats_row[2] else 0,
                "total_net": float(stats_row[3]) if stats_row[3] else 0,
                "avg_elg": float(stats_row[4]) if stats_row[4] else 0,
                "max_elg": float(stats_row[5]) if stats_row[5] else 0,
                "avg_lg": float(stats_row[6]) if stats_row[6] else 0,
                "max_lg": float(stats_row[7]) if stats_row[7] else 0,
                "latest_date": stats_row[8] or "",
                "earliest_date": stats_row[9] or "",
                "count": stats_row[10] or 0,
                "stock_count": stats_row[11] or 0
            }

        return ApiResponse.success(
            data={
                "items": items,
                "statistics": statistics,
                "total": total_count,
                "limit": limit,
                "offset": offset
            },
            message="获取个股资金流向成功"
        )

    except Exception as e:
        logger.error(f"获取个股资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_moneyflow(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    同步个股资金流向数据（管理员功能）

    同步模式：阻塞式，等待完成后返回结果
    """
    try:
        from app.services.extended_sync_service import ExtendedDataSyncService
        import asyncio

        service = ExtendedDataSyncService()

        # 转换日期格式
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 执行同步
        result = await service.sync_moneyflow(
            ts_code=ts_code,
            trade_date=trade_date_formatted,
            start_date=start_date_formatted,
            end_date=end_date_formatted
        )

        if result["status"] == "success":
            return ApiResponse.success(
                data=result,
                message=f"成功同步 {result['records']} 条个股资金流向数据"
            )
        else:
            return ApiResponse.error(
                message=result.get("error", "同步失败")
            )

    except Exception as e:
        logger.error(f"同步个股资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_moneyflow_async(
    ts_code: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步个股资金流向数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        ts_code: 股票代码（可选，不指定则获取活跃股票）
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应

    注意：
        - 积分消耗：2000积分/次
        - 单次最大6000行记录
        - 股票和时间参数至少输入一个
    """
    try:
        from app.tasks.moneyflow_tasks import sync_moneyflow_task
        from src.database.db_manager import DatabaseManager

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_moneyflow_task.apply_async(
            kwargs={
                'ts_code': ts_code,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'stock_list': None
            }
        )

        # 记录任务到celery_task_history表，用于任务面板显示
        db_manager = DatabaseManager()
        history_query = """
            INSERT INTO celery_task_history
            (celery_task_id, task_name, display_name, task_type, user_id, status, params, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """

        task_params = {
            'ts_code': ts_code,
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted
        }

        task_metadata = {
            "trigger": "manual",
            "source": "moneyflow_page"
        }

        await asyncio.to_thread(
            db_manager._execute_update,
            history_query,
            (
                celery_task.id,
                'tasks.sync_moneyflow',
                '个股资金流向（Tushare）',
                'data_sync',
                current_user.id,
                'pending',
                json.dumps(task_params),
                json.dumps(task_metadata)
            )
        )

        logger.info(f"个股资金流向同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data={
                "celery_task_id": celery_task.id,
                "task_name": "tasks.sync_moneyflow",
                "display_name": "个股资金流向（Tushare）",
                "status": "pending"
            },
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交个股资金流向同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top")
async def get_top_moneyflow_stocks(
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取资金净流入排名前N的股票（默认最新交易日）

    基于净流入额排序
    """
    try:
        # 如果没有指定日期，获取最新交易日
        if not trade_date:
            date_query = text("SELECT MAX(trade_date) FROM moneyflow")
            date_result = db.execute(date_query)
            trade_date = date_result.scalar()
        else:
            trade_date = trade_date.replace('-', '')

        query = text("""
            SELECT
                trade_date,
                ts_code,
                net_mf_amount,
                net_mf_vol,
                buy_elg_amount,
                buy_lg_amount,
                buy_md_amount,
                buy_sm_amount
            FROM moneyflow
            WHERE trade_date = :trade_date
            ORDER BY net_mf_amount DESC
            LIMIT :limit
        """)

        result = db.execute(query, {"trade_date": trade_date, "limit": limit})

        items = []
        for row in result:
            items.append({
                "trade_date": row[0],
                "ts_code": row[1],
                "net_mf_amount": float(row[2]) if row[2] else 0,
                "net_mf_vol": int(row[3]) if row[3] else 0,
                "buy_elg_amount": float(row[4]) if row[4] else 0,
                "buy_lg_amount": float(row[5]) if row[5] else 0,
                "buy_md_amount": float(row[6]) if row[6] else 0,
                "buy_sm_amount": float(row[7]) if row[7] else 0
            })

        return ApiResponse.success(
            data={
                "items": items,
                "trade_date": trade_date
            },
            message="获取资金流入排名成功"
        )

    except Exception as e:
        logger.error(f"获取资金流入排名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
