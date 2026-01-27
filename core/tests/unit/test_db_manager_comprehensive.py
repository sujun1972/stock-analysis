#!/usr/bin/env python3
"""
DatabaseManager 完整测试套件

目标：将覆盖率从53%提升到80%+
包含：单例模式测试、委托模式测试、并发安全测试、错误处理测试
"""

import sys
import unittest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import threading
import time
import psycopg2

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


class TestDatabaseManagerComprehensive(unittest.TestCase):
    """DatabaseManager 完整测试"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*80)
        print("DatabaseManager 完整测试套件 - 目标覆盖率 80%+")
        print("="*80)

    def setUp(self):
        """每个测试前的准备"""
        from database.db_manager import DatabaseManager
        # 重置单例
        DatabaseManager.reset_instance()

    def tearDown(self):
        """每个测试后的清理"""
        from database.db_manager import DatabaseManager
        DatabaseManager.reset_instance()

    # ==================== 单例模式测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_singleton_pattern_basic(self, mock_pool):
        """测试：基本单例模式"""
        print("\n[测试1] 基本单例模式")

        from database.db_manager import DatabaseManager

        db1 = DatabaseManager()
        db2 = DatabaseManager()
        db3 = DatabaseManager()

        self.assertIs(db1, db2)
        self.assertIs(db2, db3)
        # 只创建一次连接池
        self.assertEqual(mock_pool.call_count, 1)
        print("  ✓ 单例模式测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_singleton_with_get_instance(self, mock_pool):
        """测试：通过 get_instance 获取单例"""
        print("\n[测试2] get_instance 方法")

        from database.db_manager import DatabaseManager

        db1 = DatabaseManager.get_instance()
        db2 = DatabaseManager()

        self.assertIs(db1, db2)
        print("  ✓ get_instance 测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_singleton_with_get_database(self, mock_pool):
        """测试：通过 get_database 获取单例"""
        print("\n[测试3] get_database 函数")

        from database.db_manager import get_database, DatabaseManager

        db1 = get_database()
        db2 = DatabaseManager()

        self.assertIs(db1, db2)
        print("  ✓ get_database 测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_singleton_thread_safety(self, mock_pool):
        """测试：单例模式线程安全"""
        print("\n[测试4] 线程安全测试")

        from database.db_manager import DatabaseManager

        instances = []
        lock = threading.Lock()

        def create_instance():
            db = DatabaseManager()
            with lock:
                instances.append(db)

        # 创建10个线程同时获取实例
        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证所有实例都是同一个
        first_instance = instances[0]
        for instance in instances:
            self.assertIs(instance, first_instance)

        print("  ✓ 线程安全测试通过")

    # ==================== 初始化测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_initialization_with_config(self, mock_pool):
        """测试：使用自定义配置初始化"""
        print("\n[测试5] 自定义配置初始化")

        from database.db_manager import DatabaseManager

        config = {
            'host': 'test_host',
            'port': 5433,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_pass'
        }

        db = DatabaseManager(config)

        self.assertIsNotNone(db.config)
        self.assertEqual(db.config['host'], 'test_host')
        print("  ✓ 自定义配置测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_initialization_components(self, mock_pool):
        """测试：验证所有组件初始化"""
        print("\n[测试6] 组件初始化")

        from database.db_manager import DatabaseManager

        db = DatabaseManager()

        self.assertIsNotNone(db.pool_manager)
        self.assertIsNotNone(db.table_manager)
        self.assertIsNotNone(db.insert_manager)
        self.assertIsNotNone(db.query_manager)
        print("  ✓ 组件初始化测试通过")

    # ==================== 连接池管理委托测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_get_connection_delegation(self, mock_pool):
        """测试：get_connection 委托"""
        print("\n[测试7] 获取连接委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        conn = db.get_connection()

        self.assertEqual(conn, mock_conn)
        mock_pool_instance.getconn.assert_called_once()
        print("  ✓ 获取连接委托测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_release_connection_delegation(self, mock_pool):
        """测试：release_connection 委托"""
        print("\n[测试8] 释放连接委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        db.release_connection(mock_conn)

        mock_pool_instance.putconn.assert_called_once_with(mock_conn)
        print("  ✓ 释放连接委托测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_close_all_connections_delegation(self, mock_pool):
        """测试：close_all_connections 委托"""
        print("\n[测试9] 关闭所有连接委托")

        from database.db_manager import DatabaseManager

        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        db.close_all_connections()

        mock_pool_instance.closeall.assert_called_once()
        print("  ✓ 关闭连接委托测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_get_pool_status_delegation(self, mock_pool):
        """测试：get_pool_status 委托"""
        print("\n[测试10] 连接池状态委托")

        from database.db_manager import DatabaseManager

        db = DatabaseManager()

        # Mock pool_manager 的 get_pool_status 方法
        db.pool_manager.get_pool_status = Mock(return_value={
            'active': 2,
            'idle': 8,
            'total': 10
        })

        status = db.get_pool_status()

        self.assertIsNotNone(status)
        self.assertIn('active', status)
        print("  ✓ 连接池状态测试通过")

    # ==================== 表管理委托测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_init_database_delegation(self, mock_pool):
        """测试：init_database 委托"""
        print("\n[测试11] 初始化数据库委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        db.init_database()

        # 验证执行了多个 CREATE TABLE 语句
        self.assertGreater(mock_cursor.execute.call_count, 5)
        print("  ✓ 初始化数据库测试通过")

    # ==================== 数据插入委托测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_stock_list_delegation(self, mock_execute_batch, mock_pool):
        """测试：save_stock_list 委托"""
        print("\n[测试12] 保存股票列表委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['平安银行']
        })

        db = DatabaseManager()
        count = db.save_stock_list(df)

        self.assertEqual(count, 1)
        print("  ✓ 保存股票列表测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_daily_data_delegation(self, mock_execute_batch, mock_pool):
        """测试：save_daily_data 委托"""
        print("\n[测试13] 保存日线数据委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'open': [10.0] * 5,
            'high': [15.0] * 5,
            'low': [8.0] * 5,
            'close': [12.0] * 5,
            'volume': [1000000] * 5,
            'amount': [12000000.0] * 5
        }, index=dates)

        db = DatabaseManager()
        count = db.save_daily_data(df, '000001')

        self.assertEqual(count, 5)
        print("  ✓ 保存日线数据测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_save_realtime_quote_single_delegation(self, mock_pool):
        """测试：save_realtime_quote_single 委托"""
        print("\n[测试14] 保存单条行情委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        quote = {'code': '000001', 'name': '平安银行'}

        db = DatabaseManager()
        count = db.save_realtime_quote_single(quote)

        self.assertEqual(count, 1)
        print("  ✓ 保存单条行情测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_realtime_quotes_delegation(self, mock_execute_batch, mock_pool):
        """测试：save_realtime_quotes 委托"""
        print("\n[测试15] 保存批量行情委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        df = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['平安银行', '万科A']
        })

        db = DatabaseManager()
        count = db.save_realtime_quotes(df)

        self.assertEqual(count, 2)
        print("  ✓ 保存批量行情测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('database.data_insert_manager.extras.execute_batch')
    def test_save_minute_data_delegation(self, mock_execute_batch, mock_pool):
        """测试：save_minute_data 委托"""
        print("\n[测试16] 保存分时数据委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        # 为 _update_minute_meta 设置 mock
        mock_cursor.fetchone.return_value = ('2023-01-01 09:30:00', '2023-01-01 14:55:00')
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        df = pd.DataFrame({
            'trade_time': pd.date_range('2023-01-01 09:30:00', periods=48, freq='5min'),
            'close': [10.0] * 48
        })

        db = DatabaseManager()
        count = db.save_minute_data(df, '000001', '5', '2023-01-01')

        self.assertEqual(count, 48)
        print("  ✓ 保存分时数据测试通过")

    # ==================== 数据查询委托测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('pandas.read_sql_query')
    def test_load_daily_data_delegation(self, mock_read_sql, mock_pool):
        """测试：load_daily_data 委托"""
        print("\n[测试17] 加载日线数据委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        mock_df = pd.DataFrame({'close': [10.0, 11.0]})
        mock_read_sql.return_value = mock_df

        db = DatabaseManager()
        df = db.load_daily_data('000001', '2023-01-01', '2023-01-02')

        self.assertEqual(len(df), 2)
        print("  ✓ 加载日线数据测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('pandas.read_sql_query')
    def test_get_stock_list_delegation(self, mock_read_sql, mock_pool):
        """测试：get_stock_list 委托"""
        print("\n[测试18] 获取股票列表委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        mock_df = pd.DataFrame({'code': ['000001', '000002']})
        mock_read_sql.return_value = mock_df

        db = DatabaseManager()
        df = db.get_stock_list()

        self.assertEqual(len(df), 2)
        print("  ✓ 获取股票列表测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_get_oldest_realtime_stocks_delegation(self, mock_pool):
        """测试：get_oldest_realtime_stocks 委托"""
        print("\n[测试19] 获取最旧实时股票委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [('000001',), ('000002',)]
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        codes = db.get_oldest_realtime_stocks(limit=2)

        self.assertEqual(len(codes), 2)
        print("  ✓ 获取最旧股票测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_check_daily_data_completeness_delegation(self, mock_pool):
        """测试：check_daily_data_completeness 委托"""
        print("\n[测试20] 检查数据完整性委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (100, '2023-01-01', '2023-12-31')
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        result = db.check_daily_data_completeness('000001', '20230101', '20231231')

        self.assertTrue(result['has_data'])
        print("  ✓ 检查完整性测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('pandas.read_sql_query')
    def test_load_minute_data_delegation(self, mock_read_sql, mock_pool):
        """测试：load_minute_data 委托"""
        print("\n[测试21] 加载分时数据委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        mock_df = pd.DataFrame({'close': [10.0] * 48})
        mock_read_sql.return_value = mock_df

        db = DatabaseManager()
        df = db.load_minute_data('000001', '5', '2023-01-01')

        self.assertEqual(len(df), 48)
        print("  ✓ 加载分时数据测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_check_minute_data_complete_delegation(self, mock_pool):
        """测试：check_minute_data_complete 委托"""
        print("\n[测试22] 检查分时完整性委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (True, 48, 48)
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        result = db.check_minute_data_complete('000001', '5', '2023-01-01')

        self.assertTrue(result['is_complete'])
        print("  ✓ 检查分时完整性测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_is_trading_day_delegation(self, mock_pool):
        """测试：is_trading_day 委托"""
        print("\n[测试23] 判断交易日委托")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (True,)
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        result = db.is_trading_day('2023-01-03')

        self.assertTrue(result)
        print("  ✓ 判断交易日测试通过")

    # ==================== 通用查询方法测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_execute_query_basic(self, mock_pool):
        """测试：执行查询"""
        print("\n[测试24] 执行查询")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [('000001', '平安银行'), ('000002', '万科A')]
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        result = db._execute_query("SELECT code, name FROM stock_basic LIMIT 2")

        self.assertEqual(len(result), 2)
        print("  ✓ 执行查询测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_execute_query_with_params(self, mock_pool):
        """测试：带参数执行查询"""
        print("\n[测试25] 带参数查询")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [('000001', '平安银行')]
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        result = db._execute_query(
            "SELECT code, name FROM stock_basic WHERE code = %s",
            ('000001',)
        )

        self.assertEqual(len(result), 1)
        print("  ✓ 带参数查询测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_execute_query_error_handling(self, mock_pool):
        """测试：查询错误处理"""
        print("\n[测试26] 查询错误处理")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = psycopg2.DatabaseError("Query failed")
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()

        with self.assertRaises(psycopg2.DatabaseError):
            db._execute_query("INVALID SQL")

        mock_pool_instance.putconn.assert_called_once()
        print("  ✓ 查询错误处理测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_execute_update_basic(self, mock_pool):
        """测试：执行更新"""
        print("\n[测试27] 执行更新")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        rows = db._execute_update(
            "UPDATE stock_basic SET name = %s WHERE code = %s",
            ('新名字', '000001')
        )

        self.assertEqual(rows, 1)
        mock_conn.commit.assert_called_once()
        print("  ✓ 执行更新测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_execute_update_error_handling(self, mock_pool):
        """测试：更新错误处理"""
        print("\n[测试28] 更新错误处理")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = psycopg2.DatabaseError("Update failed")
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()

        with self.assertRaises(psycopg2.DatabaseError):
            db._execute_update("INVALID UPDATE")

        mock_conn.rollback.assert_called_once()
        print("  ✓ 更新错误处理测试通过")

    # ==================== 单例重置测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_reset_instance(self, mock_pool):
        """测试：重置单例实例"""
        print("\n[测试29] 重置单例")

        from database.db_manager import DatabaseManager

        db1 = DatabaseManager()
        DatabaseManager.reset_instance()
        db2 = DatabaseManager()

        self.assertIsNot(db1, db2)
        print("  ✓ 重置单例测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_reset_instance_closes_connections(self, mock_pool):
        """测试：重置时关闭连接"""
        print("\n[测试30] 重置时关闭连接")

        from database.db_manager import DatabaseManager

        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()
        DatabaseManager.reset_instance()

        mock_pool_instance.closeall.assert_called_once()
        print("  ✓ 重置关闭连接测试通过")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDatabaseManagerComprehensive)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*80)
    print("测试总结 - DatabaseManager")
    print("="*80)
    print(f"运行: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}, 错误: {len(result.errors)}")
    if result.testsRun > 0:
        print(f"成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
