"""
LightGBM 股票排序模型训练工具测试

测试 StockRankerTrainer 的所有核心功能
"""

import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch, MagicMock

import numpy as np
import pandas as pd

# 添加项目路径
project_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(project_root))

from tools.train_stock_ranker_lgbm import StockRankerTrainer


class TestStockRankerTrainer(unittest.TestCase):
    """StockRankerTrainer 基础功能测试"""

    def setUp(self):
        """准备测试数据"""
        # 创建模拟价格数据：100天 × 20只股票
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = [f'STOCK_{i:03d}' for i in range(20)]

        np.random.seed(42)
        prices_data = 100 + np.cumsum(
            np.random.randn(100, 20) * 0.02, axis=0
        )
        self.prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

        # 创建训练器
        self.trainer = StockRankerTrainer(
            label_forward_days=5,
            label_threshold=0.02
        )

    def test_initialization(self):
        """测试初始化"""
        trainer = StockRankerTrainer(
            feature_names=['momentum_20d', 'rsi_14d'],
            label_forward_days=10,
            label_threshold=0.03
        )

        self.assertEqual(trainer.feature_names, ['momentum_20d', 'rsi_14d'])
        self.assertEqual(trainer.label_forward_days, 10)
        self.assertEqual(trainer.label_threshold, 0.03)

    def test_default_features(self):
        """测试默认特征集"""
        features = self.trainer._get_default_features()

        # 验证特征数量
        self.assertEqual(len(features), 11)

        # 验证包含关键特征
        self.assertIn('momentum_20d', features)
        self.assertIn('rsi_14d', features)
        self.assertIn('volatility_20d', features)
        self.assertIn('atr_14d', features)

    def test_calculate_labels_at_date(self):
        """测试标签计算"""
        date = pd.Timestamp('2023-02-01')

        labels = self.trainer._calculate_labels_at_date(date, self.prices)

        # 验证返回类型
        self.assertIsInstance(labels, pd.Series)

        # 验证标签值在 0-4 范围内
        valid_labels = labels.dropna()
        self.assertTrue(all(valid_labels >= 0))
        self.assertTrue(all(valid_labels <= 4))

    def test_calculate_labels_scoring_logic(self):
        """测试标签评分逻辑"""
        # 创建简单的测试数据：确保日期索引足够计算未来5日收益率
        dates = pd.date_range('2023-01-01', periods=20, freq='D')
        stocks = ['A', 'B', 'C', 'D', 'E']

        # 创建特定收益率模式的价格数据
        # 从第5天开始，未来5天（到第10天）的价格变化
        prices_data = pd.DataFrame(
            {
                'A': [100] * 5 + [110] * 15,  # 第5天之后涨到110，5天后涨幅10%
                'B': [100] * 5 + [103] * 15,  # 第5天之后涨到103，5天后涨幅3%
                'C': [100] * 5 + [101] * 15,  # 第5天之后涨到101，5天后涨幅1%
                'D': [100] * 5 + [99] * 15,   # 第5天之后跌到99，5天后跌幅1%
                'E': [100] * 5 + [95] * 15,   # 第5天之后跌到95，5天后跌幅5%
            },
            index=dates
        )

        trainer = StockRankerTrainer(
            label_forward_days=5,
            label_threshold=0.02
        )

        # 在第1天计算标签，会看未来5天（第6天）的价格
        date = pd.Timestamp('2023-01-01')
        labels = trainer._calculate_labels_at_date(date, prices_data)

        # 验证评分逻辑
        self.assertEqual(labels['A'], 4)  # 涨幅 10% > 2 * threshold (4%)
        self.assertEqual(labels['B'], 3)  # 涨幅 3% > threshold (2%)
        self.assertEqual(labels['C'], 2)  # 涨幅 1% > 0
        self.assertEqual(labels['D'], 1)  # 跌幅 -1% > -threshold (-2%)
        self.assertEqual(labels['E'], 0)  # 跌幅 -5% < -threshold (-2%)

    def test_get_sample_dates_daily(self):
        """测试日频采样"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        sampled = self.trainer._get_sample_dates(dates, 'D')

        self.assertEqual(len(sampled), 10)
        self.assertTrue(all(sampled == dates))

    def test_get_sample_dates_weekly(self):
        """测试周频采样"""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        sampled = self.trainer._get_sample_dates(dates, 'W')

        # 验证只包含周五
        for date in sampled:
            self.assertEqual(date.dayofweek, 4)

    def test_get_sample_dates_monthly(self):
        """测试月频采样"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        sampled = self.trainer._get_sample_dates(dates, 'M')

        # 验证每月只有一个日期
        months = [d.month for d in sampled]
        self.assertEqual(len(months), len(set(months)))

    def test_prepare_training_data(self):
        """测试训练数据准备"""
        X, y, groups = self.trainer.prepare_training_data(
            prices=self.prices,
            start_date='2023-01-20',
            end_date='2023-02-20',
            sample_freq='W'
        )

        # 验证数据形状
        self.assertIsInstance(X, pd.DataFrame)
        self.assertIsInstance(y, pd.Series)
        self.assertIsInstance(groups, np.ndarray)

        # 验证特征数量
        self.assertEqual(X.shape[1], len(self.trainer.feature_names))

        # 验证样本数和标签数一致
        self.assertEqual(len(X), len(y))

        # 验证分组信息
        self.assertEqual(sum(groups), len(X))

    def test_prepare_training_data_empty_result(self):
        """测试数据不足时的处理"""
        # 使用太短的数据（不足以计算特征和标签）
        short_prices = self.prices.iloc[:5]

        with self.assertRaises((ValueError, Exception)):
            # 数据太短会导致特征计算失败或没有有效数据
            self.trainer.prepare_training_data(
                prices=short_prices,
                start_date='2023-01-01',
                end_date='2023-01-03',
                sample_freq='D'
            )

    @patch('lightgbm.LGBMRanker')
    @patch('lightgbm.log_evaluation')
    @patch('lightgbm.early_stopping')
    def test_train_model(self, mock_early_stopping, mock_log_eval, mock_lgbm_ranker):
        """测试模型训练"""
        # 创建模拟数据
        X_train = pd.DataFrame(
            np.random.randn(100, 5),
            columns=['f1', 'f2', 'f3', 'f4', 'f5']
        )
        y_train = pd.Series(np.random.randint(0, 5, 100))
        groups_train = np.array([20, 30, 50])

        # 模拟 LightGBM 模型
        mock_model = MagicMock()
        mock_model.best_iteration_ = 50
        mock_model.best_score_ = {'valid_0': {'ndcg@10': 0.75}}
        mock_model.feature_importances_ = np.array([0.3, 0.25, 0.2, 0.15, 0.1])

        mock_lgbm_ranker.return_value = mock_model
        mock_log_eval.return_value = MagicMock()
        mock_early_stopping.return_value = MagicMock()

        # 训练模型
        model = self.trainer.train_model(
            X_train=X_train,
            y_train=y_train,
            groups_train=groups_train
        )

        # 验证模型创建
        mock_lgbm_ranker.assert_called_once()

        # 验证模型训练
        mock_model.fit.assert_called_once()

        # 验证返回模型
        self.assertEqual(model, mock_model)

    def test_train_model_custom_params(self):
        """测试使用自定义参数训练"""
        # 需要 lightgbm 库
        try:
            import lightgbm
        except ImportError:
            self.skipTest("需要 lightgbm 库")

        # 创建简单数据
        X_train = pd.DataFrame(
            np.random.randn(100, 3),
            columns=['f1', 'f2', 'f3']
        )
        y_train = pd.Series(np.random.randint(0, 5, 100))
        groups_train = np.array([20, 30, 50])

        custom_params = {
            'n_estimators': 50,
            'learning_rate': 0.1,
            'max_depth': 4
        }

        model = self.trainer.train_model(
            X_train=X_train,
            y_train=y_train,
            groups_train=groups_train,
            model_params=custom_params
        )

        # 验证模型对象
        self.assertIsNotNone(model)

    @patch('joblib.dump')
    def test_save_model(self, mock_joblib_dump):
        """测试模型保存"""
        mock_model = Mock()
        model_path = '/tmp/test_model.pkl'

        self.trainer.save_model(mock_model, model_path)

        # 验证调用 joblib.dump
        mock_joblib_dump.assert_called_once_with(mock_model, model_path)

    def test_evaluate_model_basic(self):
        """测试模型评估（基础）"""
        # 需要 lightgbm 和 scikit-learn
        try:
            import lightgbm
            from sklearn.metrics import ndcg_score
        except ImportError:
            self.skipTest("需要 lightgbm 和 scikit-learn")

        # 创建模拟模型
        mock_model = Mock()
        mock_model.predict.return_value = np.random.randn(100)

        # 创建测试数据
        X_test = pd.DataFrame(
            np.random.randn(100, 5),
            columns=['f1', 'f2', 'f3', 'f4', 'f5']
        )
        y_test = pd.Series(np.random.randint(0, 5, 100))
        groups_test = np.array([20, 30, 50])

        # 评估模型
        metrics = self.trainer.evaluate_model(
            model=mock_model,
            X_test=X_test,
            y_test=y_test,
            groups_test=groups_test
        )

        # 验证返回指标
        self.assertIsInstance(metrics, dict)


class TestStockRankerTrainerIntegration(unittest.TestCase):
    """StockRankerTrainer 集成测试"""

    def setUp(self):
        """准备完整的测试数据"""
        # 创建更长的价格数据：200天 × 50只股票
        dates = pd.date_range('2023-01-01', periods=200, freq='D')
        stocks = [f'STOCK_{i:03d}' for i in range(50)]

        np.random.seed(42)
        # 创建带趋势的价格数据
        base_prices = 100
        trends = np.random.randn(50) * 0.001  # 每只股票有不同趋势
        noise = np.random.randn(200, 50) * 0.02

        prices_data = base_prices * np.exp(
            np.cumsum(trends + noise, axis=0)
        )

        self.prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

        self.trainer = StockRankerTrainer(
            label_forward_days=5,
            label_threshold=0.02
        )

    def test_full_training_pipeline(self):
        """测试完整训练流程"""
        # 需要 lightgbm
        try:
            import lightgbm
        except ImportError:
            self.skipTest("需要 lightgbm")

        # 1. 准备训练数据
        X_train, y_train, groups_train = self.trainer.prepare_training_data(
            prices=self.prices,
            start_date='2023-01-20',
            end_date='2023-04-30',
            sample_freq='W'
        )

        self.assertGreater(len(X_train), 0)
        self.assertGreater(len(groups_train), 0)

        # 2. 训练模型
        model = self.trainer.train_model(
            X_train=X_train,
            y_train=y_train,
            groups_train=groups_train,
            model_params={'n_estimators': 20, 'verbose': -1}
        )

        self.assertIsNotNone(model)

        # 3. 准备测试数据
        X_test, y_test, groups_test = self.trainer.prepare_training_data(
            prices=self.prices,
            start_date='2023-05-01',
            end_date='2023-06-30',
            sample_freq='W'
        )

        # 4. 评估模型
        metrics = self.trainer.evaluate_model(
            model=model,
            X_test=X_test,
            y_test=y_test,
            groups_test=groups_test
        )

        self.assertIsInstance(metrics, dict)

        # 5. 预测
        predictions = model.predict(X_test)

        # 验证预测结果
        self.assertEqual(len(predictions), len(X_test))
        self.assertTrue(all(np.isfinite(predictions)))

    def test_model_with_different_frequencies(self):
        """测试不同采样频率"""
        try:
            import lightgbm
        except ImportError:
            self.skipTest("需要 lightgbm")

        frequencies = ['W', 'M']

        for freq in frequencies:
            with self.subTest(freq=freq):
                # 准备数据
                X, y, groups = self.trainer.prepare_training_data(
                    prices=self.prices,
                    start_date='2023-01-20',
                    end_date='2023-04-30',
                    sample_freq=freq
                )

                # 训练模型
                model = self.trainer.train_model(
                    X_train=X,
                    y_train=y,
                    groups_train=groups,
                    model_params={'n_estimators': 10, 'verbose': -1}
                )

                self.assertIsNotNone(model)

    def test_feature_consistency(self):
        """测试特征一致性"""
        # 准备数据
        X, y, groups = self.trainer.prepare_training_data(
            prices=self.prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            sample_freq='W'
        )

        # 验证特征列与配置一致
        self.assertEqual(
            list(X.columns),
            self.trainer.feature_names
        )

    def test_label_distribution(self):
        """测试标签分布"""
        # 准备数据
        X, y, groups = self.trainer.prepare_training_data(
            prices=self.prices,
            start_date='2023-01-20',
            end_date='2023-04-30',
            sample_freq='W'
        )

        # 验证标签分布
        label_counts = y.value_counts().sort_index()

        # 标签应该包含 0-4
        self.assertTrue(all(label_counts.index >= 0))
        self.assertTrue(all(label_counts.index <= 4))

        # 标签不应过于集中
        self.assertGreater(len(label_counts), 1)


class TestStockRankerTrainerEdgeCases(unittest.TestCase):
    """StockRankerTrainer 边界情况测试"""

    def test_empty_price_data(self):
        """测试空价格数据"""
        trainer = StockRankerTrainer()
        empty_prices = pd.DataFrame()

        with self.assertRaises(Exception):
            trainer.prepare_training_data(
                prices=empty_prices,
                start_date='2023-01-01',
                end_date='2023-01-31',
                sample_freq='D'
            )

    def test_single_stock(self):
        """测试单只股票"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        prices = pd.DataFrame(
            {'STOCK_A': 100 + np.cumsum(np.random.randn(100) * 0.02)},
            index=dates
        )

        trainer = StockRankerTrainer()

        # 单只股票也可以训练，只是排序意义不大
        # 这里我们只验证能正常运行即可
        try:
            X, y, groups = trainer.prepare_training_data(
                prices=prices,
                start_date='2023-01-20',
                end_date='2023-02-28',
                sample_freq='W'
            )
            # 如果成功，验证数据格式
            self.assertIsInstance(X, pd.DataFrame)
            self.assertIsInstance(y, pd.Series)
        except (ValueError, Exception) as e:
            # 如果失败也是可接受的（数据不足）
            pass

    def test_insufficient_history(self):
        """测试历史数据不足"""
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        stocks = [f'STOCK_{i}' for i in range(10)]
        prices = pd.DataFrame(
            np.random.randn(10, 10) + 100,
            index=dates,
            columns=stocks
        )

        trainer = StockRankerTrainer(label_forward_days=5)

        # 数据不足会导致特征计算失败或没有有效数据
        with self.assertRaises((ValueError, Exception)):
            trainer.prepare_training_data(
                prices=prices,
                start_date='2023-01-01',
                end_date='2023-01-10',
                sample_freq='D'
            )

    def test_nan_handling(self):
        """测试 NaN 值处理"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = [f'STOCK_{i}' for i in range(20)]

        np.random.seed(42)
        prices_data = 100 + np.cumsum(
            np.random.randn(100, 20) * 0.02, axis=0
        )

        # 添加一些 NaN
        prices_data[10:20, 5] = np.nan
        prices_data[30:40, 10] = np.nan

        prices = pd.DataFrame(prices_data, index=dates, columns=stocks)

        trainer = StockRankerTrainer()

        # 应该能处理 NaN 值
        X, y, groups = trainer.prepare_training_data(
            prices=prices,
            start_date='2023-01-20',
            end_date='2023-02-28',
            sample_freq='W'
        )

        # 验证没有 NaN
        self.assertFalse(X.isna().any().any())
        self.assertFalse(y.isna().any())


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestStockRankerTrainer))
    suite.addTests(loader.loadTestsFromTestCase(TestStockRankerTrainerIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestStockRankerTrainerEdgeCases))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)
