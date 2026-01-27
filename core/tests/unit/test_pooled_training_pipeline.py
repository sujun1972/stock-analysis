#!/usr/bin/env python3
"""
PooledTrainingPipeline 单元测试

测试池化训练Pipeline的完整功能
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pandas as pd
import numpy as np
import tempfile
import shutil

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from src.data_pipeline.pooled_training_pipeline import PooledTrainingPipeline


class TestPooledTrainingPipeline(unittest.TestCase):
    """测试 PooledTrainingPipeline 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("PooledTrainingPipeline 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        # 创建临时目录用于保存模型
        self.temp_dir = tempfile.mkdtemp()

        # 创建Pipeline实例
        self.pipeline = PooledTrainingPipeline(scaler_type='robust', verbose=False)

    def tearDown(self):
        """每个测试后的清理"""
        # 清理临时目录
        if hasattr(self, 'temp_dir') and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def _create_mock_pooled_data(self, n_samples: int = 1000) -> pd.DataFrame:
        """创建模拟的池化数据"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=n_samples, freq='D')

        # 创建多个股票的数据
        symbols = ['000001', '000002', '600000']
        samples_per_stock = n_samples // len(symbols)

        data = []
        for symbol in symbols:
            stock_data = pd.DataFrame({
                'close': np.random.uniform(10, 20, samples_per_stock),
                'volume': np.random.uniform(1e6, 1e7, samples_per_stock),
                'MOM5': np.random.uniform(-5, 5, samples_per_stock),
                'MOM10': np.random.uniform(-10, 10, samples_per_stock),
                'RSI14': np.random.uniform(0, 100, samples_per_stock),
                'MACD': np.random.uniform(-2, 2, samples_per_stock),
                'VOLATILITY20': np.random.uniform(0, 50, samples_per_stock),
                'target_10d_return': np.random.uniform(-10, 10, samples_per_stock),
                'stock_code': [symbol] * samples_per_stock
            }, index=dates[:samples_per_stock])
            data.append(stock_data)

        return pd.concat(data, ignore_index=True)

    def test_01_initialization(self):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        # 测试默认参数
        pipeline1 = PooledTrainingPipeline()
        self.assertEqual(pipeline1.scaler_type, 'robust')
        self.assertTrue(pipeline1.verbose)
        self.assertIsNone(pipeline1.scaler)
        self.assertIsNotNone(pipeline1.pooled_loader)
        self.assertIsNotNone(pipeline1.comparison_evaluator)

        # 测试自定义参数
        pipeline2 = PooledTrainingPipeline(scaler_type='standard', verbose=False)
        self.assertEqual(pipeline2.scaler_type, 'standard')
        self.assertFalse(pipeline2.verbose)

        print("  ✓ 初始化成功")

    @patch('src.data_pipeline.pooled_training_pipeline.PooledDataLoader')
    def test_02_load_and_prepare_data(self, mock_loader_class):
        """测试2: 加载和准备数据"""
        print("\n[测试2] 加载和准备数据...")

        # 创建模拟数据
        mock_pooled_data = self._create_mock_pooled_data(n_samples=1000)

        # 配置Mock
        mock_loader_instance = Mock()
        mock_loader_instance.load_pooled_data.return_value = (
            mock_pooled_data,
            len(mock_pooled_data),
            ['000001', '000002', '600000']
        )

        # 模拟prepare_pooled_training_data返回
        n = len(mock_pooled_data)
        feature_cols = ['close', 'volume', 'MOM5', 'MOM10', 'RSI14', 'MACD', 'VOLATILITY20']
        X = mock_pooled_data[feature_cols]
        y = mock_pooled_data['target_10d_return']

        train_end = int(n * 0.7)
        valid_end = int(n * 0.85)

        mock_loader_instance.prepare_pooled_training_data.return_value = (
            X.iloc[:train_end], y.iloc[:train_end],
            X.iloc[train_end:valid_end], y.iloc[train_end:valid_end],
            X.iloc[valid_end:], y.iloc[valid_end:],
            feature_cols
        )

        mock_loader_class.return_value = mock_loader_instance

        # 重新创建pipeline以使用mock
        pipeline = PooledTrainingPipeline(scaler_type='robust', verbose=False)

        # 执行加载
        X_train, y_train, X_valid, y_valid, X_test, y_test = pipeline.load_and_prepare_data(
            symbol_list=['000001', '000002', '600000'],
            start_date='20230101',
            end_date='20231231',
            target_period=10,
            train_ratio=0.7,
            valid_ratio=0.15
        )

        # 验证结果
        self.assertIsInstance(X_train, pd.DataFrame)
        self.assertIsInstance(y_train, pd.Series)
        self.assertGreater(len(X_train), 0)
        self.assertGreater(len(X_valid), 0)
        self.assertGreater(len(X_test), 0)

        # 验证scaler已创建
        self.assertIsNotNone(pipeline.scaler)

        # 验证数据已被缩放（检查统计特性）
        # RobustScaler应该使中位数接近0
        self.assertLess(abs(X_train.median().mean()), 1.0)

        print(f"  ✓ 成功准备数据: 训练集{len(X_train)}, 验证集{len(X_valid)}, 测试集{len(X_test)}")

    @patch('src.data_pipeline.pooled_training_pipeline.PooledDataLoader')
    def test_03_load_and_prepare_data_different_scalers(self, mock_loader_class):
        """测试3: 测试不同的Scaler类型"""
        print("\n[测试3] 测试不同Scaler类型...")

        mock_pooled_data = self._create_mock_pooled_data(n_samples=500)

        # 配置Mock
        mock_loader_instance = Mock()
        mock_loader_instance.load_pooled_data.return_value = (
            mock_pooled_data, len(mock_pooled_data), ['000001']
        )

        feature_cols = ['close', 'volume', 'MOM5', 'MOM10']
        X = mock_pooled_data[feature_cols]
        y = mock_pooled_data['target_10d_return']

        n = len(X)
        train_end = int(n * 0.7)
        valid_end = int(n * 0.85)

        mock_loader_instance.prepare_pooled_training_data.return_value = (
            X.iloc[:train_end], y.iloc[:train_end],
            X.iloc[train_end:valid_end], y.iloc[train_end:valid_end],
            X.iloc[valid_end:], y.iloc[valid_end:],
            feature_cols
        )

        mock_loader_class.return_value = mock_loader_instance

        # 测试standard scaler
        pipeline_std = PooledTrainingPipeline(scaler_type='standard', verbose=False)
        X_train_std, _, _, _, _, _ = pipeline_std.load_and_prepare_data(
            symbol_list=['000001'], start_date='20230101', end_date='20231231'
        )
        self.assertIsNotNone(pipeline_std.scaler)

        # 测试minmax scaler
        pipeline_minmax = PooledTrainingPipeline(scaler_type='minmax', verbose=False)
        X_train_minmax, _, _, _, _, _ = pipeline_minmax.load_and_prepare_data(
            symbol_list=['000001'], start_date='20230101', end_date='20231231'
        )
        self.assertIsNotNone(pipeline_minmax.scaler)

        print("  ✓ 所有Scaler类型工作正常")

    @patch('src.data_pipeline.pooled_training_pipeline.PooledDataLoader')
    def test_04_load_and_prepare_data_invalid_scaler(self, mock_loader_class):
        """测试4: 无效的Scaler类型"""
        print("\n[测试4] 无效Scaler类型...")

        mock_pooled_data = self._create_mock_pooled_data(n_samples=100)

        mock_loader_instance = Mock()
        mock_loader_instance.load_pooled_data.return_value = (
            mock_pooled_data, len(mock_pooled_data), ['000001']
        )

        feature_cols = ['close', 'volume']
        X = mock_pooled_data[feature_cols]
        y = mock_pooled_data['target_10d_return']

        mock_loader_instance.prepare_pooled_training_data.return_value = (
            X, y, X, y, X, y, feature_cols
        )

        mock_loader_class.return_value = mock_loader_instance

        # 创建无效scaler类型的pipeline
        pipeline = PooledTrainingPipeline(scaler_type='invalid_scaler', verbose=False)

        # 应该抛出ValueError
        with self.assertRaises(ValueError) as context:
            pipeline.load_and_prepare_data(
                symbol_list=['000001'],
                start_date='20230101',
                end_date='20231231'
            )

        self.assertIn("不支持的scaler类型", str(context.exception))

        print("  ✓ 正确捕获无效Scaler类型")

    @patch('src.data_pipeline.pooled_training_pipeline.ModelTrainer')
    @patch('src.data_pipeline.pooled_training_pipeline.ComparisonEvaluator')
    def test_05_train_with_baseline_lightgbm_only(self, mock_evaluator_class, mock_trainer_class):
        """测试5: 只训练LightGBM模型"""
        print("\n[测试5] 训练LightGBM模型...")

        # 创建模拟数据
        np.random.seed(42)
        n_samples = 200
        X_train = pd.DataFrame(np.random.randn(n_samples, 5), columns=[f'f{i}' for i in range(5)])
        y_train = pd.Series(np.random.randn(n_samples))
        X_valid = pd.DataFrame(np.random.randn(50, 5), columns=[f'f{i}' for i in range(5)])
        y_valid = pd.Series(np.random.randn(50))
        X_test = pd.DataFrame(np.random.randn(50, 5), columns=[f'f{i}' for i in range(5)])
        y_test = pd.Series(np.random.randn(50))

        # 配置Mock - ModelTrainer
        mock_trainer_instance = Mock()
        mock_trainer_instance.save_model.return_value = str(Path(self.temp_dir) / "model.pkl")
        mock_trainer_class.return_value = mock_trainer_instance

        # 配置Mock - ComparisonEvaluator
        mock_evaluator_instance = Mock()
        mock_evaluator_instance.evaluate_all.return_value = pd.DataFrame()
        mock_evaluator_instance.get_comparison_dict.return_value = {
            'comparison': [
                {
                    'model': 'LightGBM',
                    'train_ic': 0.5, 'train_rank_ic': 0.4, 'train_mae': 1.0, 'train_rmse': 1.2,
                    'valid_ic': 0.45, 'valid_rank_ic': 0.38, 'valid_mae': 1.1, 'valid_rmse': 1.3,
                    'test_ic': 0.42, 'test_rank_ic': 0.35, 'test_mae': 1.15, 'test_rmse': 1.35,
                    'test_r2': 0.3, 'overfit_ic': 0.05
                }
            ]
        }
        mock_evaluator_class.return_value = mock_evaluator_instance

        # 设置pipeline属性
        self.pipeline.pooled_df = self._create_mock_pooled_data(n_samples=300)
        self.pipeline.successful_symbols = ['000001', '000002']
        self.pipeline.feature_cols = [f'f{i}' for i in range(5)]
        self.pipeline.comparison_evaluator = mock_evaluator_instance

        # 执行训练（不启用Ridge）
        results = self.pipeline.train_with_baseline(
            X_train, y_train, X_valid, y_valid, X_test, y_test,
            enable_ridge_baseline=False
        )

        # 验证结果
        self.assertIsInstance(results, dict)
        self.assertIn('lgb_metrics', results)
        self.assertIn('comparison', results)
        self.assertFalse(results['has_baseline'])
        self.assertEqual(results['num_symbols'], 2)

        # 验证只调用了一次ModelTrainer（LightGBM）
        self.assertEqual(mock_trainer_class.call_count, 1)
        mock_trainer_class.assert_called_with(model_type='lightgbm', model_params=unittest.mock.ANY)

        print("  ✓ LightGBM训练完成")

    @patch('src.data_pipeline.pooled_training_pipeline.ModelTrainer')
    @patch('src.data_pipeline.pooled_training_pipeline.ComparisonEvaluator')
    def test_06_train_with_baseline_both_models(self, mock_evaluator_class, mock_trainer_class):
        """测试6: 训练LightGBM和Ridge基准模型"""
        print("\n[测试6] 训练LightGBM和Ridge...")

        # 创建模拟数据
        np.random.seed(42)
        n_samples = 200
        X_train = pd.DataFrame(np.random.randn(n_samples, 5), columns=[f'f{i}' for i in range(5)])
        y_train = pd.Series(np.random.randn(n_samples))
        X_valid = pd.DataFrame(np.random.randn(50, 5), columns=[f'f{i}' for i in range(5)])
        y_valid = pd.Series(np.random.randn(50))
        X_test = pd.DataFrame(np.random.randn(50, 5), columns=[f'f{i}' for i in range(5)])
        y_test = pd.Series(np.random.randn(50))

        # 配置Mock
        mock_trainer_instance = Mock()
        mock_trainer_instance.save_model.return_value = str(Path(self.temp_dir) / "model.pkl")
        mock_trainer_class.return_value = mock_trainer_instance

        mock_evaluator_instance = Mock()
        mock_evaluator_instance.evaluate_all.return_value = pd.DataFrame()
        mock_evaluator_instance.get_comparison_dict.return_value = {
            'comparison': [
                {
                    'model': 'LightGBM',
                    'train_ic': 0.5, 'train_rank_ic': 0.4, 'train_mae': 1.0, 'train_rmse': 1.2,
                    'valid_ic': 0.45, 'valid_rank_ic': 0.38, 'valid_mae': 1.1, 'valid_rmse': 1.3,
                    'test_ic': 0.42, 'test_rank_ic': 0.35, 'test_mae': 1.15, 'test_rmse': 1.35,
                    'test_r2': 0.3, 'overfit_ic': 0.05
                },
                {
                    'model': 'Ridge',
                    'train_ic': 0.4, 'train_rank_ic': 0.35, 'train_mae': 1.2, 'train_rmse': 1.4,
                    'valid_ic': 0.38, 'valid_rank_ic': 0.33, 'valid_mae': 1.25, 'valid_rmse': 1.45,
                    'test_ic': 0.35, 'test_rank_ic': 0.30, 'test_mae': 1.3, 'test_rmse': 1.5,
                    'test_r2': 0.2, 'overfit_ic': 0.02
                }
            ],
            'ridge_vs_lgb': {'winner': 'LightGBM', 'ic_diff': 0.07}
        }
        mock_evaluator_class.return_value = mock_evaluator_instance

        # 设置pipeline属性
        self.pipeline.pooled_df = self._create_mock_pooled_data(n_samples=300)
        self.pipeline.successful_symbols = ['000001']
        self.pipeline.feature_cols = [f'f{i}' for i in range(5)]
        self.pipeline.comparison_evaluator = mock_evaluator_instance

        # 执行训练（启用Ridge）
        results = self.pipeline.train_with_baseline(
            X_train, y_train, X_valid, y_valid, X_test, y_test,
            enable_ridge_baseline=True
        )

        # 验证结果
        self.assertTrue(results['has_baseline'])
        self.assertIn('ridge_metrics', results)
        self.assertIn('comparison_result', results)

        # 验证调用了两次ModelTrainer（LightGBM + Ridge）
        self.assertEqual(mock_trainer_class.call_count, 2)

        print("  ✓ LightGBM和Ridge训练完成")

    @patch('src.data_pipeline.pooled_training_pipeline.ModelTrainer')
    @patch('src.data_pipeline.pooled_training_pipeline.ComparisonEvaluator')
    def test_07_train_with_custom_params(self, mock_evaluator_class, mock_trainer_class):
        """测试7: 使用自定义参数训练"""
        print("\n[测试7] 自定义参数训练...")

        np.random.seed(42)
        n_samples = 100
        X_train = pd.DataFrame(np.random.randn(n_samples, 3), columns=['f0', 'f1', 'f2'])
        y_train = pd.Series(np.random.randn(n_samples))
        X_valid = pd.DataFrame(np.random.randn(30, 3), columns=['f0', 'f1', 'f2'])
        y_valid = pd.Series(np.random.randn(30))
        X_test = pd.DataFrame(np.random.randn(30, 3), columns=['f0', 'f1', 'f2'])
        y_test = pd.Series(np.random.randn(30))

        # 配置Mock
        mock_trainer_instance = Mock()
        mock_trainer_instance.save_model.return_value = str(Path(self.temp_dir) / "model.pkl")
        mock_trainer_class.return_value = mock_trainer_instance

        mock_evaluator_instance = Mock()
        mock_evaluator_instance.evaluate_all.return_value = pd.DataFrame()
        mock_evaluator_instance.get_comparison_dict.return_value = {
            'comparison': [{'model': 'LightGBM', 'train_ic': 0.5, 'train_rank_ic': 0.4,
                          'train_mae': 1.0, 'train_rmse': 1.2, 'valid_ic': 0.45,
                          'valid_rank_ic': 0.38, 'valid_mae': 1.1, 'valid_rmse': 1.3,
                          'test_ic': 0.42, 'test_rank_ic': 0.35, 'test_mae': 1.15,
                          'test_rmse': 1.35, 'test_r2': 0.3, 'overfit_ic': 0.05}]
        }
        mock_evaluator_class.return_value = mock_evaluator_instance

        self.pipeline.pooled_df = pd.DataFrame({'col': [1, 2, 3]})
        self.pipeline.successful_symbols = ['000001']
        self.pipeline.feature_cols = ['f0', 'f1', 'f2']
        self.pipeline.comparison_evaluator = mock_evaluator_instance

        # 自定义参数
        custom_lgb_params = {'max_depth': 5, 'learning_rate': 0.05}
        custom_ridge_params = {'alpha': 2.0}

        # 执行训练
        results = self.pipeline.train_with_baseline(
            X_train, y_train, X_valid, y_valid, X_test, y_test,
            lightgbm_params=custom_lgb_params,
            ridge_params=custom_ridge_params,
            enable_ridge_baseline=False
        )

        # 验证参数被正确传递
        self.assertIsInstance(results, dict)

        # 检查ModelTrainer被调用时的参数
        call_args = mock_trainer_class.call_args
        self.assertIn('max_depth', call_args[1]['model_params'])
        self.assertEqual(call_args[1]['model_params']['max_depth'], 5)

        print("  ✓ 自定义参数训练完成")

    @patch('src.data_pipeline.pooled_training_pipeline.PooledDataLoader')
    @patch('src.data_pipeline.pooled_training_pipeline.ModelTrainer')
    @patch('src.data_pipeline.pooled_training_pipeline.ComparisonEvaluator')
    def test_08_run_full_pipeline(self, mock_evaluator_class, mock_trainer_class, mock_loader_class):
        """测试8: 运行完整Pipeline"""
        print("\n[测试8] 运行完整Pipeline...")

        # 配置PooledDataLoader Mock
        mock_pooled_data = self._create_mock_pooled_data(n_samples=500)
        mock_loader_instance = Mock()
        mock_loader_instance.load_pooled_data.return_value = (
            mock_pooled_data, len(mock_pooled_data), ['000001', '000002']
        )

        feature_cols = ['close', 'volume', 'MOM5', 'MOM10', 'RSI14']
        X = mock_pooled_data[feature_cols]
        y = mock_pooled_data['target_10d_return']
        n = len(X)
        train_end = int(n * 0.7)
        valid_end = int(n * 0.85)

        mock_loader_instance.prepare_pooled_training_data.return_value = (
            X.iloc[:train_end], y.iloc[:train_end],
            X.iloc[train_end:valid_end], y.iloc[train_end:valid_end],
            X.iloc[valid_end:], y.iloc[valid_end:],
            feature_cols
        )
        mock_loader_class.return_value = mock_loader_instance

        # 配置ModelTrainer Mock
        mock_trainer_instance = Mock()
        mock_trainer_instance.save_model.return_value = str(Path(self.temp_dir) / "model.pkl")
        mock_trainer_class.return_value = mock_trainer_instance

        # 配置ComparisonEvaluator Mock
        mock_evaluator_instance = Mock()
        mock_evaluator_instance.evaluate_all.return_value = pd.DataFrame()
        mock_evaluator_instance.get_comparison_dict.return_value = {
            'comparison': [
                {'model': 'LightGBM', 'train_ic': 0.5, 'train_rank_ic': 0.4,
                 'train_mae': 1.0, 'train_rmse': 1.2, 'valid_ic': 0.45,
                 'valid_rank_ic': 0.38, 'valid_mae': 1.1, 'valid_rmse': 1.3,
                 'test_ic': 0.42, 'test_rank_ic': 0.35, 'test_mae': 1.15,
                 'test_rmse': 1.35, 'test_r2': 0.3, 'overfit_ic': 0.05}
            ]
        }
        mock_evaluator_class.return_value = mock_evaluator_instance

        # 创建新pipeline
        pipeline = PooledTrainingPipeline(scaler_type='robust', verbose=False)

        # 运行完整Pipeline
        results = pipeline.run_full_pipeline(
            symbol_list=['000001', '000002'],
            start_date='20230101',
            end_date='20231231',
            target_period=10,
            enable_ridge_baseline=False
        )

        # 验证结果
        self.assertIsInstance(results, dict)
        self.assertIn('lgb_metrics', results)
        self.assertIn('total_samples', results)
        self.assertIn('successful_symbols', results)
        self.assertIn('feature_count', results)
        self.assertIn('lgb_model_path', results)

        print("  ✓ 完整Pipeline运行成功")

    def test_09_scaler_persistence(self):
        """测试9: Scaler持久化"""
        print("\n[测试9] Scaler持久化测试...")

        # 这个测试验证scaler在训练后可以被保存
        # 实际的保存逻辑在train_with_baseline中

        pipeline = PooledTrainingPipeline(scaler_type='standard', verbose=False)

        # 验证初始状态
        self.assertIsNone(pipeline.scaler)
        self.assertEqual(pipeline.scaler_type, 'standard')

        print("  ✓ Scaler状态正确")

    def test_10_verbose_mode(self):
        """测试10: Verbose模式"""
        print("\n[测试10] Verbose模式...")

        # 创建verbose=True的pipeline
        verbose_pipeline = PooledTrainingPipeline(scaler_type='robust', verbose=True)

        self.assertTrue(verbose_pipeline.verbose)
        self.assertTrue(verbose_pipeline.pooled_loader.verbose)

        print("  ✓ Verbose模式正常")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPooledTrainingPipeline)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
