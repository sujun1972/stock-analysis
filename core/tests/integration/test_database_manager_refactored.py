#!/usr/bin/env python3
"""
DatabaseManager 重构版本单元测试

测试重构后的 DatabaseManager 及其组件
"""

import sys
import unittest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import psycopg2

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


class TestConnectionPoolManager(unittest.TestCase):
    """测试 ConnectionPoolManager 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("ConnectionPoolManager 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        self.config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'user': 'test_user',
            'password': 'test_password'
        }

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_01_init(self, mock_pool):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        from database.connection_pool_manager import ConnectionPoolManager

        pool_manager = ConnectionPoolManager(self.config)

        self.assertIsNotNone(pool_manager)
        self.assertEqual(pool_manager.min_conn, 5)
        self.assertEqual(pool_manager.max_conn, 50)
        mock_pool.assert_called_once()

        print("  ✓ 初始化成功")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_02_get_connection(self, mock_pool):
        """测试2: 获取连接"""
        print("\n[测试2] 获取连接...")

        from database.connection_pool_manager import ConnectionPoolManager

        # 设置 mock
        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        pool_manager = ConnectionPoolManager(self.config)
        conn = pool_manager.get_connection()

        self.assertEqual(conn, mock_conn)
        mock_pool_instance.getconn.assert_called_once()

        print("  ✓ 获取连接成功")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_03_release_connection(self, mock_pool):
        """测试3: 释放连接"""
        print("\n[测试3] 释放连接...")

        from database.connection_pool_manager import ConnectionPoolManager

        # 设置 mock
        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance

        pool_manager = ConnectionPoolManager(self.config)
        pool_manager.release_connection(mock_conn)

        mock_pool_instance.putconn.assert_called_once_with(mock_conn)

        print("  ✓ 释放连接成功")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_04_close_all_connections(self, mock_pool):
        """测试4: 关闭所有连接"""
        print("\n[测试4] 关闭所有连接...")

        from database.connection_pool_manager import ConnectionPoolManager

        # 设置 mock
        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance

        pool_manager = ConnectionPoolManager(self.config)
        pool_manager.close_all_connections()

        mock_pool_instance.closeall.assert_called_once()

        print("  ✓ 关闭所有连接成功")


class TestTableManager(unittest.TestCase):
    """测试 TableManager 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("TableManager 单元测试")
        print("="*60)

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_01_init(self, mock_pool):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        from database.connection_pool_manager import ConnectionPoolManager
        from database.table_manager import TableManager

        pool_manager = ConnectionPoolManager({'host': 'localhost', 'port': 5432, 'database': 'test', 'user': 'test', 'password': 'test'})
        table_manager = TableManager(pool_manager)

        self.assertIsNotNone(table_manager)
        self.assertEqual(table_manager.pool_manager, pool_manager)

        print("  ✓ 初始化成功")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_02_create_tables(self, mock_pool):
        """测试2: 创建表"""
        print("\n[测试2] 创建表...")

        from database.connection_pool_manager import ConnectionPoolManager
        from database.table_manager import TableManager

        # 设置 mock
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        pool_manager = ConnectionPoolManager({'host': 'localhost', 'port': 5432, 'database': 'test', 'user': 'test', 'password': 'test'})
        table_manager = TableManager(pool_manager)

        # 调用 init_all_tables
        table_manager.init_all_tables()

        # 验证执行了多个 CREATE TABLE 语句
        self.assertGreater(mock_cursor.execute.call_count, 5)
        mock_conn.commit.assert_called_once()

        print("  ✓ 创建表成功")


class TestDataInsertManager(unittest.TestCase):
    """测试 DataInsertManager 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataInsertManager 单元测试")
        print("="*60)

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_01_save_stock_list(self, mock_pool):
        """测试1: 保存股票列表"""
        print("\n[测试1] 保存股票列表...")

        from database.connection_pool_manager import ConnectionPoolManager
        from database.data_insert_manager import DataInsertManager

        # 创建测试数据
        df = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['平安银行', '万科A'],
            'market': ['主板', '主板'],
            'industry': ['银行', '房地产'],
            'area': ['深圳', '深圳']
        })

        # 设置 mock
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        pool_manager = ConnectionPoolManager({'host': 'localhost', 'port': 5432, 'database': 'test', 'user': 'test', 'password': 'test'})
        insert_manager = DataInsertManager(pool_manager)

        # 使用 patch 来模拟 extras.execute_batch
        with patch('database.data_insert_manager.extras.execute_batch'):
            count = insert_manager.save_stock_list(df)

        self.assertEqual(count, 2)
        mock_conn.commit.assert_called_once()

        print("  ✓ 保存股票列表成功")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_02_save_daily_data(self, mock_pool):
        """测试2: 保存日线数据"""
        print("\n[测试2] 保存日线数据...")

        from database.connection_pool_manager import ConnectionPoolManager
        from database.data_insert_manager import DataInsertManager

        # 创建测试数据
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'open': np.random.uniform(10, 20, 10),
            'high': np.random.uniform(15, 25, 10),
            'low': np.random.uniform(5, 15, 10),
            'close': np.random.uniform(10, 20, 10),
            'volume': np.random.randint(1000000, 10000000, 10),
            'amount': np.random.uniform(10000000, 100000000, 10)
        }, index=dates)

        # 设置 mock
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        pool_manager = ConnectionPoolManager({'host': 'localhost', 'port': 5432, 'database': 'test', 'user': 'test', 'password': 'test'})
        insert_manager = DataInsertManager(pool_manager)

        # 使用 patch 来模拟 extras.execute_batch
        with patch('database.data_insert_manager.extras.execute_batch'):
            count = insert_manager.save_daily_data(df, '000001')

        self.assertEqual(count, 10)
        mock_conn.commit.assert_called_once()

        print("  ✓ 保存日线数据成功")


class TestDataQueryManager(unittest.TestCase):
    """测试 DataQueryManager 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataQueryManager 单元测试")
        print("="*60)

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('pandas.read_sql_query')
    def test_01_load_daily_data(self, mock_read_sql, mock_pool):
        """测试1: 加载日线数据"""
        print("\n[测试1] 加载日线数据...")

        from database.connection_pool_manager import ConnectionPoolManager
        from database.data_query_manager import DataQueryManager

        # 创建模拟数据
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        mock_df = pd.DataFrame({
            'open': np.random.uniform(10, 20, 10),
            'close': np.random.uniform(10, 20, 10)
        }, index=dates)
        mock_read_sql.return_value = mock_df

        # 设置 mock
        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        pool_manager = ConnectionPoolManager({'host': 'localhost', 'port': 5432, 'database': 'test', 'user': 'test', 'password': 'test'})
        query_manager = DataQueryManager(pool_manager)

        df = query_manager.load_daily_data('000001', '2023-01-01', '2023-01-10')

        self.assertIsNotNone(df)
        self.assertEqual(len(df), 10)

        print("  ✓ 加载日线数据成功")


class TestDatabaseManager(unittest.TestCase):
    """测试重构后的 DatabaseManager 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DatabaseManager (重构版本) 单元测试")
        print("="*60)

    def tearDown(self):
        """每个测试后的清理"""
        # 重置单例
        from database.db_manager import DatabaseManager
        DatabaseManager.reset_instance()

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_01_singleton_pattern(self, mock_pool):
        """测试1: 单例模式"""
        print("\n[测试1] 单例模式...")

        from database.db_manager import DatabaseManager

        db1 = DatabaseManager()
        db2 = DatabaseManager()

        self.assertIs(db1, db2)
        print("  ✓ 单例模式正常工作")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_02_component_initialization(self, mock_pool):
        """测试2: 组件初始化"""
        print("\n[测试2] 组件初始化...")

        from database.db_manager import DatabaseManager

        db = DatabaseManager()

        self.assertIsNotNone(db.pool_manager)
        self.assertIsNotNone(db.table_manager)
        self.assertIsNotNone(db.insert_manager)
        self.assertIsNotNone(db.query_manager)

        print("  ✓ 所有组件初始化成功")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_03_delegation_pattern(self, mock_pool):
        """测试3: 委托模式"""
        print("\n[测试3] 委托模式...")

        from database.db_manager import DatabaseManager

        # 设置 mock
        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()

        # 测试连接池委托
        conn = db.get_connection()
        self.assertEqual(conn, mock_conn)

        # 测试释放连接委托
        db.release_connection(conn)
        mock_pool_instance.putconn.assert_called_once_with(conn)

        print("  ✓ 委托模式正常工作")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestConnectionPoolManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTableManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataInsertManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataQueryManager))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDatabaseManager))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"运行: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}, 错误: {len(result.errors)}")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
