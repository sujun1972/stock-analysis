"""
策略发布相关API端点（用户端）

提供策略发布申请、撤回等功能

作者: Backend Team
创建日期: 2026-03-02
版本: 1.0.0
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.repositories.strategy_repository import StrategyRepository
from app.repositories.publish_review_repository import PublishReviewRepository

router = APIRouter(tags=["strategies-publish"])


@router.post(
    "/{strategy_id}/request-publish",
    summary="申请发布策略",
    status_code=status.HTTP_200_OK
)
async def request_publish_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    用户申请发布策略

    权限要求：
    - 必须是策略的创建者
    - 策略当前状态必须是 draft 或 rejected

    状态变更：
    - draft/rejected -> pending_review
    """
    strategy_repo = StrategyRepository()
    review_repo = PublishReviewRepository()

    # 获取策略信息
    strategy = strategy_repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="策略不存在"
        )

    # 检查权限：必须是策略创建者
    if strategy.get('user_id') != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有策略创建者可以申请发布"
        )

    # 检查当前状态
    current_publish_status = strategy.get('publish_status', 'draft')
    if current_publish_status not in ['draft', 'rejected']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有草稿或被拒绝的策略可以申请发布，当前状态：{current_publish_status}"
        )

    # 检查验证状态：必须通过代码验证
    validation_status = strategy.get('validation_status')
    if validation_status != 'passed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="策略代码必须通过安全验证后才能申请发布"
        )

    # 更新发布状态
    strategy_repo.update_publish_status(
        strategy_id=strategy_id,
        new_status='pending_review'
    )

    # 记录审核历史（用户申请）
    review_repo.create({
        'strategy_id': strategy_id,
        'reviewer_id': current_user.id,  # 申请人就是用户自己
        'action': 'request_publish',  # 注意：这是一个新的action类型
        'previous_status': current_publish_status,
        'new_status': 'pending_review',
        'comment': '用户申请发布'
    })

    return {
        "success": True,
        "message": "发布申请已提交，请等待管理员审核",
        "data": {
            "strategy_id": strategy_id,
            "publish_status": "pending_review"
        }
    }


@router.post(
    "/{strategy_id}/withdraw-publish",
    summary="撤回发布申请",
    status_code=status.HTTP_200_OK
)
async def withdraw_publish_request(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    用户撤回发布申请

    权限要求：
    - 必须是策略的创建者
    - 策略当前状态必须是 pending_review

    状态变更：
    - pending_review -> draft
    """
    strategy_repo = StrategyRepository()
    review_repo = PublishReviewRepository()

    # 获取策略信息
    strategy = strategy_repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="策略不存在"
        )

    # 检查权限：必须是策略创建者
    if strategy.get('user_id') != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有策略创建者可以撤回申请"
        )

    # 检查当前状态
    current_publish_status = strategy.get('publish_status', 'draft')
    if current_publish_status != 'pending_review':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有待审核的策略可以撤回申请，当前状态：{current_publish_status}"
        )

    # 更新发布状态（撤回到草稿）
    strategy_repo.update_publish_status(
        strategy_id=strategy_id,
        new_status='draft'
    )

    # 记录审核历史（用户撤回）
    review_repo.create({
        'strategy_id': strategy_id,
        'reviewer_id': current_user.id,
        'action': 'withdraw',
        'previous_status': current_publish_status,
        'new_status': 'draft',
        'comment': '用户撤回发布申请'
    })

    return {
        "success": True,
        "message": "已撤回发布申请",
        "data": {
            "strategy_id": strategy_id,
            "publish_status": "draft"
        }
    }


@router.get(
    "/my-strategies",
    summary="获取我的策略列表",
    status_code=status.HTTP_200_OK
)
async def get_my_strategies(
    publish_status: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取当前用户创建的所有策略

    支持按发布状态过滤：draft, pending_review, approved, rejected
    """
    strategy_repo = StrategyRepository()

    # 只查询当前用户的策略
    result = strategy_repo.list_all(
        user_id=current_user.id,
        publish_status=publish_status,
        page=page,
        page_size=page_size,
        include_code=False  # 列表不包含完整代码
    )

    return {
        "success": True,
        "data": result['items'],
        "meta": result['meta']
    }
