"""
异常值检测器单元测试

测试覆盖：
- IQR方法检测
- Z-score方法检测
- 价格跳空检测
- 成交量异常检测
- 异常值处理（移除/截断/插值）
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from data.outlier_detector import OutlierDetector, detect_outliers, clean_outliers


@pytest.fixture
def sample_data():
    """创建测试数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)

    # 注入异常值
    returns[20] = 0.25  # 单日暴涨25%
    returns[50] = -0.22  # 单日暴跌22%

    prices = base_price * (1 + returns).cumprod()

    return pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)


class TestOutlierDetector:
    """异常值检测器测试类"""

    def test_initialization(self, sample_data):
        """测试初始化"""
        detector = OutlierDetector(sample_data)

        assert detector.df is not None
        assert len(detector.price_cols) == 4
        assert detector.volume_col == 'volume'

    def test_detect_by_iqr(self, sample_data):
        """测试IQR方法检测"""
        detector = OutlierDetector(sample_data)
        outliers = detector.detect_by_iqr('close', multiplier=3.0, use_returns=True)

        assert isinstance(outliers, pd.Series)
        assert len(outliers) == len(sample_data)
        assert outliers.sum() >= 2  # 至少检测到注入的2个异常值

    def test_detect_by_zscore(self, sample_data):
        """测试Z-score方法检测"""
        detector = OutlierDetector(sample_data)

        # 标准Z-score
        outliers_std = detector.detect_by_zscore('close', threshold=3.0, use_modified=False)
        assert isinstance(outliers_std, pd.Series)
        assert outliers_std.sum() >= 2

        # 修正Z-score
        outliers_mad = detector.detect_by_zscore('close', threshold=3.0, use_modified=True)
        assert isinstance(outliers_mad, pd.Series)
        assert outliers_mad.sum() >= 2

    def test_detect_price_jumps(self, sample_data):
        """测试价格跳空检测"""
        detector = OutlierDetector(sample_data)
        jumps = detector.detect_price_jumps(threshold=0.20)

        assert isinstance(jumps, pd.Series)
        assert jumps.sum() >= 2  # 应该检测到25%和22%的跳空

    def test_detect_volume_anomalies(self, sample_data):
        """测试成交量异常检测"""
        detector = OutlierDetector(sample_data)

        # 注入成交量异常
        detector.df.loc[detector.df.index[10], 'volume'] = 1e8  # 极大值

        anomalies = detector.detect_volume_anomalies(method='zscore', threshold=3.0)

        assert isinstance(anomalies, pd.Series)
        assert anomalies.sum() >= 1  # 至少检测到注入的异常

    def test_detect_all_outliers(self, sample_data):
        """测试综合异常检测"""
        detector = OutlierDetector(sample_data)
        outliers_df = detector.detect_all_outliers(
            price_method='both',
            price_threshold=3.0,
            jump_threshold=0.20
        )

        assert isinstance(outliers_df, pd.DataFrame)
        assert 'is_outlier' in outliers_df.columns
        assert 'price_jump' in outliers_df.columns
        assert outliers_df['is_outlier'].sum() >= 2

    def test_get_outlier_summary(self, sample_data):
        """测试异常值摘要统计"""
        detector = OutlierDetector(sample_data)
        outliers_df = detector.detect_all_outliers()
        summary = detector.get_outlier_summary(outliers_df)

        assert 'total_records' in summary
        assert 'total_outliers' in summary
        assert 'outlier_percentage' in summary
        assert 'by_type' in summary
        assert summary['total_records'] == len(sample_data)

    def test_remove_outliers(self, sample_data):
        """测试移除异常值"""
        detector = OutlierDetector(sample_data)
        outliers_df = detector.detect_all_outliers()

        df_cleaned = detector.remove_outliers(outliers_df['is_outlier'])

        # 检查异常值被设为NaN
        assert df_cleaned.isnull().sum().sum() > 0
        assert df_cleaned.isnull().sum().sum() >= outliers_df['is_outlier'].sum()

    def test_winsorize_outliers(self, sample_data):
        """测试缩尾处理"""
        detector = OutlierDetector(sample_data)
        outliers_df = detector.detect_all_outliers()

        df_cleaned = detector.winsorize_outliers(
            outliers_df['is_outlier'],
            lower_percentile=0.01,
            upper_percentile=0.99
        )

        # 检查没有NaN
        assert df_cleaned.isnull().sum().sum() == sample_data.isnull().sum().sum()

        # 检查极值被截断
        assert df_cleaned['close'].max() <= sample_data['close'].quantile(0.99)
        assert df_cleaned['close'].min() >= sample_data['close'].quantile(0.01)

    def test_interpolate_outliers(self, sample_data):
        """测试插值处理"""
        detector = OutlierDetector(sample_data)
        outliers_df = detector.detect_all_outliers()

        df_cleaned = detector.interpolate_outliers(
            outliers_df['is_outlier'],
            method='linear'
        )

        # 检查异常值被插值填充
        assert df_cleaned.isnull().sum().sum() == 0

    def test_handle_outliers(self, sample_data):
        """测试统一处理接口"""
        detector = OutlierDetector(sample_data)
        outliers_df = detector.detect_all_outliers()

        # 测试移除方法
        df_removed = detector.handle_outliers(outliers_df['is_outlier'], method='remove')
        assert df_removed.isnull().sum().sum() > 0

        # 测试缩尾方法
        df_winsorized = detector.handle_outliers(outliers_df['is_outlier'], method='winsorize')
        assert df_winsorized.isnull().sum().sum() == sample_data.isnull().sum().sum()

        # 测试插值方法
        df_interpolated = detector.handle_outliers(outliers_df['is_outlier'], method='interpolate')
        assert df_interpolated.isnull().sum().sum() == 0


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_detect_outliers(self, sample_data):
        """测试快速检测函数"""
        outliers_df = detect_outliers(sample_data, method='both', threshold=3.0)

        assert isinstance(outliers_df, pd.DataFrame)
        assert 'is_outlier' in outliers_df.columns

    def test_clean_outliers(self, sample_data):
        """测试一键清洗函数"""
        df_cleaned = clean_outliers(
            sample_data,
            method='interpolate',
            detection_method='both',
            threshold=3.0
        )

        assert isinstance(df_cleaned, pd.DataFrame)
        assert len(df_cleaned) == len(sample_data)


class TestEdgeCases:
    """边界情况测试"""

    def test_no_outliers(self):
        """测试无异常值的情况"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        np.random.seed(42)

        # 生成非常正常的数据
        prices = 100 + np.random.normal(0, 0.1, 50)

        df = pd.DataFrame({
            'close': prices,
            'volume': np.random.uniform(5000000, 6000000, 50)
        }, index=dates)

        detector = OutlierDetector(df)
        outliers_df = detector.detect_all_outliers(price_threshold=5.0, jump_threshold=0.10)

        # 应该检测不到异常值（或很少）
        assert outliers_df['is_outlier'].sum() <= 2

    def test_all_outliers(self):
        """测试全是异常值的情况"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')

        # 生成极端随机数据
        prices = np.random.uniform(1, 1000, 50)

        df = pd.DataFrame({
            'close': prices,
            'volume': np.random.uniform(1, 1e10, 50)
        }, index=dates)

        detector = OutlierDetector(df)
        outliers_df = detector.detect_all_outliers(price_threshold=1.0, jump_threshold=0.05)

        # 应该检测到大量异常值
        assert outliers_df['is_outlier'].sum() > 10

    def test_missing_volume(self):
        """测试缺少成交量列的情况"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        prices = 100 + np.random.normal(0, 2, 50)

        df = pd.DataFrame({
            'close': prices
        }, index=dates)

        detector = OutlierDetector(df)
        outliers_df = detector.detect_all_outliers(volume_method='none')

        assert isinstance(outliers_df, pd.DataFrame)
        assert 'volume_outlier' not in outliers_df.columns

    def test_single_column(self):
        """测试单列数据"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        prices = 100 + np.random.normal(0, 5, 50)
        prices[10] = 200  # 异常值

        df = pd.DataFrame({
            'close': prices
        }, index=dates)

        detector = OutlierDetector(df, price_cols=['close'])
        outliers = detector.detect_by_iqr('close', multiplier=3.0)

        assert outliers.sum() >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
