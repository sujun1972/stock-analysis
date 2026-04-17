"""
格式化工具函数

纯函数，无状态，供数据收集和文本格式化模块共用。
"""

import math
from typing import Optional


def is_nan(val) -> bool:
    try:
        return math.isnan(float(val))
    except (TypeError, ValueError):
        return False


def safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def fmt(val, decimals: int = 2) -> str:
    if val is None:
        return 'N/A'
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 'N/A'
        return f"{f:.{decimals}f}"
    except (TypeError, ValueError):
        return str(val)


def fmt_pe(val) -> str:
    """PE-TTM 专用：亏损时 Tushare 返回 NaN，显示为"亏损/负值"。"""
    if val is None:
        return 'N/A'
    try:
        f = float(val)
        if math.isnan(f):
            return '亏损/负值'
        if math.isinf(f):
            return 'N/A'
        return f"{f:.2f}"
    except (TypeError, ValueError):
        return str(val)


def fmt_amount(val) -> str:
    """格式化成交额（单位：元），自动换算万元/亿元。"""
    if val is None:
        return 'N/A'
    try:
        v = float(val)
        if math.isnan(v):
            return 'N/A'
    except (TypeError, ValueError):
        return 'N/A'
    if v >= 1e8:
        return f"{v / 1e8:.2f} 亿元"
    if v >= 1e4:
        return f"{v / 1e4:.2f} 万元"
    return f"{v:.2f} 元"


def fmt_wan(val) -> str:
    """格式化万元单位的数值（市值等），自动换算亿元。"""
    if val is None:
        return 'N/A'
    try:
        v = float(val)
        if math.isnan(v):
            return 'N/A'
    except (TypeError, ValueError):
        return 'N/A'
    if v >= 1e4:
        return f"{v / 1e4:.2f} 亿元"
    return f"{v:,.0f} 万元"


def fmt_flow(val) -> str:
    """格式化资金流向金额，输入单位为万元（moneyflow_stock_dc.net_amount）。"""
    if val is None:
        return 'N/A'
    try:
        v = float(val)
        if math.isnan(v):
            return 'N/A'
    except (TypeError, ValueError):
        return 'N/A'
    sign = '+' if v >= 0 else ''
    if abs(v) >= 10000:
        return f"{sign}{v / 10000:.2f} 亿元"
    return f"{sign}{v:.2f} 万元"


def fmt_vol(val) -> str:
    """格式化成交量（输入为股数），自动换算万股/亿股。"""
    if val is None:
        return 'N/A'
    try:
        v = float(val)
        if math.isnan(v):
            return 'N/A'
    except (TypeError, ValueError):
        return 'N/A'
    if v >= 1e8:
        return f"{v / 1e8:.2f}亿股"
    if v >= 1e4:
        return f"{v / 1e4:.0f}万股"
    return f"{v:.0f}股"
