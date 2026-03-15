"""
用户通知配置和站内消息 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, TIMESTAMP, Date, Time, ForeignKey, JSON
from sqlalchemy.sql import func
from app.models.user import Base  # 使用统一的 Base


class UserNotificationSetting(Base):
    """用户通知配置表"""
    __tablename__ = "user_notification_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # 通知渠道
    email_enabled = Column(Boolean, default=False, nullable=False)
    telegram_enabled = Column(Boolean, default=False, nullable=False)
    in_app_enabled = Column(Boolean, default=True, nullable=False)

    # 联系方式
    email_address = Column(String(255))
    telegram_chat_id = Column(String(100))
    telegram_username = Column(String(100))

    # 订阅偏好
    subscribe_sentiment_report = Column(Boolean, default=False, nullable=False)
    subscribe_premarket_report = Column(Boolean, default=False, nullable=False)
    subscribe_backtest_report = Column(Boolean, default=True, nullable=False)
    subscribe_strategy_alert = Column(Boolean, default=True, nullable=False)

    # 发送时间偏好
    sentiment_report_time = Column(Time, default="18:30", nullable=False)
    premarket_report_time = Column(Time, default="08:00", nullable=False)

    # 内容格式
    report_format = Column(String(20), default="full", nullable=False)

    # 频率控制
    max_daily_notifications = Column(Integer, default=10, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<UserNotificationSetting(id={self.id}, user_id={self.user_id})>"


class NotificationLog(Base):
    """通知发送记录表（时序分区表）"""
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 通知内容
    notification_type = Column(String(50), nullable=False, index=True)
    content_type = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    # 发送渠道
    channel = Column(String(20), nullable=False)

    # 发送状态
    status = Column(String(20), default="pending", nullable=False, index=True)
    sent_at = Column(TIMESTAMP(timezone=True))
    failed_reason = Column(Text)
    retry_count = Column(Integer, default=0, nullable=False)

    # 关联数据
    business_date = Column(Date, index=True)
    reference_id = Column(String(100))

    # Celery 任务ID
    task_id = Column(String(100))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<NotificationLog(id={self.id}, user_id={self.user_id}, type={self.notification_type}, status={self.status})>"


class InAppNotification(Base):
    """站内消息表（时序分区表）"""
    __tablename__ = "in_app_notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 消息内容
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)

    # 状态
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(TIMESTAMP(timezone=True))

    # 优先级
    priority = Column(String(20), default="normal", nullable=False)

    # 关联数据
    business_date = Column(Date)
    reference_id = Column(String(100))
    extra_data = Column("metadata", JSON)  # Map to 'metadata' column in database

    # 过期时间
    expires_at = Column(TIMESTAMP(timezone=True))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<InAppNotification(id={self.id}, user_id={self.user_id}, title={self.title}, is_read={self.is_read})>"
