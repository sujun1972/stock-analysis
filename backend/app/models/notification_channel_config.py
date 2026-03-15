"""
通知渠道配置 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, TIMESTAMP, JSON
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NotificationChannelConfig(Base):
    """通知渠道配置表"""
    __tablename__ = "notification_channel_configs"

    id = Column(Integer, primary_key=True, index=True)
    channel_type = Column(String(20), unique=True, nullable=False, index=True)
    channel_name = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=False, nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False)
    priority = Column(Integer, default=10, nullable=False)
    config = Column(JSON, nullable=False, default={})
    description = Column(Text)
    last_test_at = Column(TIMESTAMP(timezone=True))
    last_test_status = Column(String(20))
    last_test_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<NotificationChannelConfig(id={self.id}, type={self.channel_type}, enabled={self.is_enabled})>"
