"""
LLM调用日志API端点
提供LLM调用记录的查询、统计和管理功能
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta

from app.core.database import get_db
from app.schemas.llm_call_log import (
    BusinessType, CallStatus, LLMCallLogResponse,
    LLMCallLogQuery, LLMCallStatistics
)
from app.services.llm_call_logger import llm_call_logger
from app.models.llm_call_log import LLMCallLog
from app.core.logging_config import get_logger

logger = get_logger()

router = APIRouter(prefix="/llm-logs", tags=["LLM Logs"])


@router.get("/list", response_model=dict, summary="查询LLM调用日志列表")
async def get_llm_logs(
    business_type: Optional[BusinessType] = Query(None, description="业务类型"),
    provider: Optional[str] = Query(None, description="AI提供商"),
    status: Optional[CallStatus] = Query(None, description="调用状态"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """
    查询LLM调用日志列表

    支持按业务类型、提供商、状态、日期范围筛选
    """
    try:
        query_params = LLMCallLogQuery(
            business_type=business_type,
            provider=provider,
            status=status,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )

        logs, total = llm_call_logger.query_logs(db, query_params)

        return {
            "success": True,
            "data": {
                "logs": logs,
                "pagination": {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
        }
    except Exception as e:
        logger.error(f"查询LLM日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detail/{call_id}", response_model=LLMCallLogResponse, summary="获取单条日志详情")
async def get_llm_log_detail(
    call_id: str,
    db: Session = Depends(get_db)
):
    """获取单条日志的完整详情"""
    log = db.query(LLMCallLog).filter(LLMCallLog.call_id == call_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    return LLMCallLogResponse.model_validate(log)


@router.get("/statistics", response_model=list[LLMCallStatistics], summary="获取LLM调用统计数据")
async def get_llm_statistics(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: Session = Depends(get_db)
):
    """
    获取LLM调用统计数据

    按日期、业务类型、提供商分组统计
    """
    try:
        stats = llm_call_logger.get_statistics(db, start_date, end_date)
        return stats
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", summary="获取LLM调用概览")
async def get_llm_summary(
    days: int = Query(7, ge=1, le=90, description="统计天数"),
    db: Session = Depends(get_db)
):
    """
    获取LLM调用概览（Dashboard用）

    返回：
    - 总调用次数
    - 成功率
    - 总成本
    - 按提供商分布
    - 按业务类型分布
    """
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # 总调用次数和成功率
        total_result = db.query(
            func.count(LLMCallLog.id).label('total_calls'),
            func.count(LLMCallLog.id).filter(LLMCallLog.status == 'success').label('success_calls'),
            func.sum(LLMCallLog.tokens_total).label('total_tokens'),
            func.sum(LLMCallLog.cost_estimate).label('total_cost'),
            func.avg(LLMCallLog.duration_ms).label('avg_duration_ms')
        ).filter(
            LLMCallLog.created_at >= start_date
        ).first()

        # 按提供商分布
        provider_dist = db.query(
            LLMCallLog.provider,
            func.count(LLMCallLog.id).label('count'),
            func.sum(LLMCallLog.cost_estimate).label('cost')
        ).filter(
            LLMCallLog.created_at >= start_date
        ).group_by(LLMCallLog.provider).all()

        # 按业务类型分布
        business_dist = db.query(
            LLMCallLog.business_type,
            func.count(LLMCallLog.id).label('count'),
            func.sum(LLMCallLog.cost_estimate).label('cost')
        ).filter(
            LLMCallLog.created_at >= start_date
        ).group_by(LLMCallLog.business_type).all()

        # 按日期统计（最近7天趋势）
        daily_trend = db.query(
            func.date(LLMCallLog.created_at).label('date'),
            func.count(LLMCallLog.id).label('count'),
            func.sum(LLMCallLog.cost_estimate).label('cost')
        ).filter(
            LLMCallLog.created_at >= start_date
        ).group_by(func.date(LLMCallLog.created_at)).order_by(func.date(LLMCallLog.created_at)).all()

        return {
            "success": True,
            "data": {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "days": days
                },
                "overview": {
                    "total_calls": total_result.total_calls or 0,
                    "success_calls": total_result.success_calls or 0,
                    "success_rate": round((total_result.success_calls or 0) / max(total_result.total_calls, 1) * 100, 2),
                    "total_tokens": int(total_result.total_tokens or 0),
                    "total_cost": float(total_result.total_cost or 0),
                    "avg_duration_ms": round(float(total_result.avg_duration_ms or 0), 2)
                },
                "by_provider": [
                    {
                        "provider": item.provider,
                        "count": item.count,
                        "cost": float(item.cost or 0)
                    }
                    for item in provider_dist
                ],
                "by_business_type": [
                    {
                        "business_type": item.business_type,
                        "count": item.count,
                        "cost": float(item.cost or 0)
                    }
                    for item in business_dist
                ],
                "daily_trend": [
                    {
                        "date": item.date.isoformat(),
                        "count": item.count,
                        "cost": float(item.cost or 0)
                    }
                    for item in daily_trend
                ]
            }
        }
    except Exception as e:
        logger.error(f"获取概览数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent", summary="获取最近的LLM调用记录")
async def get_recent_logs(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    db: Session = Depends(get_db)
):
    """获取最近的LLM调用记录（用于实时监控）"""
    try:
        logs = db.query(LLMCallLog).order_by(LLMCallLog.created_at.desc()).limit(limit).all()

        return {
            "success": True,
            "data": [LLMCallLogResponse.model_validate(log) for log in logs]
        }
    except Exception as e:
        logger.error(f"获取最近日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost-analysis", summary="成本分析")
async def get_cost_analysis(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    group_by: str = Query("provider", description="分组方式: provider, business_type, model"),
    db: Session = Depends(get_db)
):
    """
    成本分析

    按不同维度分组统计LLM调用成本
    """
    try:
        query = db.query(LLMCallLog)

        if start_date:
            query = query.filter(LLMCallLog.business_date >= start_date)
        if end_date:
            query = query.filter(LLMCallLog.business_date <= end_date)

        # 根据group_by选择分组字段
        if group_by == "provider":
            group_field = LLMCallLog.provider
        elif group_by == "business_type":
            group_field = LLMCallLog.business_type
        elif group_by == "model":
            group_field = LLMCallLog.model_name
        else:
            raise HTTPException(status_code=400, detail="Invalid group_by parameter")

        results = query.with_entities(
            group_field.label('group_name'),
            func.count(LLMCallLog.id).label('total_calls'),
            func.sum(LLMCallLog.tokens_total).label('total_tokens'),
            func.sum(LLMCallLog.cost_estimate).label('total_cost'),
            func.avg(LLMCallLog.cost_estimate).label('avg_cost')
        ).group_by(group_field).all()

        return {
            "success": True,
            "data": {
                "group_by": group_by,
                "results": [
                    {
                        "name": item.group_name,
                        "total_calls": item.total_calls,
                        "total_tokens": int(item.total_tokens or 0),
                        "total_cost": float(item.total_cost or 0),
                        "avg_cost": float(item.avg_cost or 0)
                    }
                    for item in results
                ]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"成本分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
