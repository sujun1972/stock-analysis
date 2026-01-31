"""
Alpha因子库（量化选股因子）- 向后兼容层

⚠️ 重要提示: 本文件已重构为模块化结构
新代码应使用: from src.features.alpha import AlphaFactors
旧代码仍可使用: from src.features.alpha_factors import AlphaFactors（向后兼容）

模块化结构:
    src/features/alpha/
    ├── __init__.py              # 统一接口（推荐使用）
    ├── base.py                  # 基础类
    ├── momentum.py              # 动量因子
    ├── reversal.py              # 反转因子
    ├── volatility.py            # 波动率因子
    ├── volume.py                # 成交量因子
    ├── trend.py                 # 趋势因子
    └── liquidity.py             # 流动性因子

使用示例（推荐新方式）:
    >>> from src.features.alpha import AlphaFactors
    >>> af = AlphaFactors(price_df)
    >>> result = af.add_all_alpha_factors()

使用示例（向后兼容旧方式）:
    >>> from src.features.alpha_factors import AlphaFactors  # 仍然有效
    >>> af = AlphaFactors(price_df)
    >>> result = af.add_all_alpha_factors()

模块化使用（新功能）:
    >>> from src.features.alpha import MomentumFactorCalculator
    >>> momentum = MomentumFactorCalculator(price_df)
    >>> result = momentum.calculate_all()
"""

# 向后兼容：重新导出所有公共接口
from src.features.alpha import (
    # 基础类
    FactorCache,
    FactorConfig,
    BaseFactorCalculator,

    # 因子计算器
    MomentumFactorCalculator,
    ReversalFactorCalculator,
    VolatilityFactorCalculator,
    VolumeFactorCalculator,
    TrendFactorCalculator,
    LiquidityFactorCalculator,

    # 聚合类（主要接口）
    AlphaFactors,

    # 便捷函数
    calculate_all_alpha_factors,
    calculate_momentum_factors,
    calculate_reversal_factors,
)


# 公开导出（保持与原模块完全一致）
__all__ = [
    # 基础类
    'FactorCache',
    'FactorConfig',
    'BaseFactorCalculator',

    # 因子计算器
    'MomentumFactorCalculator',
    'ReversalFactorCalculator',
    'VolatilityFactorCalculator',
    'VolumeFactorCalculator',
    'TrendFactorCalculator',
    'LiquidityFactorCalculator',

    # 聚合类（向后兼容）
    'AlphaFactors',

    # 便捷函数
    'calculate_all_alpha_factors',
    'calculate_momentum_factors',
    'calculate_reversal_factors',
]
