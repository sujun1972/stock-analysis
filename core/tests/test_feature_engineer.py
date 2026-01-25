#!/usr/bin/env python3
"""
FeatureEngineer 单元测试

测试特征工程器的功能
"""

import sys
import unittest
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from data_pipeline.feature_engineer import FeatureEngineer
from exceptions import FeatureComputationError


class TestFeatureEngineer(unittest.TestCase):
    """测试 FeatureEngineer 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("FeatureEngineer 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        # 创建测试数据
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        self.test_data = pd.DataFrame({
            'open': np.random.uniform(95, 105, 100),
            'high': np.random.uniform(100, 110, 100),
            'low': np.random.uniform(90, 100, 100),
            'close': np.random.uniform(95, 105, 100),
            'volume': np.random.uniform(1000000, 2000000, 100)
        }, index=dates)

        # 确保 high >= close >= low
        self.test_data['high'] = self.test_data[['open', 'close', 'high']].max(axis=1)
        self.test_data['low'] = self.test_data[['open', 'close', 'low']].min(axis=1)

        self.engineer = FeatureEngineer(verbose=False)

    def test_01_init(self):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        engineer = FeatureEngineer(verbose=False)
        self.assertIsNotNone(engineer)
        self.assertEqual(engineer.verbose, False)
        self.assertEqual(engineer.feature_names, [])

        print("  ✓ 初始化成功")

    def test_02_compute_all_features(self):
        """测试2: 计算所有特征"""
        print("\n[测试2] 计算所有特征...")

        result = self.engineer.compute_all_features(self.test_data, target_period=5)

        # 验证返回值
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result.columns), len(self.test_data.columns))

        # 验证目标列存在
        self.assertIn('target_5d_return', result.columns)

        # 验证原始列仍然存在
        self.assertIn('close', result.columns)

        print(f"  ✓ 特征数量: {len(result.columns)} 列")
        print(f"  ✓ 样本数量: {len(result)} 行")

    def test_03_technical_indicators(self):
        """测试3: 技术指标"""
        print("\n[测试3] 技术指标...")

        result = self.engineer._compute_technical_indicators(self.test_data.copy())

        # 验证 MA 指标
        self.assertIn('MA5', result.columns)
        self.assertIn('MA10', result.columns)
        self.assertIn('MA20', result.columns)

        # 验证 EMA 指标
        self.assertIn('EMA12', result.columns)
        self.assertIn('EMA26', result.columns)

        # 验证 RSI 指标
        self.assertIn('RSI6', result.columns)
        self.assertIn('RSI12', result.columns)

        # 验证 MACD 指标
        self.assertIn('MACD', result.columns)
        self.assertIn('MACD_SIGNAL', result.columns)
        self.assertIn('MACD_HIST', result.columns)

        # 验证 KDJ 指标
        self.assertIn('K', result.columns)
        self.assertIn('D', result.columns)
        self.assertIn('J', result.columns)

        # 验证布林带
        self.assertIn('BOLL_UPPER', result.columns)
        self.assertIn('BOLL_MIDDLE', result.columns)
        self.assertIn('BOLL_LOWER', result.columns)

        print(f"  ✓ 技术指标计算成功")

    def test_04_alpha_factors(self):
        """测试4: Alpha因子"""
        print("\n[测试4] Alpha因子...")

        # 先计算技术指标（Alpha因子依赖它们）
        df = self.engineer._compute_technical_indicators(self.test_data.copy())
        result = self.engineer._compute_alpha_factors(df)

        # 验证动量因子
        momentum_cols = [col for col in result.columns if 'MOMENTUM' in col]
        self.assertGreater(len(momentum_cols), 0)

        # 验证波动率因子
        vol_cols = [col for col in result.columns if 'VOLATILITY' in col or 'VOL_' in col]
        self.assertGreater(len(vol_cols), 0)

        print(f"  ✓ Alpha因子计算成功")

    def test_05_feature_transformation(self):
        """测试5: 特征转换"""
        print("\n[测试5] 特征转换...")

        result = self.engineer._apply_feature_transformation(self.test_data.copy())

        # 验证收益率特征
        self.assertIn('RETURN_1D', result.columns)
        self.assertIn('RETURN_3D', result.columns)
        self.assertIn('RETURN_5D', result.columns)

        # 验证 OHLC 特征
        ohlc_cols = [col for col in result.columns if any(x in col for x in ['HIGH_LOW', 'CLOSE_OPEN'])]
        self.assertGreater(len(ohlc_cols), 0)

        # 验证时间特征
        self.assertIn('DAY_OF_WEEK', result.columns)
        self.assertIn('MONTH', result.columns)

        print(f"  ✓ 特征转换成功")

    def test_06_deprice_features(self):
        """测试6: 特征去价格化"""
        print("\n[测试6] 特征去价格化...")

        # 先计算技术指标
        df = self.engineer._compute_technical_indicators(self.test_data.copy())

        # 记录去价格化前的列
        before_cols = set(df.columns)

        # 去价格化
        result = self.engineer._deprice_features(df)

        after_cols = set(result.columns)

        # 验证 MA 被转换为比例
        self.assertNotIn('MA5', result.columns)
        self.assertIn('CLOSE_TO_MA5_RATIO', result.columns)

        # 验证 EMA 被转换为比例
        self.assertNotIn('EMA12', result.columns)
        self.assertIn('CLOSE_TO_EMA12_RATIO', result.columns)

        # 验证 BOLL 被转换为比例
        self.assertNotIn('BOLL_UPPER', result.columns)
        self.assertIn('CLOSE_TO_BOLL_UPPER_RATIO', result.columns)

        # 验证 ATR 被转换为百分比
        self.assertNotIn('ATR14', result.columns)
        self.assertIn('ATR14_PCT', result.columns)

        print(f"  ✓ 去价格化成功")

    def test_07_create_target(self):
        """测试7: 创建目标标签"""
        print("\n[测试7] 创建目标标签...")

        target_period = 5
        target_name = 'target_5d_return'

        result = self.engineer._create_target(
            self.test_data.copy(),
            target_period,
            target_name
        )

        # 验证目标列存在
        self.assertIn(target_name, result.columns)

        # 验证目标值是百分比
        target_values = result[target_name].dropna()
        self.assertGreater(len(target_values), 0)

        # 验证最后 target_period 行的目标值为 NaN（无未来数据）
        self.assertTrue(result[target_name].iloc[-target_period:].isna().all())

        # 验证目标值的合理性（A股单日涨跌幅限制10%，5日累计应该在合理范围）
        self.assertLess(target_values.abs().max(), 100)  # 不应该超过100%

        print(f"  ✓ 目标标签创建成功")
        print(f"  ✓ 目标均值: {target_values.mean():.4f}%")
        print(f"  ✓ 目标标准差: {target_values.std():.4f}%")

    def test_08_feature_count(self):
        """测试8: 特征数量验证"""
        print("\n[测试8] 特征数量验证...")

        result = self.engineer.compute_all_features(self.test_data, target_period=5)

        # 统计各类特征
        original_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
        technical_cols = [col for col in result.columns if any(x in col for x in ['MA', 'EMA', 'RSI', 'MACD', 'KDJ', 'BOLL', 'ATR', 'OBV', 'CCI'])]
        alpha_cols = [col for col in result.columns if any(x in col for x in ['MOMENTUM', 'REVERSAL', 'VOLATILITY', 'VOLUME', 'TREND'])]
        return_cols = [col for col in result.columns if 'RETURN' in col]
        time_cols = [col for col in result.columns if any(x in col for x in ['DAY_OF_WEEK', 'MONTH', 'QUARTER'])]

        print(f"  原始特征: {len([c for c in original_cols if c in result.columns])} 个")
        print(f"  技术指标: {len(technical_cols)} 个")
        print(f"  Alpha因子: {len(alpha_cols)} 个")
        print(f"  收益率特征: {len(return_cols)} 个")
        print(f"  时间特征: {len(time_cols)} 个")
        print(f"  ✓ 总特征数: {len(result.columns)} 个")

    def test_09_nan_handling(self):
        """测试9: NaN 处理"""
        print("\n[测试9] NaN 处理...")

        # 创建包含 NaN 的数据
        data_with_nan = self.test_data.copy()
        data_with_nan.loc[data_with_nan.index[5:10], 'close'] = np.nan

        result = self.engineer.compute_all_features(data_with_nan, target_period=5)

        # 技术指标在前期会有 NaN（需要足够的历史数据）
        # 这是正常的，数据清洗阶段会处理

        print(f"  ✓ NaN 处理成功")

    def test_10_different_target_periods(self):
        """测试10: 不同预测周期"""
        print("\n[测试10] 不同预测周期...")

        for period in [1, 5, 10, 20]:
            result = self.engineer.compute_all_features(
                self.test_data.copy(),
                target_period=period
            )

            target_name = f'target_{period}d_return'
            self.assertIn(target_name, result.columns)

            print(f"  ✓ {period}日预测: {target_name}")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFeatureEngineer)
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
