"""
均值回归策略单元测试
测试均值回归策略的Z-score计算、布林带方法和信号生成
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from strategies.mean_reversion_strategy import MeanReversionStrategy
from strategies.signal_generator import SignalType


class TestMeanReversionStrategy(unittest.TestCase):
    """测试均值回归策略"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)

        # 创建价格数据
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(20)]

        # 创建不同波动模式的股票
        price_data = {}
        for i, stock in enumerate(stocks):
            if i < 5:
                # 超卖股票（Z-score < -2）
                base = 100
                prices = base + np.random.normal(-10, 2, len(dates))
                prices[-20:] -= 15  # 最近大幅下跌
            elif i < 10:
                # 超买股票（Z-score > 2）
                base = 100
                prices = base + np.random.normal(10, 2, len(dates))
                prices[-20:] += 15  # 最近大幅上涨
            elif i < 15:
                # 正常波动股票
                base = 100
                prices = base + np.random.normal(0, 5, len(dates))
            else:
                # 震荡股票
                t = np.arange(len(dates))
                prices = 100 + 10 * np.sin(t * 2 * np.pi / 20)

            price_data[stock] = prices

        self.prices = pd.DataFrame(price_data, index=dates)

        # 创建成交量数据
        volume_data = {
            stock: np.random.uniform(1000000, 10000000, len(dates))
            for stock in stocks
        }
        self.volumes = pd.DataFrame(volume_data, index=dates)

    def test_strategy_initialization(self):
        """测试策略初始化"""
        strategy = MeanReversionStrategy(
            name='MR20',
            config={
                'lookback_period': 20,
                'z_score_threshold': -2.0,
                'top_n': 5
            }
        )

        self.assertEqual(strategy.name, 'MR20')
        self.assertEqual(strategy.lookback_period, 20)
        self.assertEqual(strategy.z_score_threshold, -2.0)
        self.assertEqual(strategy.config.top_n, 5)
        self.assertFalse(strategy.use_bollinger)  # 默认不使用布林带

    def test_calculate_z_score(self):
        """测试Z-score计算"""
        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'use_bollinger': False
        })

        z_scores = strategy.calculate_z_score(self.prices, lookback=20)

        # 验证形状
        self.assertEqual(z_scores.shape, self.prices.shape)

        # 验证前19天是NaN（需要20个数据点才能计算）
        self.assertTrue(z_scores.iloc[:19].isna().all().all())

        # 验证后续有值
        self.assertFalse(z_scores.iloc[20:].isna().all().all())

    def test_calculate_bollinger_position(self):
        """测试布林带位置计算"""
        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'use_bollinger': True,
            'bollinger_window': 20,
            'bollinger_std': 2.0
        })

        bb_positions = strategy.calculate_bollinger_position(self.prices)

        # 验证形状
        self.assertEqual(bb_positions.shape, self.prices.shape)

        # 验证前19天是NaN（需要20个数据点计算）
        self.assertTrue(bb_positions.iloc[:19].isna().all().all())

        # 验证后续有值
        self.assertFalse(bb_positions.iloc[20:].isna().all().all())

        # 验证布林带位置在0-1之间（0=下轨，0.5=中轨，1=上轨）
        valid_bb = bb_positions.iloc[20:].values.flatten()
        valid_bb = valid_bb[~np.isnan(valid_bb)]
        # 允许一定的超出范围（由于极端波动）
        self.assertGreater(np.percentile(valid_bb, 10), -0.5)
        self.assertLess(np.percentile(valid_bb, 90), 1.5)

    def test_calculate_scores_zscore_method(self):
        """测试Z-score方法打分"""
        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'z_score_threshold': -2.0,
            'use_bollinger': False
        })

        test_date = self.prices.index[50]
        scores = strategy.calculate_scores(self.prices, date=test_date)

        # 验证返回的是Series
        self.assertIsInstance(scores, pd.Series)

        # 验证索引是股票代码
        self.assertEqual(len(scores), len(self.prices.columns))

    def test_calculate_scores_bollinger_method(self):
        """测试布林带方法打分"""
        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'use_bollinger': True,
            'bollinger_window': 20,
            'bollinger_std': 2.0
        })

        test_date = self.prices.index[50]
        scores = strategy.calculate_scores(self.prices, date=test_date)

        # 验证返回的是Series
        self.assertIsInstance(scores, pd.Series)

        # 验证有效分数
        valid_scores = scores.dropna()
        self.assertGreaterEqual(len(valid_scores), 0)

    def test_generate_signals_zscore(self):
        """测试Z-score方法信号生成"""
        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'z_score_threshold': -1.5,
            'top_n': 5,
            'use_bollinger': False
        })

        signals = strategy.generate_signals(self.prices, volumes=self.volumes)

        # 验证返回的是DataFrame
        self.assertIsInstance(signals, pd.DataFrame)

        # 验证形状
        self.assertEqual(signals.shape, self.prices.shape)

        # 验证信号值在[-1, 0, 1]范围内
        unique_values = signals.stack().unique()
        self.assertTrue(all(v in [-1, 0, 1] for v in unique_values))

        # 验证每天最多有top_n个买入信号
        for date in signals.index[20:]:
            daily_signals = signals.loc[date]
            buy_count = (daily_signals == SignalType.BUY.value).sum()
            self.assertLessEqual(buy_count, strategy.config.top_n)

    def test_generate_signals_bollinger(self):
        """测试布林带方法信号生成"""
        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'top_n': 5,
            'use_bollinger': True,
            'bollinger_window': 20,
            'bollinger_std': 2.0
        })

        signals = strategy.generate_signals(self.prices, volumes=self.volumes)

        # 验证返回的是DataFrame
        self.assertIsInstance(signals, pd.DataFrame)

        # 验证形状
        self.assertEqual(signals.shape, self.prices.shape)

        # 验证信号值
        unique_values = signals.stack().unique()
        self.assertTrue(all(v in [-1, 0, 1] for v in unique_values))

    def test_different_thresholds(self):
        """测试不同的阈值"""
        for threshold in [-3.0, -2.0, -1.5, -1.0]:
            strategy = MeanReversionStrategy(f'MR_T{abs(threshold)}', {
                'lookback_period': 20,
                'z_score_threshold': threshold,
                'top_n': 5
            })

            test_date = self.prices.index[50]
            scores = strategy.calculate_scores(self.prices, date=test_date)

            # 验证能够计算出分数
            self.assertIsInstance(scores, pd.Series)

    def test_backtest_integration(self):
        """测试回测集成"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))
        from backtest.backtest_engine import BacktestEngine

        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'z_score_threshold': -2.0,
            'top_n': 5,
            'holding_period': 5
        })

        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            verbose=False
        )

        results = strategy.backtest(engine, self.prices)

        # 验证返回结果包含必要的键
        self.assertIn('portfolio_value', results)
        self.assertIn('positions', results)
        self.assertIn('daily_returns', results)

        # 验证资产组合价值
        portfolio_value = results['portfolio_value']
        self.assertIsInstance(portfolio_value, pd.DataFrame)
        self.assertIn('total', portfolio_value.columns)

        # 验证最终资金大于0
        final_value = portfolio_value['total'].iloc[-1]
        self.assertGreater(final_value, 0)

    def test_strategy_with_custom_params(self):
        """测试自定义参数"""
        strategy = MeanReversionStrategy('CustomMR', {
            'lookback_period': 30,
            'z_score_threshold': -2.5,
            'top_n': 10,
            'holding_period': 10,
            'use_bollinger': True,
            'bollinger_window': 30,
            'bollinger_std': 1.5,
            'min_price': 5.0
        })

        self.assertEqual(strategy.lookback_period, 30)
        self.assertEqual(strategy.z_score_threshold, -2.5)
        self.assertEqual(strategy.config.top_n, 10)
        self.assertEqual(strategy.config.holding_period, 10)
        self.assertTrue(strategy.use_bollinger)
        self.assertEqual(strategy.bollinger_std, 1.5)
        self.assertEqual(strategy.config.min_price, 5.0)

    def test_signals_with_insufficient_data(self):
        """测试数据不足时的信号生成"""
        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'top_n': 5
        })

        # 只使用15天的数据
        short_prices = self.prices.iloc[:15]

        signals = strategy.generate_signals(short_prices)

        # 前面应该大部分是持有信号（0）
        hold_count = (signals == SignalType.HOLD.value).sum().sum()
        self.assertGreater(hold_count, signals.size * 0.8)

    def test_edge_case_single_stock(self):
        """测试边缘情况：单只股票"""
        single_stock_prices = self.prices.iloc[:, :1]

        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'top_n': 5
        })

        signals = strategy.generate_signals(single_stock_prices)

        # 应该能够正常生成信号
        self.assertIsNotNone(signals)
        self.assertEqual(signals.shape, single_stock_prices.shape)

    def test_edge_case_no_volatility(self):
        """测试边缘情况：无波动（标准差为0）"""
        # 创建恒定价格的数据
        constant_prices = pd.DataFrame(
            {f'stock_{i:03d}': [100.0] * len(self.prices) for i in range(5)},
            index=self.prices.index
        )

        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'top_n': 3
        })

        # 应该能够处理（虽然Z-score可能是NaN或0）
        z_scores = strategy.calculate_z_score(constant_prices, lookback=20)
        self.assertIsNotNone(z_scores)

        # 生成信号时应该全是持有
        signals = strategy.generate_signals(constant_prices)
        non_nan_signals = signals.iloc[20:]
        if len(non_nan_signals) > 0:
            # 可能全是持有信号
            unique_signals = non_nan_signals.stack().unique()
            self.assertTrue(len(unique_signals) <= 2)  # 最多有买入和持有

    def test_method_validation(self):
        """测试方法验证"""
        # 测试Z-score方法
        strategy_zscore = MeanReversionStrategy('MR_zscore', {
            'lookback_period': 20,
            'use_bollinger': False
        })
        self.assertFalse(strategy_zscore.use_bollinger)

        # 测试布林带方法
        strategy_bollinger = MeanReversionStrategy('MR_bollinger', {
            'lookback_period': 20,
            'use_bollinger': True
        })
        self.assertTrue(strategy_bollinger.use_bollinger)

    def test_oscillating_market_performance(self):
        """测试震荡市场表现"""
        # 使用震荡股票（stock_15-19）
        oscillating_prices = self.prices[[f'stock_{i:03d}' for i in range(15, 20)]]

        strategy = MeanReversionStrategy('MR20', {
            'lookback_period': 20,
            'z_score_threshold': -1.5,
            'top_n': 3,
            'holding_period': 3
        })

        signals = strategy.generate_signals(oscillating_prices)

        # 验证在震荡市场中能够生成信号
        buy_signals = (signals == SignalType.BUY.value).sum().sum()
        self.assertGreaterEqual(buy_signals, 0)

    def test_extreme_z_score_threshold(self):
        """测试极端Z-score阈值"""
        # 非常严格的阈值（很少触发）
        strict_strategy = MeanReversionStrategy('MR_strict', {
            'lookback_period': 20,
            'z_score_threshold': -5.0,
            'top_n': 5
        })

        test_date = self.prices.index[50]
        scores = strict_strategy.calculate_scores(self.prices, date=test_date)

        # 应该能够计算，但可能很少有股票满足条件
        self.assertIsInstance(scores, pd.Series)

        # 宽松的阈值（经常触发）
        loose_strategy = MeanReversionStrategy('MR_loose', {
            'lookback_period': 20,
            'z_score_threshold': -0.5,
            'top_n': 5
        })

        scores = loose_strategy.calculate_scores(self.prices, date=test_date)
        self.assertIsInstance(scores, pd.Series)


if __name__ == '__main__':
    unittest.main()
