"""
AI配置数据模型
用于管理AI服务提供商的配置信息
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class AIProviderConfig(Base):
    """AI提供商配置模型"""

    __tablename__ = "ai_provider_configs"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), unique=True, nullable=False, comment="提供商名称 (deepseek, gemini, openai等)")
    display_name = Column(String(100), nullable=False, comment="显示名称")
    api_key = Column(String(500), nullable=False, comment="API密钥 (加密存储)")
    api_base_url = Column(String(200), nullable=True, comment="API基础URL")
    model_name = Column(String(100), nullable=True, comment="模型名称")
    max_tokens = Column(Integer, default=8000, comment="最大token数")
    temperature = Column(Integer, default=70, comment="温度参数 (0-100, 存储时*100)")
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_default = Column(Boolean, default=False, comment="是否为默认提供商")
    priority = Column(Integer, default=0, comment="优先级 (数字越大优先级越高)")
    rate_limit = Column(Integer, default=10, comment="每分钟请求限制")
    timeout = Column(Integer, default=60, comment="请求超时时间(秒)")
    description = Column(Text, nullable=True, comment="描述信息")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<AIProviderConfig(provider='{self.provider}', display_name='{self.display_name}', is_active={self.is_active})>"
