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
        "http://localhost:3000",  # Frontend用户前端
        "http://localhost:3002",  # Admin管理后台
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

    # Redis配置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"

    # 缓存配置
    CACHE_DEFAULT_TTL: int = int(os.getenv("CACHE_DEFAULT_TTL", "300"))  # 5分钟
    CACHE_STOCK_LIST_TTL: int = int(os.getenv("CACHE_STOCK_LIST_TTL", "300"))  # 5分钟
    CACHE_DAILY_DATA_TTL: int = int(os.getenv("CACHE_DAILY_DATA_TTL", "3600"))  # 1小时
    CACHE_FEATURES_TTL: int = int(os.getenv("CACHE_FEATURES_TTL", "1800"))  # 30分钟
    CACHE_BACKTEST_TTL: int = int(os.getenv("CACHE_BACKTEST_TTL", "86400"))  # 24小时
    CACHE_MARKET_STATUS_TTL: int = int(os.getenv("CACHE_MARKET_STATUS_TTL", "60"))  # 1分钟

    @property
    def REDIS_URL(self) -> str:
        """Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # JWT认证配置
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "your-secret-key-here-please-change-in-production-use-openssl-rand-hex-32"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # 初始管理员配置（首次启动时创建）
    INITIAL_SUPER_ADMIN_EMAIL: str = os.getenv("INITIAL_SUPER_ADMIN_EMAIL", "admin@stock-analysis.com")
    INITIAL_SUPER_ADMIN_PASSWORD: str = os.getenv("INITIAL_SUPER_ADMIN_PASSWORD", "admin123456")
    INITIAL_SUPER_ADMIN_USERNAME: str = os.getenv("INITIAL_SUPER_ADMIN_USERNAME", "admin")

    # 用户配额默认值
    DEFAULT_TRIAL_BACKTEST_QUOTA: int = 5
    DEFAULT_TRIAL_ML_QUOTA: int = 2
    DEFAULT_TRIAL_MAX_STRATEGIES: int = 3
    DEFAULT_NORMAL_BACKTEST_QUOTA: int = 10
    DEFAULT_NORMAL_ML_QUOTA: int = 5
    DEFAULT_NORMAL_MAX_STRATEGIES: int = 10

    # 生产环境配置
    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """判断是否为开发环境"""
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        """判断是否为测试环境"""
        return self.ENVIRONMENT == "testing"

    @property
    def log_level(self) -> str:
        """根据环境自动设置日志级别"""
        if self.is_production:
            return "INFO"
        elif self.is_testing:
            return "WARNING"
        else:
            return "DEBUG"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
