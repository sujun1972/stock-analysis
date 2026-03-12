"""
LLM提示词模板 ORM 模型

作者: Backend Team
创建时间: 2026-03-11
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, TIMESTAMP,
    ForeignKey, ARRAY, Numeric
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class LLMPromptTemplate(Base):
    """LLM提示词模板表"""

    __tablename__ = "llm_prompt_templates"

    id = Column(Integer, primary_key=True, index=True)

    # 业务标识
    business_type = Column(String(50), nullable=False, index=True, comment="业务类型")
    template_name = Column(String(100), nullable=False, comment="模板名称")
    template_key = Column(String(100), nullable=False, unique=True, index=True, comment="模板唯一标识")

    # 模板内容
    system_prompt = Column(Text, comment="系统提示词")
    user_prompt_template = Column(Text, nullable=False, comment="用户提示词模板")
    output_format = Column(Text, comment="期望的输出格式说明")

    # 变量定义
    required_variables = Column(JSONB, comment="必填变量列表（JSONB）")
    optional_variables = Column(JSONB, comment="可选变量列表（JSONB）")

    # 版本控制
    version = Column(String(20), nullable=False, comment="版本号")
    parent_template_id = Column(Integer, ForeignKey("llm_prompt_templates.id"), comment="父模板ID")

    # 状态控制
    is_active = Column(Boolean, default=True, index=True, comment="是否启用")
    is_default = Column(Boolean, default=False, comment="是否为默认模板")

    # AI提供商配置
    recommended_provider = Column(String(50), comment="推荐的AI提供商")
    recommended_model = Column(String(100), comment="推荐的模型")
    recommended_temperature = Column(Numeric(3, 2), comment="推荐的温度")
    recommended_max_tokens = Column(Integer, comment="推荐的最大token数")

    # 元信息
    description = Column(Text, comment="模板描述")
    changelog = Column(Text, comment="版本变更日志")
    tags = Column(ARRAY(String), comment="标签")

    # 性能指标
    avg_tokens_used = Column(Integer, comment="平均token消耗")
    avg_generation_time = Column(Numeric(10, 2), comment="平均生成耗时（秒）")
    success_rate = Column(Numeric(5, 2), comment="成功率（%）")
    usage_count = Column(Integer, default=0, comment="使用次数")

    # 审计字段
    created_by = Column(String(100), comment="创建人")
    updated_by = Column(String(100), comment="更新人")
    created_at = Column(TIMESTAMP, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关联关系
    parent_template = relationship(
        "LLMPromptTemplate",
        remote_side=[id],
        backref="child_templates"
    )

    history_records = relationship(
        "LLMPromptTemplateHistory",
        back_populates="template",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<LLMPromptTemplate(id={self.id}, key={self.template_key}, version={self.version})>"


class LLMPromptTemplateHistory(Base):
    """LLM提示词模板修改历史表"""

    __tablename__ = "llm_prompt_template_history"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("llm_prompt_templates.id"), nullable=False, index=True)

    # 变更内容
    change_type = Column(String(20), nullable=False, comment="变更类型")
    old_content = Column(JSONB, comment="修改前的内容")
    new_content = Column(JSONB, comment="修改后的内容")
    change_summary = Column(Text, comment="变更摘要")

    # 审计
    changed_by = Column(String(100), comment="修改人")
    changed_at = Column(TIMESTAMP, default=datetime.utcnow, index=True, comment="修改时间")
    reason = Column(Text, comment="修改原因")

    # 关联关系
    template = relationship("LLMPromptTemplate", back_populates="history_records")

    def __repr__(self):
        return f"<LLMPromptTemplateHistory(id={self.id}, template_id={self.template_id}, type={self.change_type})>"
