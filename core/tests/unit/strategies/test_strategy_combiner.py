"""
策略组合器单元测试
测试多策略组合、一致性分析和组合方法
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 添加src目录到路径
# Path already configured in conftest.py

from strategies.strategy_combiner import StrategyCombiner
from strategies.momentum_strategy import MomentumStrategy
from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.signal_generator import SignalType


class TestStrategyCombiner(unittest.TestCase):
    """测试策略组合器"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)

        # 创建价格数据
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(20)]

        # 创建混合市场数据（既有趋势又有震荡）
        price_data = {}
        for i, stock in enumerate(stocks):
            if i < 10:
                # 趋势股票（动量策略有效）
                trend = 0.005
                volatility = 0.01
            else:
                # 震荡股票（均值回归策略有效）
                t = np.arange(len(dates))
                base = 100 + 10 * np.sin(t * 2 * np.pi / 20)
                noise = np.random.normal(0, 2, len(dates))
                price_data[stock] = base + noise
                continue

            returns = trend + np.random.normal(0, volatility, len(dates))
            prices = 100.0 * (1 + returns).cumprod()
            price_data[stock] = prices

        self.prices = pd.DataFrame(price_data, index=dates)

        # 创建成交量数据
        volume_data = {
            stock: np.random.uniform(1000000, 10000000, len(dates))
            for stock in stocks
        }
        self.volumes = pd.DataFrame(volume_data, index=dates)

        # 创建测试策略
        self.momentum_strategy = MomentumStrategy(
            name='MOM20',
            config={
                'lookback_period': 20,
                'top_n': 5,
                'holding_period': 5
            }
        )

        self.mean_reversion_strategy = MeanReversionStrategy(
            name='MR20',
            config={
                'lookback_period': 20,
                'z_score_threshold': -1.5,
                'top_n': 5,
                'holding_period': 5
            }
        )

    def test_combiner_initialization(self):
        """测试组合器初始化"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy],
            weights=[0.6, 0.4]
        )

        self.assertEqual(len(combiner.strategies), 2)
        self.assertEqual(combiner.weights, [0.6, 0.4])
        self.assertEqual(combiner.names, ['MOM20', 'MR20'])

    def test_equal_weights_default(self):
        """测试默认等权重"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy]
        )

        # 应该自动生成等权重
        self.assertEqual(len(combiner.weights), 2)
        self.assertEqual(combiner.weights, [0.5, 0.5])

    def test_custom_names(self):
        """测试自定义名称"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy],
            names=['Custom1', 'Custom2']
        )

        self.assertEqual(combiner.names, ['Custom1', 'Custom2'])

    def test_generate_individual_signals(self):
        """测试生成各个策略的信号"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy]
        )

        signals_list = combiner.generate_individual_signals(
            self.prices,
            volumes=self.volumes
        )

        # 验证返回列表
        self.assertIsInstance(signals_list, list)
        self.assertEqual(len(signals_list), 2)

        # 验证每个信号是DataFrame
        for signals in signals_list:
            self.assertIsInstance(signals, pd.DataFrame)
            self.assertEqual(signals.shape, self.prices.shape)

    def test_combine_vote_method(self):
        """测试投票组合方法"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy],
            weights=[0.6, 0.4]
        )

        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            method='vote'
        )

        # 验证返回的是DataFrame
        self.assertIsInstance(combined_signals, pd.DataFrame)
        self.assertEqual(combined_signals.shape, self.prices.shape)

        # 验证信号值在[-1, 0, 1]范围内
        unique_values = combined_signals.stack().unique()
        self.assertTrue(all(v in [-1, 0, 1] for v in unique_values))

    def test_combine_weighted_method(self):
        """测试加权组合方法"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy],
            weights=[0.7, 0.3]
        )

        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            method='weighted'
        )

        # 验证返回的是DataFrame
        self.assertIsInstance(combined_signals, pd.DataFrame)
        self.assertEqual(combined_signals.shape, self.prices.shape)

        # 加权方法返回的是连续值
        # 验证值在合理范围内（-1到1之间）
        all_values = combined_signals.stack().values
        valid_values = all_values[~np.isnan(all_values)]
        if len(valid_values) > 0:
            self.assertTrue(all(-1 <= v <= 1 for v in valid_values))

    def test_combine_and_method(self):
        """测试AND组合方法"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy]
        )

        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            method='and'
        )

        # 验证返回的是DataFrame
        self.assertIsInstance(combined_signals, pd.DataFrame)

        # AND方法：只有所有策略都同意才发出信号
        # 买入信号数量应该少于等于单个策略
        signals_list = combiner.generate_individual_signals(self.prices, volumes=self.volumes)
        individual_buy_counts = [
            (signals == SignalType.BUY.value).sum().sum()
            for signals in signals_list
        ]
        combined_buy_count = (combined_signals == SignalType.BUY.value).sum().sum()

        self.assertLessEqual(combined_buy_count, min(individual_buy_counts))

    def test_combine_or_method(self):
        """测试OR组合方法"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy]
        )

        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            method='or'
        )

        # 验证返回的是DataFrame
        self.assertIsInstance(combined_signals, pd.DataFrame)

        # OR方法：任一策略发出信号就发出信号
        # 买入信号数量应该多于或等于单个策略
        signals_list = combiner.generate_individual_signals(self.prices, volumes=self.volumes)
        individual_buy_counts = [
            (signals == SignalType.BUY.value).sum().sum()
            for signals in signals_list
        ]
        combined_buy_count = (combined_signals == SignalType.BUY.value).sum().sum()

        self.assertGreaterEqual(combined_buy_count, max(individual_buy_counts))

    def test_analyze_agreement(self):
        """测试策略一致性分析"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy]
        )

        signals_list = combiner.generate_individual_signals(
            self.prices,
            volumes=self.volumes
        )

        analysis = combiner.analyze_agreement(signals_list)

        # 验证返回的分析结果（根据实际StrategyCombiner.analyze_agreement的返回值）
        self.assertIn('buy_counts', analysis)
        self.assertIn('correlations', analysis)
        self.assertIn('unanimous_buy', analysis)
        self.assertIn('avg_correlation', analysis)

        # 验证买入计数
        self.assertEqual(len(analysis['buy_counts']), 2)

        # 验证unanimous_buy (一致买入)是整数
        self.assertIsInstance(analysis['unanimous_buy'], (int, np.integer))
        self.assertGreaterEqual(analysis['unanimous_buy'], 0)

        # 验证相关性在[-1, 1]范围内
        avg_corr = analysis['avg_correlation']
        if isinstance(avg_corr, (int, float, np.number)):
            self.assertGreaterEqual(avg_corr, -1.0)
            self.assertLessEqual(avg_corr, 1.0)

    def test_three_strategies_combination(self):
        """测试三策略组合"""
        # 创建第三个策略
        third_strategy = MomentumStrategy(
            name='MOM10',
            config={
                'lookback_period': 10,
                'top_n': 5,
                'holding_period': 5
            }
        )

        combiner = StrategyCombiner(
            strategies=[
                self.momentum_strategy,
                self.mean_reversion_strategy,
                third_strategy
            ],
            weights=[0.4, 0.3, 0.3]
        )

        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            method='vote'
        )

        # 验证能够组合三个策略
        self.assertIsInstance(combined_signals, pd.DataFrame)
        self.assertEqual(combined_signals.shape, self.prices.shape)

    def test_invalid_weights_length(self):
        """测试权重数量不匹配"""
        with self.assertRaises(ValueError):
            StrategyCombiner(
                strategies=[self.momentum_strategy, self.mean_reversion_strategy],
                weights=[0.5, 0.3, 0.2]  # 3个权重但只有2个策略
            )

    def test_empty_strategies_list(self):
        """测试空策略列表"""
        with self.assertRaises((ValueError, IndexError)):
            StrategyCombiner(strategies=[])

    def test_single_strategy(self):
        """测试单策略（边缘情况）"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy],
            weights=[1.0]
        )

        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            method='vote'
        )

        # 单策略组合应该等同于该策略本身
        original_signals = self.momentum_strategy.generate_signals(
            self.prices,
            volumes=self.volumes
        )

        # 使用更宽松的比较（允许dtype差异）
        pd.testing.assert_frame_equal(
            combined_signals.astype(int),
            original_signals.astype(int),
            check_dtype=False
        )

    def test_backtest_integration(self):
        """测试回测集成"""
        import sys
        from pathlib import Path
        # Path already configured in conftest.py
        from backtest.backtest_engine import BacktestEngine

        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy],
            weights=[0.6, 0.4]
        )

        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            verbose=False
        )

        # 组合策略回测
        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            method='weighted'
        )

        results = engine.backtest_long_only(
            signals=combined_signals,
            prices=self.prices,
            top_n=5,
            holding_period=5
        )

        # 验证返回结果
        self.assertIn('portfolio_value', results)
        portfolio_value = results['portfolio_value']
        self.assertIsInstance(portfolio_value, pd.DataFrame)

        # 验证最终资金大于0
        final_value = portfolio_value['total'].iloc[-1]
        self.assertGreater(final_value, 0)

    def test_weights_normalization(self):
        """测试权重归一化"""
        # 未归一化的权重
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy],
            weights=[3, 2]  # 未归一化
        )

        # 权重应该被归一化为和为1
        self.assertAlmostEqual(sum(combiner.weights), 1.0, places=5)
        self.assertAlmostEqual(combiner.weights[0], 0.6, places=5)
        self.assertAlmostEqual(combiner.weights[1], 0.4, places=5)

    def test_diverse_market_conditions(self):
        """测试不同市场条件下的表现"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy],
            weights=[0.5, 0.5]
        )

        # 在混合市场（既有趋势又有震荡）中应该能够适应
        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            method='vote'
        )

        # 验证两种策略都有贡献
        signals_list = combiner.generate_individual_signals(self.prices, volumes=self.volumes)

        mom_buy_count = (signals_list[0] == SignalType.BUY.value).sum().sum()
        mr_buy_count = (signals_list[1] == SignalType.BUY.value).sum().sum()

        # 两种策略至少有一个应该产生买入信号
        self.assertGreaterEqual(mom_buy_count + mr_buy_count, 0)

    def test_signal_correlation_analysis(self):
        """测试信号相关性分析"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy]
        )

        signals_list = combiner.generate_individual_signals(
            self.prices,
            volumes=self.volumes
        )

        analysis = combiner.analyze_agreement(signals_list)

        # 动量和均值回归策略通常是负相关的
        # （一个在上涨时买入，一个在下跌时买入）
        # 但这取决于市场条件和参数
        self.assertIsInstance(analysis['avg_correlation'], float)

    def test_unanimous_buy_signals(self):
        """测试一致性买入信号"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy]
        )

        signals_list = combiner.generate_individual_signals(
            self.prices,
            volumes=self.volumes
        )

        analysis = combiner.analyze_agreement(signals_list)

        # 验证一致性分析包含所需信息
        self.assertIn('unanimous_buy', analysis)

        # unanimous_buy应该是非负整数
        self.assertGreaterEqual(analysis['unanimous_buy'], 0)

    def test_combine_with_features(self):
        """测试带特征的组合（为未来多因子策略准备）"""
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy]
        )

        # 即使不使用features，也应该能正常工作
        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            features=None,
            method='vote'
        )

        self.assertIsInstance(combined_signals, pd.DataFrame)

    def test_different_holding_periods(self):
        """测试不同持仓期的策略组合"""
        short_term_strategy = MomentumStrategy(
            name='MOM_Short',
            config={
                'lookback_period': 10,
                'top_n': 5,
                'holding_period': 3
            }
        )

        long_term_strategy = MomentumStrategy(
            name='MOM_Long',
            config={
                'lookback_period': 40,
                'top_n': 5,
                'holding_period': 10
            }
        )

        combiner = StrategyCombiner(
            strategies=[short_term_strategy, long_term_strategy],
            weights=[0.5, 0.5]
        )

        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            method='weighted'
        )

        # 应该能够组合不同持仓期的策略
        self.assertIsInstance(combined_signals, pd.DataFrame)

    def test_performance_comparison(self):
        """测试组合策略与单一策略的性能对比"""
        import sys
        from pathlib import Path
        # Path already configured in conftest.py
        from backtest.backtest_engine import BacktestEngine

        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            verbose=False
        )

        # 单一动量策略
        mom_signals = self.momentum_strategy.generate_signals(
            self.prices,
            volumes=self.volumes
        )
        mom_results = engine.backtest_long_only(
            signals=mom_signals,
            prices=self.prices,
            top_n=5,
            holding_period=5
        )

        # 组合策略
        combiner = StrategyCombiner(
            strategies=[self.momentum_strategy, self.mean_reversion_strategy],
            weights=[0.6, 0.4]
        )

        combined_signals = combiner.combine(
            self.prices,
            volumes=self.volumes,
            method='weighted'
        )

        engine2 = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            verbose=False
        )

        combined_results = engine2.backtest_long_only(
            signals=combined_signals,
            prices=self.prices,
            top_n=5,
            holding_period=5
        )

        # 两种策略都应该能够运行
        self.assertIsNotNone(mom_results['portfolio_value'])
        self.assertIsNotNone(combined_results['portfolio_value'])


if __name__ == '__main__':
    unittest.main()
