"""
相关性指标计算模块
包含 IC, Rank IC, IC IR 等指标
"""
import numpy as np
import pandas as pd
from scipy import stats
from loguru import logger

from ..decorators import safe_compute
from ..utils import filter_valid_pairs
from ..exceptions import InsufficientDataError


@safe_compute("IC")
def calculate_ic(
    predictions: np.ndarray,
    actual_returns: np.ndarray,
    method: str = 'pearson'
) -> float:
    """
    计算 IC (Information Coefficient)
    衡量预测值与实际收益率的相关性

    Args:
        predictions: 预测值
        actual_returns: 实际收益率
        method: 相关系数方法 ('pearson', 'spearman')

    Returns:
        IC 值
    """
    try:
        valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)
    except InsufficientDataError:
        logger.warning("计算 IC 时数据不足")
        return np.nan

    if method == 'pearson':
        ic, _ = stats.pearsonr(valid_preds, valid_returns)
    elif method == 'spearman':
        ic, _ = stats.spearmanr(valid_preds, valid_returns)
    else:
        raise ValueError(f"不支持的方法: {method}")

    return float(ic)


@safe_compute("Rank IC")
def calculate_rank_ic(
    predictions: np.ndarray,
    actual_returns: np.ndarray
) -> float:
    """
    计算 Rank IC (秩相关系数)
    使用 Spearman 相关系数，对异常值更稳健

    Args:
        predictions: 预测值
        actual_returns: 实际收益率

    Returns:
        Rank IC 值
    """
    return calculate_ic(predictions, actual_returns, method='spearman')


@safe_compute("IC IR")
def calculate_ic_ir(ic_series: pd.Series) -> float:
    """
    计算 IC IR (Information Ratio)
    IC 的均值除以 IC 的标准差

    Args:
        ic_series: IC 时间序列

    Returns:
        IC IR 值
    """
    if len(ic_series) < 2:
        return np.nan

    ic_mean = ic_series.mean()
    ic_std = ic_series.std()

    if ic_std == 0 or np.isnan(ic_std):
        return np.nan

    return float(ic_mean / ic_std)
