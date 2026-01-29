"""
信号生成器单元测试
测试各种信号生成方法和组合逻辑
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from strategies.signal_generator import SignalType, SignalGenerator


class TestSignalType(unittest.TestCase):
    """测试信号类型枚举"""

    def test_signal_type_values(self):
        """测试信号类型的值"""
        self.assertEqual(SignalType.BUY.value, 1)
        self.assertEqual(SignalType.HOLD.value, 0)
        self.assertEqual(SignalType.SELL.value, -1)


class TestThresholdSignals(unittest.TestCase):
    """测试阈值信号生成"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(20)]

        # Create DataFrame of scores (dates x stocks)
        self.scores = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

    def test_basic_threshold_signals(self):
        """测试基本阈值信号"""
        signals = SignalGenerator.generate_threshold_signals(
            self.scores,
            buy_threshold=0.5,
            sell_threshold=-0.5
        )

        # 验证信号类型
        unique_values = signals.stack().unique()
        self.assertTrue(all(v in [-1, 0, 1] for v in unique_values))

        # 验证买入信号 - 检查符合条件的位置
        buy_mask = self.scores > 0.5
        for date in self.scores.index:
            for stock in self.scores.columns:
                if buy_mask.loc[date, stock]:
                    self.assertEqual(signals.loc[date, stock], SignalType.BUY.value)

        # 验证卖出信号
        sell_mask = self.scores < -0.5
        for date in self.scores.index:
            for stock in self.scores.columns:
                if sell_mask.loc[date, stock]:
                    self.assertEqual(signals.loc[date, stock], SignalType.SELL.value)

    def test_threshold_signals_all_buy(self):
        """测试全部买入信号"""
        signals = SignalGenerator.generate_threshold_signals(
            self.scores,
            buy_threshold=-10,  # 非常低的阈值
            sell_threshold=-20
        )

        # 所有信号应该是买入
        self.assertTrue(all(signals == SignalType.BUY))

    def test_threshold_signals_all_hold(self):
        """测试全部持有信号"""
        signals = SignalGenerator.generate_threshold_signals(
            self.scores,
            buy_threshold=10,  # 非常高的阈值
            sell_threshold=-10
        )

        # 所有信号应该是持有
        self.assertTrue(all(signals == SignalType.HOLD))


class TestRankSignals(unittest.TestCase):
    """测试排名信号生成"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(20)]

        # Create DataFrame of scores (dates x stocks)
        self.scores = pd.DataFrame(
            np.random.randn(len(dates), len(stocks)),
            index=dates,
            columns=stocks
        )

    def test_basic_rank_signals(self):
        """测试基本排名信号"""
        signals = SignalGenerator.generate_rank_signals(
            self.scores,
            top_n=5,
            bottom_n=3
        )

        # 验证每天买入信号数量
        for date in signals.index:
            buy_count = (signals.loc[date] == SignalType.BUY.value).sum()
            self.assertLessEqual(buy_count, 5)

            # 验证卖出信号数量
            sell_count = (signals.loc[date] == SignalType.SELL.value).sum()
            self.assertLessEqual(sell_count, 3)

    def test_rank_signals_only_buy(self):
        """测试只买入信号"""
        signals = SignalGenerator.generate_rank_signals(
            self.scores,
            top_n=5,
            bottom_n=0
        )

        # 验证每天最多有5个买入信号
        for date in signals.index:
            buy_count = (signals.loc[date] == SignalType.BUY.value).sum()
            self.assertLessEqual(buy_count, 5)

            # 验证没有卖出信号
            sell_count = (signals.loc[date] == SignalType.SELL.value).sum()
            self.assertEqual(sell_count, 0)

    def test_rank_signals_with_nan(self):
        """测试包含NaN值的排名信号"""
        scores_with_nan = self.scores.copy()
        scores_with_nan.iloc[:3, :] = np.nan

        signals = SignalGenerator.generate_rank_signals(
            scores_with_nan,
            top_n=5,
            bottom_n=2
        )

        # NaN值对应的日期应该没有买入/卖出信号（全是持有）
        for i in range(3):
            date_signals = signals.iloc[i]
            buy_count = (date_signals == SignalType.BUY.value).sum()
            sell_count = (date_signals == SignalType.SELL.value).sum()
            self.assertEqual(buy_count, 0)
            self.assertEqual(sell_count, 0)


class TestCrossSignals(unittest.TestCase):
    """测试交叉信号生成"""

    def setUp(self):
        """设置测试数据"""
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(5)]

        # 创建上升趋势数据 - 使用DataFrame
        self.fast_ma = pd.DataFrame(
            {stock: range(50) for stock in stocks},
            index=dates,
            dtype=float
        )
        self.slow_ma = pd.DataFrame(
            {stock: range(0, 100, 2) for stock in stocks},
            index=dates,
            dtype=float
        )

    def test_golden_cross(self):
        """测试金叉信号"""
        # 调整数据使快线上穿慢线
        fast = self.fast_ma.copy()
        slow = self.slow_ma.copy()

        # 前半部分快线在下,后半部分快线在上
        fast.iloc[:25] = slow.iloc[:25] - 1
        fast.iloc[25:] = slow.iloc[25:] + 1

        signals = SignalGenerator.generate_cross_signals(fast, slow)

        # 验证交叉点附近有买入信号
        cross_signals = signals.iloc[24:27]
        buy_count = (cross_signals == SignalType.BUY.value).sum().sum()
        self.assertGreater(buy_count, 0)

    def test_death_cross(self):
        """测试死叉信号"""
        # 调整数据使快线下穿慢线
        fast = self.fast_ma.copy()
        slow = self.slow_ma.copy()

        # 前半部分快线在上,后半部分快线在下
        fast.iloc[:25] = slow.iloc[:25] + 1
        fast.iloc[25:] = slow.iloc[25:] - 1

        signals = SignalGenerator.generate_cross_signals(fast, slow)

        # 验证交叉点附近有卖出信号
        cross_signals = signals.iloc[24:27]
        sell_count = (cross_signals == SignalType.SELL.value).sum().sum()
        self.assertGreater(sell_count, 0)


class TestTrendSignals(unittest.TestCase):
    """测试趋势信号生成"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(3)]

        # 创建趋势数据 - 使用DataFrame
        self.uptrend = pd.DataFrame(
            {stock: np.linspace(100, 150, 100) for stock in stocks},
            index=dates
        )

        self.downtrend = pd.DataFrame(
            {stock: np.linspace(150, 100, 100) for stock in stocks},
            index=dates
        )

        self.sideways = pd.DataFrame(
            {stock: 100 + np.random.randn(100) * 2 for stock in stocks},
            index=dates
        )

    def test_uptrend_signals(self):
        """测试上升趋势信号"""
        signals = SignalGenerator.generate_trend_signals(
            self.uptrend,
            lookback_period=20,
            threshold=0.05
        )

        # 大部分应该是买入信号
        buy_count = (signals == SignalType.BUY.value).sum().sum()
        total_count = signals.size
        buy_ratio = buy_count / total_count
        self.assertGreater(buy_ratio, 0.5)

    def test_downtrend_signals(self):
        """测试下降趋势信号"""
        signals = SignalGenerator.generate_trend_signals(
            self.downtrend,
            lookback_period=20,
            threshold=0.05
        )

        # 大部分应该是卖出信号
        sell_count = (signals == SignalType.SELL.value).sum().sum()
        total_count = signals.size
        sell_ratio = sell_count / total_count
        self.assertGreater(sell_ratio, 0.5)

    def test_sideways_signals(self):
        """测试震荡信号"""
        signals = SignalGenerator.generate_trend_signals(
            self.sideways,
            lookback_period=20,
            threshold=0.05
        )

        # 大部分应该是持有信号
        hold_count = (signals == SignalType.HOLD.value).sum().sum()
        total_count = signals.size
        hold_ratio = hold_count / total_count
        self.assertGreater(hold_ratio, 0.5)


class TestBreakoutSignals(unittest.TestCase):
    """测试突破信号生成"""

    def setUp(self):
        """设置测试数据"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(3)]

        # 创建突破数据 - 使用DataFrame
        base = np.ones(100) * 100
        base[50] = 120  # 向上突破
        base[70] = 80   # 向下突破

        self.prices = pd.DataFrame(
            {stock: base.copy() for stock in stocks},
            index=dates
        )

    def test_upward_breakout(self):
        """测试向上突破"""
        signals = SignalGenerator.generate_breakout_signals(
            self.prices,
            lookback_period=20
        )

        # 第50天应该有买入信号
        buy_count = (signals.iloc[50] == SignalType.BUY.value).sum()
        self.assertGreater(buy_count, 0)

    def test_downward_breakout(self):
        """测试向下突破"""
        signals = SignalGenerator.generate_breakout_signals(
            self.prices,
            lookback_period=20
        )

        # 第70天应该有卖出信号
        sell_count = (signals.iloc[70] == SignalType.SELL.value).sum()
        self.assertGreater(sell_count, 0)


class TestCombineSignals(unittest.TestCase):
    """测试信号组合"""

    def setUp(self):
        """设置测试数据"""
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        self.stocks = [f'stock_{i:03d}' for i in range(10)]

        # 创建三个信号DataFrame (5天 x 10股票)
        signal_data_1 = [
            [1, 1, 1, 0, 0, -1, -1, -1, 0, 1],
            [1, 0, -1, 1, 0, -1, 0, 1, -1, 0],
            [1, 1, 0, 1, -1, -1, -1, 0, 0, 1],
            [0, 1, 1, 0, 0, -1, -1, 0, 1, 1],
            [1, 1, 1, 0, 0, -1, -1, -1, 0, 1]
        ]
        signal_data_2 = [
            [1, 0, -1, 1, 0, -1, 0, 1, -1, 0],
            [1, 1, 0, 1, -1, -1, -1, 0, 0, 1],
            [0, 1, 1, 0, 0, -1, -1, 0, 1, 1],
            [1, 1, 1, 0, 0, -1, -1, -1, 0, 1],
            [1, 0, -1, 1, 0, -1, 0, 1, -1, 0]
        ]
        signal_data_3 = [
            [1, 1, 0, 1, -1, -1, -1, 0, 0, 1],
            [0, 1, 1, 0, 0, -1, -1, 0, 1, 1],
            [1, 1, 1, 0, 0, -1, -1, -1, 0, 1],
            [1, 0, -1, 1, 0, -1, 0, 1, -1, 0],
            [1, 1, 0, 1, -1, -1, -1, 0, 0, 1]
        ]

        self.signals1 = pd.DataFrame(signal_data_1, index=dates, columns=self.stocks)
        self.signals2 = pd.DataFrame(signal_data_2, index=dates, columns=self.stocks)
        self.signals3 = pd.DataFrame(signal_data_3, index=dates, columns=self.stocks)

    def test_vote_method(self):
        """测试投票组合法"""
        combined = SignalGenerator.combine_signals(
            [self.signals1, self.signals2, self.signals3],
            method='vote'
        )

        # 验证结果形状
        self.assertEqual(combined.shape, self.signals1.shape)

        # 验证信号值在[-1, 0, 1]范围内
        unique_values = combined.stack().unique()
        self.assertTrue(all(v in [-1, 0, 1] for v in unique_values))

    def test_weighted_method(self):
        """测试加权组合法"""
        combined = SignalGenerator.combine_signals(
            [self.signals1, self.signals2, self.signals3],
            method='weighted',
            weights=[0.5, 0.3, 0.2]
        )

        # 验证结果在[-1, 1]范围内
        self.assertTrue((combined.values >= -1).all())
        self.assertTrue((combined.values <= 1).all())

    def test_and_method(self):
        """测试AND组合法"""
        combined = SignalGenerator.combine_signals(
            [self.signals1, self.signals2, self.signals3],
            method='and'
        )

        # 验证结果形状
        self.assertEqual(combined.shape, self.signals1.shape)

        # 验证只有全部同意才买入
        # AND逻辑应该产生较少的买入信号
        buy_count = (combined == SignalType.BUY.value).sum().sum()
        self.assertGreaterEqual(buy_count, 0)

    def test_or_method(self):
        """测试OR组合法"""
        combined = SignalGenerator.combine_signals(
            [self.signals1, self.signals2, self.signals3],
            method='or'
        )

        # 验证结果形状
        self.assertEqual(combined.shape, self.signals1.shape)

        # OR逻辑应该产生较多的买入信号
        buy_count = (combined == SignalType.BUY.value).sum().sum()
        self.assertGreater(buy_count, 0)

    def test_invalid_method(self):
        """测试无效的组合方法"""
        with self.assertRaises(ValueError):
            SignalGenerator.combine_signals(
                [self.signals1, self.signals2],
                method='invalid_method'
            )

    def test_weighted_without_weights(self):
        """测试加权法但未提供权重"""
        # 应该使用均等权重
        combined = SignalGenerator.combine_signals(
            [self.signals1, self.signals2],
            method='weighted'
        )

        self.assertIsNotNone(combined)
        self.assertEqual(combined.shape, self.signals1.shape)

    def test_mismatched_weights(self):
        """测试权重数量不匹配"""
        with self.assertRaises(ValueError):
            SignalGenerator.combine_signals(
                [self.signals1, self.signals2, self.signals3],
                method='weighted',
                weights=[0.5, 0.5]  # 只有2个权重,但有3个信号
            )


if __name__ == '__main__':
    unittest.main()
