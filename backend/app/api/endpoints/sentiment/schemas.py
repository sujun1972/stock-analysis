"""
情绪数据相关的 Pydantic Schema 定义

定义所有请求和响应的数据模型，用于参数验证和文档生成。
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========== 任务相关 Schema ==========

class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, PROGRESS
    message: str = ""
    progress: int = 0
    current: Optional[int] = None
    total: Optional[int] = None
    details: Optional[dict] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class SyncTaskSubmitResponse(BaseModel):
    """同步任务提交响应"""
    task_id: str
    date: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = "pending"
    display_name: Optional[str] = None


class ActiveTask(BaseModel):
    """活动任务信息"""
    task_id: str
    task_name: str
    display_name: str
    task_type: str  # sync, ai_analysis, backtest, sentiment, other
    status: str  # running, pending
    worker: str


class ActiveTasksResponse(BaseModel):
    """活动任务列表响应"""
    total: int
    tasks: List[ActiveTask]


# ========== 情绪数据查询 Schema ==========

class SentimentReportResponse(BaseModel):
    """情绪报告响应"""
    date: str
    market_data: Optional[dict] = None
    limit_up_pool: Optional[dict] = None
    dragon_tiger: Optional[dict] = None


class SentimentListQuery(BaseModel):
    """情绪列表查询参数"""
    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页数量")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")


# ========== 涨停板相关 Schema ==========

class LimitUpDetailResponse(BaseModel):
    """涨停板详情响应"""
    date: str
    limit_up_count: int
    broken_count: int
    consecutive_boards: Optional[List[dict]] = None
    stocks: Optional[List[dict]] = None


class LimitUpTrendResponse(BaseModel):
    """涨停板趋势响应"""
    trend: List[dict]
    summary: dict


# ========== 龙虎榜相关 Schema ==========

class DragonTigerQuery(BaseModel):
    """龙虎榜查询参数"""
    date: Optional[str] = Field(None, description="日期")
    stock_code: Optional[str] = Field(None, description="股票代码")
    has_institution: Optional[bool] = Field(None, description="是否有机构参与")
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


# ========== 交易日历相关 Schema ==========

class TradingCalendarQuery(BaseModel):
    """交易日历查询参数"""
    year: Optional[int] = Field(None, description="年份")
    month: Optional[int] = Field(None, description="月份")


class TradingCalendarSyncRequest(BaseModel):
    """交易日历同步请求"""
    years: List[int] = Field(default_factory=lambda: [datetime.now().year], description="年份列表")


# ========== 统计分析 Schema ==========

class SentimentStatisticsQuery(BaseModel):
    """情绪统计查询参数"""
    start_date: str = Field(..., description="开始日期(YYYY-MM-DD)")
    end_date: str = Field(..., description="结束日期(YYYY-MM-DD)")


# ========== 情绪周期相关 Schema ==========

class CycleStageResponse(BaseModel):
    """情绪周期阶段响应"""
    date: str
    stage: str  # 冰点期/修复期/高潮期/退潮期
    score: float
    indicators: dict


class CycleTrendQuery(BaseModel):
    """情绪周期趋势查询参数"""
    days: int = Field(30, ge=7, le=90, description="天数")


class HotMoneyRankingQuery(BaseModel):
    """游资排行查询参数"""
    date: Optional[str] = Field(None, description="日期")
    seat_type: str = Field("top_tier", description="席位类型")
    limit: int = Field(10, ge=1, le=50)


class HotMoneyActivityQuery(BaseModel):
    """游资活跃度查询参数"""
    days: int = Field(30, ge=7, le=90, description="统计天数")
    limit: int = Field(20, ge=1, le=50)


class CycleCalculateRequest(BaseModel):
    """情绪周期计算请求"""
    date: str = Field(..., description="日期(YYYY-MM-DD)")


# ========== AI分析相关 Schema ==========

class AIAnalysisResponse(BaseModel):
    """AI分析响应"""
    date: str
    content: str
    ai_provider: str
    tokens_used: Optional[int] = None
    generation_time: Optional[float] = None
    created_at: str


class AIAnalysisGenerateRequest(BaseModel):
    """AI分析生成请求"""
    date: Optional[str] = Field(None, description="日期(YYYY-MM-DD)")
    provider: str = Field("deepseek", description="AI提供商(deepseek/gemini/openai)")
