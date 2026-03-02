"""
用户回测历史记录API
提供用户查看自己回测历史的功能
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import text
from loguru import logger

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(tags=["回测历史"])


@router.get("")
async def get_user_backtest_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status_filter: Optional[str] = Query(None, description="状态筛选: completed, failed, running"),
    strategy_id: Optional[int] = Query(None, description="策略ID筛选"),
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取当前用户的回测历史记录

    支持分页、状态筛选和策略筛选
    """
    try:
        # 构建查询条件
        conditions = []
        params = {"executed_by": current_user.username}

        if status_filter:
            conditions.append("se.status = :status_filter")
            params["status_filter"] = status_filter

        if strategy_id:
            conditions.append("s.id = :strategy_id")
            params["strategy_id"] = strategy_id

        where_clause = "WHERE se.executed_by = :executed_by"
        if conditions:
            where_clause += " AND " + " AND ".join(conditions)

        # 查询总数
        count_query = text(f"""
            SELECT COUNT(*)
            FROM strategy_executions se
            LEFT JOIN strategies s ON (
                s.id = CAST(se.execution_params->>'strategy_id' AS INT)
            )
            {where_clause}
        """)

        total_result = db.execute(count_query, params)
        total = total_result.scalar()

        # 查询数据
        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        query = text(f"""
            SELECT
                se.id,
                se.execution_type,
                se.status,
                se.metrics,
                se.execution_params,
                se.result,
                se.error_message,
                se.execution_duration_ms,
                se.started_at,
                se.completed_at,
                se.created_at,
                s.id as strategy_id,
                s.name as strategy_name,
                s.display_name as strategy_display_name,
                s.source_type as strategy_source_type
            FROM strategy_executions se
            LEFT JOIN strategies s ON (
                s.id = CAST(se.execution_params->>'strategy_id' AS INT)
            )
            {where_clause}
            ORDER BY se.created_at DESC
            LIMIT :limit OFFSET :offset
        """)

        result = db.execute(query, params)
        rows = result.fetchall()

        # 格式化结果
        items = []
        for row in rows:
            # 提取关键指标
            metrics = row[3] or {}
            execution_params = row[4] or {}

            item = {
                "id": row[0],
                "execution_type": row[1],
                "status": row[2],
                "metrics": {
                    "total_return": metrics.get("total_return", 0.0),
                    "annual_return": metrics.get("annual_return", 0.0),
                    "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
                    "max_drawdown": metrics.get("max_drawdown", 0.0),
                    "win_rate": metrics.get("win_rate", 0.0),
                    "total_trades": metrics.get("total_trades", 0),
                },
                "execution_params": {
                    "stock_pool": execution_params.get("stock_pool", []),
                    "start_date": execution_params.get("start_date"),
                    "end_date": execution_params.get("end_date"),
                    "initial_capital": execution_params.get("initial_capital", 1000000),
                },
                "error_message": row[6],
                "execution_duration_ms": row[7],
                "started_at": row[8].isoformat() if row[8] else None,
                "completed_at": row[9].isoformat() if row[9] else None,
                "created_at": row[10].isoformat() if row[10] else None,
                "strategy": {
                    "id": row[11],
                    "name": row[12],
                    "display_name": row[13],
                    "source_type": row[14],
                } if row[11] else None,
            }
            items.append(item)

        return {
            "success": True,
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": items
            }
        }

    except Exception as e:
        logger.error(f"获取回测历史失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取回测历史失败: {str(e)}"
        )


@router.get("/{execution_id}")
async def get_backtest_detail(
    execution_id: int,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取回测详情（包含完整的result数据）

    只能查看自己的回测记录
    """
    try:
        query = text("""
            SELECT
                se.id,
                se.execution_type,
                se.status,
                se.metrics,
                se.execution_params,
                se.result,
                se.error_message,
                se.execution_duration_ms,
                se.started_at,
                se.completed_at,
                se.created_at,
                se.executed_by,
                s.id as strategy_id,
                s.name as strategy_name,
                s.display_name as strategy_display_name,
                s.source_type as strategy_source_type,
                s.code as strategy_code
            FROM strategy_executions se
            LEFT JOIN strategies s ON (
                s.id = CAST(se.execution_params->>'strategy_id' AS INT)
            )
            WHERE se.id = :execution_id
        """)

        result = db.execute(query, {"execution_id": execution_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="回测记录不存在"
            )

        # 检查权限：只能查看自己的回测记录
        if row[11] != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权查看此回测记录"
            )

        # 格式化结果
        result = row[5] or {}

        detail = {
            "id": row[0],
            "execution_type": row[1],
            "status": row[2],
            "metrics": row[3],
            "execution_params": row[4],
            "result": {
                "equity_curve": result.get("equity_curve", []),
                "trades": result.get("trades", []),
                "stock_charts": result.get("stock_charts", {}),
            },
            "error_message": row[6],
            "execution_duration_ms": row[7],
            "started_at": row[8].isoformat() if row[8] else None,
            "completed_at": row[9].isoformat() if row[9] else None,
            "created_at": row[10].isoformat() if row[10] else None,
            "executed_by": row[11],
            "strategy": {
                "id": row[12],
                "name": row[13],
                "display_name": row[14],
                "source_type": row[15],
            } if row[12] else None,
        }

        return {
            "success": True,
            "data": detail
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取回测详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取回测详情失败: {str(e)}"
        )


@router.delete("/{execution_id}")
async def delete_backtest_record(
    execution_id: int,
    db = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    删除回测记录

    只能删除自己的回测记录
    """
    try:
        # 先查询记录是否存在且属于当前用户
        check_query = text("""
            SELECT executed_by
            FROM strategy_executions
            WHERE id = :execution_id
        """)

        result = db.execute(check_query, {"execution_id": execution_id})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="回测记录不存在"
            )

        if row[0] != current_user.username:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权删除此回测记录"
            )

        # 删除记录
        delete_query = text("""
            DELETE FROM strategy_executions
            WHERE id = :execution_id
        """)
        db.execute(delete_query, {"execution_id": execution_id})
        db.commit()

        return {
            "success": True,
            "message": "回测记录已删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除回测记录失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除回测记录失败: {str(e)}"
        )
