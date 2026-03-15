"""
定时任务管理 API
管理数据同步的定时任务配置和执行历史
"""

import asyncio
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from pydantic import BaseModel, field_validator

from app.api.error_handler import handle_api_errors
from app.core.exceptions import DatabaseError
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
from src.database.db_manager import DatabaseManager

router = APIRouter()


# ==========================================
# 工具函数
# ==========================================

def validate_cron_expression(cron_expr: str) -> bool:
    """
    验证Cron表达式是否有效

    Args:
        cron_expr: Cron表达式，格式: "分 时 日 月 周"

    Returns:
        是否有效
    """
    try:
        from croniter import croniter
        croniter(cron_expr, datetime.now())
        return True
    except Exception:
        # croniter不可用或表达式无效，使用简单验证
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False
        # 简单检查每个字段是否符合基本格式
        return all(part for part in parts)


def calculate_next_run_time(cron_expr: str) -> Optional[datetime]:
    """
    计算下次执行时间

    Args:
        cron_expr: Cron表达式

    Returns:
        下次执行时间，解析失败返回None
    """
    try:
        from croniter import croniter
        cron = croniter(cron_expr, datetime.now())
        return cron.get_next(datetime)
    except Exception:
        return None


# ==========================================
# 数据模型
# ==========================================

class ScheduledTaskCreate(BaseModel):
    """创建定时任务请求"""

    task_name: str
    module: str
    description: Optional[str] = None
    cron_expression: str
    enabled: bool = False
    params: Optional[Dict[str, Any]] = {}

    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """验证Cron表达式格式"""
        if not validate_cron_expression(v):
            raise ValueError('无效的Cron表达式，格式应为: "分 时 日 月 周"')
        return v


class ScheduledTaskUpdate(BaseModel):
    """更新定时任务请求"""

    description: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    params: Optional[Dict[str, Any]] = None

    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """验证Cron表达式格式"""
        if v is not None and not validate_cron_expression(v):
            raise ValueError('无效的Cron表达式，格式应为: "分 时 日 月 周"')
        return v


@router.get("/tasks")
@handle_api_errors
async def get_scheduled_tasks(
    current_user: User = Depends(require_admin)
):
    """
    获取所有定时任务列表

    Returns:
        定时任务列表
    """
    try:
        db = DatabaseManager()

        query = """
            SELECT
                id,
                task_name,
                module,
                description,
                cron_expression,
                enabled,
                params,
                last_run_at,
                next_run_at,
                last_status,
                last_error,
                run_count,
                created_at,
                updated_at
            FROM scheduled_tasks
            ORDER BY id
        """

        result = await asyncio.to_thread(db._execute_query, query)

        tasks = []
        for row in result:
            tasks.append(
                {
                    "id": row[0],
                    "task_name": row[1],
                    "module": row[2],
                    "description": row[3],
                    "cron_expression": row[4],
                    "enabled": row[5],
                    "params": row[6],
                    "last_run_at": row[7].strftime("%Y-%m-%d %H:%M:%S") if row[7] else None,
                    "next_run_at": row[8].strftime("%Y-%m-%d %H:%M:%S") if row[8] else None,
                    "last_status": row[9],
                    "last_error": row[10],
                    "run_count": row[11],
                    "created_at": row[12].strftime("%Y-%m-%d %H:%M:%S") if row[12] else None,
                    "updated_at": row[13].strftime("%Y-%m-%d %H:%M:%S") if row[13] else None,
                }
            )

        return ApiResponse.success(data=tasks)
    except DatabaseError as e:
        logger.error(f"数据库查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
@handle_api_errors
async def get_scheduled_task(
    task_id: int,
    current_user: User = Depends(require_admin)
):
    """
    获取单个定时任务详情

    Args:
        task_id: 任务ID

    Returns:
        定时任务详情
    """
    try:
        db = DatabaseManager()

        query = """
            SELECT
                id,
                task_name,
                module,
                description,
                cron_expression,
                enabled,
                params,
                last_run_at,
                next_run_at,
                last_status,
                last_error,
                run_count,
                created_at,
                updated_at
            FROM scheduled_tasks
            WHERE id = %s
        """

        result = await asyncio.to_thread(db._execute_query, query, (task_id,))

        if not result:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

        row = result[0]
        task = {
            "id": row[0],
            "task_name": row[1],
            "module": row[2],
            "description": row[3],
            "cron_expression": row[4],
            "enabled": row[5],
            "params": row[6],
            "last_run_at": row[7].strftime("%Y-%m-%d %H:%M:%S") if row[7] else None,
            "next_run_at": row[8].strftime("%Y-%m-%d %H:%M:%S") if row[8] else None,
            "last_status": row[9],
            "last_error": row[10],
            "run_count": row[11],
            "created_at": row[12].strftime("%Y-%m-%d %H:%M:%S") if row[12] else None,
            "updated_at": row[13].strftime("%Y-%m-%d %H:%M:%S") if row[13] else None,
        }

        return ApiResponse.success(data=task)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取定时任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks")
@handle_api_errors
async def create_scheduled_task(
    request: ScheduledTaskCreate,
    current_user: User = Depends(require_admin)
):
    """
    创建定时任务

    Args:
        request: 任务创建请求

    Returns:
        创建的任务ID
    """
    try:
        db = DatabaseManager()

        # 验证模块名称
        valid_modules = [
            "stock_list",
            "new_stocks",
            "delisted_stocks",
            "daily",
            "minute",
            "realtime",
        ]
        if request.module not in valid_modules:
            raise HTTPException(
                status_code=400, detail=f"无效的模块名称，支持: {', '.join(valid_modules)}"
            )

        # 检查任务名称是否已存在
        check_query = "SELECT id FROM scheduled_tasks WHERE task_name = %s"
        existing = await asyncio.to_thread(
            db._execute_query, check_query, (request.task_name,)
        )

        if existing:
            raise HTTPException(status_code=400, detail=f"任务名称 '{request.task_name}' 已存在")

        # 计算下次执行时间
        next_run_at = calculate_next_run_time(request.cron_expression)

        # 插入新任务
        insert_query = """
            INSERT INTO scheduled_tasks (
                task_name, module, description, cron_expression, enabled, params, next_run_at
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
            RETURNING id
        """

        import json

        result = await asyncio.to_thread(
            db._execute_query,
            insert_query,
            (
                request.task_name,
                request.module,
                request.description,
                request.cron_expression,
                request.enabled,
                json.dumps(request.params or {}),
                next_run_at,
            ),
        )

        task_id = result[0][0]
        logger.info(f"✓ 创建定时任务: {request.task_name} (ID: {task_id})")

        return ApiResponse.success(data={"id": task_id}, message="创建成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tasks/{task_id}")
@handle_api_errors
async def update_scheduled_task(
    task_id: int,
    request: ScheduledTaskUpdate,
    current_user: User = Depends(require_admin)
):
    """
    更新定时任务

    Args:
        task_id: 任务ID
        request: 任务更新请求

    Returns:
        更新结果
    """
    try:
        db = DatabaseManager()

        # 构建动态更新语句
        updates = []
        params = []

        if request.description is not None:
            updates.append("description = %s")
            params.append(request.description)

        if request.cron_expression is not None:
            updates.append("cron_expression = %s")
            params.append(request.cron_expression)
            # 同时更新下次执行时间
            next_run_at = calculate_next_run_time(request.cron_expression)
            updates.append("next_run_at = %s")
            params.append(next_run_at)

        if request.enabled is not None:
            updates.append("enabled = %s")
            params.append(request.enabled)

        if request.params is not None:
            import json

            updates.append("params = %s::jsonb")
            params.append(json.dumps(request.params))

        if not updates:
            raise HTTPException(status_code=400, detail="没有需要更新的字段")

        query = f"""
            UPDATE scheduled_tasks
            SET {', '.join(updates)}
            WHERE id = %s
        """
        params.append(task_id)

        await asyncio.to_thread(db._execute_update, query, tuple(params))

        logger.info(f"✓ 更新定时任务: {task_id}")

        return ApiResponse.success(data={"id": task_id}, message="更新成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}")
@handle_api_errors
async def delete_scheduled_task(
    task_id: int,
    current_user: User = Depends(require_admin)
):
    """
    删除定时任务

    Args:
        task_id: 任务ID

    Returns:
        删除结果
    """
    try:
        db = DatabaseManager()

        query = "DELETE FROM scheduled_tasks WHERE id = %s"

        await asyncio.to_thread(db._execute_update, query, (task_id,))

        logger.info(f"✓ 删除定时任务: {task_id}")

        return ApiResponse.success(data={"id": task_id}, message="删除成功")
    except Exception as e:
        logger.error(f"删除定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/toggle")
@handle_api_errors
async def toggle_scheduled_task(
    task_id: int,
    current_user: User = Depends(require_admin)
):
    """
    切换定时任务启用状态

    Args:
        task_id: 任务ID

    Returns:
        新的启用状态
    """
    try:
        db = DatabaseManager()

        # 获取当前状态
        query = "SELECT enabled FROM scheduled_tasks WHERE id = %s"
        result = await asyncio.to_thread(db._execute_query, query, (task_id,))

        if not result:
            raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

        current_enabled = result[0][0]
        new_enabled = not current_enabled

        # 更新状态
        update_query = "UPDATE scheduled_tasks SET enabled = %s WHERE id = %s"
        await asyncio.to_thread(
            db._execute_update, update_query, (new_enabled, task_id)
        )

        logger.info(f"✓ 切换定时任务状态: {task_id} -> {new_enabled}")

        return ApiResponse.success(data={"enabled": new_enabled}, message="状态切换成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换定时任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/history")
@handle_api_errors
async def get_task_execution_history(
    task_id: int,
    limit: int = 20,
    current_user: User = Depends(require_admin)
):
    """
    获取任务执行历史

    Args:
        task_id: 任务ID
        limit: 返回记录数

    Returns:
        执行历史列表
    """
    try:
        db = DatabaseManager()

        query = """
            SELECT
                id,
                task_name,
                module,
                status,
                started_at,
                completed_at,
                duration_seconds,
                result_summary,
                error_message
            FROM task_execution_history
            WHERE task_id = %s
            ORDER BY started_at DESC
            LIMIT %s
        """

        result = await asyncio.to_thread(db._execute_query, query, (task_id, limit))

        history = []
        for row in result:
            history.append(
                {
                    "id": row[0],
                    "task_name": row[1],
                    "module": row[2],
                    "status": row[3],
                    "started_at": row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else None,
                    "completed_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else None,
                    "duration_seconds": row[6],
                    "result_summary": row[7],
                    "error_message": row[8],
                }
            )

        return ApiResponse.success(data=history)
    except Exception as e:
        logger.error(f"获取任务执行历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/recent")
@handle_api_errors
async def get_recent_execution_history(
    limit: int = 50,
    current_user: User = Depends(require_admin)
):
    """
    获取最近的任务执行历史

    Args:
        limit: 返回记录数

    Returns:
        执行历史列表
    """
    try:
        db = DatabaseManager()

        query = """
            SELECT
                h.id,
                h.task_name,
                h.module,
                h.status,
                h.started_at,
                h.completed_at,
                h.duration_seconds,
                h.result_summary,
                h.error_message,
                t.cron_expression
            FROM task_execution_history h
            LEFT JOIN scheduled_tasks t ON h.task_id = t.id
            ORDER BY h.started_at DESC
            LIMIT %s
        """

        result = await asyncio.to_thread(db._execute_query, query, (limit,))

        history = []
        for row in result:
            history.append(
                {
                    "id": row[0],
                    "task_name": row[1],
                    "module": row[2],
                    "status": row[3],
                    "started_at": row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else None,
                    "completed_at": row[5].strftime("%Y-%m-%d %H:%M:%S") if row[5] else None,
                    "duration_seconds": row[6],
                    "result_summary": row[7],
                    "error_message": row[8],
                    "cron_expression": row[9],
                }
            )

        return ApiResponse.success(data=history)
    except Exception as e:
        logger.error(f"获取最近执行历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate-cron")
@handle_api_errors
async def validate_cron(
    cron_expression: str,
    current_user: User = Depends(require_admin)
):
    """
    验证Cron表达式并返回下次执行时间

    Args:
        cron_expression: Cron表达式

    Returns:
        验证结果和下次执行时间
    """
    try:
        is_valid = validate_cron_expression(cron_expression)

        if not is_valid:
            return ApiResponse.error(
                data={
                    "valid": False,
                    "error": "格式应为: 分 时 日 月 周 (例: 0 9 * * 1-5)"
                },
                message="无效的Cron表达式",
                code=400
            ).to_dict()

        next_run = calculate_next_run_time(cron_expression)

        return ApiResponse.success(
            data={
                "valid": True,
                "next_run_at": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None,
                "cron_expression": cron_expression
            },
            message="Cron表达式验证成功"
        ).to_dict()
    except Exception as e:
        logger.error(f"验证Cron表达式失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
