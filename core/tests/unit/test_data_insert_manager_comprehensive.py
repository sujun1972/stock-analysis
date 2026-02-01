#!/usr/bin/env python3
"""
DataInsertManager 完整测试套件

目标：将覆盖率从43%提升到80%+
包含：正常功能测试、错误处理测试、边界条件测试、大批量插入测试、事务回滚测试
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


class TestDataInsertManagerComprehensive(unittest.TestCase):
    """DataInsertManager 完整测试"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*80)
        print("DataInsertManager 完整测试套件 - 目标覆盖率 80%+")
        print("="*80)

    def setUp(self):
        """每个测试前的准备"""
        from database.connection_pool_manager import ConnectionPoolManager
        from database.data_insert_manager import DataInsertManager

        # 创建 mock pool manager
        self.mock_pool_manager = Mock(spec=ConnectionPoolManager)
        self.insert_manager = DataInsertManager(self.mock_pool_manager)

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

    # ==================== save_stock_list 测试 ====================

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_stock_list_basic(self, mock_execute_batch):
        """测试：保存基本股票列表"""
        print("\n[测试1] 保存基本股票列表")

        df = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['平安银行', '万科A', '国华网安'],
            'market': ['主板', '主板', '主板'],
            'industry': ['银行', '房地产', '软件服务'],
            'area': ['深圳', '深圳', '北京']
        })

        count = self.insert_manager.save_stock_list(df, 'akshare')

        self.assertEqual(count, 3)
        mock_execute_batch.assert_called_once()
        self.mock_conn.commit.assert_called_once()
        print("  ✓ 基本保存测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_stock_list_with_optional_fields(self, mock_execute_batch):
        """测试：保存带可选字段的股票列表"""
        print("\n[测试2] 保存带可选字段的列表")

        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['平安银行'],
            'market': ['主板'],
            'industry': ['银行'],
            'area': ['深圳'],
            'list_date': ['2020-01-01'],
            'delist_date': [None],
            'status': ['正常']
        })

        count = self.insert_manager.save_stock_list(df, 'tushare')

        self.assertEqual(count, 1)
        self.mock_conn.commit.assert_called_once()
        print("  ✓ 可选字段测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_stock_list_empty_dataframe(self, mock_execute_batch):
        """测试：保存空DataFrame"""
        print("\n[测试3] 保存空数据")

        df = pd.DataFrame(columns=['code', 'name'])

        count = self.insert_manager.save_stock_list(df)

        self.assertEqual(count, 0)
        print("  ✓ 空数据测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_stock_list_error_handling(self, mock_execute_batch):
        """测试：保存股票列表错误处理"""
        print("\n[测试4] 错误处理测试")

        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['平安银行']
        })

        mock_execute_batch.side_effect = psycopg2.IntegrityError("Duplicate key")

        with self.assertRaises(DatabaseError) as context:
            self.insert_manager.save_stock_list(df)

        # 验证异常细节
        self.assertEqual(context.exception.error_code, "DB_INTEGRITY_ERROR")
        self.assertIn("save_stock_list", str(context.exception.context))

        self.mock_conn.rollback.assert_called_once()
        print("  ✓ 错误处理测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_stock_list_large_dataset(self, mock_execute_batch):
        """测试：保存大量股票数据"""
        print("\n[测试5] 大批量数据测试")

        # 创建5000条记录
        df = pd.DataFrame({
            'code': [f'{i:06d}' for i in range(5000)],
            'name': [f'股票{i}' for i in range(5000)],
            'market': ['主板'] * 5000,
            'industry': ['未知'] * 5000,
            'area': ['未知'] * 5000
        })

        count = self.insert_manager.save_stock_list(df)

        self.assertEqual(count, 5000)
        # 验证使用了批量插入
        call_args = mock_execute_batch.call_args
        self.assertEqual(call_args[1]['page_size'], 1000)
        print("  ✓ 大批量数据测试通过")

    # ==================== save_daily_data 测试 ====================

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_daily_data_basic(self, mock_execute_batch):
        """测试：保存基本日线数据"""
        print("\n[测试6] 保存基本日线数据")

        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'open': np.random.uniform(10, 20, 10),
            'high': np.random.uniform(15, 25, 10),
            'low': np.random.uniform(5, 15, 10),
            'close': np.random.uniform(10, 20, 10),
            'volume': np.random.randint(1000000, 10000000, 10),
            'amount': np.random.uniform(10000000, 100000000, 10)
        }, index=dates)

        count = self.insert_manager.save_daily_data(df, '000001')

        self.assertEqual(count, 10)
        mock_execute_batch.assert_called_once()
        self.mock_conn.commit.assert_called_once()
        print("  ✓ 基本保存测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_daily_data_with_trade_date_column(self, mock_execute_batch):
        """测试：保存带 trade_date 列的数据"""
        print("\n[测试7] 带 trade_date 列的数据")

        df = pd.DataFrame({
            'trade_date': ['20230101', '20230102', '20230103'],
            'open': [10.0, 11.0, 12.0],
            'high': [15.0, 16.0, 17.0],
            'low': [8.0, 9.0, 10.0],
            'close': [12.0, 13.0, 14.0],
            'volume': [1000000, 1100000, 1200000],
            'amount': [10000000, 11000000, 12000000]
        })

        count = self.insert_manager.save_daily_data(df, '000001')

        self.assertEqual(count, 3)
        print("  ✓ trade_date 列测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_daily_data_with_all_fields(self, mock_execute_batch):
        """测试：保存包含所有字段的数据"""
        print("\n[测试8] 所有字段数据")

        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'open': [10.0, 11.0, 12.0, 13.0, 14.0],
            'high': [15.0, 16.0, 17.0, 18.0, 19.0],
            'low': [8.0, 9.0, 10.0, 11.0, 12.0],
            'close': [12.0, 13.0, 14.0, 15.0, 16.0],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000],
            'amount': [10000000, 11000000, 12000000, 13000000, 14000000],
            'amplitude': [5.0, 4.5, 4.0, 3.5, 3.0],
            'pct_change': [2.0, 1.5, 1.0, 0.5, 0.0],
            'change': [0.2, 0.15, 0.1, 0.05, 0.0],
            'turnover': [5.0, 5.5, 6.0, 6.5, 7.0]
        }, index=dates)

        count = self.insert_manager.save_daily_data(df, '000001')

        self.assertEqual(count, 5)
        print("  ✓ 所有字段测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_daily_data_error_handling(self, mock_execute_batch):
        """测试：保存日线数据错误处理"""
        print("\n[测试9] 错误处理测试")

        df = pd.DataFrame({
            'open': [10.0],
            'close': [12.0]
        }, index=pd.date_range('2023-01-01', periods=1))

        mock_execute_batch.side_effect = Exception("Insert failed")

        with self.assertRaises(Exception):
            self.insert_manager.save_daily_data(df, '000001')

        self.mock_conn.rollback.assert_called_once()
        print("  ✓ 错误处理测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_daily_data_large_dataset(self, mock_execute_batch):
        """测试：保存大量日线数据（10年数据）"""
        print("\n[测试10] 大批量日线数据")

        # 10年交易日约2500条
        dates = pd.date_range('2013-01-01', periods=2500, freq='D')
        df = pd.DataFrame({
            'open': np.random.uniform(10, 20, 2500),
            'close': np.random.uniform(10, 20, 2500),
            'high': np.random.uniform(15, 25, 2500),
            'low': np.random.uniform(5, 15, 2500),
            'volume': np.random.randint(1000000, 10000000, 2500),
            'amount': np.random.uniform(10000000, 100000000, 2500)
        }, index=dates)

        count = self.insert_manager.save_daily_data(df, '000001')

        self.assertEqual(count, 2500)
        print("  ✓ 大批量数据测试通过")

    # ==================== save_realtime_quote_single 测试 ====================

    def test_save_realtime_quote_single_basic(self):
        """测试：保存单条实时行情"""
        print("\n[测试11] 保存单条实时行情")

        quote = {
            'code': '000001',
            'name': '平安银行',
            'latest_price': 12.50,
            'open': 12.00,
            'high': 13.00,
            'low': 11.50,
            'pre_close': 12.00,
            'volume': 10000000,
            'amount': 125000000.0,
            'pct_change': 4.17,
            'change_amount': 0.50,
            'turnover': 2.5,
            'amplitude': 12.5
        }

        count = self.insert_manager.save_realtime_quote_single(quote)

        self.assertEqual(count, 1)
        self.mock_cursor.execute.assert_called_once()
        self.mock_conn.commit.assert_called_once()
        print("  ✓ 单条保存测试通过")

    def test_save_realtime_quote_single_with_missing_fields(self):
        """测试：保存缺少字段的实时行情"""
        print("\n[测试12] 缺少字段的行情")

        quote = {
            'code': '000001',
            'name': '平安银行',
            'latest_price': 12.50
        }

        count = self.insert_manager.save_realtime_quote_single(quote)

        self.assertEqual(count, 1)
        print("  ✓ 缺失字段测试通过")

    def test_save_realtime_quote_single_error_handling(self):
        """测试：保存单条行情错误处理"""
        print("\n[测试13] 单条行情错误处理")

        quote = {'code': '000001', 'name': '平安银行'}

        self.mock_cursor.execute.side_effect = Exception("Insert failed")

        with self.assertRaises(Exception):
            self.insert_manager.save_realtime_quote_single(quote)

        self.mock_conn.rollback.assert_called_once()
        print("  ✓ 错误处理测试通过")

    # ==================== save_realtime_quotes 测试 ====================

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_realtime_quotes_basic(self, mock_execute_batch):
        """测试：保存批量实时行情"""
        print("\n[测试14] 保存批量实时行情")

        df = pd.DataFrame({
            'code': ['000001', '000002', '000003'],
            'name': ['平安银行', '万科A', '国华网安'],
            'latest_price': [12.50, 25.80, 35.90],
            'open': [12.00, 25.00, 35.00],
            'high': [13.00, 26.50, 37.00],
            'low': [11.50, 24.50, 34.00],
            'pre_close': [12.00, 25.00, 35.00],
            'volume': [10000000, 20000000, 5000000],
            'amount': [125000000, 515000000, 178500000]
        })

        count = self.insert_manager.save_realtime_quotes(df)

        self.assertEqual(count, 3)
        mock_execute_batch.assert_called_once()
        print("  ✓ 批量保存测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_realtime_quotes_with_chinese_columns(self, mock_execute_batch):
        """测试：保存中文列名的实时行情"""
        print("\n[测试15] 中文列名测试")

        df = pd.DataFrame({
            '代码': ['000001', '000002'],
            '名称': ['平安银行', '万科A'],
            '最新价': [12.50, 25.80],
            '今开': [12.00, 25.00],
            '最高': [13.00, 26.50],
            '最低': [11.50, 24.50],
            '昨收': [12.00, 25.00],
            '成交量': [10000000, 20000000],
            '成交额': [125000000, 515000000]
        })

        count = self.insert_manager.save_realtime_quotes(df)

        self.assertEqual(count, 2)
        print("  ✓ 中文列名测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_realtime_quotes_error_handling(self, mock_execute_batch):
        """测试：批量保存行情错误处理"""
        print("\n[测试16] 批量保存错误处理")

        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['平安银行']
        })

        mock_execute_batch.side_effect = Exception("Batch insert failed")

        with self.assertRaises(Exception):
            self.insert_manager.save_realtime_quotes(df)

        self.mock_conn.rollback.assert_called_once()
        print("  ✓ 错误处理测试通过")

    # ==================== save_minute_data 测试 ====================

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_minute_data_basic(self, mock_execute_batch):
        """测试：保存基本分时数据"""
        print("\n[测试17] 保存基本分时数据")

        df = pd.DataFrame({
            'trade_time': pd.date_range('2023-01-01 09:30:00', periods=48, freq='5min'),
            'open': np.random.uniform(10, 20, 48),
            'high': np.random.uniform(15, 25, 48),
            'low': np.random.uniform(5, 15, 48),
            'close': np.random.uniform(10, 20, 48),
            'volume': np.random.randint(10000, 100000, 48),
            'amount': np.random.uniform(100000, 1000000, 48)
        })

        # 为 _update_minute_meta 设置 mock
        self.mock_cursor.fetchone.return_value = ('2023-01-01 09:30:00', '2023-01-01 14:55:00')

        count = self.insert_manager.save_minute_data(df, '000001', '5', '2023-01-01')

        self.assertEqual(count, 48)
        mock_execute_batch.assert_called_once()
        self.mock_conn.commit.assert_called_once()
        print("  ✓ 基本保存测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_minute_data_with_all_fields(self, mock_execute_batch):
        """测试：保存包含所有字段的分时数据"""
        print("\n[测试18] 所有字段分时数据")

        df = pd.DataFrame({
            'trade_time': pd.date_range('2023-01-01 09:30:00', periods=10, freq='5min'),
            'open': np.random.uniform(10, 20, 10),
            'high': np.random.uniform(15, 25, 10),
            'low': np.random.uniform(5, 15, 10),
            'close': np.random.uniform(10, 20, 10),
            'volume': np.random.randint(10000, 100000, 10),
            'amount': np.random.uniform(100000, 1000000, 10),
            'pct_change': np.random.uniform(-5, 5, 10),
            'change_amount': np.random.uniform(-1, 1, 10)
        })

        # 为 _update_minute_meta 设置 mock
        self.mock_cursor.fetchone.return_value = ('2023-01-01 09:30:00', '2023-01-01 10:15:00')

        count = self.insert_manager.save_minute_data(df, '000001', '5', '2023-01-01')

        self.assertEqual(count, 10)
        print("  ✓ 所有字段测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_minute_data_error_handling(self, mock_execute_batch):
        """测试：保存分时数据错误处理"""
        print("\n[测试19] 分时数据错误处理")

        df = pd.DataFrame({
            'trade_time': pd.date_range('2023-01-01 09:30:00', periods=5, freq='5min'),
            'close': [10.0, 11.0, 12.0, 13.0, 14.0]
        })

        mock_execute_batch.side_effect = Exception("Insert failed")

        with self.assertRaises(Exception):
            self.insert_manager.save_minute_data(df, '000001', '5', '2023-01-01')

        self.mock_conn.rollback.assert_called_once()
        print("  ✓ 错误处理测试通过")

    # ==================== _update_minute_meta 测试 ====================

    def test_update_minute_meta_complete(self):
        """测试：更新分时元数据 - 完整数据"""
        print("\n[测试20] 更新元数据 - 完整")

        # 设置 mock 返回值
        self.mock_cursor.fetchone.return_value = (
            '2023-01-01 09:30:00', '2023-01-01 14:55:00'
        )

        # 48条5分钟数据是完整的
        self.insert_manager._update_minute_meta(
            self.mock_cursor, '000001', '2023-01-01', '5', 48
        )

        # 验证执行了两次 SQL（查询时间范围 + 插入/更新元数据）
        self.assertEqual(self.mock_cursor.execute.call_count, 2)
        print("  ✓ 完整元数据更新通过")

    def test_update_minute_meta_incomplete(self):
        """测试：更新分时元数据 - 不完整数据"""
        print("\n[测试21] 更新元数据 - 不完整")

        self.mock_cursor.fetchone.return_value = (
            '2023-01-01 09:30:00', '2023-01-01 12:00:00'
        )

        # 只有30条，不足48条的95%
        self.insert_manager._update_minute_meta(
            self.mock_cursor, '000001', '2023-01-01', '5', 30
        )

        self.assertEqual(self.mock_cursor.execute.call_count, 2)
        print("  ✓ 不完整元数据更新通过")

    # ==================== _get_expected_minute_count 测试 ====================

    def test_get_expected_minute_count_all_periods(self):
        """测试：获取所有周期的期望记录数"""
        print("\n[测试22] 所有周期期望记录数")

        self.assertEqual(self.insert_manager._get_expected_minute_count('1'), 240)
        self.assertEqual(self.insert_manager._get_expected_minute_count('5'), 48)
        self.assertEqual(self.insert_manager._get_expected_minute_count('15'), 16)
        self.assertEqual(self.insert_manager._get_expected_minute_count('30'), 8)
        self.assertEqual(self.insert_manager._get_expected_minute_count('60'), 4)
        self.assertEqual(self.insert_manager._get_expected_minute_count('unknown'), 48)

        print("  ✓ 期望记录数测试通过")

    # ==================== 边界条件和特殊情况测试 ====================

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_stock_list_with_nan_values(self, mock_execute_batch):
        """测试：保存包含NaN值的股票列表"""
        print("\n[测试23] NaN值处理")

        df = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['平安银行', np.nan],
            'market': ['主板', '主板'],
            'industry': [np.nan, '房地产'],
            'area': ['深圳', np.nan]
        })

        count = self.insert_manager.save_stock_list(df)

        self.assertEqual(count, 2)
        print("  ✓ NaN值处理测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_daily_data_with_nan_values(self, mock_execute_batch):
        """测试：保存包含NaN值的日线数据"""
        print("\n[测试24] 日线数据NaN处理")

        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'open': [10.0, np.nan, 12.0, 13.0, 14.0],
            'close': [12.0, 13.0, np.nan, 15.0, 16.0],
            'high': [15.0, 16.0, 17.0, np.nan, 19.0],
            'low': [8.0, 9.0, 10.0, 11.0, np.nan],
            'volume': [1000000, 1100000, 1200000, 1300000, 1400000],
            'amount': [10000000, 11000000, 12000000, 13000000, 14000000]
        }, index=dates)

        count = self.insert_manager.save_daily_data(df, '000001')

        self.assertEqual(count, 5)
        print("  ✓ 日线NaN处理测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_transaction_rollback_on_error(self, mock_execute_batch):
        """测试：错误时事务回滚"""
        print("\n[测试25] 事务回滚测试")

        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['平安银行']
        })

        mock_execute_batch.side_effect = psycopg2.DatabaseError("Constraint violation")

        with self.assertRaises(DatabaseError):
            self.insert_manager.save_stock_list(df)

        # 验证回滚被调用
        self.mock_conn.rollback.assert_called_once()
        # 验证连接被释放
        self.mock_pool_manager.release_connection.assert_called_once()
        print("  ✓ 事务回滚测试通过")

    @patch('database.data_insert_manager.extras.execute_batch')
    def test_connection_release_on_success(self, mock_execute_batch):
        """测试：成功时连接释放"""
        print("\n[测试26] 成功时连接释放")

        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['平安银行']
        })

        self.insert_manager.save_stock_list(df)

        # 验证连接被释放
        self.mock_pool_manager.release_connection.assert_called_once()
        self.mock_cursor.close.assert_called_once()
        print("  ✓ 连接释放测试通过")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDataInsertManagerComprehensive)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*80)
    print("测试总结 - DataInsertManager")
    print("="*80)
    print(f"运行: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}, 错误: {len(result.errors)}")
    if result.testsRun > 0:
        print(f"成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
