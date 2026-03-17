"""数据质量监控API端点"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.data_quality_service import DataQualityService
from app.core.security import require_auth

router = APIRouter()


@router.get("/daily-report")
async def get_daily_quality_report(
    trade_date: Optional[date] = Query(None, description="交易日期，默认最新交易日"),
    format: str = Query("json", description="输出格式: json或html"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth)
) -> Any:
    """
    获取每日数据质量报告

    Returns:
        包含各数据源质量状况的详细报告
    """
    service = DataQualityService(db)
    report = await service.generate_daily_quality_report(trade_date)

    if format == "html":
        return await service.export_report_html(report)
    return report


@router.get("/weekly-report")
async def get_weekly_quality_report(
    start_date: Optional[date] = Query(None, description="开始日期，默认本周一"),
    end_date: Optional[date] = Query(None, description="结束日期，默认今天"),
    format: str = Query("json", description="输出格式: json或html"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth)
) -> Any:
    """
    获取周度数据质量报告

    Returns:
        包含一周内数据质量趋势的详细报告
    """
    service = DataQualityService(db)
    report = await service.generate_weekly_quality_report(start_date, end_date)

    if format == "html":
        return await service.export_report_html(report)
    return report


@router.get("/real-time-metrics")
async def get_real_time_metrics(
    data_source: Optional[str] = Query(None, description="数据源名称"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth)
) -> Dict[str, Any]:
    """
    获取实时数据质量指标

    Args:
        data_source: 可选，指定数据源名称

    Returns:
        实时质量指标
    """
    service = DataQualityService(db)

    if data_source:
        metrics = await service.get_data_source_metrics(data_source)
        if not metrics:
            raise HTTPException(status_code=404, detail=f"数据源 {data_source} 不存在")
        return {data_source: metrics}

    # 获取所有数据源的指标
    all_metrics = {}
    sources = [
        'daily_basic', 'moneyflow', 'moneyflow_hsgt',
        'hsgt_top10', 'hk_hold', 'margin', 'margin_detail',
        'stk_limit', 'adj_factor', 'block_trade', 'suspend'
    ]

    for source in sources:
        metrics = await service.get_data_source_metrics(source)
        if metrics:
            all_metrics[source] = metrics

    return all_metrics


@router.get("/health-summary")
async def get_health_summary(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth)
) -> Dict[str, Any]:
    """
    获取数据质量健康状态摘要

    Returns:
        系统整体健康状态和关键指标
    """
    service = DataQualityService(db)
    return await service.get_health_summary()


@router.get("/validation-history")
async def get_validation_history(
    data_source: str = Query(..., description="数据源名称"),
    days: int = Query(7, description="历史天数"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth)
) -> List[Dict[str, Any]]:
    """
    获取数据验证历史记录

    Args:
        data_source: 数据源名称
        days: 查询历史天数

    Returns:
        验证历史记录列表
    """
    service = DataQualityService(db)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    history = await service.get_validation_history(
        data_source, start_date, end_date
    )

    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"未找到 {data_source} 的验证历史记录"
        )

    return history


@router.get("/quality-trends")
async def get_quality_trends(
    days: int = Query(30, description="趋势天数"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth)
) -> Dict[str, Any]:
    """
    获取数据质量趋势分析

    Args:
        days: 分析天数

    Returns:
        各数据源质量趋势
    """
    service = DataQualityService(db)

    trends = {}
    sources = [
        'daily_basic', 'moneyflow', 'hsgt_top10',
        'hk_hold', 'margin_detail', 'stk_limit'
    ]

    for source in sources:
        trend = await service.get_quality_trend(source, days)
        if trend:
            trends[source] = trend

    return {
        "period_days": days,
        "trends": trends,
        "generated_at": datetime.now().isoformat()
    }


@router.post("/trigger-validation")
async def trigger_validation(
    data_source: str,
    trade_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth)
) -> Dict[str, Any]:
    """
    手动触发数据验证

    Args:
        data_source: 数据源名称
        trade_date: 交易日期

    Returns:
        验证结果
    """
    service = DataQualityService(db)

    try:
        result = await service.validate_data_source(data_source, trade_date)
        return {
            "status": "success",
            "data_source": data_source,
            "trade_date": str(trade_date) if trade_date else "latest",
            "validation_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts/active")
async def get_active_alerts(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth)
) -> List[Dict[str, Any]]:
    """
    获取当前活跃的质量告警

    Returns:
        活跃告警列表
    """
    service = DataQualityService(db)
    alerts = await service.get_active_alerts()

    return alerts


@router.post("/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth)
) -> Dict[str, Any]:
    """
    确认质量告警

    Args:
        alert_id: 告警ID

    Returns:
        确认结果
    """
    service = DataQualityService(db)

    try:
        await service.acknowledge_alert(alert_id)
        return {
            "status": "success",
            "alert_id": alert_id,
            "acknowledged_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))