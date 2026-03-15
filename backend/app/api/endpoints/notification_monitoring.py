"""
通知系统监控 API 端点

Phase 3: 提供监控数据查询接口（仅管理员可访问）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_super_admin
from app.services.notification_monitor import NotificationMonitor
from app.services.notification_alert import NotificationAlert
from app.schemas.response import ApiResponse

router = APIRouter()


@router.get("/statistics", response_model=ApiResponse)
def get_notification_statistics(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    channel: Optional[str] = Query(None, description="渠道类型 (email/telegram/in_app)"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """
    获取通知发送成功率统计

    默认查询最近 7 天数据
    """
    try:
        # 默认时间范围：最近 7 天
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        monitor = NotificationMonitor(db)
        stats = monitor.get_success_rate_statistics(
            start_date=start_date,
            end_date=end_date,
            channel=channel
        )

        return ApiResponse(
            success=True,
            message="获取统计数据成功",
            data=stats
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取统计数据失败: {str(e)}"
        )


@router.get("/failures", response_model=ApiResponse)
def get_notification_failures(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """
    获取通知发送失败记录

    默认查询最近 7 天数据
    """
    try:
        # 默认时间范围：最近 7 天
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        monitor = NotificationMonitor(db)
        failures = monitor.get_failure_analysis(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return ApiResponse(
            success=True,
            message="获取失败记录成功",
            data=failures
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取失败记录失败: {str(e)}"
        )


@router.get("/failure-reasons", response_model=ApiResponse)
def get_failure_reasons_summary(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """
    获取失败原因统计汇总

    返回失败原因及其出现次数
    """
    try:
        # 默认时间范围：最近 7 天
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        monitor = NotificationMonitor(db)
        summary = monitor.get_failure_reasons_summary(
            start_date=start_date,
            end_date=end_date
        )

        return ApiResponse(
            success=True,
            message="获取失败原因汇总成功",
            data=summary
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取失败原因汇总失败: {str(e)}"
        )


@router.get("/channel-performance", response_model=ApiResponse)
def get_channel_performance(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """
    获取各渠道性能分析

    包含成功率、平均送达时间、失败原因、发送高峰时段
    """
    try:
        # 默认时间范围：最近 7 天
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        monitor = NotificationMonitor(db)
        performance = monitor.get_channel_performance(
            start_date=start_date,
            end_date=end_date
        )

        return ApiResponse(
            success=True,
            message="获取渠道性能分析成功",
            data=performance
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取渠道性能分析失败: {str(e)}"
        )


@router.get("/daily-trend", response_model=ApiResponse)
def get_daily_trend(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    channel: Optional[str] = Query(None, description="渠道类型 (email/telegram/in_app)"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """
    获取每日发送趋势

    按日期统计发送总数、成功数、失败数
    """
    try:
        # 默认时间范围：最近 30 天
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        monitor = NotificationMonitor(db)
        trend = monitor.get_daily_trend(
            start_date=start_date,
            end_date=end_date,
            channel=channel
        )

        return ApiResponse(
            success=True,
            message="获取每日趋势成功",
            data=trend
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取每日趋势失败: {str(e)}"
        )


@router.get("/realtime", response_model=ApiResponse)
def get_realtime_stats(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """
    获取实时监控数据

    包含最近 24 小时、最近 1 小时统计，待发送数量，最近失败记录
    """
    try:
        monitor = NotificationMonitor(db)
        realtime_data = monitor.get_realtime_stats()

        return ApiResponse(
            success=True,
            message="获取实时监控数据成功",
            data=realtime_data
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取实时监控数据失败: {str(e)}"
        )


@router.get("/health-check", response_model=ApiResponse)
def health_check(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """
    通知系统健康检查

    返回系统健康状态、成功率、告警信息
    """
    try:
        monitor = NotificationMonitor(db)
        health_status = monitor.health_check()

        return ApiResponse(
            success=True,
            message="健康检查完成",
            data=health_status
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"健康检查失败: {str(e)}"
        )


@router.post("/check-and-alert", response_model=ApiResponse)
def check_and_alert(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """
    执行健康检查并触发告警

    手动触发健康检查和告警机制（通常由定时任务自动执行）
    """
    try:
        alert_service = NotificationAlert(db)
        result = alert_service.check_and_alert()

        return ApiResponse(
            success=True,
            message=f"健康检查完成，触发 {len(result.get('alerts_triggered', []))} 条告警",
            data=result
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"健康检查失败: {str(e)}"
        )


@router.get("/failure-analysis", response_model=ApiResponse)
def get_failure_analysis_and_suggestions(
    days: int = Query(7, ge=1, le=90, description="分析天数"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """
    获取失败分析和优化建议

    分析失败原因，提供优化建议和趋势分析
    """
    try:
        alert_service = NotificationAlert(db)
        analysis = alert_service.analyze_failures_and_suggest(days=days)

        return ApiResponse(
            success=True,
            message="失败分析完成",
            data=analysis
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"失败分析失败: {str(e)}"
        )


@router.get("/user-stats/{user_id}", response_model=ApiResponse)
def get_user_notification_stats(
    user_id: int,
    days: int = Query(30, ge=1, le=90, description="统计天数"),
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """
    获取指定用户的通知统计

    按通知类型和渠道统计用户的通知接收情况
    """
    try:
        monitor = NotificationMonitor(db)
        stats = monitor.get_user_notification_stats(
            user_id=user_id,
            days=days
        )

        return ApiResponse(
            success=True,
            message="获取用户通知统计成功",
            data=stats
        )

    except Exception as e:
        return ApiResponse(
            success=False,
            message=f"获取用户通知统计失败: {str(e)}"
        )
