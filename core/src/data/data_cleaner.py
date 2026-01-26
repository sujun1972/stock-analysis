"""
数据清洗模块
处理缺失值、异常值、除权除息等数据质量问题
"""

import pandas as pd
import numpy as np
from typing import Tuple

from src.config.trading_rules import DataQualityRules


class DataCleaner:
    """数据清洗器类"""

    def __init__(self, verbose: bool = True):
        """
        初始化数据清洗器

        参数:
            verbose: 是否打印详细信息
        """
        self.verbose = verbose
        self.cleaning_stats = {
            'total_rows': 0,
            'missing_filled': 0,
            'outliers_removed': 0,
            'duplicates_removed': 0,
            'final_rows': 0
        }

    def clean_price_data(
        self,
        df: pd.DataFrame,
        stock_code: str = 'unknown'
    ) -> pd.DataFrame:
        """
        清洗价格数据

        参数:
            df: 价格DataFrame
            stock_code: 股票代码（用于日志）

        返回:
            清洗后的DataFrame
        """
        if df is None or df.empty:
            return df

        self.cleaning_stats['total_rows'] = len(df)

        df = df.copy()

        # 1. 移除重复行
        df = self._remove_duplicates(df)

        # 2. 处理缺失值
        df = self._handle_missing_values(df)

        # 3. 移除异常值
        df = self._remove_outliers(df)

        # 4. 确保数据类型正确
        df = self._ensure_data_types(df)

        # 5. 排序（按日期）
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()

        self.cleaning_stats['final_rows'] = len(df)

        if self.verbose:
            removed_rows = self.cleaning_stats['total_rows'] - self.cleaning_stats['final_rows']
            if removed_rows > 0:
                print(f"[{stock_code}] 清洗完成: 原始{self.cleaning_stats['total_rows']}行 -> "
                      f"清洗后{self.cleaning_stats['final_rows']}行 "
                      f"(移除{removed_rows}行, {removed_rows/self.cleaning_stats['total_rows']*100:.2f}%)")

        return df

    def _remove_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """移除重复行"""
        before = len(df)

        if isinstance(df.index, pd.DatetimeIndex):
            # 如果索引是日期，保留第一个
            df = df[~df.index.duplicated(keep='first')]
        else:
            df = df.drop_duplicates()

        after = len(df)
        self.cleaning_stats['duplicates_removed'] = before - after

        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理缺失值

        策略:
        - 价格数据：前向填充（假设停牌期间价格不变）
        - 成交量：填充为0（停牌期间无成交）
        """
        before_missing = df.isnull().sum().sum()

        # 价格列使用前向填充
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                df[col] = df[col].ffill()

        # 成交量填充为0
        volume_columns = ['vol', 'volume', 'amount']
        for col in volume_columns:
            if col in df.columns:
                df[col] = df[col].fillna(0)

        # 其他列前向填充后向填充
        df = df.ffill().bfill()

        # 如果还有缺失值，删除这些行
        df = df.dropna()

        after_missing = df.isnull().sum().sum()
        self.cleaning_stats['missing_filled'] = before_missing - after_missing

        return df

    def _remove_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        移除异常值

        策略:
        - 价格超出合理范围
        - 单日涨跌幅异常
        """
        before = len(df)

        # 1. 移除价格异常的行
        if 'close' in df.columns:
            valid_price = df['close'].apply(
                lambda x: DataQualityRules.is_price_valid(x)
            )
            df = df[valid_price]

        # 2. 移除异常涨跌幅（可能是数据错误）
        if 'close' in df.columns:
            df['daily_return'] = df['close'].pct_change()

            # 移除单日涨跌幅超过50%的行（除首日外）
            abnormal_change = (
                (df['daily_return'].abs() > DataQualityRules.MAX_DAILY_CHANGE) &
                (df.index != df.index[0])
            )
            df = df[~abnormal_change]

            # 删除临时列
            df = df.drop('daily_return', axis=1)

        after = len(df)
        self.cleaning_stats['outliers_removed'] = before - after

        return df

    def _ensure_data_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """确保数据类型正确"""
        # 价格数据应该是float
        numeric_columns = ['open', 'high', 'low', 'close', 'vol', 'amount',
                          'volume', 'pct_change', 'amplitude', 'turnover']

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        return df

    def validate_ohlc(self, df: pd.DataFrame, fix: bool = True) -> pd.DataFrame:
        """
        验证并修复OHLC逻辑

        规则:
        - high >= max(open, close, low)
        - low <= min(open, close, high)
        - open, close, high, low 都应该 > 0

        参数:
            df: 价格DataFrame
            fix: 是否自动修复

        返回:
            验证/修复后的DataFrame
        """
        if not all(col in df.columns for col in ['open', 'high', 'low', 'close']):
            return df

        df = df.copy()

        # 1. 确保所有价格 > 0
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            df = df[df[col] > 0]

        if fix:
            # 2. 修复high：应该是OHLC中的最大值
            df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)

            # 3. 修复low：应该是OHLC中的最小值
            df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)

        # 4. 验证修复后的逻辑
        invalid_high = df['high'] < df[['open', 'close', 'low']].max(axis=1)
        invalid_low = df['low'] > df[['open', 'close', 'high']].min(axis=1)

        if invalid_high.any() or invalid_low.any():
            if self.verbose:
                print(f"警告: {invalid_high.sum() + invalid_low.sum()} 行OHLC数据仍然不一致")

            # 移除不一致的行
            df = df[~(invalid_high | invalid_low)]

        return df

    def resample_to_daily(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        将分钟数据重采样为日线数据

        参数:
            df: 分钟级别DataFrame

        返回:
            日线DataFrame
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame索引必须是DatetimeIndex")

        # 按日期分组
        daily_df = pd.DataFrame()
        daily_df['open'] = df['open'].resample('D').first()
        daily_df['high'] = df['high'].resample('D').max()
        daily_df['low'] = df['low'].resample('D').min()
        daily_df['close'] = df['close'].resample('D').last()
        daily_df['vol'] = df['vol'].resample('D').sum()

        if 'amount' in df.columns:
            daily_df['amount'] = df['amount'].resample('D').sum()

        # 移除非交易日（volume为0或NaN的日期）
        daily_df = daily_df.dropna(subset=['close'])
        daily_df = daily_df[daily_df['vol'] > 0]

        return daily_df

    def add_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加基础特征

        - 涨跌幅
        - 振幅
        - 换手率（如果有成交量和流通股本数据）

        参数:
            df: 价格DataFrame

        返回:
            添加特征后的DataFrame
        """
        df = df.copy()

        # 计算涨跌幅（如果没有）
        if 'pct_change' not in df.columns and 'close' in df.columns:
            df['pct_change'] = df['close'].pct_change() * 100

        # 计算振幅（如果没有）
        if 'amplitude' not in df.columns:
            if all(col in df.columns for col in ['high', 'low', 'close']):
                df['amplitude'] = ((df['high'] - df['low']) / df['close'].shift(1)) * 100

        return df

    def get_stats(self) -> dict:
        """获取清洗统计信息"""
        return self.cleaning_stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        for key in self.cleaning_stats:
            self.cleaning_stats[key] = 0


def batch_clean_data(
    data_dict: dict,
    verbose: bool = False
) -> Tuple[dict, dict]:
    """
    批量清洗数据

    参数:
        data_dict: {股票代码: DataFrame} 字典
        verbose: 是否打印详细信息

    返回:
        (清洗后的数据字典, 统计信息字典)
    """
    cleaner = DataCleaner(verbose=verbose)
    cleaned_dict = {}
    stats_dict = {}

    total = len(data_dict)
    for i, (stock_code, df) in enumerate(data_dict.items(), 1):
        if verbose and i % 100 == 0:
            print(f"清洗进度: {i}/{total} ({i/total*100:.1f}%)")

        cleaned_df = cleaner.clean_price_data(df, stock_code)
        cleaned_dict[stock_code] = cleaned_df
        stats_dict[stock_code] = cleaner.get_stats()
        cleaner.reset_stats()

    return cleaned_dict, stats_dict


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("数据清洗模块测试\n")

    # 创建测试数据（包含各种问题）
    dates = pd.date_range('2023-01-01', periods=100, freq='D')

    test_df = pd.DataFrame({
        'open': np.random.uniform(10, 20, 100),
        'high': np.random.uniform(15, 25, 100),
        'low': np.random.uniform(5, 15, 100),
        'close': np.random.uniform(10, 20, 100),
        'vol': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)

    # 添加一些问题数据
    test_df.loc[dates[10], 'close'] = np.nan  # 缺失值
    test_df.loc[dates[20], 'high'] = 5  # OHLC逻辑错误
    test_df.loc[dates[30], 'close'] = 1000  # 异常涨幅

    print("原始数据:")
    print(test_df.head(10))
    print(f"\n原始数据行数: {len(test_df)}")
    print(f"缺失值数量: {test_df.isnull().sum().sum()}")

    # 清洗数据
    cleaner = DataCleaner(verbose=True)
    cleaned_df = cleaner.clean_price_data(test_df, '000001')

    print("\n清洗后数据:")
    print(cleaned_df.head(10))
    print(f"\n清洗后数据行数: {len(cleaned_df)}")
    print(f"缺失值数量: {cleaned_df.isnull().sum().sum()}")

    # 验证OHLC
    validated_df = cleaner.validate_ohlc(cleaned_df, fix=True)
    print(f"\nOHLC验证后数据行数: {len(validated_df)}")

    print("\n统计信息:")
    print(cleaner.get_stats())
