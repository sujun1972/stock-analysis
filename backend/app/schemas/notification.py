"""
用户通知配置和站内消息 Schema 定义

用于用户前端配置订阅偏好和查看站内消息
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, time, date


# ==================== 请求 Schema ====================

class NotificationSettingsUpdate(BaseModel):
    """更新用户通知配置请求"""
    # 通知渠道
    email_enabled: Optional[bool] = Field(None, description="是否启用邮件通知")
    telegram_enabled: Optional[bool] = Field(None, description="是否启用 Telegram 通知")
    in_app_enabled: Optional[bool] = Field(None, description="是否启用站内消息")

    # 联系方式
    email_address: Optional[EmailStr] = Field(None, description="邮箱地址")
    telegram_chat_id: Optional[str] = Field(None, description="Telegram Chat ID")
    telegram_username: Optional[str] = Field(None, description="Telegram 用户名")

    # 订阅偏好
    subscribe_sentiment_report: Optional[bool] = Field(None, description="订阅盘后情绪报告")
    subscribe_premarket_report: Optional[bool] = Field(None, description="订阅盘前碰撞报告")
    subscribe_backtest_report: Optional[bool] = Field(None, description="订阅回测完成通知")
    subscribe_strategy_alert: Optional[bool] = Field(None, description="订阅策略审核通知")

    # 发送时间偏好
    sentiment_report_time: Optional[time] = Field(None, description="盘后报告发送时间")
    premarket_report_time: Optional[time] = Field(None, description="盘前报告发送时间")

    # 内容格式
    report_format: Optional[Literal["full", "summary", "action_only"]] = Field(
        None,
        description="报告内容格式：full=完整报告, summary=摘要, action_only=仅行动指令"
    )

    # 频率控制
    max_daily_notifications: Optional[int] = Field(None, ge=1, le=50, description="每日最大通知数")

    class Config:
        json_schema_extra = {
            "example": {
                "email_enabled": True,
                "email_address": "user@example.com",
                "subscribe_sentiment_report": True,
                "subscribe_premarket_report": True,
                "report_format": "summary"
            }
        }


# ==================== 响应 Schema ====================

class NotificationSettingsResponse(BaseModel):
    """用户通知配置响应"""
    id: int
    user_id: int

    # 通知渠道
    email_enabled: bool
    telegram_enabled: bool
    in_app_enabled: bool

    # 联系方式
    email_address: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_username: Optional[str] = None

    # 订阅偏好
    subscribe_sentiment_report: bool
    subscribe_premarket_report: bool
    subscribe_backtest_report: bool
    subscribe_strategy_alert: bool

    # 发送时间偏好
    sentiment_report_time: time
    premarket_report_time: time

    # 内容格式
    report_format: str

    # 频率控制
    max_daily_notifications: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InAppNotificationResponse(BaseModel):
    """站内消息响应"""
    id: int
    user_id: int
    title: str
    content: str
    notification_type: str
    is_read: bool
    read_at: Optional[datetime] = None
    priority: str
    business_date: Optional[date] = None
    reference_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 123,
                "title": "盘后情绪分析报告",
                "content": "【开盘预期】高开, 信心85%...",
                "notification_type": "sentiment_report",
                "is_read": False,
                "read_at": None,
                "priority": "normal",
                "business_date": "2026-03-15",
                "reference_id": None,
                "metadata": None,
                "expires_at": None,
                "created_at": "2026-03-15T18:30:00Z"
            }
        }


class NotificationLogResponse(BaseModel):
    """通知发送记录响应"""
    id: int
    user_id: int
    notification_type: str
    content_type: str
    title: str
    channel: str
    status: str
    sent_at: Optional[datetime] = None
    failed_reason: Optional[str] = None
    retry_count: int
    business_date: Optional[date] = None
    reference_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "user_id": 123,
                "notification_type": "sentiment_report",
                "content_type": "summary",
                "title": "盘后情绪分析报告",
                "channel": "email",
                "status": "sent",
                "sent_at": "2026-03-15T18:31:00Z",
                "failed_reason": None,
                "retry_count": 0,
                "business_date": "2026-03-15",
                "reference_id": None,
                "created_at": "2026-03-15T18:30:00Z"
            }
        }


class UnreadCountResponse(BaseModel):
    """未读消息数量响应"""
    unread_count: int = Field(..., description="未读消息数量")

    class Config:
        json_schema_extra = {
            "example": {
                "unread_count": 5
            }
        }
