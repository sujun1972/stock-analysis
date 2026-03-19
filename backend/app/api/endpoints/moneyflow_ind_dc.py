"""
板块资金流向API（东财概念及行业板块资金流向 DC）

提供行业、概念、地域板块资金流向数据接口，包含主力资金、超大单、大单、中单、小单的流入流出情况，
支持查询历史数据、同步最新数据、获取最新资金流向等功能。
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
async def get_moneyflow_ind_dc(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    content_type: Optional[str] = Query(None, description="数据类型(行业、概念、地域)"),
    ts_code: Optional[str] = Query(None, description="板块代码"),
    limit: int = Query(50, ge=1, le=500, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取板块资金流向数据

    Returns:
        包含资金流向数据的响应
    """
    try:
        conditions = []
        params = {}

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

        # 处理类型过滤
        if content_type:
            conditions.append("content_type = :content_type")
            params['content_type'] = content_type

        # 处理代码过滤
        if ts_code:
            conditions.append("ts_code = :ts_code")
            params['ts_code'] = ts_code

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 先获取总数
        count_query = text(f"""
            SELECT COUNT(*)
            FROM moneyflow_ind_dc
            WHERE {where_clause}
        """)

        count_result = db.execute(count_query, params)
        total_count = count_result.scalar() or 0

        # 查询数据
        query = text(f"""
            SELECT
                trade_date,
                content_type,
                ts_code,
                name,
                pct_change,
                close,
                net_amount,
                net_amount_rate,
                buy_elg_amount,
                buy_elg_amount_rate,
                buy_lg_amount,
                buy_lg_amount_rate,
                buy_md_amount,
                buy_md_amount_rate,
                buy_sm_amount,
                buy_sm_amount_rate,
                buy_sm_amount_stock,
                rank,
                created_at,
                updated_at
            FROM moneyflow_ind_dc
            WHERE {where_clause}
            ORDER BY trade_date DESC, rank ASC
            LIMIT :limit OFFSET :offset
        """)

        params['limit'] = limit
        params['offset'] = offset

        result = db.execute(query, params)

        items = []
        for row in result:
            items.append({
                "trade_date": row[0],
                "content_type": row[1],
                "ts_code": row[2],
                "name": row[3],
                "pct_change": float(row[4]) if row[4] else 0,
                "close": float(row[5]) if row[5] else 0,
                "net_amount": float(row[6]) if row[6] else 0,
                "net_amount_rate": float(row[7]) if row[7] else 0,
                "buy_elg_amount": float(row[8]) if row[8] else 0,
                "buy_elg_amount_rate": float(row[9]) if row[9] else 0,
                "buy_lg_amount": float(row[10]) if row[10] else 0,
                "buy_lg_amount_rate": float(row[11]) if row[11] else 0,
                "buy_md_amount": float(row[12]) if row[12] else 0,
                "buy_md_amount_rate": float(row[13]) if row[13] else 0,
                "buy_sm_amount": float(row[14]) if row[14] else 0,
                "buy_sm_amount_rate": float(row[15]) if row[15] else 0,
                "buy_sm_amount_stock": row[16],
                "rank": row[17] if row[17] else 0,
                "created_at": row[18].isoformat() if row[18] else None,
                "updated_at": row[19].isoformat() if row[19] else None
            })

        # 获取汇总统计
        stats_query = text(f"""
            SELECT
                AVG(net_amount) as avg_net,
                MAX(net_amount) as max_net,
                MIN(net_amount) as min_net,
                SUM(net_amount) as total_net,
                AVG(buy_elg_amount) as avg_elg,
                MAX(buy_elg_amount) as max_elg,
                AVG(buy_lg_amount) as avg_lg,
                MAX(buy_lg_amount) as max_lg,
                AVG(pct_change) as avg_pct,
                MAX(trade_date) as latest_date,
                MIN(trade_date) as earliest_date,
                COUNT(*) as count,
                COUNT(DISTINCT content_type) as type_count,
                COUNT(DISTINCT ts_code) as sector_count
            FROM moneyflow_ind_dc
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
                "avg_pct": float(stats_row[8]) if stats_row[8] else 0,
                "latest_date": stats_row[9] or "",
                "earliest_date": stats_row[10] or "",
                "count": stats_row[11] or 0,
                "type_count": stats_row[12] or 0,
                "sector_count": stats_row[13] or 0
            }

        return ApiResponse.success(
            data={
                "items": items,
                "statistics": statistics,
                "total": total_count,
                "limit": limit,
                "offset": offset
            },
            message="获取板块资金流向成功"
        )

    except Exception as e:
        logger.error(f"获取板块资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_moneyflow_ind_dc(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    content_type: Optional[str] = Query(None, description="资金类型(行业、概念、地域)"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    同步板块资金流向数据（管理员功能）
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
        result = await service.sync_moneyflow_ind_dc(
            ts_code=None,
            trade_date=trade_date_formatted,
            start_date=start_date_formatted,
            end_date=end_date_formatted,
            content_type=content_type
        )

        if result["status"] == "success":
            return ApiResponse.success(
                data=result,
                message=f"成功同步 {result['records']} 条板块资金流向数据"
            )
        else:
            return ApiResponse.error(
                message=result.get("error", "同步失败")
            )

    except Exception as e:
        logger.error(f"同步板块资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_moneyflow_ind_dc_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    content_type: Optional[str] = Query(None, description="资金类型(行业、概念、地域)"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步板块资金流向数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        content_type: 资金类型(行业、概念、地域)
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.moneyflow_ind_dc_tasks import sync_moneyflow_ind_dc_task
        from src.database.db_manager import DatabaseManager

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_moneyflow_ind_dc_task.apply_async(
            kwargs={
                'ts_code': None,
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted,
                'content_type': content_type
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
            'trade_date': trade_date_formatted,
            'start_date': start_date_formatted,
            'end_date': end_date_formatted,
            'content_type': content_type
        }

        task_metadata = {
            "trigger": "manual",
            "source": "moneyflow_ind_dc_page"
        }

        await asyncio.to_thread(
            db_manager._execute_update,
            history_query,
            (
                celery_task.id,
                'tasks.sync_moneyflow_ind_dc',
                '板块资金流向',
                'data_sync',
                current_user.id,
                'pending',
                json.dumps(task_params),
                json.dumps(task_metadata)
            )
        )

        logger.info(f"板块资金流向同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data={
                "celery_task_id": celery_task.id,
                "task_name": "tasks.sync_moneyflow_ind_dc",
                "display_name": "板块资金流向",
                "status": "pending"
            },
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交板块资金流向同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_moneyflow_ind_dc(
    content_type: Optional[str] = Query(None, description="数据类型(行业、概念、地域)"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取最新的板块资金流向数据（按最新交易日期，按资金流入排序）
    """
    try:
        # 构建WHERE条件
        where_conditions = []
        params = {}

        if content_type:
            where_conditions.append("content_type = :content_type")
            params['content_type'] = content_type

        where_clause = " AND " + " AND ".join(where_conditions) if where_conditions else ""

        query = text(f"""
            SELECT
                trade_date,
                content_type,
                ts_code,
                name,
                pct_change,
                close,
                net_amount,
                net_amount_rate,
                buy_elg_amount,
                buy_lg_amount,
                buy_md_amount,
                buy_sm_amount,
                rank
            FROM moneyflow_ind_dc
            WHERE trade_date = (SELECT MAX(trade_date) FROM moneyflow_ind_dc){where_clause}
            ORDER BY net_amount DESC
            LIMIT :limit
        """)

        params['limit'] = limit
        result = db.execute(query, params)
        rows = result.fetchall()

        if not rows:
            return ApiResponse.success(
                data=[],
                message="暂无板块资金流向数据"
            )

        data = []
        for row in rows:
            data.append({
                "trade_date": row[0],
                "content_type": row[1],
                "ts_code": row[2],
                "name": row[3],
                "pct_change": float(row[4]) if row[4] else 0,
                "close": float(row[5]) if row[5] else 0,
                "net_amount": float(row[6]) if row[6] else 0,
                "net_amount_rate": float(row[7]) if row[7] else 0,
                "buy_elg_amount": float(row[8]) if row[8] else 0,
                "buy_lg_amount": float(row[9]) if row[9] else 0,
                "buy_md_amount": float(row[10]) if row[10] else 0,
                "buy_sm_amount": float(row[11]) if row[11] else 0,
                "rank": row[12] if row[12] else 0
            })

        return ApiResponse.success(
            data=data,
            message="获取最新板块资金流向成功"
        )

    except Exception as e:
        logger.error(f"获取最新板块资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
