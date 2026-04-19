"""
格式化工具函数

纯函数，无状态，供数据收集和文本格式化模块共用。
"""

import math
from datetime import date, datetime
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


# ------------------------------------------------------------------
# 日期工具
# 数据库中 trade_date / end_date 的常见两种格式：'YYYYMMDD' 与 'YYYY-MM-DD'。
# 下面两个工具统一处理，避免各 collector 重复写日期解析/计算滞后天数的样板。
# ------------------------------------------------------------------

def parse_date_loose(raw) -> Optional[date]:
    """兼容 'YYYYMMDD' / 'YYYY-MM-DD' / datetime 对象，解析失败返回 None。"""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    digits = str(raw)[:10].replace('-', '')
    if len(digits) < 8 or not digits[:8].isdigit():
        return None
    try:
        return date(int(digits[:4]), int(digits[4:6]), int(digits[6:8]))
    except ValueError:
        return None


def days_since(raw, today: Optional[date] = None) -> Optional[int]:
    """返回 raw 日期距 today（默认当天）的天数；解析失败返回 None。"""
    d = parse_date_loose(raw)
    if d is None:
        return None
    ref = today or date.today()
    return (ref - d).days


def format_date_dashed(raw) -> str:
    """把 'YYYYMMDD' 统一成 'YYYY-MM-DD'；无法解析时保留原值（去掉超过 10 位的尾部）。"""
    d = parse_date_loose(raw)
    if d is not None:
        return d.strftime('%Y-%m-%d')
    return str(raw)[:10] if raw else ''


def quantile(sorted_vals, q: float) -> Optional[float]:
    """用最近排名法取已升序排序序列的 q 分位（q ∈ [0,1]），序列为空返回 None。"""
    n = len(sorted_vals)
    if n == 0:
        return None
    idx = max(0, min(n - 1, int(round(q * (n - 1)))))
    return round(sorted_vals[idx], 2)
