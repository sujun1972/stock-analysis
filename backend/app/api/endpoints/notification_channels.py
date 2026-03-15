"""
通知渠道配置 API 端点（Admin 后台）

管理员管理通知渠道配置（SMTP、Telegram Bot 等）
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import require_super_admin
from app.schemas.notification_channel import (
    NotificationChannelConfigResponse,
    NotificationChannelConfigUpdate,
    TestChannelRequest,
    TestChannelResponse
)
from app.services.notification_channel_service import NotificationChannelService
from app.models.api_response import ApiResponse

router = APIRouter()


@router.get("", response_model=ApiResponse[List[NotificationChannelConfigResponse]])
def get_all_notification_channels(
    db: Session = Depends(get_db),
    current_admin = Depends(require_super_admin)
):
    """获取所有通知渠道配置（仅超级管理员）"""
    try:
        service = NotificationChannelService(db)
        channels = service.get_all_channels()

        return ApiResponse(
            success=True,
            data=channels,
            message="获取成功"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{channel_type}", response_model=ApiResponse[NotificationChannelConfigResponse])
def get_notification_channel(
    channel_type: str,
    db: Session = Depends(get_db),
    current_admin = Depends(require_super_admin)
):
    """获取指定渠道配置"""
    try:
        service = NotificationChannelService(db)
        channel = service.get_channel_by_type(channel_type)

        if not channel:
            raise HTTPException(status_code=404, detail="渠道不存在")

        return ApiResponse(
            success=True,
            data=channel,
            message="获取成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{channel_type}", response_model=ApiResponse[NotificationChannelConfigResponse])
def update_notification_channel(
    channel_type: str,
    data: NotificationChannelConfigUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(require_super_admin)
):
    """更新渠道配置（敏感信息加密存储）"""
    try:
        service = NotificationChannelService(db)

        # 转换为字典（排除 None 值）
        update_dict = data.model_dump(exclude_none=True)

        channel = service.update_channel(channel_type, update_dict)

        return ApiResponse(
            success=True,
            data=channel,
            message="配置已更新"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{channel_type}/toggle", response_model=ApiResponse[NotificationChannelConfigResponse])
def toggle_notification_channel(
    channel_type: str,
    db: Session = Depends(get_db),
    current_admin = Depends(require_super_admin)
):
    """启用/禁用渠道"""
    try:
        service = NotificationChannelService(db)
        channel = service.toggle_channel(channel_type)

        status_text = "已启用" if channel.is_enabled else "已禁用"

        return ApiResponse(
            success=True,
            data=channel,
            message=f"渠道{status_text}"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{channel_type}/test", response_model=ApiResponse[TestChannelResponse])
async def test_notification_channel(
    channel_type: str,
    request: TestChannelRequest,
    db: Session = Depends(get_db),
    current_admin = Depends(require_super_admin)
):
    """测试渠道连接（发送测试消息）"""
    try:
        service = NotificationChannelService(db)
        result = await service.test_channel(channel_type, request.test_target)

        if result['success']:
            return ApiResponse(
                success=True,
                data=result,
                message="测试成功"
            )
        else:
            return ApiResponse(
                success=False,
                data=result,
                message=result['message']
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
