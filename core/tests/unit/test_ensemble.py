"""
模型集成框架单元测试
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from models.ensemble import (
    BaseEnsemble,
    WeightedAverageEnsemble,
    VotingEnsemble,
    StackingEnsemble,
    create_ensemble,
    EnsembleError,
    IncompatibleModelsError
)
from models.ridge_model import RidgeStockModel
from models.lightgbm_model import LightGBMStockModel


# ==================== 测试数据准备 ====================

@pytest.fixture
def sample_data():
    """创建测试数据"""
    np.random.seed(42)
    n_samples = 200
    n_features = 10

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )

    y = pd.Series(
        X['feature_0'] * 0.5 +
        X['feature_1'] * 0.3 +
        np.random.randn(n_samples) * 0.1
    )

    # 分割数据
    train_size = int(n_samples * 0.6)
    valid_size = int(n_samples * 0.8)

    return {
        'X_train': X[:train_size],
        'y_train': y[:train_size],
        'X_valid': X[train_size:valid_size],
        'y_valid': y[train_size:valid_size],
        'X_test': X[valid_size:],
        'y_test': y[valid_size:]
    }


@pytest.fixture
def trained_models(sample_data):
    """创建并训练测试模型"""
    # Ridge 模型
    ridge = RidgeStockModel(alpha=1.0)
    ridge.train(
        sample_data['X_train'],
        sample_data['y_train'],
        sample_data['X_valid'],
        sample_data['y_valid']
    )

    # LightGBM 模型
    lgb = LightGBMStockModel(
        learning_rate=0.1,
        n_estimators=50,
        num_leaves=15,
        verbose=-1
    )
    lgb.train(
        sample_data['X_train'],
        sample_data['y_train'],
        sample_data['X_valid'],
        sample_data['y_valid'],
        verbose_eval=0
    )

    return {
        'ridge': ridge,
        'lgb': lgb,
        'models': [ridge, lgb],
        'model_names': ['Ridge', 'LightGBM']
    }


@pytest.fixture
def mock_models():
    """创建 Mock 模型（用于测试不需要真实训练的场景）"""
    def mock_predict_1(X):
        n = len(X)
        return np.linspace(1.0, 5.0, n)

    def mock_predict_2(X):
        n = len(X)
        return np.linspace(1.5, 5.5, n)

    def mock_predict_3(X):
        n = len(X)
        return np.linspace(0.5, 4.5, n)

    mock1 = Mock()
    mock1.predict = mock_predict_1

    mock2 = Mock()
    mock2.predict = mock_predict_2

    mock3 = Mock()
    mock3.predict = mock_predict_3

    return [mock1, mock2, mock3]


# ==================== 基础功能测试 ====================

class TestBaseEnsemble:
    """测试基础集成类"""

    def test_initialization_empty_models(self):
        """测试空模型列表初始化"""
        with pytest.raises(EnsembleError, match="模型列表不能为空"):
            WeightedAverageEnsemble([])

    def test_initialization_auto_names(self, mock_models):
        """测试自动生成模型名称"""
        ensemble = WeightedAverageEnsemble(mock_models)
        assert ensemble.model_names == ['model_0', 'model_1', 'model_2']

    def test_initialization_custom_names(self, mock_models):
        """测试自定义模型名称"""
        names = ['Model_A', 'Model_B', 'Model_C']
        ensemble = WeightedAverageEnsemble(mock_models, model_names=names)
        assert ensemble.model_names == names

    def test_initialization_mismatched_names(self, mock_models):
        """测试名称数量不匹配"""
        with pytest.raises(EnsembleError, match="模型名称数量"):
            WeightedAverageEnsemble(mock_models, model_names=['A', 'B'])

    def test_get_individual_predictions(self, mock_models):
        """测试获取单个模型预测"""
        ensemble = WeightedAverageEnsemble(mock_models)
        X = pd.DataFrame(np.random.randn(5, 3))

        predictions = ensemble.get_individual_predictions(X)

        assert len(predictions) == 3
        assert 'model_0' in predictions
        assert isinstance(predictions['model_0'], np.ndarray)


# ==================== 加权平均集成测试 ====================

class TestWeightedAverageEnsemble:
    """测试加权平均集成"""

    def test_equal_weights(self, mock_models):
        """测试等权重"""
        ensemble = WeightedAverageEnsemble(mock_models)
        assert np.allclose(ensemble.weights, [1/3, 1/3, 1/3])

    def test_custom_weights(self, mock_models):
        """测试自定义权重"""
        weights = [0.5, 0.3, 0.2]
        ensemble = WeightedAverageEnsemble(mock_models, weights=weights)
        assert np.allclose(ensemble.weights, weights)

    def test_weights_normalization(self, mock_models):
        """测试权重自动归一化"""
        weights = [2.0, 3.0, 5.0]  # 和为10
        ensemble = WeightedAverageEnsemble(mock_models, weights=weights)
        assert np.allclose(ensemble.weights, [0.2, 0.3, 0.5])

    def test_mismatched_weights(self, mock_models):
        """测试权重数量不匹配"""
        with pytest.raises(EnsembleError, match="权重数量"):
            WeightedAverageEnsemble(mock_models, weights=[0.5, 0.5])

    def test_predict(self, mock_models):
        """测试加权平均预测"""
        weights = [0.5, 0.3, 0.2]
        ensemble = WeightedAverageEnsemble(mock_models, weights=weights)

        X = pd.DataFrame(np.random.randn(5, 3))
        predictions = ensemble.predict(X)

        # 手动计算期望值
        pred1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        pred2 = np.array([1.5, 2.5, 3.5, 4.5, 5.5])
        pred3 = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
        expected = pred1 * 0.5 + pred2 * 0.3 + pred3 * 0.2

        assert np.allclose(predictions, expected)

    def test_optimize_weights(self, trained_models, sample_data):
        """测试权重优化"""
        ensemble = WeightedAverageEnsemble(
            trained_models['models'],
            model_names=trained_models['model_names']
        )

        # 优化前的权重
        initial_weights = ensemble.weights.copy()

        # 执行优化
        optimized_weights = ensemble.optimize_weights(
            sample_data['X_valid'],
            sample_data['y_valid'],
            metric='ic'
        )

        # 验证权重已改变
        assert not np.allclose(optimized_weights, initial_weights)

        # 验证权重和为1
        assert np.isclose(optimized_weights.sum(), 1.0)

        # 验证权重非负
        assert np.all(optimized_weights >= 0)

    def test_optimize_weights_rank_ic(self, trained_models, sample_data):
        """测试使用 Rank IC 优化权重"""
        ensemble = WeightedAverageEnsemble(trained_models['models'])

        optimized_weights = ensemble.optimize_weights(
            sample_data['X_valid'],
            sample_data['y_valid'],
            metric='rank_ic'
        )

        assert np.isclose(optimized_weights.sum(), 1.0)

    def test_predict_real_models(self, trained_models, sample_data):
        """测试使用真实模型预测"""
        ensemble = WeightedAverageEnsemble(
            trained_models['models'],
            weights=[0.4, 0.6],
            model_names=trained_models['model_names']
        )

        predictions = ensemble.predict(sample_data['X_test'])

        # 验证预测形状
        assert predictions.shape == (len(sample_data['X_test']),)

        # 验证预测值不是常数
        assert np.std(predictions) > 0

        # 计算 IC
        ic = np.corrcoef(predictions, sample_data['y_test'])[0, 1]
        assert not np.isnan(ic)


# ==================== 投票法集成测试 ====================

class TestVotingEnsemble:
    """测试投票法集成"""

    def test_initialization(self, mock_models):
        """测试初始化"""
        ensemble = VotingEnsemble(mock_models)
        assert len(ensemble.voting_weights) == 3

    def test_custom_voting_weights(self, mock_models):
        """测试自定义投票权重"""
        weights = [2.0, 1.0, 1.0]
        ensemble = VotingEnsemble(mock_models, voting_weights=weights)
        assert ensemble.voting_weights == weights

    def test_predict(self, mock_models):
        """测试投票预测"""
        ensemble = VotingEnsemble(mock_models)
        X = pd.DataFrame(np.random.randn(5, 3))

        scores = ensemble.predict(X)

        # 验证形状
        assert scores.shape == (5,)

        # 验证分数为非负
        assert np.all(scores >= 0)

    def test_select_top_n(self, mock_models):
        """测试选择 Top N"""
        ensemble = VotingEnsemble(mock_models)
        X = pd.DataFrame(np.random.randn(10, 3))

        top_indices = ensemble.select_top_n(X, top_n=3)

        # 验证数量
        assert len(top_indices) == 3

        # 验证索引有效
        assert np.all(top_indices >= 0)
        assert np.all(top_indices < 10)

    def test_select_top_n_with_scores(self, mock_models):
        """测试选择 Top N 并返回分数"""
        ensemble = VotingEnsemble(mock_models)
        X = pd.DataFrame(np.random.randn(10, 3))

        top_indices, top_scores = ensemble.select_top_n(
            X, top_n=3, return_scores=True
        )

        # 验证数量
        assert len(top_indices) == 3
        assert len(top_scores) == 3

        # 验证分数递减
        assert np.all(top_scores[:-1] >= top_scores[1:])

    def test_predict_real_models(self, trained_models, sample_data):
        """测试使用真实模型的投票预测"""
        ensemble = VotingEnsemble(
            trained_models['models'],
            model_names=trained_models['model_names']
        )

        scores = ensemble.predict(sample_data['X_test'])

        # 验证形状
        assert scores.shape == (len(sample_data['X_test']),)

        # 验证分数不是常数
        assert np.std(scores) > 0

        # 计算与真实值的相关性
        ic = np.corrcoef(scores, sample_data['y_test'])[0, 1]
        assert not np.isnan(ic)


# ==================== Stacking 集成测试 ====================

class TestStackingEnsemble:
    """测试 Stacking 集成"""

    def test_initialization(self, trained_models):
        """测试初始化"""
        ensemble = StackingEnsemble(
            trained_models['models'],
            model_names=trained_models['model_names']
        )

        assert ensemble.n_models == 2
        assert not ensemble.is_meta_trained

    def test_predict_before_training(self, trained_models, sample_data):
        """测试未训练元学习器时预测"""
        ensemble = StackingEnsemble(trained_models['models'])

        with pytest.raises(EnsembleError, match="元学习器未训练"):
            ensemble.predict(sample_data['X_test'])

    def test_train_meta_learner(self, trained_models, sample_data):
        """测试训练元学习器"""
        ensemble = StackingEnsemble(
            trained_models['models'],
            model_names=trained_models['model_names']
        )

        ensemble.train_meta_learner(
            sample_data['X_train'],
            sample_data['y_train'],
            sample_data['X_valid'],
            sample_data['y_valid']
        )

        assert ensemble.is_meta_trained

    def test_predict_after_training(self, trained_models, sample_data):
        """测试训练后预测"""
        ensemble = StackingEnsemble(trained_models['models'])

        ensemble.train_meta_learner(
            sample_data['X_train'],
            sample_data['y_train'],
            sample_data['X_valid'],
            sample_data['y_valid']
        )

        predictions = ensemble.predict(sample_data['X_test'])

        # 验证形状
        assert predictions.shape == (len(sample_data['X_test']),)

        # 验证预测不是常数
        assert np.std(predictions) > 0

        # 计算 IC
        ic = np.corrcoef(predictions, sample_data['y_test'])[0, 1]
        assert not np.isnan(ic)

    def test_use_original_features(self, trained_models, sample_data):
        """测试使用原始特征"""
        ensemble = StackingEnsemble(
            trained_models['models'],
            use_original_features=True
        )

        ensemble.train_meta_learner(
            sample_data['X_train'],
            sample_data['y_train']
        )

        predictions = ensemble.predict(sample_data['X_test'])

        assert predictions.shape == (len(sample_data['X_test']),)

    def test_custom_meta_learner(self, trained_models, sample_data):
        """测试自定义元学习器"""
        custom_meta = RidgeStockModel(alpha=0.1)

        ensemble = StackingEnsemble(
            trained_models['models'],
            meta_learner=custom_meta
        )

        ensemble.train_meta_learner(
            sample_data['X_train'],
            sample_data['y_train']
        )

        predictions = ensemble.predict(sample_data['X_test'])
        assert predictions.shape == (len(sample_data['X_test']),)


# ==================== 便捷函数测试 ====================

class TestCreateEnsemble:
    """测试便捷函数"""

    def test_create_weighted_average(self, mock_models):
        """测试创建加权平均集成"""
        ensemble = create_ensemble(
            mock_models,
            method='weighted_average',
            weights=[0.5, 0.3, 0.2]
        )

        assert isinstance(ensemble, WeightedAverageEnsemble)
        assert np.allclose(ensemble.weights, [0.5, 0.3, 0.2])

    def test_create_voting(self, mock_models):
        """测试创建投票法集成"""
        ensemble = create_ensemble(
            mock_models,
            method='voting'
        )

        assert isinstance(ensemble, VotingEnsemble)

    def test_create_stacking(self, mock_models):
        """测试创建 Stacking 集成"""
        ensemble = create_ensemble(
            mock_models,
            method='stacking'
        )

        assert isinstance(ensemble, StackingEnsemble)

    def test_invalid_method(self, mock_models):
        """测试无效的集成方法"""
        with pytest.raises(ValueError, match="不支持的集成方法"):
            create_ensemble(mock_models, method='invalid_method')


# ==================== 边界条件测试 ====================

class TestEdgeCases:
    """测试边界条件"""

    def test_single_model(self):
        """测试单个模型"""
        mock = Mock()
        mock.predict = Mock(return_value=np.array([1.0, 2.0, 3.0]))

        ensemble = WeightedAverageEnsemble([mock])

        X = pd.DataFrame(np.random.randn(3, 2))
        predictions = ensemble.predict(X)

        # 单模型集成应该等于该模型的预测
        assert np.allclose(predictions, [1.0, 2.0, 3.0])

    def test_incompatible_predictions(self):
        """测试不兼容的预测形状"""
        mock1 = Mock()
        mock1.predict = Mock(return_value=np.array([1.0, 2.0, 3.0]))

        mock2 = Mock()
        mock2.predict = Mock(return_value=np.array([1.0, 2.0]))  # 不同形状

        ensemble = WeightedAverageEnsemble([mock1, mock2])

        X = pd.DataFrame(np.random.randn(3, 2))

        with pytest.raises(IncompatibleModelsError, match="预测形状"):
            ensemble.predict(X)


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试：测试完整工作流"""

    def test_full_workflow_weighted_average(self, trained_models, sample_data):
        """测试加权平均完整工作流"""
        # 创建集成
        ensemble = WeightedAverageEnsemble(
            trained_models['models'],
            model_names=trained_models['model_names']
        )

        # 优化权重
        ensemble.optimize_weights(
            sample_data['X_valid'],
            sample_data['y_valid']
        )

        # 预测
        predictions = ensemble.predict(sample_data['X_test'])

        # 评估
        ic = np.corrcoef(predictions, sample_data['y_test'])[0, 1]

        # 验证集成效果
        ridge_pred = trained_models['ridge'].predict(sample_data['X_test'])
        lgb_pred = trained_models['lgb'].predict(sample_data['X_test'])

        ic_ridge = np.corrcoef(ridge_pred, sample_data['y_test'])[0, 1]
        ic_lgb = np.corrcoef(lgb_pred, sample_data['y_test'])[0, 1]

        # 集成效果应该不差于最差的单模型
        assert ic >= min(ic_ridge, ic_lgb) - 0.1  # 允许小误差

    def test_full_workflow_stacking(self, trained_models, sample_data):
        """测试 Stacking 完整工作流"""
        # 创建集成
        ensemble = StackingEnsemble(
            trained_models['models'],
            model_names=trained_models['model_names']
        )

        # 训练元学习器
        ensemble.train_meta_learner(
            sample_data['X_train'],
            sample_data['y_train'],
            sample_data['X_valid'],
            sample_data['y_valid']
        )

        # 预测
        predictions = ensemble.predict(sample_data['X_test'])

        # 评估
        ic = np.corrcoef(predictions, sample_data['y_test'])[0, 1]

        # 验证 IC 有效
        assert not np.isnan(ic)
        assert abs(ic) <= 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
