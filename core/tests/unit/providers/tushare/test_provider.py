#!/usr/bin/env python3
"""
TushareProvider 单元测试

测试 Tushare 提供者的功能：
- 初始化和配置
- 获取股票列表
- 获取日线数据
- 获取分钟数据
- 获取实时行情
- 批量获取数据
- 错误处理
"""

import sys
import unittest
from datetime import datetime, date
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from src.providers.tushare.provider import TushareProvider
from src.providers.tushare.exceptions import (
    TushareDataError,
    TusharePermissionError,
    TushareRateLimitError
)


class TestTushareProvider(unittest.TestCase):
    """测试 TushareProvider 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("TushareProvider 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        # Mock TushareAPIClient
        self.mock_api_client_class = patch('src.providers.tushare.provider.TushareAPIClient')
        self.mock_api_client = self.mock_api_client_class.start()

    def tearDown(self):
        """每个测试后的清理"""
        self.mock_api_client_class.stop()

    # ========== 初始化测试 ==========

    def test_01_init_without_token(self):
        """测试1: 无 Token 初始化应失败"""
        print("\n[测试1] 无 Token 初始化应失败...")

        with self.assertRaises(ValueError):
            TushareProvider(token='')

        print("  ✓ 正确抛出 ValueError")

    def test_02_init_with_token(self):
        """测试2: 有 Token 初始化成功"""
        print("\n[测试2] 有 Token 初始化成功...")

        provider = TushareProvider(
            token='test_token_123',
            timeout=30,
            retry_count=3
        )

        self.assertEqual(provider.token, 'test_token_123')
        self.assertEqual(provider.timeout, 30)
        self.assertEqual(provider.retry_count, 3)
        self.assertIsNotNone(provider.converter)

        print("  ✓ 初始化成功")

    # ========== 股票列表测试 ==========

    def test_03_get_stock_list_success(self):
        """测试3: 成功获取股票列表"""
        print("\n[测试3] 成功获取股票列表...")

        # Mock API 返回数据
        mock_df = pd.DataFrame({
            'ts_code': ['000001.SZ', '600000.SH'],
            'symbol': ['000001', '600000'],
            'name': ['平安银行', '浦发银行'],
            'area': ['深圳', '上海'],
            'industry': ['银行', '银行'],
            'market': ['主板', '主板'],
            'list_date': ['19910403', '19991110']
        })

        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = mock_df
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')
        result = provider.get_stock_list()

        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 只股票")

    def test_04_get_stock_list_empty(self):
        """测试4: 获取空股票列表应抛出异常"""
        print("\n[测试4] 获取空股票列表应抛出异常...")

        # Mock API 返回空数据
        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = pd.DataFrame()
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')

        with self.assertRaises(TushareDataError):
            provider.get_stock_list()

        print("  ✓ 正确抛出 TushareDataError")

    def test_05_get_new_stocks(self):
        """测试5: 获取新股列表"""
        print("\n[测试5] 获取新股列表...")

        # Mock API 返回数据
        mock_df = pd.DataFrame({
            'ts_code': ['301234.SZ'],
            'name': ['新股A'],
            'ipo_date': ['20240101']
        })

        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = mock_df
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')
        result = provider.get_new_stocks(days=30)

        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)

        print(f"  ✓ 成功获取 {len(result)} 只新股")

    def test_06_get_delisted_stocks(self):
        """测试6: 获取退市股票"""
        print("\n[测试6] 获取退市股票...")

        # Mock API 返回数据
        mock_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'symbol': ['000001'],
            'name': ['退市A'],
            'list_date': ['20100101'],
            'delist_date': ['20240101'],
            'market': ['主板']
        })

        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = mock_df
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')
        result = provider.get_delisted_stocks()

        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('delist_date', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 只退市股票")

    # ========== 日线数据测试 ==========

    def test_07_get_daily_data_success(self):
        """测试7: 成功获取日线数据"""
        print("\n[测试7] 成功获取日线数据...")

        # Mock API 返回数据
        mock_df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 2,
            'trade_date': ['20240101', '20240102'],
            'open': [10.0, 10.2],
            'high': [10.5, 10.8],
            'low': [9.8, 10.0],
            'close': [10.2, 10.5],
            'pre_close': [9.9, 10.2],
            'vol': [10000.0, 12000.0],
            'amount': [100000.0, 120000.0],
            'pct_chg': [3.03, 2.94],
            'turnover': [1.5, 1.8]
        })

        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = mock_df
        mock_client_instance.daily = Mock()
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')
        result = provider.get_daily_data(
            code='000001',
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('trade_date', result.columns)
        self.assertIn('open', result.columns)
        self.assertIn('close', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 条日线数据")

    def test_08_get_daily_data_empty(self):
        """测试8: 获取空日线数据"""
        print("\n[测试8] 获取空日线数据...")

        # Mock API 返回空数据
        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = pd.DataFrame()
        mock_client_instance.daily = Mock()
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')
        result = provider.get_daily_data(code='999999')

        # 应返回空 DataFrame 而不是抛出异常
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

        print("  ✓ 空数据处理正确")

    def test_09_get_daily_batch(self):
        """测试9: 批量获取日线数据"""
        print("\n[测试9] 批量获取日线数据...")

        # Mock API 返回数据
        def mock_execute_side_effect(*args, **kwargs):
            ts_code = kwargs.get('ts_code', '')
            if '000001' in ts_code:
                return pd.DataFrame({
                    'ts_code': ['000001.SZ'],
                    'trade_date': ['20240101'],
                    'open': [10.0],
                    'close': [10.2],
                    'high': [10.5],
                    'low': [9.8],
                    'pre_close': [9.9],
                    'vol': [10000.0],
                    'amount': [100000.0],
                    'pct_chg': [3.03]
                })
            elif '600000' in ts_code:
                return pd.DataFrame({
                    'ts_code': ['600000.SH'],
                    'trade_date': ['20240101'],
                    'open': [8.0],
                    'close': [8.2],
                    'high': [8.5],
                    'low': [7.9],
                    'pre_close': [8.1],
                    'vol': [8000.0],
                    'amount': [65000.0],
                    'pct_chg': [1.23]
                })
            return pd.DataFrame()

        mock_client_instance = MagicMock()
        mock_client_instance.execute.side_effect = mock_execute_side_effect
        mock_client_instance.daily = Mock()
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')
        result = provider.get_daily_batch(
            codes=['000001', '600000'],
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        # 验证结果
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 2)
        self.assertIn('000001', result)
        self.assertIn('600000', result)

        print(f"  ✓ 成功批量获取 {len(result)} 只股票数据")

    # ========== 分钟数据测试 ==========

    def test_10_get_minute_data(self):
        """测试10: 获取分钟数据"""
        print("\n[测试10] 获取分钟数据...")

        # Mock API 返回数据
        mock_df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 2,
            'trade_time': ['2024-01-01 09:30:00', '2024-01-01 09:35:00'],
            'open': [10.0, 10.2],
            'high': [10.3, 10.5],
            'low': [9.9, 10.1],
            'close': [10.2, 10.4],
            'vol': [1000.0, 1200.0],
            'amount': [10000.0, 12000.0]
        })

        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = mock_df
        mock_client_instance.stk_mins = Mock()
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')
        result = provider.get_minute_data(
            code='000001',
            period='5',
            start_date='2024-01-01',
            end_date='2024-01-01'
        )

        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('trade_time', result.columns)
        self.assertIn('period', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 条分钟数据")

    # ========== 实时行情测试 ==========

    def test_11_get_realtime_quotes(self):
        """测试11: 获取实时行情"""
        print("\n[测试11] 获取实时行情...")

        # Mock API 返回数据
        mock_df = pd.DataFrame({
            'ts_code': ['000001.SZ', '600000.SH'],
            'name': ['平安银行', '浦发银行'],
            'price': [10.5, 8.2],
            'open': [10.0, 8.0],
            'high': [10.8, 8.5],
            'low': [9.9, 7.9],
            'pre_close': [10.2, 8.1],
            'volume': [10000.0, 8000.0],
            'amount': [100000.0, 65000.0],
            'pct_chg': [2.94, 1.23],
            'change': [0.3, 0.1]
        })

        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = mock_df
        mock_client_instance.realtime_quotes = Mock()
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')
        result = provider.get_realtime_quotes(codes=['000001', '600000'])

        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('code', result.columns)
        self.assertIn('latest_price', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 只股票实时行情")

    def test_12_get_realtime_quotes_empty(self):
        """测试12: 获取空实时行情应抛出异常"""
        print("\n[测试12] 获取空实时行情应抛出异常...")

        # Mock API 返回空数据
        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = pd.DataFrame()
        mock_client_instance.realtime_quotes = Mock()
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')

        with self.assertRaises(TushareDataError):
            provider.get_realtime_quotes()

        print("  ✓ 正确抛出 TushareDataError")

    # ========== 错误处理测试 ==========

    def test_13_permission_error_handling(self):
        """测试13: 权限错误处理"""
        print("\n[测试13] 权限错误处理...")

        # Mock API 抛出权限错误
        mock_client_instance = MagicMock()
        mock_client_instance.execute.side_effect = TusharePermissionError("积分不足")
        mock_client_instance.stock_basic = Mock()
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')

        with self.assertRaises(TusharePermissionError):
            provider.get_stock_list()

        print("  ✓ 权限错误正确传递")

    def test_14_rate_limit_error_handling(self):
        """测试14: 频率限制错误处理"""
        print("\n[测试14] 频率限制错误处理...")

        # Mock API 抛出频率限制错误
        mock_client_instance = MagicMock()
        mock_client_instance.execute.side_effect = TushareRateLimitError(
            "抱歉，您每分钟最多访问200次",
            retry_after=60
        )
        mock_client_instance.daily = Mock()
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')

        with self.assertRaises(TushareRateLimitError) as context:
            provider.get_daily_data(code='000001')

        self.assertEqual(context.exception.retry_after, 60)

        print("  ✓ 频率限制错误正确传递")

    # ========== 日期处理测试 ==========

    def test_15_date_normalization(self):
        """测试15: 日期格式标准化"""
        print("\n[测试15] 日期格式标准化...")

        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'close': [10.2],
            'high': [10.5],
            'low': [9.8],
            'pre_close': [9.9],
            'vol': [10000.0],
            'amount': [100000.0],
            'pct_chg': [3.03]
        })
        mock_client_instance.daily = Mock()
        self.mock_api_client.return_value = mock_client_instance

        provider = TushareProvider(token='test_token')

        # 测试不同的日期格式
        result1 = provider.get_daily_data(
            code='000001',
            start_date='2024-01-01',  # 带横杠
            end_date='20240131'  # 不带横杠
        )

        self.assertIsInstance(result1, pd.DataFrame)

        print("  ✓ 日期格式标准化正确")

    def test_16_repr(self):
        """测试16: 对象字符串表示"""
        print("\n[测试16] 对象字符串表示...")

        provider = TushareProvider(token='test_token_123456')
        repr_str = repr(provider)

        self.assertIn('TushareProvider', repr_str)
        self.assertIn('test_tok', repr_str)  # 应该只显示前8位
        self.assertNotIn('123456', repr_str)  # 不应显示后面的字符

        print(f"  ✓ 对象表示: {repr_str}")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTushareProvider)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
