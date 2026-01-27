#!/usr/bin/env python3
"""
PooledDataLoader 单元测试

测试池化数据加载器的各项功能
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from src.data_pipeline.pooled_data_loader import PooledDataLoader


class TestPooledDataLoader(unittest.TestCase):
    """测试 PooledDataLoader 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("PooledDataLoader 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        # 创建 Mock 数据库管理器
        self.mock_db = Mock()
        self.loader = PooledDataLoader(db_manager=self.mock_db, verbose=False)

    def _create_mock_daily_data(self, symbol: str, rows: int = 150) -> pd.DataFrame:
        """创建模拟的日线数据"""
        dates = pd.date_range('2023-01-01', periods=rows, freq='D')
        return pd.DataFrame({
            'open': np.random.uniform(10, 20, rows),
            'high': np.random.uniform(15, 25, rows),
            'low': np.random.uniform(5, 15, rows),
            'close': np.random.uniform(10, 20, rows),
            'volume': np.random.uniform(1e6, 1e7, rows),
            'amount': np.random.uniform(1e7, 1e8, rows)
        }, index=dates)

    def _create_mock_feature_data(self, rows: int = 150) -> pd.DataFrame:
        """创建模拟的特征数据"""
        dates = pd.date_range('2023-01-01', periods=rows, freq='D')
        return pd.DataFrame({
            'close': np.random.uniform(10, 20, rows),
            'volume': np.random.uniform(1e6, 1e7, rows),
            'MOM5': np.random.uniform(-5, 5, rows),
            'MOM10': np.random.uniform(-10, 10, rows),
            'VOLATILITY20': np.random.uniform(0, 50, rows),
            'RSI14': np.random.uniform(0, 100, rows),
            'target_return_10d': np.random.uniform(-10, 10, rows)
        }, index=dates)

    def test_01_initialization(self):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        # 使用默认参数
        loader1 = PooledDataLoader(db_manager=self.mock_db)
        self.assertIsNotNone(loader1.db)
        self.assertTrue(loader1.verbose)

        # 使用自定义参数
        loader2 = PooledDataLoader(db_manager=self.mock_db, verbose=False)
        self.assertFalse(loader2.verbose)

        print("  ✓ 初始化成功")

    @patch('src.data_pipeline.pooled_data_loader.FeatureEngineer')
    def test_02_load_pooled_data_single_stock(self, mock_fe_class):
        """测试2: 加载单只股票数据"""
        print("\n[测试2] 加载单只股票数据...")

        # 配置 Mock
        symbol = '000001'
        mock_raw_data = self._create_mock_daily_data(symbol, rows=150)
        self.mock_db.load_daily_data.return_value = mock_raw_data

        mock_feature_data = self._create_mock_feature_data(rows=150)
        mock_fe_instance = Mock()
        mock_fe_instance.compute_all_features.return_value = mock_feature_data
        mock_fe_class.return_value = mock_fe_instance

        # 执行加载
        pooled_df, total_samples, successful_symbols = self.loader.load_pooled_data(
            symbol_list=[symbol],
            start_date='20230101',
            end_date='20231231',
            target_period=10
        )

        # 验证结果
        self.assertIsInstance(pooled_df, pd.DataFrame)
        self.assertGreater(len(pooled_df), 0)
        self.assertEqual(total_samples, len(pooled_df))
        self.assertEqual(successful_symbols, [symbol])
        self.assertIn('stock_code', pooled_df.columns)
        self.assertEqual(pooled_df['stock_code'].iloc[0], symbol)

        # 验证调用
        self.mock_db.load_daily_data.assert_called_once_with(symbol, '20230101', '20231231')
        mock_fe_instance.compute_all_features.assert_called_once()

        print(f"  ✓ 成功加载 {len(pooled_df)} 条数据")

    @patch('src.data_pipeline.pooled_data_loader.FeatureEngineer')
    def test_03_load_pooled_data_multiple_stocks(self, mock_fe_class):
        """测试3: 加载多只股票数据"""
        print("\n[测试3] 加载多只股票数据...")

        symbols = ['000001', '000002', '600000']

        # 配置 Mock - 为每只股票返回不同的数据
        def mock_load_daily_data(symbol, start_date, end_date):
            return self._create_mock_daily_data(symbol, rows=150)

        self.mock_db.load_daily_data.side_effect = mock_load_daily_data

        # 每次调用都返回新的数据副本
        mock_fe_instance = Mock()
        mock_fe_instance.compute_all_features.side_effect = lambda *args, **kwargs: self._create_mock_feature_data(rows=150)
        mock_fe_class.return_value = mock_fe_instance

        # 执行加载
        pooled_df, total_samples, successful_symbols = self.loader.load_pooled_data(
            symbol_list=symbols,
            start_date='20230101',
            end_date='20231231',
            target_period=10
        )

        # 验证结果
        self.assertEqual(len(successful_symbols), 3)
        self.assertEqual(set(successful_symbols), set(symbols))
        self.assertGreater(total_samples, 0)
        self.assertEqual(total_samples, len(pooled_df))

        # 验证每只股票都有数据（stock_code 列已添加）
        unique_symbols = pooled_df['stock_code'].unique()
        self.assertEqual(len(unique_symbols), len(symbols))
        for symbol in symbols:
            self.assertIn(symbol, unique_symbols.tolist())

        print(f"  ✓ 成功加载 {len(symbols)} 只股票，共 {total_samples} 条数据")

    @patch('src.data_pipeline.pooled_data_loader.FeatureEngineer')
    def test_04_load_pooled_data_insufficient_data(self, mock_fe_class):
        """测试4: 数据不足的股票应被跳过"""
        print("\n[测试4] 数据不足的股票处理...")

        symbols = ['000001', '000002', '600000']

        # 配置 Mock - 第二只股票数据不足
        def mock_load_daily_data(symbol, start_date, end_date):
            if symbol == '000002':
                return self._create_mock_daily_data(symbol, rows=50)  # 数据不足
            return self._create_mock_daily_data(symbol, rows=150)

        self.mock_db.load_daily_data.side_effect = mock_load_daily_data

        mock_fe_instance = Mock()
        mock_fe_instance.compute_all_features.side_effect = lambda *args, **kwargs: self._create_mock_feature_data(rows=150)
        mock_fe_class.return_value = mock_fe_instance

        # 执行加载
        pooled_df, total_samples, successful_symbols = self.loader.load_pooled_data(
            symbol_list=symbols,
            start_date='20230101',
            end_date='20231231',
            target_period=10
        )

        # 验证结果 - 应该只有2只股票成功
        self.assertEqual(len(successful_symbols), 2)
        self.assertIn('000001', successful_symbols)
        self.assertNotIn('000002', successful_symbols)
        self.assertIn('600000', successful_symbols)

        print(f"  ✓ 正确跳过数据不足的股票")

    @patch('src.data_pipeline.pooled_data_loader.FeatureEngineer')
    def test_05_load_pooled_data_with_errors(self, mock_fe_class):
        """测试5: 加载过程中的错误处理"""
        print("\n[测试5] 错误处理...")

        symbols = ['000001', '000002', '600000']

        # 配置 Mock - 第二只股票加载失败
        def mock_load_daily_data(symbol, start_date, end_date):
            if symbol == '000002':
                raise Exception("数据库连接失败")
            return self._create_mock_daily_data(symbol, rows=150)

        self.mock_db.load_daily_data.side_effect = mock_load_daily_data

        mock_fe_instance = Mock()
        mock_fe_instance.compute_all_features.side_effect = lambda *args, **kwargs: self._create_mock_feature_data(rows=150)
        mock_fe_class.return_value = mock_fe_instance

        # 执行加载
        pooled_df, total_samples, successful_symbols = self.loader.load_pooled_data(
            symbol_list=symbols,
            start_date='20230101',
            end_date='20231231',
            target_period=10
        )

        # 验证结果 - 应该有2只股票成功，1只失败
        self.assertEqual(len(successful_symbols), 2)
        self.assertIn('000001', successful_symbols)
        self.assertNotIn('000002', successful_symbols)
        self.assertIn('600000', successful_symbols)

        print(f"  ✓ 正确处理加载错误")

    def test_06_load_pooled_data_no_success(self):
        """测试6: 所有股票都加载失败"""
        print("\n[测试6] 所有股票加载失败...")

        symbols = ['000001', '000002']

        # 配置 Mock - 所有股票都返回数据不足
        self.mock_db.load_daily_data.return_value = self._create_mock_daily_data('000001', rows=50)

        # 应该抛出 ValueError
        with self.assertRaises(ValueError) as context:
            self.loader.load_pooled_data(
                symbol_list=symbols,
                start_date='20230101',
                end_date='20231231',
                target_period=10
            )

        self.assertIn("没有成功加载任何股票数据", str(context.exception))

        print(f"  ✓ 正确抛出异常")

    def test_07_prepare_pooled_training_data(self):
        """测试7: 准备训练数据"""
        print("\n[测试7] 准备训练数据...")

        # 创建模拟的池化数据
        n_samples = 1000
        pooled_df = pd.DataFrame({
            'close': np.random.uniform(10, 20, n_samples),
            'volume': np.random.uniform(1e6, 1e7, n_samples),
            'MOM5': np.random.uniform(-5, 5, n_samples),
            'MOM10': np.random.uniform(-10, 10, n_samples),
            'VOLATILITY20': np.random.uniform(0, 50, n_samples),
            'target_return_10d': np.random.uniform(-10, 10, n_samples),
            'stock_code': ['000001'] * (n_samples // 2) + ['000002'] * (n_samples // 2)
        })

        # 执行数据分割
        X_train, y_train, X_valid, y_valid, X_test, y_test, feature_cols = \
            self.loader.prepare_pooled_training_data(
                pooled_df=pooled_df,
                target_col='target_return_10d',
                train_ratio=0.7,
                valid_ratio=0.15
            )

        # 验证数据分割
        total_samples = len(X_train) + len(X_valid) + len(X_test)
        self.assertGreater(total_samples, 0)

        # 验证比例（允许一定误差）
        train_pct = len(X_train) / total_samples
        valid_pct = len(X_valid) / total_samples
        test_pct = len(X_test) / total_samples

        self.assertAlmostEqual(train_pct, 0.7, delta=0.02)
        self.assertAlmostEqual(valid_pct, 0.15, delta=0.02)
        self.assertAlmostEqual(test_pct, 0.15, delta=0.02)

        # 验证特征列
        self.assertGreater(len(feature_cols), 0)
        self.assertNotIn('target_return_10d', feature_cols)
        self.assertNotIn('stock_code', feature_cols)

        # 验证数据形状
        self.assertEqual(X_train.shape[1], len(feature_cols))
        self.assertEqual(X_valid.shape[1], len(feature_cols))
        self.assertEqual(X_test.shape[1], len(feature_cols))

        print(f"  ✓ 训练集: {len(X_train)} ({train_pct*100:.1f}%)")
        print(f"  ✓ 验证集: {len(X_valid)} ({valid_pct*100:.1f}%)")
        print(f"  ✓ 测试集: {len(X_test)} ({test_pct*100:.1f}%)")

    def test_08_prepare_pooled_training_data_with_nan(self):
        """测试8: 准备训练数据 - 包含缺失值"""
        print("\n[测试8] 包含缺失值的数据处理...")

        # 创建包含缺失值的数据
        n_samples = 1000
        pooled_df = pd.DataFrame({
            'close': np.random.uniform(10, 20, n_samples),
            'volume': np.random.uniform(1e6, 1e7, n_samples),
            'MOM5': np.random.uniform(-5, 5, n_samples),
            'target_return_10d': np.random.uniform(-10, 10, n_samples),
            'stock_code': ['000001'] * n_samples
        })

        # 添加缺失值
        pooled_df.loc[:100, 'MOM5'] = np.nan

        # 执行数据分割
        X_train, y_train, X_valid, y_valid, X_test, y_test, feature_cols = \
            self.loader.prepare_pooled_training_data(
                pooled_df=pooled_df,
                target_col='target_return_10d',
                train_ratio=0.7,
                valid_ratio=0.15
            )

        # 验证缺失值已被删除
        total_samples = len(X_train) + len(X_valid) + len(X_test)
        self.assertLess(total_samples, n_samples)
        self.assertEqual(X_train.isna().sum().sum(), 0)
        self.assertEqual(X_valid.isna().sum().sum(), 0)
        self.assertEqual(X_test.isna().sum().sum(), 0)

        print(f"  ✓ 原始样本: {n_samples}, 清洗后: {total_samples}")

    def test_09_prepare_pooled_training_data_custom_ratios(self):
        """测试9: 自定义分割比例"""
        print("\n[测试9] 自定义分割比例...")

        # 创建模拟数据
        n_samples = 1000
        pooled_df = pd.DataFrame({
            'close': np.random.uniform(10, 20, n_samples),
            'volume': np.random.uniform(1e6, 1e7, n_samples),
            'MOM5': np.random.uniform(-5, 5, n_samples),
            'target_return_10d': np.random.uniform(-10, 10, n_samples),
            'stock_code': ['000001'] * n_samples
        })

        # 使用自定义比例 (80% / 10% / 10%)
        X_train, y_train, X_valid, y_valid, X_test, y_test, feature_cols = \
            self.loader.prepare_pooled_training_data(
                pooled_df=pooled_df,
                target_col='target_return_10d',
                train_ratio=0.8,
                valid_ratio=0.1
            )

        # 验证比例
        total_samples = len(X_train) + len(X_valid) + len(X_test)
        train_pct = len(X_train) / total_samples
        valid_pct = len(X_valid) / total_samples
        test_pct = len(X_test) / total_samples

        self.assertAlmostEqual(train_pct, 0.8, delta=0.02)
        self.assertAlmostEqual(valid_pct, 0.1, delta=0.02)
        self.assertAlmostEqual(test_pct, 0.1, delta=0.02)

        print(f"  ✓ 自定义比例正确: {train_pct:.1%} / {valid_pct:.1%} / {test_pct:.1%}")

    def test_10_verbose_mode(self):
        """测试10: Verbose模式输出"""
        print("\n[测试10] Verbose模式...")

        # 创建 verbose=True 的加载器
        verbose_loader = PooledDataLoader(db_manager=self.mock_db, verbose=True)

        # 测试应该能正常工作（不抛出异常）
        self.assertTrue(verbose_loader.verbose)

        print(f"  ✓ Verbose模式正常")

    @patch('src.data_pipeline.pooled_data_loader.FeatureEngineer')
    def test_11_verbose_logging_coverage(self, mock_fe_class):
        """测试11: 覆盖verbose日志路径"""
        print("\n[测试11] Verbose日志覆盖...")

        # 创建 verbose=True 的加载器
        verbose_loader = PooledDataLoader(db_manager=self.mock_db, verbose=True)

        symbols = ['000001', '000002', '600000', '600001', '600002', '600003']

        # 配置 Mock - 部分股票失败，以触发失败日志
        def mock_load_daily_data(symbol, start_date, end_date):
            if symbol in ['000002', '600001']:
                raise Exception("连接失败")
            return self._create_mock_daily_data(symbol, rows=150)

        self.mock_db.load_daily_data.side_effect = mock_load_daily_data

        mock_fe_instance = Mock()
        mock_fe_instance.compute_all_features.side_effect = lambda *args, **kwargs: self._create_mock_feature_data(rows=150)
        mock_fe_class.return_value = mock_fe_instance

        # 执行加载 - 应该触发verbose日志输出
        pooled_df, total_samples, successful_symbols = verbose_loader.load_pooled_data(
            symbol_list=symbols,
            start_date='20230101',
            end_date='20231231',
            target_period=10
        )

        # 验证结果
        self.assertEqual(len(successful_symbols), 4)
        self.assertGreater(total_samples, 0)

        print(f"  ✓ Verbose日志覆盖完成")

    def test_12_prepare_data_with_all_zero_samples(self):
        """测试12: 边界情况 - 处理空值导致样本数为0"""
        print("\n[测试12] 所有样本都有缺失值...")

        # 创建全是NaN的数据
        n_samples = 100
        pooled_df = pd.DataFrame({
            'close': [np.nan] * n_samples,
            'volume': [np.nan] * n_samples,
            'MOM5': [np.nan] * n_samples,
            'target_return_10d': [np.nan] * n_samples,
            'stock_code': ['000001'] * n_samples
        })

        # 执行数据分割 - 应该返回空的数据集
        X_train, y_train, X_valid, y_valid, X_test, y_test, feature_cols = \
            self.loader.prepare_pooled_training_data(
                pooled_df=pooled_df,
                target_col='target_return_10d',
                train_ratio=0.7,
                valid_ratio=0.15
            )

        # 验证所有集合都是空的
        self.assertEqual(len(X_train), 0)
        self.assertEqual(len(y_train), 0)
        self.assertEqual(len(X_valid), 0)
        self.assertEqual(len(y_valid), 0)
        self.assertEqual(len(X_test), 0)
        self.assertEqual(len(y_test), 0)

        print(f"  ✓ 正确处理全空数据集")

    def test_13_prepare_data_verbose_with_zero_samples(self):
        """测试13: verbose模式下处理零样本的日志路径"""
        print("\n[测试13] Verbose模式下的零样本日志...")

        verbose_loader = PooledDataLoader(db_manager=self.mock_db, verbose=True)

        # 创建空数据
        pooled_df = pd.DataFrame({
            'close': [np.nan] * 10,
            'volume': [np.nan] * 10,
            'target_return_10d': [np.nan] * 10,
            'stock_code': ['000001'] * 10
        })

        # 执行数据分割 - 应该触发n==0的日志路径
        X_train, y_train, X_valid, y_valid, X_test, y_test, feature_cols = \
            verbose_loader.prepare_pooled_training_data(
                pooled_df=pooled_df,
                target_col='target_return_10d',
                train_ratio=0.7,
                valid_ratio=0.15
            )

        # 验证结果
        self.assertEqual(len(X_train), 0)

        print(f"  ✓ Verbose零样本日志覆盖完成")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPooledDataLoader)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
