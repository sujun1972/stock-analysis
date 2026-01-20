"""
Alpha因子库（量化选股因子）
包含动量、反转、波动率、成交量等常用Alpha因子
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict
import warnings

warnings.filterwarnings('ignore')


class AlphaFactors:
    """Alpha因子计算器"""

    def __init__(self, df: pd.DataFrame):
        """
        初始化Alpha因子计算器

        参数:
            df: 价格DataFrame，需包含 open, high, low, close, volume/vol 列
        """
        self.df = df.copy()
        self._validate_dataframe()

    def _validate_dataframe(self):
        """验证DataFrame格式"""
        required_cols = ['close']
        missing_cols = [col for col in required_cols if col not in self.df.columns]

        if missing_cols:
            raise ValueError(f"DataFrame缺少必需的列: {missing_cols}")

    # ==================== 动量因子 ====================

    def add_momentum_factors(
        self,
        periods: list = [5, 10, 20, 60, 120],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加动量因子（价格动量）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加动量因子的DataFrame
        """
        for period in periods:
            # 简单收益率动量
            self.df[f'MOM{period}'] = self.df[price_col].pct_change(period) * 100

            # 对数收益率动量
            self.df[f'MOM_LOG{period}'] = (
                np.log(self.df[price_col] / self.df[price_col].shift(period)) * 100
            )

        return self.df

    def add_relative_strength(
        self,
        periods: list = [20, 60],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加相对强度因子（价格相对于均线的位置）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加相对强度因子的DataFrame
        """
        for period in periods:
            ma = self.df[price_col].rolling(window=period).mean()
            # 价格相对于均线的偏离度
            self.df[f'RS{period}'] = (self.df[price_col] - ma) / ma * 100

        return self.df

    def add_acceleration(
        self,
        periods: list = [5, 10, 20],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加加速度因子（动量的变化率）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加加速度因子的DataFrame
        """
        for period in periods:
            # 计算动量
            momentum = self.df[price_col].pct_change(period)
            # 动量的变化（加速度）
            self.df[f'ACC{period}'] = momentum - momentum.shift(period)

        return self.df

    # ==================== 反转因子 ====================

    def add_reversal_factors(
        self,
        short_periods: list = [1, 3, 5],
        long_periods: list = [20, 60],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加反转因子（短期反转效应）

        参数:
            short_periods: 短期周期列表
            long_periods: 长期周期列表
            price_col: 价格列名

        返回:
            添加反转因子的DataFrame
        """
        # 短期反转（负向动量）
        for period in short_periods:
            self.df[f'REV{period}'] = -self.df[price_col].pct_change(period) * 100

        # 长期反转（均值回归）
        for period in long_periods:
            ma = self.df[price_col].rolling(window=period).mean()
            std = self.df[price_col].rolling(window=period).std()
            # Z-score（标准化偏离度）
            self.df[f'ZSCORE{period}'] = (ma - self.df[price_col]) / std

        return self.df

    def add_overnight_reversal(self) -> pd.DataFrame:
        """
        添加隔夜反转因子（开盘价相对于前收盘的跳空）

        返回:
            添加隔夜反转因子的DataFrame
        """
        if 'open' not in self.df.columns:
            print("警告: 找不到'open'列，跳过隔夜反转因子")
            return self.df

        # 隔夜收益率（开盘-前收盘）
        self.df['OVERNIGHT_RET'] = (
            (self.df['open'] - self.df['close'].shift(1)) /
            self.df['close'].shift(1) * 100
        )

        # 日内收益率（收盘-开盘）
        self.df['INTRADAY_RET'] = (
            (self.df['close'] - self.df['open']) /
            self.df['open'] * 100
        )

        # 隔夜反转强度（隔夜收益的负值）
        self.df['OVERNIGHT_REV'] = -self.df['OVERNIGHT_RET']

        return self.df

    # ==================== 波动率因子 ====================

    def add_volatility_factors(
        self,
        periods: list = [5, 10, 20, 60],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加波动率因子

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加波动率因子的DataFrame
        """
        returns = self.df[price_col].pct_change()

        for period in periods:
            # 历史波动率（年化）
            self.df[f'VOLATILITY{period}'] = (
                returns.rolling(window=period).std() * np.sqrt(252) * 100
            )

            # 波动率偏度（衡量极端波动）
            self.df[f'VOLSKEW{period}'] = returns.rolling(window=period).skew()

        return self.df

    def add_high_low_volatility(
        self,
        periods: list = [10, 20]
    ) -> pd.DataFrame:
        """
        添加高低价波动率因子

        参数:
            periods: 周期列表

        返回:
            添加高低价波动率因子的DataFrame
        """
        if 'high' not in self.df.columns or 'low' not in self.df.columns:
            print("警告: 找不到'high'或'low'列，跳过高低价波动率因子")
            return self.df

        for period in periods:
            # Parkinson波动率（基于高低价）
            hl_ratio = np.log(self.df['high'] / self.df['low']) ** 2
            self.df[f'PARKINSON_VOL{period}'] = (
                np.sqrt(hl_ratio.rolling(window=period).mean() / (4 * np.log(2))) *
                np.sqrt(252) * 100
            )

        return self.df

    # ==================== 成交量因子 ====================

    def add_volume_factors(
        self,
        periods: list = [5, 10, 20],
        volume_col: str = 'vol'
    ) -> pd.DataFrame:
        """
        添加成交量因子

        参数:
            periods: 周期列表
            volume_col: 成交量列名

        返回:
            添加成交量因子的DataFrame
        """
        if volume_col not in self.df.columns:
            print(f"警告: 找不到列'{volume_col}'，跳过成交量因子")
            return self.df

        for period in periods:
            # 成交量变化率
            self.df[f'VOLUME_CHG{period}'] = (
                self.df[volume_col].pct_change(period) * 100
            )

            # 成交量相对强度
            vol_ma = self.df[volume_col].rolling(window=period).mean()
            self.df[f'VOLUME_RATIO{period}'] = self.df[volume_col] / vol_ma

            # 成交量标准化（Z-score）
            vol_std = self.df[volume_col].rolling(window=period).std()
            self.df[f'VOLUME_ZSCORE{period}'] = (
                (self.df[volume_col] - vol_ma) / vol_std
            )

        return self.df

    def add_price_volume_correlation(
        self,
        periods: list = [20, 60],
        price_col: str = 'close',
        volume_col: str = 'vol'
    ) -> pd.DataFrame:
        """
        添加价量相关性因子

        参数:
            periods: 周期列表
            price_col: 价格列名
            volume_col: 成交量列名

        返回:
            添加价量相关性因子的DataFrame
        """
        if volume_col not in self.df.columns:
            print(f"警告: 找不到列'{volume_col}'，跳过价量相关性因子")
            return self.df

        price_ret = self.df[price_col].pct_change()

        for period in periods:
            # 价格收益率与成交量的相关系数
            self.df[f'PV_CORR{period}'] = (
                price_ret.rolling(window=period).corr(self.df[volume_col])
            )

        return self.df

    # ==================== 趋势强度因子 ====================

    def add_trend_strength(
        self,
        periods: list = [20, 60],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加趋势强度因子（ADX思想）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加趋势强度因子的DataFrame
        """
        for period in periods:
            # 线性回归斜率
            self.df[f'TREND{period}'] = (
                self.df[price_col].rolling(window=period).apply(
                    lambda x: np.polyfit(np.arange(len(x)), x, 1)[0] if len(x) == period else np.nan,
                    raw=True
                )
            )

            # R-squared（趋势拟合度）
            def calc_r2(prices):
                if len(prices) != period:
                    return np.nan
                x = np.arange(len(prices))
                slope, intercept = np.polyfit(x, prices, 1)
                y_pred = slope * x + intercept
                ss_res = np.sum((prices - y_pred) ** 2)
                ss_tot = np.sum((prices - np.mean(prices)) ** 2)
                return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            self.df[f'TREND_R2_{period}'] = (
                self.df[price_col].rolling(window=period).apply(calc_r2, raw=True)
            )

        return self.df

    def add_breakout_factors(
        self,
        periods: list = [20, 60],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加突破因子（新高新低）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加突破因子的DataFrame
        """
        for period in periods:
            # 创新高因子（当前价相对于N日最高价）
            high_max = self.df[price_col].rolling(window=period).max()
            self.df[f'BREAKOUT_HIGH{period}'] = (
                (self.df[price_col] - high_max) / high_max * 100
            )

            # 创新低因子（当前价相对于N日最低价）
            low_min = self.df[price_col].rolling(window=period).min()
            self.df[f'BREAKOUT_LOW{period}'] = (
                (self.df[price_col] - low_min) / low_min * 100
            )

            # 价格在区间中的位置（0-100）
            self.df[f'PRICE_POSITION{period}'] = (
                (self.df[price_col] - low_min) / (high_max - low_min) * 100
            )

        return self.df

    # ==================== 流动性因子 ====================

    def add_liquidity_factors(
        self,
        periods: list = [20],
        volume_col: str = 'vol'
    ) -> pd.DataFrame:
        """
        添加流动性因子（Amihud非流动性指标）

        参数:
            periods: 周期列表
            volume_col: 成交量列名

        返回:
            添加流动性因子的DataFrame
        """
        if volume_col not in self.df.columns:
            print(f"警告: 找不到列'{volume_col}'，跳过流动性因子")
            return self.df

        # 日收益率
        returns = self.df['close'].pct_change().abs()

        for period in periods:
            # Amihud非流动性 = |收益率| / 成交量
            amihud = returns / (self.df[volume_col] + 1e-8)  # 避免除零
            self.df[f'ILLIQUIDITY{period}'] = (
                amihud.rolling(window=period).mean() * 1e6  # 放大倍数
            )

        return self.df

    # ==================== 综合因子 ====================

    def add_all_alpha_factors(self) -> pd.DataFrame:
        """
        一键添加所有Alpha因子

        返回:
            添加所有Alpha因子的DataFrame
        """
        print("正在计算Alpha因子...")

        # 动量因子
        self.add_momentum_factors([5, 10, 20, 60, 120])
        self.add_relative_strength([20, 60])
        self.add_acceleration([5, 10, 20])

        # 反转因子
        self.add_reversal_factors([1, 3, 5], [20, 60])
        self.add_overnight_reversal()

        # 波动率因子
        self.add_volatility_factors([5, 10, 20, 60])
        self.add_high_low_volatility([10, 20])

        # 成交量因子
        self.add_volume_factors([5, 10, 20])
        self.add_price_volume_correlation([20, 60])

        # 趋势因子
        self.add_trend_strength([20, 60])
        self.add_breakout_factors([20, 60])

        # 流动性因子
        self.add_liquidity_factors([20])

        print(f"✓ Alpha因子计算完成，共 {len(self.df.columns)} 个特征")

        return self.df

    def get_factor_names(self) -> list:
        """获取所有因子名称列表"""
        # 排除原始OHLCV列
        exclude_cols = ['open', 'high', 'low', 'close', 'vol', 'volume', 'amount']
        return [col for col in self.df.columns if col not in exclude_cols]

    def get_dataframe(self) -> pd.DataFrame:
        """获取包含所有因子的DataFrame"""
        return self.df


# ==================== 便捷函数 ====================

def calculate_all_alpha_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    便捷函数：一键计算所有Alpha因子

    参数:
        df: 价格DataFrame

    返回:
        包含所有Alpha因子的DataFrame
    """
    af = AlphaFactors(df)
    return af.add_all_alpha_factors()


def calculate_momentum_factors(df: pd.DataFrame) -> pd.DataFrame:
    """
    便捷函数：仅计算动量相关因子

    参数:
        df: 价格DataFrame

    返回:
        包含动量因子的DataFrame
    """
    af = AlphaFactors(df)
    af.add_momentum_factors([5, 10, 20, 60, 120])
    af.add_relative_strength([20, 60])
    af.add_acceleration([5, 10, 20])
    return af.get_dataframe()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("Alpha因子模块测试\n")

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=300, freq='D')

    # 模拟价格数据
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

    # 计算Alpha因子
    af = AlphaFactors(test_df)
    result_df = af.add_all_alpha_factors()

    print("\n添加Alpha因子后:")
    print(result_df.head())
    print(f"\n总列数: {len(result_df.columns)}")
    print(f"因子列数: {len(af.get_factor_names())}")

    print("\n因子列表:")
    for i, col in enumerate(af.get_factor_names(), 1):
        print(f"  {i:2d}. {col}")

    print("\n最近5天数据示例:")
    sample_cols = ['close', 'MOM20', 'REV5', 'VOLATILITY20', 'VOLUME_RATIO5', 'TREND20']
    available_cols = [col for col in sample_cols if col in result_df.columns]
    print(result_df[available_cols].tail())
