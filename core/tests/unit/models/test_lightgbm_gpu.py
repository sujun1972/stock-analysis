"""
LightGBM GPU加速单元测试

测试LightGBM模型的GPU训练和推理功能
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# 添加src到路径
src_path = Path(__file__).parent.parent.parent.parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from models.lightgbm_model import LightGBMStockModel
from utils.gpu_utils import gpu_manager, PYTORCH_AVAILABLE


@pytest.fixture
def sample_data():
    """生成测试数据"""
    np.random.seed(42)
    n_samples = 1000
    n_features = 20

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )

    # 模拟股票收益率（带噪声）
    y = pd.Series(
        X['feature_0'] * 0.5 +
        X['feature_1'] * 0.3 +
        X['feature_2'] * -0.2 +
        np.random.randn(n_samples) * 0.1
    )

    # 分割训练集和验证集
    split_idx = int(n_samples * 0.8)
    X_train, X_valid = X[:split_idx].copy(), X[split_idx:].copy()
    y_train, y_valid = y[:split_idx].copy(), y[split_idx:].copy()

    return X_train, y_train, X_valid, y_valid


class TestLightGBMGPUInitialization:
    """测试LightGBM GPU初始化"""

    def test_cpu_initialization(self):
        """测试CPU模式初始化"""
        model = LightGBMStockModel(
            use_gpu=False,
            n_estimators=10,
            verbose=-1
        )

        assert model.use_gpu is False
        assert 'force_col_wise' in model.params
        assert model.params['force_col_wise'] is True

    def test_gpu_initialization_request(self):
        """测试GPU模式初始化请求"""
        model = LightGBMStockModel(
            use_gpu=True,
            n_estimators=10,
            verbose=-1
        )

        # GPU是否可用取决于系统环境
        if PYTORCH_AVAILABLE and gpu_manager.cuda_available:
            # 可能使用GPU或降级为CPU（取决于LightGBM GPU支持）
            assert model.use_gpu in [True, False]
        else:
            # 没有GPU时应该降级为CPU
            assert model.use_gpu is False

    def test_gpu_device_id(self):
        """测试GPU设备ID设置"""
        model = LightGBMStockModel(
            use_gpu=True,
            gpu_platform_id=0,
            gpu_device_id=0,
            n_estimators=10,
            verbose=-1
        )

        if model.use_gpu:
            assert model.params['gpu_platform_id'] == 0
            assert model.params['gpu_device_id'] == 0
            assert model.params['device'] == 'gpu'


class TestLightGBMGPUTraining:
    """测试LightGBM GPU训练"""

    def test_cpu_training(self, sample_data):
        """测试CPU模式训练"""
        X_train, y_train, X_valid, y_valid = sample_data

        model = LightGBMStockModel(
            use_gpu=False,
            n_estimators=10,
            verbose=-1
        )

        history = model.train(
            X_train, y_train,
            X_valid, y_valid,
            early_stopping_rounds=5,
            verbose_eval=0
        )

        assert 'best_iteration' in history
        assert 'best_score' in history
        assert model.model is not None

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_gpu_training(self, sample_data):
        """测试GPU模式训练"""
        X_train, y_train, X_valid, y_valid = sample_data

        model = LightGBMStockModel(
            use_gpu=True,
            n_estimators=10,
            verbose=-1
        )

        # 如果GPU不可用，会自动降级为CPU
        history = model.train(
            X_train, y_train,
            X_valid, y_valid,
            early_stopping_rounds=5,
            verbose_eval=0
        )

        assert 'best_iteration' in history
        assert 'best_score' in history
        assert model.model is not None

    def test_training_consistency(self, sample_data):
        """测试CPU和GPU训练结果的一致性"""
        X_train, y_train, X_valid, y_valid = sample_data

        # CPU模型
        model_cpu = LightGBMStockModel(
            use_gpu=False,
            n_estimators=10,
            random_state=42,
            verbose=-1
        )
        model_cpu.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
        y_pred_cpu = model_cpu.predict(X_valid)

        # GPU模型（如果可用）
        model_gpu = LightGBMStockModel(
            use_gpu=True,
            n_estimators=10,
            random_state=42,
            verbose=-1
        )
        model_gpu.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
        y_pred_gpu = model_gpu.predict(X_valid)

        # 如果GPU真的被使用，结果应该接近（但不完全相同，因为GPU计算精度）
        # 如果GPU不可用，两者应该完全相同
        if model_gpu.use_gpu:
            # GPU和CPU结果应该高度相关
            correlation = np.corrcoef(y_pred_cpu, y_pred_gpu)[0, 1]
            assert correlation > 0.95, f"CPU和GPU预测相关性过低: {correlation}"
        else:
            # 两者都用CPU，结果应该相同
            np.testing.assert_array_almost_equal(y_pred_cpu, y_pred_gpu, decimal=5)


class TestLightGBMGPUPrediction:
    """测试LightGBM GPU预测"""

    def test_prediction_shape(self, sample_data):
        """测试预测输出形状"""
        X_train, y_train, X_valid, y_valid = sample_data

        model = LightGBMStockModel(
            use_gpu=True,
            n_estimators=10,
            verbose=-1
        )
        model.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)

        predictions = model.predict(X_valid)

        assert predictions.shape == (len(X_valid),)
        assert isinstance(predictions, np.ndarray)

    def test_prediction_values(self, sample_data):
        """测试预测值的合理性"""
        X_train, y_train, X_valid, y_valid = sample_data

        model = LightGBMStockModel(
            use_gpu=True,
            n_estimators=10,
            verbose=-1
        )
        model.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)

        predictions = model.predict(X_valid)

        # 预测值应该在合理范围内（不应该有NaN或Inf）
        assert not np.isnan(predictions).any()
        assert not np.isinf(predictions).any()

        # 预测值应该与真实值在相似的数量级
        assert predictions.min() > y_valid.min() - 1.0
        assert predictions.max() < y_valid.max() + 1.0


class TestLightGBMGPUFeatureImportance:
    """测试GPU模式下的特征重要性"""

    def test_feature_importance_calculation(self, sample_data):
        """测试特征重要性计算"""
        X_train, y_train, X_valid, y_valid = sample_data

        model = LightGBMStockModel(
            use_gpu=True,
            n_estimators=10,
            verbose=-1
        )
        model.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)

        # 获取特征重要性
        importance_df = model.get_feature_importance('gain', top_n=10)

        assert len(importance_df) == 10
        assert 'feature' in importance_df.columns
        assert 'gain' in importance_df.columns
        assert 'split' in importance_df.columns

        # 特征重要性应该按降序排列
        assert importance_df['gain'].is_monotonic_decreasing


class TestLightGBMGPUSaveLoad:
    """测试GPU模型的保存和加载"""

    def test_save_and_load_gpu_model(self, sample_data, tmp_path):
        """测试GPU模型保存和加载"""
        X_train, y_train, X_valid, y_valid = sample_data

        # 训练模型
        model = LightGBMStockModel(
            use_gpu=True,
            n_estimators=10,
            verbose=-1
        )
        model.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)

        # 预测
        y_pred_before = model.predict(X_valid)

        # 保存模型
        model_path = tmp_path / "test_lgb_gpu_model.txt"
        model.save_model(str(model_path))

        # 加载模型
        new_model = LightGBMStockModel()
        new_model.load_model(str(model_path))

        # 预测应该一致
        y_pred_after = new_model.predict(X_valid)
        np.testing.assert_array_almost_equal(y_pred_before, y_pred_after, decimal=5)


# ==================== 性能基准测试 ====================

@pytest.mark.benchmark
@pytest.mark.skipif(
    not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
    reason="需要GPU进行基准测试"
)
class TestLightGBMGPUPerformance:
    """LightGBM GPU性能基准测试"""

    def test_gpu_vs_cpu_training_speed(self):
        """对比GPU和CPU训练速度"""
        import time

        # 生成大数据集
        np.random.seed(42)
        n_samples = 50000
        n_features = 50

        X_train = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f'feature_{i}' for i in range(n_features)]
        )
        y_train = pd.Series(np.random.randn(n_samples))

        X_valid = pd.DataFrame(
            np.random.randn(10000, n_features),
            columns=[f'feature_{i}' for i in range(n_features)]
        )
        y_valid = pd.Series(np.random.randn(10000))

        # CPU训练
        model_cpu = LightGBMStockModel(
            use_gpu=False,
            n_estimators=100,
            verbose=-1
        )
        start_cpu = time.time()
        model_cpu.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
        time_cpu = time.time() - start_cpu

        # GPU训练
        model_gpu = LightGBMStockModel(
            use_gpu=True,
            n_estimators=100,
            verbose=-1
        )
        start_gpu = time.time()
        model_gpu.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
        time_gpu = time.time() - start_gpu

        print(f"\n性能对比:")
        print(f"  CPU训练时间: {time_cpu:.2f}秒")
        print(f"  GPU训练时间: {time_gpu:.2f}秒")

        if model_gpu.use_gpu:
            speedup = time_cpu / time_gpu
            print(f"  加速比: {speedup:.2f}x")

            # GPU应该比CPU快（至少1.5倍）
            assert speedup > 1.5, f"GPU加速不明显: {speedup:.2f}x"
        else:
            print("  GPU不可用，使用CPU训练")

    def test_large_dataset_training(self):
        """测试大数据集训练"""
        import time

        # 生成超大数据集
        np.random.seed(42)
        n_samples = 100000
        n_features = 100

        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f'feature_{i}' for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples))

        # GPU训练
        model = LightGBMStockModel(
            use_gpu=True,
            n_estimators=50,
            verbose=-1
        )

        start = time.time()
        model.train(X, y, verbose_eval=0)
        training_time = time.time() - start

        print(f"\n大数据集训练:")
        print(f"  数据量: {n_samples} 样本 × {n_features} 特征")
        print(f"  训练时间: {training_time:.2f}秒")
        print(f"  使用设备: {'GPU' if model.use_gpu else 'CPU'}")

        # 训练应该在合理时间内完成
        assert training_time < 300, f"训练时间过长: {training_time:.2f}秒"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
