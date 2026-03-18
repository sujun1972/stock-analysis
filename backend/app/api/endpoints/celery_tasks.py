"""
Celery 任务管理 API

功能:
1. 查询任务状态 (GET /celery/task/{task_id})
2. 取消任务 (POST /celery/task/{task_id}/revoke)
3. 任务历史记录 CRUD
4. 清理僵尸任务

时间处理:
- 数据库存储本地时间
- API 返回 UTC 格式（ISO 8601 + Z 后缀）
- 前端自动转换为本地时间显示
"""

import asyncio
from fastapi import APIRouter, HTTPException, Depends
from celery.result import AsyncResult
from loguru import logger
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
import json

from app.models.api_response import ApiResponse
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.celery_app import celery_app
from src.database.db_manager import DatabaseManager

router = APIRouter(prefix="/celery", tags=["Celery Tasks"])

db = DatabaseManager()


def format_datetime_utc(dt):
    """
    格式化 datetime 为 UTC ISO 格式字符串

    Args:
        dt: datetime 对象

    Returns:
        ISO 8601 格式 + Z 后缀，例如 "2026-03-18T16:52:54Z"
    """
    if dt is None:
        return None
    return dt.isoformat() + 'Z' if dt else None


# Pydantic 模型
class TaskHistoryCreate(BaseModel):
    """创建任务历史记录"""
    celery_task_id: str
    task_name: str
    display_name: Optional[str] = None
    task_type: Optional[str] = 'other'
    params: Optional[dict] = None
    metadata: Optional[dict] = None


class TaskHistoryUpdate(BaseModel):
    """更新任务历史记录"""
    status: Optional[str] = None
    progress: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    worker: Optional[str] = None


@router.get("/task/{task_id}")
async def get_celery_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取 Celery 任务状态（通用接口）

    Args:
        task_id: Celery 任务ID

    Returns:
        任务状态信息
    """
    try:
        result = AsyncResult(task_id, app=celery_app)

        # 状态映射
        status_map = {
            'PENDING': 'pending',
            'STARTED': 'running',
            'SUCCESS': 'success',
            'FAILURE': 'failure',
            'RETRY': 'running',
            'REVOKED': 'failure'
        }

        # 安全地获取任务状态 - 包裹所有访问
        task_state = 'PENDING'
        is_ready = False
        is_successful = False
        is_failed = False

        try:
            # 先获取状态
            task_state = result.state
        except Exception as e:
            logger.warning(f"获取任务state失败: {e}, 使用PENDING作为默认值")
            task_state = 'PENDING'

        try:
            is_ready = result.ready()
            if is_ready and task_state == 'SUCCESS':
                is_successful = True
            elif is_ready and task_state == 'FAILURE':
                is_failed = True
        except Exception as e:
            logger.warning(f"获取任务ready状态失败: {e}")
            # 根据state推断ready状态
            if task_state in ['SUCCESS', 'FAILURE', 'REVOKED']:
                is_ready = True
                is_successful = (task_state == 'SUCCESS')
                is_failed = (task_state in ['FAILURE', 'REVOKED'])

        response_data = {
            'task_id': task_id,
            'state': task_state,
            'status': status_map.get(task_state, 'pending'),
            'ready': is_ready,
            'successful': is_successful,
            'failed': is_failed
        }

        # 添加进度信息（如果任务设置了meta）
        try:
            if hasattr(result, 'info') and hasattr(result.info, 'get') and callable(result.info.get):
                response_data['progress'] = result.info.get('progress', 0)
                response_data['current'] = result.info.get('current', 0)
                response_data['total'] = result.info.get('total', 100)
                response_data['status_text'] = result.info.get('status', '')
        except Exception:
            pass

        # 添加结果（成功时）
        if task_state == 'SUCCESS':
            try:
                response_data['result'] = result.result
            except Exception as e:
                logger.warning(f"获取任务结果失败: {e}")
                response_data['result'] = None

        # 添加错误信息（失败时）
        if task_state == 'FAILURE':
            try:
                if hasattr(result, 'info') and result.info:
                    error_msg = str(result.info)
                else:
                    error_msg = "Unknown error"
                response_data['error'] = error_msg

                if hasattr(result, 'traceback') and result.traceback:
                    response_data['traceback'] = str(result.traceback)
            except Exception as e:
                logger.warning(f"获取任务错误信息失败: {e}")
                response_data['error'] = "Failed to retrieve error information"

        return ApiResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"获取任务 {task_id} 状态失败: {e}")
        # 返回一个基本的响应而不是抛出异常
        return ApiResponse.success(data={
            'task_id': task_id,
            'state': 'PENDING',
            'status': 'pending',
            'ready': False,
            'successful': False,
            'failed': False,
            'error': f"Failed to get task status: {str(e)}"
        })


@router.post("/task/{task_id}/revoke")
async def revoke_celery_task(
    task_id: str,
    terminate: bool = False,
    current_user: User = Depends(get_current_active_user)
):
    """
    取消 Celery 任务

    Args:
        task_id: Celery 任务ID
        terminate: 是否强制终止（发送 SIGTERM）

    Returns:
        取消结果
    """
    try:
        celery_app.control.revoke(task_id, terminate=terminate)

        return ApiResponse.success(
            message=f"任务 {task_id} 已取消",
            data={'task_id': task_id, 'terminated': terminate}
        )

    except Exception as e:
        logger.error(f"取消任务 {task_id} 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task-history")
async def create_task_history(
    task_data: TaskHistoryCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    创建任务执行历史记录

    Args:
        task_data: 任务数据

    Returns:
        创建的任务历史记录
    """
    try:
        # 检查是否已存在
        check_query = """
            SELECT id, celery_task_id, task_name, display_name, task_type, user_id,
                   status, progress, created_at, started_at, completed_at, duration_ms,
                   result, error, worker, params, metadata
            FROM celery_task_history
            WHERE celery_task_id = %s
        """
        existing = await asyncio.to_thread(
            db._execute_query, check_query, (task_data.celery_task_id,)
        )

        if existing:
            row = existing[0]
            existing_dict = {
                "id": row[0],
                "celery_task_id": row[1],
                "task_name": row[2],
                "display_name": row[3],
                "task_type": row[4],
                "user_id": row[5],
                "status": row[6],
                "progress": row[7],
                "created_at": format_datetime_utc(row[8]),
                "started_at": format_datetime_utc(row[9]),
                "completed_at": format_datetime_utc(row[10]),
                "duration_ms": row[11],
                "result": row[12],
                "error": row[13],
                "worker": row[14],
                "params": row[15],
                "metadata": row[16]
            }
            return ApiResponse.success(
                data=existing_dict,
                message="任务历史记录已存在"
            )

        # 创建新记录
        insert_query = """
            INSERT INTO celery_task_history
            (celery_task_id, task_name, display_name, task_type, user_id, status, params, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, 'pending', %s, %s, %s)
            RETURNING id
        """

        params_json = json.dumps(task_data.params) if task_data.params else None
        metadata_json = json.dumps(task_data.metadata) if task_data.metadata else None
        created_at = datetime.utcnow()

        result = await asyncio.to_thread(
            db._execute_query,
            insert_query,
            (
                task_data.celery_task_id,
                task_data.task_name,
                task_data.display_name,
                task_data.task_type,
                current_user.id,
                params_json,
                metadata_json,
                created_at
            )
        )

        new_id = result[0][0] if result else None

        logger.info(f"创建任务历史记录: {task_data.celery_task_id} - {task_data.display_name}")

        return ApiResponse.success(
            data={
                "id": new_id,
                "celery_task_id": task_data.celery_task_id,
                "task_name": task_data.task_name,
                "display_name": task_data.display_name,
                "task_type": task_data.task_type,
                "user_id": current_user.id,
                "status": "pending",
                "progress": 0,
                "created_at": format_datetime_utc(created_at),
                "started_at": None,
                "completed_at": None,
                "duration_ms": None,
                "result": None,
                "error": None,
                "worker": None,
                "params": task_data.params,
                "metadata": task_data.metadata
            },
            message="任务历史记录创建成功"
        )

    except Exception as e:
        logger.error(f"创建任务历史记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/task-history/{task_id}")
async def update_task_history(
    task_id: str,
    update_data: TaskHistoryUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    更新任务执行历史记录

    Args:
        task_id: Celery任务ID
        update_data: 更新数据

    Returns:
        更新后的任务历史记录
    """
    try:
        # 检查任务是否存在
        check_query = """
            SELECT id FROM celery_task_history
            WHERE celery_task_id = %s
        """
        existing = await asyncio.to_thread(
            db._execute_query, check_query, (task_id,)
        )

        if not existing:
            raise HTTPException(status_code=404, detail="任务历史记录不存在")

        # 构建更新语句
        update_fields = []
        update_params = []

        if update_data.status is not None:
            update_fields.append("status = %s")
            update_params.append(update_data.status)

        if update_data.progress is not None:
            update_fields.append("progress = %s")
            update_params.append(update_data.progress)

        if update_data.started_at is not None:
            update_fields.append("started_at = %s")
            update_params.append(update_data.started_at)

        if update_data.completed_at is not None:
            update_fields.append("completed_at = %s")
            update_params.append(update_data.completed_at)

            # 自动计算耗时（如果有started_at）
            if update_data.started_at:
                duration = int((update_data.completed_at - update_data.started_at).total_seconds() * 1000)
                update_fields.append("duration_ms = %s")
                update_params.append(duration)

        if update_data.duration_ms is not None:
            update_fields.append("duration_ms = %s")
            update_params.append(update_data.duration_ms)

        if update_data.result is not None:
            update_fields.append("result = %s")
            update_params.append(json.dumps(update_data.result))

        if update_data.error is not None:
            update_fields.append("error = %s")
            update_params.append(update_data.error)

        if update_data.worker is not None:
            update_fields.append("worker = %s")
            update_params.append(update_data.worker)

        if not update_fields:
            # 没有字段需要更新
            return ApiResponse.success(message="没有字段需要更新")

        # 执行更新
        update_params.append(task_id)
        update_query = f"""
            UPDATE celery_task_history
            SET {', '.join(update_fields)}
            WHERE celery_task_id = %s
        """

        await asyncio.to_thread(
            db._execute_update,
            update_query,
            tuple(update_params)
        )

        # 查询更新后的记录
        select_query = """
            SELECT id, celery_task_id, task_name, display_name, task_type, user_id,
                   status, progress, created_at, started_at, completed_at, duration_ms,
                   result, error, worker, params, metadata
            FROM celery_task_history
            WHERE celery_task_id = %s
        """
        result = await asyncio.to_thread(
            db._execute_query, select_query, (task_id,)
        )

        if result:
            row = result[0]
            history_dict = {
                "id": row[0],
                "celery_task_id": row[1],
                "task_name": row[2],
                "display_name": row[3],
                "task_type": row[4],
                "user_id": row[5],
                "status": row[6],
                "progress": row[7],
                "created_at": format_datetime_utc(row[8]),
                "started_at": format_datetime_utc(row[9]),
                "completed_at": format_datetime_utc(row[10]),
                "duration_ms": row[11],
                "result": row[12],
                "error": row[13],
                "worker": row[14],
                "params": row[15],
                "metadata": row[16]
            }

            logger.info(f"更新任务历史记录: {task_id} - status={history_dict['status']}")

            return ApiResponse.success(
                data=history_dict,
                message="任务历史记录更新成功"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新任务历史记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task-history")
async def get_task_history_list(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取任务历史列表

    Args:
        limit: 返回数量限制
        offset: 偏移量
        status: 按状态筛选
        task_type: 按任务类型筛选

    Returns:
        任务历史列表
    """
    try:
        # 构建查询条件
        where_clauses = ["user_id = %s"]
        query_params = [current_user.id]

        if status:
            where_clauses.append("status = %s")
            query_params.append(status)

        if task_type:
            where_clauses.append("task_type = %s")
            query_params.append(task_type)

        where_sql = " AND ".join(where_clauses)

        # 获取总数
        count_query = f"""
            SELECT COUNT(*) FROM celery_task_history
            WHERE {where_sql}
        """
        count_result = await asyncio.to_thread(
            db._execute_query, count_query, tuple(query_params)
        )
        total = count_result[0][0] if count_result else 0

        # 查询数据
        query_params.extend([limit, offset])
        select_query = f"""
            SELECT id, celery_task_id, task_name, display_name, task_type, user_id,
                   status, progress, created_at, started_at, completed_at, duration_ms,
                   result, error, worker, params, metadata
            FROM celery_task_history
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """

        histories = await asyncio.to_thread(
            db._execute_query, select_query, tuple(query_params)
        )

        tasks = []
        for row in histories:
            tasks.append({
                "id": row[0],
                "celery_task_id": row[1],
                "task_name": row[2],
                "display_name": row[3],
                "task_type": row[4],
                "user_id": row[5],
                "status": row[6],
                "progress": row[7],
                "created_at": format_datetime_utc(row[8]),
                "started_at": format_datetime_utc(row[9]),
                "completed_at": format_datetime_utc(row[10]),
                "duration_ms": row[11],
                "result": row[12],
                "error": row[13],
                "worker": row[14],
                "params": row[15],
                "metadata": row[16]
            })

        return ApiResponse.success(
            data={
                'total': total,
                'limit': limit,
                'offset': offset,
                'tasks': tasks
            }
        )

    except Exception as e:
        logger.error(f"获取任务历史列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task-history/{task_id}")
async def get_task_history_detail(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取任务历史详情

    Args:
        task_id: Celery任务ID

    Returns:
        任务历史详情
    """
    try:
        query = """
            SELECT id, celery_task_id, task_name, display_name, task_type, user_id,
                   status, progress, created_at, started_at, completed_at, duration_ms,
                   result, error, worker, params, metadata
            FROM celery_task_history
            WHERE celery_task_id = %s
        """
        result = await asyncio.to_thread(
            db._execute_query, query, (task_id,)
        )

        if not result:
            raise HTTPException(status_code=404, detail="任务历史记录不存在")

        row = result[0]
        history_dict = {
            "id": row[0],
            "celery_task_id": row[1],
            "task_name": row[2],
            "display_name": row[3],
            "task_type": row[4],
            "user_id": row[5],
            "status": row[6],
            "progress": row[7],
            "created_at": row[8].isoformat() if row[8] else None,
            "started_at": row[9].isoformat() if row[9] else None,
            "completed_at": row[10].isoformat() if row[10] else None,
            "duration_ms": row[11],
            "result": row[12],
            "error": row[13],
            "worker": row[14],
            "params": row[15],
            "metadata": row[16]
        }

        return ApiResponse.success(data=history_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务历史详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/task-history/{task_id}")
async def delete_task_history(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    删除任务历史记录

    Args:
        task_id: Celery任务ID

    Returns:
        删除结果
    """
    try:
        # 检查任务是否属于当前用户
        check_query = """
            SELECT user_id FROM celery_task_history
            WHERE celery_task_id = %s
        """
        check_result = await asyncio.to_thread(
            db._execute_query, check_query, (task_id,)
        )

        if not check_result:
            raise HTTPException(status_code=404, detail="任务历史记录不存在")

        task_user_id = check_result[0][0]
        if task_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除此任务记录")

        # 删除任务记录
        delete_query = """
            DELETE FROM celery_task_history
            WHERE celery_task_id = %s
        """
        await asyncio.to_thread(
            db._execute_update, delete_query, (task_id,)
        )

        logger.info(f"删除任务历史记录: {task_id}")

        return ApiResponse.success(message="任务历史记录已删除")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务历史记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/task-history/cleanup-stale")
async def cleanup_stale_tasks(
    current_user: User = Depends(get_current_active_user)
):
    """
    清理僵尸任务（运行中但超过5分钟未完成的任务）

    Returns:
        清理结果
    """
    try:
        # 查找运行中但创建时间超过5分钟的任务
        query = """
            SELECT celery_task_id, task_name, display_name, created_at
            FROM celery_task_history
            WHERE user_id = %s
              AND status IN ('running', 'pending', 'progress')
              AND created_at < NOW() - INTERVAL '5 minutes'
        """
        stale_tasks = await asyncio.to_thread(
            db._execute_query, query, (current_user.id,)
        )

        if not stale_tasks:
            return ApiResponse.success(
                data={'deleted_count': 0},
                message="没有发现僵尸任务"
            )

        # 更新这些任务为失败状态
        update_query = """
            UPDATE celery_task_history
            SET status = 'failure',
                completed_at = NOW(),
                error = 'Task marked as stale and cleaned up',
                duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
            WHERE user_id = %s
              AND status IN ('running', 'pending', 'progress')
              AND created_at < NOW() - INTERVAL '5 minutes'
        """
        rows_updated = await asyncio.to_thread(
            db._execute_update, update_query, (current_user.id,)
        )

        logger.info(f"清理了 {rows_updated} 个僵尸任务")

        return ApiResponse.success(
            data={'deleted_count': rows_updated},
            message=f"已清理 {rows_updated} 个僵尸任务"
        )

    except Exception as e:
        logger.error(f"清理僵尸任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
