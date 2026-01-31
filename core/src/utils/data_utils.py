"""
数据处理通用工具函数

该模块提供无外部依赖的数据处理函数，用于解耦各个模块之间的依赖关系。
所有函数都是纯函数或低耦合函数，可被features、data、strategies等模块安全引用。

功能分类：
- 数据填充：前向填充、后向填充、插值填充
- 数据验证：检查缺失值、检查数据类型、检查索引连续性
- 数据转换：标准化、归一化、分组转换
- 异常检测：IQR方法、Z-score方法、MAD方法

作者: AI Assistant
日期: 2026-01-31
版本: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Optional, Union, Tuple, List, Literal
from scipy import stats


# ==================== 数据填充函数 ====================


def forward_fill_series(
    series: pd.Series,
    limit: Optional[int] = None,
    inplace: bool = False
) -> pd.Series:
    """
    前向填充序列（从data_cleaner.py提取并增强）

    参数:
        series: 待填充的Series
        limit: 最大填充次数，None表示无限制
        inplace: 是否原地修改

    返回:
        填充后的Series

    示例:
        >>> s = pd.Series([1, np.nan, np.nan, 4])
        >>> forward_fill_series(s, limit=1)
        0    1.0
        1    1.0
        2    NaN
        3    4.0
        dtype: float64
    """
    if not inplace:
        series = series.copy()

    return series.ffill(limit=limit)


def backward_fill_series(
    series: pd.Series,
    limit: Optional[int] = None,
    inplace: bool = False
) -> pd.Series:
    """
    后向填充序列

    参数:
        series: 待填充的Series
        limit: 最大填充次数，None表示无限制
        inplace: 是否原地修改

    返回:
        填充后的Series
    """
    if not inplace:
        series = series.copy()

    return series.bfill(limit=limit)


def interpolate_series(
    series: pd.Series,
    method: Literal['linear', 'time', 'polynomial', 'spline'] = 'linear',
    order: int = 2,
    limit: Optional[int] = None,
    inplace: bool = False
) -> pd.Series:
    """
    插值填充序列

    参数:
        series: 待填充的Series
        method: 插值方法 ('linear', 'time', 'polynomial', 'spline')
        order: 多项式或样条阶数（仅用于polynomial/spline）
        limit: 最大填充的连续NaN数量
        inplace: 是否原地修改

    返回:
        填充后的Series

    示例:
        >>> s = pd.Series([1.0, np.nan, np.nan, 4.0])
        >>> interpolate_series(s, method='linear')
        0    1.0
        1    2.0
        2    3.0
        3    4.0
        dtype: float64
    """
    if not inplace:
        series = series.copy()

    if method in ['polynomial', 'spline']:
        return series.interpolate(method=method, order=order, limit=limit)
    else:
        return series.interpolate(method=method, limit=limit)


def fill_with_value(
    series: pd.Series,
    value: Union[float, int, str] = 0,
    inplace: bool = False
) -> pd.Series:
    """
    用指定值填充缺失值

    参数:
        series: 待填充的Series
        value: 填充值
        inplace: 是否原地修改

    返回:
        填充后的Series
    """
    if not inplace:
        series = series.copy()

    return series.fillna(value)


# ==================== 异常值检测函数 ====================


def detect_outliers_iqr(
    series: pd.Series,
    multiplier: float = 1.5,
    return_bounds: bool = False
) -> Union[pd.Series, Tuple[pd.Series, float, float]]:
    """
    使用IQR（四分位距）方法检测异常值

    异常值定义：
    - 下界: Q1 - multiplier * IQR
    - 上界: Q3 + multiplier * IQR

    参数:
        series: 待检测的Series
        multiplier: IQR倍数，默认1.5（标准值）
        return_bounds: 是否返回上下界

    返回:
        如果return_bounds=False: 布尔Series（True表示异常值）
        如果return_bounds=True: (布尔Series, 下界, 上界)

    示例:
        >>> s = pd.Series([1, 2, 3, 4, 5, 100])
        >>> outliers = detect_outliers_iqr(s)
        >>> outliers
        0    False
        1    False
        2    False
        3    False
        4    False
        5     True
        dtype: bool
    """
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - multiplier * IQR
    upper_bound = Q3 + multiplier * IQR

    outliers = (series < lower_bound) | (series > upper_bound)

    if return_bounds:
        return outliers, lower_bound, upper_bound
    return outliers


def detect_outliers_zscore(
    series: pd.Series,
    threshold: float = 3.0,
    return_scores: bool = False
) -> Union[pd.Series, Tuple[pd.Series, pd.Series]]:
    """
    使用Z-score方法检测异常值

    异常值定义：|z-score| > threshold

    参数:
        series: 待检测的Series
        threshold: Z-score阈值，默认3.0（标准值）
        return_scores: 是否返回z-scores

    返回:
        如果return_scores=False: 布尔Series（True表示异常值）
        如果return_scores=True: (布尔Series, z-scores Series)

    示例:
        >>> s = pd.Series([1, 2, 3, 4, 5, 100])
        >>> outliers = detect_outliers_zscore(s, threshold=2.0)
    """
    z_scores = np.abs(stats.zscore(series, nan_policy='omit'))
    outliers = pd.Series(z_scores > threshold, index=series.index)

    if return_scores:
        return outliers, pd.Series(z_scores, index=series.index)
    return outliers


def detect_outliers_mad(
    series: pd.Series,
    threshold: float = 3.5,
    return_scores: bool = False
) -> Union[pd.Series, Tuple[pd.Series, pd.Series]]:
    """
    使用MAD（中位数绝对偏差）方法检测异常值

    更稳健的异常检测方法，不受极端值影响。

    修正Z-score = 0.6745 * (x - median) / MAD
    异常值定义：|修正Z-score| > threshold

    参数:
        series: 待检测的Series
        threshold: 修正Z-score阈值，默认3.5
        return_scores: 是否返回修正z-scores

    返回:
        如果return_scores=False: 布尔Series（True表示异常值）
        如果return_scores=True: (布尔Series, 修正z-scores Series)
    """
    median = series.median()
    mad = np.median(np.abs(series - median))

    # 避免除零
    if mad == 0:
        # MAD为0说明数据几乎没有变化，使用标准差作为备用
        std = series.std()
        if std == 0:
            return pd.Series(False, index=series.index)
        modified_z_scores = 0.6745 * (series - median) / std
    else:
        modified_z_scores = 0.6745 * (series - median) / mad

    outliers = pd.Series(np.abs(modified_z_scores) > threshold, index=series.index)

    if return_scores:
        return outliers, modified_z_scores
    return outliers


# ==================== 数据验证函数 ====================


def check_missing_values(
    df: pd.DataFrame,
    threshold: float = 0.5
) -> Tuple[pd.Series, List[str]]:
    """
    检查DataFrame中的缺失值

    参数:
        df: 待检查的DataFrame
        threshold: 缺失值比例阈值（超过此值的列将被标记）

    返回:
        (缺失值比例Series, 超过阈值的列名列表)

    示例:
        >>> df = pd.DataFrame({'a': [1, 2, np.nan], 'b': [1, np.nan, np.nan]})
        >>> missing_ratio, bad_cols = check_missing_values(df, threshold=0.4)
        >>> print(bad_cols)
        ['b']
    """
    missing_ratio = df.isnull().sum() / len(df)
    bad_columns = missing_ratio[missing_ratio > threshold].index.tolist()

    return missing_ratio, bad_columns


def check_data_types(
    df: pd.DataFrame,
    expected_types: dict
) -> Tuple[bool, List[str]]:
    """
    检查DataFrame列的数据类型

    参数:
        df: 待检查的DataFrame
        expected_types: 期望的数据类型字典 {列名: 类型}

    返回:
        (是否全部匹配, 不匹配的列名列表)

    示例:
        >>> df = pd.DataFrame({'a': [1, 2], 'b': ['x', 'y']})
        >>> expected = {'a': 'int64', 'b': 'object'}
        >>> is_valid, mismatched = check_data_types(df, expected)
    """
    mismatched_columns = []

    for col, expected_type in expected_types.items():
        if col not in df.columns:
            mismatched_columns.append(f"{col} (missing)")
            continue

        actual_type = str(df[col].dtype)
        if actual_type != expected_type:
            mismatched_columns.append(f"{col} ({actual_type} != {expected_type})")

    is_valid = len(mismatched_columns) == 0
    return is_valid, mismatched_columns


def check_index_continuity(
    df: pd.DataFrame,
    freq: Optional[str] = None
) -> Tuple[bool, List[pd.Timestamp]]:
    """
    检查时间序列索引的连续性

    参数:
        df: 待检查的DataFrame（需要DatetimeIndex）
        freq: 期望的频率（如 'D', 'B', 'H'），None表示自动推断

    返回:
        (是否连续, 缺失的日期列表)

    示例:
        >>> dates = pd.date_range('2024-01-01', periods=3, freq='D')
        >>> df = pd.DataFrame({'value': [1, 2, 3]}, index=dates)
        >>> df = df.drop(df.index[1])  # 删除中间日期
        >>> is_continuous, missing = check_index_continuity(df, freq='D')
        >>> print(missing)
        [Timestamp('2024-01-02 00:00:00')]
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame索引必须是DatetimeIndex")

    if freq is None:
        freq = pd.infer_freq(df.index)
        if freq is None:
            # 无法推断频率，使用最小时间差
            freq = df.index.to_series().diff().min()

    # 生成期望的完整索引
    expected_index = pd.date_range(
        start=df.index.min(),
        end=df.index.max(),
        freq=freq
    )

    # 找出缺失的日期
    missing_dates = expected_index.difference(df.index).tolist()

    is_continuous = len(missing_dates) == 0
    return is_continuous, missing_dates


# ==================== 数据转换函数 ====================


def standardize_series(
    series: pd.Series,
    ddof: int = 1,
    inplace: bool = False
) -> pd.Series:
    """
    标准化序列（Z-score标准化）

    转换后的数据均值为0，标准差为1

    参数:
        series: 待标准化的Series
        ddof: 自由度修正（1表示样本标准差）
        inplace: 是否原地修改

    返回:
        标准化后的Series

    示例:
        >>> s = pd.Series([1, 2, 3, 4, 5])
        >>> standardized = standardize_series(s)
        >>> print(f"mean={standardized.mean():.6f}, std={standardized.std():.6f}")
        mean=0.000000, std=1.000000
    """
    if not inplace:
        series = series.copy()

    mean = series.mean()
    std = series.std(ddof=ddof)

    if std == 0:
        # 避免除零，返回全0序列
        return series - mean

    return (series - mean) / std


def normalize_series(
    series: pd.Series,
    method: Literal['minmax', 'maxabs'] = 'minmax',
    feature_range: Tuple[float, float] = (0, 1),
    inplace: bool = False
) -> pd.Series:
    """
    归一化序列

    参数:
        series: 待归一化的Series
        method: 归一化方法
            - 'minmax': 缩放到[min, max]范围
            - 'maxabs': 缩放到[-1, 1]范围（除以最大绝对值）
        feature_range: 目标范围（仅用于minmax）
        inplace: 是否原地修改

    返回:
        归一化后的Series

    示例:
        >>> s = pd.Series([1, 2, 3, 4, 5])
        >>> normalized = normalize_series(s, method='minmax', feature_range=(0, 1))
        >>> print(f"min={normalized.min()}, max={normalized.max()}")
        min=0.0, max=1.0
    """
    if not inplace:
        series = series.copy()

    if method == 'minmax':
        min_val = series.min()
        max_val = series.max()

        if max_val == min_val:
            # 避免除零，返回中点值
            return pd.Series(
                (feature_range[0] + feature_range[1]) / 2,
                index=series.index
            )

        # 归一化到[0, 1]
        normalized = (series - min_val) / (max_val - min_val)

        # 缩放到目标范围
        target_min, target_max = feature_range
        return normalized * (target_max - target_min) + target_min

    elif method == 'maxabs':
        max_abs = series.abs().max()

        if max_abs == 0:
            return series

        return series / max_abs

    else:
        raise ValueError(f"不支持的归一化方法: {method}")


def rank_series(
    series: pd.Series,
    method: Literal['average', 'min', 'max', 'first', 'dense'] = 'average',
    ascending: bool = True,
    pct: bool = False
) -> pd.Series:
    """
    对序列进行排名

    参数:
        series: 待排名的Series
        method: 排名方法（处理相同值的方式）
        ascending: 是否升序排名
        pct: 是否返回百分位排名（0-1之间）

    返回:
        排名后的Series

    示例:
        >>> s = pd.Series([3, 1, 2, 3])
        >>> rank_series(s, pct=True)
        0    0.875
        1    0.250
        2    0.500
        3    0.875
        dtype: float64
    """
    return series.rank(method=method, ascending=ascending, pct=pct)


# ==================== 辅助函数 ====================


def winsorize_series(
    series: pd.Series,
    lower: float = 0.05,
    upper: float = 0.95,
    inplace: bool = False
) -> pd.Series:
    """
    Winsorize处理（截断极端值）

    将低于lower分位数的值替换为lower分位数值，
    将高于upper分位数的值替换为upper分位数值。

    参数:
        series: 待处理的Series
        lower: 下分位数（0-1之间）
        upper: 上分位数（0-1之间）
        inplace: 是否原地修改

    返回:
        处理后的Series

    示例:
        >>> s = pd.Series([1, 2, 3, 4, 5, 100])
        >>> winsorized = winsorize_series(s, lower=0.1, upper=0.9)
    """
    if not inplace:
        series = series.copy()

    lower_bound = series.quantile(lower)
    upper_bound = series.quantile(upper)

    return series.clip(lower=lower_bound, upper=upper_bound)


def remove_outliers(
    series: pd.Series,
    method: Literal['iqr', 'zscore', 'mad'] = 'iqr',
    threshold: float = 1.5,
    replace_with: Optional[Union[float, str]] = np.nan
) -> pd.Series:
    """
    移除或替换异常值

    参数:
        series: 待处理的Series
        method: 检测方法 ('iqr', 'zscore', 'mad')
        threshold: 阈值（具体含义取决于method）
        replace_with: 替换值（None表示删除，'median'表示用中位数替换）

    返回:
        处理后的Series

    示例:
        >>> s = pd.Series([1, 2, 3, 4, 5, 100])
        >>> cleaned = remove_outliers(s, method='iqr', replace_with='median')
    """
    # 检测异常值
    if method == 'iqr':
        outliers = detect_outliers_iqr(series, multiplier=threshold)
    elif method == 'zscore':
        outliers = detect_outliers_zscore(series, threshold=threshold)
    elif method == 'mad':
        outliers = detect_outliers_mad(series, threshold=threshold)
    else:
        raise ValueError(f"不支持的检测方法: {method}")

    # 处理异常值
    result = series.copy()

    if replace_with == 'median':
        result[outliers] = series.median()
    elif replace_with == 'mean':
        result[outliers] = series.mean()
    elif replace_with is None:
        # 删除异常值
        result = result[~outliers]
    else:
        # 替换为指定值
        result[outliers] = replace_with

    return result


# ==================== 模块导出 ====================


__all__ = [
    # 数据填充
    'forward_fill_series',
    'backward_fill_series',
    'interpolate_series',
    'fill_with_value',
    # 异常检测
    'detect_outliers_iqr',
    'detect_outliers_zscore',
    'detect_outliers_mad',
    # 数据验证
    'check_missing_values',
    'check_data_types',
    'check_index_continuity',
    # 数据转换
    'standardize_series',
    'normalize_series',
    'rank_series',
    # 辅助函数
    'winsorize_series',
    'remove_outliers',
]
