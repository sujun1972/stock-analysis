"""
个人资料API端点（所有登录用户可访问）
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, hash_password
from app.core.dependencies import get_current_active_user
from app.models.user import User, UserQuota, UserActivityLog, LoginHistory
from app.schemas.user import (
    UserWithQuota,
    UserUpdate,
    PasswordChange,
    UserQuotaResponse,
    ActivityLogResponse,
    LoginHistoryResponse
)
from app.schemas.auth import MessageResponse

router = APIRouter(prefix="/profile", tags=["个人资料"])


@router.get("", response_model=UserWithQuota)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user)
):
    """
    获取我的个人资料

    返回当前登录用户的完整信息（包含配额）
    """
    return current_user


@router.patch("", response_model=UserWithQuota)
async def update_my_profile(
    profile_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    更新我的个人资料

    - 可以更新：username, full_name, phone, avatar_url
    - 不能更新：role, is_active（需要管理员权限）
    """
    # 不允许普通用户修改的字段
    restricted_fields = {"role", "is_active", "email"}
    update_data = profile_data.model_dump(exclude_unset=True)

    # 检查是否尝试修改受限字段
    for field in restricted_fields:
        if field in update_data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"不允许修改字段: {field}"
            )

    # 如果修改用户名，检查是否重复
    if "username" in update_data and update_data["username"] != current_user.username:
        existing = db.query(User).filter(
            User.username == update_data["username"],
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该用户名已被使用"
            )

    # 更新字段
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    修改密码

    - **old_password**: 旧密码
    - **new_password**: 新密码（至少6个字符）
    """
    # 验证旧密码
    if not verify_password(password_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )

    # 更新密码
    current_user.password_hash = hash_password(password_data.new_password)
    db.commit()

    return MessageResponse(message="密码修改成功")


@router.get("/quota", response_model=UserQuotaResponse)
async def get_my_quota(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    查看我的配额

    返回当前用户的配额信息（包含剩余配额计算）
    """
    # 先重置过期的配额
    db.execute("SELECT reset_quota_if_needed(:user_id)", {"user_id": current_user.id})
    db.commit()

    # 查询配额
    quota = db.query(UserQuota).filter(UserQuota.user_id == current_user.id).first()
    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配额记录不存在"
        )

    return quota


@router.get("/activity", response_model=List[ActivityLogResponse])
async def get_my_activity(
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    action_type: str = Query(None, description="操作类型筛选"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    查看我的操作记录

    - **limit**: 返回记录数（1-200）
    - **action_type**: 操作类型筛选（可选）
    """
    # 构建查询
    query = db.query(UserActivityLog).filter(UserActivityLog.user_id == current_user.id)

    # 操作类型筛选
    if action_type:
        query = query.filter(UserActivityLog.action_type == action_type)

    # 查询日志
    logs = query.order_by(UserActivityLog.created_at.desc()).limit(limit).all()

    return logs


@router.get("/login-history", response_model=List[LoginHistoryResponse])
async def get_my_login_history(
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    查看我的登录历史

    - **limit**: 返回记录数（1-100）
    """
    # 查询登录历史
    history = db.query(LoginHistory).filter(
        LoginHistory.user_id == current_user.id
    ).order_by(
        LoginHistory.login_at.desc()
    ).limit(limit).all()

    return history
