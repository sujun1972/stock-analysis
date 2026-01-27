"""
模型评估器单元测试
测试量化交易专用评估指标：IC, RankIC, Sharpe, 分组收益等

测试重构后的模块化架构：
- 异常处理和数据验证
- MetricsCalculator 指标计算器
- ResultFormatter 结果格式化器
- ModelEvaluator 主评估器
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path

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


class TestModelEvaluatorBasicMetrics(unittest.TestCase):
    """模型评估器基础指标测试"""

    @classmethod
    def setUpClass(cls):
        """类级别设置 - 创建测试数据"""
        np.random.seed(42)
        cls.n_samples = 1000

        # 创建有相关性的测试数据
        cls.true_signal = np.random.randn(cls.n_samples)
        cls.predictions = cls.true_signal + np.random.randn(cls.n_samples) * 0.5
        cls.actual_returns = cls.true_signal * 0.02 + np.random.randn(cls.n_samples) * 0.01

    def test_01_calculate_ic_pearson(self):
        """测试Pearson IC计算"""
        ic = ModelEvaluator.calculate_ic(
            self.predictions,
            self.actual_returns,
            method='pearson'
        )

        # 验证IC在合理范围内
        self.assertIsInstance(ic, float)
        self.assertGreater(ic, 0.3, f"IC should be > 0.3, got {ic:.4f}")
        self.assertLess(ic, 1.0)
        self.assertFalse(np.isnan(ic))

    def test_02_calculate_ic_spearman(self):
        """测试Spearman IC计算（Rank IC）"""
        rank_ic = ModelEvaluator.calculate_ic(
            self.predictions,
            self.actual_returns,
            method='spearman'
        )

        # 验证Rank IC在合理范围内
        self.assertIsInstance(rank_ic, float)
        self.assertGreater(rank_ic, 0.3)
        self.assertLess(rank_ic, 1.0)
        self.assertFalse(np.isnan(rank_ic))

    def test_03_calculate_rank_ic(self):
        """测试Rank IC专用方法"""
        rank_ic = ModelEvaluator.calculate_rank_ic(
            self.predictions,
            self.actual_returns
        )

        # 与Spearman方法对比
        spearman_ic = ModelEvaluator.calculate_ic(
            self.predictions,
            self.actual_returns,
            method='spearman'
        )

        np.testing.assert_almost_equal(
            rank_ic, spearman_ic,
            decimal=10,
            err_msg="Rank IC should equal Spearman IC"
        )

    def test_04_ic_with_nan_values(self):
        """测试包含NaN值的IC计算"""
        predictions_with_nan = self.predictions.copy()
        predictions_with_nan[0] = np.nan
        predictions_with_nan[50] = np.nan

        ic = ModelEvaluator.calculate_ic(
            predictions_with_nan,
            self.actual_returns,
            method='pearson'
        )

        # 验证能正确处理NaN
        self.assertFalse(np.isnan(ic))
        self.assertIsInstance(ic, float)

    def test_05_ic_with_insufficient_data(self):
        """测试数据不足时的IC计算"""
        ic = ModelEvaluator.calculate_ic(
            np.array([1.0]),
            np.array([0.5]),
            method='pearson'
        )

        # 单个数据点应返回NaN
        self.assertTrue(np.isnan(ic))

    def test_06_calculate_ic_ir(self):
        """测试IC IR计算"""
        # 创建IC时间序列
        ic_series = pd.Series([0.05, 0.03, 0.08, 0.02, 0.06, 0.04, -0.01, 0.07])

        ic_ir = ModelEvaluator.calculate_ic_ir(ic_series)

        # 验证IC IR
        expected_ic_mean = ic_series.mean()
        expected_ic_std = ic_series.std()
        expected_ic_ir = expected_ic_mean / expected_ic_std

        self.assertAlmostEqual(ic_ir, expected_ic_ir, places=10)

    def test_07_ic_ir_with_zero_std(self):
        """测试标准差为零的IC IR"""
        ic_series = pd.Series([0.05, 0.05, 0.05, 0.05])

        ic_ir = ModelEvaluator.calculate_ic_ir(ic_series)

        # 标准差为0应返回NaN
        self.assertTrue(np.isnan(ic_ir))


class TestModelEvaluatorGroupReturns(unittest.TestCase):
    """分组收益率测试"""

    def setUp(self):
        """每个测试前的设置"""
        np.random.seed(42)

    def test_01_calculate_group_returns(self):
        """测试分组收益率计算"""
        n_samples = 500
        predictions = np.random.randn(n_samples)
        actual_returns = predictions * 0.02 + np.random.randn(n_samples) * 0.01

        group_returns = ModelEvaluator.calculate_group_returns(
            predictions,
            actual_returns,
            n_groups=5
        )

        # 验证返回的是字典
        self.assertIsInstance(group_returns, dict)

        # 验证有5个分组
        self.assertEqual(len(group_returns), 5)

        # 验证分组编号正确
        for i in range(5):
            self.assertIn(i, group_returns)

        # 验证分组0（预测值最低组）的收益小于分组4（预测值最高组）
        # 因为actual_returns = predictions * 0.02 + noise
        self.assertLess(group_returns[0], group_returns[4])

    def test_02_group_returns_monotonicity(self):
        """测试分组收益率的单调性"""
        n_samples = 1000
        # 创建强相关的数据
        predictions = np.random.randn(n_samples)
        actual_returns = predictions * 0.03  # 强正相关，无噪声

        group_returns = ModelEvaluator.calculate_group_returns(
            predictions,
            actual_returns,
            n_groups=5
        )

        # 验证分组收益单调递增
        returns_list = [group_returns[i] for i in range(5)]
        for i in range(4):
            self.assertLess(
                returns_list[i], returns_list[i+1],
                f"Group {i} return should be less than group {i+1}"
            )


class TestModelEvaluatorLongShortReturns(unittest.TestCase):
    """多空收益率测试"""

    def test_01_calculate_long_short_return(self):
        """测试多空收益率计算"""
        np.random.seed(42)
        n_samples = 500

        # 创建相关数据
        predictions = np.random.randn(n_samples)
        actual_returns = predictions * 0.02 + np.random.randn(n_samples) * 0.005

        long_short = ModelEvaluator.calculate_long_short_return(
            predictions,
            actual_returns,
            top_pct=0.2,
            bottom_pct=0.2
        )

        # 验证返回值结构
        self.assertIn('long', long_short)
        self.assertIn('short', long_short)
        self.assertIn('long_short', long_short)

        # 验证多头收益 > 空头收益（因为正相关）
        self.assertGreater(long_short['long'], long_short['short'])

        # 验证多空收益 = 多头 - 空头
        self.assertAlmostEqual(
            long_short['long_short'],
            long_short['long'] - long_short['short'],
            places=10
        )

        # 验证多空收益为正（因为正相关）
        self.assertGreater(long_short['long_short'], 0)

    def test_02_long_short_different_percentiles(self):
        """测试不同百分位的多空收益"""
        np.random.seed(42)
        n_samples = 1000
        predictions = np.random.randn(n_samples)
        actual_returns = predictions * 0.03

        # 20%分位
        ls_20 = ModelEvaluator.calculate_long_short_return(
            predictions, actual_returns, top_pct=0.2, bottom_pct=0.2
        )

        # 10%分位（更激进）
        ls_10 = ModelEvaluator.calculate_long_short_return(
            predictions, actual_returns, top_pct=0.1, bottom_pct=0.1
        )

        # 验证更激进的策略应该有更高的多空收益（因为选择更极端的股票）
        self.assertGreater(ls_10['long_short'], ls_20['long_short'])


class TestModelEvaluatorRiskMetrics(unittest.TestCase):
    """风险指标测试"""

    def test_01_calculate_sharpe_ratio(self):
        """测试Sharpe比率计算"""
        np.random.seed(42)

        # 创建日收益率序列（年化Sharpe约2.0）
        daily_returns = np.random.randn(252) * 0.01 + 0.001  # 均值0.1%, 波动1%

        sharpe = ModelEvaluator.calculate_sharpe_ratio(
            daily_returns,
            risk_free_rate=0.03,
            periods_per_year=252
        )

        # 验证Sharpe在合理范围
        self.assertIsInstance(sharpe, float)
        self.assertFalse(np.isnan(sharpe))
        self.assertGreater(sharpe, 0)

    def test_02_sharpe_ratio_calculation(self):
        """测试Sharpe比率计算的正确性"""
        # 固定的收益率序列
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.01])

        sharpe = ModelEvaluator.calculate_sharpe_ratio(
            returns,
            risk_free_rate=0.0,
            periods_per_year=252
        )

        # 手动计算预期值
        mean_return = np.mean(returns) * 252
        std_return = np.std(returns, ddof=1) * np.sqrt(252)
        expected_sharpe = mean_return / std_return

        self.assertAlmostEqual(sharpe, expected_sharpe, places=10)

    def test_03_sharpe_with_zero_volatility(self):
        """测试零波动率的Sharpe比率"""
        returns = np.array([0.01, 0.01, 0.01, 0.01])

        sharpe = ModelEvaluator.calculate_sharpe_ratio(returns)

        # 波动率为0应返回NaN
        self.assertTrue(np.isnan(sharpe))

    def test_04_calculate_max_drawdown(self):
        """测试最大回撤计算"""
        # 创建有明显回撤的收益率序列
        returns = np.array([0.05, 0.03, -0.10, -0.05, 0.02, 0.04, -0.08, 0.03])

        max_dd = ModelEvaluator.calculate_max_drawdown(returns)

        # 验证最大回撤为正值
        self.assertGreater(max_dd, 0)
        self.assertIsInstance(max_dd, float)

    def test_05_max_drawdown_no_drawdown(self):
        """测试无回撤情况"""
        # 持续上涨
        returns = np.array([0.01, 0.02, 0.01, 0.03, 0.02])

        max_dd = ModelEvaluator.calculate_max_drawdown(returns)

        # 无回撤应该接近0
        self.assertAlmostEqual(max_dd, 0.0, places=10)

    def test_06_calculate_win_rate(self):
        """测试胜率计算"""
        # 60%正收益，40%负收益
        returns = np.array([0.01, 0.02, -0.01, 0.03, -0.02, 0.01, 0.02, -0.01, 0.01, 0.02])

        win_rate = ModelEvaluator.calculate_win_rate(returns, threshold=0.0)

        # 验证胜率
        expected_win_rate = 7 / 10  # 7个正收益
        self.assertAlmostEqual(win_rate, expected_win_rate, places=10)

    def test_07_win_rate_with_threshold(self):
        """测试自定义阈值的胜率"""
        returns = np.array([0.001, 0.002, 0.005, 0.01, 0.02])

        # 阈值0.5%
        win_rate = ModelEvaluator.calculate_win_rate(returns, threshold=0.005)

        # 只有2个值>0.005 (0.01和0.02)，0.005等于阈值不算win
        self.assertAlmostEqual(win_rate, 0.4, places=10)


class TestModelEvaluatorComprehensive(unittest.TestCase):
    """综合评估测试"""

    def test_01_evaluate_regression(self):
        """测试完整回归评估"""
        np.random.seed(42)
        n_samples = 500

        true_signal = np.random.randn(n_samples)
        predictions = true_signal + np.random.randn(n_samples) * 0.3
        actual_returns = true_signal * 0.02 + np.random.randn(n_samples) * 0.005

        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_regression(
            predictions,
            actual_returns,
            verbose=False
        )

        # 验证所有关键指标都存在
        required_metrics = [
            'mse', 'rmse', 'mae', 'r2',
            'ic', 'rank_ic',
            'long_return', 'short_return', 'long_short_return'
        ]

        for metric in required_metrics:
            self.assertIn(metric, metrics, f"Missing metric: {metric}")
            self.assertFalse(np.isnan(metrics[metric]), f"Metric {metric} is NaN")

        # 验证分组收益率
        for i in range(5):
            self.assertIn(f'group_{i}_return', metrics)

        # 验证IC合理（R²对于随机数据可能为负，所以主要看IC）
        self.assertGreater(metrics['ic'], 0.3)

        # IC应该比R²更可靠，因为我们的数据有很强的相关性
        self.assertGreater(metrics['ic'], 0.7)

    def test_02_evaluate_timeseries(self):
        """测试时间序列评估"""
        np.random.seed(42)

        # 创建多日数据
        predictions_by_date = {}
        actuals_by_date = {}

        for i in range(20):
            date = f"2024-01-{i+1:02d}"
            n_stocks = 100

            true_signal = np.random.randn(n_stocks)
            predictions_by_date[date] = true_signal + np.random.randn(n_stocks) * 0.5
            actuals_by_date[date] = true_signal * 0.02 + np.random.randn(n_stocks) * 0.01

        evaluator = ModelEvaluator()
        metrics = evaluator.evaluate_timeseries(
            predictions_by_date,
            actuals_by_date,
            verbose=False
        )

        # 验证时间序列指标
        required_metrics = [
            'ic_mean', 'ic_std', 'ic_ir', 'ic_positive_rate',
            'rank_ic_mean', 'rank_ic_std', 'rank_ic_ir', 'rank_ic_positive_rate'
        ]

        for metric in required_metrics:
            self.assertIn(metric, metrics)
            self.assertFalse(np.isnan(metrics[metric]))

        # 验证IC正率应该较高（因为有相关性）
        self.assertGreater(metrics['ic_positive_rate'], 0.5)

    def test_03_get_and_print_metrics(self):
        """测试获取和打印指标"""
        np.random.seed(42)
        predictions = np.random.randn(100)
        actual_returns = predictions * 0.02 + np.random.randn(100) * 0.01

        evaluator = ModelEvaluator()
        evaluator.evaluate_regression(predictions, actual_returns, verbose=False)

        # 获取指标
        metrics = evaluator.get_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertGreater(len(metrics), 0)

        # 测试打印（不应抛出异常）
        try:
            evaluator.print_metrics()
        except Exception as e:
            self.fail(f"print_metrics() raised exception: {e}")


class TestModelEvaluatorConvenienceFunctions(unittest.TestCase):
    """便捷函数测试"""

    def test_01_evaluate_model_regression(self):
        """测试便捷函数 - 回归评估"""
        np.random.seed(42)
        predictions = np.random.randn(200)
        actual_returns = predictions * 0.02 + np.random.randn(200) * 0.01

        metrics = evaluate_model(
            predictions,
            actual_returns,
            evaluation_type='regression',
            verbose=False
        )

        self.assertIn('ic', metrics)
        self.assertIn('r2', metrics)

    def test_02_evaluate_model_ranking(self):
        """测试便捷函数 - 排名评估"""
        np.random.seed(42)
        predictions = np.random.randn(200)
        actual_returns = predictions * 0.02 + np.random.randn(200) * 0.01

        metrics = evaluate_model(
            predictions,
            actual_returns,
            evaluation_type='ranking',
            verbose=False
        )

        # 排名评估只包含IC和多空收益
        self.assertIn('rank_ic', metrics)
        self.assertIn('long', metrics)
        self.assertIn('short', metrics)
        self.assertIn('long_short', metrics)
        self.assertNotIn('r2', metrics)

    def test_03_evaluate_model_invalid_type(self):
        """测试无效评估类型"""
        predictions = np.random.randn(100)
        actual_returns = np.random.randn(100)

        with self.assertRaises(ValueError):
            evaluate_model(predictions, actual_returns, evaluation_type='invalid', verbose=False)

    def test_04_evaluate_model_with_custom_config(self):
        """测试使用自定义配置"""
        np.random.seed(42)
        predictions = np.random.randn(200)
        actual_returns = predictions * 0.02 + np.random.randn(200) * 0.01

        config = EvaluationConfig(
            n_groups=10,
            top_pct=0.1,
            bottom_pct=0.1
        )

        metrics = evaluate_model(
            predictions,
            actual_returns,
            evaluation_type='regression',
            config=config,
            verbose=False
        )

        # 验证使用了10个分组
        group_count = sum(1 for k in metrics.keys() if k.startswith('group_'))
        self.assertGreater(group_count, 5)  # 应该有更多分组


class TestExceptionHandling(unittest.TestCase):
    """异常处理测试"""

    def test_01_invalid_input_none(self):
        """测试 None 输入"""
        evaluator = ModelEvaluator()

        with self.assertRaises(InvalidInputError):
            evaluator.evaluate_regression(None, np.array([1, 2, 3]))

    def test_02_invalid_input_empty(self):
        """测试空数组输入"""
        evaluator = ModelEvaluator()

        with self.assertRaises(InsufficientDataError):
            evaluator.evaluate_regression(np.array([]), np.array([]))

    def test_03_invalid_input_mismatched_length(self):
        """测试长度不匹配的输入"""
        evaluator = ModelEvaluator()

        with self.assertRaises(InvalidInputError):
            evaluator.evaluate_regression(
                np.array([1, 2, 3]),
                np.array([1, 2])
            )

    def test_04_insufficient_data_filter(self):
        """测试数据不足过滤"""
        with self.assertRaises(InsufficientDataError):
            filter_valid_pairs(
                np.array([1.0]),
                np.array([2.0]),
                min_samples=2
            )

    def test_05_nan_handling(self):
        """测试 NaN 处理"""
        predictions = np.array([1.0, 2.0, np.nan, 4.0, 5.0])
        actual_returns = np.array([0.01, 0.02, 0.03, np.nan, 0.05])

        valid_preds, valid_returns = filter_valid_pairs(predictions, actual_returns)

        # 应该过滤掉 NaN
        self.assertEqual(len(valid_preds), 3)
        self.assertEqual(len(valid_returns), 3)


class TestMetricsCalculatorDirect(unittest.TestCase):
    """直接测试 MetricsCalculator 类"""

    def test_01_calculator_ic(self):
        """测试 MetricsCalculator 的 IC 计算"""
        np.random.seed(42)
        predictions = np.random.randn(100)
        actual_returns = predictions * 0.02 + np.random.randn(100) * 0.01

        calc = MetricsCalculator()
        ic = calc.calculate_ic(predictions, actual_returns)

        self.assertIsInstance(ic, float)
        self.assertFalse(np.isnan(ic))

    def test_02_calculator_group_returns(self):
        """测试 MetricsCalculator 的分组收益"""
        np.random.seed(42)
        predictions = np.random.randn(200)
        actual_returns = predictions * 0.02

        calc = MetricsCalculator()
        group_returns = calc.calculate_group_returns(predictions, actual_returns, n_groups=5)

        self.assertIsInstance(group_returns, dict)
        self.assertEqual(len(group_returns), 5)


class TestEvaluationConfig(unittest.TestCase):
    """评估配置测试"""

    def test_01_default_config(self):
        """测试默认配置"""
        config = EvaluationConfig()

        self.assertEqual(config.n_groups, 5)
        self.assertEqual(config.top_pct, 0.2)
        self.assertEqual(config.bottom_pct, 0.2)
        self.assertEqual(config.periods_per_year, 252)

    def test_02_custom_config(self):
        """测试自定义配置"""
        config = EvaluationConfig(
            n_groups=10,
            top_pct=0.1,
            bottom_pct=0.1,
            periods_per_year=250
        )

        self.assertEqual(config.n_groups, 10)
        self.assertEqual(config.top_pct, 0.1)
        self.assertEqual(config.periods_per_year, 250)

    def test_03_evaluator_with_config(self):
        """测试评估器使用配置"""
        config = EvaluationConfig(n_groups=8)
        evaluator = ModelEvaluator(config=config)

        self.assertEqual(evaluator.config.n_groups, 8)


class TestResultFormatter(unittest.TestCase):
    """结果格式化器测试"""

    def test_01_print_empty_metrics(self):
        """测试打印空指标"""
        formatter = ResultFormatter()

        # 不应抛出异常
        try:
            formatter.print_metrics({})
        except Exception as e:
            self.fail(f"print_metrics() raised exception: {e}")

    def test_02_print_full_metrics(self):
        """测试打印完整指标"""
        formatter = ResultFormatter()

        metrics = {
            'ic': 0.5,
            'rank_ic': 0.48,
            'mse': 0.01,
            'rmse': 0.1,
            'long_return': 0.02,
            'short_return': -0.01,
            'long_short_return': 0.03
        }

        # 不应抛出异常
        try:
            formatter.print_metrics(metrics)
        except Exception as e:
            self.fail(f"print_metrics() raised exception: {e}")


def run_tests():
    """运行测试"""
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
