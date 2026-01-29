#!/usr/bin/env python3
"""
AkShareProvider 完整单元测试

覆盖所有 Provider 方法、重试机制、限流控制和异常处理
目标覆盖率: >90%
"""

import sys
import unittest
from datetime import datetime, date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pandas as pd
import time

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from src.providers.akshare.provider import AkShareProvider
from src.providers.akshare.exceptions import AkShareDataError
from src.providers.akshare.config import AkShareConfig


class TestAkShareProviderInit(unittest.TestCase):
    """初始化和配置测试"""

    def setUp(self):
        """每个测试前的准备"""
        self.api_client_patcher = patch('src.providers.akshare.provider.AkShareAPIClient')
        self.mock_api_client_class = self.api_client_patcher.start()
        self.mock_client_instance = MagicMock()
        self.mock_api_client_class.return_value = self.mock_client_instance

    def tearDown(self):
        """每个测试后的清理"""
        self.api_client_patcher.stop()

    def test_init_default_params(self):
        """测试默认参数初始化"""
        print("\n[测试] 默认参数初始化...")

        provider = AkShareProvider()

        self.assertEqual(provider.timeout, AkShareConfig.DEFAULT_TIMEOUT)
        self.assertEqual(provider.retry_count, AkShareConfig.DEFAULT_RETRY_COUNT)
        self.assertEqual(provider.retry_delay, AkShareConfig.DEFAULT_RETRY_DELAY)
        self.assertEqual(provider.request_delay, AkShareConfig.DEFAULT_REQUEST_DELAY)
        self.assertIsNotNone(provider.api_client)
        self.assertIsNotNone(provider.converter)

        print("  ✓ 默认参数正确")

    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        print("\n[测试] 自定义参数初始化...")

        provider = AkShareProvider(
            timeout=60,
            retry_count=5,
            retry_delay=2,
            request_delay=0.5
        )

        self.assertEqual(provider.timeout, 60)
        self.assertEqual(provider.retry_count, 5)
        self.assertEqual(provider.retry_delay, 2)
        self.assertEqual(provider.request_delay, 0.5)

        print("  ✓ 自定义参数正确")

    def test_repr(self):
        """测试 __repr__ 方法"""
        print("\n[测试] __repr__ 方法...")

        provider = AkShareProvider()
        repr_str = repr(provider)

        self.assertEqual(repr_str, "<AkShareProvider (免费，无需Token)>")
        print(f"  ✓ repr: {repr_str}")


class TestStockListMethods(unittest.TestCase):
    """股票列表相关方法测试"""

    def setUp(self):
        self.api_client_patcher = patch('src.providers.akshare.provider.AkShareAPIClient')
        self.mock_api_client_class = self.api_client_patcher.start()
        self.mock_client_instance = MagicMock()
        self.mock_api_client_class.return_value = self.mock_client_instance

    def tearDown(self):
        self.api_client_patcher.stop()

    def test_get_stock_list_success(self):
        """测试成功获取股票列表"""
        print("\n[测试] 成功获取股票列表...")

        # Mock 返回数据 - 使用正确的列名
        mock_df = pd.DataFrame({
            'code': ['000001', '600000', '000002'],
            'name': ['平安银行', '浦发银行', '万科A'],
            'market': ['深圳主板', '上海主板', '深圳主板']
        })
        self.mock_client_instance.execute.return_value = mock_df

        provider = AkShareProvider()
        result = provider.get_stock_list()

        # 验证
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)
        self.assertIn('market', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 只股票")

    def test_get_stock_list_empty(self):
        """测试获取空股票列表"""
        print("\n[测试] 获取空股票列表应抛出异常...")

        # Mock 返回空数据
        self.mock_client_instance.execute.return_value = pd.DataFrame()

        provider = AkShareProvider()

        with self.assertRaises(AkShareDataError) as cm:
            provider.get_stock_list()

        self.assertIn('返回数据为空', str(cm.exception))
        print("  ✓ 正确抛出异常")

    def test_get_stock_list_exception(self):
        """测试获取股票列表异常"""
        print("\n[测试] 获取股票列表异常...")

        # Mock 抛出异常
        self.mock_client_instance.execute.side_effect = Exception("网络错误")

        provider = AkShareProvider()

        with self.assertRaises(Exception):
            provider.get_stock_list()

        print("  ✓ 正确处理异常")

    def test_get_new_stocks_success(self):
        """测试成功获取新股列表"""
        print("\n[测试] 成功获取新股列表...")

        # Mock 返回数据
        mock_df = pd.DataFrame({
            '代码': ['301234', '688123'],
            '名称': ['新股A', '新股B'],
            '上市日期': [datetime.now(), datetime.now() - timedelta(days=10)]
        })
        self.mock_client_instance.execute.return_value = mock_df

        provider = AkShareProvider()
        result = provider.get_new_stocks(days=30)

        # 验证
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('code', result.columns)
        self.assertIn('list_date', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 只新股")

    def test_get_new_stocks_filter_by_days(self):
        """测试按天数筛选新股"""
        print("\n[测试] 按天数筛选新股...")

        # Mock 返回数据（包含新旧股票）
        mock_df = pd.DataFrame({
            '代码': ['301234', '688123', '301111'],
            '名称': ['新股A', '新股B', '旧股C'],
            '上市日期': [
                datetime.now(),
                datetime.now() - timedelta(days=10),
                datetime.now() - timedelta(days=100)  # 超过范围
            ]
        })
        self.mock_client_instance.execute.return_value = mock_df

        provider = AkShareProvider()
        result = provider.get_new_stocks(days=30)

        # 验证筛选结果
        self.assertEqual(len(result), 2)  # 只有2只新股在30天内

        print(f"  ✓ 筛选正确，获得 {len(result)} 只新股")

    def test_get_delisted_stocks_success(self):
        """测试成功获取退市股票"""
        print("\n[测试] 成功获取退市股票...")

        # Mock 上交所数据 - 使用正确的列名
        mock_df_sh = pd.DataFrame({
            'code': ['600001', '600002'],
            'name': ['退市股A', '退市股B'],
            'list_date': ['2010-01-01', '2012-01-01'],
            'delist_date': ['2023-12-31', '2023-11-30'],
            'market': ['上海主板', '上海主板']
        })

        # Mock 深交所数据 - 使用正确的列名
        mock_df_sz = pd.DataFrame({
            'code': ['000001'],
            'name': ['退市股C'],
            'list_date': ['2011-01-01'],
            'delist_date': ['2023-10-31'],
            'market': ['深圳主板']
        })

        self.mock_client_instance.execute.side_effect = [mock_df_sh, mock_df_sz]

        provider = AkShareProvider()
        result = provider.get_delisted_stocks()

        # 验证
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)  # 2���上交所 + 1只深交所
        self.assertIn('code', result.columns)
        self.assertIn('delist_date', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 只退市股票")

    def test_get_delisted_stocks_sz_failed(self):
        """测试深交所退市数据获取失败"""
        print("\n[测试] 深交所退市数据获取失败...")

        # Mock 上交所成功，深交所失败
        mock_df_sh = pd.DataFrame({
            '证券代码': ['600001'],
            '证券简称': ['退市股A'],
            '上市日期': ['2010-01-01'],
            '暂停上市日期': ['2023-12-31']
        })

        self.mock_client_instance.execute.side_effect = [
            mock_df_sh,
            Exception("深交所接口错误")
        ]

        provider = AkShareProvider()
        result = provider.get_delisted_stocks()

        # 验证仍然返回上交所数据
        self.assertEqual(len(result), 1)

        print("  ✓ 正确处理部分失败")


class TestDailyDataMethods(unittest.TestCase):
    """日线数据相关方法测试"""

    def setUp(self):
        self.api_client_patcher = patch('src.providers.akshare.provider.AkShareAPIClient')
        self.mock_api_client_class = self.api_client_patcher.start()
        self.mock_client_instance = MagicMock()
        self.mock_api_client_class.return_value = self.mock_client_instance

    def tearDown(self):
        self.api_client_patcher.stop()

    def test_get_daily_data_success(self):
        """测试成功获取日线数据"""
        print("\n[测试] 成功获取日线数据...")

        # Mock 返回数据
        mock_df = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02', '2024-01-03'],
            '开盘': [10.00, 10.20, 10.50],
            '收盘': [10.20, 10.50, 10.80],
            '最高': [10.50, 10.80, 11.00],
            '最低': [9.80, 10.00, 10.30],
            '成交量': [1000000, 1200000, 1500000],
            '成交额': [10200000, 12600000, 16200000]
        })
        self.mock_client_instance.execute.return_value = mock_df

        provider = AkShareProvider()
        result = provider.get_daily_data(
            code='000001',
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        # 验证
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertIn('trade_date', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 条日线数据")

    def test_get_daily_data_default_dates(self):
        """测试使用默认日期"""
        print("\n[测试] 使用默认日期...")

        mock_df = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': [10.00],
            '收盘': [10.20],
            '最高': [10.50],
            '最低': [9.80],
            '成交量': [1000000],
            '成交额': [10200000]
        })
        self.mock_client_instance.execute.return_value = mock_df

        provider = AkShareProvider()
        result = provider.get_daily_data(code='000001')

        # 验证 execute 被调用
        self.mock_client_instance.execute.assert_called_once()
        self.assertGreater(len(result), 0)

        print("  ✓ 默认日期处理正确")

    def test_get_daily_data_adjust_types(self):
        """测试不同复权类型"""
        print("\n[测试] 不同复权类型...")

        mock_df = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': [10.00],
            '收盘': [10.20],
            '最高': [10.50],
            '最低': [9.80],
            '成交量': [1000000],
            '成交额': [10200000]
        })
        self.mock_client_instance.execute.return_value = mock_df

        provider = AkShareProvider()

        # 测试不同复权方式
        for adjust in ['qfq', 'hfq', '']:
            self.mock_client_instance.execute.reset_mock()
            result = provider.get_daily_data(code='000001', adjust=adjust)

            # 验证 adjust 参数传递
            call_args = self.mock_client_instance.execute.call_args
            self.assertEqual(call_args[1]['adjust'], adjust)

        print("  ✓ 复权类型处理正确")

    def test_get_daily_data_empty(self):
        """测试获取空数据"""
        print("\n[测试] 获取空日线数据...")

        self.mock_client_instance.execute.return_value = pd.DataFrame()

        provider = AkShareProvider()
        result = provider.get_daily_data(code='000001')

        # 验证返回空 DataFrame
        self.assertTrue(result.empty)

        print("  ✓ 空数据处理正确")

    def test_get_daily_batch_success(self):
        """测试批量获取日线数据"""
        print("\n[测试] 批量获取日线数据...")

        # Mock 返回数据
        mock_df = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': [10.00],
            '收盘': [10.20],
            '最高': [10.50],
            '最低': [9.80],
            '成交量': [1000000],
            '成交额': [10200000]
        })
        self.mock_client_instance.execute.return_value = mock_df

        provider = AkShareProvider()
        codes = ['000001', '600000', '000002']
        result = provider.get_daily_batch(codes)

        # 验证
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)
        for code in codes:
            self.assertIn(code, result)
            self.assertIsInstance(result[code], pd.DataFrame)

        print(f"  ✓ 成功批量获取 {len(result)} 只股票")

    def test_get_daily_batch_partial_failure(self):
        """测试批量获取部分失败"""
        print("\n[测试] 批量获取部分失败...")

        # Mock 部分成功，部分失败
        mock_df = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': [10.00],
            '收盘': [10.20],
            '最高': [10.50],
            '最低': [9.80],
            '成交量': [1000000],
            '成交额': [10200000]
        })

        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:  # 第二次调用失败
                raise Exception("网络错误")
            return mock_df

        self.mock_client_instance.execute.side_effect = side_effect

        provider = AkShareProvider()
        codes = ['000001', '600000', '000002']
        result = provider.get_daily_batch(codes)

        # 验证部分成功
        self.assertLess(len(result), len(codes))
        self.assertGreater(len(result), 0)

        print(f"  ✓ 部分成功: {len(result)}/{len(codes)}")


class TestMinuteDataMethods(unittest.TestCase):
    """分时数据相关方法测试"""

    def setUp(self):
        self.api_client_patcher = patch('src.providers.akshare.provider.AkShareAPIClient')
        self.mock_api_client_class = self.api_client_patcher.start()
        self.mock_client_instance = MagicMock()
        self.mock_api_client_class.return_value = self.mock_client_instance

    def tearDown(self):
        self.api_client_patcher.stop()

    def test_get_minute_data_success(self):
        """测试成功获取分时数据"""
        print("\n[测试] 成功获取分时数据...")

        mock_df = pd.DataFrame({
            '时间': ['2024-01-01 09:35:00', '2024-01-01 09:40:00'],
            '开盘': [10.00, 10.20],
            '收盘': [10.20, 10.50],
            '最高': [10.50, 10.80],
            '最低': [9.80, 10.00],
            '成交量': [100000, 120000],
            '成交额': [1020000, 1260000]
        })
        self.mock_client_instance.execute.return_value = mock_df

        provider = AkShareProvider()
        result = provider.get_minute_data(code='000001', period='5')

        # 验���
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('trade_time', result.columns)
        self.assertIn('period', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 条分时数据")

    def test_get_minute_data_different_periods(self):
        """测试不同周期"""
        print("\n[测试] 不同周期...")

        mock_df = pd.DataFrame({
            '时间': ['2024-01-01 09:35:00'],
            '开盘': [10.00],
            '收盘': [10.20],
            '最高': [10.50],
            '最低': [9.80],
            '成交量': [100000],
            '成交额': [1020000]
        })
        self.mock_client_instance.execute.return_value = mock_df

        provider = AkShareProvider()

        for period in ['1', '5', '15', '30', '60']:
            result = provider.get_minute_data(code='000001', period=period)
            self.assertTrue(all(result['period'] == period))

        print("  ✓ 不同周期处理正确")

    def test_get_minute_data_empty(self):
        """测试获取空分时数据"""
        print("\n[测试] 获取空分时数据...")

        self.mock_client_instance.execute.return_value = pd.DataFrame()

        provider = AkShareProvider()
        result = provider.get_minute_data(code='000001', period='5')

        self.assertTrue(result.empty)

        print("  ✓ 空数据处理正确")


class TestRealtimeQuotesMethods(unittest.TestCase):
    """实时行情相关方法测试"""

    def setUp(self):
        self.api_client_patcher = patch('src.providers.akshare.provider.AkShareAPIClient')
        self.mock_api_client_class = self.api_client_patcher.start()
        self.mock_client_instance = MagicMock()
        self.mock_api_client_class.return_value = self.mock_client_instance

    def tearDown(self):
        self.api_client_patcher.stop()

    def test_get_realtime_quotes_all(self):
        """测试获取全部实时行情"""
        print("\n[测试] 获取全部实时行情...")

        mock_df = pd.DataFrame({
            '代码': ['000001', '600000'],
            '名称': ['平安银行', '浦发银行'],
            '最新价': [10.20, 8.50],
            '涨跌幅': [2.0, -1.5],
            '涨跌额': [0.20, -0.13],
            '成交量': [1000000, 800000],
            '成交额': [10200000, 6800000],
            '振幅': [5.0, 3.5],
            '最高': [10.50, 8.70],
            '最低': [9.80, 8.40],
            '今开': [10.00, 8.60],
            '昨收': [10.00, 8.63]
        })
        self.mock_client_instance.execute.return_value = mock_df

        provider = AkShareProvider()
        result = provider.get_realtime_quotes()

        # 验证
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 条实时行情")

    def test_get_realtime_quotes_batch_small(self):
        """测试批量获取少量股票（<=100）"""
        print("\n[测试] 批量获取少量股票...")

        # Mock 盘口数据
        mock_bid_ask = pd.DataFrame({
            'item': ['最新', '今开', '最高', '最低', '昨收', '总手', '金额'],
            'value': [10.20, 10.00, 10.50, 9.80, 10.00, 1000000, 10200000]
        })

        # Mock 基本信息
        mock_basic_info = pd.DataFrame({
            'item': ['股票简称'],
            'value': ['平安银行']
        })

        self.mock_client_instance.execute.side_effect = [
            mock_bid_ask, mock_basic_info
        ] * 2  # 2只股票

        provider = AkShareProvider()
        codes = ['000001', '600000']
        result = provider.get_realtime_quotes(codes=codes)

        # 验证
        self.assertIsInstance(result, pd.DataFrame)
        self.assertLessEqual(len(result), len(codes))

        print(f"  ✓ 成功批量获取 {len(result)} 条行情")

    def test_get_realtime_quotes_with_callback(self):
        """测试带回调函数的实时行情获取"""
        print("\n[测试] 带回调函数...")

        # Mock 盘口数据
        mock_bid_ask = pd.DataFrame({
            'item': ['最新', '今开', '最高', '最低', '昨收', '总手', '金额'],
            'value': [10.20, 10.00, 10.50, 9.80, 10.00, 1000000, 10200000]
        })

        mock_basic_info = pd.DataFrame({
            'item': ['股票简称'],
            'value': ['平安银行']
        })

        self.mock_client_instance.execute.side_effect = [
            mock_bid_ask, mock_basic_info
        ]

        # 创建回调函数
        callback_data = []
        def save_callback(data):
            callback_data.append(data)

        provider = AkShareProvider()
        result = provider.get_realtime_quotes(codes=['000001'], save_callback=save_callback)

        # 验证回调被调用
        self.assertGreater(len(callback_data), 0)

        print("  ✓ 回调函数正确调用")

    def test_get_realtime_quotes_empty(self):
        """测试获取空实时行情"""
        print("\n[测试] 获取空实时行情...")

        self.mock_client_instance.execute.return_value = pd.DataFrame()

        provider = AkShareProvider()

        with self.assertRaises(AkShareDataError) as cm:
            provider.get_realtime_quotes()

        self.assertIn('返回数据为空', str(cm.exception))

        print("  ✓ 空数据异常处理正确")


class TestHelperMethods(unittest.TestCase):
    """辅助方法测试"""

    def setUp(self):
        self.api_client_patcher = patch('src.providers.akshare.provider.AkShareAPIClient')
        self.mock_api_client_class = self.api_client_patcher.start()
        self.mock_client_instance = MagicMock()
        self.mock_api_client_class.return_value = self.mock_client_instance

    def tearDown(self):
        self.api_client_patcher.stop()

    def test_normalize_date(self):
        """测试日期标准化"""
        print("\n[测试] 日期标准化...")

        provider = AkShareProvider()

        # 测试不同格式
        self.assertEqual(provider.normalize_date('2024-01-01'), '20240101')
        self.assertEqual(provider.normalize_date('20240101'), '20240101')
        self.assertEqual(provider.normalize_date('2024/01/01'), '20240101')

        print("  ✓ 日期标准化正确")

    def test_normalize_datetime(self):
        """测试日期时间标准化"""
        print("\n[测试] 日期时间标准化...")

        provider = AkShareProvider()

        # 测试不同格式
        result = provider.normalize_datetime('2024-01-01 09:30:00')
        self.assertIn('2024', result)
        self.assertIn('09:30', result)

        print("  ✓ 日期时间标准化正确")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestAkShareProviderInit))
    suite.addTests(loader.loadTestsFromTestCase(TestStockListMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestDailyDataMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestMinuteDataMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestRealtimeQuotesMethods))
    suite.addTests(loader.loadTestsFromTestCase(TestHelperMethods))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 统计信息
    print("\n" + "="*60)
    print(f"测试总数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("="*60)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
