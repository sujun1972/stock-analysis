"""
券商每月荐股 API 端点

提供券商月度金股推荐数据的查询和同步功能
"""

from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException
from loguru import logger

from app.models.api_response import ApiResponse
from app.services.broker_recommend_service import BrokerRecommendService
from app.services import TaskHistoryHelper
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter()


@router.get("")
async def get_broker_recommend(
    month: Optional[str] = Query(None, description="月度,格式：YYYY-MM"),
    start_month: Optional[str] = Query(None, description="开始月度,格式:YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月度,格式:YYYY-MM"),
    broker: Optional[str] = Query(None, description="券商名称"),
    ts_code: Optional[str] = Query(None, description="股票代码"),
    limit: int = Query(100, description="限制返回数量")
):
    """
    查询券商荐股数据

    Args:
        month: 单个月度,格式：YYYY-MM
        start_month: 开始月度,格式：YYYY-MM
        end_month: 结束月度,格式：YYYY-MM
        broker: 券商名称（可选）
        ts_code: 股票代码（可选）
        limit: 限制返回数量

    Returns:
        券商荐股数据列表
    """
    try:
        service = BrokerRecommendService()

        # 转换日期格式：YYYY-MM -> YYYYMM
        month_fmt = month.replace('-', '') if month else None
        start_month_fmt = start_month.replace('-', '') if start_month else None
        end_month_fmt = end_month.replace('-', '') if end_month else None

        result = await service.get_broker_recommend_data(
            month=month_fmt,
            start_month=start_month_fmt,
            end_month=end_month_fmt,
            broker=broker,
            ts_code=ts_code,
            limit=limit
        )

        # 格式化返回数据（YYYYMM -> YYYY-MM）
        for item in result['items']:
            if item['month']:
                item['month'] = f"{item['month'][:4]}-{item['month'][4:]}"

        return ApiResponse.success(data=result)

    except Exception as e:
        logger.error(f"查询券商荐股数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(
    start_month: Optional[str] = Query(None, description="开始月度,格式：YYYY-MM"),
    end_month: Optional[str] = Query(None, description="结束月度,格式：YYYY-MM")
):
    """
    获取券商荐股统计信息

    Args:
        start_month: 开始月度（可选）
        end_month: 结束月度（可选）

    Returns:
        统计信息
    """
    try:
        service = BrokerRecommendService()

        # 转换日期格式
        start_month_fmt = start_month.replace('-', '') if start_month else None
        end_month_fmt = end_month.replace('-', '') if end_month else None

        stats = await service.get_statistics(
            start_month=start_month_fmt,
            end_month=end_month_fmt
        )

        return ApiResponse.success(data=stats)

    except Exception as e:
        logger.error(f"获取券商荐股统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest():
    """
    获取最新月度数据

    Returns:
        最新月度及数据
    """
    try:
        service = BrokerRecommendService()

        # 获取最新月度
        latest_month = await service.get_latest_month()
        if not latest_month:
            return ApiResponse.success(data={
                "latest_month": None,
                "items": [],
                "total": 0
            })

        # 格式化月度（YYYYMM -> YYYY-MM）
        latest_month_formatted = f"{latest_month[:4]}-{latest_month[4:]}"

        # 获取最新月度的数据
        result = await service.get_broker_recommend_data(
            month=latest_month,
            limit=100
        )

        # 格式化返回数据
        for item in result['items']:
            if item['month']:
                item['month'] = f"{item['month'][:4]}-{item['month'][4:]}"

        return ApiResponse.success(data={
            "latest_month": latest_month_formatted,
            "items": result['items'],
            "total": result['total']
        })

    except Exception as e:
        logger.error(f"获取最新月度数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/brokers")
async def get_broker_list(
    month: Optional[str] = Query(None, description="月度,格式：YYYY-MM")
):
    """
    获取券商列表

    Args:
        month: 月度（可选）

    Returns:
        券商名称列表
    """
    try:
        service = BrokerRecommendService()

        # 转换日期格式
        month_fmt = month.replace('-', '') if month else None

        brokers = await service.get_broker_list(month=month_fmt)

        return ApiResponse.success(data={"brokers": brokers})

    except Exception as e:
        logger.error(f"获取券商列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-stocks")
async def get_top_stocks(
    month: str = Query(..., description="月度,格式：YYYY-MM"),
    limit: int = Query(20, description="返回数量")
):
    """
    获取某月被推荐次数最多的股票

    Args:
        month: 月度,格式：YYYY-MM（必需）
        limit: 返回数量

    Returns:
        热门股票列表
    """
    try:
        service = BrokerRecommendService()

        # 转换日期格式
        month_fmt = month.replace('-', '')

        stocks = await service.get_top_stocks(
            month=month_fmt,
            limit=limit
        )

        return ApiResponse.success(data={"stocks": stocks})

    except Exception as e:
        logger.error(f"获取热门股票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-async")
async def sync_broker_recommend_async(
    month: Optional[str] = Query(None, description="月度,格式：YYYY-MM"),
    current_user: User = Depends(require_admin)
):
    """
    异步同步券商荐股数据（通过Celery任务）

    该接口立即返回Celery任务ID，不等待任务完成。
    前端可以通过任务面板查看进度和结果。

    Args:
        month: 月度,格式：YYYY-MM（可选,不传则同步当前月）
        current_user: 当前登录用户（管理员）

    Returns:
        包含Celery任务ID和任务信息的响应
    """
    try:
        from app.tasks.broker_recommend_tasks import sync_broker_recommend_task

        # 转换日期格式：YYYY-MM -> YYYYMM
        month_formatted = month.replace('-', '') if month else None

        # 提交Celery任务（异步执行）
        celery_task = sync_broker_recommend_task.apply_async(
            kwargs={'month': month_formatted}
        )

        # 使用 TaskHistoryHelper 创建任务历史记录
        helper = TaskHistoryHelper()
        task_data = await helper.create_task_record(
            celery_task_id=celery_task.id,
            task_name='tasks.sync_broker_recommend',
            display_name='券商每月荐股',
            task_type='data_sync',
            user_id=current_user.id,
            task_params={
                'month': month_formatted
            },
            source='broker_recommend_page'
        )

        logger.info(f"券商荐股同步任务已提交: {celery_task.id}")

        return ApiResponse.success(
            data=task_data,
            message="任务已提交，正在后台执行"
        )

    except Exception as e:
        logger.error(f"提交券商荐股同步任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
