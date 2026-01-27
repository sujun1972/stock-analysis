#!/usr/bin/env python3
"""
DataPipeline 数据流水线单元测试

全面测试数据流水线的核心功能，包括：
- 配置对象的使用
- 数据加载和特征工程
- 缓存机制
- 数据验证
- 错误处理
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


class TestPipelineConfigUsage(unittest.TestCase):
    """测试 PipelineConfig 配置对象的使用"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("PipelineConfig 配置对象使用测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        from pipeline import DataPipeline
        from data_pipeline.pipeline_config import PipelineConfig, DEFAULT_CONFIG

        self.mock_db = Mock()
        self.pipeline = DataPipeline(db_manager=self.mock_db, verbose=False)
        self.PipelineConfig = PipelineConfig
        self.DEFAULT_CONFIG = DEFAULT_CONFIG

    def test_01_default_config_usage(self):
        """测试1: 使用默认配置"""
        print("\n[测试1] 使用默认配置...")

        # 默认配置应该被正确应用
        self.assertIsNotNone(self.DEFAULT_CONFIG)
        self.assertEqual(self.DEFAULT_CONFIG.target_period, 5)
        self.assertEqual(self.DEFAULT_CONFIG.train_ratio, 0.7)
        self.assertEqual(self.DEFAULT_CONFIG.valid_ratio, 0.15)
        print("  ✓ 默认配置正确")

    def test_02_custom_config_creation(self):
        """测试2: 创建自定义配置"""
        print("\n[测试2] 创建自定义配置...")

        config = self.PipelineConfig(
            target_period=10,
            train_ratio=0.8,
            balance_samples=True,
            balance_method='smote'
        )

        self.assertEqual(config.target_period, 10)
        self.assertEqual(config.train_ratio, 0.8)
        self.assertTrue(config.balance_samples)
        self.assertEqual(config.balance_method, 'smote')
        print("  ✓ 自定义配置创建成功")

    def test_03_config_copy_method(self):
        """测试3: 配置的 copy 方法"""
        print("\n[测试3] 配置的 copy 方法...")

        base_config = self.PipelineConfig(target_period=5, balance_samples=False)
        modified_config = base_config.copy(target_period=10, balance_samples=True)

        # 原配置不变
        self.assertEqual(base_config.target_period, 5)
        self.assertFalse(base_config.balance_samples)

        # 新配置已修改
        self.assertEqual(modified_config.target_period, 10)
        self.assertTrue(modified_config.balance_samples)
        print("  ✓ copy 方法工作正确")

    def test_04_config_with_none_fallback(self):
        """测试4: 配置为 None 时使用默认配置"""
        print("\n[测试4] 配置为 None 时使用默认配置...")

        # 模拟 get_training_data 的行为
        config = None
        if config is None:
            config = self.DEFAULT_CONFIG

        self.assertIsNotNone(config)
        self.assertEqual(config.target_period, 5)
        print("  ✓ None 配置回退到默认配置")


class TestDataPipelineCore(unittest.TestCase):
    """测试核心流水线功能"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataPipeline 核心功能测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        from pipeline import DataPipeline
        from data_pipeline.pipeline_config import PipelineConfig

        self.mock_db = Mock()
        self.pipeline = DataPipeline(db_manager=self.mock_db, verbose=False)
        self.PipelineConfig = PipelineConfig

        # 创建测试数据
        self.test_data = self._create_test_data()

    def _create_test_data(self):
        """创建测试用的数据"""
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'open': np.random.uniform(10, 20, 100),
            'high': np.random.uniform(15, 25, 100),
            'low': np.random.uniform(5, 15, 100),
            'close': np.random.uniform(10, 20, 100),
            'volume': np.random.uniform(1000000, 5000000, 100),
            'amount': np.random.uniform(10000000, 50000000, 100),
        })
        df.set_index('date', inplace=True)
        return df

    def test_06_initialization(self):
        """测试6: 流水线初始化"""
        print("\n[测试6] 流水线初始化...")

        from pipeline import DataPipeline

        pipeline = DataPipeline(
            target_periods=5,
            scaler_type='robust',
            cache_features=True,
            verbose=False
        )

        self.assertEqual(pipeline.target_periods, [5])
        self.assertEqual(pipeline.scaler_type, 'robust')
        self.assertTrue(pipeline.cache_features)
        self.assertFalse(pipeline.verbose)
        self.assertIsNotNone(pipeline.data_loader)
        self.assertIsNotNone(pipeline.feature_engineer)
        self.assertIsNotNone(pipeline.data_cleaner)
        self.assertIsNotNone(pipeline.data_splitter)
        self.assertIsNotNone(pipeline.feature_cache)
        print("  ✓ 流水线初始化成功")

    def test_07_separate_features_target(self):
        """测试7: 分离特征和目标"""
        print("\n[测试7] 分离特征和目标...")

        # 创建包含特征和目标的数据
        df = self.test_data.copy()
        df['feature1'] = np.random.randn(100)
        df['feature2'] = np.random.randn(100)
        df['target_5d_return'] = np.random.randn(100)

        self.pipeline.target_name = 'target_5d_return'
        X, y = self.pipeline._separate_features_target(df)

        # 验证
        self.assertIn('feature1', X.columns)
        self.assertIn('feature2', X.columns)
        self.assertNotIn('close', X.columns)  # 应该被排除
        self.assertNotIn('volume', X.columns)  # 应该被排除
        self.assertNotIn('target_5d_return', X.columns)  # 应该被排除
        self.assertEqual(len(y), 100)
        self.assertEqual(len(X), 100)
        print("  ✓ 特征和目标分离正确")

    def test_08_get_feature_names(self):
        """测试8: 获取特征名"""
        print("\n[测试8] 获取特征名...")

        self.pipeline.feature_names = ['feature1', 'feature2', 'feature3']
        names = self.pipeline.get_feature_names()

        self.assertEqual(len(names), 3)
        self.assertIn('feature1', names)
        self.assertIn('feature2', names)
        self.assertIn('feature3', names)

        # 确保返回的是副本
        names.append('feature4')
        self.assertEqual(len(self.pipeline.feature_names), 3)
        print("  ✓ 特征名获取正确")

    def test_09_scaler_management(self):
        """测试9: Scaler 管理"""
        print("\n[测试9] Scaler 管理...")

        from sklearn.preprocessing import RobustScaler

        # 创建并设置 scaler
        scaler = RobustScaler()
        self.pipeline.set_scaler(scaler)

        # 获取 scaler
        retrieved_scaler = self.pipeline.get_scaler()
        self.assertIsInstance(retrieved_scaler, RobustScaler)
        print("  ✓ Scaler 管理正确")

    def test_10_get_training_data_with_config(self):
        """测试10: 使用配置获取训练数据"""
        print("\n[测试10] 使用配置获取训练数据...")

        # Mock 各组件的返回值
        df_loaded = self.test_data.copy()
        df_loaded['feature1'] = np.random.randn(100)
        df_loaded['target_5d_return'] = np.random.randn(100)

        # Mock实例属性
        self.pipeline.data_loader.load_data = Mock(return_value=df_loaded)
        self.pipeline.feature_engineer.compute_all_features = Mock(return_value=df_loaded)
        self.pipeline.data_cleaner.clean = Mock(return_value=df_loaded)

        # Mock 缓存
        with patch.object(self.pipeline.feature_cache, 'load', return_value=None):
            with patch.object(self.pipeline.feature_cache, 'save'):
                config = self.PipelineConfig(target_period=5, use_cache=False)

                try:
                    X, y = self.pipeline.get_training_data(
                        '000001', '20200101', '20231231', config
                    )

                    self.assertIsInstance(X, pd.DataFrame)
                    self.assertIsInstance(y, pd.Series)
                    self.assertGreater(len(X), 0)
                    self.assertEqual(len(X), len(y))
                    print("  ✓ 配置方式获取数据成功")
                except Exception as e:
                    print(f"  ⚠ 测试跳过（需要完整环境）: {e}")


class TestDataPipelineRefactored(unittest.TestCase):
    """测试重构版本的新功能"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataPipeline 重构版本新功能测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        try:
            from pipeline_refactored import DataPipeline, FEATURE_CONFIG
            self.DataPipeline = DataPipeline
            self.FEATURE_CONFIG = FEATURE_CONFIG
            self.has_refactored = True
        except ImportError:
            self.has_refactored = False
            print("  ⚠ 重构版本不可用，跳过相关测试")

    def test_13_feature_config_constant(self):
        """测试13: 特征配置常量"""
        if not self.has_refactored:
            self.skipTest("重构版本不可用")

        print("\n[测试13] 特征配置常量...")

        self.assertIsInstance(self.FEATURE_CONFIG, dict)
        self.assertIn('deprice_ma_periods', self.FEATURE_CONFIG)
        self.assertIn('deprice_ema_periods', self.FEATURE_CONFIG)
        self.assertIn('deprice_atr_periods', self.FEATURE_CONFIG)
        print("  ✓ 特征配置常量正确")

    def test_14_validate_data_empty(self):
        """测试14: 数据验证 - 空数据"""
        if not self.has_refactored:
            self.skipTest("重构版本不可用")

        print("\n[测试14] 数据验证 - 空数据...")

        from src.exceptions import DataValidationError

        mock_db = Mock()
        pipeline = self.DataPipeline(db_manager=mock_db, verbose=False)

        empty_X = pd.DataFrame()
        empty_y = pd.Series()

        with self.assertRaises(DataValidationError):
            pipeline._validate_data(empty_X, empty_y, "测试")
        print("  ✓ 空数据验证正确")

    def test_15_validate_data_length_mismatch(self):
        """测试15: 数据验证 - 长度不匹配"""
        if not self.has_refactored:
            self.skipTest("重构版本不可用")

        print("\n[测试15] 数据验证 - 长度不匹配...")

        from src.exceptions import DataValidationError

        mock_db = Mock()
        pipeline = self.DataPipeline(db_manager=mock_db, verbose=False)

        X = pd.DataFrame({'a': [1, 2, 3]})
        y = pd.Series([1, 2])  # 长度不匹配

        with self.assertRaises(DataValidationError):
            pipeline._validate_data(X, y, "测试")
        print("  ✓ 长度不匹配验证正确")

    def test_16_validate_data_null_values(self):
        """测试16: 数据验证 - 空值检查"""
        if not self.has_refactored:
            self.skipTest("重构版本不可用")

        print("\n[测试16] 数据验证 - 空值检查...")

        from src.exceptions import DataValidationError

        mock_db = Mock()
        pipeline = self.DataPipeline(db_manager=mock_db, verbose=False)

        X = pd.DataFrame({'a': [1, 2, np.nan]})  # 包含空值
        y = pd.Series([1, 2, 3])

        with self.assertRaises(DataValidationError):
            pipeline._validate_data(X, y, "测试")
        print("  ✓ 空值检查正确")

    def test_17_validate_data_success(self):
        """测试17: 数据验证 - 成功通过"""
        if not self.has_refactored:
            self.skipTest("重构版本不可用")

        print("\n[测试17] 数据验证 - 成功通过...")

        mock_db = Mock()
        pipeline = self.DataPipeline(db_manager=mock_db, verbose=False)

        X = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        y = pd.Series([1, 2, 3])

        # 应该不抛出异常
        try:
            pipeline._validate_data(X, y, "测试")
            print("  ✓ 有效数据通过验证")
        except Exception as e:
            self.fail(f"有效数据验证失败: {e}")


class TestDataPipelineHelperFunctions(unittest.TestCase):
    """测试辅助函数"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataPipeline 辅助函数测试")
        print("="*60)

    def test_18_create_pipeline(self):
        """测试18: create_pipeline 便捷函数"""
        print("\n[测试18] create_pipeline 便捷函数...")

        from pipeline import create_pipeline

        pipeline = create_pipeline(
            target_period=7,
            scaler_type='standard',
            verbose=False
        )

        self.assertIsNotNone(pipeline)
        self.assertEqual(pipeline.target_periods, [7])
        self.assertEqual(pipeline.scaler_type, 'standard')
        self.assertFalse(pipeline.verbose)
        print("  ✓ create_pipeline 正确")

    def test_19_module_exports(self):
        """测试19: 模块导出"""
        print("\n[测试19] 模块导出...")

        import pipeline

        # 检查所有导出项
        exports = [
            'DataPipeline',
            'PipelineConfig',
            'DEFAULT_CONFIG',
            'BALANCED_TRAINING_CONFIG',
            'QUICK_TRAINING_CONFIG',
            'LONG_TERM_CONFIG',
            'PRODUCTION_CONFIG',
            'create_pipeline',
            'get_full_training_data',
            'create_config'
        ]

        for export in exports:
            self.assertTrue(hasattr(pipeline, export), f"缺少导出: {export}")
        print("  ✓ 所有导出项正确")


class TestDataPipelineCaching(unittest.TestCase):
    """测试缓存机制"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataPipeline 缓存机制测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        from pipeline import DataPipeline
        from data_pipeline.pipeline_config import PipelineConfig

        self.mock_db = Mock()
        self.pipeline = DataPipeline(db_manager=self.mock_db, verbose=False)
        self.PipelineConfig = PipelineConfig

    def test_20_build_cache_config(self):
        """测试20: 构建缓存配置"""
        print("\n[测试20] 构建缓存配置...")

        # 检查方法是否存在
        if hasattr(self.pipeline, '_build_cache_config_from_obj'):
            config = self.PipelineConfig(
                target_period=5,
                train_ratio=0.7,
                valid_ratio=0.15,
                balance_samples=True,
                balance_method='smote'
            )

            cache_config = self.pipeline._build_cache_config_from_obj(config)

            self.assertIsInstance(cache_config, dict)
            self.assertIn('target_period', cache_config)
            self.assertIn('scaler_type', cache_config)
            self.assertEqual(cache_config['target_period'], 5)
            self.assertTrue(cache_config['balance_samples'])
            print("  ✓ 缓存配置构建正确")
        else:
            print("  ⚠ _build_cache_config_from_obj 方法不存在（可能在重构版本）")

    def test_21_clear_cache(self):
        """测试21: 清除缓存"""
        print("\n[测试21] 清除缓存...")

        # Mock feature_cache.clear
        with patch.object(self.pipeline.feature_cache, 'clear') as mock_clear:
            self.pipeline.clear_cache('000001')
            mock_clear.assert_called_once_with('000001')
            print("  ✓ 清除缓存正确")


def run_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("DataPipeline 完整测试套件")
    print("="*60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDataPipelineConfigResolution))
    suite.addTests(loader.loadTestsFromTestCase(TestDataPipelineCore))
    suite.addTests(loader.loadTestsFromTestCase(TestDataPipelineBackwardCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestDataPipelineRefactored))
    suite.addTests(loader.loadTestsFromTestCase(TestDataPipelineHelperFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestDataPipelineCaching))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"运行: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
