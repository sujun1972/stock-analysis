"""
预定义策略模块

包含所有预定义的交易策略类：

价格 / 量价类：
- 动量策略 (MomentumStrategy)
- 均值回归策略 (MeanReversionStrategy)
- 多因子策略 (MultiFactorStrategy)

财务因子类（使用 fundamentals 参数）：
- Piotroski F-Score 质量策略 (PiotroskiFScoreStrategy)
- Sloan 应计策略 (SloanAccrualsStrategy)
- FCF 收益率策略 (FCFYieldStrategy)
- 研发密度策略 (RDIntensityStrategy)
- 应收账款风险策略 (AccountsReceivableRiskStrategy)
- 存货周转率策略 (InventoryTurnoverStrategy)

组合因子类（prices + fundamentals）：
- Quality × Momentum 组合策略 (QualityMomentumStrategy)

这些策略都继承自 BaseStrategy，可直接使用或通过 StrategyFactory 创建
"""

from .momentum_strategy import MomentumStrategy
from .mean_reversion_strategy import MeanReversionStrategy
from .multi_factor_strategy import MultiFactorStrategy
from .piotroski_fscore_strategy import PiotroskiFScoreStrategy
from .sloan_accruals_strategy import SloanAccrualsStrategy
from .fcf_yield_strategy import FCFYieldStrategy
from .rd_intensity_strategy import RDIntensityStrategy
from .ar_risk_strategy import AccountsReceivableRiskStrategy
from .inventory_turnover_strategy import InventoryTurnoverStrategy
from .quality_momentum_strategy import QualityMomentumStrategy

__all__ = [
    'MomentumStrategy',
    'MeanReversionStrategy',
    'MultiFactorStrategy',
    'PiotroskiFScoreStrategy',
    'SloanAccrualsStrategy',
    'FCFYieldStrategy',
    'RDIntensityStrategy',
    'AccountsReceivableRiskStrategy',
    'InventoryTurnoverStrategy',
    'QualityMomentumStrategy',
]
