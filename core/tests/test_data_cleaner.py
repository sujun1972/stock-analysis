#!/usr/bin/env python3
"""
DataCleaner 单元测试

测试数据清洗器的功能
"""

import sys
import unittest
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from data_pipeline.data_cleaner import DataCleaner


class TestDataCleaner(unittest.TestCase):
    """测试 DataCleaner 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataCleaner 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        self.cleaner = DataCleaner(verbose=False)

        # 创建测试数据
        np.random.seed(42)
        self.test_data = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'feature3': np.random.randn(100),
            'target': np.random.randn(100)
        })

    def test_01_init(self):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        cleaner = DataCleaner(verbose=False)
        self.assertIsNotNone(cleaner)
        self.assertEqual(cleaner.verbose, False)
        self.assertIsInstance(cleaner.stats, dict)

        print("  ✓ 初始化成功")

    def test_02_clean_normal_data(self):
        """测试2: 清洗正常数据"""
        print("\n[测试2] 清洗正常数据...")

        result = self.cleaner.clean(self.test_data, 'target')

        # 验证返回值
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)

        # 正常数据不应该被大量删除
        self.assertGreaterEqual(len(result), len(self.test_data) * 0.9)

        print(f"  ✓ 原始: {len(self.test_data)}, 清洗后: {len(result)}")

    def test_03_handle_inf_values(self):
        """测试3: 处理无穷值"""
        print("\n[测试3] 处理无穷值...")

        # 添加无穷值
        data_with_inf = self.test_data.copy()
        data_with_inf.loc[5, 'feature1'] = np.inf
        data_with_inf.loc[10, 'feature2'] = -np.inf

        result = self.cleaner.clean(data_with_inf, 'target')

        # 验证无穷值被处理
        self.assertFalse(np.isinf(result.values).any())

        print(f"  ✓ 无穷值已处理")

    def test_04_remove_feature_nan(self):
        """测试4: 移除特征 NaN"""
        print("\n[测试4] 移除特征 NaN...")

        # 添加特征 NaN
        data_with_nan = self.test_data.copy()
        data_with_nan.loc[5:10, 'feature1'] = np.nan

        result = self.cleaner.clean(data_with_nan, 'target')

        # 验证特征列无 NaN
        feature_cols = [c for c in result.columns if c != 'target']
        self.assertFalse(result[feature_cols].isna().any().any())

        # 验证统计信息
        stats = self.cleaner.get_stats()
        self.assertGreater(stats['removed_nan'], 0)

        print(f"  ✓ 移除特征NaN: {stats['removed_nan']} 条")

    def test_05_remove_target_nan(self):
        """测试5: 移除目标 NaN"""
        print("\n[测试5] 移除目标 NaN...")

        # 添加目标 NaN
        data_with_nan = self.test_data.copy()
        data_with_nan.loc[80:90, 'target'] = np.nan

        result = self.cleaner.clean(data_with_nan, 'target')

        # 验证目标列无 NaN
        self.assertFalse(result['target'].isna().any())

        # 验证统计信息
        stats = self.cleaner.get_stats()
        self.assertGreaterEqual(stats['removed_target_nan'], 10)

        print(f"  ✓ 移除目标NaN: {stats['removed_target_nan']} 条")

    def test_06_clip_outliers(self):
        """测试6: 截断极端值"""
        print("\n[测试6] 截断极端值...")

        # 添加极端值
        data_with_outliers = self.test_data.copy()
        data_with_outliers.loc[5, 'feature1'] = 100  # 极大值
        data_with_outliers.loc[10, 'feature2'] = -100  # 极小值

        result = self.cleaner.clean(
            data_with_outliers,
            'target',
            clip_quantile_low=0.01,
            clip_quantile_high=0.99
        )

        # 验证极端值被截断
        self.assertLess(result['feature1'].max(), 100)
        self.assertGreater(result['feature2'].min(), -100)

        print(f"  ✓ 极端值已截断")

    def test_07_stats_tracking(self):
        """测试7: 统计信息追踪"""
        print("\n[测试7] 统计信息追踪...")

        data = self.test_data.copy()
        # 添加各种问题
        data.loc[5:10, 'feature1'] = np.nan
        data.loc[80:90, 'target'] = np.nan
        data.loc[15, 'feature2'] = np.inf

        result = self.cleaner.clean(data, 'target')

        # 获取统计信息
        stats = self.cleaner.get_stats()

        # 验证统计信息
        self.assertIn('raw_samples', stats)
        self.assertIn('final_samples', stats)
        self.assertIn('removed_nan', stats)
        self.assertIn('removed_target_nan', stats)

        self.assertEqual(stats['raw_samples'], len(data))
        self.assertEqual(stats['final_samples'], len(result))
        self.assertGreater(stats['removed_nan'], 0)
        self.assertGreater(stats['removed_target_nan'], 0)

        print(f"  原始样本: {stats['raw_samples']}")
        print(f"  最终样本: {stats['final_samples']}")
        print(f"  移除特征NaN: {stats['removed_nan']}")
        print(f"  移除目标NaN: {stats['removed_target_nan']}")
        print(f"  ✓ 统计信息正确")

    def test_08_empty_data(self):
        """测试8: 空数据"""
        print("\n[测试8] 空数据...")

        empty_data = pd.DataFrame()
        result = self.cleaner.clean(empty_data, 'target')

        self.assertEqual(len(result), 0)

        print(f"  ✓ 空数据处理正确")

    def test_09_all_nan_features(self):
        """测试9: 所有特征都是 NaN"""
        print("\n[测试9] 所有特征都是 NaN...")

        data_all_nan = self.test_data.copy()
        data_all_nan.loc[:, ['feature1', 'feature2', 'feature3']] = np.nan

        result = self.cleaner.clean(data_all_nan, 'target')

        # 所有特征都是 NaN，清洗后应该为空
        self.assertEqual(len(result), 0)

        print(f"  ✓ 全NaN特征处理正确")

    def test_10_preservation_rate(self):
        """测试10: 数据保留率"""
        print("\n[测试10] 数据保留率...")

        # 正常数据应该有高保留率
        result = self.cleaner.clean(self.test_data, 'target')

        stats = self.cleaner.get_stats()
        preservation_rate = stats['final_samples'] / stats['raw_samples']

        self.assertGreater(preservation_rate, 0.95)  # 至少95%保留率

        print(f"  ✓ 保留率: {preservation_rate*100:.1f}%")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDataCleaner)
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
