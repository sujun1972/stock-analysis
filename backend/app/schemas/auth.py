"""
认证相关Pydantic Schema
"""

from typing import Optional, Literal
from pydantic import BaseModel, EmailStr, Field


# ============================================================
# 认证请求Schema
# ============================================================

class LoginRequest(BaseModel):
    """登录请求Schema"""
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """注册请求Schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)


class RefreshTokenRequest(BaseModel):
    """刷新Token请求Schema"""
    refresh_token: str


# ============================================================
# 认证响应Schema
# ============================================================

class TokenResponse(BaseModel):
    """Token响应Schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15分钟，单位：秒


class LoginResponse(BaseModel):
    """登录响应Schema"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    user: dict  # 用户基本信息


class RegisterResponse(BaseModel):
    """注册响应Schema"""
    message: str
    user_id: int
    email: str


# ============================================================
# Token载荷Schema
# ============================================================

class TokenPayload(BaseModel):
    """Token载荷Schema"""
    sub: int  # user_id
    email: str
    role: str
    exp: Optional[int] = None
    iat: Optional[int] = None
    type: Literal["access", "refresh"] = "access"


# ============================================================
# 密码重置Schema
# ============================================================

class ForgotPasswordRequest(BaseModel):
    """忘记密码请求Schema"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """重置密码请求Schema"""
    token: str
    new_password: str = Field(..., min_length=6, max_length=50)


class MessageResponse(BaseModel):
    """通用消息响应Schema"""
    message: str
