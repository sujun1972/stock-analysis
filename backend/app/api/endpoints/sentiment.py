"""
市场情绪API端点

提供市场情绪数据的查询和同步接口。
"""

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime

from loguru import logger

from app.services.sentiment_service import MarketSentimentService
from app.core.exceptions import DatabaseError, ExternalAPIError


router = APIRouter()
sentiment_service = MarketSentimentService()


# ========== 情绪数据查询 ==========

@router.get("/daily")
async def get_daily_sentiment(
    date: Optional[str] = Query(None, description="日期(YYYY-MM-DD)，默认为今天")
):
    """
    获取指定日期的市场情绪数据

    Returns:
        包含大盘数据、涨停板池、龙虎榜统计的完整情绪报告
    """
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        report = await sentiment_service.get_sentiment_report(date)

        return {
            "code": 200,
            "message": "success",
            "data": report
        }

    except DatabaseError as e:
        logger.error(f"查询每日情绪数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def get_sentiment_list(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期")
):
    """
    分页查询情绪数据列表（Admin管理界面用）

    Returns:
        分页的情绪数据列表
    """
    try:
        result = await sentiment_service.get_sentiment_list(
            page=page,
            limit=limit,
            start_date=start_date,
            end_date=end_date
        )

        return {
            "code": 200,
            "message": "success",
            "data": result
        }

    except DatabaseError as e:
        logger.error(f"查询情绪列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 涨停板池 ==========

@router.get("/limit-up")
async def get_limit_up_pool(
    date: Optional[str] = Query(None, description="日期(YYYY-MM-DD)")
):
    """
    获取涨停板池数据

    包含涨停股票列表、炸板数据、连板天梯等。
    """
    try:
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        data = await sentiment_service.get_limit_up_detail(date)

        if not data:
            return {
                "code": 404,
                "message": f"{date}没有涨停板数据",
                "data": None
            }

        return {
            "code": 200,
            "message": "success",
            "data": data
        }

    except DatabaseError as e:
        logger.error(f"查询涨停板池失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/limit-up/trend")
async def get_limit_up_trend(
    days: int = Query(30, ge=7, le=90, description="天数")
):
    """
    获取涨停板趋势（近N天）

    Returns:
        涨停、炸板、连板天数的时间序列数据
    """
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        stats = await sentiment_service.get_sentiment_statistics(start_date, end_date)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "trend": stats.get("trend", []),
                "summary": stats.get("limit_up_stats", {})
            }
        }

    except DatabaseError as e:
        logger.error(f"查询涨停板趋势失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 龙虎榜 ==========

@router.get("/dragon-tiger")
async def get_dragon_tiger_list(
    date: Optional[str] = Query(None, description="日期"),
    stock_code: Optional[str] = Query(None, description="股票代码"),
    has_institution: Optional[bool] = Query(None, description="是否有机构参与"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    查询龙虎榜数据

    支持按日期、股票代码、是否有机构等条件筛选。
    """
    try:
        result = await sentiment_service.get_dragon_tiger_list(
            date=date,
            stock_code=stock_code,
            has_institution=has_institution,
            page=page,
            limit=limit
        )

        return {
            "code": 200,
            "message": "success",
            "data": result
        }

    except DatabaseError as e:
        logger.error(f"查询龙虎榜失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dragon-tiger/stock/{stock_code}")
async def get_stock_dragon_tiger_history(
    stock_code: str,
    days: int = Query(90, ge=1, le=365, description="查询天数")
):
    """
    查询个股龙虎榜历史

    Args:
        stock_code: 股票代码
        days: 查询天数

    Returns:
        该股票的龙虎榜历史记录
    """
    try:
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        result = await sentiment_service.get_dragon_tiger_list(
            stock_code=stock_code,
            page=1,
            limit=days  # 查询所有记录
        )

        return {
            "code": 200,
            "message": "success",
            "data": result.get("items", [])
        }

    except DatabaseError as e:
        logger.error(f"查询个股龙虎榜历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 交易日历 ==========

@router.get("/calendar")
async def get_trading_calendar(
    year: Optional[int] = Query(None, description="年份"),
    month: Optional[int] = Query(None, description="月份")
):
    """
    查询交易日历

    Args:
        year: 年份（可选）
        month: 月份（可选）

    Returns:
        交易日历列表
    """
    try:
        # 默认查询当年
        if not year:
            year = datetime.now().year

        calendar = await sentiment_service.get_trading_calendar(
            year=year,
            month=month
        )

        return {
            "code": 200,
            "message": "success",
            "data": calendar
        }

    except DatabaseError as e:
        logger.error(f"查询交易日历失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calendar/sync")
async def sync_trading_calendar(
    years: List[int] = Query([datetime.now().year], description="年份列表")
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

        return {
            "code": 200,
            "message": f"交易日历同步成功，共{total_count}条记录",
            "data": {
                "years": years,
                "total_count": total_count
            }
        }

    except ExternalAPIError as e:
        logger.error(f"同步交易日历失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 数据同步 ==========

@router.get("/sync/status/{task_id}")
async def get_sync_task_status(task_id: str):
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

        return {
            "code": 200,
            "message": "success",
            "data": response_data
        }

    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_sentiment_data(
    date: Optional[str] = Query(None, description="日期(YYYY-MM-DD)")
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
                return {
                    "code": 409,  # Conflict
                    "message": "数据同步任务正在执行中",
                    "data": {
                        "date": date,
                        "status": "locked",
                        "reason": "已有同步任务正在进行，请等待其完成后再试"
                    }
                }

        # 提交到 Celery 异步执行
        task = manual_sentiment_sync_task.apply_async(
            args=[date],
            task_id=f"manual_sentiment_sync_{date}"  # 使用固定ID，便于查询
        )

        return {
            "code": 200,
            "message": "同步任务已提交",
            "data": {
                "task_id": task.id,
                "date": date,
                "status": "pending"
            }
        }

    except Exception as e:
        logger.error(f"提交同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/batch")
async def sync_sentiment_batch(
    start_date: str = Query(..., description="起始日期(YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期(YYYY-MM-DD)")
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
        import uuid

        logger.info(f"手动触发情绪数据批量同步（异步）: {start_date} ~ {end_date}")

        # 验证日期格式
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            return {
                "code": 400,
                "message": "日期格式错误，请使用 YYYY-MM-DD 格式",
                "data": None
            }

        # 验证日期范围
        if start_date > end_date:
            return {
                "code": 400,
                "message": "起始日期不能晚于结束日期",
                "data": None
            }

        # 生成唯一任务ID
        task_id = f"batch_sentiment_sync_{start_date}_{end_date}_{uuid.uuid4().hex[:8]}"

        # 提交到 Celery 异步执行
        task = batch_sentiment_sync_task.apply_async(
            args=[start_date, end_date],
            task_id=task_id
        )

        return {
            "code": 200,
            "message": "批量同步任务已提交",
            "data": {
                "task_id": task.id,
                "start_date": start_date,
                "end_date": end_date,
                "status": "pending",
                "display_name": f"情绪数据批量同步 ({start_date} ~ {end_date})"
            }
        }

    except Exception as e:
        logger.error(f"提交批量同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 统计分析 ==========

@router.get("/statistics")
async def get_sentiment_statistics(
    start_date: str = Query(..., description="开始日期(YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期(YYYY-MM-DD)")
):
    """
    获取情绪数据统计分析

    用于Admin看板展示，包括：
    - 平均炸板率
    - 涨停/跌停趋势
    - 连板天数分布
    - 龙虎榜活跃度

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        统计分析数据
    """
    try:
        stats = await sentiment_service.get_sentiment_statistics(
            start_date=start_date,
            end_date=end_date
        )

        return {
            "code": 200,
            "message": "success",
            "data": stats
        }

    except DatabaseError as e:
        logger.error(f"统计分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 健康检查 ==========

@router.get("/health")
async def sentiment_health_check():
    """
    情绪数据模块健康检查

    检查：
    - 数据库连接
    - 最新数据日期
    - 数据完整性
    """
    try:
        # 查询最新数据日期
        latest_date_query = """
            SELECT MAX(trade_date) FROM market_sentiment_daily
        """

        conn = sentiment_service._pool_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute(latest_date_query)
        latest_date = cursor.fetchone()[0]
        cursor.close()
        sentiment_service._pool_manager.release_connection(conn)

        return {
            "code": 200,
            "message": "healthy",
            "data": {
                "latest_date": latest_date.strftime('%Y-%m-%d') if latest_date else None,
                "database_connected": True
            }
        }

    except Exception as e:
        return {
            "code": 500,
            "message": "unhealthy",
            "data": {
                "error": str(e),
                "database_connected": False
            }
        }


# ========== 情绪周期相关（新增）==========

try:
    from app.services.sentiment_cycle_service import SentimentCycleService
    cycle_service = SentimentCycleService()
    _cycle_service_available = True
except Exception as e:
    logger.warning(f"情绪周期服务不可用: {e}")
    _cycle_service_available = False


@router.get("/cycle/current")
async def get_current_cycle():
    """
    获取当前情绪周期阶段

    Returns:
        当前市场情绪周期数据
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        cycle = cycle_service.get_cycle_stage()

        if 'error' in cycle:
            return {
                "code": 404,
                "message": cycle['error'],
                "data": None
            }

        return {
            "code": 200,
            "message": "success",
            "data": cycle
        }

    except Exception as e:
        logger.error(f"获取当前情绪周期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cycle/trend")
async def get_cycle_trend(
    days: int = Query(30, ge=7, le=90, description="天数")
):
    """
    获取情绪周期趋势（近N天）

    Returns:
        趋势图数据
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        trend = cycle_service.get_cycle_trend(days=days)

        return {
            "code": 200,
            "message": "success",
            "data": trend
        }

    except Exception as e:
        logger.error(f"获取情绪周期趋势失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== 游资分析相关（新增）==========

@router.get("/hot-money/institution-top")
async def get_institution_top_stocks(
    date: Optional[str] = Query(None, description="日期"),
    limit: int = Query(3, ge=1, le=10)
):
    """
    获取机构净买入排行

    Returns:
        机构净买入前N的个股
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        ranking = cycle_service.get_institution_ranking(
            date=date,
            limit=limit
        )

        return {
            "code": 200,
            "message": "success",
            "data": ranking
        }

    except Exception as e:
        logger.error(f"获取机构排行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-money/top-tier-limit-up")
async def get_top_tier_limit_up_stocks(
    date: Optional[str] = Query(None, description="日期"),
    seat_type: str = Query("top_tier", description="席位类型"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    获取顶级游资主导打板的个股

    Args:
        date: 日期
        seat_type: 席位类型 (top_tier/famous)
        limit: 返回数量

    Returns:
        游资打板排行榜
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        ranking = cycle_service.get_hot_money_ranking(
            date=date,
            seat_type=seat_type,
            limit=limit
        )

        return {
            "code": 200,
            "message": "success",
            "data": ranking
        }

    except Exception as e:
        logger.error(f"获取游资打板排行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-money/activity-ranking")
async def get_hot_money_activity_ranking(
    days: int = Query(30, ge=7, le=90, description="统计天数"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    获取游资活跃度排行榜

    Returns:
        游资活跃度排行
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        ranking = cycle_service.get_hot_money_activity_ranking(
            days=days,
            limit=limit
        )

        return {
            "code": 200,
            "message": "success",
            "data": ranking
        }

    except Exception as e:
        logger.error(f"获取游资活跃度排行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cycle/calculate")
async def calculate_cycle(
    date: str = Query(..., description="日期(YYYY-MM-DD)")
):
    """
    手动触发情绪周期计算

    Args:
        date: 日期

    Returns:
        计算结果
    """
    if not _cycle_service_available:
        raise HTTPException(status_code=503, detail="情绪周期服务不可用")

    try:
        cycle_service.sync_cycle_calculation(date)

        # 返回计算结果
        cycle = cycle_service.get_cycle_stage(date)

        return {
            "code": 200,
            "message": "计算成功",
            "data": cycle
        }

    except Exception as e:
        logger.error(f"计算情绪周期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# AI分析相关端点
# =====================================================

@router.get("/ai-analysis/{date}")
async def get_ai_analysis(date: str):
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
            return {
                "code": 404,
                "message": f"{date} 暂无AI分析数据",
                "data": None
            }

        return {
            "code": 200,
            "message": "获取成功",
            "data": result
        }

    except Exception as e:
        logger.error(f"获取AI分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-analysis/generate")
async def generate_ai_analysis(
    date: str = None,
    provider: str = "deepseek"
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
        if existing_task.state in ['PENDING', 'STARTED']:
            logger.warning(f"AI分析任务已在执行中: {task_id}")
            return {
                "code": 409,
                "message": "AI分析任务正在执行中，请稍候",
                "data": {
                    "task_id": task_id,
                    "date": date,
                    "status": "running"
                }
            }

        # 提交 Celery 异步任务
        task = daily_sentiment_ai_analysis_task.apply_async(
            args=[date, provider, 0],  # 第三个参数是 retry_count
            task_id=task_id
        )

        logger.info(f"AI分析任务已提交: {task_id}")

        return {
            "code": 200,
            "message": "AI分析任务已提交，正在后台生成",
            "data": {
                "task_id": task.id,
                "date": date,
                "provider": provider,
                "status": "pending"
            }
        }

    except Exception as e:
        logger.error(f"提交AI分析任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/active")
async def get_active_tasks():
    """
    获取所有正在执行的异步任务列表

    用于前端启动时恢复任务轮询状态

    Returns:
        正在执行的任务列表
    """
    try:
        from celery.result import AsyncResult
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

        return {
            "code": 200,
            "message": "success",
            "data": {
                "total": len(active_tasks),
                "tasks": active_tasks
            }
        }

    except Exception as e:
        logger.error(f"获取活动任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
