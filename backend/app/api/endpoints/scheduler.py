"""
定时任务管理 API
管理数据同步的定时任务配置和执行历史
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger
from pydantic import BaseModel, field_validator

from app.api.error_handler import handle_api_errors
from app.core.exceptions import DatabaseError, QueryError, ValidationError
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.api_response import ApiResponse
from app.services.scheduler import ScheduledTaskService

router = APIRouter()


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
        service = ScheduledTaskService()
        if not service.validate_cron_expression(v):
            raise ValueError('无效的Cron表达式，格式应为: "分 时 日 月 周"')
        return v


class ScheduledTaskUpdate(BaseModel):
    """更新定时任务请求"""

    description: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    params: Optional[Dict[str, Any]] = None
    display_name: Optional[str] = None
    category: Optional[str] = None
    display_order: Optional[int] = None
    points_consumption: Optional[int] = None

    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """验证Cron表达式格式"""
        if v is not None:
            service = ScheduledTaskService()
            if not service.validate_cron_expression(v):
                raise ValueError('无效的Cron表达式，格式应为: "分 时 日 月 周"')
        return v

    @field_validator('display_order')
    @classmethod
    def validate_display_order(cls, v: Optional[int]) -> Optional[int]:
        """验证显示顺序"""
        if v is not None and v < 0:
            raise ValueError('显示顺序必须大于等于0')
        return v

    @field_validator('points_consumption')
    @classmethod
    def validate_points(cls, v: Optional[int]) -> Optional[int]:
        """
        验证积分消耗字段

        Args:
            v: 积分消耗值，可为 None（表示不消耗或未知）

        Returns:
            验证后的积分值

        Raises:
            ValueError: 如果积分值为负数
        """
        if v is not None and v < 0:
            raise ValueError('积分消耗必须大于等于0')
        return v


# ==========================================
# API 端点
# ==========================================

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
        service = ScheduledTaskService()
        tasks = await service.get_all_tasks()
        return ApiResponse.success(data=tasks)

    except Exception as e:
        logger.error(f"获取定时任务列表失败: {e}")
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
        service = ScheduledTaskService()
        task = await service.get_task_by_id(task_id)
        return ApiResponse.success(data=task)

    except QueryError as e:
        logger.error(f"获取定时任务详情失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
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
        service = ScheduledTaskService()
        task = await service.create_task(
            task_name=request.task_name,
            module=request.module,
            description=request.description,
            cron_expression=request.cron_expression,
            enabled=request.enabled,
            params=request.params
        )
        return ApiResponse.success(data={"id": task['id']}, message="创建成功")

    except ValidationError as e:
        logger.error(f"创建定时任务失败（验证错误）: {e}")
        raise HTTPException(status_code=400, detail=str(e))
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
        service = ScheduledTaskService()
        task = await service.update_task(
            task_id=task_id,
            description=request.description,
            cron_expression=request.cron_expression,
            enabled=request.enabled,
            params=request.params,
            display_name=request.display_name,
            category=request.category,
            display_order=request.display_order,
            points_consumption=request.points_consumption
        )
        return ApiResponse.success(data={"id": task['id']}, message="更新成功")

    except ValidationError as e:
        logger.error(f"更新定时任务失败（验证错误）: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except QueryError as e:
        logger.error(f"更新定时任务失败（任务不存在）: {e}")
        raise HTTPException(status_code=404, detail=str(e))
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
        service = ScheduledTaskService()
        await service.delete_task(task_id)
        return ApiResponse.success(data={"id": task_id}, message="删除成功")

    except QueryError as e:
        logger.error(f"删除定时任务失败（任务不存在）: {e}")
        raise HTTPException(status_code=404, detail=str(e))
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
        service = ScheduledTaskService()
        task = await service.toggle_task(task_id)
        return ApiResponse.success(
            data={"enabled": task['enabled']},
            message="状态切换成功"
        )

    except QueryError as e:
        logger.error(f"切换定时任务状态失败（任务不存在）: {e}")
        raise HTTPException(status_code=404, detail=str(e))
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
        service = ScheduledTaskService()
        history = await service.get_task_execution_history(task_id, limit)
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
        service = ScheduledTaskService()
        history = await service.get_recent_execution_history(limit)
        return ApiResponse.success(data=history)

    except Exception as e:
        logger.error(f"获取最近执行历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/execute")
@handle_api_errors
async def execute_scheduled_task(
    task_id: int,
    current_user: User = Depends(require_admin)
):
    """
    立即执行定时任务

    Args:
        task_id: 任务ID

    Returns:
        执行结果，包含Celery任务ID
    """
    try:
        service = ScheduledTaskService()
        result = await service.execute_task_async(task_id, current_user.id)
        return ApiResponse.success(data=result, message="任务已提交执行")

    except QueryError as e:
        logger.error(f"执行定时任务失败（任务不存在）: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"执行定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/status")
@handle_api_errors
async def get_task_execution_status(
    task_id: int,
    celery_task_id: Optional[str] = None,
    current_user: User = Depends(require_admin)
):
    """
    获取任务执行状态

    Args:
        task_id: 数据库任务ID
        celery_task_id: Celery任务ID

    Returns:
        任务执行状态
    """
    try:
        service = ScheduledTaskService()
        status = await service.get_task_execution_status(task_id, celery_task_id)
        return ApiResponse.success(data=status)

    except Exception as e:
        logger.error(f"获取任务执行状态失败: {e}")
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
        service = ScheduledTaskService()
        result = await service.validate_and_get_next_run(cron_expression)

        if not result['valid']:
            return ApiResponse.error(
                data=result,
                message="无效的Cron表达式",
                code=400
            ).to_dict()

        return ApiResponse.success(
            data=result,
            message="Cron表达式验证成功"
        ).to_dict()

    except Exception as e:
        logger.error(f"验证Cron表达式失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
