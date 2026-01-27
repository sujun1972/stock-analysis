"""
收益率指标计算模块
包含分组收益率、多空组合收益等
"""
import numpy as np
import pandas as pd
from typing import Dict
from loguru import logger

from ..decorators import safe_compute
from ..utils import filter_valid_pairs
from ..exceptions import InsufficientDataError


@safe_compute("分组收益率", default_value={})
def calculate_group_returns(
    predictions: np.ndarray,
    actual_returns: np.ndarray,
    n_groups: int = 5
) -> Dict[int, float]:
    """
    计算分组收益率
    将预测值分成 N 组，计算各组的平均收益率

    Args:
        predictions: 预测值
        actual_returns: 实际收益率
        n_groups: 分组数量

    Returns:
        {组号: 平均收益率} 字典
    """
    try:
        valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)
    except InsufficientDataError:
        logger.warning("计算分组收益率时数据不足")
        return {}

    # 按预测值分组
    df = pd.DataFrame({
        'pred': valid_preds,
        'ret': valid_returns
    })

    try:
        df['group'] = pd.qcut(df['pred'], q=n_groups, labels=False, duplicates='drop')
    except ValueError as e:
        logger.warning(f"分组失败: {e}，使用简单分组")
        # 使用简单的等间隔分组
        df['group'] = pd.cut(df['pred'], bins=n_groups, labels=False)

    # 计算各组平均收益
    group_returns = df.groupby('group')['ret'].mean().to_dict()

    return group_returns


@safe_compute("多空收益", default_value={'long': np.nan, 'short': np.nan, 'long_short': np.nan})
def calculate_long_short_return(
    predictions: np.ndarray,
    actual_returns: np.ndarray,
    top_pct: float = 0.2,
    bottom_pct: float = 0.2
) -> Dict[str, float]:
    """
    计算多空组合收益率
    做多预测值最高的 top_pct，做空预测值最低的 bottom_pct

    Args:
        predictions: 预测值
        actual_returns: 实际收益率
        top_pct: 做多比例
        bottom_pct: 做空比例

    Returns:
        {'long': 多头收益, 'short': 空头收益, 'long_short': 多空收益}
    """
    try:
        valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)
    except InsufficientDataError:
        logger.warning("计算多空收益时数据不足")
        return {'long': np.nan, 'short': np.nan, 'long_short': np.nan}

    # 排序
    df = pd.DataFrame({
        'pred': valid_preds,
        'ret': valid_returns
    }).sort_values('pred', ascending=False)

    # 计算多头和空头
    n_stocks = len(df)
    n_long = max(1, int(n_stocks * top_pct))
    n_short = max(1, int(n_stocks * bottom_pct))

    long_return = df.head(n_long)['ret'].mean()
    short_return = df.tail(n_short)['ret'].mean()
    long_short_return = long_return - short_return

    return {
        'long': float(long_return),
        'short': float(short_return),
        'long_short': float(long_short_return)
    }
