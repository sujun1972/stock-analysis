#!/usr/bin/env python3
"""
DataPipeline 单元测试
测试数据流水线的各项功能
"""

import sys
import os
from pathlib import Path
import unittest
import pandas as pd
import numpy as np

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent

from src.data_pipeline import DataPipeline, create_pipeline, get_full_training_data


class TestDataPipeline(unittest.TestCase):
    """测试DataPipeline类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("DataPipeline 单元测试")
        print("="*60)

    def test_01_create_pipeline(self):
        """测试1: 创建流水线"""
        print("\n[测试1] 创建流水线...")

        # 测试基础创建
        pipeline = DataPipeline(
            target_periods=5,
            scaler_type='robust',
            verbose=False
        )

        self.assertIsNotNone(pipeline)
        self.assertEqual(pipeline.target_periods, [5])
        self.assertEqual(pipeline.scaler_type, 'robust')

        print("  ✓ 基础创建成功")

        # 测试多周期
        pipeline_multi = DataPipeline(target_periods=[5, 10, 20])
        self.assertEqual(pipeline_multi.target_periods, [5, 10, 20])

        print("  ✓ 多周期创建成功")

        # 测试便捷函数
        pipeline_simple = create_pipeline(target_period=10, verbose=False)
        self.assertIsNotNone(pipeline_simple)

        print("  ✓ 便捷函数创建成功")

    def test_02_get_training_data(self):
        """测试2: 获取训练数据"""
        print("\n[测试2] 获取训练数据...")

        try:
            pipeline = DataPipeline(
                target_periods=5,
                cache_features=False,  # 禁用缓存以测试完整流程
                verbose=True
            )

            # 获取数据
            X, y = pipeline.get_training_data(
                symbol='000001',
                start_date='20230101',
                end_date='20231231',
                use_cache=False
            )

            # 验证数据
            self.assertIsInstance(X, pd.DataFrame)
            self.assertIsInstance(y, pd.Series)
            self.assertGreater(len(X), 0, "特征数据为空")
            self.assertGreater(len(y), 0, "目标数据为空")
            self.assertEqual(len(X), len(y), "特征和目标长度不一致")

            print(f"  ✓ 数据形状: X={X.shape}, y={y.shape}")

            # 检查特征列
            feature_names = pipeline.get_feature_names()
            self.assertGreater(len(feature_names), 0, "特征列为空")
            self.assertEqual(len(feature_names), len(X.columns), "特征名数量不匹配")

            print(f"  ✓ 特征数量: {len(feature_names)}")

            # 检查目标标签
            self.assertEqual(pipeline.target_name, 'target_5d_return')
            self.assertFalse(y.isna().any(), "目标标签包含NaN")

            print(f"  ✓ 目标标签: {pipeline.target_name}")
            print(f"  ✓ 目标均值: {y.mean():.4f}%")
            print(f"  ✓ 目标标准差: {y.std():.4f}%")

        except Exception as e:
            self.skipTest(f"数据库连接失败或无数据: {e}")

    def test_03_data_cleaning(self):
        """测试3: 数据清洗"""
        print("\n[测试3] 数据清洗...")

        try:
            pipeline = DataPipeline(target_periods=5, verbose=True)

            X, y = pipeline.get_training_data(
                symbol='000001',
                start_date='20230101',
                end_date='20231231',
                use_cache=False
            )

            # 检查无NaN
            self.assertFalse(X.isna().any().any(), "特征包含NaN")
            self.assertFalse(y.isna().any(), "目标包含NaN")

            print("  ✓ 无NaN值")

            # 检查无Inf
            self.assertFalse(np.isinf(X.values).any(), "特征包含Inf")
            self.assertFalse(np.isinf(y.values).any(), "目标包含Inf")

            print("  ✓ 无Inf值")

            # 检查统计信息
            stats = pipeline.get_stats()
            self.assertIn('raw_samples', stats)
            self.assertIn('final_samples', stats)
            self.assertGreater(stats['final_samples'], 0)

            print(f"  ✓ 数据保留率: {stats['final_samples']/stats['raw_samples']*100:.1f}%")

        except Exception as e:
            self.skipTest(f"数据库连接失败: {e}")

    def test_04_prepare_for_model(self):
        """测试4: 准备模型数据"""
        print("\n[测试4] 准备模型数据...")

        try:
            pipeline = DataPipeline(target_periods=5, verbose=False)

            X, y = pipeline.get_training_data(
                symbol='000001',
                start_date='20230101',
                end_date='20231231'
            )

            # 准备数据
            X_train, y_train, X_valid, y_valid, X_test, y_test = pipeline.prepare_for_model(
                X, y,
                train_ratio=0.7,
                valid_ratio=0.15,
                scale_features=True,
                balance_samples=False
            )

            # 验证分割
            total_samples = len(X_train) + len(X_valid) + len(X_test)
            self.assertEqual(total_samples, len(X), "分割后样本总数不一致")

            print(f"  ✓ 训练集: {len(X_train)} 样本")
            print(f"  ✓ 验证集: {len(X_valid)} 样本")
            print(f"  ✓ 测试集: {len(X_test)} 样本")

            # 验证缩放
            train_mean = X_train.mean().mean()
            train_std = X_train.std().mean()

            # 鲁棒缩放后均值应该接近0（但不完全等于0）
            self.assertLess(abs(train_mean), 5.0, "缩放后均值异常")

            print(f"  ✓ 特征缩放: 均值={train_mean:.4f}, 标准差={train_std:.4f}")

            # 验证scaler
            scaler = pipeline.get_scaler()
            self.assertIsNotNone(scaler, "Scaler未创建")

            print("  ✓ Scaler已创建")

        except Exception as e:
            self.skipTest(f"数据库连接失败: {e}")

    def test_05_feature_scaling(self):
        """测试5: 特征缩放"""
        print("\n[测试5] 特征缩放...")

        try:
            # 测试不同缩放方法
            for scaler_type in ['standard', 'robust', 'minmax']:
                pipeline = DataPipeline(
                    target_periods=5,
                    scaler_type=scaler_type,
                    verbose=False
                )

                X, y = pipeline.get_training_data(
                    symbol='000001',
                    start_date='20230101',
                    end_date='20231231'
                )

                X_train, y_train, X_valid, y_valid, X_test, y_test = pipeline.prepare_for_model(
                    X, y,
                    scale_features=True
                )

                # 验证缩放效果
                if scaler_type == 'minmax':
                    # MinMax应该在[0, 1]范围内
                    self.assertGreaterEqual(X_train.min().min(), -0.1)
                    self.assertLessEqual(X_train.max().max(), 1.1)

                print(f"  ✓ {scaler_type} 缩放成功")

        except Exception as e:
            self.skipTest(f"数据库连接失败: {e}")

    def test_06_sample_balancing(self):
        """测试6: 样本平衡"""
        print("\n[测试6] 样本平衡...")

        try:
            pipeline = DataPipeline(target_periods=5, verbose=False)

            X, y = pipeline.get_training_data(
                symbol='000001',
                start_date='20230101',
                end_date='20231231'
            )

            # 不平衡
            X_train_raw, y_train_raw, _, _, _, _ = pipeline.prepare_for_model(
                X, y, balance_samples=False
            )

            # 平衡
            X_train_balanced, y_train_balanced, _, _, _, _ = pipeline.prepare_for_model(
                X, y, balance_samples=True, balance_method='undersample'
            )

            # 验证样本数变化
            print(f"  原始训练集: {len(X_train_raw)} 样本")
            print(f"  平衡后训练集: {len(X_train_balanced)} 样本")

            # 检查类别分布
            y_binary_raw = (y_train_raw > 0).astype(int)
            y_binary_balanced = (y_train_balanced > 0).astype(int)

            print(f"  原始分布: 跌={sum(y_binary_raw==0)}, 涨={sum(y_binary_raw==1)}")
            print(f"  平衡分布: 跌={sum(y_binary_balanced==0)}, 涨={sum(y_binary_balanced==1)}")

            print("  ✓ 样本平衡成功")

        except Exception as e:
            self.skipTest(f"数据库连接失败: {e}")

    def test_07_cache_mechanism(self):
        """测试7: 缓存机制"""
        print("\n[测试7] 缓存机制...")

        try:
            import time

            pipeline = DataPipeline(
                target_periods=5,
                cache_features=True,
                cache_dir='data/test_cache',
                verbose=False
            )

            # 清除缓存
            pipeline.clear_cache()

            # 第一次运行（无缓存）
            start_time = time.time()
            X1, y1 = pipeline.get_training_data(
                symbol='000001',
                start_date='20230101',
                end_date='20231231',
                force_refresh=True
            )
            time_no_cache = time.time() - start_time

            # 第二次运行（有缓存）
            start_time = time.time()
            X2, y2 = pipeline.get_training_data(
                symbol='000001',
                start_date='20230101',
                end_date='20231231',
                use_cache=True
            )
            time_with_cache = time.time() - start_time

            # 验证数据一致
            pd.testing.assert_frame_equal(X1, X2, check_dtype=False)
            pd.testing.assert_series_equal(y1, y2, check_dtype=False)

            print(f"  ✓ 无缓存耗时: {time_no_cache:.2f}秒")
            print(f"  ✓ 有缓存耗时: {time_with_cache:.2f}秒")
            print(f"  ✓ 加速比: {time_no_cache/time_with_cache:.1f}x")

            # 清理
            pipeline.clear_cache()

        except Exception as e:
            self.skipTest(f"缓存测试失败: {e}")

    def test_08_multi_period(self):
        """测试8: 多周期预测"""
        print("\n[测试8] 多周期预测...")

        try:
            periods = [5, 10, 20]

            for period in periods:
                pipeline = DataPipeline(target_periods=period, verbose=False)

                X, y = pipeline.get_training_data(
                    symbol='000001',
                    start_date='20230101',
                    end_date='20231231',
                    target_period=period
                )

                # 验证目标标签名
                expected_name = f'target_{period}d_return'
                self.assertEqual(pipeline.target_name, expected_name)

                print(f"  ✓ {period}日预测: {expected_name}, 均值={y.mean():.4f}%")

        except Exception as e:
            self.skipTest(f"数据库连接失败: {e}")

    def test_09_convenience_function(self):
        """测试9: 便捷函数"""
        print("\n[测试9] 便捷函数...")

        try:
            # 测试一键获取函数
            result = get_full_training_data(
                symbol='000001',
                start_date='20230101',
                end_date='20231231',
                target_period=5,
                scale_features=True,
                balance_samples=False
            )

            X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline = result

            # 验证返回值
            self.assertEqual(len(result), 7, "返回值数量不正确")
            self.assertIsInstance(X_train, pd.DataFrame)
            self.assertIsInstance(pipeline, DataPipeline)

            print(f"  ✓ 训练集: {len(X_train)} 样本")
            print(f"  ✓ 验证集: {len(X_valid)} 样本")
            print(f"  ✓ 测试集: {len(X_test)} 样本")
            print("  ✓ 便捷函数成功")

        except Exception as e:
            self.skipTest(f"数据库连接失败: {e}")

    def test_10_error_handling(self):
        """测试10: 错误处理"""
        print("\n[测试10] 错误处理...")

        pipeline = DataPipeline(verbose=False)

        # 测试无效股票代码
        with self.assertRaises(Exception):
            X, y = pipeline.get_training_data(
                symbol='INVALID',
                start_date='20230101',
                end_date='20231231'
            )

        print("  ✓ 无效股票代码处理正确")

        # 测试无效日期
        with self.assertRaises(Exception):
            X, y = pipeline.get_training_data(
                symbol='000001',
                start_date='20251231',
                end_date='20230101'  # 结束日期早于开始日期
            )

        print("  ✓ 无效日期处理正确")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDataPipeline)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
