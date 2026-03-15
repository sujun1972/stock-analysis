"""
用户通知配置和站内消息 API 端点

用户管理订阅偏好和查看站内消息
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.schemas.notification import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    InAppNotificationResponse,
    NotificationLogResponse,
    UnreadCountResponse
)
from app.services.notification_service import NotificationService
from app.models.api_response import ApiResponse

router = APIRouter()


# ==================== 用户通知配置 ====================

@router.get("/settings")
def get_notification_settings(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户通知配置"""
    try:
        service = NotificationService(db)
        settings = service.get_user_settings(current_user.id)

        if not settings:
            # 自动创建默认配置
            settings = service.update_user_settings(current_user.id, {})

        return ApiResponse.success(
            data=settings,
            message="获取成功"
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
def update_notification_settings(
    settings_data: NotificationSettingsUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新用户通知配置"""
    try:
        service = NotificationService(db)

        # 转换为字典（排除 None 值）
        update_dict = settings_data.model_dump(exclude_none=True)

        settings = service.update_user_settings(current_user.id, update_dict)

        return ApiResponse.success(
            data=settings,
            message="配置已更新"
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 站内消息 ====================

@router.get("/in-app")
def get_in_app_notifications(
    unread_only: bool = Query(False, description="仅未读消息"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取站内消息列表"""
    try:
        service = NotificationService(db)
        notifications = service.get_in_app_notifications(
            user_id=current_user.id,
            unread_only=unread_only,
            limit=limit,
            offset=offset
        )

        return ApiResponse.success(
            data=notifications,
            message="获取成功"
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/in-app/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """标记消息为已读"""
    try:
        service = NotificationService(db)
        service.mark_as_read(notification_id, current_user.id)

        return ApiResponse.success(
            data=None,
            message="已标记为已读"
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/in-app/read-all")
def mark_all_as_read(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """全部标记为已读"""
    try:
        service = NotificationService(db)
        count = service.mark_all_as_read(current_user.id)

        return ApiResponse.success(
            data={"count": count},
            message=f"已标记 {count} 条消息为已读"
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unread-count")
def get_unread_count(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取未读消息数量"""
    try:
        service = NotificationService(db)
        count = service.get_unread_count(current_user.id)

        return ApiResponse.success(
            data={"unread_count": count},
            message="获取成功"
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 通知发送历史 ====================

@router.get("/logs")
def get_notification_logs(
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取通知发送历史"""
    try:
        service = NotificationService(db)
        logs = service.get_notification_logs(current_user.id, limit, offset)

        return ApiResponse.success(
            data=logs,
            message="获取成功"
        ).to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
