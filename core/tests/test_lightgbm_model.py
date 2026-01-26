"""
LightGBM模型单元测试
测试模型训练、预测、保存/加载等功能
"""

import unittest
import pandas as pd
import numpy as np
import tempfile
import shutil
from pathlib import Path

# 添加src目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from models.lightgbm_model import LightGBMStockModel, train_lightgbm_model


class TestLightGBMStockModel(unittest.TestCase):
    """LightGBM模型测试类"""

    @classmethod
    def setUpClass(cls):
        """类级别的设置 - 创建测试数据"""
        np.random.seed(42)
        cls.n_samples = 500
        cls.n_features = 15

        # 创建测试特征
        cls.X = pd.DataFrame(
            np.random.randn(cls.n_samples, cls.n_features),
            columns=[f'feature_{i}' for i in range(cls.n_features)]
        )

        # 创建目标（模拟股票收益率，带线性关系和噪声）
        cls.y = pd.Series(
            cls.X['feature_0'] * 0.5 +
            cls.X['feature_1'] * 0.3 +
            cls.X['feature_2'] * -0.2 +
            np.random.randn(cls.n_samples) * 0.1
        )

        # 分割数据
        split_idx = int(cls.n_samples * 0.8)
        cls.X_train = cls.X[:split_idx]
        cls.X_test = cls.X[split_idx:]
        cls.y_train = cls.y[:split_idx]
        cls.y_test = cls.y[split_idx:]

        # 创建临时目录用于保存模型
        cls.temp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        """类级别的清理 - 删除临时目录"""
        shutil.rmtree(cls.temp_dir)

    def test_01_model_initialization(self):
        """测试模型初始化"""
        model = LightGBMStockModel(
            objective='regression',
            metric='rmse',
            num_leaves=31,
            learning_rate=0.1,
            n_estimators=100
        )

        # 验证参数设置
        self.assertEqual(model.params['objective'], 'regression')
        self.assertEqual(model.params['metric'], 'rmse')
        self.assertEqual(model.params['num_leaves'], 31)
        self.assertEqual(model.params['learning_rate'], 0.1)
        self.assertEqual(model.params['n_estimators'], 100)

        # 验证初始状态
        self.assertIsNone(model.model)
        self.assertIsNone(model.feature_names)
        self.assertIsNone(model.feature_importance)

    def test_02_model_training(self):
        """测试模型训练"""
        model = LightGBMStockModel(
            learning_rate=0.1,
            n_estimators=50,
            verbose=-1
        )

        history = model.train(
            self.X_train, self.y_train,
            self.X_test, self.y_test,
            early_stopping_rounds=10,
            verbose_eval=-1
        )

        # 验证模型已训练
        self.assertIsNotNone(model.model)
        self.assertIsNotNone(model.feature_names)
        self.assertIsNotNone(model.feature_importance)

        # 验证特征名称正确
        self.assertEqual(model.feature_names, list(self.X_train.columns))

        # 验证训练历史
        self.assertIn('best_iteration', history)
        self.assertIn('best_score', history)
        self.assertIsInstance(history['best_iteration'], int)
        self.assertGreater(history['best_iteration'], 0)

    def test_03_model_prediction(self):
        """测试模型预测"""
        model = LightGBMStockModel(learning_rate=0.1, n_estimators=50, verbose=-1)
        model.train(self.X_train, self.y_train, verbose_eval=-1)

        # 预测
        y_pred = model.predict(self.X_test)

        # 验证预测结果
        self.assertIsInstance(y_pred, np.ndarray)
        self.assertEqual(len(y_pred), len(self.X_test))
        self.assertFalse(np.any(np.isnan(y_pred)))

        # 验证预测值的合理性（使用R²检验拟合质量）
        from sklearn.metrics import r2_score
        r2 = r2_score(self.y_test, y_pred)
        self.assertGreater(r2, 0.5, f"R² too low: {r2:.4f}")

    def test_04_predict_rank(self):
        """测试排名预测"""
        model = LightGBMStockModel(learning_rate=0.1, n_estimators=50, verbose=-1)
        model.train(self.X_train, self.y_train, verbose_eval=-1)

        # 预测排名
        ranks = model.predict_rank(self.X_test, ascending=False)

        # 验证排名结果
        self.assertEqual(len(ranks), len(self.X_test))
        self.assertTrue(np.min(ranks) >= 1)
        self.assertTrue(np.max(ranks) <= len(self.X_test))

        # 验证排名的唯一性（应该都不相同，除非有tie）
        unique_ranks = len(np.unique(ranks))
        self.assertGreater(unique_ranks, len(self.X_test) * 0.9)

    def test_05_feature_importance(self):
        """测试特征重要性计算"""
        model = LightGBMStockModel(learning_rate=0.1, n_estimators=50, verbose=-1)
        model.train(self.X_train, self.y_train, verbose_eval=-1)

        # 获取特征重要性
        importance_df = model.get_feature_importance('gain', top_n=10)

        # 验证结果
        self.assertIsInstance(importance_df, pd.DataFrame)
        self.assertIn('feature', importance_df.columns)
        self.assertIn('gain', importance_df.columns)
        self.assertLessEqual(len(importance_df), 10)

        # 验证按重要性降序排列
        gains = importance_df['gain'].values
        self.assertTrue(np.all(gains[:-1] >= gains[1:]))

        # 验证最重要的特征包含真实相关特征
        top_features = importance_df.head(3)['feature'].tolist()
        self.assertTrue(
            any(f in top_features for f in ['feature_0', 'feature_1', 'feature_2']),
            f"Top features should include feature_0, feature_1, or feature_2, got {top_features}"
        )

    def test_06_save_and_load_model(self):
        """测试模型保存和加载"""
        # 训练模型
        model = LightGBMStockModel(learning_rate=0.1, n_estimators=50, verbose=-1)
        model.train(self.X_train, self.y_train, verbose_eval=-1)

        # 预测
        y_pred_before = model.predict(self.X_test)

        # 保存模型
        model_path = Path(self.temp_dir) / 'test_model.txt'
        model.save_model(str(model_path))

        # 验证文件已创建
        self.assertTrue(model_path.exists())
        self.assertTrue(model_path.with_suffix('.meta.pkl').exists())

        # 加载模型
        new_model = LightGBMStockModel()
        new_model.load_model(str(model_path))

        # 预测
        y_pred_after = new_model.predict(self.X_test)

        # 验证预测一致性
        np.testing.assert_array_almost_equal(
            y_pred_before, y_pred_after,
            decimal=6,
            err_msg="Predictions before and after save/load don't match"
        )

        # 验证特征名称一致
        self.assertEqual(model.feature_names, new_model.feature_names)

    def test_07_model_with_no_validation(self):
        """测试无验证集训练"""
        model = LightGBMStockModel(learning_rate=0.1, n_estimators=30, verbose=-1)

        history = model.train(
            self.X_train, self.y_train,
            X_valid=None, y_valid=None,
            verbose_eval=-1
        )

        # 验证模型可正常训练
        self.assertIsNotNone(model.model)
        self.assertIn('best_iteration', history)

        # 验证可正常预测
        y_pred = model.predict(self.X_test)
        self.assertEqual(len(y_pred), len(self.X_test))

    def test_08_train_lightgbm_model_function(self):
        """测试便捷训练函数"""
        model = train_lightgbm_model(
            self.X_train, self.y_train,
            self.X_test, self.y_test,
            params={'learning_rate': 0.1, 'n_estimators': 30},
            early_stopping_rounds=10
        )

        # 验证模型已训练
        self.assertIsNotNone(model.model)

        # 验证可预测
        y_pred = model.predict(self.X_test)
        self.assertEqual(len(y_pred), len(self.X_test))

    def test_09_get_params(self):
        """测试获取模型参数"""
        original_params = {
            'learning_rate': 0.05,
            'num_leaves': 15,
            'n_estimators': 100
        }

        model = LightGBMStockModel(**original_params, verbose=-1)
        retrieved_params = model.get_params()

        # 验证关键参数
        self.assertEqual(retrieved_params['learning_rate'], 0.05)
        self.assertEqual(retrieved_params['num_leaves'], 15)
        self.assertEqual(retrieved_params['n_estimators'], 100)

    def test_10_feature_mismatch_handling(self):
        """测试特征不匹配的处理"""
        model = LightGBMStockModel(learning_rate=0.1, n_estimators=30, verbose=-1)
        model.train(self.X_train, self.y_train, verbose_eval=-1)

        # 创建列顺序不同的测试数据
        X_shuffled = self.X_test[list(reversed(self.X_test.columns))]

        # 验证仍能正确预测（应自动重排序）
        y_pred = model.predict(X_shuffled)
        self.assertEqual(len(y_pred), len(X_shuffled))

    def test_11_predict_without_training(self):
        """测试未训练就预测会抛出异常"""
        model = LightGBMStockModel()

        with self.assertRaises(ValueError) as context:
            model.predict(self.X_test)

        self.assertIn("模型未训练", str(context.exception))

    def test_12_feature_importance_without_training(self):
        """测试未训练就获取特征重要性会抛出异常"""
        model = LightGBMStockModel()

        with self.assertRaises(ValueError) as context:
            model.get_feature_importance()

        self.assertIn("特征重要性未计算", str(context.exception))


class TestLightGBMModelEdgeCases(unittest.TestCase):
    """LightGBM模型边界情况测试"""

    def test_small_dataset(self):
        """测试小数据集"""
        X_small = pd.DataFrame(np.random.randn(50, 5), columns=[f'f_{i}' for i in range(5)])
        y_small = pd.Series(np.random.randn(50))

        model = LightGBMStockModel(learning_rate=0.1, n_estimators=10, verbose=-1)
        model.train(X_small, y_small, verbose_eval=-1)

        y_pred = model.predict(X_small)
        self.assertEqual(len(y_pred), len(X_small))

    def test_single_feature(self):
        """测试单特征"""
        X_single = pd.DataFrame(np.random.randn(100, 1), columns=['feature_0'])
        y_single = pd.Series(X_single['feature_0'] * 2 + np.random.randn(100) * 0.1)

        model = LightGBMStockModel(learning_rate=0.1, n_estimators=20, verbose=-1)
        model.train(X_single, y_single, verbose_eval=-1)

        y_pred = model.predict(X_single)
        self.assertEqual(len(y_pred), len(X_single))

        # 验证单特征的重要性
        importance = model.get_feature_importance()
        self.assertEqual(len(importance), 1)
        self.assertEqual(importance.iloc[0]['feature'], 'feature_0')


def run_tests():
    """运行测试"""
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
