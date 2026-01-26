#!/usr/bin/env python3
"""
DataLoader 单元测试

测试数据加载器的功能
"""

import sys
import unittest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from data_pipeline.data_loader import DataLoader
from exceptions import DataNotFoundError, DataError


class TestDataLoader(unittest.TestCase):
    """测试 DataLoader 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataLoader 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        # 创建 Mock 数据库管理器
        self.mock_db = Mock()
        self.loader = DataLoader(db_manager=self.mock_db)

    def test_01_init(self):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        # 使用 Mock 数据库
        loader = DataLoader(db_manager=self.mock_db)
        self.assertIsNotNone(loader.db)
        self.assertEqual(loader.db, self.mock_db)

        print("  ✓ 初始化成功")

    def test_02_load_data_success(self):
        """测试2: 成功加载数据"""
        print("\n[测试2] 成功加载数据...")

        # 创建模拟数据
        mock_data = pd.DataFrame({
            'open': [10.0, 11.0, 12.0],
            'high': [10.5, 11.5, 12.5],
            'low': [9.5, 10.5, 11.5],
            'close': [10.2, 11.2, 12.2],
            'volume': [1000, 1100, 1200]
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))

        # 配置 Mock 返回值
        self.mock_db.load_daily_data.return_value = mock_data

        # 加载数据
        result = self.loader.load_data('000001', '20230101', '20230103')

        # 验证
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertIsInstance(result.index, pd.DatetimeIndex)
        self.assertIn('close', result.columns)

        # 验证数据库调用
        self.mock_db.load_daily_data.assert_called_once_with('000001', '20230101', '20230103')

        print(f"  ✓ 数据加载成功: {len(result)} 条记录")

    def test_03_load_data_empty(self):
        """测试3: 数据为空"""
        print("\n[测试3] 数据为空...")

        # 配置返回空数据
        self.mock_db.load_daily_data.return_value = pd.DataFrame()

        # 应该抛出 DataNotFoundError
        with self.assertRaises(DataNotFoundError) as context:
            self.loader.load_data('INVALID', '20230101', '20230103')

        error = context.exception
        self.assertIn('symbol', error.details)
        self.assertEqual(error.details['symbol'], 'INVALID')

        print("  ✓ 空数据异常处理正确")

    def test_04_load_data_none(self):
        """测试4: 数据为 None"""
        print("\n[测试4] 数据为 None...")

        # 配置返回 None
        self.mock_db.load_daily_data.return_value = None

        # 应该抛出 DataNotFoundError
        with self.assertRaises(DataNotFoundError):
            self.loader.load_data('000001', '20230101', '20230103')

        print("  ✓ None 数据异常处理正确")

    def test_05_missing_columns(self):
        """测试5: 缺少必要列"""
        print("\n[测试5] 缺少必要列...")

        # 创建缺少列的数据
        mock_data = pd.DataFrame({
            'close': [10.0, 11.0, 12.0],
            'volume': [1000, 1100, 1200]
            # 缺少 open, high, low
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))

        self.mock_db.load_daily_data.return_value = mock_data

        # 应该抛出 DataError
        with self.assertRaises(DataError) as context:
            self.loader.load_data('000001', '20230101', '20230103')

        error = context.exception
        self.assertIn('missing_columns', error.details)

        print("  ✓ 缺少列异常处理正确")

    def test_06_datetime_index_conversion(self):
        """测试6: 日期索引转换"""
        print("\n[测试6] 日期索引转换...")

        # 创建带 date 列的数据（非索引）
        mock_data = pd.DataFrame({
            'date': ['2023-01-01', '2023-01-02', '2023-01-03'],
            'open': [10.0, 11.0, 12.0],
            'high': [10.5, 11.5, 12.5],
            'low': [9.5, 10.5, 11.5],
            'close': [10.2, 11.2, 12.2],
            'volume': [1000, 1100, 1200]
        })

        self.mock_db.load_daily_data.return_value = mock_data

        # 加载数据
        result = self.loader.load_data('000001', '20230101', '20230103')

        # 验证索引转换
        self.assertIsInstance(result.index, pd.DatetimeIndex)
        self.assertNotIn('date', result.columns)

        print("  ✓ 日期索引转换成功")

    def test_07_data_sorting(self):
        """测试7: 数据排序"""
        print("\n[测试7] 数据排序...")

        # 创建无序数据
        mock_data = pd.DataFrame({
            'open': [12.0, 10.0, 11.0],
            'high': [12.5, 10.5, 11.5],
            'low': [11.5, 9.5, 10.5],
            'close': [12.2, 10.2, 11.2],
            'volume': [1200, 1000, 1100]
        }, index=pd.to_datetime(['2023-01-03', '2023-01-01', '2023-01-02']))

        self.mock_db.load_daily_data.return_value = mock_data

        # 加载数据
        result = self.loader.load_data('000001', '20230101', '20230103')

        # 验证排序
        self.assertTrue(result.index.is_monotonic_increasing)
        self.assertEqual(result.iloc[0]['close'], 10.2)  # 第一天
        self.assertEqual(result.iloc[-1]['close'], 12.2)  # 最后一天

        print("  ✓ 数据排序成功")

    def test_08_database_exception(self):
        """测试8: 数据库异常"""
        print("\n[测试8] 数据库异常...")

        # 配置数据库抛出异常
        self.mock_db.load_daily_data.side_effect = Exception("Database connection error")

        # 应该抛出 DataError
        with self.assertRaises(DataError) as context:
            self.loader.load_data('000001', '20230101', '20230103')

        error = context.exception
        self.assertIn('symbol', error.details)

        print("  ✓ 数据库异常处理正确")

    def test_09_no_date_index(self):
        """测试9: 无日期索引或列"""
        print("\n[测试9] 无日期索引或列...")

        # 创建无日期信息的数据
        mock_data = pd.DataFrame({
            'open': [10.0, 11.0, 12.0],
            'high': [10.5, 11.5, 12.5],
            'low': [9.5, 10.5, 11.5],
            'close': [10.2, 11.2, 12.2],
            'volume': [1000, 1100, 1200]
        })

        self.mock_db.load_daily_data.return_value = mock_data

        # 应该抛出 DataError
        with self.assertRaises(DataError) as context:
            self.loader.load_data('000001', '20230101', '20230103')

        print("  ✓ 无日期异常处理正确")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDataLoader)
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
