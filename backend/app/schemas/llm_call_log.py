"""
LLM调用日志的Pydantic Schema定义
用于API请求和响应验证
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime, date
from enum import Enum


class BusinessType(str, Enum):
    """业务类型枚举"""
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    PREMARKET_ANALYSIS = "premarket_analysis"
    STRATEGY_GENERATION = "strategy_generation"
    STOCK_EXPERT_ANALYSIS = "stock_expert_analysis"
    SENTIMENT_SCORING = "sentiment_scoring"  # 公告/快讯批量情绪打分


class CallStatus(str, Enum):
    """调用状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


class LLMCallLogCreate(BaseModel):
    """创建LLM调用日志"""
    call_id: str
    business_type: BusinessType
    business_date: Optional[date] = None
    business_id: Optional[str] = None

    provider: str
    model_name: str
    api_base_url: Optional[str] = None

    call_parameters: Dict[str, Any]

    prompt_text: str
    prompt_length: int
    prompt_hash: str

    response_text: Optional[str] = None
    response_length: Optional[int] = None
    parsed_result: Optional[Dict[str, Any]] = None

    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    tokens_total: Optional[int] = None
    cost_estimate: Optional[float] = None

    duration_ms: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None

    status: CallStatus
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    http_status_code: Optional[int] = None
    request_headers: Optional[Dict[str, Any]] = None
    response_headers: Optional[Dict[str, Any]] = None

    caller_service: Optional[str] = None
    caller_function: Optional[str] = None
    user_id: Optional[str] = None
    is_scheduled: bool = False
    retry_count: int = 0
    parent_call_id: Optional[str] = None


class LLMCallLogResponse(BaseModel):
    """LLM调用日志响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    call_id: str
    business_type: str
    business_date: Optional[date] = None
    business_id: Optional[str] = None

    provider: str
    model_name: str
    api_base_url: Optional[str] = None

    call_parameters: Dict[str, Any]

    prompt_text: str
    prompt_length: int
    prompt_hash: str

    response_text: Optional[str] = None
    response_length: Optional[int] = None
    parsed_result: Optional[Dict[str, Any]] = None

    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    tokens_total: Optional[int] = None
    cost_estimate: Optional[float] = None

    duration_ms: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None

    status: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    http_status_code: Optional[int] = None
    request_headers: Optional[Dict[str, Any]] = None
    response_headers: Optional[Dict[str, Any]] = None

    caller_service: Optional[str] = None
    caller_function: Optional[str] = None
    user_id: Optional[str] = None
    is_scheduled: bool = False
    retry_count: int = 0
    parent_call_id: Optional[str] = None

    created_at: datetime
    updated_at: datetime


class LLMCallLogQuery(BaseModel):
    """LLM调用日志查询参数"""
    business_type: Optional[BusinessType] = None
    provider: Optional[str] = None
    status: Optional[CallStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class LLMCallStatistics(BaseModel):
    """LLM调用统计"""
    stat_date: date
    business_type: str
    provider: str
    model_name: str

    total_calls: int
    success_calls: int
    failed_calls: int
    success_rate: float

    total_tokens: Optional[int] = None
    avg_tokens_per_call: Optional[float] = None
    max_tokens: Optional[int] = None

    total_cost: Optional[float] = None
    avg_cost_per_call: Optional[float] = None

    avg_duration_ms: Optional[float] = None
    min_duration_ms: Optional[int] = None
    max_duration_ms: Optional[int] = None
    p95_duration_ms: Optional[float] = None

    total_retries: Optional[int] = None
    avg_retry_per_call: Optional[float] = None


class LLMPricingConfigResponse(BaseModel):
    """LLM定价配置响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: str
    model_name: str
    input_price_per_million: Optional[float] = None
    output_price_per_million: Optional[float] = None
    effective_from: date
    effective_to: Optional[date] = None
    currency: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
