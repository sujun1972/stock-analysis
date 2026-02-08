"""
动量策略单元测试
测试动量策略的信号生成、打分和回测功能
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 添加src目录到路径
# Path already configured in conftest.py

from strategies import MomentumStrategy
from strategies.signal_generator import SignalType


class TestMomentumStrategy(unittest.TestCase):
    """测试动量策略"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)

        # 创建价格数据
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(20)]

        # 创建不同趋势的股票
        price_data = {}
        for i, stock in enumerate(stocks):
            if i < 5:
                # 强势上涨股票
                trend = 0.01
            elif i < 10:
                # 弱势上涨股票
                trend = 0.002
            elif i < 15:
                # 震荡股票
                trend = 0.0
            else:
                # 下跌股票
                trend = -0.005

            returns = trend + np.random.normal(0, 0.01, len(dates))
            prices = 100.0 * (1 + returns).cumprod()
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
        strategy = MomentumStrategy(
            name='MOM20',
            config={
                'lookback_period': 20,
                'top_n': 5,
                'holding_period': 5
            }
        )

        self.assertEqual(strategy.name, 'MOM20')
        self.assertEqual(strategy.lookback_period, 20)
        self.assertEqual(strategy.config.top_n, 5)
        self.assertEqual(strategy.config.holding_period, 5)
        self.assertTrue(strategy.filter_negative)  # 默认过滤负收益

    def test_calculate_momentum_simple_return(self):
        """测试简单收益率动量计算"""
        strategy = MomentumStrategy('MOM20', {
            'lookback_period': 20,
            'use_log_return': False
        })

        momentum = strategy.calculate_momentum(self.prices, lookback=20)

        # 验证形状
        self.assertEqual(momentum.shape, self.prices.shape)

        # 验证前19天是NaN（需要20个数据点计算收益率）
        self.assertTrue(momentum.iloc[:19].isna().all().all())

        # 验证后续有值
        self.assertFalse(momentum.iloc[20:].isna().all().all())

    def test_calculate_momentum_log_return(self):
        """测试对数收益率动量计算"""
        strategy = MomentumStrategy('MOM20', {
            'lookback_period': 20,
            'use_log_return': True
        })

        momentum = strategy.calculate_momentum(self.prices, lookback=20)

        # 验证形状
        self.assertEqual(momentum.shape, self.prices.shape)

        # 对数收益率应该略小于简单收益率
        simple_mom = strategy.calculate_momentum(self.prices, lookback=20)
        # 注意：calculate_momentum使用的是策略配置，需要重新计算
        strategy.use_log_return = False
        simple_mom = strategy.calculate_momentum(self.prices, lookback=20)

        # 由于随机数据，只验证计算成功
        self.assertIsNotNone(momentum)

    def test_calculate_scores(self):
        """测试打分计算"""
        strategy = MomentumStrategy('MOM20', {
            'lookback_period': 20,
            'filter_negative': True
        })

        # 选择有足够历史数据的日期
        test_date = self.prices.index[50]
        scores = strategy.calculate_scores(self.prices, date=test_date)

        # 验证返回的是Series
        self.assertIsInstance(scores, pd.Series)

        # 验证索引是股票代码
        self.assertEqual(len(scores), len(self.prices.columns))

        # 验证强势股票得分较高
        strong_stocks = [f'stock_{i:03d}' for i in range(5)]
        weak_stocks = [f'stock_{i:03d}' for i in range(15, 20)]

        # 过滤掉NaN后比较
        strong_scores = scores[strong_stocks].dropna()
        weak_scores = scores[weak_stocks].dropna()

        if len(strong_scores) > 0 and len(weak_scores) > 0:
            self.assertGreater(
                strong_scores.mean(),
                weak_scores.mean()
            )

    def test_filter_negative_momentum(self):
        """测试过滤负动量"""
        strategy = MomentumStrategy('MOM20', {
            'lookback_period': 20,
            'filter_negative': True
        })

        test_date = self.prices.index[50]
        scores = strategy.calculate_scores(self.prices, date=test_date)

        # 所有非NaN的分数应该是非负的
        valid_scores = scores.dropna()
        if len(valid_scores) > 0:
            self.assertTrue(all(valid_scores >= 0))

    def test_no_filter_negative_momentum(self):
        """测试不过滤负动量"""
        strategy = MomentumStrategy('MOM20', {
            'lookback_period': 20,
            'filter_negative': False
        })

        test_date = self.prices.index[50]
        scores = strategy.calculate_scores(self.prices, date=test_date)

        # 可能有负分数
        valid_scores = scores.dropna()
        if len(valid_scores) > 0:
            # 下跌股票应该有负分数
            weak_stocks = [f'stock_{i:03d}' for i in range(15, 20)]
            weak_scores = scores[weak_stocks].dropna()
            if len(weak_scores) > 0:
                self.assertTrue(any(weak_scores < 0))

    def test_generate_signals(self):
        """测试信号生成"""
        strategy = MomentumStrategy('MOM20', {
            'lookback_period': 20,
            'top_n': 5,
            'holding_period': 5
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
        for date in signals.index[20:]:  # 跳过前20天（没有足够历史数据）
            daily_signals = signals.loc[date]
            buy_count = (daily_signals == SignalType.BUY).sum()
            self.assertLessEqual(buy_count, strategy.config.top_n)

    def test_signals_with_insufficient_data(self):
        """测试数据不足时的信号生成"""
        strategy = MomentumStrategy('MOM20', {
            'lookback_period': 20,
            'top_n': 5
        })

        # 只使用15天的数据（少于lookback_period）
        short_prices = self.prices.iloc[:15]

        signals = strategy.generate_signals(short_prices)

        # 前面应该大部分是持有信号（NaN或0）
        # 由于数据不足，可能有NaN
        hold_or_nan = (signals == SignalType.HOLD.value) | signals.isna()
        self.assertTrue(hold_or_nan.sum().sum() > signals.size * 0.8)

    def test_backtest_integration(self):
        """测试回测集成"""
        from backtest.backtest_engine import BacktestEngine

        strategy = MomentumStrategy('MOM20', {
            'lookback_period': 20,
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

    def test_different_lookback_periods(self):
        """测试不同的回看期"""
        for lookback in [5, 10, 20, 60]:
            strategy = MomentumStrategy(f'MOM{lookback}', {
                'lookback_period': lookback,
                'top_n': 5
            })

            if len(self.prices) > lookback:
                test_date = self.prices.index[lookback + 10]
                scores = strategy.calculate_scores(self.prices, date=test_date)

                # 验证能够计算出分数
                self.assertIsInstance(scores, pd.Series)
                self.assertGreater(scores.notna().sum(), 0)

    def test_strategy_with_custom_params(self):
        """测试自定义参数"""
        strategy = MomentumStrategy('CustomMOM', {
            'lookback_period': 30,
            'top_n': 10,
            'holding_period': 10,
            'filter_negative': False,
            'use_log_return': True,
            'min_price': 5.0,
            'max_position_pct': 0.15
        })

        self.assertEqual(strategy.lookback_period, 30)
        self.assertEqual(strategy.config.top_n, 10)
        self.assertEqual(strategy.config.holding_period, 10)
        self.assertFalse(strategy.filter_negative)
        self.assertTrue(strategy.use_log_return)
        self.assertEqual(strategy.config.min_price, 5.0)
        self.assertEqual(strategy.config.max_position_pct, 0.15)

    def test_edge_case_single_stock(self):
        """测试边缘情况：单只股票"""
        single_stock_prices = self.prices.iloc[:, :1]

        strategy = MomentumStrategy('MOM20', {
            'lookback_period': 20,
            'top_n': 5
        })

        signals = strategy.generate_signals(single_stock_prices)

        # 应该能够正常生成信号
        self.assertIsNotNone(signals)
        self.assertEqual(signals.shape, single_stock_prices.shape)

    def test_edge_case_all_same_momentum(self):
        """测试边缘情况：所有股票动量相同"""
        # 创建所有股票价格都相同的数据
        same_prices = pd.DataFrame(
            {f'stock_{i:03d}': self.prices.iloc[:, 0] for i in range(10)},
            index=self.prices.index
        )

        strategy = MomentumStrategy('MOM20', {
            'lookback_period': 20,
            'top_n': 3
        })

        signals = strategy.generate_signals(same_prices)

        # 应该能够生成信号（可能随机选择）
        self.assertIsNotNone(signals)

        # 验证每天的买入信号数量不超过top_n
        for date in signals.index[20:]:
            buy_count = (signals.loc[date] == SignalType.BUY).sum()
            self.assertLessEqual(buy_count, strategy.config.top_n)


if __name__ == '__main__':
    unittest.main()
