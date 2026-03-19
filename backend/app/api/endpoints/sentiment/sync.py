"""
情绪数据同步端点

包含以下功能：
- 数据同步（单日/批量）
- 交易日历同步
- 任务状态查询
- 活动任务列表
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import uuid

from loguru import logger

from app.services.sentiment_service import MarketSentimentService
from app.core.exceptions import ExternalAPIError
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.api_response import ApiResponse


router = APIRouter()
sentiment_service = MarketSentimentService()


# ========== 交易日历同步 ==========

@router.post("/calendar/sync")
async def sync_trading_calendar(
    years: List[int] = Query([datetime.now().year], description="年份列表"),
    current_user: User = Depends(require_admin)
):
    """
    同步交易日历

    Args:
        years: 要同步的年份列表

    Returns:
        同步结果
    """
    try:
        total_count = await sentiment_service.sync_trading_calendar_batch(years)

        return ApiResponse.success(
            message=f"交易日历同步成功，共{total_count}条记录",
            data={
                "years": years,
                "total_count": total_count
            }
        )

    except ExternalAPIError as e:
        logger.error(f"同步交易日历失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 数据同步 ==========

@router.get("/sync/status/{task_id}")
async def get_sync_task_status(
    task_id: str,
    current_user: User = Depends(require_admin)
):
    """
    查询同步任务状态（支持数据同步和AI分析任务）

    Args:
        task_id: 任务ID

    Returns:
        任务状态信息
    """
    try:
        from celery.result import AsyncResult

        task_result = AsyncResult(task_id)

        # 获取任务状态
        state = task_result.state
        info = task_result.info

        response_data = {
            "task_id": task_id,
            "status": state,  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, PROGRESS
        }

        if state == 'PENDING':
            response_data["message"] = "任务等待中"
            response_data["progress"] = 0
        elif state == 'STARTED':
            response_data["message"] = "任务执行中"
            response_data["progress"] = 10
        elif state == 'PROGRESS':
            # 自定义进度状态，从 info 中获取详细信息
            if isinstance(info, dict):
                response_data["message"] = info.get('message', '任务执行中')
                response_data["progress"] = info.get('progress', 0)
                response_data["current"] = info.get('current', 0)
                response_data["total"] = info.get('total', 0)
                # 如果有详细信息，也一并返回
                if 'details' in info:
                    response_data["details"] = info['details']
            else:
                response_data["message"] = "任务执行中"
                response_data["progress"] = 0
        elif state == 'SUCCESS':
            response_data["message"] = "任务完成"
            response_data["progress"] = 100
            response_data["result"] = info  # 任务返回的结果

            # 针对AI分析任务，返回更友好的结果格式
            if isinstance(info, dict) and 'ai_provider' in info:
                response_data["result"] = {
                    "success": True,
                    "date": info.get('date'),
                    "ai_provider": info.get('ai_provider'),
                    "tokens_used": info.get('tokens_used'),
                    "generation_time": info.get('generation_time')
                }
        elif state == 'FAILURE':
            response_data["message"] = "任务失败"
            response_data["progress"] = 0
            response_data["error"] = str(info) if info else "未知错误"
        elif state == 'RETRY':
            response_data["message"] = "任务重试中"
            response_data["progress"] = 25
        else:
            response_data["message"] = f"未知状态: {state}"
            response_data["progress"] = 0

        return ApiResponse.success(data=response_data)

    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_sentiment_data(
    date: Optional[str] = Query(None, description="日期(YYYY-MM-DD)"),
    current_user: User = Depends(require_admin)
):
    """
    手动触发情绪数据同步（异步任务）

    Args:
        date: 日期，默认为今天

    Returns:
        任务ID，用于后续查询任务状态
    """
    try:
        from app.tasks.sentiment_tasks import manual_sentiment_sync_task
        from app.core.redis_lock import redis_lock

        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"手动触发情绪数据同步（异步）: {date}")

        # 检查是否有同步任务正在执行（双层保护：API层 + 任务层）
        lock_key = f"sentiment_sync:{date}"
        if redis_lock:
            is_locked = redis_lock.redis.exists(lock_key)

            if is_locked:
                logger.warning(f"⚠️  {date} 数据同步任务已在执行中，拒绝重复提交")
                return ApiResponse.error(
                    message="数据同步任务正在执行中",
                    code=409,
                    data={
                        "date": date,
                        "status": "locked",
                        "reason": "已有同步任务正在进行，请等待其完成后再试"
                    }
                )

        # 提交到 Celery 异步执行
        task = manual_sentiment_sync_task.apply_async(
            args=[date],
            task_id=f"manual_sentiment_sync_{date}"  # 使用固定ID，便于查询
        )

        return ApiResponse.success(
            message="同步任务已提交",
            data={
                "task_id": task.id,
                "date": date,
                "status": "pending"
            }
        )

    except Exception as e:
        logger.error(f"提交同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/batch")
async def sync_sentiment_batch(
    start_date: str = Query(..., description="起始日期(YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期(YYYY-MM-DD)"),
    current_user: User = Depends(require_admin)
):
    """
    批量同步情绪数据（异步任务）

    Args:
        start_date: 起始日期
        end_date: 结束日期

    Returns:
        任务ID，用于后续查询任务状态
    """
    try:
        from app.tasks.sentiment_tasks import batch_sentiment_sync_task

        logger.info(f"手动触发情绪数据批量同步（异步）: {start_date} ~ {end_date}")

        # 验证日期格式
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return ApiResponse.error(message="日期格式错误，请使用 YYYY-MM-DD 格式", code=400)

        # 验证日期范围
        if start_date > end_date:
            return ApiResponse.error(message="起始日期不能晚于结束日期", code=400)

        # 生成唯一任务ID
        task_id = f"batch_sentiment_sync_{start_date}_{end_date}_{uuid.uuid4().hex[:8]}"

        # 提交到 Celery 异步执行
        task = batch_sentiment_sync_task.apply_async(
            args=[start_date, end_date],
            task_id=task_id
        )

        return ApiResponse.success(
            message="批量同步任务已提交",
            data={
                "task_id": task.id,
                "start_date": start_date,
                "end_date": end_date,
                "status": "pending",
                "display_name": f"情绪数据批量同步 ({start_date} ~ {end_date})"
            }
        )

    except Exception as e:
        logger.error(f"提交批量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 活动任务管理 ==========

@router.get("/tasks/active")
async def get_active_tasks(
    current_user: User = Depends(require_admin)
):
    """
    获取所有正在执行的异步任务列表

    用于前端启动时恢复任务轮询状态

    Returns:
        正在执行的任务列表
    """
    try:
        from app.celery_app import celery_app

        active_tasks = []

        # 获取 Celery Inspector
        inspect = celery_app.control.inspect()

        # 获取所有活动任务（正在执行 + 等待中）
        active = inspect.active()  # 正在执行的任务
        reserved = inspect.reserved()  # 已预留但未执行的任务

        if active:
            for worker, tasks in active.items():
                for task in tasks:
                    task_id = task.get('id')
                    task_name = task.get('name', '')

                    # 解析任务类型和显示名称
                    display_name = _get_task_display_name(task_id, task_name)
                    task_type = _get_task_type(task_name)

                    active_tasks.append({
                        "task_id": task_id,
                        "task_name": task_name,
                        "display_name": display_name,
                        "task_type": task_type,
                        "status": "running",
                        "worker": worker
                    })

        if reserved:
            for worker, tasks in reserved.items():
                for task in tasks:
                    task_id = task.get('id')
                    task_name = task.get('name', '')

                    # 解析任务类型和显示名称
                    display_name = _get_task_display_name(task_id, task_name)
                    task_type = _get_task_type(task_name)

                    active_tasks.append({
                        "task_id": task_id,
                        "task_name": task_name,
                        "display_name": display_name,
                        "task_type": task_type,
                        "status": "pending",
                        "worker": worker
                    })

        logger.info(f"获取到 {len(active_tasks)} 个活动任务")

        return ApiResponse.success(data={
            "total": len(active_tasks),
            "tasks": active_tasks
        })

    except Exception as e:
        logger.error(f"获取活动任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 辅助函数 ==========

def _get_task_type(task_name: str) -> str:
    """
    根据任务名称获取任务类型

    Args:
        task_name: 任务名称

    Returns:
        任务类型 (sync, ai_analysis, backtest, other)
    """
    if task_name.startswith('sync.'):
        return 'sync'
    elif task_name.startswith('sentiment.'):
        # 细分 sentiment 任务类型
        if 'ai_analysis' in task_name:
            return 'ai_analysis'
        return 'sentiment'
    elif 'ai_analysis' in task_name or 'ai_strategy' in task_name:
        return 'ai_analysis'
    elif 'backtest' in task_name:
        return 'backtest'
    elif 'premarket' in task_name:
        return 'premarket'
    else:
        return 'other'


def _get_task_display_name(task_id: str, task_name: str) -> str:
    """
    根据任务ID和任务名称生成友好的显示名称

    Args:
        task_id: 任务ID
        task_name: 任务名称

    Returns:
        显示名称
    """
    # 根据任务名称（Celery 注册的任务名）生成显示名称
    task_name_mapping = {
        "sync.stock_list": "股票列表同步",
        "sync.daily_batch": "日线数据批量同步",
        "sync.new_stocks": "新股列表同步",
        "sync.delisted_stocks": "退市股票同步",
        "sync.concept": "概念数据同步",
        "sentiment.daily_sync_17_30": "情绪数据定时同步",
        "sentiment.manual_sync": "情绪数据手动同步",
        "sentiment.ai_analysis_18_00": "情绪AI分析（定时任务）",
        "backtest.run_strategy": "策略回测",
        "ai_strategy.generate": "AI策略生成",
        "premarket.daily_analysis": "盘前预期分析"
    }

    # 优先使用任务名称映射
    if task_name in task_name_mapping:
        return task_name_mapping[task_name]

    # AI分析任务（通过 task_id 识别）
    if task_id.startswith('ai_analysis_'):
        parts = task_id.split('_')
        if len(parts) >= 3:
            date = parts[2]
            provider = parts[3] if len(parts) >= 4 else ""
            if provider:
                return f"AI分析生成（{date} - {provider}）"
            return f"AI分析生成（{date}）"
        return "AI分析生成"

    # 手动情绪同步任务（通过 task_id 识别）
    if task_id.startswith('manual_sentiment_sync_'):
        parts = task_id.split('_')
        if len(parts) >= 4:
            date = parts[3]
            return f"情绪数据同步（{date}）"
        return "情绪数据同步"

    # 回测任务
    if 'backtest' in task_name.lower():
        return "策略回测"

    # AI策略生成任务
    if 'ai_strategy' in task_name.lower():
        return "AI策略生成"

    # 盘前任务
    if 'premarket' in task_name.lower():
        return "盘前预期管理"

    # 默认使用任务名称
    return task_name.replace('_', ' ').title()
