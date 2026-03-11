"""
LLM调用日志数据模型
记录所有AI模型调用的详细信息
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, Numeric, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class LLMCallLog(Base):
    """LLM调用日志模型"""
    __tablename__ = "llm_call_logs"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 调用标识
    call_id = Column(String(50), unique=True, nullable=False, index=True)

    # 业务关联
    business_type = Column(String(50), nullable=False, index=True)
    business_date = Column(Date, index=True)
    business_id = Column(String(100))

    # LLM配置
    provider = Column(String(50), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    api_base_url = Column(String(200))

    # 调用参数
    call_parameters = Column(JSONB, nullable=False)

    # 输入内容
    prompt_text = Column(Text, nullable=False)
    prompt_length = Column(Integer)
    prompt_hash = Column(String(64))

    # 输出内容
    response_text = Column(Text)
    response_length = Column(Integer)
    parsed_result = Column(JSONB)

    # 性能指标
    tokens_input = Column(Integer)
    tokens_output = Column(Integer)
    tokens_total = Column(Integer)
    cost_estimate = Column(Numeric(10, 4))

    duration_ms = Column(Integer)
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    end_time = Column(TIMESTAMP(timezone=True))

    # 状态信息
    status = Column(String(20), nullable=False, index=True)
    error_code = Column(String(50))
    error_message = Column(Text)

    # HTTP信息
    http_status_code = Column(Integer)
    request_headers = Column(JSONB)
    response_headers = Column(JSONB)

    # 元数据
    caller_service = Column(String(100))
    caller_function = Column(String(100))
    user_id = Column(String(50))
    is_scheduled = Column(Boolean, default=False)
    retry_count = Column(Integer, default=0)
    parent_call_id = Column(String(50))

    # 审计字段
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<LLMCallLog(call_id={self.call_id}, business_type={self.business_type}, provider={self.provider}, status={self.status})>"


class LLMPricingConfig(Base):
    """LLM定价配置模型"""
    __tablename__ = "llm_pricing_config"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)

    # 价格（每百万token的美元价格）
    input_price_per_million = Column(Numeric(10, 4))
    output_price_per_million = Column(Numeric(10, 4))

    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date)

    currency = Column(String(10), default='USD')
    notes = Column(Text)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<LLMPricingConfig(provider={self.provider}, model={self.model_name}, input_price={self.input_price_per_million}, output_price={self.output_price_per_million})>"
