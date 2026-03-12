"""
LLM提示词模板 Pydantic Schema

作者: Backend Team
创建时间: 2026-03-11
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator


class PromptTemplateBase(BaseModel):
    """提示词模板基础模型"""

    business_type: str = Field(..., description="业务类型")
    template_name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    template_key: str = Field(..., min_length=1, max_length=100, description="模板唯一标识")

    system_prompt: Optional[str] = Field(None, description="系统提示词")
    user_prompt_template: str = Field(..., min_length=1, description="用户提示词模板")
    output_format: Optional[str] = Field(None, description="期望的输出格式说明")

    required_variables: Optional[Dict[str, str]] = Field(default_factory=dict, description="必填变量")
    optional_variables: Optional[Dict[str, str]] = Field(default_factory=dict, description="可选变量")

    version: str = Field(..., description="版本号")
    parent_template_id: Optional[int] = Field(None, description="父模板ID")

    is_active: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否为默认模板")

    recommended_provider: Optional[str] = Field(None, description="推荐的AI提供商")
    recommended_model: Optional[str] = Field(None, description="推荐的模型")
    recommended_temperature: Optional[float] = Field(None, ge=0, le=2, description="推荐的温度")
    recommended_max_tokens: Optional[int] = Field(None, ge=100, le=128000, description="推荐的最大token数")

    description: Optional[str] = Field(None, description="模板描述")
    changelog: Optional[str] = Field(None, description="版本变更日志")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")


class PromptTemplateCreate(PromptTemplateBase):
    """创建提示词模板"""

    created_by: Optional[str] = Field(None, description="创建人")

    @validator('template_key')
    def validate_template_key(cls, v):
        """验证template_key格式（只允许字母、数字、下划线）"""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('template_key只能包含字母、数字、下划线和连字符')
        return v.lower()


class PromptTemplateUpdate(BaseModel):
    """更新提示词模板"""

    template_name: Optional[str] = Field(None, min_length=1, max_length=100)
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = Field(None, min_length=1)
    output_format: Optional[str] = None

    required_variables: Optional[Dict[str, str]] = None
    optional_variables: Optional[Dict[str, str]] = None

    is_active: Optional[bool] = None
    is_default: Optional[bool] = None

    recommended_provider: Optional[str] = None
    recommended_model: Optional[str] = None
    recommended_temperature: Optional[float] = Field(None, ge=0, le=2)
    recommended_max_tokens: Optional[int] = Field(None, ge=100, le=128000)

    description: Optional[str] = None
    changelog: Optional[str] = None
    tags: Optional[List[str]] = None

    updated_by: Optional[str] = Field(None, description="更新人")


class PromptTemplateResponse(PromptTemplateBase):
    """提示词模板响应模型"""

    id: int
    avg_tokens_used: Optional[int] = None
    avg_generation_time: Optional[float] = None
    success_rate: Optional[float] = None
    usage_count: int = 0

    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptTemplateListResponse(BaseModel):
    """提示词模板列表响应"""

    total: int
    items: List[PromptTemplateResponse]


class PromptTemplateVersionCreate(BaseModel):
    """基于现有模板创建新版本"""

    version: str = Field(..., description="新版本号")
    changelog: str = Field(..., min_length=1, description="版本变更日志")

    # 可选的修改内容
    template_name: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    output_format: Optional[str] = None
    required_variables: Optional[Dict[str, str]] = None
    optional_variables: Optional[Dict[str, str]] = None

    recommended_provider: Optional[str] = None
    recommended_model: Optional[str] = None
    recommended_temperature: Optional[float] = Field(None, ge=0, le=2)
    recommended_max_tokens: Optional[int] = Field(None, ge=100, le=128000)

    description: Optional[str] = None
    tags: Optional[List[str]] = None

    created_by: Optional[str] = Field(None, description="创建人")


class PromptTemplatePreviewRequest(BaseModel):
    """提示词预览请求"""

    variables: Dict[str, Any] = Field(..., description="变量字典")


class PromptTemplatePreviewResponse(BaseModel):
    """提示词预览响应"""

    system_prompt: Optional[str] = None
    user_prompt: str
    full_prompt: str
    missing_variables: List[str] = Field(default_factory=list, description="缺失的必填变量")
    extra_variables: List[str] = Field(default_factory=list, description="多余的变量")


class PromptTemplateStatistics(BaseModel):
    """提示词模板统计信息"""

    template_id: int
    template_name: str
    template_key: str
    version: str

    # 调用统计
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    success_rate: float = 0.0

    # 性能指标
    avg_tokens_used: Optional[float] = None
    avg_duration_sec: Optional[float] = None
    total_cost: Optional[float] = None

    # 时间范围
    last_used_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PromptTemplateHistoryResponse(BaseModel):
    """提示词模板历史记录响应"""

    id: int
    template_id: int
    change_type: str
    old_content: Optional[Dict[str, Any]] = None
    new_content: Optional[Dict[str, Any]] = None
    change_summary: Optional[str] = None
    changed_by: Optional[str] = None
    changed_at: datetime
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class BusinessTypeEnum:
    """业务类型枚举"""

    SENTIMENT_ANALYSIS = "sentiment_analysis"
    PREMARKET_ANALYSIS = "premarket_analysis"
    STRATEGY_GENERATION = "strategy_generation"

    @classmethod
    def all(cls) -> List[str]:
        return [
            cls.SENTIMENT_ANALYSIS,
            cls.PREMARKET_ANALYSIS,
            cls.STRATEGY_GENERATION
        ]


class PromptRenderError(Exception):
    """提示词渲染错误"""
    pass
