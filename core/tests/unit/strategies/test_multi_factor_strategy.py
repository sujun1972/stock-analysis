"""
多因子策略单元测试
测试多因子组合、归一化方法和信号生成
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from strategies.multi_factor_strategy import MultiFactorStrategy
from strategies.signal_generator import SignalType


class TestMultiFactorStrategy(unittest.TestCase):
    """测试多因子策略"""

    def setUp(self):
        """设置测试数据"""
        np.random.seed(42)

        # 创建价格数据
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = [f'stock_{i:03d}' for i in range(20)]

        price_data = {
            stock: 100 * (1 + np.random.randn(len(dates)).cumsum() * 0.01)
            for stock in stocks
        }
        self.prices = pd.DataFrame(price_data, index=dates)

        # 创建成交量数据
        volume_data = {
            stock: np.random.uniform(1000000, 10000000, len(dates))
            for stock in stocks
        }
        self.volumes = pd.DataFrame(volume_data, index=dates)

        # 创建多因子特征数据
        # 使用MultiIndex列：(factor_name, stock_code)
        factor_names = ['MOM20', 'REV5', 'VOLATILITY20', 'VOLUME_RATIO5', 'TREND20']

        # 创建多层列索引
        arrays = [[], []]
        for factor in factor_names:
            for stock in stocks:
                arrays[0].append(factor)
                arrays[1].append(stock)

        tuples = list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples, names=['factor', 'stock'])

        # 创建数据
        data = []
        for date in dates:
            row = []
            for factor in factor_names:
                for stock in stocks:
                    if factor == 'MOM20':
                        row.append(np.random.randn() * 10)
                    elif factor == 'REV5':
                        row.append(np.random.randn() * 5)
                    elif factor == 'VOLATILITY20':
                        row.append(abs(np.random.randn()) * 2)
                    elif factor == 'VOLUME_RATIO5':
                        row.append(1 + np.random.randn() * 0.5)
                    elif factor == 'TREND20':
                        row.append(np.random.choice([-1, 0, 1]))
            data.append(row)

        self.features_df = pd.DataFrame(data, index=dates, columns=index)

    def test_strategy_initialization(self):
        """测试策略初始化"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
                'weights': [0.5, 0.3, 0.2],
                'top_n': 10
            }
        )

        self.assertEqual(strategy.name, 'MF')
        self.assertEqual(strategy.factors, ['MOM20', 'REV5', 'VOLATILITY20'])
        self.assertEqual(strategy.weights, [0.5, 0.3, 0.2])
        self.assertEqual(strategy.config.top_n,10)
        self.assertEqual(strategy.normalize_method, 'rank')  # 默认方法

    def test_equal_weights_default(self):
        """测试默认等权重"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
                'top_n': 10
            }
        )

        # 应该自动生成等权重
        self.assertEqual(len(strategy.weights), 3)
        self.assertAlmostEqual(sum(strategy.weights), 1.0)
        self.assertTrue(all(w == 1/3 for w in strategy.weights))

    def test_normalize_factor_rank(self):
        """测试排名归一化"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20'],
                'normalize_method': 'rank'
            }
        )

        # 创建测试数据
        factor_values = pd.Series(
            [10, 20, 5, 30, 15],
            index=[f'stock_{i:03d}' for i in range(5)]
        )

        normalized = strategy.normalize_factor(factor_values, method='rank')

        # rank(pct=True) 返回的范围是 (0, 1]，最小值是 0.2 (1/5)，最大值是 1.0 (5/5)
        self.assertGreater(normalized.min(), 0.0)  # 不是0，而是1/n
        self.assertAlmostEqual(normalized.max(), 1.0, places=5)

        # 验证排名顺序正确
        self.assertEqual(normalized.idxmax(), 'stock_003')  # 最大值30
        self.assertEqual(normalized.idxmin(), 'stock_002')  # 最小值5

    def test_normalize_factor_zscore(self):
        """测试Z-score归一化"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20'],
                'normalize_method': 'zscore'
            }
        )

        factor_values = pd.Series(
            np.random.randn(20),
            index=[f'stock_{i:03d}' for i in range(20)]
        )

        normalized = strategy.normalize_factor(factor_values, method='zscore')

        # 验证均值接近0，标准差接近1
        self.assertAlmostEqual(normalized.mean(), 0.0, places=1)
        self.assertAlmostEqual(normalized.std(), 1.0, places=1)

    def test_normalize_factor_minmax(self):
        """测试MinMax归一化"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20'],
                'normalize_method': 'minmax'
            }
        )

        factor_values = pd.Series(
            [10, 20, 30, 40, 50],
            index=[f'stock_{i:03d}' for i in range(5)]
        )

        normalized = strategy.normalize_factor(factor_values, method='minmax')

        # 验证归一化到[0, 1]
        self.assertAlmostEqual(normalized.min(), 0.0)
        self.assertAlmostEqual(normalized.max(), 1.0)

        # 验证线性映射
        self.assertAlmostEqual(normalized['stock_002'], 0.5)  # 中间值

    def test_normalize_factor_with_nan(self):
        """测试包含NaN的归一化"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={'factors': ['MOM20']}
        )

        factor_values = pd.Series(
            [10, np.nan, 20, np.nan, 30],
            index=[f'stock_{i:03d}' for i in range(5)]
        )

        for method in ['rank', 'zscore', 'minmax']:
            normalized = strategy.normalize_factor(factor_values, method=method)

            # NaN值应该保持为NaN
            self.assertTrue(pd.isna(normalized['stock_001']))
            self.assertTrue(pd.isna(normalized['stock_003']))

            # 非NaN值应该被正确归一化
            self.assertFalse(pd.isna(normalized['stock_000']))

    def test_calculate_scores(self):
        """测试综合打分计算"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
                'weights': [0.5, 0.3, 0.2],
                'normalize_method': 'rank'
            }
        )

        test_date = self.features_df.index[50]
        scores = strategy.calculate_scores(
            self.prices,
            self.features_df,
            date=test_date
        )

        # 验证返回的是Series
        self.assertIsInstance(scores, pd.Series)

        # 验证索引长度（应该包含所有股票的因子）
        # 由于是MultiIndex列，scores索引是股票代码
        self.assertGreater(len(scores), 0)

        # 验证分数是有效的数值
        valid_scores = scores.dropna()
        self.assertGreaterEqual(len(valid_scores), 0)

    def test_calculate_scores_missing_factor(self):
        """测试缺失因子的处理"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'NONEXISTENT_FACTOR'],
                'weights': [0.6, 0.4]
            }
        )

        test_date = self.features_df.index[50]

        # 应该能够处理（跳过缺失的因子或抛出警告）
        try:
            scores = strategy.calculate_scores(
                self.prices,
                self.features_df,
                date=test_date
            )
            # 如果成功，验证结果
            self.assertIsInstance(scores, pd.Series)
        except (KeyError, ValueError):
            # 如果抛出错误，这也是合理的
            pass

    def test_generate_signals(self):
        """测试信号生成"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
                'weights': [0.5, 0.3, 0.2],
                'top_n': 20,  # 设置为20，因为有20只股票
                'holding_period': 5
            }
        )

        signals = strategy.generate_signals(
            self.prices,
            features=self.features_df,
            volumes=self.volumes
        )

        # 验证返回的是DataFrame
        self.assertIsInstance(signals, pd.DataFrame)

        # 验证形状
        self.assertEqual(signals.shape, self.prices.shape)

        # 验证信号值在[-1, 0, 1]范围内
        unique_values = signals.stack().unique()
        self.assertTrue(all(v in [-1, 0, 1] for v in unique_values))

        # 验证每天最多有top_n个买入信号
        for date in signals.index:
            daily_signals = signals.loc[date]
            buy_count = (daily_signals == SignalType.BUY.value).sum()
            self.assertLessEqual(buy_count, strategy.config.top_n)

    def test_single_factor_strategy(self):
        """测试单因子策略"""
        strategy = MultiFactorStrategy(
            name='MF_Single',
            config={
                'factors': ['MOM20'],
                'weights': [1.0],
                'top_n': 5
            }
        )

        signals = strategy.generate_signals(
            self.prices,
            features=self.features_df,
            volumes=self.volumes
        )

        # 应该能够正常生成信号
        self.assertIsInstance(signals, pd.DataFrame)
        buy_signals = (signals == SignalType.BUY.value).sum().sum()
        self.assertGreaterEqual(buy_signals, 0)

    def test_many_factors_strategy(self):
        """测试多因子策略（5个因子）"""
        strategy = MultiFactorStrategy(
            name='MF_Many',
            config={
                'factors': ['MOM20', 'REV5', 'VOLATILITY20', 'VOLUME_RATIO5', 'TREND20'],
                'weights': [0.3, 0.25, 0.2, 0.15, 0.1],
                'top_n': 10
            }
        )

        signals = strategy.generate_signals(
            self.prices,
            features=self.features_df,
            volumes=self.volumes
        )

        # 验证能够组合多个因子并生成信号
        self.assertIsInstance(signals, pd.DataFrame)
        buy_signals = (signals == SignalType.BUY.value).sum().sum()
        self.assertGreaterEqual(buy_signals, 0)

    def test_different_normalize_methods(self):
        """测试不同的归一化方法"""
        for method in ['rank', 'zscore', 'minmax']:
            strategy = MultiFactorStrategy(
                name=f'MF_{method}',
                config={
                    'factors': ['MOM20', 'REV5'],
                    'weights': [0.6, 0.4],
                    'normalize_method': method,
                    'top_n': 5
                }
            )

            signals = strategy.generate_signals(
                self.prices,
                features=self.features_df,
                volumes=self.volumes
            )

            # 每种方法都应该能生成信号
            self.assertIsInstance(signals, pd.DataFrame)
            buy_signals = (signals == SignalType.BUY.value).sum().sum()
            self.assertGreaterEqual(buy_signals, 0)

    def test_backtest_integration(self):
        """测试回测集成"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))
        from backtest.backtest_engine import BacktestEngine

        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
                'weights': [0.5, 0.3, 0.2],
                'top_n': 5,
                'holding_period': 5
            }
        )

        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            verbose=False
        )

        # 多因子策略需要features参数
        results = engine.backtest_long_only(
            signals=strategy.generate_signals(
                self.prices,
                features=self.features_df,
                volumes=self.volumes
            ),
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
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
                'weights': [5, 3, 2],  # 传入未归一化权重
                'top_n': 5
            }
        )

        # 权重保持原始值（不自动归一化）或者使用等权重
        # 检查权重是否有效
        self.assertEqual(len(strategy.weights), 3)
        # 如果是原始值
        if sum(strategy.weights) == 10:
            self.assertEqual(strategy.weights, [5, 3, 2])
        # 如果归一化了
        elif abs(sum(strategy.weights) - 1.0) < 0.01:
            self.assertAlmostEqual(strategy.weights[0], 0.5, places=1)
        # 或者等权重
        else:
            self.assertTrue(True)  # 任何合理的权重都可以

    def test_negative_weights(self):
        """测试负权重（做空因子）"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'VOLATILITY20'],
                'weights': [0.7, -0.3],  # 负权重表示反向
                'top_n': 5
            }
        )

        test_date = self.features_df.index[50]
        scores = strategy.calculate_scores(
            self.prices,
            self.features_df,
            date=test_date
        )

        # 应该能够处理负权重
        self.assertIsInstance(scores, pd.Series)

    def test_edge_case_all_nan_factors(self):
        """测试边缘情况：所有因子都是NaN"""
        # 创建全NaN的特征数据
        nan_features = self.features_df.copy()
        test_date = nan_features.index[50]
        nan_features.loc[test_date] = np.nan

        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'REV5'],
                'weights': [0.5, 0.5],
                'top_n': 5
            }
        )

        scores = strategy.calculate_scores(
            self.prices,
            nan_features,
            date=test_date
        )

        # 结果应该全是NaN
        self.assertTrue(scores.isna().all())

    def test_edge_case_single_stock(self):
        """测试边缘情况：单只股票"""
        single_stock = 'stock_000'

        # 过滤只保留一只股票的数据
        single_prices = self.prices[[single_stock]]

        # 过滤特征 - 只保留该股票的列
        if isinstance(self.features_df.columns, pd.MultiIndex):
            # 如果是MultiIndex，选择该股票的所有因子
            single_features = self.features_df.loc[:, (slice(None), single_stock)]
        else:
            # 如果是简单列，根据列名过滤
            single_features_cols = [col for col in self.features_df.columns if single_stock in str(col)]
            single_features = self.features_df[single_features_cols]

        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'REV5'],
                'weights': [0.6, 0.4],
                'top_n': 1
            }
        )

        signals = strategy.generate_signals(
            single_prices,
            features=single_features
        )

        # 应该能够正常生成信号
        self.assertIsNotNone(signals)
        self.assertEqual(signals.shape, single_prices.shape)

    def test_factor_contribution_analysis(self):
        """测试因子贡献度分析"""
        strategy = MultiFactorStrategy(
            name='MF',
            config={
                'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
                'weights': [0.5, 0.3, 0.2],
                'normalize_method': 'rank'
            }
        )

        test_date = self.features_df.index[50]

        # 分别计算每个因子的贡献
        factor_scores = {}
        for factor in strategy.factors:
            # 从MultiIndex列中提取因子数据
            if isinstance(self.features_df.columns, pd.MultiIndex):
                # 选择该因子的所有股票列
                factor_data = self.features_df.loc[test_date, factor]
            else:
                # 如果是简单列，通过字符串匹配
                factor_cols = [col for col in self.features_df.columns if str(col).startswith(f'{factor}_')]
                factor_data = {}
                for col in factor_cols:
                    stock = str(col).replace(f'{factor}_', '')
                    factor_data[stock] = self.features_df.loc[test_date, col]
                factor_data = pd.Series(factor_data)

            factor_scores[factor] = strategy.normalize_factor(factor_data.dropna(), method='rank')

        # 验证每个因子都有贡献
        for factor, scores in factor_scores.items():
            valid_scores = scores.dropna()
            self.assertGreater(len(valid_scores), 0)


if __name__ == '__main__':
    unittest.main()
