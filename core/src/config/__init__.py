#!/usr/bin/env python3
"""
统一配置模块

提供整个应用的配置访问入口,集成了:
- 全局应用设置 (settings.py)
- 交易规则 (trading_rules.py)
- 数据提供者配置 (providers.py)
- 数据流水线配置 (pipeline.py)
"""

from loguru import logger

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

# ==================== 特征工程配置 ====================
from .features import (
    FeatureEngineerConfig,
    TradingDaysConfig,
    TechnicalIndicatorConfig,
    AlphaFactorConfig,
    FeatureTransformConfig,
    DEFAULT_FEATURE_CONFIG,
    QUICK_FEATURE_CONFIG,
    FULL_FEATURE_CONFIG,
    DEBUG_FEATURE_CONFIG,
    get_feature_config,
    set_feature_config,
    reset_feature_config,
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
    feature_config = get_feature_config()

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
        "【特征工程配置】",
        f"  年交易日数: {feature_config.trading_days.annual_trading_days}",
        f"  MA周期: {feature_config.technical_indicators.ma_periods}",
        f"  动量因子周期: {feature_config.alpha_factors.momentum_periods}",
        f"  数据泄漏检测: {'启用' if feature_config.enable_leak_detection else '禁用'}",
        f"  缓存统计: {'启用' if feature_config.show_cache_stats else '禁用'}",
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
                # 同时输出到stdout和logger，以便CLI和测试都能捕获
                print("警告: 使用 Tushare 但未配置 Token")
                logger.warning("使用 Tushare 但未配置 Token")

        # 验证路径配置
        from pathlib import Path
        data_path = Path(settings.paths.data_dir)
        if not data_path.exists():
            # 同时输出到stdout和logger，以便CLI和测试都能捕获
            print(f"警告: 数据目录不存在: {data_path}")
            logger.warning(f"数据目录不存在: {data_path}")

        return True

    except Exception as e:
        # 同时输出到stdout和logger，以便CLI和测试都能捕获
        print(f"配置验证失败: {e}")
        logger.error(f"配置验证失败: {e}")
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

    # 特征工程配置
    'FeatureEngineerConfig',
    'TradingDaysConfig',
    'TechnicalIndicatorConfig',
    'AlphaFactorConfig',
    'FeatureTransformConfig',
    'DEFAULT_FEATURE_CONFIG',
    'QUICK_FEATURE_CONFIG',
    'FULL_FEATURE_CONFIG',
    'DEBUG_FEATURE_CONFIG',
    'get_feature_config',
    'set_feature_config',
    'reset_feature_config',

    # 向后兼容
    'DATA_PATH',
    'TUSHARE_TOKEN',
    'DATABASE_CONFIG',
    'DEFAULT_DATA_SOURCE',

    # 便捷函数
    'get_config_summary',
    'validate_config',
]
