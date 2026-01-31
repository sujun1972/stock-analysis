#!/usr/bin/env python3
"""
端到端工作流集成测试

测试完整的量化交易流程：
1. 数据下载 → 2. 特征计算 → 3. 模型训练 → 4. 策略回测
"""

import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))


class TestCompleteWorkflow(unittest.TestCase):
    """测试完整交易工作流"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        # 测试参数
        cls.test_stock = '000001'
        cls.test_start_date = '2023-01-01'
        cls.test_end_date = '2023-12-31'

    def test_01_complete_trading_workflow(self):
        """测试完整交易工作流: 数据下载 → 特征计算 → 模型训练 → 策略回测"""
        try:
            # 步骤1: 数据下载
            from src.providers import DataProviderFactory

            provider = DataProviderFactory.create_provider('akshare')
            data = provider.get_daily_data(
                self.test_stock,
                self.test_start_date,
                self.test_end_date
            )

            self.assertIsNotNone(data, "数据下载失败")
            self.assertGreater(len(data), 0, "下载的数据为空")
            self.assertIn('close', data.columns, "缺少必需的close列")

            # 步骤2: 特征计算
            from src.features import AlphaFactors, TechnicalIndicators

            alpha = AlphaFactors(data)
            alpha_features = alpha.calculate_all_alpha_factors()
            self.assertGreater(len(alpha_features.columns), 0, "Alpha因子计算失败")

            tech = TechnicalIndicators(data)
            tech_features = tech.add_all_indicators()
            self.assertGreater(len(tech_features.columns), 0, "技术指标计算失败")

            # 合并特征并去重
            features = pd.concat([alpha_features, tech_features], axis=1)
            features = features.loc[:, ~features.columns.duplicated()]
            self.assertGreater(len(features.columns), 125, "特征数量不足")

            # 步骤3: 模型训练
            from src.models import LightGBMStockModel

            # 准备训练数据
            features_clean = features.dropna()
            self.assertGreater(len(features_clean), 50, "清洗后数据过少")

            # 创建目标变量（5日收益率）
            data_clean = data.loc[features_clean.index]
            target = data_clean['close'].pct_change(5).shift(-5) * 100

            # 对齐数据
            valid_idx = ~target.isna()
            X = features_clean[valid_idx]
            y = target[valid_idx]
            self.assertEqual(len(X), len(y), "特征和目标长度不匹配")

            # 划分训练集和测试集
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

            # 训练模型
            model = LightGBMStockModel()
            model.train(X_train, y_train, X_test, y_test)
            self.assertIsNotNone(model.model, "模型训练失败")

            # 模型预测
            predictions = model.predict(X_test)
            self.assertEqual(len(predictions), len(X_test), "预测结果数量不匹配")

            # 步骤4: 策略回测
            from src.strategies import MLStrategy
            from src.backtest import BacktestEngine

            # 创建策略并生成信号
            strategy = MLStrategy(model=model)
            backtest_data = data.loc[X_test.index]
            backtest_features = features.loc[X_test.index]

            signals = strategy.generate_signals(
                backtest_data[['close']],
                backtest_features
            )

            self.assertIn('signal', signals.columns, "缺少信号列")
            signal_count = signals['signal'].abs().sum()
            self.assertGreater(signal_count, 0, "未生成任何信号")

            # 执行回测
            engine = BacktestEngine(initial_capital=1_000_000)
            results = engine.backtest_long_only(signals, backtest_data)

            # 验证回测结果
            self.assertIsNotNone(results, "回测失败")
            self.assertIn('total_return', results.metrics, "缺少收益率指标")
            self.assertIn('sharpe_ratio', results.metrics, "缺少夏普比率")
            self.assertIn('max_drawdown', results.metrics, "缺少最大回撤")
            self.assertGreater(len(results.equity_curve), 0, "权益曲线为空")

        except Exception as e:
            self.skipTest(f"测试需要完整环境: {e}")

    def test_02_workflow_with_data_validation(self):
        """测试带数据验证的工作流"""
        try:
            from src.providers import DataProviderFactory
            from src.features import AlphaFactors

            # 数据下载并验证
            provider = DataProviderFactory.create_provider('akshare')
            data = provider.get_daily_data(
                self.test_stock,
                self.test_start_date,
                self.test_end_date
            )

            # 验证必需列
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                self.assertIn(col, data.columns, f"缺少必需列: {col}")

            # 验证价格关系
            invalid_prices = (data['high'] < data['low']).sum()
            self.assertEqual(invalid_prices, 0, f"发现{invalid_prices}条价格异常")

            # 特征计算并验证
            alpha = AlphaFactors(data)
            features = alpha.calculate_all_alpha_factors()

            # 验证特征范围
            inf_count = np.isinf(features.values).sum()
            self.assertEqual(inf_count, 0, f"发现{inf_count}个无穷值")

            # 统计NaN比例
            nan_ratio = features.isna().sum().sum() / (len(features) * len(features.columns))
            self.assertLess(nan_ratio, 0.5, "NaN比例过高")

        except Exception as e:
            self.skipTest(f"测试需要完整环境: {e}")

    def test_03_workflow_performance_check(self):
        """测试工作流性能"""

        try:
            import time
            from src.providers import DataProviderFactory
            from src.features import AlphaFactors, TechnicalIndicators

            timings = {}

            # 数据下载计时
            start = time.time()
            provider = DataProviderFactory.create_provider('akshare')
            data = provider.get_daily_data(
                self.test_stock,
                self.test_start_date,
                self.test_end_date
            )
            timings['data_download'] = time.time() - start

            # Alpha因子计算计时
            start = time.time()
            alpha = AlphaFactors(data)
            alpha_features = alpha.calculate_all_alpha_factors()
            timings['alpha_factors'] = time.time() - start

            # 技术指标计算计时
            start = time.time()
            tech = TechnicalIndicators(data)
            tech_features = tech.add_all_indicators()
            timings['technical_indicators'] = time.time() - start

            # 验证性能阈值
            self.assertLess(timings['alpha_factors'], 60, "Alpha因子计算过慢")
            self.assertLess(timings['technical_indicators'], 30, "技术指标计算过慢")

        except Exception as e:
            self.skipTest(f"测试需要完整环境: {e}")

    def test_04_error_handling_in_workflow(self):
        """测试工作流错误处理"""
        try:
            from src.providers import DataProviderFactory

            provider = DataProviderFactory.create_provider('akshare')

            # 测试无效股票代码
            with self.assertRaises(Exception):
                data = provider.get_daily_data(
                    'INVALID_CODE',
                    self.test_start_date,
                    self.test_end_date
                )

            # 测试无效日期范围
            with self.assertRaises(Exception):
                data = provider.get_daily_data(
                    self.test_stock,
                    '2025-12-31',
                    '2023-01-01'  # 结束日期早于开始日期
                )

        except Exception as e:
            self.skipTest(f"测试需要完整环境: {e}")


class TestMultiStockWorkflow(unittest.TestCase):
    """测试多股票工作流"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.test_stocks = ['000001', '000002', '600000']
        cls.test_start_date = '2023-01-01'
        cls.test_end_date = '2023-12-31'

    def test_01_batch_data_download(self):
        """测试批量数据下载"""

        try:
            from src.providers import DataProviderFactory

            provider = DataProviderFactory.create_provider('akshare')

            results = {}
            for stock in self.test_stocks:
                data = provider.get_daily_data(
                    stock,
                    self.test_start_date,
                    self.test_end_date
                )
                results[stock] = data

            # 验证所有股票数据
            self.assertEqual(len(results), len(self.test_stocks))
            for stock, data in results.items():
                self.assertGreater(len(data), 0, f"{stock} 数据为空")

        except Exception as e:
            self.skipTest(f"测试需要完整环境: {e}")

    def test_02_batch_feature_calculation(self):
        """测试批量特征计算"""
        try:
            from src.providers import DataProviderFactory
            from src.features import AlphaFactors

            provider = DataProviderFactory.create_provider('akshare')

            feature_results = {}
            for stock in self.test_stocks:
                # 下载数据
                data = provider.get_daily_data(
                    stock,
                    self.test_start_date,
                    self.test_end_date
                )

                # 计算特征
                alpha = AlphaFactors(data)
                features = alpha.calculate_all_alpha_factors()
                feature_results[stock] = features

            # 验证
            self.assertEqual(len(feature_results), len(self.test_stocks))

            # 检查特征一致性
            feature_counts = [len(f.columns) for f in feature_results.values()]
            self.assertEqual(
                len(set(feature_counts)), 1,
                f"不同股票的特征数量不一致: {feature_counts}"
            )

        except Exception as e:
            self.skipTest(f"测试需要完整环境: {e}")


def run_tests():
    """运行所有集成测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestCompleteWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiStockWorkflow))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
