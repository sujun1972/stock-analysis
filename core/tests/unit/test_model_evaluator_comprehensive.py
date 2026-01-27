"""
模型评估器综合测试套件
涵盖所有功能、边界情况、性能测试和集成测试

测试覆盖范围：
1. 基础指标计算（IC, Rank IC, IC IR）
2. 分组收益和多空收益
3. 风险指标（Sharpe, 最大回撤, 胜率）
4. 异常处理和边界情况
5. 配置管理
6. 结果格式化
7. 时间序列评估
8. 性能和压力测试
9. 数据验证和过滤
10. 向后兼容性测试
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import time
from unittest.mock import patch, MagicMock
import warnings

# 添加src目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'core' / 'src'))

from src.models.model_evaluator import (
    ModelEvaluator,
    MetricsCalculator,
    ResultFormatter,
    EvaluationConfig,
    evaluate_model,
    EvaluationError,
    InvalidInputError,
    InsufficientDataError,
    filter_valid_pairs
)


# ==================== 测试数据生成工具 ====================

class TestDataGenerator:
    """测试数据生成器"""

    @staticmethod
    def generate_correlated_data(n_samples=1000, correlation=0.8, noise_level=0.5, seed=42):
        """
        生成相关数据

        Args:
            n_samples: 样本数量
            correlation: 相关系数（0-1）
            noise_level: 噪声水平
            seed: 随机种子

        Returns:
            (predictions, actual_returns)
        """
        np.random.seed(seed)
        true_signal = np.random.randn(n_samples)
        predictions = true_signal + np.random.randn(n_samples) * noise_level
        actual_returns = true_signal * correlation * 0.02 + np.random.randn(n_samples) * 0.01
        return predictions, actual_returns

    @staticmethod
    def generate_uncorrelated_data(n_samples=1000, seed=42):
        """生成无相关数据"""
        np.random.seed(seed)
        predictions = np.random.randn(n_samples)
        actual_returns = np.random.randn(n_samples) * 0.01
        return predictions, actual_returns

    @staticmethod
    def generate_perfect_data(n_samples=1000, seed=42):
        """生成完全相关数据"""
        np.random.seed(seed)
        true_signal = np.random.randn(n_samples)
        predictions = true_signal
        actual_returns = true_signal * 0.02
        return predictions, actual_returns

    @staticmethod
    def generate_data_with_outliers(n_samples=1000, outlier_ratio=0.05, seed=42):
        """生成含异常值的数据"""
        np.random.seed(seed)
        predictions, actual_returns = TestDataGenerator.generate_correlated_data(n_samples, seed=seed)

        # 添加异常值
        n_outliers = int(n_samples * outlier_ratio)
        outlier_indices = np.random.choice(n_samples, n_outliers, replace=False)
        predictions[outlier_indices] = np.random.randn(n_outliers) * 10

        return predictions, actual_returns

    @staticmethod
    def generate_sparse_data(n_samples=1000, nan_ratio=0.3, seed=42):
        """生成含 NaN 的稀疏数据"""
        np.random.seed(seed)
        predictions, actual_returns = TestDataGenerator.generate_correlated_data(n_samples, seed=seed)

        # 添加 NaN
        n_nans = int(n_samples * nan_ratio)
        nan_indices_pred = np.random.choice(n_samples, n_nans, replace=False)
        nan_indices_ret = np.random.choice(n_samples, n_nans, replace=False)

        predictions[nan_indices_pred] = np.nan
        actual_returns[nan_indices_ret] = np.nan

        return predictions, actual_returns


# ==================== 基础指标测试 ====================

class TestICMetrics(unittest.TestCase):
    """IC 指标详细测试"""

    def test_01_ic_with_perfect_correlation(self):
        """测试完全相关的 IC"""
        predictions, actual_returns = TestDataGenerator.generate_perfect_data()
        ic = MetricsCalculator.calculate_ic(predictions, actual_returns, method='pearson')

        # 完全相关应该接近 1.0
        self.assertGreater(ic, 0.99)

    def test_02_ic_with_no_correlation(self):
        """测试无相关的 IC"""
        predictions, actual_returns = TestDataGenerator.generate_uncorrelated_data()
        ic = MetricsCalculator.calculate_ic(predictions, actual_returns, method='pearson')

        # 无相关应该接近 0
        self.assertLess(abs(ic), 0.2)

    def test_03_ic_with_negative_correlation(self):
        """测试负相关的 IC"""
        np.random.seed(42)
        predictions = np.random.randn(1000)
        actual_returns = -predictions * 0.02 + np.random.randn(1000) * 0.01

        ic = MetricsCalculator.calculate_ic(predictions, actual_returns, method='pearson')

        # 负相关应该为负值
        self.assertLess(ic, -0.5)

    def test_04_ic_with_outliers(self):
        """测试含异常值的 IC（Spearman 更稳健）"""
        predictions, actual_returns = TestDataGenerator.generate_data_with_outliers()

        pearson_ic = MetricsCalculator.calculate_ic(predictions, actual_returns, method='pearson')
        spearman_ic = MetricsCalculator.calculate_ic(predictions, actual_returns, method='spearman')

        # Spearman 应该对异常值更稳健
        self.assertIsInstance(pearson_ic, float)
        self.assertIsInstance(spearman_ic, float)

    def test_05_ic_invalid_method(self):
        """测试无效的 IC 方法"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()

        # 应该返回 NaN（通过 safe_compute 装饰器处理）
        result = MetricsCalculator.calculate_ic(predictions, actual_returns, method='invalid')
        self.assertTrue(np.isnan(result))

    def test_06_ic_ir_stability(self):
        """测试 IC IR 的稳定性"""
        # 创建稳定的 IC 序列
        stable_ic = pd.Series([0.05, 0.06, 0.05, 0.06, 0.05])
        stable_ir = MetricsCalculator.calculate_ic_ir(stable_ic)

        # 创建波动的 IC 序列
        volatile_ic = pd.Series([0.10, -0.05, 0.15, -0.10, 0.20])
        volatile_ir = MetricsCalculator.calculate_ic_ir(volatile_ic)

        # 稳定序列的 IR 应该更高
        self.assertGreater(stable_ir, volatile_ir)

    def test_07_ic_ir_with_single_value(self):
        """测试单个值的 IC IR"""
        single_ic = pd.Series([0.05])
        ic_ir = MetricsCalculator.calculate_ic_ir(single_ic)

        # 单个值无法计算标准差，应返回 NaN
        self.assertTrue(np.isnan(ic_ir))

    def test_08_ic_ir_with_all_negative(self):
        """测试全负 IC 的 IC IR"""
        negative_ic = pd.Series([-0.05, -0.03, -0.08, -0.02, -0.06])
        ic_ir = MetricsCalculator.calculate_ic_ir(negative_ic)

        # 全负 IC 的 IR 应为负值
        self.assertLess(ic_ir, 0)


# ==================== 分组收益测试 ====================

class TestGroupReturns(unittest.TestCase):
    """分组收益详细测试"""

    def test_01_group_returns_with_perfect_prediction(self):
        """测试完美预测的分组收益"""
        predictions, actual_returns = TestDataGenerator.generate_perfect_data()
        group_returns = MetricsCalculator.calculate_group_returns(predictions, actual_returns, n_groups=5)

        # 完美预测应该严格单调递增
        returns_list = [group_returns[i] for i in range(5)]
        for i in range(4):
            self.assertLess(returns_list[i], returns_list[i+1])

    def test_02_group_returns_with_different_group_numbers(self):
        """测试不同分组数量"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()

        for n_groups in [3, 5, 10, 20]:
            group_returns = MetricsCalculator.calculate_group_returns(
                predictions, actual_returns, n_groups=n_groups
            )
            # 验证分组数量（可能因为重复值而少于预期）
            self.assertGreater(len(group_returns), 0)
            self.assertLessEqual(len(group_returns), n_groups)

    def test_03_group_returns_with_duplicate_predictions(self):
        """测试预测值有大量重复的情况"""
        # 创建大量重复值
        predictions = np.array([1.0] * 500 + [2.0] * 500)
        actual_returns = np.random.randn(1000) * 0.01

        group_returns = MetricsCalculator.calculate_group_returns(
            predictions, actual_returns, n_groups=5
        )

        # 应该能处理重复值（使用 duplicates='drop'）
        self.assertIsInstance(group_returns, dict)
        self.assertGreater(len(group_returns), 0)

    def test_04_group_returns_symmetry(self):
        """测试分组收益的对称性"""
        np.random.seed(42)
        # 创建对称分布的数据
        n = 500
        predictions = np.concatenate([np.random.randn(n), -np.random.randn(n)])
        actual_returns = predictions * 0.02

        group_returns = MetricsCalculator.calculate_group_returns(
            predictions, actual_returns, n_groups=5
        )

        # 最高组和最低组的绝对值应该接近
        if len(group_returns) >= 5:
            self.assertAlmostEqual(
                abs(group_returns[0]),
                abs(group_returns[4]),
                places=2
            )


# ==================== 多空收益测试 ====================

class TestLongShortReturns(unittest.TestCase):
    """多空收益详细测试"""

    def test_01_long_short_with_perfect_prediction(self):
        """测试完美预测的多空收益"""
        predictions, actual_returns = TestDataGenerator.generate_perfect_data(n_samples=1000)
        long_short = MetricsCalculator.calculate_long_short_return(
            predictions, actual_returns, top_pct=0.2, bottom_pct=0.2
        )

        # 完美预测应该有很高的多空收益
        self.assertGreater(long_short['long_short'], 0.03)
        self.assertGreater(long_short['long'], long_short['short'])

    def test_02_long_short_different_percentiles(self):
        """测试不同百分位的影响"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()

        # 比较不同的百分位
        ls_10 = MetricsCalculator.calculate_long_short_return(
            predictions, actual_returns, top_pct=0.1, bottom_pct=0.1
        )
        ls_20 = MetricsCalculator.calculate_long_short_return(
            predictions, actual_returns, top_pct=0.2, bottom_pct=0.2
        )
        ls_30 = MetricsCalculator.calculate_long_short_return(
            predictions, actual_returns, top_pct=0.3, bottom_pct=0.3
        )

        # 更激进的策略（10%）通常有更高的多空收益
        self.assertGreater(ls_10['long_short'], 0)

    def test_03_long_short_asymmetric_percentiles(self):
        """测试不对称的多空比例"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()

        # 多多空少
        ls_asym = MetricsCalculator.calculate_long_short_return(
            predictions, actual_returns, top_pct=0.3, bottom_pct=0.1
        )

        self.assertIn('long', ls_asym)
        self.assertIn('short', ls_asym)
        self.assertIn('long_short', ls_asym)

    def test_04_long_short_calculation_correctness(self):
        """验证多空收益计算的正确性"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()
        long_short = MetricsCalculator.calculate_long_short_return(
            predictions, actual_returns, top_pct=0.2, bottom_pct=0.2
        )

        # 验证计算关系
        calculated_spread = long_short['long'] - long_short['short']
        self.assertAlmostEqual(
            long_short['long_short'],
            calculated_spread,
            places=10
        )

    def test_05_long_short_with_small_sample(self):
        """测试小样本的多空收益"""
        predictions = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        actual_returns = np.array([0.01, 0.02, 0.03, 0.04, 0.05])

        long_short = MetricsCalculator.calculate_long_short_return(
            predictions, actual_returns, top_pct=0.2, bottom_pct=0.2
        )

        # 应该至少选择 1 只股票
        self.assertIsInstance(long_short['long'], float)
        self.assertIsInstance(long_short['short'], float)


# ==================== 风险指标测试 ====================

class TestRiskMetrics(unittest.TestCase):
    """风险指标详细测试"""

    def test_01_sharpe_with_positive_returns(self):
        """测试正收益的 Sharpe 比率"""
        # 创建正期望收益
        returns = np.random.randn(252) * 0.01 + 0.002  # 日均 0.2%
        sharpe = MetricsCalculator.calculate_sharpe_ratio(returns, risk_free_rate=0.03)

        # 正收益应该有正的 Sharpe
        self.assertGreater(sharpe, 0)

    def test_02_sharpe_with_negative_returns(self):
        """测试负收益的 Sharpe 比率"""
        returns = np.random.randn(252) * 0.01 - 0.002  # 日均 -0.2%
        sharpe = MetricsCalculator.calculate_sharpe_ratio(returns, risk_free_rate=0.03)

        # 负收益应该有负的 Sharpe
        self.assertLess(sharpe, 0)

    def test_03_sharpe_with_different_periods(self):
        """测试不同周期的 Sharpe"""
        returns = np.random.randn(252) * 0.01 + 0.001

        sharpe_daily = MetricsCalculator.calculate_sharpe_ratio(
            returns, periods_per_year=252
        )
        sharpe_weekly = MetricsCalculator.calculate_sharpe_ratio(
            returns, periods_per_year=52
        )

        # 不同年化方式应该有不同的结果
        self.assertNotEqual(sharpe_daily, sharpe_weekly)

    def test_04_max_drawdown_with_continuous_growth(self):
        """测试持续上涨的最大回撤"""
        returns = np.array([0.01] * 100)  # 持续上涨
        max_dd = MetricsCalculator.calculate_max_drawdown(returns)

        # 持续上涨应该没有回撤（接近0）
        self.assertLess(max_dd, 0.01)

    def test_05_max_drawdown_with_steep_drop(self):
        """测试陡峭下跌的最大回撤"""
        returns = np.array([0.05] * 10 + [-0.10] * 5 + [0.02] * 10)
        max_dd = MetricsCalculator.calculate_max_drawdown(returns)

        # 应该有明显的回撤
        self.assertGreater(max_dd, 0.3)

    def test_06_max_drawdown_calculation_accuracy(self):
        """验证最大回撤计算精度"""
        # 创建已知回撤的序列
        returns = np.array([0.10, 0.05, -0.20, -0.10, 0.05])
        max_dd = MetricsCalculator.calculate_max_drawdown(returns)

        # 手动计算预期回撤
        cum_returns = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cum_returns)
        drawdown = (cum_returns - running_max) / running_max
        expected_dd = -drawdown.min()

        self.assertAlmostEqual(max_dd, expected_dd, places=10)

    def test_07_win_rate_all_wins(self):
        """测试全胜的胜率"""
        returns = np.array([0.01, 0.02, 0.03, 0.04, 0.05])
        win_rate = MetricsCalculator.calculate_win_rate(returns)

        # 全胜应该是 1.0
        self.assertAlmostEqual(win_rate, 1.0, places=10)

    def test_08_win_rate_all_losses(self):
        """测试全亏的胜率"""
        returns = np.array([-0.01, -0.02, -0.03, -0.04, -0.05])
        win_rate = MetricsCalculator.calculate_win_rate(returns)

        # 全亏应该是 0.0
        self.assertAlmostEqual(win_rate, 0.0, places=10)

    def test_09_win_rate_with_custom_threshold(self):
        """测试自定义阈值的胜率"""
        returns = np.array([0.001, 0.002, 0.005, 0.01, 0.02])

        # 不同阈值应该有不同的胜率
        wr_0 = MetricsCalculator.calculate_win_rate(returns, threshold=0.0)
        wr_005 = MetricsCalculator.calculate_win_rate(returns, threshold=0.005)
        wr_01 = MetricsCalculator.calculate_win_rate(returns, threshold=0.01)

        # 阈值越高，胜率越低
        self.assertGreaterEqual(wr_0, wr_005)
        self.assertGreaterEqual(wr_005, wr_01)


# ==================== 异常处理和边界测试 ====================

class TestExceptionHandlingComprehensive(unittest.TestCase):
    """全面的异常处理测试"""

    def test_01_none_input_predictions(self):
        """测试预测值为 None"""
        evaluator = ModelEvaluator()
        with self.assertRaises(InvalidInputError):
            evaluator.evaluate_regression(None, np.array([1, 2, 3]))

    def test_02_none_input_returns(self):
        """测试收益率为 None"""
        evaluator = ModelEvaluator()
        with self.assertRaises(InvalidInputError):
            evaluator.evaluate_regression(np.array([1, 2, 3]), None)

    def test_03_empty_arrays(self):
        """测试空数组"""
        evaluator = ModelEvaluator()
        with self.assertRaises(InsufficientDataError):
            evaluator.evaluate_regression(np.array([]), np.array([]))

    def test_04_mismatched_lengths(self):
        """测试长度不匹配"""
        evaluator = ModelEvaluator()
        with self.assertRaises(InvalidInputError):
            evaluator.evaluate_regression(
                np.array([1, 2, 3, 4, 5]),
                np.array([1, 2, 3])
            )

    def test_05_all_nan_input(self):
        """测试全 NaN 输入"""
        predictions = np.array([np.nan] * 10)
        actual_returns = np.array([np.nan] * 10)

        with self.assertRaises(InsufficientDataError):
            filter_valid_pairs(predictions, actual_returns)

    def test_06_all_inf_input(self):
        """测试全 Inf 输入"""
        predictions = np.array([np.inf] * 10)
        actual_returns = np.array([np.inf] * 10)

        with self.assertRaises(InsufficientDataError):
            filter_valid_pairs(predictions, actual_returns)

    def test_07_mixed_nan_inf_input(self):
        """测试混合 NaN 和 Inf"""
        predictions = np.array([1.0, np.nan, np.inf, 4.0, 5.0])
        actual_returns = np.array([0.01, 0.02, np.nan, np.inf, 0.05])

        valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)

        # 只有第一个和最后一个元素是有效的（索引 0 和 4）
        self.assertEqual(len(valid_preds), 2)
        self.assertEqual(len(valid_returns), 2)
        np.testing.assert_array_equal(valid_preds, np.array([1.0, 5.0]))
        np.testing.assert_array_equal(valid_returns, np.array([0.01, 0.05]))

    def test_08_insufficient_data_after_filtering(self):
        """测试过滤后数据不足"""
        predictions = np.array([1.0, np.nan, np.nan, np.nan, np.nan])
        actual_returns = np.array([0.01, 0.02, 0.03, 0.04, 0.05])

        with self.assertRaises(InsufficientDataError):
            filter_valid_pairs(predictions, actual_returns, min_samples=2)

    def test_09_timeseries_empty_dict(self):
        """测试时间序列评估的空字典"""
        evaluator = ModelEvaluator()

        with self.assertRaises(InvalidInputError):
            evaluator.evaluate_timeseries({}, {})

    def test_10_timeseries_missing_dates(self):
        """测试时间序列评估缺少日期"""
        evaluator = ModelEvaluator()

        predictions_by_date = {'2024-01-01': np.array([1, 2, 3])}
        actuals_by_date = {'2024-01-02': np.array([0.01, 0.02, 0.03])}

        with self.assertRaises(InsufficientDataError):
            evaluator.evaluate_timeseries(predictions_by_date, actuals_by_date, verbose=False)


# ==================== 配置管理测试 ====================

class TestEvaluationConfigComprehensive(unittest.TestCase):
    """评估配置全面测试"""

    def test_01_default_config_values(self):
        """测试默认配置值"""
        config = EvaluationConfig()

        self.assertEqual(config.n_groups, 5)
        self.assertEqual(config.top_pct, 0.2)
        self.assertEqual(config.bottom_pct, 0.2)
        self.assertEqual(config.risk_free_rate, 0.0)
        self.assertEqual(config.periods_per_year, 252)
        self.assertEqual(config.min_samples, 2)

    def test_02_custom_config_all_parameters(self):
        """测试自定义所有配置参数"""
        config = EvaluationConfig(
            n_groups=10,
            top_pct=0.1,
            bottom_pct=0.15,
            risk_free_rate=0.03,
            periods_per_year=250,
            min_samples=5
        )

        self.assertEqual(config.n_groups, 10)
        self.assertEqual(config.top_pct, 0.1)
        self.assertEqual(config.bottom_pct, 0.15)
        self.assertEqual(config.risk_free_rate, 0.03)
        self.assertEqual(config.periods_per_year, 250)
        self.assertEqual(config.min_samples, 5)

    def test_03_config_in_evaluator(self):
        """测试评估器使用配置"""
        config = EvaluationConfig(n_groups=8, top_pct=0.15)
        evaluator = ModelEvaluator(config=config)

        self.assertEqual(evaluator.config.n_groups, 8)
        self.assertEqual(evaluator.config.top_pct, 0.15)

    def test_04_config_affects_group_returns(self):
        """测试配置影响分组收益"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()

        config_5 = EvaluationConfig(n_groups=5)
        config_10 = EvaluationConfig(n_groups=10)

        evaluator_5 = ModelEvaluator(config=config_5)
        evaluator_10 = ModelEvaluator(config=config_10)

        metrics_5 = evaluator_5.evaluate_regression(predictions, actual_returns, verbose=False)
        metrics_10 = evaluator_10.evaluate_regression(predictions, actual_returns, verbose=False)

        # 不同配置应该有不同数量的分组
        group_count_5 = sum(1 for k in metrics_5.keys() if k.startswith('group_'))
        group_count_10 = sum(1 for k in metrics_10.keys() if k.startswith('group_'))

        self.assertLess(group_count_5, group_count_10)

    def test_05_config_affects_long_short(self):
        """测试配置影响多空收益"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()

        config_20 = EvaluationConfig(top_pct=0.2, bottom_pct=0.2)
        config_10 = EvaluationConfig(top_pct=0.1, bottom_pct=0.1)

        evaluator_20 = ModelEvaluator(config=config_20)
        evaluator_10 = ModelEvaluator(config=config_10)

        metrics_20 = evaluator_20.evaluate_regression(predictions, actual_returns, verbose=False)
        metrics_10 = evaluator_10.evaluate_regression(predictions, actual_returns, verbose=False)

        # 不同配置应该有不同的多空收益
        # (通常更激进的策略有更高的收益)
        self.assertNotEqual(metrics_20['long_short_return'], metrics_10['long_short_return'])


# ==================== 结果格式化测试 ====================

class TestResultFormatterComprehensive(unittest.TestCase):
    """结果格式化器全面测试"""

    def test_01_print_empty_metrics(self):
        """测试打印空指标"""
        formatter = ResultFormatter()

        try:
            formatter.print_metrics({})
        except Exception as e:
            self.fail(f"打印空指标失败: {e}")

    def test_02_print_regression_metrics(self):
        """测试打印回归指标"""
        formatter = ResultFormatter()
        metrics = {
            'mse': 0.01,
            'rmse': 0.1,
            'mae': 0.08,
            'r2': 0.75
        }

        try:
            formatter.print_metrics(metrics)
        except Exception as e:
            self.fail(f"打印回归指标失败: {e}")

    def test_03_print_ic_metrics(self):
        """测试打印 IC 指标"""
        formatter = ResultFormatter()
        metrics = {
            'ic': 0.5,
            'rank_ic': 0.48,
            'ic_mean': 0.52,
            'ic_std': 0.1,
            'ic_ir': 5.2,
            'ic_positive_rate': 0.75
        }

        try:
            formatter.print_metrics(metrics)
        except Exception as e:
            self.fail(f"打印 IC 指标失败: {e}")

    def test_04_print_return_metrics(self):
        """测试打印收益指标"""
        formatter = ResultFormatter()
        metrics = {
            'long_return': 0.02,
            'short_return': -0.01,
            'long_short_return': 0.03
        }

        try:
            formatter.print_metrics(metrics)
        except Exception as e:
            self.fail(f"打印收益指标失败: {e}")

    def test_05_print_group_returns(self):
        """测试打印分组收益"""
        formatter = ResultFormatter()
        metrics = {
            'group_0_return': -0.01,
            'group_1_return': 0.0,
            'group_2_return': 0.005,
            'group_3_return': 0.01,
            'group_4_return': 0.02
        }

        try:
            formatter.print_metrics(metrics)
        except Exception as e:
            self.fail(f"打印分组收益失败: {e}")

    def test_06_print_all_metrics_combined(self):
        """测试打印所有指标组合"""
        formatter = ResultFormatter()
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()

        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_regression(predictions, actual_returns, verbose=False)

        try:
            formatter.print_metrics(metrics)
        except Exception as e:
            self.fail(f"打印完整指标失败: {e}")


# ==================== 时间序列评估测试 ====================

class TestTimeseriesEvaluation(unittest.TestCase):
    """时间序列评估详细测试"""

    def test_01_timeseries_basic(self):
        """测试基础时间序列评估"""
        predictions_by_date = {}
        actuals_by_date = {}

        for i in range(20):
            date = f"2024-01-{i+1:02d}"
            preds, rets = TestDataGenerator.generate_correlated_data(n_samples=100, seed=i)
            predictions_by_date[date] = preds
            actuals_by_date[date] = rets

        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_timeseries(
            predictions_by_date, actuals_by_date, verbose=False
        )

        # 验证所有时间序列指标都存在
        required_metrics = [
            'ic_mean', 'ic_std', 'ic_ir', 'ic_positive_rate',
            'rank_ic_mean', 'rank_ic_std', 'rank_ic_ir', 'rank_ic_positive_rate'
        ]
        for metric in required_metrics:
            self.assertIn(metric, metrics)
            self.assertFalse(np.isnan(metrics[metric]))

    def test_02_timeseries_with_varying_sample_sizes(self):
        """测试不同样本量的时间序列"""
        predictions_by_date = {}
        actuals_by_date = {}

        for i in range(10):
            date = f"2024-01-{i+1:02d}"
            n_samples = np.random.randint(50, 150)  # 不同的样本量
            preds, rets = TestDataGenerator.generate_correlated_data(n_samples=n_samples, seed=i)
            predictions_by_date[date] = preds
            actuals_by_date[date] = rets

        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_timeseries(
            predictions_by_date, actuals_by_date, verbose=False
        )

        self.assertGreater(metrics['ic_mean'], 0)

    def test_03_timeseries_with_missing_dates(self):
        """测试部分日期缺失"""
        predictions_by_date = {}
        actuals_by_date = {}

        for i in range(10):
            date = f"2024-01-{i+1:02d}"
            preds, rets = TestDataGenerator.generate_correlated_data(n_samples=100, seed=i)
            predictions_by_date[date] = preds

            # 只添加偶数日期的实际收益
            if i % 2 == 0:
                actuals_by_date[date] = rets

        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_timeseries(
            predictions_by_date, actuals_by_date, verbose=False
        )

        # 应该只处理匹配的日期
        self.assertIsInstance(metrics, dict)

    def test_04_timeseries_ic_positive_rate(self):
        """测试 IC 正率的计算"""
        predictions_by_date = {}
        actuals_by_date = {}

        # 创建一半正相关，一半负相关的数据
        for i in range(10):
            date = f"2024-01-{i+1:02d}"
            if i < 5:
                # 正相关
                preds, rets = TestDataGenerator.generate_correlated_data(
                    n_samples=100, correlation=0.8, seed=i
                )
            else:
                # 负相关
                preds, rets = TestDataGenerator.generate_correlated_data(
                    n_samples=100, correlation=0.8, seed=i
                )
                rets = -rets  # 反转收益

            predictions_by_date[date] = preds
            actuals_by_date[date] = rets

        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_timeseries(
            predictions_by_date, actuals_by_date, verbose=False
        )

        # IC 正率应该在 0-1 之间
        self.assertGreaterEqual(metrics['ic_positive_rate'], 0.0)
        self.assertLessEqual(metrics['ic_positive_rate'], 1.0)


# ==================== 综合集成测试 ====================

class TestIntegration(unittest.TestCase):
    """综合集成测试"""

    def test_01_full_evaluation_workflow(self):
        """测试完整评估工作流"""
        # 1. 创建数据
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()

        # 2. 创建配置
        config = EvaluationConfig(n_groups=10, top_pct=0.1)

        # 3. 创建评估器
        evaluator = ModelEvaluator(config=config)

        # 4. 执行评估
        metrics = evaluator.evaluate_regression(predictions, actual_returns, verbose=False)

        # 5. 验证结果
        self.assertIsInstance(metrics, dict)
        self.assertGreater(len(metrics), 10)

        # 6. 获取指标
        retrieved_metrics = evaluator.get_metrics()
        self.assertEqual(metrics, retrieved_metrics)

        # 7. 清空指标
        evaluator.clear_metrics()
        self.assertEqual(len(evaluator.get_metrics()), 0)

    def test_02_multiple_evaluations(self):
        """测试多次评估"""
        evaluator = ModelEvaluator()

        for i in range(5):
            preds, rets = TestDataGenerator.generate_correlated_data(seed=i)
            metrics = evaluator.evaluate_regression(preds, rets, verbose=False)

            self.assertIsInstance(metrics, dict)
            self.assertGreater(len(metrics), 0)

    def test_03_convenience_function_workflow(self):
        """测试便捷函数工作流"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()

        # 测试回归评估
        regression_metrics = evaluate_model(
            predictions, actual_returns,
            evaluation_type='regression',
            verbose=False
        )
        self.assertIn('ic', regression_metrics)
        self.assertIn('r2', regression_metrics)

        # 测试排名评估
        ranking_metrics = evaluate_model(
            predictions, actual_returns,
            evaluation_type='ranking',
            verbose=False
        )
        self.assertIn('rank_ic', ranking_metrics)
        self.assertNotIn('r2', ranking_metrics)

    def test_04_backward_compatibility(self):
        """测试向后兼容性"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data()

        # 旧的静态方法调用方式
        ic = ModelEvaluator.calculate_ic(predictions, actual_returns)
        rank_ic = ModelEvaluator.calculate_rank_ic(predictions, actual_returns)
        group_returns = ModelEvaluator.calculate_group_returns(predictions, actual_returns)
        long_short = ModelEvaluator.calculate_long_short_return(predictions, actual_returns)

        # 所有方法都应该正常工作
        self.assertIsInstance(ic, float)
        self.assertIsInstance(rank_ic, float)
        self.assertIsInstance(group_returns, dict)
        self.assertIsInstance(long_short, dict)


# ==================== 性能和压力测试 ====================

class TestPerformance(unittest.TestCase):
    """性能和压力测试"""

    def test_01_large_dataset_performance(self):
        """测试大数据集性能"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data(n_samples=100000)

        start_time = time.time()
        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_regression(predictions, actual_returns, verbose=False)
        elapsed_time = time.time() - start_time

        # 10万样本应该在合理时间内完成（例如 < 5秒）
        self.assertLess(elapsed_time, 5.0, f"评估用时 {elapsed_time:.2f}秒，超过5秒")
        self.assertIsInstance(metrics, dict)

    def test_02_many_groups_performance(self):
        """测试大量分组的性能"""
        predictions, actual_returns = TestDataGenerator.generate_correlated_data(n_samples=10000)

        config = EvaluationConfig(n_groups=100)
        evaluator = ModelEvaluator(config=config)

        start_time = time.time()
        metrics = evaluator.evaluate_regression(predictions, actual_returns, verbose=False)
        elapsed_time = time.time() - start_time

        # 100 分组应该在合理时间内完成
        self.assertLess(elapsed_time, 3.0)
        self.assertIsInstance(metrics, dict)

    def test_03_timeseries_performance(self):
        """测试时间序列评估性能"""
        predictions_by_date = {}
        actuals_by_date = {}

        # 100个交易日，每日1000只股票
        for i in range(100):
            date = f"2024-{(i//30)+1:02d}-{(i%30)+1:02d}"
            preds, rets = TestDataGenerator.generate_correlated_data(n_samples=1000, seed=i)
            predictions_by_date[date] = preds
            actuals_by_date[date] = rets

        evaluator = ModelEvaluator()

        start_time = time.time()
        metrics = evaluator.evaluate_timeseries(
            predictions_by_date, actuals_by_date, verbose=False
        )
        elapsed_time = time.time() - start_time

        # 应该在合理时间内完成
        self.assertLess(elapsed_time, 10.0)
        self.assertIsInstance(metrics, dict)

    def test_04_sparse_data_performance(self):
        """测试稀疏数据性能"""
        predictions, actual_returns = TestDataGenerator.generate_sparse_data(
            n_samples=50000, nan_ratio=0.5
        )

        start_time = time.time()
        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_regression(predictions, actual_returns, verbose=False)
        elapsed_time = time.time() - start_time

        # 稀疏数据处理应该高效
        self.assertLess(elapsed_time, 5.0)
        self.assertIsInstance(metrics, dict)


# ==================== 数据验证测试 ====================

class TestDataValidation(unittest.TestCase):
    """数据验证详细测试"""

    def test_01_filter_valid_pairs_basic(self):
        """测试基础数据过滤"""
        predictions = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        actual_returns = np.array([0.01, 0.02, 0.03, np.nan, 0.05])

        valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)

        self.assertEqual(len(valid_preds), 3)
        self.assertEqual(len(valid_returns), 3)
        np.testing.assert_array_equal(valid_preds, np.array([1.0, 2.0, 5.0]))

    def test_02_filter_valid_pairs_with_inf(self):
        """测试过滤 Inf 值"""
        predictions = np.array([1.0, np.inf, 3.0, -np.inf, 5.0])
        actual_returns = np.array([0.01, 0.02, np.inf, 0.04, 0.05])

        valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)

        self.assertEqual(len(valid_preds), 2)
        np.testing.assert_array_equal(valid_preds, np.array([1.0, 5.0]))

    def test_03_filter_valid_pairs_min_samples(self):
        """测试最小样本数要求"""
        predictions = np.array([1.0, np.nan, np.nan, np.nan, np.nan])
        actual_returns = np.array([0.01, 0.02, 0.03, 0.04, 0.05])

        # 只有1个有效样本，但要求至少2个
        with self.assertRaises(InsufficientDataError):
            filter_valid_pairs(predictions, actual_returns, min_samples=2)

    def test_04_filter_valid_pairs_custom_min_samples(self):
        """测试自定义最小样本数"""
        predictions = np.array([1.0, 2.0, 3.0, np.nan, np.nan])
        actual_returns = np.array([0.01, 0.02, 0.03, 0.04, 0.05])

        # 要求至少 5 个样本，但只有 3 个有效
        with self.assertRaises(InsufficientDataError):
            filter_valid_pairs(predictions, actual_returns, min_samples=5)


# ==================== 测试套件 ====================

def create_test_suite():
    """创建完整的测试套件"""
    suite = unittest.TestSuite()

    # 基础指标测试
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestICMetrics))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestGroupReturns))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLongShortReturns))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestRiskMetrics))

    # 异常处理和边界测试
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestExceptionHandlingComprehensive))

    # 配置管理测试
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestEvaluationConfigComprehensive))

    # 结果格式化测试
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestResultFormatterComprehensive))

    # 时间序列评估测试
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTimeseriesEvaluation))

    # 综合集成测试
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestIntegration))

    # 性能和压力测试
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPerformance))

    # 数据验证测试
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestDataValidation))

    return suite


def run_all_tests(verbosity=2):
    """运行所有测试"""
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    # 打印测试摘要
    print("\n" + "="*70)
    print("测试摘要")
    print("="*70)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")
    print("="*70)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests(verbosity=2)
    sys.exit(0 if success else 1)
