"""
Celery任务执行历史模型
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class CeleryTaskHistory(Base):
    """Celery任务执行历史"""

    __tablename__ = "celery_task_history"

    id = Column(Integer, primary_key=True, index=True)

    # 任务标识
    celery_task_id = Column(String(255), nullable=False, unique=True, index=True, comment="Celery任务ID")
    task_name = Column(String(255), nullable=False, comment="Celery任务名称")
    display_name = Column(String(255), comment="用户友好的显示名称")
    task_type = Column(String(50), index=True, comment="任务类型")

    # 用户信息
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True, comment="执行任务的用户ID")

    # 任务状态
    status = Column(String(20), nullable=False, default="pending", index=True, comment="任务状态")
    progress = Column(Integer, default=0, comment="进度 0-100")

    # 时间信息
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True, comment="任务创建时间")
    started_at = Column(DateTime, comment="任务开始执行时间")
    completed_at = Column(DateTime, index=True, comment="任务完成时间")
    duration_ms = Column(Integer, comment="执行耗时（毫秒）")

    # 结果信息
    result = Column(JSON, comment="任务执行结果")
    error = Column(Text, comment="错误信息")

    # Worker信息
    worker = Column(String(255), comment="执行任务的Worker")

    # 任务参数和元数据
    params = Column(JSON, comment="任务参数")
    task_metadata = Column('metadata', JSON, comment="其他元数据")

    # 关系
    user = relationship("User", backref="task_history")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "celery_task_id": self.celery_task_id,
            "task_name": self.task_name,
            "display_name": self.display_name,
            "task_type": self.task_type,
            "user_id": self.user_id,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "result": self.result,
            "error": self.error,
            "worker": self.worker,
            "params": self.params,
            "metadata": self.task_metadata
        }

    def __repr__(self):
        return f"<CeleryTaskHistory(id={self.id}, task_name={self.task_name}, status={self.status})>"
