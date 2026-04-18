"""
用户回测历史记录API
提供用户查看自己回测历史的功能
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status

from app.api.error_handler import handle_api_errors
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.api_response import ApiResponse
from app.services.backtest_history_service import BacktestHistoryService

router = APIRouter(tags=["回测历史"])


@router.get("")
@handle_api_errors
async def get_user_backtest_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status_filter: Optional[str] = Query(None, description="状态筛选: completed, failed, running"),
    strategy_id: Optional[int] = Query(None, description="策略ID筛选"),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的回测历史记录

    支持分页、状态筛选和策略筛选
    """
    service = BacktestHistoryService()
    result = await asyncio.to_thread(
        service.get_user_history,
        username=current_user.username,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        strategy_id=strategy_id
    )

    return ApiResponse.success(data=result)


@router.get("/{execution_id}")
@handle_api_errors
async def get_backtest_detail(
    execution_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    获取回测详情（包含完整的result数据）

    只能查看自己的回测记录
    """
    service = BacktestHistoryService()
    try:
        detail = await asyncio.to_thread(
            service.get_backtest_detail,
            execution_id=execution_id,
            username=current_user.username
        )
    except ValueError as e:
        error_msg = str(e)
        if "不存在" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        elif "无权" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg
            )
        raise

    return ApiResponse.success(data=detail)


@router.delete("/{execution_id}")
@handle_api_errors
async def delete_backtest_record(
    execution_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    删除回测记录

    只能删除自己的回测记录
    """
    service = BacktestHistoryService()
    try:
        await asyncio.to_thread(
            service.delete_backtest_record,
            execution_id=execution_id,
            username=current_user.username
        )
    except ValueError as e:
        error_msg = str(e)
        if "不存在" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        elif "无权" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg
            )
        raise

    return ApiResponse.success(message="回测记录已删除")
