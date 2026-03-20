"""
用户回测历史记录API
提供用户查看自己回测历史的功能
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from loguru import logger

from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.api_response import ApiResponse
from app.services.backtest_history_service import BacktestHistoryService

router = APIRouter(tags=["回测历史"])


@router.get("")
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
    try:
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

    except Exception as e:
        logger.error(f"获取回测历史失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取回测历史失败: {str(e)}"
        )


@router.get("/{execution_id}")
async def get_backtest_detail(
    execution_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    获取回测详情（包含完整的result数据）

    只能查看自己的回测记录
    """
    try:
        service = BacktestHistoryService()
        detail = await asyncio.to_thread(
            service.get_backtest_detail,
            execution_id=execution_id,
            username=current_user.username
        )

        return ApiResponse.success(data=detail)

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

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"获取回测详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取回测详情失败: {str(e)}"
        )


@router.delete("/{execution_id}")
async def delete_backtest_record(
    execution_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    删除回测记录

    只能删除自己的回测记录
    """
    try:
        service = BacktestHistoryService()
        await asyncio.to_thread(
            service.delete_backtest_record,
            execution_id=execution_id,
            username=current_user.username
        )

        return ApiResponse.success(message="回测记录已删除")

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

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"删除回测记录失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除回测记录失败: {str(e)}"
        )
