"""
应用配置
"""

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # 项目信息
    PROJECT_NAME: str = "Stock Analysis Backend"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # API配置
    API_PREFIX: str = "/api"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",  # React默认端口
        "http://localhost:5173",  # Vite默认端口
        "http://localhost:8080",  # Vue默认端口
        "http://localhost",
    ]

    # 数据库配置
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "timescaledb")
    DATABASE_PORT: int = int(os.getenv("DATABASE_PORT", "5432"))
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "stock_analysis")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "stock_user")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "stock_password_123")

    @property
    def DATABASE_URL(self) -> str:
        """数据库连接URL"""
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    # Tushare配置
    TUSHARE_TOKEN: str = os.getenv("TUSHARE_TOKEN", "")

    # 数据源配置
    DEFAULT_DATA_SOURCE: str = os.getenv("DATA_SOURCE", "akshare")

    # Redis配置（可选）
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
