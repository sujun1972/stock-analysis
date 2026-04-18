"""
应用配置

统一入口：`from app.core.config import settings`

- 保留向后兼容的扁平字段（DATABASE_HOST、REDIS_HOST、CACHE_*_TTL 等）
- 提供聚合 helper：`settings.db_config_dict()`（psycopg2 连接字典）
- 提供子分组 helper：`settings.database`、`settings.redis`、`settings.cache_ttl`
  —— 作为逻辑分组的只读视图，内部字段指向扁平字段以保持单一事实源
"""

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类（扁平结构，保持历史兼容性）"""

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

    def db_config_dict(self) -> dict:
        """
        返回 psycopg2 / ConnectionPoolManager 标准连接字典

        字段名：host / port / database / user / password
        """
        return {
            "host": self.DATABASE_HOST,
            "port": self.DATABASE_PORT,
            "database": self.DATABASE_NAME,
            "user": self.DATABASE_USER,
            "password": self.DATABASE_PASSWORD,
        }

    def db_config_dict_dbname(self) -> dict:
        """
        返回使用 `dbname` 字段的连接字典（psycopg2.connect() 关键字参数命名）
        """
        return {
            "host": self.DATABASE_HOST,
            "port": self.DATABASE_PORT,
            "dbname": self.DATABASE_NAME,
            "user": self.DATABASE_USER,
            "password": self.DATABASE_PASSWORD,
        }

    # Tushare配置
    TUSHARE_TOKEN: str = os.getenv("TUSHARE_TOKEN", "")

    # AI 提供商回退配置（当 ai_provider_configs 表无记录时使用）
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")

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
    CACHE_QUOTE_TRADING_TTL: int = int(os.getenv("CACHE_QUOTE_TRADING_TTL", "60"))  # 行情（交易时段）
    CACHE_QUOTE_NON_TRADING_TTL: int = int(os.getenv("CACHE_QUOTE_NON_TRADING_TTL", "3600"))  # 行情（非交易时段）
    CACHE_ANALYSIS_TTL: int = int(os.getenv("CACHE_ANALYSIS_TTL", "1800"))  # 分析结果 30 分钟
    CACHE_HOT_TTL: int = int(os.getenv("CACHE_HOT_TTL", "120"))  # 热点数据 2 分钟
    CACHE_REALTIME_TTL: int = int(os.getenv("CACHE_REALTIME_TTL", "30"))  # 实时数据 30 秒
    CACHE_MINUTE_TTL: int = int(os.getenv("CACHE_MINUTE_TTL", "60"))  # 分钟数据 1 分钟
    CACHE_STATIC_TTL: int = int(os.getenv("CACHE_STATIC_TTL", "3600"))  # 静态数据 1 小时

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

    # ── 分组视图（只读代理，便于按领域组织访问） ────────────────────
    @property
    def database(self) -> "_DatabaseView":
        return _DatabaseView(self)

    @property
    def redis(self) -> "_RedisView":
        return _RedisView(self)

    @property
    def cache_ttl(self) -> "_CacheTTLView":
        return _CacheTTLView(self)

    class Config:
        env_file = ".env"
        case_sensitive = True


class _DatabaseView:
    """数据库配置分组视图（指向 Settings 扁平字段，避免双份状态）"""
    __slots__ = ("_s",)

    def __init__(self, s: "Settings") -> None:
        self._s = s

    @property
    def host(self) -> str: return self._s.DATABASE_HOST

    @property
    def port(self) -> int: return self._s.DATABASE_PORT

    @property
    def name(self) -> str: return self._s.DATABASE_NAME

    @property
    def user(self) -> str: return self._s.DATABASE_USER

    @property
    def password(self) -> str: return self._s.DATABASE_PASSWORD

    @property
    def url(self) -> str: return self._s.DATABASE_URL

    def to_psycopg2_dict(self) -> dict:
        return self._s.db_config_dict()

    def to_psycopg2_dbname_dict(self) -> dict:
        return self._s.db_config_dict_dbname()


class _RedisView:
    """Redis 配置分组视图"""
    __slots__ = ("_s",)

    def __init__(self, s: "Settings") -> None:
        self._s = s

    @property
    def host(self) -> str: return self._s.REDIS_HOST

    @property
    def port(self) -> int: return self._s.REDIS_PORT

    @property
    def db(self) -> int: return self._s.REDIS_DB

    @property
    def password(self) -> str: return self._s.REDIS_PASSWORD

    @property
    def enabled(self) -> bool: return self._s.REDIS_ENABLED

    @property
    def url(self) -> str: return self._s.REDIS_URL


class _CacheTTLView:
    """缓存 TTL 分组视图（秒）"""
    __slots__ = ("_s",)

    def __init__(self, s: "Settings") -> None:
        self._s = s

    @property
    def default(self) -> int: return self._s.CACHE_DEFAULT_TTL

    @property
    def stock_list(self) -> int: return self._s.CACHE_STOCK_LIST_TTL

    @property
    def daily(self) -> int: return self._s.CACHE_DAILY_DATA_TTL

    @property
    def features(self) -> int: return self._s.CACHE_FEATURES_TTL

    @property
    def backtest(self) -> int: return self._s.CACHE_BACKTEST_TTL

    @property
    def market_status(self) -> int: return self._s.CACHE_MARKET_STATUS_TTL

    @property
    def quote_trading(self) -> int: return self._s.CACHE_QUOTE_TRADING_TTL

    @property
    def quote_non_trading(self) -> int: return self._s.CACHE_QUOTE_NON_TRADING_TTL

    @property
    def analysis(self) -> int: return self._s.CACHE_ANALYSIS_TTL

    @property
    def hot(self) -> int: return self._s.CACHE_HOT_TTL

    @property
    def realtime(self) -> int: return self._s.CACHE_REALTIME_TTL

    @property
    def minute(self) -> int: return self._s.CACHE_MINUTE_TTL

    @property
    def static(self) -> int: return self._s.CACHE_STATIC_TTL


# 创建全局配置实例
settings = Settings()
