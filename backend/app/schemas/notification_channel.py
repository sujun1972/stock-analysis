"""
通知渠道配置 Schema 定义

用于管理员在 Admin 后台配置通知渠道（SMTP、Telegram Bot 等）
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, Literal
from datetime import datetime


# ==================== 配置子类型 ====================

class EmailConfig(BaseModel):
    """Email 渠道配置"""
    smtp_host: str = Field(..., description="SMTP 服务器地址")
    smtp_port: int = Field(..., ge=1, le=65535, description="SMTP 端口")
    smtp_username: str = Field(..., description="SMTP 用户名")
    smtp_password: str = Field("", description="SMTP 密码（留空表示不修改）")
    smtp_use_tls: bool = Field(True, description="是否使用 TLS 加密")
    from_email: EmailStr = Field(..., description="发件人邮箱")
    from_name: str = Field(..., description="发件人名称")


class TelegramConfig(BaseModel):
    """Telegram 渠道配置"""
    bot_token: str = Field("", description="Bot Token（留空表示不修改）")
    parse_mode: Literal["Markdown", "HTML"] = Field("Markdown", description="消息格式")
    timeout: int = Field(30, ge=5, le=120, description="请求超时时间（秒）")


# ==================== 请求 Schema ====================

class NotificationChannelConfigUpdate(BaseModel):
    """更新通知渠道配置请求"""
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    config: Optional[Dict[str, Any]] = Field(None, description="配置参数")
    description: Optional[str] = Field(None, description="描述信息")

    class Config:
        json_schema_extra = {
            "example": {
                "is_enabled": True,
                "config": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "smtp_username": "noreply@example.com",
                    "smtp_password": "",
                    "smtp_use_tls": True,
                    "from_email": "noreply@example.com",
                    "from_name": "股票分析系统"
                },
                "description": "Gmail SMTP 邮件服务"
            }
        }


class TestChannelRequest(BaseModel):
    """测试通知渠道请求"""
    test_target: str = Field(..., description="测试目标（邮箱地址或 Telegram Chat ID）")

    class Config:
        json_schema_extra = {
            "example": {
                "test_target": "test@example.com"
            }
        }


# ==================== 响应 Schema ====================

class NotificationChannelConfigResponse(BaseModel):
    """通知渠道配置响应"""
    id: int
    channel_type: str = Field(..., description="渠道类型")
    channel_name: str = Field(..., description="渠道名称")
    is_enabled: bool = Field(..., description="是否启用")
    is_default: bool = Field(..., description="是否为默认渠道")
    priority: int = Field(..., description="优先级")
    config: Dict[str, Any] = Field(..., description="配置参数（敏感信息已脱敏）")
    description: Optional[str] = Field(None, description="描述信息")
    last_test_at: Optional[datetime] = Field(None, description="最后测试时间")
    last_test_status: Optional[str] = Field(None, description="最后测试状态")
    last_test_message: Optional[str] = Field(None, description="最后测试消息")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "channel_type": "email",
                "channel_name": "邮件通知",
                "is_enabled": True,
                "is_default": True,
                "priority": 1,
                "config": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "smtp_username": "noreply@example.com",
                    "smtp_password": "****",  # 脱敏
                    "smtp_use_tls": True,
                    "from_email": "noreply@example.com",
                    "from_name": "股票分析系统"
                },
                "description": "Gmail SMTP 邮件服务",
                "last_test_at": "2026-03-15T10:30:00Z",
                "last_test_status": "success",
                "last_test_message": "测试邮件发送成功",
                "created_at": "2026-03-15T10:00:00Z",
                "updated_at": "2026-03-15T10:30:00Z"
            }
        }


class TestChannelResponse(BaseModel):
    """测试通知渠道响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="测试结果消息")
    test_time: datetime = Field(..., description="测试时间")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "测试邮件已成功发送到 test@example.com",
                "test_time": "2026-03-15T10:30:00Z"
            }
        }
