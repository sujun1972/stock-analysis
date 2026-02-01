#!/usr/bin/env python3
"""
DataQueryManager 完整测试套件

目标：将覆盖率从25%提升到80%+
包含：正常功能测试、错误处理测试、边界条件测试、SQL注入防护测试
"""

import sys
import unittest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import psycopg2

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

# 导入异常类
from src.exceptions import DatabaseError


class TestDataQueryManagerComprehensive(unittest.TestCase):
    """DataQueryManager 完整测试"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*80)
        print("DataQueryManager 完整测试套件 - 目标覆盖率 80%+")
        print("="*80)

    def setUp(self):
        """每个测试前的准备"""
        from database.connection_pool_manager import ConnectionPoolManager
        from database.data_query_manager import DataQueryManager

        # 创建 mock pool manager
        self.mock_pool_manager = Mock(spec=ConnectionPoolManager)
        self.query_manager = DataQueryManager(self.mock_pool_manager)

        # 创建 mock 连接和游标
        self.mock_cursor = Mock()
        self.mock_conn = Mock()
        self.mock_conn.cursor.return_value = self.mock_cursor
        self.mock_conn.__enter__ = Mock(return_value=self.mock_conn)
        self.mock_conn.__exit__ = Mock(return_value=False)
        self.mock_pool_manager.get_connection.return_value = self.mock_conn

    def tearDown(self):
        """每个测试后的清理"""
        self.mock_pool_manager.reset_mock()

    # ==================== load_daily_data 测试 ====================

    @patch('pandas.read_sql_query')
    def test_load_daily_data_basic(self, mock_read_sql):
        """测试：加载基本日线数据"""
        print("\n[测试1] 加载基本日线数据")

        # 创建模拟数据
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        mock_df = pd.DataFrame({
            'open': np.random.uniform(10, 20, 10),
            'high': np.random.uniform(15, 25, 10),
            'low': np.random.uniform(5, 15, 10),
            'close': np.random.uniform(10, 20, 10),
            'volume': np.random.randint(1000000, 10000000, 10),
            'amount': np.random.uniform(10000000, 100000000, 10),
            'amplitude': np.random.uniform(0, 10, 10),
            'pct_change': np.random.uniform(-5, 5, 10),
            'change': np.random.uniform(-1, 1, 10),
            'turnover': np.random.uniform(0, 10, 10)
        }, index=dates)
        mock_read_sql.return_value = mock_df

        # 调用方法
        df = self.query_manager.load_daily_data('000001')

        # 验证
        self.assertIsNotNone(df)
        self.assertEqual(len(df), 10)
        self.mock_pool_manager.get_connection.assert_called_once()
        self.mock_pool_manager.release_connection.assert_called_once()
        print("  ✓ 基本加载测试通过")

    @patch('pandas.read_sql_query')
    def test_load_daily_data_with_date_range(self, mock_read_sql):
        """测试：带日期范围的加载"""
        print("\n[测试2] 带日期范围的加载")

        mock_df = pd.DataFrame({
            'open': [10.0, 11.0],
            'close': [10.5, 11.5]
        }, index=pd.date_range('2023-01-01', periods=2, freq='D'))
        mock_read_sql.return_value = mock_df

        df = self.query_manager.load_daily_data('000001', '2023-01-01', '2023-01-02')

        self.assertIsNotNone(df)
        # 验证 SQL 查询包含日期条件
        call_args = mock_read_sql.call_args
        self.assertIn('2023-01-01', call_args[1]['params'])
        self.assertIn('2023-01-02', call_args[1]['params'])
        print("  ✓ 日期范围测试通过")

    @patch('pandas.read_sql_query')
    def test_load_daily_data_error_handling(self, mock_read_sql):
        """测试：加载数据时的错误处理"""
        print("\n[测试3] 错误处理测试")

        mock_read_sql.side_effect = Exception("Database connection failed")

        with self.assertRaises(Exception):
            self.query_manager.load_daily_data('000001')

        # 确保连接被释放
        self.mock_pool_manager.release_connection.assert_called_once()
        print("  ✓ 错误处理测试通过")

    @patch('pandas.read_sql_query')
    def test_load_daily_data_empty_result(self, mock_read_sql):
        """测试：加载空数据"""
        print("\n[测试4] 空数据测试")

        mock_df = pd.DataFrame()
        mock_read_sql.return_value = mock_df

        df = self.query_manager.load_daily_data('999999')

        self.assertIsNotNone(df)
        self.assertEqual(len(df), 0)
        print("  ✓ 空数据测试通过")

    # ==================== get_stock_list 测试 ====================

    @patch('pandas.read_sql_query')
    def test_get_stock_list_basic(self, mock_read_sql):
        """测试：获取基本股票列表"""
        print("\n[测试5] 获取基本股票列表")

        mock_df = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['平安银行', '万科A', '国华网安'],
            'market': ['主板', '主板', '主板'],
            'status': ['正常', '正常', '正常']
        })
        mock_read_sql.return_value = mock_df

        df = self.query_manager.get_stock_list()

        self.assertEqual(len(df), 3)
        self.assertIn('code', df.columns)
        print("  ✓ 基本列表测试通过")

    @patch('pandas.read_sql_query')
    def test_get_stock_list_with_market_filter(self, mock_read_sql):
        """测试：带市场过滤的股票列表"""
        print("\n[测试6] 市场过滤测试")

        mock_df = pd.DataFrame({
            'code': ['000001'],
            'name': ['平安银行'],
            'market': ['主板']
        })
        mock_read_sql.return_value = mock_df

        df = self.query_manager.get_stock_list(market='主板')

        call_args = mock_read_sql.call_args
        self.assertIn('主板', call_args[1]['params'])
        print("  ✓ 市场过滤测试通过")

    @patch('pandas.read_sql_query')
    def test_get_stock_list_error_handling(self, mock_read_sql):
        """测试：获取股票列表错误处理"""
        print("\n[测试7] 股票列表错误处理")

        mock_read_sql.side_effect = psycopg2.OperationalError("Connection lost")

        with self.assertRaises(DatabaseError) as context:
            self.query_manager.get_stock_list()

        # 验证异常细节
        self.assertEqual(context.exception.error_code, "DB_CONNECTION_ERROR")

        self.mock_pool_manager.release_connection.assert_called()
        print("  ✓ 错误处理测试通过")

    # ==================== get_oldest_realtime_stocks 测试 ====================

    def test_get_oldest_realtime_stocks_basic(self):
        """测试：获取最旧实时行情股票"""
        print("\n[测试8] 获取最旧实时行情股票")

        # 设置 mock 返回值
        self.mock_cursor.fetchall.return_value = [
            ('000001',), ('000002',), ('000003',)
        ]

        codes = self.query_manager.get_oldest_realtime_stocks(limit=3)

        self.assertEqual(len(codes), 3)
        self.assertEqual(codes, ['000001', '000002', '000003'])
        self.mock_cursor.execute.assert_called_once()
        print("  ✓ 基本功能测试通过")

    def test_get_oldest_realtime_stocks_custom_limit(self):
        """测试：自定义返回数量"""
        print("\n[测试9] 自定义返回数量")

        self.mock_cursor.fetchall.return_value = [
            ('000001',), ('000002',), ('000003',), ('000004',), ('000005',)
        ]

        codes = self.query_manager.get_oldest_realtime_stocks(limit=5)

        self.assertEqual(len(codes), 5)
        # 验证 limit 参数
        call_args = self.mock_cursor.execute.call_args
        self.assertEqual(call_args[0][1], (5,))
        print("  ✓ 自定义数量测试通过")

    def test_get_oldest_realtime_stocks_error_handling(self):
        """测试：获取最旧股票错误处理"""
        print("\n[测试10] 最旧股票错误处理")

        self.mock_cursor.execute.side_effect = Exception("Query failed")

        with self.assertRaises(Exception):
            self.query_manager.get_oldest_realtime_stocks()

        self.mock_cursor.close.assert_called_once()
        self.mock_pool_manager.release_connection.assert_called()
        print("  ✓ 错误处理测试通过")

    # ==================== check_daily_data_completeness 测试 ====================

    def test_check_daily_data_completeness_has_data(self):
        """测试：检查数据完整性 - 有数据"""
        print("\n[测试11] 数据完整性检查 - 有数据")

        # 180条记录，满足200条的80%要求（>=160），且最新日期接近结束日期
        self.mock_cursor.fetchone.return_value = (180, '2023-01-01', '2023-12-31')

        result = self.query_manager.check_daily_data_completeness(
            '000001', '20230101', '20231231', min_expected_days=200
        )

        self.assertTrue(result['has_data'])
        self.assertTrue(result['is_complete'])
        self.assertEqual(result['record_count'], 180)
        print("  ✓ 完整性检查测试通过")

    def test_check_daily_data_completeness_no_data(self):
        """测试：检查数据完整性 - 无数据"""
        print("\n[测试12] 数据完整性检查 - 无数据")

        self.mock_cursor.fetchone.return_value = (0, None, None)

        result = self.query_manager.check_daily_data_completeness(
            '999999', '20230101', '20231231'
        )

        self.assertFalse(result['has_data'])
        self.assertEqual(result['record_count'], 0)
        print("  ✓ 无数据检查通过")

    def test_check_daily_data_completeness_incomplete_data(self):
        """测试：检查数据完整性 - 数据不完整"""
        print("\n[测试13] 数据完整性检查 - 数据不完整")

        # 只有50条记录，远低于期望的200条
        self.mock_cursor.fetchone.return_value = (50, '2023-01-01', '2023-06-30')

        result = self.query_manager.check_daily_data_completeness(
            '000001', '20230101', '20231231', min_expected_days=200
        )

        self.assertTrue(result['has_data'])
        self.assertFalse(result['is_complete'])  # 不到80%，应该不完整
        print("  ✓ 不完整数据检查通过")

    def test_check_daily_data_completeness_error_handling(self):
        """测试：数据完整性检查错误处理"""
        print("\n[测试14] 完整性检查错误处理")

        self.mock_cursor.execute.side_effect = Exception("Database error")

        result = self.query_manager.check_daily_data_completeness(
            '000001', '20230101', '20231231'
        )

        self.assertFalse(result['has_data'])
        self.assertFalse(result['is_complete'])
        print("  ✓ 错误处理测试通过")

    # ==================== load_minute_data 测试 ====================

    @patch('pandas.read_sql_query')
    def test_load_minute_data_basic(self, mock_read_sql):
        """测试：加载分时数据"""
        print("\n[测试15] 加载分时数据")

        mock_df = pd.DataFrame({
            'trade_time': pd.date_range('2023-01-01 09:30:00', periods=48, freq='5min'),
            'open': np.random.uniform(10, 20, 48),
            'close': np.random.uniform(10, 20, 48)
        })
        mock_read_sql.return_value = mock_df

        df = self.query_manager.load_minute_data('000001', '5', '2023-01-01')

        self.assertEqual(len(df), 48)
        print("  ✓ 分时数据加载通过")

    @patch('pandas.read_sql_query')
    def test_load_minute_data_error_handling(self, mock_read_sql):
        """测试：分时数据加载错误处理"""
        print("\n[测试16] 分时数据错误处理")

        mock_read_sql.side_effect = Exception("Query failed")

        with self.assertRaises(Exception):
            self.query_manager.load_minute_data('000001', '5', '2023-01-01')

        self.mock_pool_manager.release_connection.assert_called()
        print("  ✓ 错误处理测试通过")

    # ==================== check_minute_data_complete 测试 ====================

    def test_check_minute_data_complete_from_meta(self):
        """测试：从元数据检查分时数据完整性"""
        print("\n[测试17] 从元数据检查完整性")

        self.mock_cursor.fetchone.return_value = (True, 48, 48)

        result = self.query_manager.check_minute_data_complete('000001', '5', '2023-01-01')

        self.assertTrue(result['is_complete'])
        self.assertEqual(result['record_count'], 48)
        self.assertEqual(result['completeness'], 100.0)
        print("  ✓ 元数据检查通过")

    def test_check_minute_data_complete_from_data_table(self):
        """测试：从数据表检查分时数据完整性"""
        print("\n[测试18] 从数据表检查完整性")

        # 第一次查询元数据返回 None，第二次查询数据表返回计数
        self.mock_cursor.fetchone.side_effect = [None, (46,)]

        result = self.query_manager.check_minute_data_complete('000001', '5', '2023-01-01')

        self.assertTrue(result['is_complete'])  # 46/48 > 95%
        self.assertEqual(result['record_count'], 46)
        print("  ✓ 数据表检查通过")

    def test_check_minute_data_complete_incomplete(self):
        """测试：检查不完整的分时数据"""
        print("\n[测试19] 检查不完整数据")

        self.mock_cursor.fetchone.return_value = (False, 30, 48)

        result = self.query_manager.check_minute_data_complete('000001', '5', '2023-01-01')

        self.assertFalse(result['is_complete'])
        self.assertLess(result['completeness'], 100.0)
        print("  ✓ 不完整数据检查通过")

    def test_check_minute_data_complete_error_handling(self):
        """测试：分时数据完整性检查错误处理"""
        print("\n[测试20] 完整性检查错误处理")

        self.mock_cursor.execute.side_effect = Exception("Database error")

        result = self.query_manager.check_minute_data_complete('000001', '5', '2023-01-01')

        self.assertFalse(result['is_complete'])
        self.assertEqual(result['record_count'], 0)
        print("  ✓ 错误处理测试通过")

    # ==================== is_trading_day 测试 ====================

    def test_is_trading_day_true(self):
        """测试：判断交易日 - 是"""
        print("\n[测试21] 判断交易日 - 是")

        self.mock_cursor.fetchone.return_value = (True,)

        result = self.query_manager.is_trading_day('2023-01-03')

        self.assertTrue(result)
        print("  ✓ 交易日判断通过")

    def test_is_trading_day_false(self):
        """测试：判断交易日 - 否"""
        print("\n[测试22] 判断交易日 - 否")

        self.mock_cursor.fetchone.return_value = (False,)

        result = self.query_manager.is_trading_day('2023-01-01')

        self.assertFalse(result)
        print("  ✓ 非交易日判断通过")

    def test_is_trading_day_no_calendar_data(self):
        """测试：判断交易日 - 无日历数据（回退到周一到周五）"""
        print("\n[测试23] 无日历数据回退测试")

        self.mock_cursor.fetchone.return_value = None

        # 测试周一（2023-01-02 是周一）
        result = self.query_manager.is_trading_day('2023-01-02')
        self.assertTrue(result)

        # 测试周六（2023-01-07 是周六）
        result = self.query_manager.is_trading_day('2023-01-07')
        self.assertFalse(result)

        print("  ✓ 回退逻辑测试通过")

    def test_is_trading_day_error_handling(self):
        """测试：判断交易日错误处理"""
        print("\n[测试24] 交易日判断错误处理")

        self.mock_cursor.execute.side_effect = Exception("Query failed")

        result = self.query_manager.is_trading_day('2023-01-01')

        # 默认返回 True
        self.assertTrue(result)
        print("  ✓ 错误处理测试通过")

    # ==================== _get_expected_minute_count 测试 ====================

    def test_get_expected_minute_count_various_periods(self):
        """测试：获取期望的分时记录数 - 各种周期"""
        print("\n[测试25] 各种周期的期望记录数")

        # 测试所有周期
        self.assertEqual(self.query_manager._get_expected_minute_count('1'), 240)
        self.assertEqual(self.query_manager._get_expected_minute_count('5'), 48)
        self.assertEqual(self.query_manager._get_expected_minute_count('15'), 16)
        self.assertEqual(self.query_manager._get_expected_minute_count('30'), 8)
        self.assertEqual(self.query_manager._get_expected_minute_count('60'), 4)

        # 测试未知周期（默认返回48）
        self.assertEqual(self.query_manager._get_expected_minute_count('unknown'), 48)

        print("  ✓ 期望记录数测试通过")

    # ==================== SQL 注入防护测试 ====================

    @patch('pandas.read_sql_query')
    def test_sql_injection_protection_load_daily_data(self, mock_read_sql):
        """测试：SQL注入防护 - load_daily_data"""
        print("\n[测试26] SQL注入防护测试 - 日线数据")

        mock_read_sql.return_value = pd.DataFrame()

        # 尝试 SQL 注入
        malicious_code = "000001'; DROP TABLE stock_daily; --"
        self.query_manager.load_daily_data(malicious_code)

        # 验证参数化查询被使用
        call_args = mock_read_sql.call_args
        self.assertIsNotNone(call_args[1].get('params'))
        self.assertIn(malicious_code, call_args[1]['params'])

        print("  ✓ SQL注入防护测试通过")

    @patch('pandas.read_sql_query')
    def test_sql_injection_protection_get_stock_list(self, mock_read_sql):
        """测试：SQL注入防护 - get_stock_list"""
        print("\n[测试27] SQL注入防护测试 - 股票列表")

        mock_read_sql.return_value = pd.DataFrame()

        malicious_market = "主板' OR '1'='1"
        self.query_manager.get_stock_list(market=malicious_market)

        # 验证参数化查询
        call_args = mock_read_sql.call_args
        self.assertIn(malicious_market, call_args[1]['params'])

        print("  ✓ SQL注入防护测试通过")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDataQueryManagerComprehensive)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*80)
    print("测试总结 - DataQueryManager")
    print("="*80)
    print(f"运行: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}, 错误: {len(result.errors)}")
    if result.testsRun > 0:
        print(f"成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
