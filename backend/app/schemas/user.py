"""
用户相关Pydantic Schema
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field, validator


# ============================================================
# 用户基础Schema
# ============================================================

class UserBase(BaseModel):
    """用户基础Schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserCreate(UserBase):
    """创建用户Schema"""
    password: str = Field(..., min_length=6, max_length=50)
    role: Literal["super_admin", "admin", "vip_user", "normal_user", "trial_user"] = "trial_user"

    @validator("password")
    def validate_password(cls, v):
        """验证密码强度"""
        if len(v) < 6:
            raise ValueError("密码长度至少为6个字符")
        return v


class UserUpdate(BaseModel):
    """更新用户Schema"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    avatar_url: Optional[str] = None
    role: Optional[Literal["super_admin", "admin", "vip_user", "normal_user", "trial_user"]] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """数据库中的用户Schema"""
    id: int
    role: str
    is_active: bool
    is_email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    login_count: int
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    """用户响应Schema（不包含密码）"""
    pass


class UserWithQuota(UserResponse):
    """用户响应Schema（包含配额信息）"""
    quota: Optional["UserQuotaResponse"] = None


# ============================================================
# 用户配额Schema
# ============================================================

class UserQuotaBase(BaseModel):
    """用户配额基础Schema"""
    backtest_quota_total: int
    backtest_quota_used: int
    ml_prediction_quota_total: int
    ml_prediction_quota_used: int
    max_strategies: int
    current_strategies: int


class UserQuotaResponse(UserQuotaBase):
    """用户配额响应Schema"""
    id: int
    user_id: int
    backtest_quota_reset_at: Optional[datetime]
    ml_prediction_quota_reset_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # 计算字段
    @property
    def backtest_quota_remaining(self) -> int:
        return max(0, self.backtest_quota_total - self.backtest_quota_used)

    @property
    def ml_quota_remaining(self) -> int:
        return max(0, self.ml_prediction_quota_total - self.ml_prediction_quota_used)

    @property
    def strategies_remaining(self) -> int:
        return max(0, self.max_strategies - self.current_strategies)

    class Config:
        from_attributes = True


class UserQuotaUpdate(BaseModel):
    """更新用户配额Schema"""
    backtest_quota_total: Optional[int] = None
    ml_prediction_quota_total: Optional[int] = None
    max_strategies: Optional[int] = None


# ============================================================
# 登录历史Schema
# ============================================================

class LoginHistoryResponse(BaseModel):
    """登录历史响应Schema"""
    id: int
    user_id: int
    login_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    login_successful: bool
    failure_reason: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================
# 操作日志Schema
# ============================================================

class ActivityLogResponse(BaseModel):
    """操作日志响应Schema"""
    id: int
    user_id: Optional[int] = None
    action_type: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityLogCreate(BaseModel):
    """创建操作日志Schema"""
    action_type: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    details: Optional[dict] = None


# ============================================================
# 用户列表Schema
# ============================================================

class UserListResponse(BaseModel):
    """用户列表响应Schema"""
    total: int
    page: int
    page_size: int
    users: list[UserWithQuota]


# ============================================================
# 密码相关Schema
# ============================================================

class PasswordChange(BaseModel):
    """修改密码Schema"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=50)

    @validator("new_password")
    def validate_password(cls, v, values):
        """验证新密码"""
        if len(v) < 6:
            raise ValueError("密码长度至少为6个字符")
        if "old_password" in values and v == values["old_password"]:
            raise ValueError("新密码不能与旧密码相同")
        return v


class PasswordReset(BaseModel):
    """重置密码Schema"""
    token: str
    new_password: str = Field(..., min_length=6, max_length=50)


# 更新 UserWithQuota 的前向引用
UserWithQuota.model_rebuild()
