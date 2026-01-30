"""
缺失值处理器单元测试

测试覆盖：
- 缺失值检测
- 各种填充方法（ffill/bfill/interpolate/mean）
- 智能填充
- 缺失模式分析
"""

import pytest
import pandas as pd
import numpy as np

from data.missing_handler import MissingHandler, fill_missing, analyze_missing


@pytest.fixture
def data_with_missing():
    """创建包含缺失值的测试数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    prices = 100 + np.random.normal(0, 5, 100)
    volumes = np.random.uniform(1000000, 10000000, 100)

    df = pd.DataFrame({
        'close': prices,
        'volume': volumes
    }, index=dates)

    # 注入不同类型的缺失值
    df.loc[dates[0:3], 'close'] = np.nan  # 前导缺失
    df.loc[dates[10:15], 'close'] = np.nan  # 中间连续缺失
    df.loc[dates[30], 'close'] = np.nan  # 孤立缺失
    df.loc[dates[95:], 'close'] = np.nan  # 尾部缺失
    df.loc[dates[50], 'volume'] = np.nan  # volume孤立缺失

    return df


class TestMissingHandler:
    """缺失值处理器测试类"""

    def test_initialization(self, data_with_missing):
        """测试初始化"""
        handler = MissingHandler(data_with_missing)

        assert handler.df is not None
        assert handler.original_shape == data_with_missing.shape

    def test_detect_missing(self, data_with_missing):
        """测试缺失值检测"""
        handler = MissingHandler(data_with_missing)
        stats = handler.detect_missing()

        assert 'total_missing' in stats
        assert 'missing_rate' in stats
        assert 'column_stats' in stats
        assert stats['total_missing'] > 0
        assert 'close' in stats['column_stats']

    def test_get_missing_patterns(self, data_with_missing):
        """测试缺失模式分析"""
        handler = MissingHandler(data_with_missing)
        patterns = handler.get_missing_patterns()

        assert 'consecutive_missing' in patterns
        assert 'leading_missing' in patterns
        assert 'trailing_missing' in patterns

        # 应该检测到前导和尾部缺失
        assert 'close' in patterns['leading_missing']
        assert 'close' in patterns['trailing_missing']

    def test_fill_forward(self, data_with_missing):
        """测试前向填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.fill_forward()

        # 前导缺失不会被填充
        assert df_filled['close'].iloc[0:3].isnull().all()

        # 中间缺失应该被填充
        assert not df_filled['close'].iloc[10:15].isnull().any()

    def test_fill_backward(self, data_with_missing):
        """测试后向填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.fill_backward()

        # 尾部缺失不会被填充
        assert df_filled['close'].iloc[95:].isnull().all()

        # 前导缺失应该被填充
        assert not df_filled['close'].iloc[0:3].isnull().any()

    def test_interpolate_linear(self, data_with_missing):
        """测试线性插值"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.interpolate(method='linear')

        # 中间缺失应该被插值
        original_missing = data_with_missing['close'].isnull().sum()
        remaining_missing = df_filled['close'].isnull().sum()

        assert remaining_missing < original_missing

    def test_interpolate_with_limit(self, data_with_missing):
        """测试限制插值数量"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.interpolate(method='linear', limit=3)

        # 长间隔（5天）不应完全被填充
        assert df_filled['close'].iloc[10:15].isnull().any()

    def test_fill_with_mean_global(self, data_with_missing):
        """测试全局均值填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.fill_with_mean(window=None)

        # 所有缺失值应该被填充
        assert df_filled['close'].isnull().sum() == 0

        # 填充值应该接近均值
        mean_value = data_with_missing['close'].mean()
        filled_values = df_filled.loc[data_with_missing['close'].isnull(), 'close']
        assert all(np.isclose(filled_values, mean_value, rtol=0.01))

    def test_fill_with_mean_rolling(self, data_with_missing):
        """测试滚动均值填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.fill_with_mean(window=10)

        # 缺失值应该被填充
        assert df_filled['close'].isnull().sum() < data_with_missing['close'].isnull().sum()

    def test_fill_with_value_scalar(self, data_with_missing):
        """测试指定标量值填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.fill_with_value(value=100.0)

        # 所有缺失值应该被填充为100
        filled_values = df_filled.loc[data_with_missing['close'].isnull(), 'close']
        assert all(filled_values == 100.0)

    def test_fill_with_value_dict(self, data_with_missing):
        """测试字典值填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.fill_with_value(value={'close': 100.0, 'volume': 5000000.0})

        # close填充为100
        filled_close = df_filled.loc[data_with_missing['close'].isnull(), 'close']
        assert all(filled_close == 100.0)

        # volume填充为5000000
        filled_volume = df_filled.loc[data_with_missing['volume'].isnull(), 'volume']
        assert all(filled_volume == 5000000.0)

    def test_drop_missing_any(self, data_with_missing):
        """测试删除任意缺失值的行"""
        handler = MissingHandler(data_with_missing)
        df_dropped = handler.drop_missing(how='any')

        # 所有包含缺失值的行都被删除
        assert df_dropped.isnull().sum().sum() == 0
        assert len(df_dropped) < len(data_with_missing)

    def test_drop_missing_all(self, data_with_missing):
        """测试删除全部缺失的行"""
        # 添加全部缺失的行
        df = data_with_missing.copy()
        df.loc[df.index[5], :] = np.nan

        handler = MissingHandler(df)
        df_dropped = handler.drop_missing(how='all')

        # 只有全部缺失的行被删除
        assert len(df_dropped) == len(df) - 1

    def test_drop_missing_threshold(self, data_with_missing):
        """测试阈值删除"""
        handler = MissingHandler(data_with_missing)
        df_dropped = handler.drop_missing(threshold=2)

        # threshold=2 表示至少有2个非缺失值的行被保留
        # data_with_missing有2列，所以只有两列都非缺失的行被保留
        expected_rows = (data_with_missing.notna().sum(axis=1) >= 2).sum()
        assert len(df_dropped) == expected_rows

    def test_smart_fill(self, data_with_missing):
        """测试智能填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.smart_fill(
            leading_method='bfill',
            trailing_method='ffill',
            middle_method='interpolate',
            max_gap=5
        )

        # 前导缺失应该被后向填充
        assert not df_filled['close'].iloc[0:3].isnull().any()

        # 尾部缺失应该被前向填充
        assert not df_filled['close'].iloc[95:].isnull().any()

        # 中间小间隔应该被插值
        assert df_filled['close'].isnull().sum() < data_with_missing['close'].isnull().sum()

    def test_handle_missing_ffill(self, data_with_missing):
        """测试统一接口 - 前向填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.handle_missing(method='ffill')

        assert df_filled['close'].isnull().sum() < data_with_missing['close'].isnull().sum()

    def test_handle_missing_bfill(self, data_with_missing):
        """测试统一接口 - 后向填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.handle_missing(method='bfill')

        assert df_filled['close'].isnull().sum() < data_with_missing['close'].isnull().sum()

    def test_handle_missing_interpolate(self, data_with_missing):
        """测试统一接口 - 插值"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.handle_missing(method='interpolate')

        assert df_filled['close'].isnull().sum() < data_with_missing['close'].isnull().sum()

    def test_handle_missing_mean(self, data_with_missing):
        """测试统一接口 - 均值填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.handle_missing(method='mean')

        assert df_filled['close'].isnull().sum() == 0

    def test_handle_missing_drop(self, data_with_missing):
        """测试统一接口 - 删除"""
        handler = MissingHandler(data_with_missing)
        df_dropped = handler.handle_missing(method='drop')

        assert len(df_dropped) < len(data_with_missing)

    def test_handle_missing_smart(self, data_with_missing):
        """测试统一接口 - 智能填充"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.handle_missing(method='smart')

        assert df_filled['close'].isnull().sum() < data_with_missing['close'].isnull().sum()

    def test_get_fill_report(self, data_with_missing):
        """测试填充报告生成"""
        handler = MissingHandler(data_with_missing)
        df_filled = handler.smart_fill()

        report = handler.get_fill_report(df_filled)

        assert 'original_missing' in report
        assert 'remaining_missing' in report
        assert 'filled_count' in report
        assert 'fill_rate' in report
        assert report['filled_count'] > 0


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_fill_missing(self, data_with_missing):
        """测试快速填充函数"""
        df_filled = fill_missing(data_with_missing, method='interpolate')

        assert isinstance(df_filled, pd.DataFrame)
        assert df_filled['close'].isnull().sum() < data_with_missing['close'].isnull().sum()

    def test_analyze_missing(self, data_with_missing):
        """测试缺失分析函数"""
        analysis = analyze_missing(data_with_missing)

        assert 'stats' in analysis
        assert 'patterns' in analysis
        assert analysis['stats']['total_missing'] > 0


class TestEdgeCases:
    """边界情况测试"""

    def test_no_missing(self):
        """测试无缺失值的情况"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        df = pd.DataFrame({
            'close': np.random.uniform(90, 110, 50),
            'volume': np.random.uniform(1000000, 10000000, 50)
        }, index=dates)

        handler = MissingHandler(df)
        stats = handler.detect_missing()

        assert stats['total_missing'] == 0
        assert len(stats['column_stats']) == 0

    def test_all_missing(self):
        """测试全部缺失的情况"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        df = pd.DataFrame({
            'close': np.full(50, np.nan),
            'volume': np.full(50, np.nan)
        }, index=dates)

        handler = MissingHandler(df)
        stats = handler.detect_missing()

        assert stats['total_missing'] == 100  # 50行 x 2列
        assert stats['missing_rate'] == 100.0

    def test_single_missing(self):
        """测试单个缺失值"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        df = pd.DataFrame({
            'close': np.random.uniform(90, 110, 50),
            'volume': np.random.uniform(1000000, 10000000, 50)
        }, index=dates)

        df.loc[dates[25], 'close'] = np.nan

        handler = MissingHandler(df)
        df_filled = handler.interpolate(method='linear')

        # 单个缺失值应该被完美插值
        assert df_filled['close'].isnull().sum() == 0

    def test_large_gap(self):
        """测试大间隔缺失"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'close': np.random.uniform(90, 110, 100)
        }, index=dates)

        df.loc[dates[30:80], 'close'] = np.nan  # 50天间隔

        handler = MissingHandler(df)
        df_filled = handler.smart_fill(max_gap=10)

        # 大间隔不应被填充（max_gap=10，所以50天的间隔不会被填充）
        assert df_filled['close'].iloc[30:80].isnull().sum() >= 40

    def test_alternating_missing(self):
        """测试交替缺失"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        df = pd.DataFrame({
            'close': np.random.uniform(90, 110, 50)
        }, index=dates)

        # 每隔一天缺失
        df.loc[dates[::2], 'close'] = np.nan

        handler = MissingHandler(df)
        df_filled = handler.interpolate(method='linear', limit=1)

        # 第一个值无法插值（没有前值），其余应该被填充
        assert df_filled['close'].isnull().sum() == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
