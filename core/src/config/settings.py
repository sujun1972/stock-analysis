#!/usr/bin/env python3
"""
统一的应用配置管理（使用 Pydantic Settings）

提供类型安全的配置管理，支持环境变量和配置文件
"""

from typing import Optional
from functools import lru_cache
from pathlib import Path
import os

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    # 降级到传统方式
    from pydantic import BaseSettings, Field

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class DatabaseSettings(BaseSettings):
    """数据库配置"""

    host: str = Field(default="localhost", description="数据库主机地址")
    port: int = Field(default=5432, description="数据库端口")
    database: str = Field(default="stock_analysis", description="数据库名称")
    user: str = Field(default="stock_user", description="数据库用户名")
    password: str = Field(default="stock_password_123", description="数据库密码")

    class Config:
        env_prefix = "DATABASE_"
        case_sensitive = False


class DataSourceSettings(BaseSettings):
    """数据源配置"""

    provider: str = Field(default="akshare", description="默认数据源")
    tushare_token: str = Field(default="", description="Tushare API Token")
    deepseek_api_key: str = Field(default="", description="DeepSeek API Key")

    class Config:
        env_prefix = "DATA_"
        case_sensitive = False

    @property
    def has_tushare(self) -> bool:
        """是否配置了 Tushare Token"""
        return bool(self.tushare_token)


class PathSettings(BaseSettings):
    """路径配置"""

    data_dir: str = Field(default="/data", description="数据存储目录")
    models_dir: str = Field(default="/data/models/ml_models", description="模型存储目录")
    cache_dir: str = Field(default="/data/pipeline_cache", description="缓存目录")
    results_dir: str = Field(default="/data/backtest_results", description="回测结果目录")

    class Config:
        env_prefix = "PATH_"
        case_sensitive = False

    def get_data_path(self) -> Path:
        """获取数据目录路径"""
        return Path(self.data_dir)

    def get_models_path(self) -> Path:
        """获取模型目录路径"""
        path = Path(self.models_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_cache_path(self) -> Path:
        """获取缓存目录路径"""
        path = Path(self.cache_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


class MLSettings(BaseSettings):
    """机器学习配置"""

    default_target_period: int = Field(default=5, description="默认预测周期（天）")
    default_scaler_type: str = Field(default="robust", description="默认特征缩放类型")
    default_train_ratio: float = Field(default=0.7, description="默认训练集比例")
    default_valid_ratio: float = Field(default=0.15, description="默认验证集比例")
    cache_features: bool = Field(default=True, description="是否缓存特征")
    feature_version: str = Field(default="v2.0", description="特征版本号")

    class Config:
        env_prefix = "ML_"
        case_sensitive = False


class AppSettings(BaseSettings):
    """应用配置"""

    environment: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=True, description="调试模式")
    log_level: str = Field(default="INFO", description="日志级别")
    api_host: str = Field(default="0.0.0.0", description="API 服务器地址")
    api_port: int = Field(default=8000, description="API 服务器端口")

    class Config:
        env_prefix = "APP_"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment.lower() == "development"


class Settings(BaseSettings):
    """
    统一的应用配置类

    自动从环境变量和 .env 文件加载配置
    支持类型验证和默认值
    """

    # 子配置
    database: DatabaseSettings = DatabaseSettings()
    data_source: DataSourceSettings = DataSourceSettings()
    paths: PathSettings = PathSettings()
    ml: MLSettings = MLSettings()
    app: AppSettings = AppSettings()

    class Config:
        env_file = str(ENV_FILE) if ENV_FILE.exists() else None
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_database_config(self) -> dict:
        """
        获取数据库配置字典（兼容旧代码）

        Returns:
            数据库配置字典
        """
        return {
            "host": self.database.host,
            "port": self.database.port,
            "database": self.database.database,
            "user": self.database.user,
            "password": self.database.password,
        }

    def display_config(self) -> str:
        """
        显示当前配置（隐藏敏感信息）

        Returns:
            配置摘要字符串
        """
        lines = [
            "=" * 60,
            "当前配置摘要",
            "=" * 60,
            f"环境: {self.app.environment}",
            f"数据库: {self.database.user}@{self.database.host}:{self.database.port}/{self.database.database}",
            f"数据源: {self.data_source.provider}",
            f"Tushare: {'已配置' if self.data_source.has_tushare else '未配置'}",
            f"模型目录: {self.paths.models_dir}",
            f"缓存目录: {self.paths.cache_dir}",
            f"特征版本: {self.ml.feature_version}",
            f"调试模式: {self.app.debug}",
            "=" * 60,
        ]
        return "\n".join(lines)


@lru_cache()
def get_settings() -> Settings:
    """
    获取全局配置单例

    使用 @lru_cache 确保全局只有一个配置实例

    Returns:
        Settings 实例

    Example:
        from config.settings import get_settings

        settings = get_settings()
        db_config = settings.get_database_config()
    """
    return Settings()


# ==================== 便捷函数 ====================

def get_database_config() -> dict:
    """
    获取数据库配置（便捷函数）

    Returns:
        数据库配置字典
    """
    return get_settings().get_database_config()


def get_data_source() -> str:
    """
    获取当前数据源

    Returns:
        数据源名称
    """
    return get_settings().data_source.provider


def get_models_dir() -> Path:
    """
    获取模型存储目录

    Returns:
        模型目录路径
    """
    return get_settings().paths.get_models_path()


# ==================== 向后兼容 ====================

# 保持与旧代码的兼容性
DATABASE_CONFIG = get_database_config()
DEFAULT_DATA_SOURCE = get_data_source()


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("\n测试配置管理模块\n")

    settings = get_settings()
    print(settings.display_config())

    print("\n测试配置访问:")
    print(f"  数据库主机: {settings.database.host}")
    print(f"  数据源: {settings.data_source.provider}")
    print(f"  模型目录: {settings.paths.models_dir}")
    print(f"  是否生产环境: {settings.app.is_production}")

    print("\n测试单例模式:")
    settings2 = get_settings()
    assert settings is settings2, "应该返回同一实例"
    print("  ✓ 单例模式正常工作")

    print("\n✅ 配置管理模块测试通过")
