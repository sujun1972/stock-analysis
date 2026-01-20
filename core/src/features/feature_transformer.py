"""
特征转换器（Feature Transformer）
用于AI模型的特征变换，包括价格变动率矩阵、标准化等
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, List, Dict
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
import warnings

warnings.filterwarnings('ignore')


class FeatureTransformer:
    """特征转换器"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化特征转换器

        参数:
            df: 包含价格和特征的DataFrame
        """
        self.df = df.copy()
        self.scalers = {}  # 存储各列的scaler

    # ==================== 价格变动率矩阵 ====================

    def create_price_change_matrix(
        self,
        lookback_days: int = 20,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        创建价格变动率矩阵（用于GRU/LSTM输入）
        ΔP_t = (P_t - P_{t-1}) / P_{t-1}

        参数:
            lookback_days: 回看天数
            price_col: 价格列名

        返回:
            包含价格变动率矩阵的DataFrame
        """
        # 计算每日价格变动率
        price_changes = self.df[price_col].pct_change()

        # 创建回看窗口特征
        for i in range(1, lookback_days + 1):
            self.df[f'PRICE_CHG_T-{i}'] = price_changes.shift(i) * 100

        return self.df

    def create_multi_timeframe_returns(
        self,
        periods: list = [1, 3, 5, 10, 20],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        创建多时间尺度收益率特征

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            包含多时间尺度收益率的DataFrame
        """
        for period in periods:
            # 简单收益率
            self.df[f'RET_{period}D'] = (
                self.df[price_col].pct_change(period) * 100
            )

            # 对数收益率
            self.df[f'LOG_RET_{period}D'] = (
                np.log(self.df[price_col] / self.df[price_col].shift(period)) * 100
            )

        return self.df

    def create_ohlc_features(self) -> pd.DataFrame:
        """
        创建OHLC衍生特征

        返回:
            包含OHLC特征的DataFrame
        """
        if not all(col in self.df.columns for col in ['open', 'high', 'low', 'close']):
            print("警告: 缺少OHLC列，跳过OHLC特征创建")
            return self.df

        # 价格位置（在当日振幅中的位置）
        self.df['PRICE_POSITION_DAILY'] = (
            (self.df['close'] - self.df['low']) /
            (self.df['high'] - self.df['low'] + 1e-8) * 100
        )

        # 实体强度（收盘相对开盘）
        self.df['BODY_STRENGTH'] = (
            (self.df['close'] - self.df['open']) /
            (self.df['high'] - self.df['low'] + 1e-8) * 100
        )

        # 上影线比例
        upper_shadow = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        self.df['UPPER_SHADOW_RATIO'] = (
            upper_shadow / (self.df['high'] - self.df['low'] + 1e-8) * 100
        )

        # 下影线比例
        lower_shadow = self.df[['open', 'close']].min(axis=1) - self.df['low']
        self.df['LOWER_SHADOW_RATIO'] = (
            lower_shadow / (self.df['high'] - self.df['low'] + 1e-8) * 100
        )

        return self.df

    # ==================== 特征标准化 ====================

    def normalize_features(
        self,
        feature_cols: list,
        method: str = 'standard',
        fit: bool = True
    ) -> pd.DataFrame:
        """
        标准化特征（用于机器学习模型）

        参数:
            feature_cols: 需要标准化的特征列列表
            method: 标准化方法 ('standard', 'robust', 'minmax')
            fit: 是否拟合scaler（训练时True，测试时False）

        返回:
            包含标准化特征的DataFrame
        """
        # 选择scaler
        if method == 'standard':
            scaler_class = StandardScaler
        elif method == 'robust':
            scaler_class = RobustScaler
        elif method == 'minmax':
            scaler_class = MinMaxScaler
        else:
            raise ValueError(f"不支持的标准化方法: {method}")

        for col in feature_cols:
            if col not in self.df.columns:
                print(f"警告: 列 '{col}' 不存在，跳过")
                continue

            # 处理缺失值和无穷值
            valid_mask = np.isfinite(self.df[col])
            if not valid_mask.all():
                self.df.loc[~valid_mask, col] = np.nan

            # 创建或使用已有的scaler
            scaler_key = f"{col}_{method}"
            if fit:
                scaler = scaler_class()
                valid_data = self.df.loc[valid_mask, [col]]
                if len(valid_data) > 0:
                    scaler.fit(valid_data)
                    self.scalers[scaler_key] = scaler
            else:
                if scaler_key not in self.scalers:
                    print(f"警告: 找不到列 '{col}' 的scaler，跳过")
                    continue
                scaler = self.scalers[scaler_key]

            # 转换数据
            if valid_mask.sum() > 0:
                transformed = scaler.transform(self.df.loc[valid_mask, [col]])
                self.df.loc[valid_mask, f'{col}_NORM'] = transformed.flatten()

        return self.df

    def rank_transform(
        self,
        feature_cols: list,
        window: int = None,
        pct: bool = True
    ) -> pd.DataFrame:
        """
        排名转换（截面排名或滚动排名）

        参数:
            feature_cols: 需要排名的特征列列表
            window: 滚动窗口大小（None表示全局排名）
            pct: 是否转为百分位排名（0-1之间）

        返回:
            包含排名特征的DataFrame
        """
        for col in feature_cols:
            if col not in self.df.columns:
                print(f"警告: 列 '{col}' 不存在，跳过")
                continue

            if window is None:
                # 全局排名
                ranked = self.df[col].rank(pct=pct)
            else:
                # 滚动排名
                ranked = self.df[col].rolling(window=window).apply(
                    lambda x: pd.Series(x).rank(pct=pct).iloc[-1] if len(x) == window else np.nan,
                    raw=False
                )

            suffix = '_PCT_RANK' if pct else '_RANK'
            self.df[f'{col}{suffix}'] = ranked

        return self.df

    # ==================== 特征交互 ====================

    def create_ratio_features(
        self,
        numerator_cols: list,
        denominator_cols: list
    ) -> pd.DataFrame:
        """
        创建比率特征（特征间的比值）

        参数:
            numerator_cols: 分子列列表
            denominator_cols: 分母列列表

        返回:
            包含比率特征的DataFrame
        """
        for num_col in numerator_cols:
            for den_col in denominator_cols:
                if num_col in self.df.columns and den_col in self.df.columns:
                    # 避免除零
                    ratio = self.df[num_col] / (self.df[den_col] + 1e-8)
                    self.df[f'{num_col}_DIV_{den_col}'] = ratio

        return self.df

    def create_diff_features(
        self,
        col_pairs: list
    ) -> pd.DataFrame:
        """
        创建差值特征（特征间的差值）

        参数:
            col_pairs: 列对列表 [(col1, col2), ...]

        返回:
            包含差值特征的DataFrame
        """
        for col1, col2 in col_pairs:
            if col1 in self.df.columns and col2 in self.df.columns:
                diff = self.df[col1] - self.df[col2]
                self.df[f'{col1}_MINUS_{col2}'] = diff

        return self.df

    # ==================== 时间特征 ====================

    def add_time_features(self) -> pd.DataFrame:
        """
        添加时间相关特征（星期几、月份、季度等）

        返回:
            包含时间特征的DataFrame
        """
        if not isinstance(self.df.index, pd.DatetimeIndex):
            print("警告: DataFrame索引不是DatetimeIndex，跳过时间特征")
            return self.df

        # 星期几（0=周一, 4=周五）
        self.df['DAY_OF_WEEK'] = self.df.index.dayofweek

        # 月份
        self.df['MONTH'] = self.df.index.month

        # 季度
        self.df['QUARTER'] = self.df.index.quarter

        # 月初/月末标志
        self.df['IS_MONTH_START'] = self.df.index.is_month_start.astype(int)
        self.df['IS_MONTH_END'] = self.df.index.is_month_end.astype(int)

        # 季度初/季度末标志
        self.df['IS_QUARTER_START'] = self.df.index.is_quarter_start.astype(int)
        self.df['IS_QUARTER_END'] = self.df.index.is_quarter_end.astype(int)

        # 年初/年末标志
        self.df['IS_YEAR_START'] = self.df.index.is_year_start.astype(int)
        self.df['IS_YEAR_END'] = self.df.index.is_year_end.astype(int)

        return self.df

    # ==================== 滞后特征 ====================

    def create_lag_features(
        self,
        feature_cols: list,
        lags: list = [1, 2, 3, 5, 10]
    ) -> pd.DataFrame:
        """
        创建滞后特征（用于时间序列模型）

        参数:
            feature_cols: 需要创建滞后的特征列列表
            lags: 滞后期数列表

        返回:
            包含滞后特征的DataFrame
        """
        for col in feature_cols:
            if col not in self.df.columns:
                print(f"警告: 列 '{col}' 不存在，跳过")
                continue

            for lag in lags:
                self.df[f'{col}_LAG{lag}'] = self.df[col].shift(lag)

        return self.df

    def create_rolling_features(
        self,
        feature_cols: list,
        windows: list = [5, 10, 20],
        funcs: list = ['mean', 'std', 'max', 'min']
    ) -> pd.DataFrame:
        """
        创建滚动统计特征

        参数:
            feature_cols: 需要计算滚动统计的特征列列表
            windows: 窗口大小列表
            funcs: 统计函数列表

        返回:
            包含滚动统计特征的DataFrame
        """
        for col in feature_cols:
            if col not in self.df.columns:
                print(f"警告: 列 '{col}' 不存在，跳过")
                continue

            for window in windows:
                rolling = self.df[col].rolling(window=window)

                for func in funcs:
                    if func == 'mean':
                        self.df[f'{col}_ROLL{window}_MEAN'] = rolling.mean()
                    elif func == 'std':
                        self.df[f'{col}_ROLL{window}_STD'] = rolling.std()
                    elif func == 'max':
                        self.df[f'{col}_ROLL{window}_MAX'] = rolling.max()
                    elif func == 'min':
                        self.df[f'{col}_ROLL{window}_MIN'] = rolling.min()
                    elif func == 'median':
                        self.df[f'{col}_ROLL{window}_MEDIAN'] = rolling.median()
                    elif func == 'skew':
                        self.df[f'{col}_ROLL{window}_SKEW'] = rolling.skew()
                    elif func == 'kurt':
                        self.df[f'{col}_ROLL{window}_KURT'] = rolling.kurt()

        return self.df

    # ==================== 缺失值处理 ====================

    def handle_missing_values(
        self,
        method: str = 'forward',
        fill_value: float = 0.0
    ) -> pd.DataFrame:
        """
        处理缺失值

        参数:
            method: 填充方法 ('forward', 'backward', 'mean', 'median', 'zero', 'value')
            fill_value: 当method='value'时使用的填充值

        返回:
            处理缺失值后的DataFrame
        """
        if method == 'forward':
            self.df = self.df.fillna(method='ffill')
        elif method == 'backward':
            self.df = self.df.fillna(method='bfill')
        elif method == 'mean':
            self.df = self.df.fillna(self.df.mean())
        elif method == 'median':
            self.df = self.df.fillna(self.df.median())
        elif method == 'zero':
            self.df = self.df.fillna(0)
        elif method == 'value':
            self.df = self.df.fillna(fill_value)
        else:
            raise ValueError(f"不支持的填充方法: {method}")

        return self.df

    def handle_infinite_values(self) -> pd.DataFrame:
        """
        处理无穷值（替换为NaN）

        返回:
            处理无穷值后的DataFrame
        """
        self.df = self.df.replace([np.inf, -np.inf], np.nan)
        return self.df

    # ==================== 辅助方法 ====================

    def get_dataframe(self) -> pd.DataFrame:
        """获取转换后的DataFrame"""
        return self.df

    def get_scalers(self) -> dict:
        """获取所有scaler（用于保存和加载）"""
        return self.scalers

    def set_scalers(self, scalers: dict):
        """设置scaler（从保存的模型加载）"""
        self.scalers = scalers


# ==================== 便捷函数 ====================

def prepare_ml_features(
    df: pd.DataFrame,
    lookback_days: int = 20,
    normalize: bool = True
) -> pd.DataFrame:
    """
    便捷函数：准备机器学习特征（一站式）

    参数:
        df: 原始DataFrame
        lookback_days: 价格变动率矩阵回看天数
        normalize: 是否标准化

    返回:
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


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("特征转换器模块测试\n")

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=300, freq='D')

    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 300)
    prices = base_price * (1 + returns).cumprod()

    test_df = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 300)),
        'high': prices * (1 + np.random.uniform(0, 0.03, 300)),
        'low': prices * (1 + np.random.uniform(-0.03, 0, 300)),
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, 300)
    }, index=dates)

    print("原始数据:")
    print(test_df.head())
    print(f"\n原始列数: {len(test_df.columns)}")

    # 特征转换
    ft = FeatureTransformer(test_df)

    print("\n1. 创建价格变动率矩阵（20天回看）")
    ft.create_price_change_matrix(lookback_days=20)

    print("\n2. 创建多时间尺度收益率")
    ft.create_multi_timeframe_returns([1, 3, 5, 10, 20])

    print("\n3. 创建OHLC特征")
    ft.create_ohlc_features()

    print("\n4. 添加时间特征")
    ft.add_time_features()

    print("\n5. 处理缺失值和无穷值")
    ft.handle_infinite_values()
    ft.handle_missing_values(method='forward')

    result_df = ft.get_dataframe()

    print(f"\n转换后总列数: {len(result_df.columns)}")
    print("\n部分特征列表:")
    print(result_df.columns.tolist()[:30])

    print("\n最近5天数据示例:")
    sample_cols = ['close', 'RET_1D', 'RET_5D', 'PRICE_POSITION_DAILY',
                   'DAY_OF_WEEK', 'MONTH']
    print(result_df[sample_cols].tail())

    print("\n✓ 特征转换器测试完成")
