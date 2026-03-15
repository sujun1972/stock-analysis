"""
通知频率限制记录 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, UniqueConstraint, Index, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NotificationRateLimit(Base):
    """通知频率限制记录表"""

    __tablename__ = "notification_rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_date = Column(Date, nullable=False, default=func.current_date())

    # 各渠道发送计数
    email_count = Column(Integer, default=0)
    telegram_count = Column(Integer, default=0)
    in_app_count = Column(Integer, default=0)
    total_count = Column(Integer, default=0)

    # 时间窗口统计（每小时）
    hourly_counts = Column(JSONB, default=dict, comment="每小时计数 {'00': 2, '01': 0, ...}")

    # 时间戳
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # 唯一约束
    __table_args__ = (
        UniqueConstraint('user_id', 'notification_date', name='uq_user_notification_date'),
        Index('idx_notification_rate_limits_user_date', 'user_id', 'notification_date'),
    )

    def __repr__(self):
        return f"<NotificationRateLimit(user_id={self.user_id}, date={self.notification_date}, total={self.total_count})>"
