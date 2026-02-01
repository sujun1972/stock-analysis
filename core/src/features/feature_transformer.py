"""
特征转换器（Feature Transformer）- 向后兼容包装器

这是一个向后兼容的包装器，内部使用策略模式实现。
保持原有 API 不变，同时享受策略模式的优势。

## 迁移指南

推荐使用新的策略模式 API（在 transform_strategy.py 中）：

```python
# 旧方式（仍然支持）
from features.feature_transformer import FeatureTransformer
ft = FeatureTransformer(df)
ft.create_price_change_matrix()
result = ft.get_dataframe()

# 新方式（推荐）
from features.transform_strategy import create_default_transform_pipeline
pipeline = create_default_transform_pipeline()
result = pipeline.transform(df)
```

作者: Stock Analysis Team
更新: 2026-01-27
版本: v3.0 (策略模式重构)
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Union
from pathlib import Path

# 导入新的策略模式类
from .transform_strategy import (
    PriceChangeTransformStrategy,
    NormalizationStrategy,
    TimeFeatureStrategy,
    StatisticalFeatureStrategy,
    CompositeTransformStrategy,
    TransformError,
    InvalidDataError,
    ScalerNotFoundError,
)

from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from loguru import logger

from src.utils.data_utils import forward_fill_series, backward_fill_series, fill_with_value


# ==================== 向后兼容的 FeatureTransformer 类 ====================

class FeatureTransformer:
    """
    特征转换器（向后兼容包装器）

    这个类保持原有 API 不变，内部使用策略模式实现。
    所有方法都委托给相应的策略类。

    推荐使用新的策略模式 API (见 transform_strategy.py)
    """

    def __init__(self, df: pd.DataFrame) -> None:
        """
        初始化特征转换器

        Args:
            df: 包含价格和特征的DataFrame
        """
        self.df: pd.DataFrame = df.copy()
        self.scalers: Dict[str, Union[StandardScaler, RobustScaler, MinMaxScaler]] = {}

        # 内部策略实例（懒加载）
        self._price_strategy: Optional[PriceChangeTransformStrategy] = None
        self._norm_strategy: Optional[NormalizationStrategy] = None
        self._time_strategy: Optional[TimeFeatureStrategy] = None
        self._stat_strategy: Optional[StatisticalFeatureStrategy] = None

    # ==================== 价格变动率矩阵 ====================

    def create_price_change_matrix(
        self,
        lookback_days: int = 20,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        创建价格变动率矩阵（用于GRU/LSTM输入）

        Args:
            lookback_days: 回看天数
            price_col: 价格列名

        Returns:
            包含价格变动率矩阵的DataFrame
        """
        strategy = PriceChangeTransformStrategy(config={
            'lookback_days': lookback_days,
            'price_col': price_col,
            'return_periods': [],  # 不生成收益率
            'include_log_returns': False,
            'include_ohlc_features': False,
        })

        self.df = strategy.transform(self.df)
        return self.df

    def create_multi_timeframe_returns(
        self,
        periods: List[int] = [1, 3, 5, 10, 20],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        创建多时间尺度收益率特征

        Args:
            periods: 周期列表
            price_col: 价格列名

        Returns:
            包含多时间尺度收益率的DataFrame
        """
        strategy = PriceChangeTransformStrategy(config={
            'lookback_days': 0,  # 不生成价格变动率矩阵
            'price_col': price_col,
            'return_periods': periods,
            'include_log_returns': True,
            'include_ohlc_features': False,
        })

        self.df = strategy.transform(self.df)
        return self.df

    def create_ohlc_features(self) -> pd.DataFrame:
        """
        创建OHLC衍生特征

        Returns:
            包含OHLC特征的DataFrame
        """
        strategy = PriceChangeTransformStrategy(config={
            'lookback_days': 0,
            'return_periods': [],
            'include_ohlc_features': True,
        })

        self.df = strategy.transform(self.df)
        return self.df

    # ==================== 特征标准化 ====================

    def normalize_features(
        self,
        feature_cols: List[str],
        method: str = 'standard',
        fit: bool = True
    ) -> pd.DataFrame:
        """
        标准化特征（用于机器学习模型）

        Args:
            feature_cols: 需要标准化的特征列列表
            method: 标准化方法 ('standard', 'robust', 'minmax')
            fit: 是否拟合scaler（训练时True，测试时False）

        Returns:
            包含标准化特征的DataFrame
        """
        if self._norm_strategy is None or self._norm_strategy.config['method'] != method:
            self._norm_strategy = NormalizationStrategy(config={
                'method': method,
                'feature_cols': feature_cols,
                'fit': fit,
            })
        else:
            # 更新配置
            self._norm_strategy.config['feature_cols'] = feature_cols
            self._norm_strategy.config['fit'] = fit

        self.df = self._norm_strategy.transform(self.df)

        # 同步 scalers
        self.scalers = self._norm_strategy.scalers

        return self.df

    def rank_transform(
        self,
        feature_cols: List[str],
        window: Optional[int] = None,
        pct: bool = True
    ) -> pd.DataFrame:
        """
        排名转换（截面排名或滚动排名）

        Args:
            feature_cols: 需要排名的特征列列表
            window: 滚动窗口大小（None表示全局排名）
            pct: 是否转为百分位排名（0-1之间）

        Returns:
            包含排名特征的DataFrame
        """
        strategy = NormalizationStrategy(config={
            'method': 'robust',  # method参数在rank_transform时不使用
            'feature_cols': feature_cols,
            'rank_transform': True,
            'rank_window': window,
        })

        self.df = strategy.transform(self.df)
        return self.df

    # ==================== 时间特征 ====================

    def add_time_features(self) -> pd.DataFrame:
        """
        添加时间相关特征（星期几、月份、季度等）

        Returns:
            包含时间特征的DataFrame
        """
        if self._time_strategy is None:
            self._time_strategy = TimeFeatureStrategy()

        self.df = self._time_strategy.transform(self.df)
        return self.df

    # ==================== 滞后特征 ====================

    def create_lag_features(
        self,
        feature_cols: List[str],
        lags: List[int] = [1, 2, 3, 5, 10]
    ) -> pd.DataFrame:
        """
        创建滞后特征（用于时间序列模型）

        Args:
            feature_cols: 需要创建滞后的特征列列表
            lags: 滞后期数列表

        Returns:
            包含滞后特征的DataFrame
        """
        strategy = StatisticalFeatureStrategy(config={
            'feature_cols': feature_cols,
            'lag_periods': lags,
            'rolling_windows': [],  # 不生成滚动特征
        })

        self.df = strategy.transform(self.df)
        return self.df

    def create_rolling_features(
        self,
        feature_cols: List[str],
        windows: Optional[List[int]] = None,
        funcs: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        创建滚动统计特征

        Args:
            feature_cols: 需要计算滚动统计的特征列列表
            windows: 窗口大小列表（默认 [5, 10, 20]）
            funcs: 统计函数列表

        Returns:
            包含滚动统计特征的DataFrame
        """
        if windows is None:
            windows = [5, 10, 20]
        if funcs is None:
            funcs = ['mean', 'std', 'max', 'min']

        strategy = StatisticalFeatureStrategy(config={
            'feature_cols': feature_cols,
            'lag_periods': [],  # 不生成滞后特征
            'rolling_windows': windows,
            'rolling_funcs': funcs,
        })

        self.df = strategy.transform(self.df)
        return self.df

    # ==================== 缺失值处理 ====================

    def handle_missing_values(
        self,
        method: str = 'forward',
        fill_value: float = 0.0
    ) -> pd.DataFrame:
        """
        处理缺失值

        Args:
            method: 填充方法 ('forward', 'backward', 'mean', 'median', 'zero', 'value')
            fill_value: 当method='value'时使用的填充值

        Returns:
            处理缺失值后的DataFrame
        """
        if method == 'forward':
            # 使用通用工具函数
            for col in self.df.columns:
                self.df[col] = forward_fill_series(self.df[col])
        elif method == 'backward':
            # 使用通用工具函数
            for col in self.df.columns:
                self.df[col] = backward_fill_series(self.df[col])
        elif method == 'mean':
            self.df = self.df.fillna(self.df.mean())
        elif method == 'median':
            self.df = self.df.fillna(self.df.median())
        elif method == 'zero':
            # 使用通用工具函数
            for col in self.df.columns:
                self.df[col] = fill_with_value(self.df[col], value=0)
        elif method == 'value':
            # 使用通用工具函数
            for col in self.df.columns:
                self.df[col] = fill_with_value(self.df[col], value=fill_value)
        else:
            raise ValueError(f"不支持的填充方法: {method}")

        return self.df

    def handle_infinite_values(self) -> pd.DataFrame:
        """
        处理无穷值（替换为NaN）

        Returns:
            处理无穷值后的DataFrame
        """
        self.df = self.df.replace([np.inf, -np.inf], np.nan)
        return self.df

    # ==================== 辅助方法 ====================

    def get_dataframe(self) -> pd.DataFrame:
        """获取转换后的DataFrame"""
        return self.df

    def get_scalers(self) -> Dict[str, Union[StandardScaler, RobustScaler, MinMaxScaler]]:
        """获取所有scaler（用于保存和加载）"""
        return self.scalers

    def set_scalers(self, scalers: Dict[str, Union[StandardScaler, RobustScaler, MinMaxScaler]]) -> None:
        """设置scaler（从保存的模型加载）"""
        self.scalers = scalers
        if self._norm_strategy is not None:
            self._norm_strategy.scalers = scalers

    def save_scalers(self, file_path: Union[str, Path]) -> bool:
        """
        保存scalers到文件

        Args:
            file_path: 保存路径

        Returns:
            是否保存成功
        """
        if self._norm_strategy is None:
            self._norm_strategy = NormalizationStrategy()
            self._norm_strategy.scalers = self.scalers

        return self._norm_strategy.save_scalers(file_path)

    def load_scalers(self, file_path: Union[str, Path]) -> bool:
        """
        从文件加载scalers

        Args:
            file_path: 文件路径

        Returns:
            是否加载成功
        """
        if self._norm_strategy is None:
            self._norm_strategy = NormalizationStrategy()

        success = self._norm_strategy.load_scalers(file_path)
        if success:
            self.scalers = self._norm_strategy.scalers

        return success


# ==================== 便捷函数 ====================

def prepare_ml_features(
    df: pd.DataFrame,
    lookback_days: int = 20,
    normalize: bool = True
) -> pd.DataFrame:
    """
    便捷函数：准备机器学习特征（一站式）

    Args:
        df: 原始DataFrame
        lookback_days: 价格变动率矩阵回看天数
        normalize: 是否标准化

    Returns:
        准备好的特征DataFrame
    """
    ft = FeatureTransformer(df)

    # 价格变动率矩阵
    ft.create_price_change_matrix(lookback_days)

    # 多时间尺度收益率
    ft.create_multi_timeframe_returns([1, 3, 5, 10, 20])

    # OHLC特征
    ft.create_ohlc_features()

    # 时间特征
    ft.add_time_features()

    # 处理无穷值和缺失值
    ft.handle_infinite_values()
    ft.handle_missing_values(method='forward')

    result_df = ft.get_dataframe()

    # 标准化（如果需要）
    if normalize:
        # 找出所有数值列（排除时间特征）
        numeric_cols = result_df.select_dtypes(include=[np.number]).columns.tolist()
        exclude_cols = ['DAY_OF_WEEK', 'MONTH', 'QUARTER', 'IS_MONTH_START',
                       'IS_MONTH_END', 'IS_QUARTER_START', 'IS_QUARTER_END',
                       'IS_YEAR_START', 'IS_YEAR_END']
        feature_cols = [col for col in numeric_cols if col not in exclude_cols]

        ft.normalize_features(feature_cols, method='robust', fit=True)
        result_df = ft.get_dataframe()

    return result_df


# ==================== 导出 ====================

__all__ = [
    # 主类（向后兼容）
    'FeatureTransformer',
    # 便捷函数
    'prepare_ml_features',
    # 异常类（从 transform_strategy 导入）
    'TransformError',
    'InvalidDataError',
    'ScalerNotFoundError',
]
