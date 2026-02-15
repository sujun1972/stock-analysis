"""
FastAPI依赖注入
提供认证、权限检查等依赖
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.core.database import get_db
from app.models.user import User, UserQuota, RefreshToken
from app.schemas.auth import TokenPayload

# HTTP Bearer认证方案
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前登录用户

    Args:
        credentials: HTTP认证凭证
        db: 数据库会话

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 认证失败时抛出401错误
    """
    token = credentials.credentials

    # 验证Token
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 获取用户ID（JWT规范要求sub为字符串，需转换为整数）
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的Token载荷",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户ID格式",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 从数据库查询用户
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户（必须is_active=True）

    Args:
        current_user: 当前用户

    Returns:
        User: 当前活跃用户

    Raises:
        HTTPException: 用户未激活时抛出403错误
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被禁用"
        )
    return current_user


async def require_role(
    required_roles: list[str],
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    要求用户具有特定角色

    Args:
        required_roles: 允许的角色列表
        current_user: 当前用户

    Returns:
        User: 当前用户

    Raises:
        HTTPException: 权限不足时抛出403错误
    """
    if current_user.role not in required_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"权限不足，需要以下角色之一: {', '.join(required_roles)}"
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    要求管理员权限（super_admin 或 admin）

    Args:
        current_user: 当前用户

    Returns:
        User: 当前用户（管理员）

    Raises:
        HTTPException: 权限不足时抛出403错误
    """
    if current_user.role not in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


async def require_super_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    要求超级管理员权限

    Args:
        current_user: 当前用户

    Returns:
        User: 当前用户（超级管理员）

    Raises:
        HTTPException: 权限不足时抛出403错误
    """
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级管理员权限"
        )
    return current_user


async def check_quota(
    quota_type: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> User:
    """
    检查用户配额

    Args:
        quota_type: 配额类型（"backtest" 或 "ml_prediction"）
        current_user: 当前用户
        db: 数据库会话

    Returns:
        User: 当前用户

    Raises:
        HTTPException: 配额不足时抛出429错误
    """
    # 管理员和VIP用户无限制
    if current_user.role in ["super_admin", "admin", "vip_user"]:
        return current_user

    # 查询用户配额
    quota = db.query(UserQuota).filter(UserQuota.user_id == current_user.id).first()
    if quota is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="用户配额记录不存在"
        )

    # 检查是否需要重置配额（由数据库函数处理）
    db.execute("SELECT reset_quota_if_needed(:user_id)", {"user_id": current_user.id})
    db.refresh(quota)

    # 检查配额余量
    if quota_type == "backtest":
        remaining = quota.backtest_quota_total - quota.backtest_quota_used
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"回测配额已用尽，下次重置时间: {quota.backtest_quota_reset_at}"
            )
    elif quota_type == "ml_prediction":
        remaining = quota.ml_prediction_quota_total - quota.ml_prediction_quota_used
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"ML预测配额已用尽，下次重置时间: {quota.ml_prediction_quota_reset_at}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"未知的配额类型: {quota_type}"
        )

    return current_user


async def increment_quota_usage(
    quota_type: str,
    user_id: int,
    db: Session
) -> bool:
    """
    增加配额使用次数

    Args:
        quota_type: 配额类型
        user_id: 用户ID
        db: 数据库会话

    Returns:
        bool: 是否增加成功
    """
    result = db.execute(
        "SELECT increment_quota_usage(:user_id, :quota_type)",
        {"user_id": user_id, "quota_type": quota_type}
    )
    return result.scalar()


# Optional: 获取客户端IP地址
async def get_client_ip(x_forwarded_for: Optional[str] = Header(None)) -> Optional[str]:
    """
    获取客户端IP地址

    Args:
        x_forwarded_for: X-Forwarded-For请求头

    Returns:
        str | None: 客户端IP地址
    """
    if x_forwarded_for:
        # 取第一个IP（真实客户端IP）
        return x_forwarded_for.split(",")[0].strip()
    return None
