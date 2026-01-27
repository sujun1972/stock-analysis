"""
评估模块辅助函数
"""
import numpy as np
from typing import Tuple

from .exceptions import InsufficientDataError


def filter_valid_pairs(
    predictions: np.ndarray,
    actual_returns: np.ndarray,
    min_samples: int = 2
) -> Tuple[np.ndarray, np.ndarray]:
    """
    过滤有效的预测-收益对

    Args:
        predictions: 预测值
        actual_returns: 实际收益率
        min_samples: 最小样本数

    Returns:
        过滤后的 (predictions, actual_returns)

    Raises:
        InsufficientDataError: 有效数据不足
    """
    # 移除 NaN 和 Inf
    mask = (
        ~np.isnan(predictions) &
        ~np.isnan(actual_returns) &
        ~np.isinf(predictions) &
        ~np.isinf(actual_returns)
    )

    valid_preds = predictions[mask]
    valid_returns = actual_returns[mask]

    if len(valid_preds) < min_samples:
        raise InsufficientDataError(
            f"有效数据不足: {len(valid_preds)} < {min_samples}"
        )

    return valid_preds, valid_returns
