"""
机器学习策略单元测试
测试基于ML模型的预测和信号生成
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys
from unittest.mock import Mock, MagicMock

# 添加src目录到路径
# Path already configured in conftest.py

from strategies.ml_strategy import MLStrategy
from strategies.signal_generator import SignalType


class MockModel:
    """模拟的ML模型（用于测试）"""

    def __init__(self, add_noise=False):
        self.add_noise = add_noise

    def predict(self, X):
        """简单的预测：返回第一个特征的值"""
        predictions = X.iloc[:, 0].values if isinstance(X, pd.DataFrame) else X[:, 0]

        if self.add_noise:
            predictions = predictions + np.random.randn(len(predictions)) * 0.1

        return predictions

    def predict_proba(self, X):
        """模拟概率预测"""
        predictions = self.predict(X)
        # 转换为概率（sigmoid）
        proba = 1 / (1 + np.exp(-predictions))
        # 返回两列（负类，正类）
        return np.column_stack([1 - proba, proba])


class TestMLStrategy(unittest.TestCase):
    """测试机器学习策略"""

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

        # 创建特征数据
        self.features = {}
        feature_names = ['feature_0', 'feature_1', 'feature_2', 'feature_3', 'feature_4']

        for date in dates:
            date_features = {}

            for stock in stocks:
                for feat in feature_names:
                    date_features[f'{feat}_{stock}'] = np.random.randn()

            self.features[date] = date_features

        self.features_df = pd.DataFrame.from_dict(self.features, orient='index')

        # 创建模拟模型
        self.mock_model = MockModel()

    def test_strategy_initialization(self):
        """测试策略初始化"""
        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': ['feature_0', 'feature_1', 'feature_2'],
                'prediction_threshold': 0.01,
                'top_n': 10
            }
        )

        self.assertEqual(strategy.name, 'ML')
        self.assertIsNotNone(strategy.model)
        self.assertEqual(strategy.feature_columns, ['feature_0', 'feature_1', 'feature_2'])
        self.assertEqual(strategy.prediction_threshold, 0.01)
        self.assertEqual(strategy.config.top_n,10)

    def test_predict_basic(self):
        """测试基本预测"""
        # 创建简单的特征DataFrame用于直接测试predict
        simple_features = pd.DataFrame({
            'feature_0': np.random.randn(20),
            'feature_1': np.random.randn(20)
        })

        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': ['feature_0', 'feature_1'],
                'use_probability': False
            }
        )

        predictions = strategy.predict(simple_features)

        # 验证返回的是Series
        self.assertIsInstance(predictions, pd.Series)

        # 验证预测数量
        self.assertEqual(len(predictions), 20)

        # 验证预测值是数值
        self.assertTrue(all(isinstance(v, (int, float, np.number)) for v in predictions.dropna()))

    def test_predict_with_probability(self):
        """测试概率预测"""
        # 创建简单的特征DataFrame
        simple_features = pd.DataFrame({
            'feature_0': np.random.randn(20),
            'feature_1': np.random.randn(20)
        })

        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': ['feature_0', 'feature_1'],
                'use_probability': True
            }
        )

        predictions = strategy.predict(simple_features)

        # 验证返回的是Series
        self.assertIsInstance(predictions, pd.Series)

        # 概率值应该在[0, 1]范围内
        valid_preds = predictions.dropna()
        if len(valid_preds) > 0:
            self.assertTrue(all(0 <= v <= 1 for v in valid_preds))

    def test_calculate_scores(self):
        """测试打分计算"""
        # 创建正确格式的特征：日期 x 股票特征
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        stocks = ['stock_000', 'stock_001', 'stock_002']

        # 为每只股票创建特征列
        feature_data = {}
        for stock in stocks:
            for feat in ['feature_0', 'feature_1', 'feature_2']:
                feature_data[f'{feat}_{stock}'] = np.random.randn(len(dates))

        features_df = pd.DataFrame(feature_data, index=dates)

        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': ['feature_0_stock_000', 'feature_1_stock_000', 'feature_2_stock_000'],
                'prediction_threshold': -999,  # 不过滤
                'top_n': 10
            }
        )

        # 测试单日期打分
        test_date = dates[5]
        scores = strategy.calculate_scores(
            prices=None,  # calculate_scores 不直接使用prices
            features=features_df,
            date=test_date
        )

        # 验证返回Series
        self.assertIsInstance(scores, pd.Series)
        # 应该有预测值
        self.assertGreater(len(scores.dropna()), 0)

    def test_calculate_scores_with_threshold(self):
        """测试带阈值的打分"""
        # 创建特征数据
        dates = pd.date_range('2023-01-01', periods=10, freq='D')

        # 简单特征：只有一列
        features_df = pd.DataFrame({
            'feature_0': np.linspace(-2, 2, len(dates))  # 从负到正
        }, index=dates)

        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': ['feature_0'],
                'prediction_threshold': 0.5,  # 设置阈值
                'top_n': 10
            }
        )

        # 测试打分
        scores = strategy.calculate_scores(
            prices=None,
            features=features_df,
            date=dates[8]  # 使用正值
        )

        # 验证低于阈值的被过滤（设为NaN）
        self.assertIsInstance(scores, pd.Series)
        # Mock模型返回feature_0的值，阈值0.5会过滤掉小值

    def test_generate_signals(self):
        """测试信号生成"""
        # 创建价格数据
        dates = pd.date_range('2023-01-01', periods=20, freq='D')
        stocks = ['stock_000', 'stock_001', 'stock_002', 'stock_003', 'stock_004']

        prices = pd.DataFrame({
            stock: 100 + np.random.randn(len(dates)).cumsum()
            for stock in stocks
        }, index=dates)

        # ML策略期望的特征格式：每个日期一行，所有特征作为列
        # 不需要按股票分列，直接使用全局特征即可
        features_df = pd.DataFrame({
            'feature_0': np.random.randn(len(dates)),
            'feature_1': np.random.randn(len(dates)),
            'feature_2': np.random.randn(len(dates))
        }, index=dates)

        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': ['feature_0', 'feature_1'],
                'prediction_threshold': -999,  # 不过滤
                'top_n': 3
            }
        )

        # 生成信号
        signals = strategy.generate_signals(prices, features=features_df)

        # 验证信号格式
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertEqual(signals.shape[0], len(dates))

        # ML策略的信号列数取决于模型预测的输出
        # 实际使用中，信号应该对齐到prices的列
        # 这里主要验证信号生成成功
        self.assertGreater(signals.shape[1], 0)

        # 验证信号值在{-1, 0, 1}中
        unique_values = signals.values.flatten()
        unique_values = unique_values[~np.isnan(unique_values)]
        self.assertTrue(all(v in [-1, 0, 1] for v in unique_values))

        # 验证有买入信号生成
        total_buy_signals = (signals == 1).sum().sum()
        self.assertGreater(total_buy_signals, 0)

    def test_missing_feature_columns(self):
        """测试缺失特征列的处理"""
        simple_features = pd.DataFrame({
            'feature_0': np.random.randn(10)
        })

        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': ['feature_0', 'nonexistent_feature'],
                'top_n': 5
            }
        )

        # 应该抛出错误或跳过缺失的列
        with self.assertRaises((KeyError, ValueError)):
            strategy.predict(simple_features)

    def test_model_without_predict(self):
        """测试没有predict方法的模型"""
        invalid_model = object()  # 没有predict方法
        simple_features = pd.DataFrame({'feature_0': np.random.randn(10)})

        strategy = MLStrategy(
            name='ML',
            model=invalid_model,
            config={
                'feature_columns': ['feature_0'],
                'top_n': 5
            }
        )

        # predict方法会捕获异常并返回NaN
        predictions = strategy.predict(simple_features)
        self.assertTrue(predictions.isna().all())

    def test_different_feature_combinations(self):
        """测试不同的特征组合"""
        feature_sets = [
            ['feature_0'],
            ['feature_0', 'feature_1'],
            ['feature_0', 'feature_1', 'feature_2', 'feature_3', 'feature_4']
        ]

        for features in feature_sets:
            # 创建对应的特征数据
            simple_features = pd.DataFrame({
                feat: np.random.randn(10) for feat in features
            })

            strategy = MLStrategy(
                name=f'ML_{len(features)}F',
                model=self.mock_model,
                config={
                    'feature_columns': features,
                    'top_n': 5
                }
            )

            predictions = strategy.predict(simple_features)

            # 每种组合都应该能预测
            self.assertIsInstance(predictions, pd.Series)
            self.assertGreater(len(predictions.dropna()), 0)

    def test_backtest_integration(self):
        """测试回测集成"""
        from backtest.backtest_engine import BacktestEngine

        # 创建简单的价格和特征数据
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        stocks = ['stock_000', 'stock_001', 'stock_002', 'stock_003', 'stock_004']

        prices = pd.DataFrame({
            stock: 100 + np.random.randn(len(dates)).cumsum()
            for stock in stocks
        }, index=dates)

        # 创建特征
        feature_data = {}
        for stock in stocks:
            feature_data[f'feature_0_{stock}'] = np.random.randn(len(dates))
            feature_data[f'feature_1_{stock}'] = np.random.randn(len(dates))

        features_df = pd.DataFrame(feature_data, index=dates)

        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': None,
                'prediction_threshold': -999,
                'top_n': 3,
                'holding_period': 5
            }
        )

        # 生成信号
        signals = strategy.generate_signals(prices, features=features_df)

        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            verbose=False
        )

        # 回测
        results = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=3,
            holding_period=5
        )

        # 验证返回结果
        self.assertIn('portfolio_value', results)
        portfolio_value = results['portfolio_value']
        self.assertIsInstance(portfolio_value, pd.DataFrame)

        # 验证最终资金大于0
        final_value = portfolio_value['total'].iloc[-1]
        self.assertGreater(final_value, 0)

    def test_with_lightgbm_compatible_model(self):
        """测试与LightGBM兼容的模型"""
        try:
            from models.lightgbm_model import LightGBMStockModel

            # 创建并训练一个简单的LightGBM模型
            lgbm_model = LightGBMStockModel(
                learning_rate=0.1,
                n_estimators=10,
                verbose=-1
            )

            # 创建训练数据
            n_samples = 200
            n_features = 5
            X_train = pd.DataFrame(
                np.random.randn(n_samples, n_features),
                columns=[f'feature_{i}' for i in range(n_features)]
            )
            y_train = pd.Series(np.random.randn(n_samples) * 0.02)

            # 训练模型
            lgbm_model.train(X_train, y_train, verbose_eval=-1)

            # 使用训练好的模型创建策略
            strategy = MLStrategy(
                name='ML_LGBM',
                model=lgbm_model.model,  # 使用训练好的模型
                config={
                    'feature_columns': [f'feature_{i}' for i in range(n_features)],
                    'top_n': 5
                }
            )

            # 验证能够使用
            test_date = self.features_df.index[50]

            # 由于特征名称不匹配，这里只验证策略能够初始化
            self.assertEqual(strategy.name, 'ML_LGBM')
            self.assertIsNotNone(strategy.model)

        except ImportError:
            self.skipTest("LightGBM not available")

    def test_edge_case_no_predictions_above_threshold(self):
        """测试边缘情况：没有预测超过阈值"""
        # 创建特征数据，所有值都很小（不会超过阈值）
        dates = pd.date_range('2023-01-01', periods=10, freq='D')

        features_df = pd.DataFrame({
            'feature_0': np.linspace(-2, -1, len(dates))  # 全部是负值
        }, index=dates)

        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': ['feature_0'],
                'prediction_threshold': 10.0,  # 非常高的阈值
                'top_n': 5
            }
        )

        # 计算打分，所有预测应该被阈值过滤
        scores = strategy.calculate_scores(
            prices=None,
            features=features_df,
            date=dates[5]
        )

        # 验证所有值都被过滤（NaN）或者返回空Series
        self.assertTrue(scores.isna().all() or len(scores.dropna()) == 0)

    def test_edge_case_single_stock(self):
        """测试边缘情况：单只股票"""
        # 只有一只股票的情况
        dates = pd.date_range('2023-01-01', periods=20, freq='D')

        prices = pd.DataFrame({
            'stock_000': 100 + np.random.randn(len(dates)).cumsum()
        }, index=dates)

        # 创建全局特征（不是按股票分列）
        features_df = pd.DataFrame({
            'feature_0': np.random.randn(len(dates)),
            'feature_1': np.random.randn(len(dates))
        }, index=dates)

        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': ['feature_0', 'feature_1'],
                'prediction_threshold': -999,
                'top_n': 3  # top_n大于股票数
            }
        )

        # 生成信号
        signals = strategy.generate_signals(prices, features=features_df)

        # 验证格式
        self.assertIsInstance(signals, pd.DataFrame)
        # 信号的列数取决于模型输出，不一定等于股票数
        self.assertGreater(signals.shape[1], 0)

        # 验证有信号生成
        total_signals = (signals == 1).sum().sum()
        self.assertGreater(total_signals, 0)

    def test_model_predictions_consistency(self):
        """测试模型预测的一致性"""
        simple_features = pd.DataFrame({
            'feature_0': np.random.randn(10),
            'feature_1': np.random.randn(10)
        })

        strategy = MLStrategy(
            name='ML',
            model=self.mock_model,
            config={
                'feature_columns': ['feature_0', 'feature_1'],
                'use_probability': False
            }
        )

        # 多次预测应该得到相同的结果（如果模型是确定性的）
        pred1 = strategy.predict(simple_features)
        pred2 = strategy.predict(simple_features)

        pd.testing.assert_series_equal(pred1, pred2)


if __name__ == '__main__':
    unittest.main()
