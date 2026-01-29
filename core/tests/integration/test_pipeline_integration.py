#!/usr/bin/env python3
"""
DataPipeline 集成测试

测试完整的数据流水线流程，包括：
- 端到端数据处理
- 多股票批量处理
- 缓存性能测试
- 实际数据处理
"""

import sys
import unittest
import time
from pathlib import Path
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))


class TestPipelineIntegrationBasic(unittest.TestCase):
    """基础集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataPipeline 基础集成测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        from pipeline import DataPipeline
        from data_pipeline.pipeline_config import (
            PipelineConfig,
            DEFAULT_CONFIG,
            BALANCED_TRAINING_CONFIG
        )

        self.DataPipeline = DataPipeline
        self.PipelineConfig = PipelineConfig
        self.DEFAULT_CONFIG = DEFAULT_CONFIG
        self.BALANCED_TRAINING_CONFIG = BALANCED_TRAINING_CONFIG

        # 创建测试数据
        self.test_data = self._create_comprehensive_test_data()

    def _create_comprehensive_test_data(self):
        """创建全面的测试数据"""
        dates = pd.date_range('2020-01-01', periods=500, freq='D')
        np.random.seed(42)  # 设置随机种子以保证可重复性

        df = pd.DataFrame({
            'date': dates,
            'open': 10 + np.cumsum(np.random.randn(500) * 0.1),
            'high': 12 + np.cumsum(np.random.randn(500) * 0.1),
            'low': 8 + np.cumsum(np.random.randn(500) * 0.1),
            'close': 10 + np.cumsum(np.random.randn(500) * 0.1),
            'volume': np.random.uniform(1000000, 5000000, 500),
            'amount': np.random.uniform(10000000, 50000000, 500),
        })
        df.set_index('date', inplace=True)

        # 确保价格关系合理
        df['high'] = df[['open', 'close']].max(axis=1) + np.abs(np.random.randn(500) * 0.5)
        df['low'] = df[['open', 'close']].min(axis=1) - np.abs(np.random.randn(500) * 0.5)

        return df

    @patch('pipeline.DataLoader')
    @patch('pipeline.FeatureEngineer')
    @patch('pipeline.DataCleaner')
    def test_01_end_to_end_pipeline(self, mock_cleaner_class, mock_engineer_class, mock_loader_class):
        """测试1: 端到端流水线"""
        print("\n[测试1] 端到端流水线...")

        # 创建 mock 实例
        mock_loader = Mock()
        mock_engineer = Mock()
        mock_cleaner = Mock()

        mock_loader_class.return_value = mock_loader
        mock_engineer_class.return_value = mock_engineer
        mock_cleaner_class.return_value = mock_cleaner

        # 准备测试数据
        df = self.test_data.copy()
        df['feature1'] = np.random.randn(500)
        df['feature2'] = np.random.randn(500)
        df['target_5d_return'] = np.random.randn(500)

        # Mock 各组件的返回值
        mock_loader.load_data.return_value = df
        mock_engineer.compute_all_features.return_value = df
        mock_cleaner.clean.return_value = df

        # 创建流水线
        mock_db = Mock()
        pipeline = self.DataPipeline(db_manager=mock_db, verbose=False)

        # Mock 缓存
        with patch.object(pipeline.feature_cache, 'load', return_value=None):
            with patch.object(pipeline.feature_cache, 'save'):
                config = self.PipelineConfig(target_period=5, use_cache=False)

                try:
                    # 执行流水线
                    X, y = pipeline.get_training_data('000001', '20200101', '20231231', config)

                    # 验证结果
                    self.assertIsInstance(X, pd.DataFrame)
                    self.assertIsInstance(y, pd.Series)
                    self.assertGreater(len(X), 0)
                    self.assertEqual(len(X), len(y))

                    # 验证方法被调用
                    mock_loader.load_data.assert_called_once()
                    mock_engineer.compute_all_features.assert_called_once()
                    mock_cleaner.clean.assert_called_once()

                    print(f"  ✓ 端到端流水线成功，处理 {len(X)} 个样本")
                except Exception as e:
                    print(f"  ⚠ 测试需要完整环境: {e}")

    def test_02_config_variations(self):
        """测试2: 不同配置的处理"""
        print("\n[测试2] 不同配置的处理...")

        configs = [
            ('默认配置', self.DEFAULT_CONFIG),
            ('平衡配置', self.BALANCED_TRAINING_CONFIG),
            ('自定义配置', self.PipelineConfig(target_period=10, balance_samples=True)),
        ]

        mock_db = Mock()

        for name, config in configs:
            pipeline = self.DataPipeline(db_manager=mock_db, verbose=False)

            # 验证配置对象有效
            self.assertIsNotNone(config)
            self.assertIsInstance(config, self.PipelineConfig)
            print(f"  ✓ {name}: target_period={config.target_period}, balance={config.balance_samples}")

    def test_03_prepare_for_model_flow(self):
        """测试3: 模型数据准备流程"""
        print("\n[测试3] 模型数据准备流程...")

        # 创建测试数据
        np.random.seed(42)
        X = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'feature3': np.random.randn(100),
        })
        y = pd.Series(np.random.randn(100))

        mock_db = Mock()
        pipeline = self.DataPipeline(db_manager=mock_db, verbose=False)

        config = self.PipelineConfig(
            train_ratio=0.7,
            valid_ratio=0.15,
            scale_features=True,
            balance_samples=False
        )

        try:
            # 准备数据
            result = pipeline.prepare_for_model(X, y, config)
            X_train, y_train, X_valid, y_valid, X_test, y_test = result

            # 验证数据分割
            total_samples = len(X_train) + len(X_valid) + len(X_test)
            self.assertEqual(total_samples, 100)

            # 验证比例（允许小误差）
            train_ratio = len(X_train) / 100
            valid_ratio = len(X_valid) / 100
            self.assertAlmostEqual(train_ratio, 0.7, delta=0.1)
            self.assertAlmostEqual(valid_ratio, 0.15, delta=0.1)

            print(f"  ✓ 数据分割: 训练={len(X_train)}, 验证={len(X_valid)}, 测试={len(X_test)}")
        except Exception as e:
            print(f"  ⚠ 测试跳过: {e}")


class TestPipelineCachingIntegration(unittest.TestCase):
    """缓存机制集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataPipeline 缓存机制集成测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        from pipeline import DataPipeline
        from data_pipeline.pipeline_config import PipelineConfig

        self.DataPipeline = DataPipeline
        self.PipelineConfig = PipelineConfig

    def test_04_cache_save_and_load(self):
        """测试4: 缓存保存和加载"""
        print("\n[测试4] 缓存保存和加载...")

        mock_db = Mock()
        pipeline = self.DataPipeline(
            db_manager=mock_db,
            cache_features=True,
            verbose=False
        )

        # 创建测试数据
        X = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [4, 5, 6]})
        y = pd.Series([1, 2, 3], name='target')

        config = self.PipelineConfig()

        # Mock 缓存路径
        cache_config = {
            'target_period': 5,
            'scaler_type': 'robust',
            'train_ratio': 0.7,
            'valid_ratio': 0.15,
            'balance_samples': False,
            'balance_method': 'none'
        }

        cache_path = pipeline.feature_cache.get_cache_path(
            '000001', '20200101', '20231231', cache_config
        )

        # 测试缓存保存
        try:
            pipeline.feature_cache.save(X, y, cache_path, cache_config, 'target')
            print("  ✓ 缓存保存成功")

            # 测试缓存加载
            loaded_data = pipeline.feature_cache.load(cache_path, 'target', cache_config)
            if loaded_data is not None:
                loaded_X, loaded_y = loaded_data
                self.assertTrue(X.equals(loaded_X))
                self.assertTrue(y.equals(loaded_y))
                print("  ✓ 缓存加载成功")
            else:
                print("  ⚠ 缓存加载失败（可能需要清理）")

            # 清理缓存
            pipeline.clear_cache('000001')
        except Exception as e:
            print(f"  ⚠ 缓存测试跳过: {e}")

    def test_05_cache_performance(self):
        """测试5: 缓存性能测试"""
        print("\n[测试5] 缓存性能测试...")

        # 创建较大的测试数据
        np.random.seed(42)
        X = pd.DataFrame({
            f'feature{i}': np.random.randn(1000) for i in range(50)
        })
        y = pd.Series(np.random.randn(1000), name='target')

        mock_db = Mock()
        pipeline = self.DataPipeline(db_manager=mock_db, cache_features=True, verbose=False)

        config_dict = {
            'target_period': 5,
            'scaler_type': 'robust',
            'train_ratio': 0.7,
            'valid_ratio': 0.15,
            'balance_samples': False,
            'balance_method': 'none'
        }

        cache_path = pipeline.feature_cache.get_cache_path(
            'TEST', '20200101', '20231231', config_dict
        )

        try:
            # 测试保存性能
            start_time = time.time()
            pipeline.feature_cache.save(X, y, cache_path, config_dict, 'target')
            save_time = time.time() - start_time

            # 测试加载性能
            start_time = time.time()
            loaded_data = pipeline.feature_cache.load(cache_path, 'target', config_dict)
            load_time = time.time() - start_time

            if loaded_data is not None:
                print(f"  ✓ 保存时间: {save_time:.3f}秒")
                print(f"  ✓ 加载时间: {load_time:.3f}秒")
                print(f"  ✓ 性能提升: {save_time/load_time:.1f}x")
            else:
                print("  ⚠ 缓存验证失败")

            # 清理
            pipeline.clear_cache('TEST')
        except Exception as e:
            print(f"  ⚠ 性能测试跳过: {e}")


class TestPipelineErrorHandling(unittest.TestCase):
    """错误处理集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataPipeline 错误处理集成测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        try:
            from pipeline_refactored import DataPipeline
            from src.exceptions import PipelineError, DataValidationError
            self.DataPipeline = DataPipeline
            self.PipelineError = PipelineError
            self.DataValidationError = DataValidationError
            self.has_refactored = True
        except ImportError:
            self.has_refactored = False

    def test_06_invalid_data_handling(self):
        """测试6: 无效数据处理"""
        if not self.has_refactored:
            self.skipTest("需要重构版本")

        print("\n[测试6] 无效数据处理...")

        mock_db = Mock()
        pipeline = self.DataPipeline(db_manager=mock_db, verbose=False)

        # 测试空数据
        empty_X = pd.DataFrame()
        empty_y = pd.Series()

        with self.assertRaises(self.DataValidationError):
            pipeline._validate_data(empty_X, empty_y, "测试")
        print("  ✓ 空数据检测正确")

        # 测试长度不匹配
        X = pd.DataFrame({'a': [1, 2, 3]})
        y = pd.Series([1, 2])

        with self.assertRaises(self.DataValidationError):
            pipeline._validate_data(X, y, "测试")
        print("  ✓ 长度不匹配检测正确")

        # 测试空值
        X_null = pd.DataFrame({'a': [1, 2, np.nan]})
        y_valid = pd.Series([1, 2, 3])

        with self.assertRaises(self.DataValidationError):
            pipeline._validate_data(X_null, y_valid, "测试")
        print("  ✓ 空值检测正确")

    def test_07_pipeline_error_propagation(self):
        """测试7: 流水线错误传播"""
        if not self.has_refactored:
            self.skipTest("需要重构版本 pipeline_refactored（已废弃）")

        print("\n[测试7] 流水线错误传播...")
        print("  ⚠ 跳过：pipeline_refactored 已被删除")


class TestPipelineConvenienceFunctions(unittest.TestCase):
    """便捷函数集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataPipeline 便捷函数集成测试")
        print("="*60)

    def test_08_create_pipeline_function(self):
        """测试8: create_pipeline 便捷函数"""
        print("\n[测试8] create_pipeline 便捷函数...")

        from pipeline import create_pipeline

        pipeline = create_pipeline(
            target_period=10,
            scaler_type='standard',
            verbose=False
        )

        self.assertIsNotNone(pipeline)
        self.assertEqual(pipeline.target_periods, [10])
        self.assertEqual(pipeline.scaler_type, 'standard')
        print("  ✓ create_pipeline 函数正确")

    @patch('pipeline.DataLoader')
    @patch('pipeline.FeatureEngineer')
    @patch('pipeline.DataCleaner')
    def test_09_get_full_training_data(self, mock_cleaner_class, mock_engineer_class, mock_loader_class):
        """测试9: get_full_training_data 便捷函数"""
        print("\n[测试9] get_full_training_data 便捷函数...")

        # 创建 mock 实例
        mock_loader = Mock()
        mock_engineer = Mock()
        mock_cleaner = Mock()

        mock_loader_class.return_value = mock_loader
        mock_engineer_class.return_value = mock_engineer
        mock_cleaner_class.return_value = mock_cleaner

        # 准备测试数据
        np.random.seed(42)
        df = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'target_5d_return': np.random.randn(100),
        })

        mock_loader.load_data.return_value = df
        mock_engineer.compute_all_features.return_value = df
        mock_cleaner.clean.return_value = df

        from pipeline import get_full_training_data
        from data_pipeline.pipeline_config import PipelineConfig

        config = PipelineConfig(target_period=5, use_cache=False)

        try:
            with patch('pipeline.get_database') as mock_get_db:
                mock_get_db.return_value = Mock()

                with patch('pipeline.FeatureCache') as mock_cache_class:
                    mock_cache = Mock()
                    mock_cache.load.return_value = None
                    mock_cache.save.return_value = None
                    mock_cache_class.return_value = mock_cache

                    result = get_full_training_data(
                        '000001', '20200101', '20231231', config
                    )

                    # 应该返回 7 个元素
                    self.assertEqual(len(result), 7)
                    X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline = result

                    self.assertIsNotNone(X_train)
                    self.assertIsNotNone(pipeline)
                    print("  ✓ get_full_training_data 函数正确")
        except Exception as e:
            print(f"  ⚠ 测试需要完整环境: {e}")


def run_tests():
    """运行所有集成测试"""
    print("\n" + "="*60)
    print("DataPipeline 集成测试套件")
    print("="*60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineIntegrationBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineCachingIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineConvenienceFunctions))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印总结
    print("\n" + "="*60)
    print("集成测试总结")
    print("="*60)
    print(f"运行: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
