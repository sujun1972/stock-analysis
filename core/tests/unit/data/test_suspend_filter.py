"""
停牌股票过滤器单元测试

测试覆盖：
- 零成交量检测
- 价格不变检测
- 涨跌停检测
- 停牌期间识别
- 数据过滤
"""

import pytest
import pandas as pd
import numpy as np

from data.suspend_filter import SuspendFilter, detect_suspended_stocks, filter_suspended_data


@pytest.fixture
def sample_data_with_suspension():
    """创建带停牌的测试数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * (1 + returns).cumprod()

    # 模拟停牌: 第20-25天停牌
    prices[20:26] = prices[19]  # 价格不变

    volumes = np.random.uniform(1000000, 10000000, 100)
    volumes[20:26] = 0  # 成交量为0

    return pd.DataFrame({
        'close': prices,
        'volume': volumes
    }, index=dates)


@pytest.fixture
def multi_stock_data():
    """创建多股票面板数据"""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    stocks = ['000001', '000002', '000003']

    np.random.seed(42)
    prices_data = {}
    volumes_data = {}

    for stock in stocks:
        base_price = 100
        returns = np.random.normal(0.001, 0.02, 50)
        prices_data[stock] = base_price * (1 + returns).cumprod()
        volumes_data[stock] = np.random.uniform(1000000, 10000000, 50)

    # 000001停牌10-15天
    prices_data['000001'][10:16] = prices_data['000001'][9]
    volumes_data['000001'][10:16] = 0

    prices = pd.DataFrame(prices_data, index=dates)
    volumes = pd.DataFrame(volumes_data, index=dates)

    return prices, volumes


class TestSuspendFilterSingleStock:
    """单股票模式测试"""

    def test_initialization(self, sample_data_with_suspension):
        """测试初始化"""
        filter_obj = SuspendFilter(sample_data_with_suspension)

        assert filter_obj.single_stock_mode is True
        assert filter_obj.df is not None
        assert filter_obj.volume_col == 'volume'

    def test_detect_zero_volume(self, sample_data_with_suspension):
        """测试零成交量检测"""
        filter_obj = SuspendFilter(sample_data_with_suspension)
        zero_vol = filter_obj.detect_zero_volume(threshold=100)

        assert isinstance(zero_vol, pd.Series)
        assert zero_vol.sum() >= 6  # 至少检测到6天停牌

    def test_detect_price_unchanged(self, sample_data_with_suspension):
        """测试价格不变检测"""
        filter_obj = SuspendFilter(sample_data_with_suspension)
        unchanged = filter_obj.detect_price_unchanged(consecutive_days=3)

        assert isinstance(unchanged, pd.Series)
        assert unchanged.sum() >= 3  # 至少检测到3天连续不变

    def test_detect_limit_move(self):
        """测试涨跌停检测"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        prices = np.full(50, 100.0)

        # 注入涨停
        prices[10] = 110.0  # 涨停10%
        prices[20] = 90.0   # 跌停10%

        df = pd.DataFrame({
            'close': prices,
            'volume': np.random.uniform(1000000, 10000000, 50)
        }, index=dates)

        filter_obj = SuspendFilter(df)
        limit_dict = filter_obj.detect_limit_move(limit_threshold=0.095)

        assert 'upper_limit' in limit_dict
        assert 'lower_limit' in limit_dict
        assert limit_dict['upper_limit'].sum() >= 1
        assert limit_dict['lower_limit'].sum() >= 1

    def test_detect_all_suspended(self, sample_data_with_suspension):
        """测试综合停牌检测"""
        filter_obj = SuspendFilter(sample_data_with_suspension)
        suspended_df = filter_obj.detect_all_suspended(
            volume_threshold=100,
            consecutive_days=3
        )

        assert isinstance(suspended_df, pd.DataFrame)
        assert 'is_suspended' in suspended_df.columns
        assert 'zero_volume' in suspended_df.columns
        assert 'price_unchanged' in suspended_df.columns
        assert suspended_df['is_suspended'].sum() >= 6

    def test_get_suspension_periods(self, sample_data_with_suspension):
        """测试停牌期间识别"""
        filter_obj = SuspendFilter(sample_data_with_suspension)
        suspended_df = filter_obj.detect_all_suspended()
        periods = filter_obj.get_suspension_periods(
            suspended_df['is_suspended'],
            min_duration=3
        )

        assert isinstance(periods, list)
        assert len(periods) >= 1

        # 检查停牌期间格式
        if periods:
            start, end, days = periods[0]
            assert isinstance(days, int)
            assert days >= 3

    def test_get_suspension_summary(self, sample_data_with_suspension):
        """测试停牌摘要统计"""
        filter_obj = SuspendFilter(sample_data_with_suspension)
        suspended_df = filter_obj.detect_all_suspended()
        summary = filter_obj.get_suspension_summary(suspended_df)

        assert 'total_days' in summary
        assert 'suspended_days' in summary
        assert 'suspension_rate' in summary
        assert summary['suspended_days'] >= 6

    def test_filter_suspended(self, sample_data_with_suspension):
        """测试过滤停牌数据"""
        filter_obj = SuspendFilter(sample_data_with_suspension)
        suspended_df = filter_obj.detect_all_suspended()

        df_filtered = filter_obj.filter_suspended(
            suspended_df['is_suspended'],
            fill_value=np.nan
        )

        # 检查停牌期间被设为NaN
        assert df_filtered.isnull().sum().sum() > 0

    def test_remove_suspended_rows(self, sample_data_with_suspension):
        """测试移除停牌行"""
        filter_obj = SuspendFilter(sample_data_with_suspension)
        suspended_df = filter_obj.detect_all_suspended()

        df_filtered = filter_obj.remove_suspended_rows(suspended_df['is_suspended'])

        # 检查行数减少
        assert len(df_filtered) < len(sample_data_with_suspension)
        assert len(df_filtered) == len(sample_data_with_suspension) - suspended_df['is_suspended'].sum()


class TestSuspendFilterMultiStock:
    """多股票模式测试"""

    def test_initialization(self, multi_stock_data):
        """测试多股票初始化"""
        prices, volumes = multi_stock_data
        filter_obj = SuspendFilter(prices=prices, volumes=volumes)

        assert filter_obj.single_stock_mode is False
        assert filter_obj.prices is not None
        assert filter_obj.volumes is not None

    def test_detect_zero_volume_multi(self, multi_stock_data):
        """测试多股票零成交量检测"""
        prices, volumes = multi_stock_data
        filter_obj = SuspendFilter(prices=prices, volumes=volumes)

        zero_vol = filter_obj.detect_zero_volume(threshold=100)

        assert isinstance(zero_vol, pd.DataFrame)
        assert zero_vol.shape == prices.shape
        assert zero_vol.sum().sum() >= 6  # 至少检测到6条停牌记录

    def test_detect_price_unchanged_multi(self, multi_stock_data):
        """测试多股票价格不变检测"""
        prices, volumes = multi_stock_data
        filter_obj = SuspendFilter(prices=prices, volumes=volumes)

        unchanged = filter_obj.detect_price_unchanged(consecutive_days=3)

        assert isinstance(unchanged, pd.DataFrame)
        assert unchanged.shape == prices.shape

    def test_detect_all_suspended_multi(self, multi_stock_data):
        """测试多股票综合停牌检测"""
        prices, volumes = multi_stock_data
        filter_obj = SuspendFilter(prices=prices, volumes=volumes)

        suspended_dict = filter_obj.detect_all_suspended()

        assert isinstance(suspended_dict, dict)
        assert 'is_suspended' in suspended_dict
        assert isinstance(suspended_dict['is_suspended'], pd.DataFrame)
        assert suspended_dict['is_suspended'].sum().sum() >= 6

    def test_get_suspension_summary_multi(self, multi_stock_data):
        """测试多股票停牌摘要"""
        prices, volumes = multi_stock_data
        filter_obj = SuspendFilter(prices=prices, volumes=volumes)

        suspended_dict = filter_obj.detect_all_suspended()
        summary = filter_obj.get_suspension_summary(suspended_dict)

        assert 'total_records' in summary
        assert 'suspended_records' in summary
        assert 'by_stock' in summary
        assert '000001' in summary['by_stock']

    def test_filter_suspended_multi(self, multi_stock_data):
        """测试多股票数据过滤"""
        prices, volumes = multi_stock_data
        filter_obj = SuspendFilter(prices=prices, volumes=volumes)

        suspended_dict = filter_obj.detect_all_suspended()
        prices_filtered = filter_obj.filter_suspended(
            suspended_dict['is_suspended'],
            fill_value=np.nan
        )

        assert isinstance(prices_filtered, pd.DataFrame)
        assert prices_filtered.isnull().sum().sum() > 0


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_detect_suspended_stocks_single(self, sample_data_with_suspension):
        """测试单股票快速检测"""
        suspended_df = detect_suspended_stocks(
            df=sample_data_with_suspension,
            volume_threshold=100,
            consecutive_days=3
        )

        assert isinstance(suspended_df, pd.DataFrame)
        assert 'is_suspended' in suspended_df.columns

    def test_detect_suspended_stocks_multi(self, multi_stock_data):
        """测试多股票快速检测"""
        prices, volumes = multi_stock_data
        suspended_dict = detect_suspended_stocks(
            prices=prices,
            volumes=volumes,
            volume_threshold=100,
            consecutive_days=3
        )

        assert isinstance(suspended_dict, dict)
        assert 'is_suspended' in suspended_dict

    def test_filter_suspended_data(self, sample_data_with_suspension):
        """测试一键过滤函数"""
        df_filtered = filter_suspended_data(
            df=sample_data_with_suspension,
            volume_threshold=100,
            consecutive_days=3,
            fill_value=np.nan
        )

        assert isinstance(df_filtered, pd.DataFrame)
        assert df_filtered.isnull().sum().sum() > 0


class TestEdgeCases:
    """边界情况测试"""

    def test_no_suspension(self):
        """测试无停牌情况"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        prices = 100 + np.random.normal(0, 2, 50)
        volumes = np.random.uniform(1000000, 10000000, 50)

        df = pd.DataFrame({
            'close': prices,
            'volume': volumes
        }, index=dates)

        filter_obj = SuspendFilter(df)
        suspended_df = filter_obj.detect_all_suspended()

        # 应该检测不到停牌（或很少）
        assert suspended_df['is_suspended'].sum() <= 3

    def test_all_suspended(self):
        """测试全部停牌情况"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        prices = np.full(50, 100.0)  # 价格完全不变
        volumes = np.zeros(50)       # 成交量全为0

        df = pd.DataFrame({
            'close': prices,
            'volume': volumes
        }, index=dates)

        filter_obj = SuspendFilter(df)
        suspended_df = filter_obj.detect_all_suspended(consecutive_days=2)

        # 应该检测到大量停牌
        assert suspended_df['is_suspended'].sum() > 40

    def test_missing_volume(self):
        """测试缺少成交量列的情况"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        prices = 100 + np.random.normal(0, 2, 50)

        df = pd.DataFrame({
            'close': prices
        }, index=dates)

        filter_obj = SuspendFilter(df)
        suspended_df = filter_obj.detect_all_suspended()

        # 只能检测价格不变的停牌
        assert isinstance(suspended_df, pd.DataFrame)
        assert 'is_suspended' in suspended_df.columns


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
