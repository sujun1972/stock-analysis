"""
用户管理API端点（仅管理员可访问）
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.database import get_db
from app.core.security import hash_password
from app.core.dependencies import require_admin, require_super_admin
from app.models.user import User, UserQuota, LoginHistory, UserActivityLog
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserWithQuota,
    UserListResponse,
    UserQuotaUpdate,
    LoginHistoryResponse,
    ActivityLogResponse
)
from app.schemas.auth import MessageResponse

router = APIRouter(prefix="/users", tags=["用户管理（Admin）"])


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    role: Optional[str] = Query(None, description="角色筛选"),
    search: Optional[str] = Query(None, description="搜索用户名或邮箱"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取用户列表（分页）

    - **page**: 页码（从1开始）
    - **page_size**: 每页数量（1-100）
    - **role**: 角色筛选（可选）
    - **search**: 搜索用户名或邮箱（可选）
    - **is_active**: 是否激活（可选）

    需要管理员权限
    """
    # 构建查询
    query = db.query(User)

    # 角色筛选
    if role:
        query = query.filter(User.role == role)

    # 搜索
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                User.username.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.full_name.ilike(search_pattern)
            )
        )

    # 激活状态筛选
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # 总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    # 加载配额信息
    users_with_quota = []
    for user in users:
        user_dict = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
            "is_email_verified": user.is_email_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_login_at": user.last_login_at,
            "login_count": user.login_count,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
            "phone": user.phone,
            "quota": user.quota
        }
        users_with_quota.append(user_dict)

    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        users=users_with_quota
    )


@router.post("", response_model=UserWithQuota, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    创建用户

    - 普通管理员只能创建普通用户（vip_user, normal_user, trial_user）
    - 超级管理员可以创建任何角色的用户

    需要管理员权限
    """
    # 权限检查：普通管理员不能创建管理员
    if current_user.role == "admin" and user_data.role in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="普通管理员无法创建管理员账户"
        )

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
        phone=user_data.phone,
        role=user_data.role,
        is_active=True,
        is_email_verified=False
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.get("/{user_id}", response_model=UserWithQuota)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取用户详情

    - **user_id**: 用户ID

    需要管理员权限
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    return user


@router.patch("/{user_id}", response_model=UserWithQuota)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    更新用户信息

    - 普通管理员不能修改管理员账户
    - 超级管理员可以修改任何用户

    需要管理员权限
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 权限检查：普通管理员不能修改管理员
    if current_user.role == "admin" and user.role in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="普通管理员无法修改管理员账户"
        )

    # 权限检查：普通管理员不能将用户提升为管理员
    if current_user.role == "admin" and user_data.role in ["super_admin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="普通管理员无法将用户提升为管理员"
        )

    # 更新字段
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return user


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    删除用户（仅超级管理员）

    - **user_id**: 用户ID

    需要超级管理员权限
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 不能删除自己
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己的账户"
        )

    db.delete(user)
    db.commit()

    return MessageResponse(message=f"用户 {user.username} 已被删除")


@router.post("/{user_id}/reset-quota", response_model=MessageResponse)
async def reset_user_quota(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    重置用户配额

    - **user_id**: 用户ID

    需要管理员权限
    """
    quota = db.query(UserQuota).filter(UserQuota.user_id == user_id).first()
    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户配额不存在"
        )

    # 重置配额
    quota.backtest_quota_used = 0
    quota.ml_prediction_quota_used = 0
    db.commit()

    return MessageResponse(message="用户配额已重置")


@router.patch("/{user_id}/quota", response_model=UserWithQuota)
async def update_user_quota(
    user_id: int,
    quota_data: UserQuotaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    更新用户配额总量

    - **user_id**: 用户ID

    需要管理员权限
    """
    quota = db.query(UserQuota).filter(UserQuota.user_id == user_id).first()
    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户配额不存在"
        )

    # 更新字段
    update_data = quota_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(quota, field, value)

    db.commit()

    # 返回用户信息（包含更新后的配额）
    user = db.query(User).filter(User.id == user_id).first()
    return user


@router.get("/{user_id}/login-history", response_model=List[LoginHistoryResponse])
async def get_user_login_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取用户登录历史

    - **user_id**: 用户ID
    - **limit**: 返回记录数（1-200）

    需要管理员权限
    """
    # 检查用户是否存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 查询登录历史
    history = db.query(LoginHistory).filter(
        LoginHistory.user_id == user_id
    ).order_by(
        LoginHistory.login_at.desc()
    ).limit(limit).all()

    return history


@router.get("/{user_id}/activity-logs", response_model=List[ActivityLogResponse])
async def get_user_activity_logs(
    user_id: int,
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    action_type: Optional[str] = Query(None, description="操作类型筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    获取用户操作日志

    - **user_id**: 用户ID
    - **limit**: 返回记录数（1-200）
    - **action_type**: 操作类型筛选（可选）

    需要管理员权限
    """
    # 检查用户是否存在
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 构建查询
    query = db.query(UserActivityLog).filter(UserActivityLog.user_id == user_id)

    # 操作类型筛选
    if action_type:
        query = query.filter(UserActivityLog.action_type == action_type)

    # 查询日志
    logs = query.order_by(UserActivityLog.created_at.desc()).limit(limit).all()

    return logs
