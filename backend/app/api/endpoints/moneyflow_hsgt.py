"""
沪深港通资金流向API

提供沪股通、深股通、港股通(上海)、港股通(深圳)的资金流向数据接口，
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
async def get_moneyflow_hsgt(
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    limit: int = Query(30, ge=1, le=365, description="返回记录数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取沪深港通资金流向数据

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

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # 先获取总数
        count_query = text(f"""
            SELECT COUNT(*)
            FROM moneyflow_hsgt
            WHERE {where_clause}
        """)

        count_result = db.execute(count_query, params)
        total_count = count_result.scalar() or 0

        # 查询数据
        query = text(f"""
            SELECT
                trade_date,
                ggt_ss,
                ggt_sz,
                hgt,
                sgt,
                north_money,
                south_money,
                created_at,
                updated_at
            FROM moneyflow_hsgt
            WHERE {where_clause}
            ORDER BY trade_date DESC
            LIMIT :limit OFFSET :offset
        """)

        params['limit'] = limit
        params['offset'] = offset

        result = db.execute(query, params)

        items = []
        for row in result:
            items.append({
                "trade_date": row[0],
                "ggt_ss": float(row[1]) if row[1] else 0,  # 港股通（上海）
                "ggt_sz": float(row[2]) if row[2] else 0,  # 港股通（深圳）
                "hgt": float(row[3]) if row[3] else 0,     # 沪股通
                "sgt": float(row[4]) if row[4] else 0,     # 深股通
                "north_money": float(row[5]) if row[5] else 0,  # 北向资金
                "south_money": float(row[6]) if row[6] else 0,  # 南向资金
                "created_at": row[7].isoformat() if row[7] else None,
                "updated_at": row[8].isoformat() if row[8] else None
            })

        # 获取汇总统计
        stats_query = text(f"""
            SELECT
                AVG(north_money) as avg_north,
                MAX(north_money) as max_north,
                MIN(north_money) as min_north,
                SUM(north_money) as total_north,
                AVG(south_money) as avg_south,
                MAX(south_money) as max_south,
                MIN(south_money) as min_south,
                SUM(south_money) as total_south,
                MAX(trade_date) as latest_date,
                MIN(trade_date) as earliest_date,
                COUNT(*) as count
            FROM moneyflow_hsgt
            WHERE {where_clause}
        """)

        stats_result = db.execute(stats_query, params)
        stats_row = stats_result.fetchone()

        statistics = None
        if stats_row:
            statistics = {
                "avg_north": float(stats_row[0]) if stats_row[0] else 0,
                "max_north": float(stats_row[1]) if stats_row[1] else 0,
                "min_north": float(stats_row[2]) if stats_row[2] else 0,
                "total_north": float(stats_row[3]) if stats_row[3] else 0,
                "avg_south": float(stats_row[4]) if stats_row[4] else 0,
                "max_south": float(stats_row[5]) if stats_row[5] else 0,
                "min_south": float(stats_row[6]) if stats_row[6] else 0,
                "total_south": float(stats_row[7]) if stats_row[7] else 0,
                "latest_date": stats_row[8] or "",
                "earliest_date": stats_row[9] or "",
                "count": stats_row[10] or 0
            }

        return ApiResponse.success(
            data={
                "items": items,
                "statistics": statistics,
                "total": total_count,
                "limit": limit,
                "offset": offset
            },
            message="获取沪深港通资金流向成功"
        )

    except Exception as e:
        logger.error(f"获取沪深港通资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_moneyflow_hsgt(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    同步沪深港通资金流向数据（管理员功能）
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
        result = await service.sync_moneyflow_hsgt(
            trade_date=trade_date_formatted,
            start_date=start_date_formatted,
            end_date=end_date_formatted
        )

        if result["status"] == "success":
            return ApiResponse.success(
                data=result,
                message=f"成功同步 {result['records']} 条资金流向数据"
            )
        else:
            return ApiResponse.error(
                message=result.get("error", "同步失败")
            )

    except Exception as e:
        logger.error(f"同步沪深港通资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_moneyflow_hsgt_async(
    trade_date: Optional[str] = Query(None, description="交易日期，格式：YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="开始日期，格式：YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期，格式：YYYY-MM-DD"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步沪深港通资金流向数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        trade_date: 单个交易日期，格式：YYYY-MM-DD
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.moneyflow_hsgt_tasks import sync_moneyflow_hsgt_task
        from src.database.db_manager import DatabaseManager

        # 转换日期格式：YYYY-MM-DD -> YYYYMMDD（Tushare格式）
        trade_date_formatted = trade_date.replace('-', '') if trade_date else None
        start_date_formatted = start_date.replace('-', '') if start_date else None
        end_date_formatted = end_date.replace('-', '') if end_date else None

        # 提交Celery任务（异步执行）
        celery_task = sync_moneyflow_hsgt_task.apply_async(
            kwargs={
                'trade_date': trade_date_formatted,
                'start_date': start_date_formatted,
                'end_date': end_date_formatted
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
            'end_date': end_date_formatted
        }

        task_metadata = {
            "trigger": "manual",
            "source": "moneyflow_hsgt_page"
        }

        await asyncio.to_thread(
            db_manager._execute_update,
            history_query,
            (
                celery_task.id,
                'tasks.sync_moneyflow_hsgt',
                '沪深港通资金流向',
                'data_sync',
                current_user.id,
                'pending',
                json.dumps(task_params),
                json.dumps(task_metadata)
            )
        )

        logger.info(f"沪深港通资金流向同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data={
                "celery_task_id": celery_task.id,
                "task_name": "tasks.sync_moneyflow_hsgt",
                "display_name": "沪深港通资金流向",
                "status": "pending"
            },
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交沪深港通资金流向同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_moneyflow(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取最新的资金流向数据
    """
    try:
        query = text("""
            SELECT
                trade_date,
                ggt_ss,
                ggt_sz,
                hgt,
                sgt,
                north_money,
                south_money
            FROM moneyflow_hsgt
            ORDER BY trade_date DESC
            LIMIT 1
        """)

        result = db.execute(query)
        row = result.fetchone()

        if not row:
            return ApiResponse.success(
                data=None,
                message="暂无资金流向数据"
            )

        data = {
            "trade_date": row[0],
            "ggt_ss": float(row[1]) if row[1] else 0,
            "ggt_sz": float(row[2]) if row[2] else 0,
            "hgt": float(row[3]) if row[3] else 0,
            "sgt": float(row[4]) if row[4] else 0,
            "north_money": float(row[5]) if row[5] else 0,
            "south_money": float(row[6]) if row[6] else 0,
            "net_inflow": float(row[5]) - float(row[6]) if row[5] and row[6] else 0
        }

        return ApiResponse.success(
            data=data,
            message="获取最新资金流向成功"
        )

    except Exception as e:
        logger.error(f"获取最新资金流向失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))