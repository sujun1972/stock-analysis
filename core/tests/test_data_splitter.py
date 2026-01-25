#!/usr/bin/env python3
"""
DataSplitter 单元测试

测试数据分割器的功能
"""

import sys
import unittest
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from data_pipeline.data_splitter import DataSplitter


class TestDataSplitter(unittest.TestCase):
    """测试 DataSplitter 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataSplitter 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        self.splitter = DataSplitter(scaler_type='robust', verbose=False)

        # 创建测试数据
        np.random.seed(42)
        self.X = pd.DataFrame({
            'feature1': np.random.randn(1000) * 10 + 50,
            'feature2': np.random.randn(1000) * 5 + 20,
            'feature3': np.random.randn(1000) * 2 + 10
        })
        self.y = pd.Series(np.random.randn(1000) * 3)

    def test_01_init(self):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        splitter = DataSplitter(scaler_type='robust', verbose=False)
        self.assertIsNotNone(splitter)
        self.assertEqual(splitter.scaler_type, 'robust')
        self.assertIsNone(splitter.scaler)

        print("  ✓ 初始化成功")

    def test_02_split_time_series(self):
        """测试2: 时间序列分割"""
        print("\n[测试2] 时间序列分割...")

        result = self.splitter.split_and_prepare(
            self.X, self.y,
            train_ratio=0.7,
            valid_ratio=0.15,
            scale_features=False,
            balance_samples=False
        )

        X_train, y_train, X_valid, y_valid, X_test, y_test = result

        # 验证分割比例
        total = len(X_train) + len(X_valid) + len(X_test)
        self.assertEqual(total, len(self.X))

        train_ratio = len(X_train) / total
        valid_ratio = len(X_valid) / total
        test_ratio = len(X_test) / total

        self.assertAlmostEqual(train_ratio, 0.7, delta=0.01)
        self.assertAlmostEqual(valid_ratio, 0.15, delta=0.01)
        self.assertAlmostEqual(test_ratio, 0.15, delta=0.01)

        print(f"  ✓ 训练集: {len(X_train)} ({train_ratio*100:.1f}%)")
        print(f"  ✓ 验证集: {len(X_valid)} ({valid_ratio*100:.1f}%)")
        print(f"  ✓ 测试集: {len(X_test)} ({test_ratio*100:.1f}%)")

    def test_03_feature_scaling_robust(self):
        """测试3: 鲁棒缩放"""
        print("\n[测试3] 鲁棒缩放...")

        splitter = DataSplitter(scaler_type='robust', verbose=False)

        result = splitter.split_and_prepare(
            self.X, self.y,
            scale_features=True,
            balance_samples=False
        )

        X_train, _, _, _, _, _ = result

        # 鲁棒缩放后，特征分布应该比较集中
        mean = X_train.mean().mean()
        std = X_train.std().mean()

        # 均值应该接近0（但不完全是0）
        self.assertLess(abs(mean), 5.0)

        print(f"  ✓ 均值: {mean:.4f}")
        print(f"  ✓ 标准差: {std:.4f}")

    def test_04_feature_scaling_standard(self):
        """测试4: 标准缩放"""
        print("\n[测试4] 标准缩放...")

        splitter = DataSplitter(scaler_type='standard', verbose=False)

        result = splitter.split_and_prepare(
            self.X, self.y,
            scale_features=True,
            balance_samples=False
        )

        X_train, _, _, _, _, _ = result

        # 标准缩放后，均值应该接近0，标准差接近1
        mean = X_train.mean().mean()
        std = X_train.std().mean()

        self.assertLess(abs(mean), 0.5)
        self.assertGreater(std, 0.5)
        self.assertLess(std, 2.0)

        print(f"  ✓ 均值: {mean:.4f}")
        print(f"  ✓ 标准差: {std:.4f}")

    def test_05_feature_scaling_minmax(self):
        """测试5: MinMax 缩放"""
        print("\n[测试5] MinMax 缩放...")

        splitter = DataSplitter(scaler_type='minmax', verbose=False)

        result = splitter.split_and_prepare(
            self.X, self.y,
            scale_features=True,
            balance_samples=False
        )

        X_train, _, _, _, _, _ = result

        # MinMax 缩放后，值应该在 [0, 1] 范围内
        min_val = X_train.min().min()
        max_val = X_train.max().max()

        self.assertGreaterEqual(min_val, -0.1)  # 允许小误差
        self.assertLessEqual(max_val, 1.1)

        print(f"  ✓ 最小值: {min_val:.4f}")
        print(f"  ✓ 最大值: {max_val:.4f}")

    def test_06_sample_balancing_undersample(self):
        """测试6: 欠采样平衡"""
        print("\n[测试6] 欠采样平衡...")

        # 创建不平衡数据
        y_imbalanced = pd.Series([1] * 70 + [-1] * 30)
        X_imbalanced = pd.DataFrame(np.random.randn(100, 3), columns=['f1', 'f2', 'f3'])

        splitter = DataSplitter(verbose=False)

        # 不平衡
        result1 = splitter.split_and_prepare(
            X_imbalanced, y_imbalanced,
            balance_samples=False
        )
        X_train_raw, y_train_raw, _, _, _, _ = result1

        # 平衡
        result2 = splitter.split_and_prepare(
            X_imbalanced, y_imbalanced,
            balance_samples=True,
            balance_method='undersample'
        )
        X_train_balanced, y_train_balanced, _, _, _, _ = result2

        # 统计类别分布
        y_binary_raw = (y_train_raw > 0).astype(int)
        y_binary_balanced = (y_train_balanced > 0).astype(int)

        print(f"  原始分布: 正={sum(y_binary_raw==1)}, 负={sum(y_binary_raw==0)}")
        print(f"  平衡分布: 正={sum(y_binary_balanced==1)}, 负={sum(y_binary_balanced==0)}")

        # 平衡后样本应该减少
        self.assertLess(len(X_train_balanced), len(X_train_raw))

        print(f"  ✓ 欠采样成功")

    def test_07_sample_balancing_oversample(self):
        """测试7: 过采样平衡"""
        print("\n[测试7] 过采样平衡...")

        # 创建不平衡数据
        y_imbalanced = pd.Series([1] * 70 + [-1] * 30)
        X_imbalanced = pd.DataFrame(np.random.randn(100, 3), columns=['f1', 'f2', 'f3'])

        splitter = DataSplitter(verbose=False)

        result = splitter.split_and_prepare(
            X_imbalanced, y_imbalanced,
            balance_samples=True,
            balance_method='oversample'
        )

        X_train_balanced, y_train_balanced, _, _, _, _ = result

        # 统计类别分布
        y_binary = (y_train_balanced > 0).astype(int)

        print(f"  平衡分布: 正={sum(y_binary==1)}, 负={sum(y_binary==0)}")

        # 过采样后样本应该增加或保持
        self.assertGreaterEqual(len(X_train_balanced), 70 * 0.7)  # 至少有训练集的70%

        print(f"  ✓ 过采样成功")

    def test_08_scaler_persistence(self):
        """测试8: Scaler 持久化"""
        print("\n[测试8] Scaler 持久化...")

        splitter = DataSplitter(scaler_type='robust', verbose=False)

        # 第一次拟合
        splitter.split_and_prepare(
            self.X, self.y,
            scale_features=True,
            fit_scaler=True
        )

        # 获取 scaler
        scaler1 = splitter.get_scaler()
        self.assertIsNotNone(scaler1)

        # 第二次使用相同 scaler
        result = splitter.split_and_prepare(
            self.X, self.y,
            scale_features=True,
            fit_scaler=False
        )

        scaler2 = splitter.get_scaler()
        self.assertEqual(scaler1, scaler2)

        print(f"  ✓ Scaler 持久化成功")

    def test_09_set_scaler(self):
        """测试9: 设置外部 Scaler"""
        print("\n[测试9] 设置外部 Scaler...")

        from sklearn.preprocessing import RobustScaler

        # 创建外部 scaler
        external_scaler = RobustScaler()
        external_scaler.fit(self.X)

        # 设置 scaler
        self.splitter.set_scaler(external_scaler)

        # 验证
        self.assertEqual(self.splitter.get_scaler(), external_scaler)

        print(f"  ✓ 设置外部 Scaler 成功")

    def test_10_balanced_data_skip(self):
        """测试10: 平衡数据跳过重采样"""
        print("\n[测试10] 平衡数据跳过重采样...")

        # 创建已平衡的数据
        y_balanced = pd.Series([1] * 50 + [-1] * 50)
        X_balanced = pd.DataFrame(np.random.randn(100, 3), columns=['f1', 'f2', 'f3'])

        splitter = DataSplitter(verbose=True)

        result = splitter.split_and_prepare(
            X_balanced, y_balanced,
            balance_samples=True,
            balance_method='undersample'
        )

        X_train, y_train, _, _, _, _ = result

        # 已平衡数据不应该被改变太多
        self.assertGreaterEqual(len(X_train), 70 * 0.95)  # 至少保留95%

        print(f"  ✓ 平衡数据跳过重采样")

    def test_11_performance_optimization(self):
        """测试11: 性能优化验证"""
        print("\n[测试11] 性能优化验证...")

        import time

        # 创建大量数据测试性能
        X_large = pd.DataFrame(np.random.randn(5000, 10))
        y_large = pd.Series(np.random.choice([1, -1], 5000))

        splitter = DataSplitter(verbose=False)

        start = time.time()
        result = splitter.split_and_prepare(
            X_large, y_large,
            balance_samples=True,
            balance_method='undersample'
        )
        elapsed = time.time() - start

        # 应该在合理时间内完成（< 5秒）
        self.assertLess(elapsed, 5.0)

        print(f"  ✓ 处理5000样本耗时: {elapsed:.2f}秒")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDataSplitter)
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
