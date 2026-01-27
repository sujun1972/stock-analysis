#!/usr/bin/env python3
"""
统一配置模块

提供整个应用的配置访问入口,集成了:
- 全局应用设置 (settings.py)
- 交易规则 (trading_rules.py)
- 数据提供者配置 (providers.py)
- 数据流水线配置 (pipeline.py)
"""

# ==================== 核心配置 ====================
from .settings import (
    get_settings,
    Settings,
    DatabaseSettings,
    DataSourceSettings,
    PathSettings,
    MLSettings,
    AppSettings,
    get_database_config,
    get_data_source,
    get_models_dir,
)

# ==================== 交易规则配置 ====================
from .trading_rules import (
    TradingHours,
    T_PLUS_N,
    PriceLimitRules,
    TradingCosts,
    TradingUnits,
    StockFilterRules,
    MarketType,
    DataQualityRules,
    AdjustType,
)

# ==================== 提供者配置 ====================
from .providers import (
    ProviderConfigManager,
    get_provider_config_manager,
    get_current_provider,
    get_current_provider_config,
    get_tushare_config,
    get_akshare_config,
    TushareConfig,
    TushareErrorMessages,
    TushareFields,
    AkShareConfig,
    AkShareFields,
    AkShareNotes,
)

# ==================== 流水线配置 ====================
from .pipeline import (
    PipelineConfig,
    DEFAULT_CONFIG,
    QUICK_TRAINING_CONFIG,
    BALANCED_TRAINING_CONFIG,
    LONG_TERM_CONFIG,
    PRODUCTION_CONFIG,
    create_config,
)

# ==================== 向后兼容导出 ====================

# 获取全局设置实例
_settings = get_settings()

# 向后兼容的常量导出
DATA_PATH = str(_settings.paths.data_path)
TUSHARE_TOKEN = _settings.data_source.tushare_token
DATABASE_CONFIG = _settings.get_database_config()
DEFAULT_DATA_SOURCE = _settings.data_source.provider

# ==================== 便捷函数 ====================

def get_config_summary() -> str:
    """获取配置摘要信息"""
    settings = get_settings()
    provider_manager = get_provider_config_manager()

    lines = [
        "=" * 70,
        "配置系统摘要 (统一配置管理)",
        "=" * 70,
        "",
        "【应用配置】",
        f"  环境: {settings.app.environment}",
        f"  调试模式: {settings.app.debug}",
        f"  日志级别: {settings.app.log_level}",
        "",
        "【数据库配置】",
        f"  地址: {settings.database.user}@{settings.database.host}:{settings.database.port}",
        f"  数据库: {settings.database.database}",
        "",
        "【数据源配置】",
        f"  当前提供者: {provider_manager.get_provider_name()}",
        f"  Tushare Token: {'已配置' if provider_manager.has_tushare_token() else '未配置'}",
        f"  DeepSeek API: {'已配置' if settings.data_source.deepseek_api_key else '未配置'}",
        "",
        "【路径配置】",
        f"  数据目录: {settings.paths.data_dir}",
        f"  模型目录: {settings.paths.models_dir}",
        f"  缓存目录: {settings.paths.cache_dir}",
        f"  结果目录: {settings.paths.results_dir}",
        "",
        "【机器学习配置】",
        f"  特征版本: {settings.ml.feature_version}",
        f"  默认预测周期: {settings.ml.default_target_period}天",
        f"  默认缩放类型: {settings.ml.default_scaler_type}",
        f"  特征缓存: {'启用' if settings.ml.cache_features else '禁用'}",
        "",
        "=" * 70,
    ]

    return "\n".join(lines)


def validate_config() -> bool:
    """验证配置的完整性和正确性"""
    try:
        settings = get_settings()

        # 验证必要的配置项
        assert settings.database.host, "数据库主机地址未配置"
        assert settings.database.database, "数据库名称未配置"

        # 验证数据源配置
        provider = settings.data_source.provider
        if provider == 'tushare':
            if not settings.data_source.tushare_token:
                print("警告: 使用 Tushare 但未配置 Token")

        # 验证路径配置
        from pathlib import Path
        data_path = Path(settings.paths.data_dir)
        if not data_path.exists():
            print(f"警告: 数据目录不存在: {data_path}")

        return True

    except Exception as e:
        print(f"配置验证失败: {e}")
        return False


# ==================== 导出所有公共接口 ====================

__all__ = [
    # 核心配置
    'get_settings',
    'Settings',
    'DatabaseSettings',
    'DataSourceSettings',
    'PathSettings',
    'MLSettings',
    'AppSettings',
    'get_database_config',
    'get_data_source',
    'get_models_dir',

    # 交易规则
    'TradingHours',
    'T_PLUS_N',
    'PriceLimitRules',
    'TradingCosts',
    'TradingUnits',
    'StockFilterRules',
    'MarketType',
    'DataQualityRules',
    'AdjustType',

    # 提供者配置
    'ProviderConfigManager',
    'get_provider_config_manager',
    'get_current_provider',
    'get_current_provider_config',
    'get_tushare_config',
    'get_akshare_config',
    'TushareConfig',
    'TushareErrorMessages',
    'TushareFields',
    'AkShareConfig',
    'AkShareFields',
    'AkShareNotes',

    # 流水线配置
    'PipelineConfig',
    'DEFAULT_CONFIG',
    'QUICK_TRAINING_CONFIG',
    'BALANCED_TRAINING_CONFIG',
    'LONG_TERM_CONFIG',
    'PRODUCTION_CONFIG',
    'create_config',

    # 向后兼容
    'DATA_PATH',
    'TUSHARE_TOKEN',
    'DATABASE_CONFIG',
    'DEFAULT_DATA_SOURCE',

    # 便捷函数
    'get_config_summary',
    'validate_config',
]
