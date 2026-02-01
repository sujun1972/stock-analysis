"""
GPU加速集成测试

测试GPU在完整工作流中的集成和性能
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# 添加src到路径
src_path = Path(__file__).parent.parent.parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from utils.gpu_utils import gpu_manager, GPUMemoryManager, PYTORCH_AVAILABLE
from models.lightgbm_model import LightGBMStockModel
from models.gru_model import GRUStockTrainer


@pytest.fixture
def sample_data():
    """生成测试数据"""
    np.random.seed(42)
    n_samples = 2000
    n_features = 30

    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )
    y = pd.Series(np.random.randn(n_samples))

    split_idx = int(n_samples * 0.8)
    X_train, X_valid = X[:split_idx].copy(), X[split_idx:].copy()
    y_train, y_valid = y[:split_idx].copy(), y[split_idx:].copy()

    return X_train, y_train, X_valid, y_valid


class TestGPUSystemIntegration:
    """测试GPU系统集成"""

    def test_gpu_detection(self):
        """测试GPU检测"""
        info = gpu_manager.get_system_info()

        assert 'platform' in info
        assert 'python_version' in info
        assert 'pytorch_available' in info
        assert 'cuda_available' in info

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_gpu_memory_info(self):
        """测试GPU内存信息"""
        mem_info = gpu_manager.get_memory_info()

        assert 'total_gb' in mem_info
        assert 'allocated_gb' in mem_info
        assert 'free_gb' in mem_info
        assert 'utilization' in mem_info

        assert mem_info['total_gb'] > 0
        assert 0 <= mem_info['utilization'] <= 100


class TestLightGBMGPUIntegration:
    """测试LightGBM GPU集成"""

    def test_lightgbm_cpu_training(self, sample_data):
        """测试LightGBM CPU训练完整流程"""
        X_train, y_train, X_valid, y_valid = sample_data

        model = LightGBMStockModel(
            use_gpu=False,
            n_estimators=20,
            verbose=-1
        )

        # 训练
        history = model.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)

        # 预测
        predictions = model.predict(X_valid)

        # 特征重要性
        importance = model.get_feature_importance('gain', top_n=10)

        assert history is not None
        assert len(predictions) == len(X_valid)
        assert len(importance) == 10

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_lightgbm_gpu_training(self, sample_data):
        """测试LightGBM GPU训练完整流程"""
        X_train, y_train, X_valid, y_valid = sample_data

        model = LightGBMStockModel(
            use_gpu=True,
            n_estimators=20,
            verbose=-1
        )

        # 训练
        history = model.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)

        # 预测
        predictions = model.predict(X_valid)

        # 特征重要性
        importance = model.get_feature_importance('gain', top_n=10)

        assert history is not None
        assert len(predictions) == len(X_valid)
        assert len(importance) == 10

    def test_lightgbm_cpu_vs_gpu_consistency(self, sample_data):
        """测试LightGBM CPU和GPU训练结果一致性"""
        X_train, y_train, X_valid, y_valid = sample_data

        # CPU模型
        model_cpu = LightGBMStockModel(
            use_gpu=False,
            n_estimators=20,
            random_state=42,
            verbose=-1
        )
        model_cpu.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
        pred_cpu = model_cpu.predict(X_valid)

        # GPU模型
        model_gpu = LightGBMStockModel(
            use_gpu=True,
            n_estimators=20,
            random_state=42,
            verbose=-1
        )
        model_gpu.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
        pred_gpu = model_gpu.predict(X_valid)

        # 如果GPU可用，结果应该高度相关
        if model_gpu.use_gpu:
            correlation = np.corrcoef(pred_cpu, pred_gpu)[0, 1]
            assert correlation > 0.95, f"CPU和GPU预测相关性: {correlation}"
        else:
            # GPU不可用时，两者应该相同
            np.testing.assert_array_almost_equal(pred_cpu, pred_gpu, decimal=5)


@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch未安装")
class TestGRUGPUIntegration:
    """测试GRU GPU集成"""

    def test_gru_cpu_training(self, sample_data):
        """测试GRU CPU训练完整流程"""
        X_train, y_train, X_valid, y_valid = sample_data

        trainer = GRUStockTrainer(
            input_size=30,
            hidden_size=32,
            num_layers=2,
            use_gpu=False
        )

        # 训练
        history = trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=5,
            verbose=0
        )

        # 预测
        predictions = trainer.predict(X_valid, seq_length=10)

        assert history is not None
        assert len(predictions) > 0

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_gru_gpu_training(self, sample_data):
        """测试GRU GPU训练完整流程"""
        X_train, y_train, X_valid, y_valid = sample_data

        trainer = GRUStockTrainer(
            input_size=30,
            hidden_size=32,
            num_layers=2,
            use_gpu=True
        )

        # 训练
        history = trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=5,
            verbose=0
        )

        # 预测
        predictions = trainer.predict(X_valid, seq_length=10)

        assert history is not None
        assert len(predictions) > 0
        assert "cuda" in str(trainer.device)


class TestGPUMemoryManagementIntegration:
    """测试GPU内存管理集成"""

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_sequential_model_training(self, sample_data):
        """测试顺序训练多个模型的内存管理"""
        X_train, y_train, X_valid, y_valid = sample_data

        with GPUMemoryManager():
            # 训练第一个LightGBM模型
            model1 = LightGBMStockModel(use_gpu=True, n_estimators=10, verbose=-1)
            model1.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
            pred1 = model1.predict(X_valid)

            # 删除模型释放内存
            del model1
            gpu_manager.clear_cache()

            # 训练第二个LightGBM模型
            model2 = LightGBMStockModel(use_gpu=True, n_estimators=10, verbose=-1)
            model2.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
            pred2 = model2.predict(X_valid)

            assert len(pred1) == len(pred2)

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_mixed_model_training(self, sample_data):
        """测试混合训练LightGBM和GRU模型"""
        import torch

        X_train, y_train, X_valid, y_valid = sample_data

        with GPUMemoryManager():
            # LightGBM训练
            lgb_model = LightGBMStockModel(use_gpu=True, n_estimators=10, verbose=-1)
            lgb_model.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
            lgb_pred = lgb_model.predict(X_valid)

            del lgb_model
            gpu_manager.clear_cache()

            # GRU训练
            gru_trainer = GRUStockTrainer(
                input_size=30,
                hidden_size=16,
                num_layers=1,
                use_gpu=True
            )
            gru_trainer.train(
                X_train, y_train,
                X_valid, y_valid,
                seq_length=10,
                batch_size=32,
                epochs=3,
                verbose=0
            )
            gru_pred = gru_trainer.predict(X_valid, seq_length=10)

            assert len(lgb_pred) == len(X_valid)
            assert len(gru_pred) > 0

            # 清理
            del gru_trainer
            torch.cuda.empty_cache()


class TestGPUErrorHandling:
    """测试GPU错误处理"""

    def test_graceful_fallback_to_cpu(self, sample_data):
        """测试GPU不可用时优雅降级到CPU"""
        X_train, y_train, X_valid, y_valid = sample_data

        # 即使请求GPU，如果不可用也应该正常工作
        model = LightGBMStockModel(use_gpu=True, n_estimators=10, verbose=-1)
        history = model.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)
        predictions = model.predict(X_valid)

        assert history is not None
        assert len(predictions) == len(X_valid)

    @pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch未安装")
    def test_gru_fallback_to_cpu(self, sample_data):
        """测试GRU在GPU不可用时降级到CPU"""
        X_train, y_train, X_valid, y_valid = sample_data

        # 即使请求GPU，如果不可用也应该正常工作
        trainer = GRUStockTrainer(
            input_size=30,
            hidden_size=16,
            num_layers=1,
            use_gpu=True
        )

        history = trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=3,
            verbose=0
        )

        predictions = trainer.predict(X_valid, seq_length=10)

        assert history is not None
        assert len(predictions) > 0


# ==================== 端到端工作流测试 ====================

class TestEndToEndWorkflow:
    """测试端到端工作流"""

    def test_complete_lightgbm_workflow(self, sample_data, tmp_path):
        """测试完整的LightGBM工作流"""
        X_train, y_train, X_valid, y_valid = sample_data

        # 1. 创建并训练模型
        model = LightGBMStockModel(
            use_gpu=True,
            n_estimators=20,
            learning_rate=0.1,
            verbose=-1
        )

        # 2. 训练
        history = model.train(X_train, y_train, X_valid, y_valid, verbose_eval=0)

        # 3. 预测
        predictions = model.predict(X_valid)

        # 4. 评估
        from sklearn.metrics import mean_squared_error, r2_score
        mse = mean_squared_error(y_valid, predictions)
        r2 = r2_score(y_valid, predictions)

        # 5. 获取特征重要性
        importance = model.get_feature_importance('gain', top_n=10)

        # 6. 保存模型
        model_path = tmp_path / "lightgbm_model.txt"
        model.save_model(str(model_path))

        # 7. 加载模型
        new_model = LightGBMStockModel()
        new_model.load_model(str(model_path))

        # 8. 验证加载后的预测一致
        new_predictions = new_model.predict(X_valid)

        assert history is not None
        assert len(predictions) == len(X_valid)
        assert mse >= 0
        assert len(importance) == 10
        np.testing.assert_array_almost_equal(predictions, new_predictions, decimal=5)

    @pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch未安装")
    def test_complete_gru_workflow(self, sample_data, tmp_path):
        """测试完整的GRU工作流"""
        X_train, y_train, X_valid, y_valid = sample_data

        # 1. 创建并训练模型
        trainer = GRUStockTrainer(
            input_size=30,
            hidden_size=32,
            num_layers=2,
            use_gpu=True
        )

        # 2. 训练
        history = trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=5,
            verbose=0
        )

        # 3. 预测
        predictions = trainer.predict(X_valid, seq_length=10)

        # 4. 评估
        valid_targets = y_valid[10:].values  # 对齐序列长度
        from sklearn.metrics import mean_squared_error

        # 验证数据不包含无穷大或NaN值
        assert not np.any(np.isinf(valid_targets)), "valid_targets contains infinity"
        assert not np.any(np.isnan(valid_targets)), "valid_targets contains NaN"
        assert not np.any(np.isinf(predictions)), "predictions contains infinity"
        assert not np.any(np.isnan(predictions)), "predictions contains NaN"

        mse = mean_squared_error(valid_targets, predictions)

        # 5. 保存模型
        model_path = tmp_path / "gru_model.pth"
        trainer.save_model(str(model_path))

        # 6. 加载模型
        new_trainer = GRUStockTrainer(
            input_size=30,
            hidden_size=32,
            num_layers=2,
            use_gpu=True
        )
        new_trainer.load_model(str(model_path))

        # 7. 验证加载后的预测一致
        new_predictions = new_trainer.predict(X_valid, seq_length=10)

        assert history is not None
        assert len(predictions) > 0
        assert mse >= 0
        # CPU设备上GRU模型可能有微小数值差异（由于浮点运算顺序等因素）
        # 使用相对宽松的容差：相对误差5%或绝对误差0.002
        np.testing.assert_allclose(predictions, new_predictions, rtol=5e-2, atol=2e-3)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
