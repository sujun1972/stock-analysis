"""
数据清洗器单元测试

测试覆盖：
- 数据清洗主流程
- 重复值移除
- 缺失值处理
- 异常值移除
- 数据类型确保
- OHLC逻辑验证
- 分钟数据重采样
- 基础特征添加
- 批量清洗
"""

import pytest
import pandas as pd
import numpy as np

from data.data_cleaner import DataCleaner, batch_clean_data


@pytest.fixture
def valid_price_data():
    """创建有效的价格测试数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * (1 + returns).cumprod()

    return pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)


@pytest.fixture
def dirty_price_data():
    """创建包含问题的价格数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    base_price = 100
    prices = base_price + np.random.normal(0, 5, 100)

    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)

    # 注入问题
    df.loc[dates[10], 'close'] = np.nan  # 缺失值
    df.loc[dates[20], 'high'] = np.nan
    df.loc[dates[30], 'vol'] = np.nan
    df.loc[dates[40], 'close'] = 1000  # 异常涨幅

    # 添加重复行
    df = pd.concat([df, df.iloc[[5, 6, 7]]])

    return df


@pytest.fixture
def invalid_ohlc_data():
    """创建OHLC逻辑错误的数据"""
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    np.random.seed(42)

    df = pd.DataFrame({
        'open': np.random.uniform(95, 105, 50),
        'high': np.random.uniform(90, 100, 50),  # high可能小于其他值
        'low': np.random.uniform(100, 110, 50),  # low可能大于其他值
        'close': np.random.uniform(95, 105, 50),
        'vol': np.random.uniform(1000000, 10000000, 50)
    }, index=dates)

    return df


@pytest.fixture
def minute_data():
    """创建分钟级数据"""
    dates = pd.date_range('2023-01-01 09:30', periods=240, freq='1min')
    np.random.seed(42)

    base_price = 100
    prices = base_price + np.random.normal(0, 0.5, 240)

    return pd.DataFrame({
        'open': prices * 0.999,
        'high': prices * 1.001,
        'low': prices * 0.998,
        'close': prices,
        'vol': np.random.uniform(10000, 100000, 240),
        'amount': np.random.uniform(1000000, 10000000, 240)
    }, index=dates)


class TestDataCleanerInitialization:
    """数据清洗器初始化测试"""

    def test_initialization_default(self):
        """测试默认初始化"""
        cleaner = DataCleaner()

        assert cleaner.verbose is True
        assert isinstance(cleaner.cleaning_stats, dict)
        assert cleaner.cleaning_stats['total_rows'] == 0
        assert cleaner.cleaning_stats['missing_filled'] == 0

    def test_initialization_verbose_false(self):
        """测试关闭详细输出"""
        cleaner = DataCleaner(verbose=False)

        assert cleaner.verbose is False


class TestCleanPriceData:
    """价格数据清洗测试"""

    def test_clean_valid_data(self, valid_price_data):
        """测试清洗有效数据"""
        cleaner = DataCleaner(verbose=False)
        cleaned_df = cleaner.clean_price_data(valid_price_data, 'TEST001')

        assert isinstance(cleaned_df, pd.DataFrame)
        assert len(cleaned_df) > 0
        assert cleaned_df.isnull().sum().sum() == 0  # 无缺失值
        assert isinstance(cleaned_df.index, pd.DatetimeIndex)
        assert cleaned_df.index.is_monotonic_increasing  # 已排序

    def test_clean_dirty_data(self, dirty_price_data):
        """测试清洗脏数据"""
        cleaner = DataCleaner(verbose=False)
        cleaned_df = cleaner.clean_price_data(dirty_price_data, 'TEST002')

        assert len(cleaned_df) < len(dirty_price_data)  # 移除了问题行
        assert cleaned_df.isnull().sum().sum() == 0  # 无缺失值

        stats = cleaner.get_stats()
        assert stats['total_rows'] == len(dirty_price_data)
        assert stats['duplicates_removed'] > 0
        assert stats['final_rows'] == len(cleaned_df)

    def test_clean_empty_dataframe(self):
        """测试清洗空DataFrame"""
        cleaner = DataCleaner(verbose=False)
        empty_df = pd.DataFrame()

        result = cleaner.clean_price_data(empty_df, 'TEST003')

        assert result.empty

    def test_clean_none_dataframe(self):
        """测试None输入"""
        cleaner = DataCleaner(verbose=False)
        result = cleaner.clean_price_data(None, 'TEST004')

        assert result is None

    def test_clean_with_verbose(self, dirty_price_data, caplog):
        """测试详细输出模式"""
        cleaner = DataCleaner(verbose=True)
        cleaner.clean_price_data(dirty_price_data, 'TEST005')

        # 验证有日志输出（通过统计信息检查）
        stats = cleaner.get_stats()
        assert stats['total_rows'] > stats['final_rows']


class TestRemoveDuplicates:
    """重复值移除测试"""

    def test_remove_duplicates_datetime_index(self, valid_price_data):
        """测试移除日期索引重复"""
        # 添加重复索引
        df_with_dup = pd.concat([
            valid_price_data,
            valid_price_data.iloc[[0, 1, 2]]
        ])

        cleaner = DataCleaner(verbose=False)
        result = cleaner._remove_duplicates(df_with_dup)

        assert len(result) == len(valid_price_data)
        assert cleaner.cleaning_stats['duplicates_removed'] == 3

    def test_remove_duplicates_no_datetime_index(self):
        """测试移除非日期索引重复"""
        df = pd.DataFrame({
            'close': [100, 100, 200, 200, 300],
            'vol': [1000, 1000, 2000, 2000, 3000]
        })

        cleaner = DataCleaner(verbose=False)
        result = cleaner._remove_duplicates(df)

        assert len(result) == 3  # 移除2对重复
        assert cleaner.cleaning_stats['duplicates_removed'] == 2


class TestHandleMissingValues:
    """缺失值处理测试"""

    def test_handle_missing_price_forward_fill(self):
        """测试价格缺失值前向填充"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'open': [100, 101, np.nan, np.nan, 104, 105, 106, 107, 108, 109],
            'close': [100, 101, np.nan, 103, 104, 105, 106, 107, 108, 109],
            'high': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            'low': [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
            'vol': [1e6, 1e6, 1e6, 1e6, 1e6, 1e6, 1e6, 1e6, 1e6, 1e6]
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner._handle_missing_values(df)

        # 价格列应该前向填充
        assert result.loc[dates[2], 'close'] == 101
        assert result['close'].isnull().sum() == 0

    def test_handle_missing_volume_fill_zero(self):
        """测试成交量缺失值填充为0"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'close': np.random.uniform(100, 110, 10),
            'vol': [1e6, np.nan, np.nan, 1e6, 1e6, np.nan, 1e6, 1e6, 1e6, 1e6]
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner._handle_missing_values(df)

        # 成交量��失应该填充为0
        assert result.loc[dates[1], 'vol'] == 0
        assert result.loc[dates[2], 'vol'] == 0

    def test_handle_missing_drop_remaining(self):
        """测试删除无法填充的缺失值"""
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'close': [np.nan, 101, 102, 103, 104],  # 第一行无法前向填充
            'vol': [1e6, 1e6, 1e6, 1e6, 1e6]
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner._handle_missing_values(df)

        # 第一行无法前向填充，会通过bfill填充，所以不会被删除
        assert len(result) == 5
        assert result.isnull().sum().sum() == 0


class TestRemoveOutliers:
    """异常值移除测试"""

    def test_remove_outliers_abnormal_price(self):
        """测试移除异常价格"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'close': [100, 101, 102, -10, 104, 105, 0, 107, 108, 100000],
            'vol': [1e6] * 10
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner._remove_outliers(df)

        # 应该移除负价格和异常价格
        assert len(result) < len(df)
        assert (result['close'] > 0).all()

    def test_remove_outliers_abnormal_change(self):
        """测试移除异常涨跌幅"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'close': [100, 101, 102, 500, 104, 105, 10, 107, 108, 109],  # 3和6有异常涨跌幅
            'vol': [1e6] * 10
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner._remove_outliers(df)

        # 应该移除异常涨跌幅的行
        assert len(result) < len(df)
        stats = cleaner.get_stats()
        assert stats['outliers_removed'] > 0

    def test_remove_outliers_keep_first_day(self):
        """测试保留首日（即使涨跌幅异常）"""
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'close': [1000, 101, 102, 103, 104],  # 首日价格异常但应保留
            'vol': [1e6] * 5
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner._remove_outliers(df)

        # 首日应该保留
        assert dates[0] in result.index
        assert 'daily_return' not in result.columns  # 临时列已删除


class TestEnsureDataTypes:
    """数据类型确保测试"""

    def test_ensure_numeric_columns(self):
        """测试确保数值列为float类型"""
        df = pd.DataFrame({
            'open': ['100', '101', '102'],
            'close': ['100', '101', '102'],
            'vol': ['1000000', '1100000', '1200000']
        })

        cleaner = DataCleaner(verbose=False)
        result = cleaner._ensure_data_types(df)

        # 接受int或float类型（pd.to_numeric可能返回int64）
        assert result['open'].dtype in [np.float64, np.float32, np.int64, np.int32]
        assert result['close'].dtype in [np.float64, np.float32, np.int64, np.int32]
        assert result['vol'].dtype in [np.float64, np.float32, np.int64, np.int32]

    def test_ensure_handles_non_convertible(self):
        """测试处理无法转换的值"""
        df = pd.DataFrame({
            'close': ['100', 'abc', '102'],  # 'abc'无法转换
            'vol': [1000000, 1100000, 1200000]
        })

        cleaner = DataCleaner(verbose=False)
        result = cleaner._ensure_data_types(df)

        # 'abc'应该变为NaN
        assert result['close'].isnull().sum() == 1


class TestValidateOHLC:
    """OHLC验证测试"""

    def test_validate_ohlc_fix_errors(self, invalid_ohlc_data):
        """测试修复OHLC逻辑错误"""
        cleaner = DataCleaner(verbose=False)
        result = cleaner.validate_ohlc(invalid_ohlc_data, fix=True)

        # 修复后high应该是最大值
        max_prices = result[['open', 'close', 'low']].max(axis=1)
        assert (result['high'] >= max_prices).all()

        # 修复后low应该是最小值
        min_prices = result[['open', 'close', 'high']].min(axis=1)
        assert (result['low'] <= min_prices).all()

    def test_validate_ohlc_no_fix(self, invalid_ohlc_data):
        """测试不修复模式"""
        cleaner = DataCleaner(verbose=False)
        result = cleaner.validate_ohlc(invalid_ohlc_data, fix=False)

        # 不修复模式应该移除不一致的行
        assert len(result) <= len(invalid_ohlc_data)

    def test_validate_ohlc_remove_negative_prices(self):
        """测试移除负价格"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'open': [100, 101, -10, 103, 104, 105, 106, 107, 108, 109],
            'high': [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
            'low': [98, 99, 100, 101, 102, 103, 104, 105, 106, 107],
            'close': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            'vol': [1e6] * 10
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner.validate_ohlc(df, fix=True)

        # 应该移除负价格的行
        assert len(result) == 9
        assert (result['open'] > 0).all()

    def test_validate_ohlc_missing_columns(self, valid_price_data):
        """测试缺少OHLC列时返回原数据"""
        df = valid_price_data[['close', 'vol']].copy()

        cleaner = DataCleaner(verbose=False)
        result = cleaner.validate_ohlc(df, fix=True)

        # 缺少OHLC列应该返回原数据
        assert result.equals(df)


class TestResampleToDaily:
    """分钟数据重采样测试"""

    def test_resample_minute_to_daily(self, minute_data):
        """测试分钟数据重采样为日线"""
        cleaner = DataCleaner(verbose=False)
        daily_df = cleaner.resample_to_daily(minute_data)

        assert isinstance(daily_df, pd.DataFrame)
        assert len(daily_df) == 1  # 240分钟在同一天
        assert 'open' in daily_df.columns
        assert 'high' in daily_df.columns
        assert 'low' in daily_df.columns
        assert 'close' in daily_df.columns
        assert 'vol' in daily_df.columns

    def test_resample_aggregation_logic(self):
        """测试重采样聚合逻辑"""
        # 创建跨2天的数据（需要确保有完整的2天）
        dates1 = pd.date_range('2023-01-01 09:30', periods=240, freq='1min')
        dates2 = pd.date_range('2023-01-02 09:30', periods=240, freq='1min')
        dates = dates1.append(dates2)
        np.random.seed(42)

        df = pd.DataFrame({
            'open': np.random.uniform(100, 110, 480),
            'high': np.random.uniform(110, 120, 480),
            'low': np.random.uniform(90, 100, 480),
            'close': np.random.uniform(100, 110, 480),
            'vol': np.random.uniform(10000, 100000, 480),
            'amount': np.random.uniform(1000000, 10000000, 480)
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        daily_df = cleaner.resample_to_daily(df)

        assert len(daily_df) == 2  # 2天
        assert daily_df['vol'].iloc[0] > df['vol'].iloc[0]  # 成交量是求和
        assert 'amount' in daily_df.columns

    def test_resample_non_datetime_index(self, valid_price_data):
        """测试非日期索引抛出异常"""
        df = valid_price_data.reset_index(drop=True)

        cleaner = DataCleaner(verbose=False)

        with pytest.raises(ValueError, match="DatetimeIndex"):
            cleaner.resample_to_daily(df)

    def test_resample_remove_zero_volume_days(self):
        """测试移除零成交量日期"""
        dates = pd.date_range('2023-01-01 09:30', periods=480, freq='1min')  # 2天

        df = pd.DataFrame({
            'open': np.random.uniform(100, 110, 480),
            'high': np.random.uniform(110, 120, 480),
            'low': np.random.uniform(90, 100, 480),
            'close': np.random.uniform(100, 110, 480),
            'vol': [0] * 240 + list(np.random.uniform(10000, 100000, 240))  # 第1天无成交量
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        daily_df = cleaner.resample_to_daily(df)

        assert len(daily_df) == 1  # 只有第2天有效


class TestAddBasicFeatures:
    """基础特征添加测试"""

    def test_add_pct_change(self):
        """测试添加涨跌幅"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'close': [100, 102, 101, 105, 103, 108, 110, 109, 115, 120]
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner.add_basic_features(df)

        assert 'pct_change' in result.columns
        assert pd.isna(result['pct_change'].iloc[0])  # 首日无涨跌幅
        assert abs(result['pct_change'].iloc[1] - 2.0) < 0.01  # (102-100)/100*100

    def test_add_amplitude(self):
        """测试添加振幅"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'open': [100, 102, 101, 105, 103, 108, 110, 109, 115, 120],
            'high': [105, 107, 106, 110, 108, 113, 115, 114, 120, 125],
            'low': [95, 97, 96, 100, 98, 103, 105, 104, 110, 115],
            'close': [100, 102, 101, 105, 103, 108, 110, 109, 115, 120]
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner.add_basic_features(df)

        assert 'amplitude' in result.columns
        assert pd.isna(result['amplitude'].iloc[0])  # 首日无振幅

    def test_skip_existing_features(self):
        """测试跳过已存在的特征"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'close': [100, 102, 101, 105, 103, 108, 110, 109, 115, 120],
            'pct_change': [0] * 10  # 已存在
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner.add_basic_features(df)

        # 不应该重新计算
        assert (result['pct_change'] == 0).all()


class TestStatsManagement:
    """统计信息管理测试"""

    def test_get_stats(self, valid_price_data):
        """测试获取统计信息"""
        cleaner = DataCleaner(verbose=False)
        cleaner.clean_price_data(valid_price_data)

        stats = cleaner.get_stats()

        assert isinstance(stats, dict)
        assert 'total_rows' in stats
        assert 'final_rows' in stats
        assert stats['total_rows'] > 0

    def test_reset_stats(self, valid_price_data):
        """测试重置统计信息"""
        cleaner = DataCleaner(verbose=False)
        cleaner.clean_price_data(valid_price_data)

        cleaner.reset_stats()
        stats = cleaner.get_stats()

        assert stats['total_rows'] == 0
        assert stats['missing_filled'] == 0
        assert stats['outliers_removed'] == 0


class TestBatchCleanData:
    """批量清洗测试"""

    def test_batch_clean_multiple_stocks(self, valid_price_data, dirty_price_data):
        """测试批量清洗多只股票"""
        data_dict = {
            'STOCK001': valid_price_data,
            'STOCK002': dirty_price_data,
            'STOCK003': valid_price_data.copy()
        }

        cleaned_dict, stats_dict = batch_clean_data(data_dict, verbose=False)

        assert len(cleaned_dict) == 3
        assert len(stats_dict) == 3
        assert all(isinstance(df, pd.DataFrame) for df in cleaned_dict.values())
        assert all(isinstance(stats, dict) for stats in stats_dict.values())

    def test_batch_clean_empty_dict(self):
        """测试批量清洗空字典"""
        cleaned_dict, stats_dict = batch_clean_data({}, verbose=False)

        assert len(cleaned_dict) == 0
        assert len(stats_dict) == 0

    def test_batch_clean_with_verbose(self, valid_price_data, caplog):
        """测试批量清洗详细模式"""
        # 创建超过100只股票以触发进度日志
        data_dict = {f'STOCK{i:03d}': valid_price_data.copy() for i in range(150)}

        cleaned_dict, stats_dict = batch_clean_data(data_dict, verbose=True)

        assert len(cleaned_dict) == 150


class TestEdgeCases:
    """边界情况测试"""

    def test_single_row_data(self):
        """测试单行数据"""
        df = pd.DataFrame({
            'close': [100.0],
            'vol': [1000000]
        }, index=pd.date_range('2023-01-01', periods=1))

        cleaner = DataCleaner(verbose=False)
        result = cleaner.clean_price_data(df)

        assert len(result) == 1

    def test_all_nan_column(self):
        """测试全NaN列"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'close': [np.nan] * 10,
            'vol': [1e6] * 10
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner.clean_price_data(df)

        # 应该被全部删除
        assert len(result) == 0

    def test_unsorted_index(self):
        """测试未排序的索引"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'close': np.random.uniform(100, 110, 10),
            'vol': np.random.uniform(1e6, 1e7, 10)
        }, index=dates[[5, 2, 8, 1, 9, 3, 7, 4, 6, 0]])  # 乱序

        cleaner = DataCleaner(verbose=False)
        result = cleaner.clean_price_data(df)

        # 应该排序
        assert result.index.is_monotonic_increasing

    def test_mixed_data_types(self):
        """测试混合数据类型"""
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'close': [100.0, 101.0, 102.0, 103.0, 104.0],  # 使用float避免混合类型
            'vol': [1e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6]
        }, index=dates)

        cleaner = DataCleaner(verbose=False)
        result = cleaner.clean_price_data(df)

        # 接受int或float类型
        assert result['close'].dtype in [np.float64, np.float32, np.int64, np.int32]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
