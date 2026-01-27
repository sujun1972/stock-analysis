"""
评估配置类
"""
from dataclasses import dataclass


@dataclass
class EvaluationConfig:
    """评估配置"""
    n_groups: int = 5
    top_pct: float = 0.2
    bottom_pct: float = 0.2
    risk_free_rate: float = 0.0
    periods_per_year: int = 252
    min_samples: int = 2
