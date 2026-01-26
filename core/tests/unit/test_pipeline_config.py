#!/usr/bin/env python3
"""
PipelineConfig 配置类单元测试

测试配置类的功能和验证逻辑
"""

import sys
import unittest
from pathlib import Path

# 添加项目路径 - 直接指向 data_pipeline 目录以避免 __init__.py 依赖
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src' / 'data_pipeline'))


class TestPipelineConfig(unittest.TestCase):
    """测试 PipelineConfig 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("PipelineConfig 配置类单元测试")
        print("="*60)

    def test_01_default_config(self):
        """测试1: 默认配置"""
        print("\n[测试1] 默认配置...")

        from pipeline_config import PipelineConfig

        config = PipelineConfig()

        self.assertEqual(config.target_period, 5)
        self.assertEqual(config.train_ratio, 0.7)
        self.assertEqual(config.valid_ratio, 0.15)
        self.assertFalse(config.balance_samples)
        self.assertEqual(config.balance_method, 'none')
        self.assertTrue(config.scale_features)
        self.assertEqual(config.scaler_type, 'robust')

        print("  ✓ 默认配置正确")

    def test_02_custom_config(self):
        """测试2: 自定义配置"""
        print("\n[测试2] 自定义配置...")

        from pipeline_config import PipelineConfig

        config = PipelineConfig(
            target_period=10,
            train_ratio=0.8,
            valid_ratio=0.1,
            balance_samples=True,
            balance_method='smote'
        )

        self.assertEqual(config.target_period, 10)
        self.assertEqual(config.train_ratio, 0.8)
        self.assertEqual(config.valid_ratio, 0.1)
        self.assertTrue(config.balance_samples)
        self.assertEqual(config.balance_method, 'smote')

        print("  ✓ 自定义配置正确")

    def test_03_validation_train_ratio(self):
        """测试3: 训练集比例验证"""
        print("\n[测试3] 训练集比例验证...")

        from pipeline_config import PipelineConfig

        # 无效比例应该抛出异常
        with self.assertRaises(ValueError):
            PipelineConfig(train_ratio=0)

        with self.assertRaises(ValueError):
            PipelineConfig(train_ratio=1.0)

        with self.assertRaises(ValueError):
            PipelineConfig(train_ratio=-0.5)

        print("  ✓ 训练集比例验证正确")

    def test_04_validation_ratios_sum(self):
        """测试4: 比例总和验证"""
        print("\n[测试4] 比例总和验证...")

        from pipeline_config import PipelineConfig

        # train_ratio + valid_ratio 必须 < 1
        with self.assertRaises(ValueError):
            PipelineConfig(train_ratio=0.7, valid_ratio=0.3)

        with self.assertRaises(ValueError):
            PipelineConfig(train_ratio=0.5, valid_ratio=0.6)

        # 合法的比例
        config = PipelineConfig(train_ratio=0.7, valid_ratio=0.2)
        self.assertIsNotNone(config)

        print("  ✓ 比例总和验证正确")

    def test_05_auto_balance_method(self):
        """测试5: 自动设置平衡方法"""
        print("\n[测试5] 自动设置平衡方法...")

        from pipeline_config import PipelineConfig

        # 当 balance_samples=True 但 balance_method='none'时，自动设置
        config = PipelineConfig(balance_samples=True, balance_method='none')

        self.assertTrue(config.balance_samples)
        self.assertEqual(config.balance_method, 'undersample')  # 自动设置为默认值

        print("  ✓ 自动设置平衡方法正确")

    def test_06_to_dict(self):
        """测试6: 转换为字典"""
        print("\n[测试6] 转换为字典...")

        from pipeline_config import PipelineConfig

        config = PipelineConfig(
            target_period=5,
            train_ratio=0.7,
            valid_ratio=0.15,
            balance_samples=True,
            balance_method='smote',
            scaler_type='standard'
        )

        config_dict = config.to_dict()

        self.assertEqual(config_dict['target_period'], 5)
        self.assertEqual(config_dict['train_ratio'], 0.7)
        self.assertEqual(config_dict['valid_ratio'], 0.15)
        self.assertTrue(config_dict['balance_samples'])
        self.assertEqual(config_dict['balance_method'], 'smote')
        self.assertEqual(config_dict['scaler_type'], 'standard')

        print("  ✓ 转换为字典正确")

    def test_07_from_dict(self):
        """测试7: 从字典创建"""
        print("\n[测试7] 从字典创建...")

        from pipeline_config import PipelineConfig

        config_dict = {
            'target_period': 10,
            'train_ratio': 0.8,
            'valid_ratio': 0.1,
            'balance_samples': True,
            'balance_method': 'oversample',
            'scaler_type': 'minmax'
        }

        config = PipelineConfig.from_dict(config_dict)

        self.assertEqual(config.target_period, 10)
        self.assertEqual(config.train_ratio, 0.8)
        self.assertEqual(config.valid_ratio, 0.1)
        self.assertTrue(config.balance_samples)
        self.assertEqual(config.balance_method, 'oversample')
        self.assertEqual(config.scaler_type, 'minmax')

        print("  ✓ 从字典创建正确")

    def test_08_copy(self):
        """测试8: 复制配置"""
        print("\n[测试8] 复制配置...")

        from pipeline_config import PipelineConfig

        config1 = PipelineConfig(target_period=5, balance_samples=False)
        config2 = config1.copy(target_period=10, balance_samples=True)

        # 原配置不变
        self.assertEqual(config1.target_period, 5)
        self.assertFalse(config1.balance_samples)

        # 新配置已修改
        self.assertEqual(config2.target_period, 10)
        self.assertTrue(config2.balance_samples)

        print("  ✓ 复制配置正确")

    def test_09_predefined_configs(self):
        """测试9: 预定义配置"""
        print("\n[测试9] 预定义配置...")

        from pipeline_config import (
            DEFAULT_CONFIG,
            QUICK_TRAINING_CONFIG,
            BALANCED_TRAINING_CONFIG,
            LONG_TERM_CONFIG,
            PRODUCTION_CONFIG
        )

        # DEFAULT_CONFIG
        self.assertEqual(DEFAULT_CONFIG.target_period, 5)
        self.assertFalse(DEFAULT_CONFIG.balance_samples)

        # QUICK_TRAINING_CONFIG
        self.assertEqual(QUICK_TRAINING_CONFIG.target_period, 3)

        # BALANCED_TRAINING_CONFIG
        self.assertTrue(BALANCED_TRAINING_CONFIG.balance_samples)
        self.assertEqual(BALANCED_TRAINING_CONFIG.balance_method, 'undersample')

        # LONG_TERM_CONFIG
        self.assertEqual(LONG_TERM_CONFIG.target_period, 20)
        self.assertEqual(LONG_TERM_CONFIG.train_ratio, 0.8)

        # PRODUCTION_CONFIG
        self.assertTrue(PRODUCTION_CONFIG.balance_samples)
        self.assertEqual(PRODUCTION_CONFIG.balance_method, 'smote')

        print("  ✓ 所有预定义配置正确")

    def test_10_create_config_helper(self):
        """测试10: create_config 便捷函数"""
        print("\n[测试10] create_config 便捷函数...")

        from pipeline_config import create_config

        config = create_config(
            target_period=7,
            train_ratio=0.75,
            balance_samples=True
        )

        self.assertEqual(config.target_period, 7)
        self.assertEqual(config.train_ratio, 0.75)
        self.assertTrue(config.balance_samples)

        print("  ✓ create_config 正确")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPipelineConfig)
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
