"""
缺失值处理器 - 处理股票数据中的缺失值

功能：
- 缺失值检测和统计
- 前向填充/后向填充
- 线性插值/时间加权插值
- 移动平均填充
- 生成缺失值分析报告

作者: AI Assistant
日期: 2026-01-30
"""

import pandas as pd
import numpy as np
from typing import Optional, Literal, Dict, List, Tuple, Union, Any
from loguru import logger

from src.utils.data_utils import (
    forward_fill_series,
    backward_fill_series,
    interpolate_series,
    fill_with_value
)


class MissingHandler:
    """
    缺失值处理器 - 智能处理股票数据缺失值

    支持的填充方法：
    1. 前向填充 (ffill) - 用前一个有效值填充
    2. 后向填充 (bfill) - 用后一个有效值填充
    3. 线性插值 (linear) - 线性插值
    4. 时间插值 (time) - 基于时间的插值
    5. 样条插值 (spline) - 平滑曲线插值
    6. 移动平均 (rolling_mean) - 用移动平均填充
    7. 删除 (drop) - 删除包含缺失值的行

    用途：
    - 数据预处理
    - 特征工程前的数据清洗
    - 回测数据准备
    """

    def __init__(self, df: pd.DataFrame):
        """
        初始化缺失值处理器

        参数：
            df: 待处理的DataFrame
        """
        self.df = df.copy()
        self.original_shape = df.shape

        logger.debug(
            f"初始化缺失值处理器: 形状={self.original_shape}, "
            f"缺失值={self.df.isnull().sum().sum()}"
        )

    def detect_missing(self) -> Dict[str, Any]:
        """
        检测缺失值并生成统计报告

        返回：
            缺失值统计字典
        """
        total_cells = self.df.size
        total_missing = self.df.isnull().sum().sum()
        missing_rate = (total_missing / total_cells) * 100

        # 各列缺失统计
        column_stats = {}
        for col in self.df.columns:
            missing_count = self.df[col].isnull().sum()
            if missing_count > 0:
                column_stats[col] = {
                    'count': int(missing_count),
                    'rate': round((missing_count / len(self.df)) * 100, 2),
                    'first_missing_index': self.df[self.df[col].isnull()].index[0] if missing_count > 0 else None,
                    'last_missing_index': self.df[self.df[col].isnull()].index[-1] if missing_count > 0 else None
                }

        # 各行缺失统计
        rows_with_missing = (self.df.isnull().sum(axis=1) > 0).sum()

        stats = {
            'total_cells': int(total_cells),
            'total_missing': int(total_missing),
            'missing_rate': round(missing_rate, 2),
            'rows_with_missing': int(rows_with_missing),
            'rows_with_missing_rate': round((rows_with_missing / len(self.df)) * 100, 2),
            'columns_with_missing': len(column_stats),
            'column_stats': column_stats
        }

        logger.info(
            f"缺失值检测: 总缺失={total_missing} ({missing_rate:.2f}%), "
            f"受影响行={rows_with_missing}, 受影响列={len(column_stats)}"
        )

        return stats

    def get_missing_patterns(self) -> Dict[str, List]:
        """
        分析缺失值模式

        返回：
            缺失模式字典
        """
        patterns = {
            'consecutive_missing': {},  # 连续缺失段
            'isolated_missing': {},     # 孤立缺失点
            'leading_missing': {},      # 前导缺失
            'trailing_missing': {}      # 尾部缺失
        }

        for col in self.df.columns:
            if self.df[col].isnull().any():
                missing_mask = self.df[col].isnull()

                # 连续缺失段
                consecutive = []
                in_gap = False
                gap_start = None

                for idx, is_missing in missing_mask.items():
                    if is_missing and not in_gap:
                        in_gap = True
                        gap_start = idx
                    elif not is_missing and in_gap:
                        in_gap = False
                        gap_length = len(pd.date_range(gap_start, idx, freq='D')) - 1
                        if gap_length > 1:  # 只记录连续2天以上的
                            consecutive.append((gap_start, idx, gap_length))

                if consecutive:
                    patterns['consecutive_missing'][col] = consecutive

                # 前导缺失
                if missing_mask.iloc[0]:
                    first_valid_idx = self.df[col].first_valid_index()
                    if first_valid_idx:
                        leading_count = self.df.index.get_loc(first_valid_idx)
                        patterns['leading_missing'][col] = leading_count

                # 尾部缺失
                if missing_mask.iloc[-1]:
                    last_valid_idx = self.df[col].last_valid_index()
                    if last_valid_idx:
                        trailing_count = len(self.df) - self.df.index.get_loc(last_valid_idx) - 1
                        patterns['trailing_missing'][col] = trailing_count

        logger.debug(f"缺失模式分析完成: {patterns}")

        return patterns

    # ==================== 填充方法 ====================

    def fill_forward(
        self,
        columns: List[str] = None,
        limit: int = None
    ) -> pd.DataFrame:
        """
        前向填充（用前一个有效值填充）

        参数：
            columns: 要填充的列（None表示所有列）
            limit: 最大连续填充数量（None表示无限制）

        返回：
            填充后的DataFrame
        """
        df_filled = self.df.copy()
        cols = columns if columns else self.df.columns

        for col in cols:
            if col in df_filled.columns:
                # 使用通用工具函数
                df_filled[col] = forward_fill_series(df_filled[col], limit=limit)

        filled_count = self.df.isnull().sum().sum() - df_filled.isnull().sum().sum()
        logger.info(f"前向填充完成: 填充={filled_count}个缺失值")

        return df_filled

    def fill_backward(
        self,
        columns: List[str] = None,
        limit: int = None
    ) -> pd.DataFrame:
        """
        后向填充（用后一个有效值填充）

        参数：
            columns: 要填充的列
            limit: 最大连续填充数量

        返回：
            填充后的DataFrame
        """
        df_filled = self.df.copy()
        cols = columns if columns else self.df.columns

        for col in cols:
            if col in df_filled.columns:
                # 使用通用工具函数
                df_filled[col] = backward_fill_series(df_filled[col], limit=limit)

        filled_count = self.df.isnull().sum().sum() - df_filled.isnull().sum().sum()
        logger.info(f"后向填充完成: 填充={filled_count}个缺失值")

        return df_filled

    def interpolate(
        self,
        method: Literal['linear', 'time', 'spline', 'polynomial'] = 'linear',
        columns: List[str] = None,
        order: int = 2,
        limit: int = None
    ) -> pd.DataFrame:
        """
        插值填充

        参数：
            method: 插值方法
                - 'linear': 线性插值（默认）
                - 'time': 基于时间的插值（需要DatetimeIndex）
                - 'spline': 样条插值（需指定order）
                - 'polynomial': 多项式插值（需指定order）
            columns: 要填充的列
            order: 样条/多项式阶数（默认2）
            limit: 最大连续插值数量

        返回：
            填充后的DataFrame
        """
        df_filled = self.df.copy()
        cols = columns if columns else self.df.columns

        for col in cols:
            if col not in df_filled.columns:
                continue

            try:
                # 使用通用工具函数
                if method in ['spline', 'polynomial']:
                    df_filled[col] = interpolate_series(
                        df_filled[col],
                        method=method,
                        order=order,
                        limit=limit
                    )
                else:
                    # 使用通用工具函数
                    df_filled[col] = interpolate_series(
                        df_filled[col],
                        method=method,
                        limit=limit
                    )
            except Exception as e:
                logger.warning(f"插值失败 [{col}]: {e}，使用线性插值")
                # 使用通用工具函数
                df_filled[col] = interpolate_series(df_filled[col], method='linear', limit=limit)

        filled_count = self.df.isnull().sum().sum() - df_filled.isnull().sum().sum()
        logger.info(f"插值填充完成 ({method}): 填充={filled_count}个缺失值")

        return df_filled

    def fill_with_mean(
        self,
        columns: List[str] = None,
        window: int = None
    ) -> pd.DataFrame:
        """
        用均值填充缺失值

        参数：
            columns: 要填充的列
            window: 滚动窗口大小（None表示全局均值）

        返回：
            填充后的DataFrame
        """
        df_filled = self.df.copy()
        cols = columns if columns else self.df.columns

        for col in cols:
            if col not in df_filled.columns:
                continue

            if window:
                # 滚动窗口均值
                rolling_mean = df_filled[col].rolling(window=window, center=True, min_periods=1).mean()
                df_filled[col] = df_filled[col].fillna(rolling_mean)
            else:
                # 全局均值
                df_filled[col] = df_filled[col].fillna(df_filled[col].mean())

        filled_count = self.df.isnull().sum().sum() - df_filled.isnull().sum().sum()
        logger.info(f"均值填充完成 (window={window}): 填充={filled_count}个缺失值")

        return df_filled

    def fill_with_value(
        self,
        value: Union[float, Dict[str, float]],
        columns: List[str] = None
    ) -> pd.DataFrame:
        """
        用指定值填充

        参数：
            value: 填充值（可以是标量或字典）
            columns: 要填充的列

        返回：
            填充后的DataFrame
        """
        df_filled = self.df.copy()

        if isinstance(value, dict):
            # 字典模式：为不同列指定不同值
            for col, val in value.items():
                if col in df_filled.columns:
                    df_filled[col] = df_filled[col].fillna(val)
        else:
            # 标量模式：所有列用同一个值
            cols = columns if columns else self.df.columns
            for col in cols:
                if col in df_filled.columns:
                    df_filled[col] = df_filled[col].fillna(value)

        filled_count = self.df.isnull().sum().sum() - df_filled.isnull().sum().sum()
        logger.info(f"指定值填充完成: 填充={filled_count}个缺失值")

        return df_filled

    def drop_missing(
        self,
        how: Literal['any', 'all'] = 'any',
        subset: List[str] = None,
        threshold: int = None
    ) -> pd.DataFrame:
        """
        删除包含缺失值的行

        参数：
            how: 删除策略
                - 'any': 只要有缺失值就删除（默认）
                - 'all': 所有值都缺失才删除
            subset: 只考虑这些列的缺失值
            threshold: 非缺失值数量阈值（至少有threshold个非缺失值才保留）

        返回：
            删除缺失行后的DataFrame
        """
        # pandas不能同时使用how和thresh参数
        if threshold is not None:
            df_dropped = self.df.dropna(subset=subset, thresh=threshold)
        else:
            df_dropped = self.df.dropna(how=how, subset=subset)

        removed_rows = len(self.df) - len(df_dropped)
        removed_pct = (removed_rows / len(self.df)) * 100

        logger.info(f"删除缺失行: 删除={removed_rows}行 ({removed_pct:.2f}%)")

        return df_dropped

    # ==================== 智能填充 ====================

    def smart_fill(
        self,
        columns: List[str] = None,
        leading_method: Literal['bfill', 'drop'] = 'bfill',
        trailing_method: Literal['ffill', 'drop'] = 'ffill',
        middle_method: Literal['interpolate', 'ffill'] = 'interpolate',
        max_gap: int = 5
    ) -> pd.DataFrame:
        """
        智能填充：根据缺失值位置选择不同策略

        策略：
        - 前导缺失：用后向填充或删除
        - 尾部缺失：用前向填充或删除
        - 中间缺失：用插值或前向填充
        - 大间隔（>max_gap）：保留为NaN或删除

        参数：
            columns: 要填充的列
            leading_method: 前导缺失处理方法
            trailing_method: 尾部缺失处理方法
            middle_method: 中间缺失处理方法
            max_gap: 最大允许间隔天数

        返回：
            智能填充后的DataFrame
        """
        df_filled = self.df.copy()
        cols = columns if columns else self.df.columns

        patterns = self.get_missing_patterns()

        for col in cols:
            if col not in df_filled.columns or not df_filled[col].isnull().any():
                continue

            # 处理前导缺失
            if col in patterns['leading_missing']:
                if leading_method == 'bfill':
                    first_valid_idx = df_filled[col].first_valid_index()
                    df_filled.loc[:first_valid_idx, col] = df_filled[col].bfill()
                # drop在最后统一处理

            # 处理尾部缺失
            if col in patterns['trailing_missing']:
                if trailing_method == 'ffill':
                    last_valid_idx = df_filled[col].last_valid_index()
                    df_filled.loc[last_valid_idx:, col] = df_filled[col].ffill()

            # 处理中间缺失（小间隔）
            if middle_method == 'interpolate':
                df_filled[col] = df_filled[col].interpolate(method='linear', limit=max_gap)
            elif middle_method == 'ffill':
                df_filled[col] = df_filled[col].ffill(limit=max_gap)

        filled_count = self.df.isnull().sum().sum() - df_filled.isnull().sum().sum()
        remaining_missing = df_filled.isnull().sum().sum()

        logger.info(
            f"智能填充完成: 填充={filled_count}个缺失值, "
            f"剩余={remaining_missing}个缺失值"
        )

        return df_filled

    def handle_missing(
        self,
        method: Literal['ffill', 'bfill', 'interpolate', 'mean', 'drop', 'smart'] = 'smart',
        columns: List[str] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        统一的缺失值处理接口

        参数：
            method: 处理方法
            columns: 要处理的列
            **kwargs: 传递给具体方法的参数

        返回：
            处理后的DataFrame
        """
        if method == 'ffill':
            return self.fill_forward(columns, **kwargs)
        elif method == 'bfill':
            return self.fill_backward(columns, **kwargs)
        elif method == 'interpolate':
            return self.interpolate(columns=columns, **kwargs)
        elif method == 'mean':
            return self.fill_with_mean(columns, **kwargs)
        elif method == 'drop':
            return self.drop_missing(**kwargs)
        elif method == 'smart':
            return self.smart_fill(columns, **kwargs)
        else:
            logger.error(f"未知的处理方法: {method}")
            return self.df.copy()

    def get_fill_report(self, df_filled: pd.DataFrame) -> Dict[str, Any]:
        """
        生成填充报告

        参数：
            df_filled: 填充后的DataFrame

        返回：
            填充报告字典
        """
        original_missing = self.df.isnull().sum().sum()
        filled_missing = df_filled.isnull().sum().sum()
        filled_count = original_missing - filled_missing

        report = {
            'original_shape': self.original_shape,
            'filled_shape': df_filled.shape,
            'original_missing': int(original_missing),
            'remaining_missing': int(filled_missing),
            'filled_count': int(filled_count),
            'fill_rate': round((filled_count / original_missing) * 100, 2) if original_missing > 0 else 100.0,
            'by_column': {}
        }

        # 各列填充统计
        for col in self.df.columns:
            if col in df_filled.columns:
                original = self.df[col].isnull().sum()
                remaining = df_filled[col].isnull().sum()

                if original > 0:
                    report['by_column'][col] = {
                        'original_missing': int(original),
                        'remaining_missing': int(remaining),
                        'filled': int(original - remaining)
                    }

        return report


# ==================== 便捷函数 ====================


def fill_missing(
    df: pd.DataFrame,
    method: Literal['ffill', 'bfill', 'interpolate', 'mean', 'smart'] = 'interpolate',
    **kwargs
) -> pd.DataFrame:
    """
    便捷函数：快速填充缺失值

    参数：
        df: 待处理的DataFrame
        method: 填充方法
        **kwargs: 额外参数

    返回：
        填充后的DataFrame
    """
    handler = MissingHandler(df)
    return handler.handle_missing(method=method, **kwargs)


def analyze_missing(df: pd.DataFrame) -> Dict[str, Any]:
    """
    便捷函数：分析缺失值

    参数：
        df: 待分析的DataFrame

    返回：
        缺失值分析报告
    """
    handler = MissingHandler(df)
    stats = handler.detect_missing()
    patterns = handler.get_missing_patterns()

    return {
        'stats': stats,
        'patterns': patterns
    }


# ==================== 使用示例 ====================


if __name__ == "__main__":
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')

    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * (1 + returns).cumprod()

    test_df = pd.DataFrame({
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)

    # 注入缺失值
    test_df.loc[dates[0:3], 'close'] = np.nan  # 前导缺失
    test_df.loc[dates[10:15], 'close'] = np.nan  # 中间缺失
    test_df.loc[dates[95:], 'close'] = np.nan  # 尾部缺失
    test_df.loc[dates[30], 'volume'] = np.nan  # 孤立缺失

    print("=" * 60)
    print("缺失值处理器测试")
    print("=" * 60)

    # 1. 检测缺失值
    handler = MissingHandler(test_df)
    stats = handler.detect_missing()

    print(f"\n缺失值统计:")
    print(f"  总缺失: {stats['total_missing']} ({stats['missing_rate']:.2f}%)")
    print(f"  受影响行: {stats['rows_with_missing']}")

    # 2. 分析缺失模式
    patterns = handler.get_missing_patterns()
    print(f"\n缺失模式:")
    print(f"  前导缺失: {patterns['leading_missing']}")
    print(f"  尾部缺失: {patterns['trailing_missing']}")
    print(f"  连续缺失: {patterns['consecutive_missing']}")

    # 3. 智能填充
    df_filled = handler.smart_fill()

    # 4. 生成报告
    report = handler.get_fill_report(df_filled)
    print(f"\n填充报告:")
    print(f"  原始缺失: {report['original_missing']}")
    print(f"  剩余缺失: {report['remaining_missing']}")
    print(f"  填充数量: {report['filled_count']}")
    print(f"  填充率: {report['fill_rate']:.2f}%")

    print("\n测试完成！")
