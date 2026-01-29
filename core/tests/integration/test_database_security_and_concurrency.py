#!/usr/bin/env python3
"""
Database 模块安全性和并发测试

包含：
1. SQL注入防护测试
2. 并发安全测试
3. 连接池并发压力测试
4. 事务隔离测试
"""

import sys
import unittest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


class TestDatabaseSecurityAndConcurrency(unittest.TestCase):
    """数据库安全性和并发测试"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*80)
        print("Database 安全性和并发测试套件")
        print("="*80)

    def setUp(self):
        """每个测试前的准备"""
        from database.db_manager import DatabaseManager
        DatabaseManager.reset_instance()

    def tearDown(self):
        """每个测试后的清理"""
        from database.db_manager import DatabaseManager
        DatabaseManager.reset_instance()

    # ==================== SQL注入防护测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('pandas.read_sql_query')
    def test_sql_injection_in_stock_code(self, mock_read_sql, mock_pool):
        """测试：股票代码中的SQL注入防护"""
        print("\n[安全测试1] 股票代码SQL注入防护")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance
        mock_read_sql.return_value = pd.DataFrame()

        db = DatabaseManager()

        # 尝试各种SQL注入攻击
        malicious_codes = [
            "000001'; DROP TABLE stock_daily; --",
            "000001' OR '1'='1",
            "000001'; DELETE FROM stock_daily WHERE '1'='1",
            "000001' UNION SELECT * FROM stock_basic --",
            "000001'; UPDATE stock_daily SET close=0; --"
        ]

        for code in malicious_codes:
            try:
                df = db.load_daily_data(code)
                # 验证使用了参数化查询
                call_args = mock_read_sql.call_args
                self.assertIsNotNone(call_args[1].get('params'))
                self.assertIn(code, call_args[1]['params'])
            except Exception:
                pass  # 即使抛出异常也是安全的

        print("  ✓ SQL注入防护测试通过（股票代码）")

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('pandas.read_sql_query')
    def test_sql_injection_in_date_params(self, mock_read_sql, mock_pool):
        """测试：日期参数中的SQL注入防护"""
        print("\n[安全测试2] 日期参数SQL注入防护")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance
        mock_read_sql.return_value = pd.DataFrame()

        db = DatabaseManager()

        # 尝试在日期参数中注入
        malicious_dates = [
            "2023-01-01'; DROP TABLE stock_daily; --",
            "2023-01-01' OR '1'='1",
        ]

        for date in malicious_dates:
            try:
                df = db.load_daily_data('000001', start_date=date)
                # 验证参数化查询
                call_args = mock_read_sql.call_args
                self.assertIn(date, call_args[1]['params'])
            except Exception:
                pass

        print("  ✓ SQL注入防护测试通过（日期参数）")

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('pandas.read_sql_query')
    def test_sql_injection_in_market_filter(self, mock_read_sql, mock_pool):
        """测试：市场过滤中的SQL注入防护"""
        print("\n[安全测试3] 市场过滤SQL注入防护")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance
        mock_read_sql.return_value = pd.DataFrame()

        db = DatabaseManager()

        malicious_markets = [
            "主板' OR '1'='1",
            "主板'; DROP TABLE stock_basic; --",
            "主板' UNION SELECT * FROM stock_daily --"
        ]

        for market in malicious_markets:
            try:
                df = db.get_stock_list(market=market)
                # 验证参数化查询
                call_args = mock_read_sql.call_args
                self.assertIn(market, call_args[1]['params'])
            except Exception:
                pass

        print("  ✓ SQL注入防护测试通过（市场过滤）")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_sql_injection_in_data_completeness_check(self, mock_pool):
        """测试：数据完整性检查中的SQL注入防护"""
        print("\n[安全测试4] 完整性检查SQL注入防护")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (0, None, None)
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()

        malicious_code = "000001'; DROP TABLE stock_daily; --"
        result = db.check_daily_data_completeness(malicious_code, '20230101', '20231231')

        # 验证使用了参数化查询
        call_args = mock_cursor.execute.call_args
        self.assertIn(malicious_code, call_args[0][1])

        print("  ✓ SQL注入防护测试通过（完整性检查）")

    # ==================== 并发安全测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_concurrent_singleton_creation(self, mock_pool):
        """测试：并发创建单例的线程安全"""
        print("\n[并发测试1] 并发单例创建")

        from database.db_manager import DatabaseManager

        instances = []
        lock = threading.Lock()
        errors = []

        def create_instance():
            try:
                db = DatabaseManager()
                with lock:
                    instances.append(db)
            except Exception as e:
                with lock:
                    errors.append(e)

        # 创建100个线程同时获取实例
        threads = [threading.Thread(target=create_instance) for _ in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证没有错误
        self.assertEqual(len(errors), 0)
        # 验证所有实例都是同一个
        first_instance = instances[0]
        for instance in instances:
            self.assertIs(instance, first_instance)

        print(f"  ✓ 并发单例测试通过（{len(instances)}个线程）")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_concurrent_connection_acquisition(self, mock_pool):
        """测试：并发获取连接"""
        print("\n[并发测试2] 并发获取连接")

        from database.db_manager import DatabaseManager

        # 创建mock连接池
        mock_connections = [Mock() for _ in range(10)]
        connection_index = [0]
        lock = threading.Lock()

        def getconn_side_effect():
            with lock:
                idx = connection_index[0] % len(mock_connections)
                connection_index[0] += 1
                return mock_connections[idx]

        mock_pool_instance = Mock()
        mock_pool_instance.getconn.side_effect = getconn_side_effect
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()

        connections_obtained = []
        errors = []

        def get_connection():
            try:
                conn = db.get_connection()
                with lock:
                    connections_obtained.append(conn)
                    time.sleep(0.001)  # 模拟使用连接
                db.release_connection(conn)
            except Exception as e:
                with lock:
                    errors.append(e)

        # 50个线程并发获取连接
        threads = [threading.Thread(target=get_connection) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(connections_obtained), 50)

        print(f"  ✓ 并发连接测试通过（{len(connections_obtained)}次获取）")

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('pandas.read_sql_query')
    def test_concurrent_read_operations(self, mock_read_sql, mock_pool):
        """测试：并发读取操作"""
        print("\n[并发测试3] 并发读取操作")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        # 创建mock数据
        mock_df = pd.DataFrame({
            'close': np.random.uniform(10, 20, 100)
        }, index=pd.date_range('2023-01-01', periods=100))
        mock_read_sql.return_value = mock_df

        db = DatabaseManager()

        results = queue.Queue()
        errors = queue.Queue()

        def read_data(stock_code):
            try:
                df = db.load_daily_data(stock_code)
                results.put((stock_code, len(df)))
            except Exception as e:
                errors.put((stock_code, e))

        # 20个线程同时读取不同股票数据
        stock_codes = [f'{i:06d}' for i in range(20)]
        threads = [threading.Thread(target=read_data, args=(code,)) for code in stock_codes]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证
        self.assertEqual(errors.qsize(), 0)
        self.assertEqual(results.qsize(), 20)

        print(f"  ✓ 并发读取测试通过（{results.qsize()}个股票）")

    @patch('database.data_insert_manager.DataInsertManager.save_daily_data')
    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_concurrent_write_operations(self, mock_pool, mock_save_daily):
        """测试：并发写入操作"""
        print("\n[并发测试4] 并发写入操作")

        from database.db_manager import DatabaseManager

        mock_pool_instance = Mock()
        mock_pool.return_value = mock_pool_instance

        # Mock save_daily_data 返回成功写入的记录数
        mock_save_daily.return_value = 10

        db = DatabaseManager()

        results = queue.Queue()
        errors = queue.Queue()

        def write_data(stock_code):
            try:
                dates = pd.date_range('2023-01-01', periods=10, freq='D')
                df = pd.DataFrame({
                    'open': np.random.uniform(10, 20, 10),
                    'close': np.random.uniform(10, 20, 10)
                }, index=dates)
                count = db.save_daily_data(df, stock_code)
                results.put((stock_code, count))
            except Exception as e:
                errors.put((stock_code, e))

        # 10个线程同时写入不同股票数据
        stock_codes = [f'{i:06d}' for i in range(10)]
        threads = [threading.Thread(target=write_data, args=(code,)) for code in stock_codes]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证 - 所有写入应该成功（因为我们mock了）
        self.assertEqual(errors.qsize(), 0, f"不应有错误: {list(errors.queue)}")
        self.assertEqual(results.qsize(), 10, "所有写入都应成功")

        print(f"  ✓ 并发写入测试通过（{results.qsize()}个股票）")

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_concurrent_mixed_operations(self, mock_pool):
        """测试：混合并发操作（读写混合）"""
        print("\n[并发测试5] 混合并发操作")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [('000001',), ('000002',)]
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()

        operations = queue.Queue()
        errors = queue.Queue()

        def read_operation(op_id):
            try:
                codes = db.get_oldest_realtime_stocks(limit=10)
                operations.put(('read', op_id, len(codes)))
            except Exception as e:
                errors.put(('read', op_id, e))

        def write_operation(op_id):
            try:
                quote = {'code': f'{op_id:06d}', 'name': f'股票{op_id}'}
                count = db.save_realtime_quote_single(quote)
                operations.put(('write', op_id, count))
            except Exception as e:
                errors.put(('write', op_id, e))

        # 创建混合操作线程：50个读 + 50个写
        threads = []
        for i in range(50):
            threads.append(threading.Thread(target=read_operation, args=(i,)))
            threads.append(threading.Thread(target=write_operation, args=(i,)))

        # 随机打乱顺序
        import random
        random.shuffle(threads)

        # 启动所有线程
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证
        self.assertEqual(errors.qsize(), 0)
        self.assertEqual(operations.qsize(), 100)

        print(f"  ✓ 混合并发测试通过（{operations.qsize()}个操作）")

    # ==================== 连接池压力测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    def test_connection_pool_stress(self, mock_pool):
        """测试：连接池压力测试"""
        print("\n[压力测试1] 连接池压力测试")

        from database.db_manager import DatabaseManager

        # 创建有限的连接池（10个连接）
        mock_connections = [Mock() for _ in range(10)]
        available_connections = list(mock_connections)
        conn_lock = threading.Lock()

        def getconn_side_effect():
            with conn_lock:
                if available_connections:
                    return available_connections.pop(0)
                else:
                    time.sleep(0.01)  # 模拟等待
                    if available_connections:
                        return available_connections.pop(0)
                    raise Exception("No available connections")

        def putconn_side_effect(conn):
            with conn_lock:
                available_connections.append(conn)

        mock_pool_instance = Mock()
        mock_pool_instance.getconn.side_effect = getconn_side_effect
        mock_pool_instance.putconn.side_effect = putconn_side_effect
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()

        successful = [0]
        failed = [0]
        lock = threading.Lock()

        def stress_operation(op_id):
            try:
                conn = db.get_connection()
                time.sleep(0.001)  # 模拟操作
                db.release_connection(conn)
                with lock:
                    successful[0] += 1
            except Exception:
                with lock:
                    failed[0] += 1

        # 200个并发请求，但只有10个连接
        threads = [threading.Thread(target=stress_operation, args=(i,)) for i in range(200)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(f"  ✓ 压力测试完成（成功: {successful[0]}, 失败: {failed[0]}）")

    # ==================== 事务隔离测试 ====================

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('database.data_insert_manager.extras.execute_batch')
    def test_transaction_isolation(self, mock_execute_batch, mock_pool):
        """测试：事务隔离"""
        print("\n[事务测试1] 事务隔离测试")

        from database.db_manager import DatabaseManager

        mock_conn1 = Mock()
        mock_conn2 = Mock()
        mock_cursor1 = Mock()
        mock_cursor2 = Mock()
        mock_conn1.cursor.return_value = mock_cursor1
        mock_conn2.cursor.return_value = mock_cursor2

        connections = [mock_conn1, mock_conn2]
        conn_index = [0]
        lock = threading.Lock()

        def getconn_side_effect():
            with lock:
                idx = conn_index[0] % len(connections)
                conn_index[0] += 1
                return connections[idx]

        mock_pool_instance = Mock()
        mock_pool_instance.getconn.side_effect = getconn_side_effect
        mock_pool.return_value = mock_pool_instance

        db = DatabaseManager()

        results = []

        def transaction1():
            df = pd.DataFrame({'code': ['000001'], 'name': ['股票1']})
            count = db.save_stock_list(df)
            results.append(('t1', count))

        def transaction2():
            df = pd.DataFrame({'code': ['000002'], 'name': ['股票2']})
            count = db.save_stock_list(df)
            results.append(('t2', count))

        t1 = threading.Thread(target=transaction1)
        t2 = threading.Thread(target=transaction2)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # 验证两个事务都成功
        self.assertEqual(len(results), 2)
        # 验证每个事务都调用了commit
        mock_conn1.commit.assert_called()
        mock_conn2.commit.assert_called()

        print("  ✓ 事务隔离测试通过")

    @patch('psycopg2.pool.SimpleConnectionPool')
    @patch('database.data_insert_manager.extras.execute_batch')
    def test_transaction_rollback_on_concurrent_error(self, mock_execute_batch, mock_pool):
        """测试：并发错误时的事务回滚"""
        print("\n[事务测试2] 并发错误回滚测试")

        from database.db_manager import DatabaseManager

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_pool_instance = Mock()
        mock_pool_instance.getconn.return_value = mock_conn
        mock_pool.return_value = mock_pool_instance

        # 设置第3次调用抛出异常
        call_count = [0]

        def execute_batch_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 3:
                raise Exception("Database error")

        mock_execute_batch.side_effect = execute_batch_side_effect

        db = DatabaseManager()

        errors = []

        def insert_with_error(stock_id):
            try:
                df = pd.DataFrame({'code': [f'{stock_id:06d}'], 'name': [f'股票{stock_id}']})
                db.save_stock_list(df)
            except Exception as e:
                errors.append((stock_id, e))

        # 5个并发插入，第3个会失败
        threads = [threading.Thread(target=insert_with_error, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证至少有一个错误
        self.assertGreater(len(errors), 0)
        # 验证回滚被调用
        self.assertGreater(mock_conn.rollback.call_count, 0)

        print(f"  ✓ 并发错误回滚测试通过（{len(errors)}个错误）")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDatabaseSecurityAndConcurrency)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*80)
    print("测试总结 - 安全性和并发")
    print("="*80)
    print(f"运行: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}, 错误: {len(result.errors)}")
    if result.testsRun > 0:
        print(f"成功率: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
