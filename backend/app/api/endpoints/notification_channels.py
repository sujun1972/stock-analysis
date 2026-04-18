"""
通知渠道配置 API 端点（Admin 后台）

管理员管理通知渠道配置（SMTP、Telegram Bot 等）
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.error_handler import handle_api_errors, handle_api_errors_sync
from app.core.database import get_db
from app.core.dependencies import require_super_admin
from app.schemas.notification_channel import (
    NotificationChannelConfigUpdate,
    TestChannelRequest,
)
from app.services.notification_channel_service import NotificationChannelService
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("")
@handle_api_errors_sync
def get_all_notification_channels(
    db: Session = Depends(get_db),
    current_admin = Depends(require_super_admin)
):
    """获取所有通知渠道配置（仅超级管理员）"""
    service = NotificationChannelService(db)
    channels = service.get_all_channels()

    return ApiResponse.success(
        data=channels,
        message="获取成功"
    ).to_dict()


@router.get("/{channel_type}")
@handle_api_errors_sync
def get_notification_channel(
    channel_type: str,
    db: Session = Depends(get_db),
    current_admin = Depends(require_super_admin)
):
    """获取指定渠道配置"""
    service = NotificationChannelService(db)
    channel = service.get_channel_by_type(channel_type)

    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")

    return ApiResponse.success(
        data=channel,
        message="获取成功"
    ).to_dict()


@router.put("/{channel_type}")
@handle_api_errors_sync
def update_notification_channel(
    channel_type: str,
    data: NotificationChannelConfigUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(require_super_admin)
):
    """更新渠道配置（敏感信息加密存储）"""
    service = NotificationChannelService(db)

    # 转换为字典（排除 None 值）
    update_dict = data.model_dump(exclude_none=True)

    try:
        channel = service.update_channel(channel_type, update_dict)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return ApiResponse.success(
        data=channel,
        message="配置已更新"
    ).to_dict()


@router.post("/{channel_type}/toggle")
@handle_api_errors_sync
def toggle_notification_channel(
    channel_type: str,
    db: Session = Depends(get_db),
    current_admin = Depends(require_super_admin)
):
    """启用/禁用渠道"""
    service = NotificationChannelService(db)

    try:
        channel = service.toggle_channel(channel_type)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    status_text = "已启用" if channel.is_enabled else "已禁用"

    return ApiResponse.success(
        data=channel,
        message=f"渠道{status_text}"
    ).to_dict()


@router.post("/{channel_type}/test")
@handle_api_errors
async def test_notification_channel(
    channel_type: str,
    request: TestChannelRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(require_super_admin)
):
    """测试渠道连接（发送测试消息）"""
    service = NotificationChannelService(db)
    result = await service.test_channel(channel_type, request.test_target)

    if result['success']:
        return ApiResponse.success(
            data=result,
            message="测试成功"
        ).to_dict()
    else:
        return ApiResponse.error(
            data=result,
            message=result['message'],
            code=400
        ).to_dict()
