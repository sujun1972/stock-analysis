"""
通知模板 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, TIMESTAMP, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NotificationTemplate(Base):
    """通知模板表 - 支持 Jinja2 模板渲染"""

    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)

    # 模板标识
    template_name = Column(String(100), nullable=False, unique=True, comment="模板名称（唯一标识）")
    notification_type = Column(String(50), nullable=False, comment="通知类型")
    channel = Column(String(20), nullable=False, comment="渠道类型: email, telegram, in_app")

    # 模板内容
    subject_template = Column(Text, comment="主题/标题模板（Jinja2）")
    content_template = Column(Text, nullable=False, comment="内容模板（Jinja2）")

    # 变量说明
    available_variables = Column(
        JSONB,
        comment="可用变量列表（JSON数组，用于前端提示）"
    )

    # 示例数据（用于模板预览）
    example_data = Column(
        JSONB,
        comment="示例变量数据（用于模板预览测试）"
    )

    # 状态
    is_active = Column(Boolean, default=True, comment="是否启用")

    # 优先级
    priority = Column(Integer, default=10, comment="优先级（数字越小优先级越高）")

    # 描述
    description = Column(Text, comment="模板描述")

    # 时间戳
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # 索引
    __table_args__ = (
        Index('idx_notification_templates_type_channel', 'notification_type', 'channel'),
        Index('idx_notification_templates_active', 'is_active'),
        Index('idx_notification_templates_name', 'template_name'),
    )

    def __repr__(self):
        return f"<NotificationTemplate(id={self.id}, name='{self.template_name}', type='{self.notification_type}', channel='{self.channel}')>"
