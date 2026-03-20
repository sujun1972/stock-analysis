"""
定时任务调度器的 Pydantic 数据模型

包含：
- 任务配置请求/响应模型
- 任务执行参数模型
- Cron 验证模型
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


# ==================== 任务配置模型 ====================

class TaskConfigBase(BaseModel):
    """任务配置基础模型"""
    task_name: str = Field(..., description="任务名称（唯一标识）")
    module: str = Field(..., description="模块名称")
    description: Optional[str] = Field(None, description="任务描述")
    cron_expression: str = Field("0 0 * * *", description="Cron 表达式")
    enabled: bool = Field(False, description="是否启用")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="任务参数")


class TaskConfigCreate(TaskConfigBase):
    """创建任务配置请求模型"""

    @validator('module')
    def validate_module(cls, v):
        valid_modules = [
            "stock_list", "new_stocks", "delisted_stocks",
            "daily", "minute", "realtime", "daily_basic",
            "moneyflow", "moneyflow_hsgt", "moneyflow_mkt_dc",
            "moneyflow_ind_dc", "moneyflow_stock_dc",
            "margin", "margin_detail", "hk_hold",
            "stk_limit", "block_trade", "adj_factor",
            "sentiment", "limit_up_pool", "dragon_tiger",
            "sentiment_cycle", "ai_analysis", "premarket",
            "quality_check", "email_report", "telegram_notify",
            "cleanup"
        ]
        if v not in valid_modules:
            raise ValueError(f"无效的模块名称，支持: {', '.join(valid_modules)}")
        return v


class TaskConfigUpdate(BaseModel):
    """更新任务配置请求模型"""
    description: Optional[str] = None
    cron_expression: Optional[str] = None
    enabled: Optional[bool] = None
    params: Optional[Dict[str, Any]] = None
    display_name: Optional[str] = None
    category: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0, description="显示排序（>=0）")
    points_consumption: Optional[int] = Field(None, ge=0, description="积分消耗（>=0）")


class TaskConfigResponse(BaseModel):
    """任务配置响应模型"""
    id: int
    task_name: str
    module: str
    description: Optional[str]
    cron_expression: str
    enabled: bool
    params: Optional[Dict[str, Any]]
    display_name: Optional[str]
    category: Optional[str]
    display_order: Optional[int]
    points_consumption: Optional[int]
    last_run_at: Optional[str]
    next_run_at: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


# ==================== 任务执行模型 ====================

class TaskExecuteRequest(BaseModel):
    """手动执行任务请求模型"""
    task_id: int = Field(..., description="任务ID")


class TaskExecuteResponse(BaseModel):
    """任务执行响应模型"""
    task_id: int
    task_name: str
    celery_task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    celery_task_id: Optional[str] = None
    history_id: Optional[int] = None
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[int] = None
    message: Optional[str] = None


# ==================== 任务执行历史模型 ====================

class TaskExecutionHistoryResponse(BaseModel):
    """任务执行历史响应模型"""
    id: int
    task_name: str
    module: str
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[float]
    result_summary: Optional[Dict[str, Any]]
    error_message: Optional[str]
    cron_expression: Optional[str] = None  # 仅在 recent history 中存在

    class Config:
        from_attributes = True


# ==================== Cron 验证模型 ====================

class CronValidateRequest(BaseModel):
    """Cron 表达式验证请求模型"""
    cron_expression: str = Field(..., description="Cron 表达式")


class CronValidateResponse(BaseModel):
    """Cron 表达式验证响应模型"""
    valid: bool
    next_run_at: Optional[str] = None
    cron_expression: Optional[str] = None
    error: Optional[str] = None
