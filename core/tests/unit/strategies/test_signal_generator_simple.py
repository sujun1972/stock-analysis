"""
信号生成器简化测试
测试SignalGenerator的核心功能
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from strategies.signal_generator import SignalType, SignalGenerator


class TestSignalGenerator(unittest.TestCase):
    """测试信号生成器基本功能"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)
        self.dates = pd.date_range('2023-01-01', periods=20, freq='D')
        self.stocks = [f'stock_{i:03d}' for i in range(10)]

        # 创建评分DataFrame (dates x stocks)
        self.scores = pd.DataFrame(
            np.random.randn(len(self.dates), len(self.stocks)),
            index=self.dates,
            columns=self.stocks
        )

    def test_signal_type_enum(self):
        """测试信号类型枚举"""
        self.assertEqual(SignalType.BUY.value, 1)
        self.assertEqual(SignalType.HOLD.value, 0)
        self.assertEqual(SignalType.SELL.value, -1)

    def test_generate_threshold_signals(self):
        """测试阈值信号生成"""
        signals = SignalGenerator.generate_threshold_signals(
            self.scores,
            buy_threshold=0.5,
            sell_threshold=-0.5
        )

        # 验证返回DataFrame
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertEqual(signals.shape, self.scores.shape)

        # 验证信号值
        unique_values = signals.stack().unique()
        self.assertTrue(all(v in [-1, 0, 1] for v in unique_values))

    def test_generate_rank_signals(self):
        """测试排名信号生成"""
        signals = SignalGenerator.generate_rank_signals(
            self.scores,
            top_n=3,
            bottom_n=2
        )

        # 验证每天的买入信号数量
        for date in signals.index:
            buy_count = (signals.loc[date] == SignalType.BUY.value).sum()
            sell_count = (signals.loc[date] == SignalType.SELL.value).sum()

            self.assertEqual(buy_count, 3)
            self.assertEqual(sell_count, 2)

    def test_combine_signals_vote(self):
        """测试信号组合-投票法"""
        # 创建两个信号序列
        signal1 = pd.DataFrame(1, index=self.dates, columns=self.stocks)
        signal2 = pd.DataFrame(-1, index=self.dates, columns=self.stocks)

        combined = SignalGenerator.combine_signals(
            [signal1, signal2],
            method='vote'
        )

        # 投票应该产生某种结果
        self.assertIsInstance(combined, pd.DataFrame)
        self.assertEqual(combined.shape, signal1.shape)

    def test_combine_signals_weighted(self):
        """测试信号组合-加权法"""
        signal1 = pd.DataFrame(1, index=self.dates, columns=self.stocks)
        signal2 = pd.DataFrame(-1, index=self.dates, columns=self.stocks)

        combined = SignalGenerator.combine_signals(
            [signal1, signal2],
            method='weighted',
            weights=[0.7, 0.3]
        )

        # 验证加权结果
        self.assertIsInstance(combined, pd.DataFrame)

        # 0.7 * 1 + 0.3 * (-1) = 0.4, which is between -0.5 and 0.5, so becomes HOLD (0)
        self.assertEqual(combined.iloc[0, 0], SignalType.HOLD.value)


if __name__ == '__main__':
    unittest.main()
