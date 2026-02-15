"""
用户相关数据库模型
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, Text, CheckConstraint,
    ForeignKey, TIMESTAMP, func
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        String(20),
        nullable=False,
        index=True,
        default="trial_user"
    )
    is_active = Column(Boolean, default=True, index=True)
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    login_count = Column(Integer, default=0)

    # 用户资料
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)

    # 关系
    quota = relationship("UserQuota", back_populates="user", uselist=False, cascade="all, delete-orphan")
    login_histories = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("UserActivityLog", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(
            "role IN ('super_admin', 'admin', 'vip_user', 'normal_user', 'trial_user')",
            name="chk_role"
        ),
    )


class UserQuota(Base):
    """用户配额模型"""

    __tablename__ = "user_quotas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # 回测配额
    backtest_quota_total = Column(Integer, default=10)
    backtest_quota_used = Column(Integer, default=0)
    backtest_quota_reset_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # ML预测配额
    ml_prediction_quota_total = Column(Integer, default=5)
    ml_prediction_quota_used = Column(Integer, default=0)
    ml_prediction_quota_reset_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # 策略数量限制
    max_strategies = Column(Integer, default=3)
    current_strategies = Column(Integer, default=0)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    user = relationship("User", back_populates="quota")


class LoginHistory(Base):
    """登录历史模型"""

    __tablename__ = "login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    login_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    login_successful = Column(Boolean, default=True, index=True)
    failure_reason = Column(String(200), nullable=True)

    # 关系
    user = relationship("User", back_populates="login_histories")


class UserActivityLog(Base):
    """用户操作日志模型"""

    __tablename__ = "user_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True, index=True)
    resource_id = Column(Integer, nullable=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(INET, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), index=True)

    # 关系
    user = relationship("User", back_populates="activity_logs")


class RefreshToken(Base):
    """刷新令牌模型"""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_revoked = Column(Boolean, default=False, index=True)

    # 关系
    user = relationship("User", back_populates="refresh_tokens")
