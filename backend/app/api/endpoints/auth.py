"""
认证相关API端点
包括登录、注册、Token刷新等
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    verify_password,
    hash_password,
    create_token_pair,
    verify_token
)
from app.core.dependencies import get_current_active_user, get_client_ip
from app.models.user import User, RefreshToken, LoginHistory
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    RefreshTokenRequest,
    TokenResponse,
    MessageResponse
)
from app.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册（仅普通用户，默认trial_user）

    - **email**: 邮箱地址（唯一）
    - **username**: 用户名（唯一，3-50字符）
    - **password**: 密码（6-50字符）
    - **full_name**: 可选，真实姓名
    """
    # 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )

    # 检查用户名是否已存在
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户名已被使用"
        )

    # 创建新用户
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=hash_password(user_data.password),
        full_name=user_data.full_name,
        role="trial_user",  # 默认试用用户
        is_active=True,
        is_email_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RegisterResponse(
        message="注册成功",
        user_id=new_user.id,
        email=new_user.email
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    client_ip: Optional[str] = Depends(get_client_ip)
):
    """
    用户登录

    - **email**: 邮箱地址
    - **password**: 密码

    返回access_token和refresh_token
    """
    # 查找用户
    user = db.query(User).filter(User.email == login_data.email).first()

    # 创建登录历史记录的辅助函数
    def record_login(successful: bool, failure_reason: Optional[str] = None):
        login_history = LoginHistory(
            user_id=user.id if user else None,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent"),
            login_successful=successful,
            failure_reason=failure_reason
        )
        db.add(login_history)
        db.commit()

    # 验证用户存在
    if not user:
        record_login(False, "用户不存在")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    # 验证密码
    if not verify_password(login_data.password, user.password_hash):
        record_login(False, "密码错误")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    # 检查用户是否被禁用
    if not user.is_active:
        record_login(False, "账户已被禁用")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用，请联系管理员"
        )

    # 生成Token对
    token_data = {
        "sub": str(user.id),  # JWT规范要求sub必须是字符串
        "email": user.email,
        "role": user.role
    }
    tokens = create_token_pair(token_data)

    # 保存refresh_token到数据库
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token=tokens["refresh_token"],
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        is_revoked=False
    )
    db.add(refresh_token_obj)

    # 更新用户登录信息
    user.last_login_at = datetime.utcnow()
    user.login_count += 1

    # 记录成功登录
    record_login(True)

    db.commit()

    # 返回Token和用户信息
    return LoginResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url
        }
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    刷新访问令牌

    - **refresh_token**: 刷新令牌

    返回新的access_token和refresh_token
    """
    # 验证refresh_token
    payload = verify_token(refresh_data.refresh_token, token_type="refresh")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    # 检查token是否在数据库中且未被撤销
    token_obj = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_data.refresh_token,
        RefreshToken.is_revoked == False
    ).first()

    if not token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已失效"
        )

    # 检查token是否过期
    if token_obj.expires_at < datetime.utcnow():
        token_obj.is_revoked = True
        token_obj.revoked_at = datetime.utcnow()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已过期"
        )

    # 获取用户信息
    user = db.query(User).filter(User.id == token_obj.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用"
        )

    # 生成新的Token对
    token_data = {
        "sub": str(user.id),  # JWT规范要求sub必须是字符串
        "email": user.email,
        "role": user.role
    }
    new_tokens = create_token_pair(token_data)

    # 撤销旧的refresh_token
    token_obj.is_revoked = True
    token_obj.revoked_at = datetime.utcnow()

    # 保存新的refresh_token
    new_refresh_token = RefreshToken(
        user_id=user.id,
        token=new_tokens["refresh_token"],
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        is_revoked=False
    )
    db.add(new_refresh_token)
    db.commit()

    return TokenResponse(
        access_token=new_tokens["access_token"],
        refresh_token=new_tokens["refresh_token"],
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    refresh_data: RefreshTokenRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    用户登出（撤销refresh_token）

    - **refresh_token**: 要撤销的刷新令牌
    """
    # 查找并撤销refresh_token
    token_obj = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_data.refresh_token,
        RefreshToken.user_id == current_user.id,
        RefreshToken.is_revoked == False
    ).first()

    if token_obj:
        token_obj.is_revoked = True
        token_obj.revoked_at = datetime.utcnow()
        db.commit()

    return MessageResponse(message="登出成功")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前登录用户信息

    需要在Header中提供有效的access_token
    """
    return current_user


@router.post("/verify-email/{token}", response_model=MessageResponse)
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    验证邮箱（预留接口，需要邮件服务支持）

    - **token**: 邮箱验证令牌
    """
    # TODO: 实现邮箱验证逻辑
    # 1. 解析token获取user_id
    # 2. 更新user.is_email_verified = True
    return MessageResponse(message="邮箱验证功能尚未实现")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(email: str, db: Session = Depends(get_db)):
    """
    忘记密码（预留接口，需要邮件服务支持）

    - **email**: 邮箱地址
    """
    # TODO: 实现忘记密码逻辑
    # 1. 查找用户
    # 2. 生成重置密码token
    # 3. 发送邮件
    return MessageResponse(message="密码重置功能尚未实现，请联系管理员")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    token: str,
    new_password: str,
    db: Session = Depends(get_db)
):
    """
    重置密码（预留接口，需要邮件服务支持）

    - **token**: 重置密码令牌
    - **new_password**: 新密码
    """
    # TODO: 实现重置密码逻辑
    # 1. 验证token
    # 2. 更新密码
    return MessageResponse(message="密码重置功能尚未实现")
