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

架构说明:
- 使用 CeleryTaskHistoryService 处理业务逻辑
- 使用 CeleryTaskHistoryRepository 访问数据库
- 移除所有直接 SQL 查询
"""

import asyncio

from fastapi import APIRouter, HTTPException, Depends
from celery.result import AsyncResult
from loguru import logger
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.api_response import ApiResponse
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.celery_app import celery_app
from app.services.celery_task_history_service import CeleryTaskHistoryService
from app.repositories.celery_task_history_repository import CeleryTaskHistoryRepository

router = APIRouter(prefix="/celery", tags=["Celery Tasks"])


# ==================== Pydantic 模型 ====================

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


# ==================== Celery 任务状态查询 ====================

@router.get("/task/{task_id}")
async def get_celery_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取 Celery 任务状态（实时从 Celery 查询）

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

        # 安全地获取任务状态
        task_state = 'PENDING'
        is_ready = False
        is_successful = False
        is_failed = False

        try:
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
            if task_state in ['SUCCESS', 'FAILURE', 'REVOKED']:
                is_ready = True
                is_successful = (task_state == 'SUCCESS')
                is_failed = (task_state in ['FAILURE', 'REVOKED'])

        # PENDING + 数据库有 started_at 说明 worker 重启后任务已丢失（僵尸任务）
        # 注意：新提交的任务存在竞态窗口（task_prerun 已写 started_at，但 Redis 还未变成 STARTED）
        # 因此要求 started_at 距今超过 60 秒才判定为僵尸，避免误杀新任务
        zombie_error: Optional[str] = None
        if task_state == 'PENDING':
            try:
                repo = CeleryTaskHistoryRepository()
                db_task = await asyncio.to_thread(repo.get_by_task_id, task_id)
                if db_task and db_task.get('started_at') and db_task.get('status') in ('running', 'pending', 'progress'):
                    started_at = db_task['started_at']
                    # 计算 started_at 距今的秒数，给新任务 60 秒的宽限期
                    if isinstance(started_at, str):
                        started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    now = datetime.now(tz=started_at.tzinfo) if started_at.tzinfo else datetime.now()
                    seconds_since_start = (now - started_at).total_seconds()
                    if seconds_since_start > 60:
                        # worker 已重启，任务不会再运行，标记为失败并更新数据库
                        zombie_error = 'Worker 重启，任务已中断'
                        await asyncio.to_thread(
                            repo.update_task_status,
                            task_id,
                            status='failure',
                            error=zombie_error
                        )
                        task_state = 'FAILURE'
                        is_ready = True
                        is_failed = True
                        logger.warning(f"检测到僵尸任务（worker重启）: {task_id[:8]}... (started {seconds_since_start:.0f}s ago)")
            except Exception as e:
                logger.warning(f"僵尸任务检测失败: {e}")

        response_data = {
            'task_id': task_id,
            'state': task_state,
            'status': status_map.get(task_state, 'pending'),
            'ready': is_ready,
            'successful': is_successful,
            'failed': is_failed
        }

        # 添加进度信息（如果任务设置了meta）—— 仅在 PROGRESS/STARTED 状态时读取，
        # PENDING 下 result.info 可能是残留的旧数据，不可信
        try:
            if task_state in ('PROGRESS', 'STARTED') and hasattr(result, 'info') and hasattr(result.info, 'get') and callable(result.info.get):
                # 优先读 progress（百分比），兜底读 percent（旧字段名兼容）
                response_data['progress'] = result.info.get('progress') or result.info.get('percent', 0)
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
                if zombie_error:
                    error_msg = zombie_error
                elif hasattr(result, 'info') and result.info:
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


# ==================== 任务历史记录 CRUD ====================

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
        service = CeleryTaskHistoryService()

        # 使用 Service 层的验证和创建方法
        task = await service.validate_and_create_or_update(
            celery_task_id=task_data.celery_task_id,
            task_name=task_data.task_name,
            display_name=task_data.display_name,
            task_type=task_data.task_type,
            user_id=current_user.id,
            params=task_data.params,
            metadata=task_data.metadata
        )

        if task.get('id'):
            # 任务已存在
            message = "任务历史记录已存在"
        else:
            message = "任务历史记录创建成功"

        return ApiResponse.success(data=task, message=message)

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
        service = CeleryTaskHistoryService()

        # 检查任务是否存在
        existing_task = await service.get_task_by_id(task_id)
        if not existing_task:
            raise HTTPException(status_code=404, detail="任务历史记录不存在")

        # 检查权限
        if existing_task.get('user_id') != current_user.id:
            raise HTTPException(status_code=403, detail="无权修改此任务记录")

        # 更新任务状态
        updated_task = await service.update_task_status(
            celery_task_id=task_id,
            status=update_data.status,
            progress=update_data.progress,
            started_at=update_data.started_at,
            completed_at=update_data.completed_at,
            duration_ms=update_data.duration_ms,
            result=update_data.result,
            error=update_data.error,
            worker=update_data.worker
        )

        return ApiResponse.success(
            data=updated_task,
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
        任务历史列表和统计信息
    """
    try:
        service = CeleryTaskHistoryService()

        # 使用组合查询方法，同时获取列表和统计
        result = await service.get_task_list_with_statistics(
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            status=status,
            task_type=task_type
        )

        return ApiResponse.success(data=result)

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
        service = CeleryTaskHistoryService()

        task = await service.get_task_by_id(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="任务历史记录不存在")

        # 检查权限（可选，根据需求决定是否限制）
        # if task.get('user_id') != current_user.id:
        #     raise HTTPException(status_code=403, detail="无权查看此任务记录")

        return ApiResponse.success(data=task)

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
        service = CeleryTaskHistoryService()

        # 检查任务是否存在
        task = await service.get_task_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务历史记录不存在")

        # 检查权限
        if task.get('user_id') != current_user.id:
            raise HTTPException(status_code=403, detail="无权删除此任务记录")

        # 若任务仍在运行，先撤销 Celery 任务（防止后台继续运行）
        active_statuses = {'pending', 'running'}
        if task.get('status') in active_statuses:
            try:
                celery_app.control.revoke(task_id, terminate=True)
                logger.info(f"删除前撤销活动任务: {task_id[:8]}...")
            except Exception as revoke_err:
                logger.warning(f"撤销任务失败（继续删除记录）: {revoke_err}")

        # 删除任务记录
        rows_deleted = await service.delete_task_history(
            celery_task_id=task_id,
            user_id=current_user.id
        )

        if rows_deleted > 0:
            message = "任务历史记录已删除"
        else:
            message = "未找到要删除的记录"

        return ApiResponse.success(message=message)

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
    清理僵尸任务（运行中但超过10小时未完成的任务）

    注意：全量历史同步任务（_full_history）可能运行数小时，因此阈值设为 600 分钟（10小时），
    避免误杀正在运行的长任务。

    Returns:
        清理结果
    """
    try:
        service = CeleryTaskHistoryService()

        # 查找僵尸任务（10小时阈值，避免误杀全量历史同步等长任务）
        stale_tasks = await service.get_stale_tasks(
            user_id=current_user.id,
            minutes=600
        )

        if not stale_tasks:
            return ApiResponse.success(
                data={'deleted_count': 0},
                message="没有发现僵尸任务"
            )

        # 清理僵尸任务
        deleted_count = await service.cleanup_stale_tasks(
            user_id=current_user.id,
            minutes=600
        )

        logger.info(f"清理了 {deleted_count} 个僵尸任务 (user_id={current_user.id})")

        return ApiResponse.success(
            data={'deleted_count': deleted_count},
            message=f"已清理 {deleted_count} 个僵尸任务"
        )

    except Exception as e:
        logger.error(f"清理僵尸任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 统计信息 ====================

@router.get("/task-history/statistics/summary")
async def get_task_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取任务统计信息

    Args:
        start_date: 开始日期，格式：YYYY-MM-DD（可选）
        end_date: 结束日期，格式：YYYY-MM-DD（可选）

    Returns:
        统计信息
    """
    try:
        service = CeleryTaskHistoryService()

        stats = await service.get_statistics(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date
        )

        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
