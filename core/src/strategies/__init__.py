"""
交易策略模块

提供多种量化交易策略实现：
- 动量策略 (MomentumStrategy)
- 均值回归策略 (MeanReversionStrategy)
- 多因子策略 (MultiFactorStrategy)
- 策略组合器 (StrategyCombiner)

新增功能（v2.0.0）：
- 策略工厂 (StrategyFactory) - 统一的策略创建接口
- 策略加载器 (ConfigLoader, DynamicCodeLoader) - 支持从数据库加载策略
- 安全模块 (CodeSanitizer, PermissionChecker) - 多层安全防护

注意: MLStrategy 已废弃，请使用新的 ml.MLEntry 策略
详情参考: core/docs/planning/ml_system_refactoring_plan.md

使用示例（方式1 - 直接创建预定义策略）：
    from strategies import MomentumStrategy
    from backtest.backtest_engine import BacktestEngine

    # 创建策略
    strategy = MomentumStrategy(
        name='MOM20',
        config={'lookback_period': 20, 'top_n': 50}
    )

    # 生成信号
    signals = strategy.generate_signals(prices, features)

    # 回测
    engine = BacktestEngine(initial_capital=1000000)
    results = engine.backtest_long_only(signals, prices)

使用示例（方式2 - 使用策略工厂）：
    from strategies import StrategyFactory

    factory = StrategyFactory()

    # 方式1: 创建预定义策略
    strategy1 = factory.create(
        strategy_type='momentum',
        config={'lookback_period': 20, 'top_n': 50},
        name='MOM20'
    )

    # 方式2: 从配置创建策略（参数配置方案）
    strategy2 = factory.create_from_config(config_id=123)

    # 方式3: 从AI代码创建策略（AI代码生成方案）
    strategy3 = factory.create_from_code(strategy_id=456, strict_mode=True)
"""

# 基础类
from .base_strategy import BaseStrategy, StrategyConfig
from .signal_generator import SignalGenerator, SignalType

# 策略工厂
from .strategy_factory import StrategyFactory

# 预定义策略
from .predefined.momentum_strategy import MomentumStrategy
from .predefined.mean_reversion_strategy import MeanReversionStrategy
from .predefined.multi_factor_strategy import MultiFactorStrategy

# 工具类
from .strategy_combiner import StrategyCombiner

# 加载器（高级用法）
from .loaders.loader_factory import LoaderFactory
from .loaders.config_loader import ConfigLoader
from .loaders.dynamic_loader import DynamicCodeLoader

# 安全模块（高级用法）
from .security.code_sanitizer import CodeSanitizer
from .security.permission_checker import PermissionChecker
from .security.resource_limiter import ResourceLimiter
from .security.audit_logger import AuditLogger
from .security.security_config import SecurityConfig

__all__ = [
    # 基础类
    'BaseStrategy',
    'StrategyConfig',
    'SignalGenerator',
    'SignalType',

    # 策略工厂（推荐使用）
    'StrategyFactory',

    # 预定义策略
    'MomentumStrategy',
    'MeanReversionStrategy',
    'MultiFactorStrategy',

    # 工具类
    'StrategyCombiner',

    # 加载器（高级用法）
    'LoaderFactory',
    'ConfigLoader',
    'DynamicCodeLoader',

    # 安全模块（高级用法）
    'CodeSanitizer',
    'PermissionChecker',
    'ResourceLimiter',
    'AuditLogger',
    'SecurityConfig',
]

__version__ = '2.0.0'
