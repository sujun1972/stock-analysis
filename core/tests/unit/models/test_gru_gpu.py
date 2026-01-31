"""
GRU GPU加速单元测试

测试GRU模型的GPU训练和推理功能
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

from models.gru_model import GRUStockTrainer, PYTORCH_AVAILABLE
from utils.gpu_utils import gpu_manager


# 跳过所有测试如果PyTorch不可用
pytestmark = pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch未安装")


@pytest.fixture
def sample_sequence_data():
    """生成时序测试数据"""
    np.random.seed(42)
    n_samples = 500
    n_features = 10

    # 模拟时序数据
    X = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )

    # 模拟目标（下一期收益率）
    y = pd.Series(np.random.randn(n_samples) * 0.02)

    # 分割训练集和验证集
    split_idx = int(n_samples * 0.8)
    X_train, X_valid = X[:split_idx].copy(), X[split_idx:].copy()
    y_train, y_valid = y[:split_idx].copy(), y[split_idx:].copy()

    return X_train, y_train, X_valid, y_valid


class TestGRUGPUInitialization:
    """测试GRU GPU初始化"""

    def test_cpu_initialization(self):
        """测试CPU模式初始化"""
        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=32,
            num_layers=2,
            use_gpu=False
        )

        assert str(trainer.device) == "cpu"
        assert trainer.model is not None

    def test_gpu_initialization_request(self):
        """测试GPU模式初始化请求"""
        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=32,
            num_layers=2,
            use_gpu=True
        )

        # GPU是否可用取决于系统环境
        import torch
        device_str = str(trainer.device)

        # 接受任何可用的加速设备：CUDA、MPS或CPU
        assert device_str in ["cuda", "mps", "cpu"] or "cuda" in device_str

    def test_auto_batch_size(self):
        """测试自动批次大小计算"""
        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=32,
            num_layers=2,
            use_gpu=True,
            batch_size=None  # 自动计算
        )

        assert trainer.batch_size is not None
        assert 16 <= trainer.batch_size <= 1024

    def test_manual_batch_size(self):
        """测试手动设置批次大小"""
        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=32,
            num_layers=2,
            use_gpu=True,
            batch_size=128
        )

        assert trainer.batch_size == 128

    def test_mixed_precision_detection(self):
        """测试混合精度训练检测"""
        import torch

        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=32,
            num_layers=2,
            use_gpu=True
        )

        if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 7:
            assert trainer.use_amp is True
            assert trainer.scaler is not None
        else:
            # CPU或旧GPU不支持混合精度
            pass


class TestGRUGPUTraining:
    """测试GRU GPU训练"""

    def test_cpu_training(self, sample_sequence_data):
        """测试CPU模式训练"""
        X_train, y_train, X_valid, y_valid = sample_sequence_data

        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=16,
            num_layers=1,
            use_gpu=False
        )

        history = trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=5,
            early_stopping_patience=3,
            verbose=0
        )

        assert 'train_loss' in history
        assert 'valid_loss' in history
        assert len(history['train_loss']) <= 5
        assert len(history['valid_loss']) <= 5

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_gpu_training(self, sample_sequence_data):
        """测试GPU模式训练"""
        X_train, y_train, X_valid, y_valid = sample_sequence_data

        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=16,
            num_layers=1,
            use_gpu=True
        )

        history = trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=5,
            early_stopping_patience=3,
            verbose=0
        )

        assert 'train_loss' in history
        assert 'valid_loss' in history
        assert "cuda" in str(trainer.device) or str(trainer.device) == "cpu"

    def test_training_convergence(self, sample_sequence_data):
        """测试训练收敛性"""
        import platform
        X_train, y_train, X_valid, y_valid = sample_sequence_data

        # macOS上MPS设备训练GRU数值不稳定，使用CPU
        use_gpu = False if platform.system() == 'Darwin' else True

        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=32,
            num_layers=2,
            use_gpu=use_gpu,
            learning_rate=0.01
        )

        history = trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=20,
            early_stopping_patience=5,
            verbose=0
        )

        # 训练损失应该下降
        initial_loss = history['train_loss'][0]
        final_loss = history['train_loss'][-1]
        assert final_loss < initial_loss

    def test_early_stopping(self, sample_sequence_data):
        """测试早停机制"""
        X_train, y_train, X_valid, y_valid = sample_sequence_data

        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=16,
            num_layers=1,
            use_gpu=True
        )

        history = trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=100,
            early_stopping_patience=3,
            verbose=0
        )

        # 应该早停，不会训练满100轮
        assert len(history['train_loss']) < 100


class TestGRUGPUPrediction:
    """测试GRU GPU预测"""

    def test_prediction_shape(self, sample_sequence_data):
        """测试预测输出形状"""
        X_train, y_train, X_valid, y_valid = sample_sequence_data

        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=16,
            num_layers=1,
            use_gpu=True
        )

        trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=5,
            verbose=0
        )

        predictions = trainer.predict(X_valid, seq_length=10)

        # 预测数量 = 总样本数 - 序列长度
        expected_length = len(X_valid) - 10
        assert len(predictions) == expected_length
        assert isinstance(predictions, np.ndarray)

    def test_prediction_values(self, sample_sequence_data):
        """测试预测值的合理性"""
        import platform
        X_train, y_train, X_valid, y_valid = sample_sequence_data

        # macOS上MPS设备训练GRU数值不稳定，使用CPU
        use_gpu = False if platform.system() == 'Darwin' else True

        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=16,
            num_layers=1,
            use_gpu=use_gpu
        )

        trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=5,
            verbose=0
        )

        predictions = trainer.predict(X_valid, seq_length=10)

        # 预测值应该不包含NaN或Inf
        assert not np.isnan(predictions).any()
        assert not np.isinf(predictions).any()

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_gpu_prediction_speed(self, sample_sequence_data):
        """测试GPU预测速度"""
        import time

        X_train, y_train, X_valid, y_valid = sample_sequence_data

        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=32,
            num_layers=2,
            use_gpu=True
        )

        trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=5,
            verbose=0
        )

        start = time.time()
        predictions = trainer.predict(X_valid, seq_length=10)
        prediction_time = time.time() - start

        # 预测应该很快（< 1秒）
        assert prediction_time < 1.0
        assert len(predictions) > 0


class TestGRUGPUSaveLoad:
    """测试GRU GPU模型的保存和加载"""

    def test_save_and_load_gpu_model(self, sample_sequence_data, tmp_path):
        """测试GPU模型保存和加载"""
        X_train, y_train, X_valid, y_valid = sample_sequence_data

        # 训练模型
        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=16,
            num_layers=1,
            use_gpu=True
        )

        trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=5,
            verbose=0
        )

        # 预测
        y_pred_before = trainer.predict(X_valid, seq_length=10)

        # 保存模型
        model_path = tmp_path / "test_gru_gpu_model.pth"
        trainer.save_model(str(model_path))

        # 加载模型
        new_trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=16,
            num_layers=1,
            use_gpu=True
        )
        new_trainer.load_model(str(model_path))

        # 预测应该一致
        y_pred_after = new_trainer.predict(X_valid, seq_length=10)
        np.testing.assert_array_almost_equal(y_pred_before, y_pred_after, decimal=4)


class TestGRUGPUMemoryManagement:
    """测试GRU GPU内存管理"""

    @pytest.mark.skipif(
        not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
        reason="需要GPU"
    )
    def test_memory_cleanup(self, sample_sequence_data):
        """测试内存清理"""
        import torch
        X_train, y_train, X_valid, y_valid = sample_sequence_data

        # 记录初始内存
        initial_mem = gpu_manager.get_memory_info()

        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=32,
            num_layers=2,
            use_gpu=True
        )

        trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=10,
            batch_size=32,
            epochs=5,
            verbose=0
        )

        # 删除模型
        del trainer
        torch.cuda.empty_cache()

        # 内存应该被释放
        final_mem = gpu_manager.get_memory_info()
        # 允许一定的内存波动
        assert final_mem['allocated_gb'] <= initial_mem['allocated_gb'] + 1.0


# ==================== 性能基准测试 ====================

@pytest.mark.benchmark
@pytest.mark.skipif(
    not PYTORCH_AVAILABLE or not hasattr(gpu_manager, 'cuda_available') or not gpu_manager.cuda_available,
    reason="需要GPU进行基准测试"
)
class TestGRUGPUPerformance:
    """GRU GPU性能基准测试"""

    def test_gpu_vs_cpu_training_speed(self):
        """对比GPU和CPU训练速度"""
        import time
        import torch

        # 生成大数据集
        np.random.seed(42)
        n_samples = 2000
        n_features = 50

        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f'feature_{i}' for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples) * 0.02)

        split_idx = int(n_samples * 0.8)
        X_train, X_valid = X[:split_idx], X[split_idx:]
        y_train, y_valid = y[:split_idx], y[split_idx:]

        # CPU训练
        trainer_cpu = GRUStockTrainer(
            input_size=50,
            hidden_size=64,
            num_layers=2,
            use_gpu=False
        )
        start_cpu = time.time()
        trainer_cpu.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=20,
            batch_size=64,
            epochs=10,
            verbose=0
        )
        time_cpu = time.time() - start_cpu

        # GPU训练
        trainer_gpu = GRUStockTrainer(
            input_size=50,
            hidden_size=64,
            num_layers=2,
            use_gpu=True
        )
        start_gpu = time.time()
        trainer_gpu.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=20,
            batch_size=64,
            epochs=10,
            verbose=0
        )
        time_gpu = time.time() - start_gpu

        print(f"\n性能对比:")
        print(f"  CPU训练时间: {time_cpu:.2f}秒")
        print(f"  GPU训练时间: {time_gpu:.2f}秒")

        if torch.cuda.is_available():
            speedup = time_cpu / time_gpu
            print(f"  加速比: {speedup:.2f}x")

            # GPU应该比CPU快（至少1.5倍）
            assert speedup > 1.5, f"GPU加速不明显: {speedup:.2f}x"

        # 清理
        del trainer_cpu, trainer_gpu
        torch.cuda.empty_cache()

    def test_mixed_precision_performance(self):
        """测试混合精度训练性能"""
        import time
        import torch

        # 只在支持混合精度的GPU上测试
        if not torch.cuda.is_available() or torch.cuda.get_device_capability()[0] < 7:
            pytest.skip("需要支持混合精度的GPU (Compute Capability >= 7.0)")

        # 生成数据
        np.random.seed(42)
        n_samples = 2000
        n_features = 50

        X = pd.DataFrame(
            np.random.randn(n_samples, n_features),
            columns=[f'feature_{i}' for i in range(n_features)]
        )
        y = pd.Series(np.random.randn(n_samples) * 0.02)

        split_idx = int(n_samples * 0.8)
        X_train, X_valid = X[:split_idx], X[split_idx:]
        y_train, y_valid = y[:split_idx], y[split_idx:]

        # 不使用混合精度
        trainer_fp32 = GRUStockTrainer(
            input_size=50,
            hidden_size=128,
            num_layers=3,
            use_gpu=True
        )
        # 手动禁用混合精度
        trainer_fp32.use_amp = False
        trainer_fp32.scaler = None

        start_fp32 = time.time()
        trainer_fp32.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=20,
            batch_size=64,
            epochs=10,
            verbose=0
        )
        time_fp32 = time.time() - start_fp32

        # 使用混合精度
        trainer_amp = GRUStockTrainer(
            input_size=50,
            hidden_size=128,
            num_layers=3,
            use_gpu=True
        )

        start_amp = time.time()
        trainer_amp.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=20,
            batch_size=64,
            epochs=10,
            verbose=0
        )
        time_amp = time.time() - start_amp

        print(f"\n混合精度性能:")
        print(f"  FP32训练时间: {time_fp32:.2f}秒")
        print(f"  AMP训练时间: {time_amp:.2f}秒")

        if trainer_amp.use_amp:
            speedup = time_fp32 / time_amp
            print(f"  加速比: {speedup:.2f}x")

            # 混合精度应该更快
            assert speedup > 1.0, f"混合精度没有加速: {speedup:.2f}x"

        # 清理
        del trainer_fp32, trainer_amp
        torch.cuda.empty_cache()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
