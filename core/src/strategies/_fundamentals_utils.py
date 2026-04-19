"""Fundamentals 策略共用工具

为使用 `fundamentals` 参数的选股策略提供安全除法等辅助函数，避免 6+ 策略各自重复实现。
"""

from typing import Any

import numpy as np


def safe_div(num: Any, den: Any) -> float:
    """安全除法：分母为 0 / NaN / None 返回 NaN。

    与 pandas/numpy 运算保持一致的 NaN 语义，便于后续比较（`x > y` 在 NaN 上返回 False）。
    """
    try:
        n = float(num) if num is not None else np.nan
        d = float(den) if den is not None else np.nan
        if np.isnan(n) or np.isnan(d) or d == 0:
            return np.nan
        return n / d
    except (TypeError, ValueError):
        return np.nan
