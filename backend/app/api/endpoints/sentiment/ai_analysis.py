"""
情绪AI分析端点

包含以下功能：
- 查询AI分析报告
- 生成AI分析报告
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime

from loguru import logger

from app.core.dependencies import get_current_active_user, require_admin
from app.models.user import User
from app.models.api_response import ApiResponse


router = APIRouter()


# ========== AI分析相关端点 ==========

@router.get("/{date}")
async def get_ai_analysis(
    date: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取指定日期的AI情绪分析报告

    Args:
        date: 日期 (YYYY-MM-DD)

    Returns:
        AI分析报告（四个灵魂拷问）
    """
    try:
        from app.services.sentiment_ai_analysis_service import sentiment_ai_analysis_service

        result = sentiment_ai_analysis_service.get_ai_analysis(date)

        if not result:
            # 无数据时返回统一的404响应格式，避免前端显示不必要的错误提示
            return ApiResponse.error(message=f"{date} 暂无AI分析数据", code=404)

        return ApiResponse.success(message="获取成功", data=result)

    except Exception as e:
        logger.error(f"获取AI分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate")
async def generate_ai_analysis(
    date: Optional[str] = None,
    provider: str = "deepseek",
    current_user: User = Depends(require_admin)
):
    """
    手动触发AI情绪分析生成（异步任务）

    Args:
        date: 日期 (YYYY-MM-DD)，默认为今天
        provider: AI提供商 (deepseek/gemini/openai)

    Returns:
        任务ID和状态，用于后续轮询
    """
    try:
        from app.tasks.sentiment_ai_analysis_task import daily_sentiment_ai_analysis_task
        from celery.result import AsyncResult

        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"手动触发AI分析（异步）: {date}, 提供商: {provider}")

        # 生成固定任务ID（便于查询和去重）
        task_id = f"ai_analysis_{date}_{provider}"

        # 检查是否已有任务正在执行
        existing_task = AsyncResult(task_id)
        # PENDING 是默认状态，不代表任务存在，只检查真正运行中的状态
        if existing_task.state in ['STARTED', 'PROGRESS', 'RETRY']:
            logger.warning(f"AI分析任务已在执行中: {task_id}, 状态: {existing_task.state}")
            return ApiResponse.error(
                message="AI分析任务正在执行中，请稍候",
                code=409,
                data={
                    "task_id": task_id,
                    "date": date,
                    "status": "running"
                }
            )

        # 如果任务已完成或失败，先撤销旧任务结果，避免ID冲突
        if existing_task.state in ['SUCCESS', 'FAILURE']:
            logger.info(f"撤销已完成的任务结果: {task_id}, 旧状态: {existing_task.state}")
            existing_task.forget()  # 清除任务结果，允许使用相同ID

        # 提交 Celery 异步任务
        task = daily_sentiment_ai_analysis_task.apply_async(
            args=[date, provider, 0],  # 第三个参数是 retry_count
            task_id=task_id
        )

        logger.info(f"AI分析任务已提交: {task_id}")

        return ApiResponse.success(
            message="AI分析任务已提交，正在后台生成",
            data={
                "task_id": task.id,
                "date": date,
                "provider": provider,
                "status": "pending"
            }
        )

    except Exception as e:
        logger.error(f"提交AI分析任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
