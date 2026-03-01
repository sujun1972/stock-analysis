"""
AI配置数据访问层
"""

from typing import List, Optional
from sqlalchemy import create_engine, select, update, delete
from sqlalchemy.orm import Session
from loguru import logger

from app.core.config import settings
from app.models.ai_config import AIProviderConfig, Base


class AIConfigRepository:
    """AI配置数据访问层"""

    def __init__(self):
        # 创建数据库连接
        database_url = (
            f"postgresql://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}"
            f"@{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"
        )
        self.engine = create_engine(database_url)
        # 创建表（如果不存在）
        Base.metadata.create_all(bind=self.engine)

    def get_all(self) -> List[AIProviderConfig]:
        """获取所有AI提供商配置"""
        with Session(self.engine) as session:
            stmt = select(AIProviderConfig).order_by(AIProviderConfig.priority.desc())
            result = session.execute(stmt)
            return list(result.scalars().all())

    def get_by_provider(self, provider: str) -> Optional[AIProviderConfig]:
        """根据提供商名称获取配置"""
        with Session(self.engine) as session:
            stmt = select(AIProviderConfig).where(AIProviderConfig.provider == provider)
            result = session.execute(stmt)
            return result.scalar_one_or_none()

    def get_default(self) -> Optional[AIProviderConfig]:
        """获取默认AI提供商配置"""
        with Session(self.engine) as session:
            stmt = (
                select(AIProviderConfig)
                .where(AIProviderConfig.is_default == True)
                .where(AIProviderConfig.is_active == True)
            )
            result = session.execute(stmt)
            config = result.scalar_one_or_none()

            # 如果没有设置默认，返回第一个激活的配置
            if not config:
                stmt = (
                    select(AIProviderConfig)
                    .where(AIProviderConfig.is_active == True)
                    .order_by(AIProviderConfig.priority.desc())
                )
                result = session.execute(stmt)
                config = result.first()
                if config:
                    config = config[0]

            return config

    def create(self, config_data: dict) -> AIProviderConfig:
        """创建AI提供商配置"""
        with Session(self.engine) as session:
            # 如果设置为默认，先取消其他默认配置
            if config_data.get("is_default"):
                stmt = (
                    update(AIProviderConfig)
                    .where(AIProviderConfig.is_default == True)
                    .values(is_default=False)
                )
                session.execute(stmt)

            # 温度参数转换 (0-1 -> 0-100)
            if "temperature" in config_data:
                config_data["temperature"] = int(config_data["temperature"] * 100)

            config = AIProviderConfig(**config_data)
            session.add(config)
            session.commit()
            session.refresh(config)
            logger.info(f"创建AI配置: {config.provider}")
            return config

    def update(self, provider: str, update_data: dict) -> Optional[AIProviderConfig]:
        """更新AI提供商配置"""
        with Session(self.engine) as session:
            config = self.get_by_provider(provider)
            if not config:
                return None

            # 如果设置为默认，先取消其他默认配置
            if update_data.get("is_default"):
                stmt = (
                    update(AIProviderConfig)
                    .where(AIProviderConfig.is_default == True)
                    .values(is_default=False)
                )
                session.execute(stmt)

            # 温度参数转换
            if "temperature" in update_data:
                update_data["temperature"] = int(update_data["temperature"] * 100)

            # 移除None值
            update_data = {k: v for k, v in update_data.items() if v is not None}

            stmt = (
                update(AIProviderConfig)
                .where(AIProviderConfig.provider == provider)
                .values(**update_data)
            )
            session.execute(stmt)
            session.commit()

            logger.info(f"更新AI配置: {provider}")
            return self.get_by_provider(provider)

    def delete(self, provider: str) -> bool:
        """删除AI提供商配置"""
        with Session(self.engine) as session:
            stmt = delete(AIProviderConfig).where(AIProviderConfig.provider == provider)
            result = session.execute(stmt)
            session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"删除AI配置: {provider}")
            return deleted


# 全局实例
ai_config_repository = AIConfigRepository()
