"""
ML-3 LightGBM 排序模型完整工作流集成测试

测试从数据准备、模型训练、到实际选股的完整流程
"""

import sys
from pathlib import Path
import unittest
import tempfile
import shutil

import numpy as np
import pandas as pd

# 添加项目路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


class TestML3LightGBMWorkflow(unittest.TestCase):
    """ML-3 完整工作流测试"""

    @classmethod
    def setUpClass(cls):
        """准备测试数据和临时目录"""
        # 创建临时目录
        cls.temp_dir = tempfile.mkdtemp()

        # 创建模拟市场数据：300天 × 100只股票
        dates = pd.date_range('2023-01-01', periods=300, freq='D')
        stocks = [f'STOCK_{i:03d}' for i in range(100)]

        np.random.seed(42)

        # 创建带趋势和板块效应的价格数据
        base_price = 100
        n_days = len(dates)
        n_stocks = len(stocks)

        # 创建板块（10个板块，每个板块10只股票）
        sector_trends = np.random.randn(10) * 0.001
        stock_sectors = np.repeat(sector_trends, 10)

        # 生成价格
        trends = stock_sectors.reshape(1, -1)
        noise = np.random.randn(n_days, n_stocks) * 0.02

        prices_data = base_price * np.exp(
            np.cumsum(trends + noise, axis=0)
        )

        cls.prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

    @classmethod
    def tearDownClass(cls):
        """清理临时目录"""
        if hasattr(cls, 'temp_dir'):
            shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_workflow_1_train_model(self):
        """工作流步骤1: 训练 LightGBM 模型"""
        try:
            import lightgbm
        except ImportError:
            self.skipTest("需要 lightgbm")

        from tools.train_stock_ranker_lgbm import StockRankerTrainer

        # 创建训练器
        trainer = StockRankerTrainer(
            label_forward_days=5,
            label_threshold=0.02
        )

        # 准备训练数据（前6个月）
        X_train, y_train, groups_train = trainer.prepare_training_data(
            prices=self.prices,
            start_date='2023-01-20',
            end_date='2023-06-30',
            sample_freq='W'
        )

        # 验证数据质量
        self.assertGreater(len(X_train), 0)
        self.assertEqual(len(X_train), len(y_train))
        self.assertEqual(sum(groups_train), len(X_train))

        # 训练模型
        model = trainer.train_model(
            X_train=X_train,
            y_train=y_train,
            groups_train=groups_train,
            model_params={
                'n_estimators': 50,
                'learning_rate': 0.1,
                'verbose': -1
            }
        )

        self.assertIsNotNone(model)

        # 保存模型
        model_path = Path(self.temp_dir) / 'test_ranker_model.pkl'
        trainer.save_model(model, str(model_path))

        # 验证模型文件
        self.assertTrue(model_path.exists())

        # 存储模型路径供后续测试使用
        self.__class__.model_path = str(model_path)

    def test_workflow_2_use_model_in_selector(self):
        """工作流步骤2: 在 MLSelector 中使用训练好的模型"""
        # 检查是否有训练好的模型
        if not hasattr(self.__class__, 'model_path'):
            self.skipTest("需要先运行 test_workflow_1_train_model")

        try:
            import lightgbm
        except ImportError:
            self.skipTest("需要 lightgbm")

        from src.strategies.three_layer.selectors.ml_selector import MLSelector

        # 创建 MLSelector，使用 LightGBM 模型
        selector = MLSelector(params={
            'mode': 'lightgbm_ranker',
            'model_path': self.__class__.model_path,
            'top_n': 20
        })

        # 验证模型加载
        self.assertIsNotNone(selector.model)
        self.assertEqual(selector.mode, 'lightgbm_ranker')

        # 执行选股（使用测试期数据）
        test_date = pd.Timestamp('2023-08-01')
        selected_stocks = selector.select(test_date, self.prices)

        # 验证选股结果
        self.assertIsInstance(selected_stocks, list)
        self.assertLessEqual(len(selected_stocks), 20)
        self.assertGreater(len(selected_stocks), 0)

        # 验证股票代码格式
        for stock in selected_stocks:
            self.assertTrue(stock.startswith('STOCK_'))

    def test_workflow_3_backtest_with_lightgbm_selector(self):
        """工作流步骤3: 使用 LightGBM 选股器进行回测"""
        # 检查是否有训练好的模型
        if not hasattr(self.__class__, 'model_path'):
            self.skipTest("需要先运行 test_workflow_1_train_model")

        try:
            import lightgbm
        except ImportError:
            self.skipTest("需要 lightgbm")

        from src.strategies.three_layer.selectors.ml_selector import MLSelector
        from src.strategies.three_layer.entries import ImmediateEntry
        from src.strategies.three_layer.exits import FixedHoldingPeriodExit
        from src.strategies.three_layer.base import StrategyComposer

        # 创建三层策略
        selector = MLSelector(params={
            'mode': 'lightgbm_ranker',
            'model_path': self.__class__.model_path,
            'top_n': 30
        })

        entry = ImmediateEntry()

        exit_strategy = FixedHoldingPeriodExit(params={
            'holding_period': 10
        })

        composer = StrategyComposer(
            selector=selector,
            entry=entry,
            exit_strategy=exit_strategy,
            rebalance_freq='M'  # 月度调仓
        )

        # 验证组合
        self.assertEqual(composer.selector, selector)
        self.assertEqual(composer.entry, entry)
        self.assertEqual(composer.exit, exit_strategy)

        # 模拟回测（简化版）
        test_dates = pd.date_range('2023-08-01', '2023-09-30', freq='M')
        all_selections = []

        for test_date in test_dates:
            selected = selector.select(test_date, self.prices)
            all_selections.append({
                'date': test_date,
                'stocks': selected,
                'count': len(selected)
            })

        # 验证回测结果
        self.assertEqual(len(all_selections), len(test_dates))
        for selection in all_selections:
            self.assertGreater(selection['count'], 0)

    def test_workflow_4_compare_models(self):
        """工作流步骤4: 对比不同模型的选股结果"""
        if not hasattr(self.__class__, 'model_path'):
            self.skipTest("需要先运行 test_workflow_1_train_model")

        try:
            import lightgbm
        except ImportError:
            self.skipTest("需要 lightgbm")

        from src.strategies.three_layer.selectors.ml_selector import MLSelector

        # 创建两个选股器：多因子加权 vs LightGBM
        selector_weighted = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 20,
            'features': 'momentum_20d,rsi_14d,volatility_20d'
        })

        selector_lgbm = MLSelector(params={
            'mode': 'lightgbm_ranker',
            'model_path': self.__class__.model_path,
            'top_n': 20
        })

        # 在同一日期选股
        test_date = pd.Timestamp('2023-08-15')

        stocks_weighted = selector_weighted.select(test_date, self.prices)
        stocks_lgbm = selector_lgbm.select(test_date, self.prices)

        # 验证两种方法都能选出股票
        self.assertGreater(len(stocks_weighted), 0)
        self.assertGreater(len(stocks_lgbm), 0)

        # 计算重叠度
        overlap = set(stocks_weighted) & set(stocks_lgbm)
        overlap_ratio = len(overlap) / max(len(stocks_weighted), len(stocks_lgbm))

        # 两种方法应该有一定差异（不完全相同）
        self.assertLess(overlap_ratio, 1.0)

        print(f"\n模型对比:")
        print(f"多因子加权选股: {len(stocks_weighted)} 只")
        print(f"LightGBM选股: {len(stocks_lgbm)} 只")
        print(f"重叠率: {overlap_ratio:.2%}")


class TestML3ModelPersistence(unittest.TestCase):
    """ML-3 模型持久化测试"""

    def setUp(self):
        """创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理临时目录"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_model_save_and_load(self):
        """测试模型保存和加载"""
        try:
            import lightgbm
            import joblib
        except ImportError:
            self.skipTest("需要 lightgbm 和 joblib")

        from tools.train_stock_ranker_lgbm import StockRankerTrainer

        # 创建测试数据
        dates = pd.date_range('2023-01-01', periods=150, freq='D')
        stocks = [f'STOCK_{i:03d}' for i in range(50)]

        np.random.seed(42)
        prices_data = 100 + np.cumsum(
            np.random.randn(150, 50) * 0.02, axis=0
        )
        prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

        # 训练模型
        trainer = StockRankerTrainer()

        X, y, groups = trainer.prepare_training_data(
            prices=prices,
            start_date='2023-01-20',
            end_date='2023-03-31',
            sample_freq='W'
        )

        model = trainer.train_model(
            X_train=X,
            y_train=y,
            groups_train=groups,
            model_params={'n_estimators': 20, 'verbose': -1}
        )

        # 保存模型
        model_path = Path(self.temp_dir) / 'test_model.pkl'
        trainer.save_model(model, str(model_path))

        # 验证文件存在
        self.assertTrue(model_path.exists())

        # 加载模型
        loaded_model = joblib.load(model_path)

        # 验证模型类型
        self.assertIsInstance(loaded_model, lightgbm.LGBMRanker)

        # 验证预测一致性
        X_test = X.iloc[:10]
        pred_original = model.predict(X_test)
        pred_loaded = loaded_model.predict(X_test)

        np.testing.assert_array_almost_equal(
            pred_original, pred_loaded
        )


class TestML3FeatureEngineering(unittest.TestCase):
    """ML-3 特征工程测试"""

    def test_feature_calculation_consistency(self):
        """测试特征计算的一致性"""
        from tools.train_stock_ranker_lgbm import StockRankerTrainer

        # 创建测试数据
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = ['STOCK_A', 'STOCK_B', 'STOCK_C']

        np.random.seed(42)
        prices_data = 100 + np.cumsum(
            np.random.randn(100, 3) * 0.02, axis=0
        )
        prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

        trainer = StockRankerTrainer()

        # 在同一日期计算两次特征
        test_date = pd.Timestamp('2023-02-15')

        features_1 = trainer._calculate_features_at_date(test_date, prices)
        features_2 = trainer._calculate_features_at_date(test_date, prices)

        # 验证一致性
        pd.testing.assert_frame_equal(features_1, features_2)

    def test_all_features_calculated(self):
        """测试所有特征都能正确计算"""
        from tools.train_stock_ranker_lgbm import StockRankerTrainer

        # 创建足够长的测试数据
        dates = pd.date_range('2023-01-01', periods=120, freq='D')
        stocks = [f'STOCK_{i}' for i in range(10)]

        np.random.seed(42)
        prices_data = 100 + np.cumsum(
            np.random.randn(120, 10) * 0.02, axis=0
        )
        prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

        trainer = StockRankerTrainer()

        test_date = pd.Timestamp('2023-03-01')
        features = trainer._calculate_features_at_date(test_date, prices)

        # 验证所有特征都被计算
        expected_features = trainer.feature_names
        actual_features = features.columns.tolist()

        self.assertEqual(set(expected_features), set(actual_features))

        # 验证没有 NaN 值
        self.assertFalse(features.isna().any().any())


def run_integration_tests():
    """运行所有集成测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类（按执行顺序）
    suite.addTests(loader.loadTestsFromTestCase(TestML3LightGBMWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestML3ModelPersistence))
    suite.addTests(loader.loadTestsFromTestCase(TestML3FeatureEngineering))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    result = run_integration_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
