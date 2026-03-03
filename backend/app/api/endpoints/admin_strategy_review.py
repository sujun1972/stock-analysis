"""
策略审核API端点（管理员端）

提供策略发布审核、批准、拒绝等功能

作者: Backend Team
创建日期: 2026-03-02
版本: 1.0.0
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_admin
from app.models.user import User
from app.repositories.strategy_repository import StrategyRepository
from app.repositories.publish_review_repository import PublishReviewRepository
from app.schemas.strategy import ApproveStrategyRequest, RejectStrategyRequest, PublishReviewResponse

router = APIRouter(tags=["admin-strategy-review"])


@router.get(
    "/pending-review",
    summary="获取待审核策略列表",
    status_code=status.HTTP_200_OK
)
async def get_pending_review_strategies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    获取所有待审核的策略列表

    权限要求：管理员或超级管理员
    """
    strategy_repo = StrategyRepository()

    result = strategy_repo.list_all(
        publish_status='pending_review',
        page=page,
        page_size=page_size,
        include_code=False
    )

    return {
        "success": True,
        "data": result['items'],
        "meta": result['meta']
    }


@router.post(
    "/{strategy_id}/approve",
    summary="批准策略发布",
    status_code=status.HTTP_200_OK
)
async def approve_strategy(
    strategy_id: int,
    request: ApproveStrategyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    批准策略发布

    权限要求：管理员或超级管理员

    状态变更：
    - pending_review -> approved

    可选：自动启用策略（auto_enable=True）
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

    # 检查当前状态
    current_publish_status = strategy.get('publish_status', 'draft')
    if current_publish_status != 'pending_review':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有待审核的策略可以批准，当前状态：{current_publish_status}"
        )

    # 更新发布状态为已批准
    strategy_repo.update_publish_status(
        strategy_id=strategy_id,
        new_status='approved',
        reviewer_id=current_user.id
    )

    # 如果需要自动启用
    if request.auto_enable:
        strategy_repo.update(strategy_id, {'is_enabled': True})

    # 记录审核历史
    review_repo.create({
        'strategy_id': strategy_id,
        'reviewer_id': current_user.id,
        'action': 'approve',
        'previous_status': current_publish_status,
        'new_status': 'approved',
        'comment': request.comment or '管理员批准发布',
        'metadata': {
            'auto_enabled': request.auto_enable
        }
    })

    return {
        "success": True,
        "message": "策略已批准发布" + ("并启用" if request.auto_enable else ""),
        "data": {
            "strategy_id": strategy_id,
            "publish_status": "approved",
            "is_enabled": request.auto_enable
        }
    }


@router.post(
    "/{strategy_id}/reject",
    summary="拒绝策略发布",
    status_code=status.HTTP_200_OK
)
async def reject_strategy(
    strategy_id: int,
    request: RejectStrategyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    拒绝策略发布

    权限要求：管理员或超级管理员

    状态变更：
    - pending_review -> rejected

    必须提供拒绝原因
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

    # 检查当前状态
    current_publish_status = strategy.get('publish_status', 'draft')
    if current_publish_status != 'pending_review':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有待审核的策略可以拒绝，当前状态：{current_publish_status}"
        )

    # 更新发布状态为已拒绝
    strategy_repo.update_publish_status(
        strategy_id=strategy_id,
        new_status='rejected',
        reviewer_id=current_user.id,
        reject_reason=request.reason
    )

    # 记录审核历史
    review_repo.create({
        'strategy_id': strategy_id,
        'reviewer_id': current_user.id,
        'action': 'reject',
        'previous_status': current_publish_status,
        'new_status': 'rejected',
        'comment': request.reason
    })

    return {
        "success": True,
        "message": "策略发布已拒绝",
        "data": {
            "strategy_id": strategy_id,
            "publish_status": "rejected",
            "reject_reason": request.reason
        }
    }


@router.get(
    "/{strategy_id}/review-history",
    summary="获取策略审核历史",
    status_code=status.HTTP_200_OK,
    response_model=List[PublishReviewResponse]
)
async def get_strategy_review_history(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """
    获取策略的所有审核历史记录

    权限要求：管理员或超级管理员
    """
    strategy_repo = StrategyRepository()
    review_repo = PublishReviewRepository()

    # 检查策略是否存在
    strategy = strategy_repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="策略不存在"
        )

    # 获取审核历史
    reviews = review_repo.get_by_strategy_id(strategy_id)

    return reviews


@router.post(
    "/{strategy_id}/unpublish",
    summary="取消策略发布",
    status_code=status.HTTP_200_OK
)
async def unpublish_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> Dict[str, Any]:
    """
    取消策略发布（管理员权限）

    权限要求：管理员或超级管理员

    状态变更：
    - approved -> draft

    说明：将已发布的策略撤回到草稿状态，用户需要重新申请发布
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

    # 检查当前状态
    current_publish_status = strategy.get('publish_status', 'draft')
    if current_publish_status != 'approved':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"只有已发布的策略可以取消发布，当前状态：{current_publish_status}"
        )

    # 更新发布状态为草稿，并禁用策略
    strategy_repo.update_publish_status(
        strategy_id=strategy_id,
        new_status='draft',
        reviewer_id=current_user.id
    )

    # 同时禁用策略（取消发布后不应该在策略中心显示）
    strategy_repo.update(strategy_id, {'is_enabled': False})

    # 记录审核历史
    review_repo.create({
        'strategy_id': strategy_id,
        'reviewer_id': current_user.id,
        'action': 'unpublish',
        'previous_status': current_publish_status,
        'new_status': 'draft',
        'comment': '管理员取消发布'
    })

    return {
        "success": True,
        "message": "策略已取消发布",
        "data": {
            "strategy_id": strategy_id,
            "publish_status": "draft",
            "is_enabled": False
        }
    }
