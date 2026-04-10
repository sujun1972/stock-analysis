"""
AI配置相关的Pydantic模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class AIProviderConfigBase(BaseModel):
    """AI提供商配置基础模型"""

    provider: str = Field(..., description="提供商名称 (deepseek, gemini, openai等)")
    display_name: str = Field(..., description="显示名称")
    api_key: str = Field(..., description="API密钥")
    api_base_url: Optional[str] = Field(None, description="API基础URL")
    model_name: Optional[str] = Field(None, description="模型名称")
    max_tokens: int = Field(8000, ge=1000, le=128000, description="最大token数")
    temperature: float = Field(0.7, ge=0, le=1, description="温度参数 (0-1)")
    is_active: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否为默认提供商")
    priority: int = Field(0, description="优先级")
    rate_limit: int = Field(10, ge=1, le=1000, description="每分钟请求限制")
    timeout: int = Field(60, ge=10, le=300, description="请求超时时间(秒)")
    description: Optional[str] = Field(None, description="描述信息")


class AIProviderConfigCreate(AIProviderConfigBase):
    """创建AI提供商配置"""
    pass


class AIProviderConfigUpdate(BaseModel):
    """更新AI提供商配置"""

    display_name: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    model_name: Optional[str] = None
    max_tokens: Optional[int] = Field(None, ge=1000, le=128000)
    temperature: Optional[float] = Field(None, ge=0, le=1)
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    priority: Optional[int] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=1000)
    timeout: Optional[int] = Field(None, ge=10, le=300)
    description: Optional[str] = None


class AIProviderConfigResponse(AIProviderConfigBase):
    """AI提供商配置响应模型"""

    id: int
    api_key: str = Field(..., description="脱敏后的API密钥")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @validator('api_key', pre=False, always=True)
    def mask_api_key(cls, v):
        """脱敏API密钥"""
        if not v:
            return ""
        if len(v) <= 8:
            return "*" * len(v)
        return f"{v[:4]}{'*' * (len(v) - 8)}{v[-4:]}"


class AIStrategyGenerateRequest(BaseModel):
    """AI策略生成请求模型"""

    strategy_requirement: str = Field(..., min_length=10, description="策略需求描述")
    strategy_type: Optional[str] = Field("entry", description="策略类型：entry / exit / stock_selection")
    provider: Optional[str] = Field(None, description="指定AI提供商，不指定则使用默认")
    use_custom_prompt: bool = Field(False, description="是否使用自定义提示词模板")
    custom_prompt_template: Optional[str] = Field(None, description="自定义提示词模板")


class AIStrategyGenerateResponse(BaseModel):
    """AI策略生成响应模型"""

    success: bool = Field(..., description="是否成功")
    strategy_code: Optional[str] = Field(None, description="生成的策略代码")
    strategy_metadata: Optional[dict] = Field(None, description="策略元信息")
    provider_used: str = Field(..., description="使用的AI提供商")
    error_message: Optional[str] = Field(None, description="错误信息")
    tokens_used: Optional[int] = Field(None, description="使用的token数")
    generation_time: Optional[float] = Field(None, description="生成耗时(秒)")
