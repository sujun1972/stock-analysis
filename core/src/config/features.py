#!/usr/bin/env python3
"""
特征工程配置

集中管理所有特征计算相关的配置参数,消除硬编码
"""

from typing import List
from dataclasses import dataclass, field


@dataclass
class TradingDaysConfig:
    """交易日配置"""

    annual_trading_days: int = 252
    """年交易日数（用于年化收益率、波动率等计算）"""

    epsilon: float = 1e-8
    """除法运算的最小值，防止除零错误"""


@dataclass
class TechnicalIndicatorConfig:
    """技术指标配置"""

    # 移动平均线周期
    ma_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60, 120, 250])
    """移动平均线(MA)计算周期列表"""

    # 指数移动平均线周期
    ema_periods: List[int] = field(default_factory=lambda: [12, 26, 50])
    """指数移动平均线(EMA)计算周期列表"""

    # RSI周期
    rsi_periods: List[int] = field(default_factory=lambda: [6, 12, 24])
    """相对强弱指标(RSI)计算周期列表"""

    # ATR周期
    atr_periods: List[int] = field(default_factory=lambda: [14, 28])
    """平均真实波幅(ATR)计算周期列表"""

    # CCI周期
    cci_periods: List[int] = field(default_factory=lambda: [14, 28])
    """顺势指标(CCI)计算周期列表"""

    # 布林带参数
    bollinger_period: int = 20
    """布林带周期"""

    bollinger_std_multiplier: float = 2.0
    """布林带标准差倍数"""

    # MACD参数
    macd_fast_period: int = 12
    """MACD快线周期"""

    macd_slow_period: int = 26
    """MACD慢线周期"""

    macd_signal_period: int = 9
    """MACD信号线周期"""

    # KDJ参数
    kdj_n: int = 9
    """KDJ指标N值(RSV周期)"""

    kdj_m1: int = 3
    """KDJ指标M1值(K值平滑)"""

    kdj_m2: int = 3
    """KDJ指标M2值(D值平滑)"""


@dataclass
class AlphaFactorConfig:
    """Alpha因子配置"""

    # 默认周期配置
    default_short_periods: List[int] = field(default_factory=lambda: [5, 10, 20])
    """短期周期（用于动量、反转等因子）"""

    default_medium_periods: List[int] = field(default_factory=lambda: [20, 60])
    """中期周期（用于趋势强度等因子）"""

    default_long_periods: List[int] = field(default_factory=lambda: [60, 120])
    """长期周期（用于长期动量等因子）"""

    # 动量因子周期
    momentum_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60, 120])
    """动量因子计算周期"""

    # 反转因子周期
    reversal_short_periods: List[int] = field(default_factory=lambda: [1, 3, 5])
    """短期反转因子周期"""

    reversal_long_periods: List[int] = field(default_factory=lambda: [20, 60])
    """长期反转因子周期"""

    # 波动率因子周期
    volatility_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60])
    """波动率因子计算周期"""

    # 成交量因子周期
    volume_periods: List[int] = field(default_factory=lambda: [5, 10, 20])
    """成交量因子计算周期"""

    # 趋势强度因子周期
    trend_periods: List[int] = field(default_factory=lambda: [20, 60])
    """趋势强度因子计算周期"""

    # 高低价波动率周期
    parkinson_vol_periods: List[int] = field(default_factory=lambda: [10, 20])
    """Parkinson波动率计算周期"""

    # 流动性因子周期
    liquidity_periods: List[int] = field(default_factory=lambda: [20])
    """流动性因子计算周期（Amihud指标）"""

    # 缓存配置
    cache_max_size: int = 200
    """因子计算缓存最大条目数"""

    # 列名映射
    price_columns: List[str] = field(default_factory=lambda: ['open', 'high', 'low', 'close'])
    """价格列名"""

    volume_columns: List[str] = field(default_factory=lambda: ['vol', 'volume'])
    """成交量列名（自动检测使用哪个）"""


@dataclass
class FeatureTransformConfig:
    """特征转换配置"""

    # 多时间尺度收益率周期
    return_periods: List[int] = field(default_factory=lambda: [1, 3, 5, 10, 20])
    """多时间尺度收益率计算周期"""

    # 去价格化配置
    deprice_ma_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60, 120, 250])
    """去价格化时使用的MA周期"""

    deprice_ema_periods: List[int] = field(default_factory=lambda: [12, 26, 50])
    """去价格化时使用的EMA周期"""

    deprice_atr_periods: List[int] = field(default_factory=lambda: [14, 28])
    """去价格化时使用的ATR周期"""


@dataclass
class ParallelComputingConfig:
    """并行计算配置"""

    enable_parallel: bool = True
    """是否启用并行计算"""

    n_workers: int = -1
    """
    工作进程数:
    - -1: 自动检测（CPU核心数 - 1）
    - 1: 禁用并行（串行执行）
    - >1: 指定进程数
    """

    parallel_backend: str = 'multiprocessing'
    """
    并行后端:
    - 'multiprocessing': 标准多进程（推荐）
    - 'threading': 多线程（适用于I/O密集型）
    - 'ray': Ray分布式框架（需安装ray）
    - 'dask': Dask框架（需安装dask）
    """

    chunk_size: int = 100
    """批量任务的分块大小（每个进程处理的任务数）"""

    use_shared_memory: bool = False
    """是否使用共享内存（减少数据复制，Python 3.8+）"""

    ray_address: str = None
    """Ray集群地址（None表示本地模式，'auto'表示自动检测）"""

    show_progress: bool = True
    """是否显示并行任务进度条"""

    timeout: int = 300
    """单个任务超时时间（秒），0表示不超时"""


@dataclass
class FeatureEngineerConfig:
    """特征工程器总配置"""

    trading_days: TradingDaysConfig = field(default_factory=TradingDaysConfig)
    """交易日配置"""

    technical_indicators: TechnicalIndicatorConfig = field(default_factory=TechnicalIndicatorConfig)
    """技术指标配置"""

    alpha_factors: AlphaFactorConfig = field(default_factory=AlphaFactorConfig)
    """Alpha因子配置"""

    feature_transform: FeatureTransformConfig = field(default_factory=FeatureTransformConfig)
    """特征转换配置"""

    parallel_computing: ParallelComputingConfig = field(default_factory=ParallelComputingConfig)
    """并行计算配置"""

    # 全局开关
    enable_copy_on_write: bool = True
    """是否启用Pandas Copy-on-Write模式（节省内存）"""

    enable_leak_detection: bool = False
    """是否启用数据泄漏检测（会降低性能，仅用于调试）"""

    show_cache_stats: bool = False
    """是否显示缓存统计信息"""


# ==================== 预定义配置 ====================

DEFAULT_FEATURE_CONFIG = FeatureEngineerConfig()
"""默认特征配置"""

QUICK_FEATURE_CONFIG = FeatureEngineerConfig(
    technical_indicators=TechnicalIndicatorConfig(
        ma_periods=[5, 10, 20, 60],  # 减少周期
        ema_periods=[12, 26],
        rsi_periods=[6, 12],
        atr_periods=[14],
        cci_periods=[14],
    ),
    alpha_factors=AlphaFactorConfig(
        momentum_periods=[5, 10, 20],  # 减少周期
        volatility_periods=[5, 10, 20],
        volume_periods=[5, 10],
        trend_periods=[20],
    ),
)
"""快速计算配置（减少特征数量，提高速度）"""

FULL_FEATURE_CONFIG = FeatureEngineerConfig(
    technical_indicators=TechnicalIndicatorConfig(
        ma_periods=[5, 10, 20, 30, 60, 90, 120, 250],  # 增加周期
        ema_periods=[12, 26, 50, 100],
        rsi_periods=[6, 12, 24, 48],
        atr_periods=[14, 28, 56],
        cci_periods=[14, 28, 56],
    ),
    alpha_factors=AlphaFactorConfig(
        momentum_periods=[5, 10, 20, 30, 60, 90, 120],  # 增加周期
        volatility_periods=[5, 10, 20, 30, 60],
        volume_periods=[5, 10, 20, 30],
        trend_periods=[20, 60, 120],
        parkinson_vol_periods=[10, 20, 30],
        liquidity_periods=[20, 60],
    ),
    show_cache_stats=True,
)
"""完整特征配置（最大化特征数量）"""

DEBUG_FEATURE_CONFIG = FeatureEngineerConfig(
    enable_leak_detection=True,
    show_cache_stats=True,
)
"""调试配置（启用数据泄漏检测和缓存统计）"""


# ==================== 便捷函数 ====================

_default_config: FeatureEngineerConfig = None


def get_feature_config() -> FeatureEngineerConfig:
    """
    获取全局特征配置单例

    Returns:
        FeatureEngineerConfig实例

    Example:
        from config.features import get_feature_config

        config = get_feature_config()
        ma_periods = config.technical_indicators.ma_periods
    """
    global _default_config
    if _default_config is None:
        _default_config = DEFAULT_FEATURE_CONFIG
    return _default_config


def set_feature_config(config: FeatureEngineerConfig) -> None:
    """
    设置全局特征配置

    Args:
        config: 新的特征配置

    Example:
        from config.features import set_feature_config, QUICK_FEATURE_CONFIG

        set_feature_config(QUICK_FEATURE_CONFIG)
    """
    global _default_config
    _default_config = config


def reset_feature_config() -> None:
    """重置为默认配置"""
    global _default_config
    _default_config = DEFAULT_FEATURE_CONFIG


# ==================== 测试代码 ====================

if __name__ == "__main__":
    from loguru import logger

    logger.info("\n特征配置模块测试\n")
    logger.info("=" * 60)

    # 测试默认配置
    config = get_feature_config()
    logger.info(f"\n默认配置:")
    logger.info(f"  年交易日数: {config.trading_days.annual_trading_days}")
    logger.info(f"  MA周期: {config.technical_indicators.ma_periods}")
    logger.info(f"  动量因子周期: {config.alpha_factors.momentum_periods}")
    logger.info(f"  收益率周期: {config.feature_transform.return_periods}")

    # 测试快速配置
    logger.info(f"\n快速配置:")
    logger.info(f"  MA周期: {QUICK_FEATURE_CONFIG.technical_indicators.ma_periods}")
    logger.info(f"  动量因子周期: {QUICK_FEATURE_CONFIG.alpha_factors.momentum_periods}")

    # 测试完整配置
    logger.info(f"\n完整配置:")
    logger.info(f"  MA周期: {FULL_FEATURE_CONFIG.technical_indicators.ma_periods}")
    logger.info(f"  动量因子周期: {FULL_FEATURE_CONFIG.alpha_factors.momentum_periods}")

    logger.info("\n" + "=" * 60)
    logger.info("测试完成！")
