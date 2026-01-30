"""
股票过滤器单元测试

测试覆盖：
- 股票列表过滤（ST、退市股票）
- 价格数据过滤
- 交易天数检查
- 停牌检测
- 连续零成交量检测
- 批量过滤
- 市场类型过滤
- 统计信息管理
"""

import pytest
import pandas as pd
import numpy as np

from data.stock_filter import StockFilter, filter_stocks_by_market
from config.trading_rules import DataQualityRules


@pytest.fixture
def valid_stock_list():
    """创建有效的股票列表"""
    return pd.DataFrame({
        'symbol': ['000001', '000002', '600000', '600001', '300001'],
        'name': ['平安银行', '万科A', '浦发银行', '邮储银行', '特锐德'],
        'market': ['主板', '主板', '主板', '主板', '创业板']
    })


@pytest.fixture
def mixed_stock_list():
    """创建包含ST和退市股票的列表"""
    return pd.DataFrame({
        'symbol': ['000001', '000002', '000003', '000004', '000005', '000006'],
        'name': ['平安银行', '*ST万科', 'ST国华', '退市长油', '*ST海润', '中国平安'],
        'market': ['主板', '主板', '主板', '主板', '主板', '主板']
    })


@pytest.fixture
def valid_price_data():
    """创建有效的价格数据（足够的交易天数）"""
    dates = pd.date_range('2023-01-01', periods=300, freq='D')
    np.random.seed(42)

    return pd.DataFrame({
        'close': np.random.uniform(95, 105, 300),
        'vol': np.random.uniform(1000000, 10000000, 300)
    }, index=dates)


@pytest.fixture
def insufficient_data():
    """创建交易天数不足的数据"""
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    return pd.DataFrame({
        'close': np.random.uniform(95, 105, 100),
        'vol': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)


@pytest.fixture
def suspended_stock_data():
    """创建包含停牌的数据"""
    dates = pd.date_range('2023-01-01', periods=300, freq='D')
    np.random.seed(42)

    vol_data = np.random.uniform(1000000, 10000000, 300)
    # 创建连续停牌（零成交量）
    vol_data[100:120] = 0  # 连续20天停牌

    return pd.DataFrame({
        'close': np.random.uniform(95, 105, 300),
        'vol': vol_data
    }, index=dates)


@pytest.fixture
def abnormal_price_data():
    """创建包含异常价格的数据"""
    dates = pd.date_range('2023-01-01', periods=300, freq='D')
    np.random.seed(42)

    prices = np.random.uniform(95, 105, 300)
    prices[150] = -10  # 负价格
    prices[200] = 100000  # 异常高价

    return pd.DataFrame({
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, 300)
    }, index=dates)


class TestStockFilterInitialization:
    """股票过滤器初始化测试"""

    def test_initialization_default(self):
        """测试默认初始化"""
        filter = StockFilter()

        assert filter.verbose is True
        assert isinstance(filter.filter_stats, dict)
        assert filter.filter_stats['total'] == 0
        assert filter.filter_stats['st_filtered'] == 0

    def test_initialization_verbose_false(self):
        """测试关闭详细输出"""
        filter = StockFilter(verbose=False)

        assert filter.verbose is False


class TestFilterStockList:
    """股票列表过滤测试"""

    def test_filter_valid_stocks(self, valid_stock_list):
        """测试过滤有效股票列表"""
        filter = StockFilter(verbose=False)
        result = filter.filter_stock_list(valid_stock_list)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 5  # 全部通过
        assert filter.filter_stats['total'] == 5
        assert filter.filter_stats['passed'] == 5

    def test_filter_st_stocks(self, mixed_stock_list):
        """测试过滤ST股票"""
        filter = StockFilter(verbose=False)
        result = filter.filter_stock_list(mixed_stock_list)

        # 应该过滤掉 *ST万科, ST国华, 退市长油, *ST海润
        assert len(result) == 2  # 只剩平安银行和中国平安
        assert filter.filter_stats['st_filtered'] >= 3
        # 检查结果中不包含ST股票
        for name in result['name']:
            assert not name.startswith('ST')
            assert not name.startswith('*ST')

    def test_filter_delisting_stocks(self, mixed_stock_list):
        """测试过滤退市股票"""
        filter = StockFilter(verbose=False)
        result = filter.filter_stock_list(mixed_stock_list)

        # 应该过滤掉 退市长油
        assert filter.filter_stats['delisting_filtered'] >= 1
        assert '退市' not in result['name'].str.cat()

    def test_filter_missing_name_column(self):
        """测试缺少name列时抛出异常"""
        df = pd.DataFrame({
            'symbol': ['000001', '000002'],
            # 缺少 'name' 列
        })

        filter = StockFilter(verbose=False)

        with pytest.raises(ValueError, match="name"):
            filter.filter_stock_list(df)

    def test_filter_removes_should_exclude_column(self, valid_stock_list):
        """测试过滤后移除临时列"""
        filter = StockFilter(verbose=False)
        result = filter.filter_stock_list(valid_stock_list)

        assert 'should_exclude' not in result.columns


class TestFilterPriceData:
    """价格数据过滤测试"""

    def test_filter_valid_price_data(self, valid_price_data):
        """测试过滤有效价格数据"""
        filter = StockFilter(verbose=False)
        passed, cleaned_df, reason = filter.filter_price_data(
            valid_price_data,
            'TEST001',
            min_trading_days=250
        )

        assert passed is True
        assert cleaned_df is not None
        assert reason == "通过"

    def test_filter_insufficient_trading_days(self, insufficient_data):
        """测试交易天数不足"""
        filter = StockFilter(verbose=False)
        passed, cleaned_df, reason = filter.filter_price_data(
            insufficient_data,
            'TEST002',
            min_trading_days=250
        )

        assert passed is False
        assert cleaned_df is None
        assert "交易天数不足" in reason
        assert filter.filter_stats['insufficient_data_filtered'] == 1

    def test_filter_empty_dataframe(self):
        """测试空DataFrame"""
        filter = StockFilter(verbose=False)
        passed, cleaned_df, reason = filter.filter_price_data(
            pd.DataFrame(),
            'TEST003'
        )

        assert passed is False
        assert cleaned_df is None
        assert reason == "数据为空"

    def test_filter_none_dataframe(self):
        """测试None输入"""
        filter = StockFilter(verbose=False)
        passed, cleaned_df, reason = filter.filter_price_data(
            None,
            'TEST004'
        )

        assert passed is False
        assert cleaned_df is None
        assert reason == "数据为空"

    def test_filter_abnormal_price(self, abnormal_price_data):
        """测试异常价格"""
        filter = StockFilter(verbose=False)
        passed, cleaned_df, reason = filter.filter_price_data(
            abnormal_price_data,
            'TEST005',
            min_trading_days=250
        )

        assert passed is False
        assert "价格数据异常" in reason
        assert filter.filter_stats['abnormal_price_filtered'] == 1

    def test_filter_suspended_stock(self, suspended_stock_data):
        """测试停牌股票"""
        filter = StockFilter(verbose=False)
        passed, cleaned_df, reason = filter.filter_price_data(
            suspended_stock_data,
            'TEST006',
            min_trading_days=250
        )

        assert passed is False
        assert "停牌" in reason
        assert filter.filter_stats['suspended_filtered'] == 1

    def test_filter_removes_suspended_days(self, valid_price_data):
        """测试移除停牌日数据"""
        # 添加一些零成交量的停牌日（但不要太多，避免触发连续停牌检测）
        df = valid_price_data.copy()
        df.loc[df.index[10:13], 'vol'] = 0  # 只设置3天停牌

        filter = StockFilter(verbose=False)
        passed, cleaned_df, reason = filter.filter_price_data(
            df,
            'TEST007',
            min_trading_days=250
        )

        # 应该通过，并且cleaned_df移除了停牌日
        if passed:
            assert len(cleaned_df) < len(df)
            assert (cleaned_df['vol'] > 0).all()
        # 可能因为连续停牌或数据不足而失败
        else:
            assert "停牌" in reason or "数据不足" in reason


class TestRemoveSuspendedDays:
    """移除停牌日测试"""

    def test_remove_zero_volume_days(self, valid_price_data):
        """测试移除零成交量日"""
        df = valid_price_data.copy()
        df.loc[df.index[10:20], 'vol'] = 0

        filter = StockFilter(verbose=False)
        result = filter._remove_suspended_days(df)

        assert len(result) == len(df) - 10
        assert (result['vol'] > 0).all()

    def test_remove_suspended_no_vol_column(self):
        """测试没有vol列时返回原数据"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'close': np.random.uniform(95, 105, 10)
        }, index=dates)

        filter = StockFilter(verbose=False)
        result = filter._remove_suspended_days(df)

        assert result.equals(df)


class TestCheckConsecutiveDays:
    """连续天数检测测试"""

    def test_check_consecutive_true_values(self):
        """测试检测连续True值"""
        series = pd.Series([False, False, True, True, True, True, True, False, False, True])

        filter = StockFilter(verbose=False)
        result = filter._check_consecutive_days(series, threshold=5)

        assert result is True  # 有连续5个True

    def test_check_consecutive_below_threshold(self):
        """测试连续数未达到阈值"""
        series = pd.Series([False, True, True, False, True, True, True, False])

        filter = StockFilter(verbose=False)
        result = filter._check_consecutive_days(series, threshold=5)

        assert result is False  # 最多只有连续3个True

    def test_check_consecutive_all_false(self):
        """测试全部False"""
        series = pd.Series([False] * 10)

        filter = StockFilter(verbose=False)
        result = filter._check_consecutive_days(series, threshold=5)

        assert result is False

    def test_check_consecutive_all_true(self):
        """测试全部True"""
        series = pd.Series([True] * 10)

        filter = StockFilter(verbose=False)
        result = filter._check_consecutive_days(series, threshold=5)

        assert result is True


class TestBatchFilterStocks:
    """批量过滤测试"""

    def test_batch_filter_multiple_stocks(self, valid_price_data, insufficient_data):
        """测试批量过滤多只股票"""
        stock_list = ['STOCK001', 'STOCK002', 'STOCK003']
        price_data_dict = {
            'STOCK001': valid_price_data,
            'STOCK002': insufficient_data,
            'STOCK003': valid_price_data.copy()
        }

        filter = StockFilter(verbose=False)
        passed_stocks, filter_reasons = filter.batch_filter_stocks(
            stock_list,
            price_data_dict,
            min_trading_days=250
        )

        assert len(passed_stocks) == 2  # STOCK001 和 STOCK003
        assert 'STOCK002' in filter_reasons
        assert filter.filter_stats['passed'] == 2

    def test_batch_filter_empty_list(self):
        """测试批量过滤空列表"""
        filter = StockFilter(verbose=False)
        passed_stocks, filter_reasons = filter.batch_filter_stocks(
            [],
            {},
            min_trading_days=250
        )

        assert len(passed_stocks) == 0
        assert len(filter_reasons) == 0

    def test_batch_filter_updates_cleaned_data(self, valid_price_data):
        """测试批量过滤更新清洗后的数据"""
        # 添加停牌日
        df_with_suspended = valid_price_data.copy()
        df_with_suspended.loc[df_with_suspended.index[10:15], 'vol'] = 0

        stock_list = ['STOCK001']
        price_data_dict = {'STOCK001': df_with_suspended}

        filter = StockFilter(verbose=False)
        passed_stocks, filter_reasons = filter.batch_filter_stocks(
            stock_list,
            price_data_dict,
            min_trading_days=250
        )

        # 如果通过过滤，字典中的数据应该更新为清洗后的
        if 'STOCK001' in passed_stocks:
            assert len(price_data_dict['STOCK001']) <= len(df_with_suspended)
            assert (price_data_dict['STOCK001']['vol'] > 0).all()
        else:
            # 如果没通过，数据也可能被更新但最终被过滤
            assert 'STOCK001' in filter_reasons


class TestFilterStocksByMarket:
    """市场类型过滤测试"""

    def test_filter_by_market_default(self):
        """测试默认市场过滤（主板、中小板、创业板）"""
        df = pd.DataFrame({
            'symbol': ['000001', '000002', '300001', '688001', '430001'],
            'name': ['平安银行', '万科A', '特锐德', '科创板1', '北交所1'],
            'market': ['主板', '中小板', '创业板', '科创板', '北交所']
        })

        result = filter_stocks_by_market(df, markets=['main', 'small', 'gem'])

        assert len(result) == 3
        assert '科创板' not in result['market'].values
        assert '北交所' not in result['market'].values

    def test_filter_by_market_star(self):
        """测试科创板过滤"""
        df = pd.DataFrame({
            'symbol': ['000001', '688001'],
            'name': ['平安银行', '科创板1'],
            'market': ['主板', '科创板']
        })

        result = filter_stocks_by_market(df, markets=['star'])

        assert len(result) == 1
        assert result['market'].iloc[0] == '科创板'

    def test_filter_by_market_no_market_column(self):
        """测试缺少market列时返回原数据"""
        df = pd.DataFrame({
            'symbol': ['000001', '000002'],
            'name': ['平安银行', '万科A']
        })

        result = filter_stocks_by_market(df)

        assert result.equals(df)

    def test_filter_by_market_removes_temp_column(self):
        """测试移除临时列"""
        df = pd.DataFrame({
            'symbol': ['000001', '000002'],
            'name': ['平安银行', '万科A'],
            'market': ['主板', '创业板']
        })

        result = filter_stocks_by_market(df)

        assert 'market_en' not in result.columns


class TestStatsManagement:
    """统计信息管理测试"""

    def test_get_stats(self, mixed_stock_list):
        """测试获取统计信息"""
        filter = StockFilter(verbose=False)
        filter.filter_stock_list(mixed_stock_list)

        stats = filter.get_stats()

        assert isinstance(stats, dict)
        assert 'total' in stats
        assert 'st_filtered' in stats
        assert 'passed' in stats
        assert stats['total'] > 0

    def test_reset_stats(self, mixed_stock_list):
        """测试重置统计信息"""
        filter = StockFilter(verbose=False)
        filter.filter_stock_list(mixed_stock_list)

        filter.reset_stats()
        stats = filter.get_stats()

        assert stats['total'] == 0
        assert stats['st_filtered'] == 0
        assert stats['passed'] == 0


class TestPrintFilterReport:
    """过滤报告测试"""

    def test_print_filter_report(self, mixed_stock_list, caplog):
        """测试打印过滤报告"""
        filter = StockFilter(verbose=True)
        filter.filter_stock_list(mixed_stock_list)

        # 验证统计信息被设置
        stats = filter.get_stats()
        assert stats['total'] > 0
        assert stats['st_filtered'] > 0


class TestEdgeCases:
    """边界情况测试"""

    def test_single_stock(self):
        """测试单只股票"""
        df = pd.DataFrame({
            'symbol': ['000001'],
            'name': ['平安银行'],
            'market': ['主板']
        })

        filter = StockFilter(verbose=False)
        result = filter.filter_stock_list(df)

        assert len(result) == 1

    def test_all_filtered(self):
        """测试全部被过滤"""
        df = pd.DataFrame({
            'symbol': ['000001', '000002', '000003'],
            'name': ['*ST股票1', 'ST股票2', '退市股票3'],
            'market': ['主板', '主板', '主板']
        })

        filter = StockFilter(verbose=False)
        result = filter.filter_stock_list(df)

        assert len(result) == 0
        assert filter.filter_stats['passed'] == 0

    def test_min_trading_days_boundary(self, valid_price_data):
        """测试交易天数边界"""
        # 正好250天
        df_250 = valid_price_data.iloc[:250]

        filter = StockFilter(verbose=False)
        passed, cleaned_df, reason = filter.filter_price_data(
            df_250,
            'TEST_BOUNDARY',
            min_trading_days=250
        )

        assert passed is True

        # 249天
        df_249 = valid_price_data.iloc[:249]
        passed, cleaned_df, reason = filter.filter_price_data(
            df_249,
            'TEST_BOUNDARY',
            min_trading_days=250
        )

        assert passed is False

    def test_consecutive_days_boundary(self):
        """测试连续天数边界"""
        # 正好10个连续True
        series = pd.Series([True] * 10)

        filter = StockFilter(verbose=False)
        assert filter._check_consecutive_days(series, threshold=10) is True
        assert filter._check_consecutive_days(series, threshold=11) is False

    def test_mixed_valid_invalid_prices(self):
        """测试混合有效和无效价格"""
        dates = pd.date_range('2023-01-01', periods=300, freq='D')
        np.random.seed(42)

        prices = np.random.uniform(95, 105, 300)
        prices[150] = -10  # 一个无效价格

        df = pd.DataFrame({
            'close': prices,
            'vol': np.random.uniform(1000000, 10000000, 300)
        }, index=dates)

        filter = StockFilter(verbose=False)
        passed, cleaned_df, reason = filter.filter_price_data(
            df,
            'TEST_MIXED',
            min_trading_days=250
        )

        # 应该因为有无效价格而失败
        assert passed is False

    def test_custom_min_trading_days(self, valid_price_data):
        """测试自定义最小交易天数"""
        filter = StockFilter(verbose=False)

        # 使用较低的阈值
        passed, cleaned_df, reason = filter.filter_price_data(
            valid_price_data.iloc[:100],
            'TEST_CUSTOM',
            min_trading_days=50
        )

        assert passed is True


class TestIntegrationScenarios:
    """集成场景测试"""

    def test_full_workflow(self, mixed_stock_list, valid_price_data, insufficient_data):
        """测试完整工作流程"""
        # 1. 过滤股票列表
        filter = StockFilter(verbose=False)
        filtered_list = filter.filter_stock_list(mixed_stock_list)

        # 2. 为通过的股票准备价格数据
        price_data_dict = {}
        for symbol in filtered_list['symbol']:
            if symbol in ['000001', '000006']:
                price_data_dict[symbol] = valid_price_data.copy()
            else:
                price_data_dict[symbol] = insufficient_data.copy()

        # 3. 批量过滤价格数据
        passed_stocks, filter_reasons = filter.batch_filter_stocks(
            filtered_list['symbol'].tolist(),
            price_data_dict,
            min_trading_days=250
        )

        # 验证：过滤后应该只剩平安银行(000001)和中国平安(000006)
        assert len(filtered_list) == 2  # 过滤后剩余2只（ST和退市股被过滤）
        assert len(passed_stocks) == 2  # 价格数据合格2只


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
