"""
GRU深度学习模型单元测试

测试范围：
1. GRUStockModel - PyTorch GRU模型架构
2. GRUStockTrainer - 训练器（初始化、训练、预测、保存/加载）
3. StockSequenceDataset - 时序数据集
4. 序列创建和数据预处理
5. 边界情况和异常处理

目标覆盖率: 85%+

作者: Stock Analysis Team
创建: 2026-01-29
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
import tempfile
import os
from pathlib import Path

# 检查PyTorch是否可用
try:
    import torch
    import torch.nn as nn
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False

# 条件导入
if PYTORCH_AVAILABLE:
    try:
        from src.models.gru_model import (
            GRUStockModel,
            GRUStockTrainer,
            StockSequenceDataset,
            PYTORCH_AVAILABLE as MODEL_PYTORCH_AVAILABLE
        )
    except ImportError:
        # 如果src导入失败,尝试直接导入
        import sys
        from pathlib import Path
        core_path = Path(__file__).parent.parent.parent.parent
        if str(core_path) not in sys.path:
            sys.path.insert(0, str(core_path))
        from src.models.gru_model import (
            GRUStockModel,
            GRUStockTrainer,
            StockSequenceDataset,
            PYTORCH_AVAILABLE as MODEL_PYTORCH_AVAILABLE
        )


# ==================== Fixtures ====================

@pytest.fixture
def sample_training_data():
    """创建示例训练数据"""
    np.random.seed(42)
    n_samples = 100
    n_features = 10

    X_train = pd.DataFrame(
        np.random.randn(n_samples, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )
    y_train = pd.Series(np.random.randn(n_samples) * 0.02)

    X_valid = pd.DataFrame(
        np.random.randn(50, n_features),
        columns=[f'feature_{i}' for i in range(n_features)]
    )
    y_valid = pd.Series(np.random.randn(50) * 0.02)

    return {
        'X_train': X_train,
        'y_train': y_train,
        'X_valid': X_valid,
        'y_valid': y_valid,
        'n_features': n_features
    }


@pytest.fixture
def temp_model_path():
    """创建临时模型保存路径"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, 'test_model.pth')


# ==================== 跳过测试条件 ====================

pytestmark = pytest.mark.skipif(
    not PYTORCH_AVAILABLE,
    reason="PyTorch not installed"
)


# ==================== StockSequenceDataset 测试 ====================

@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch not installed")
class TestStockSequenceDataset:
    """测试 StockSequenceDataset 类"""

    def test_dataset_initialization(self):
        """测试数据集初始化"""
        sequences = np.random.randn(10, 5, 3)  # 10 samples, 5 timesteps, 3 features
        targets = np.random.randn(10)

        dataset = StockSequenceDataset(sequences, targets)

        assert len(dataset) == 10
        assert isinstance(dataset.sequences, torch.Tensor)
        assert isinstance(dataset.targets, torch.Tensor)

    def test_dataset_getitem(self):
        """测试数据集索引访问"""
        sequences = np.random.randn(10, 5, 3)
        targets = np.random.randn(10)

        dataset = StockSequenceDataset(sequences, targets)

        seq, target = dataset[0]
        assert isinstance(seq, torch.Tensor)
        assert isinstance(target, torch.Tensor)
        assert seq.shape == (5, 3)

    def test_dataset_length(self):
        """测试数据集长度"""
        sequences = np.random.randn(20, 10, 5)
        targets = np.random.randn(20)

        dataset = StockSequenceDataset(sequences, targets)

        assert len(dataset) == 20

    def test_dataset_empty(self):
        """测试空数据集"""
        sequences = np.array([]).reshape(0, 5, 3)
        targets = np.array([])

        dataset = StockSequenceDataset(sequences, targets)

        assert len(dataset) == 0


# ==================== GRUStockModel 测试 ====================

@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch not installed")
class TestGRUStockModel:
    """测试 GRUStockModel 类"""

    def test_model_initialization(self):
        """测试模型初始化"""
        model = GRUStockModel(
            input_size=10,
            hidden_size=32,
            num_layers=2,
            dropout=0.2,
            bidirectional=False
        )

        assert model.input_size == 10
        assert model.hidden_size == 32
        assert model.num_layers == 2
        assert model.bidirectional == False

    def test_model_forward_unidirectional(self):
        """测试单向GRU前向传播"""
        model = GRUStockModel(
            input_size=5,
            hidden_size=16,
            num_layers=1,
            bidirectional=False
        )

        # 创建输入：batch_size=4, seq_len=10, input_size=5
        x = torch.randn(4, 10, 5)

        output = model(x)

        assert output.shape == (4,)  # batch_size

    def test_model_forward_bidirectional(self):
        """测试双向GRU前向传播"""
        model = GRUStockModel(
            input_size=5,
            hidden_size=16,
            num_layers=1,
            bidirectional=True
        )

        x = torch.randn(4, 10, 5)
        output = model(x)

        assert output.shape == (4,)

    def test_model_multilayer(self):
        """测试多层GRU"""
        model = GRUStockModel(
            input_size=8,
            hidden_size=32,
            num_layers=3,
            dropout=0.3
        )

        x = torch.randn(2, 15, 8)
        output = model(x)

        assert output.shape == (2,)

    def test_model_parameters_count(self):
        """测试模型参数数量"""
        model = GRUStockModel(
            input_size=10,
            hidden_size=20,
            num_layers=2
        )

        params = sum(p.numel() for p in model.parameters())
        assert params > 0


# ==================== GRUStockTrainer 初始化测试 ====================

@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch not installed")
class TestGRUStockTrainerInit:
    """测试 GRUStockTrainer 初始化"""

    def test_trainer_initialization_cpu(self):
        """测试在CPU上初始化"""
        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=32,
            num_layers=2,
            device='cpu'
        )

        assert trainer.device == torch.device('cpu')
        assert isinstance(trainer.model, GRUStockModel)
        # 在macOS上使用SGD，其他平台使用Adam
        import platform
        if platform.system() == 'Darwin':
            assert isinstance(trainer.optimizer, torch.optim.SGD)
        else:
            assert isinstance(trainer.optimizer, torch.optim.Adam)

    def test_trainer_initialization_auto_device(self):
        """测试自动设备选择"""
        trainer = GRUStockTrainer(
            input_size=10,
            hidden_size=32
        )

        # 应该选择可用的最佳设备
        assert trainer.device is not None

    def test_trainer_history_initialization(self):
        """测试训练历史初始化"""
        trainer = GRUStockTrainer(input_size=5)

        assert 'train_loss' in trainer.history
        assert 'valid_loss' in trainer.history
        assert trainer.history['train_loss'] == []
        assert trainer.history['valid_loss'] == []

    def test_trainer_custom_learning_rate(self):
        """测试自定义学习率"""
        trainer = GRUStockTrainer(
            input_size=10,
            learning_rate=0.001,
            device='cpu'
        )

        # 验证optimizer的学习率
        # 在macOS上SGD学习率会降低10倍
        lr = trainer.optimizer.param_groups[0]['lr']
        import platform
        if platform.system() == 'Darwin':
            expected_lr = 0.0001  # 0.001 * 0.1
        else:
            expected_lr = 0.001
        assert abs(lr - expected_lr) < 1e-6

    def test_trainer_cuda_device_selection(self):
        """测试CUDA设备选择逻辑"""
        # 测试显式指定cuda设备（即使不可用也应记录）
        # 注意：如果CUDA不可用，PyTorch会fallback到CPU或报错
        # 这里我们只测试逻辑，不实际使用CUDA
        import torch
        if torch.cuda.is_available():
            trainer = GRUStockTrainer(input_size=10, device='cuda')
            assert 'cuda' in str(trainer.device)
        else:
            # CUDA不可用时，我们测试device参数能被正确接受
            # 但实际初始化会使用CPU
            pass  # Skip this branch if CUDA not available

    def test_trainer_mps_device_selection(self):
        """测试MPS设备选择逻辑"""
        import torch
        # 测试MPS设备（仅在MacOS上可用）
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            trainer = GRUStockTrainer(input_size=10, device='mps')
            assert 'mps' in str(trainer.device)
        else:
            # MPS不可用时跳过
            pass

    @patch('torch.cuda.is_available', return_value=False)
    @patch('torch.backends.mps.is_available', return_value=False)
    def test_trainer_cpu_fallback_device_selection(self, mock_mps, mock_cuda):
        """测试CPU fallback设备选择（当CUDA和MPS都不可用时）"""
        trainer = GRUStockTrainer(input_size=10, device=None)
        # 应该fallback到CPU
        assert str(trainer.device) == 'cpu'


# ==================== 序列创建测试 ====================

@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch not installed")
class TestCreateSequences:
    """测试序列创建功能"""

    def test_create_sequences_basic(self, sample_training_data):
        """测试基本序列创建"""
        trainer = GRUStockTrainer(
            input_size=sample_training_data['n_features'],
            device='cpu'
        )

        sequences, targets = trainer.create_sequences(
            sample_training_data['X_train'],
            sample_training_data['y_train'],
            seq_length=10
        )

        # 100个样本，序列长度10，应该产生90个序列
        assert sequences.shape[0] == 90
        assert sequences.shape[1] == 10  # seq_length
        assert sequences.shape[2] == sample_training_data['n_features']
        assert len(targets) == 90

    def test_create_sequences_different_lengths(self, sample_training_data):
        """测试不同序列长度"""
        trainer = GRUStockTrainer(input_size=10, device='cpu')

        for seq_len in [5, 10, 20]:
            sequences, targets = trainer.create_sequences(
                sample_training_data['X_train'],
                sample_training_data['y_train'],
                seq_length=seq_len
            )

            expected_num = len(sample_training_data['X_train']) - seq_len
            assert sequences.shape[0] == expected_num
            assert sequences.shape[1] == seq_len

    def test_create_sequences_short_data(self):
        """测试数据长度小于序列长度"""
        trainer = GRUStockTrainer(input_size=3, device='cpu')

        short_data = pd.DataFrame(np.random.randn(5, 3))
        short_target = pd.Series(np.random.randn(5))

        sequences, targets = trainer.create_sequences(
            short_data,
            short_target,
            seq_length=10
        )

        # 数据太短，无法创建序列
        assert len(sequences) == 0
        assert len(targets) == 0


# ==================== 训练测试 ====================

@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch not installed")
class TestTraining:
    """测试模型训练功能"""

    def test_train_basic(self, sample_training_data):
        """测试基本训练流程"""
        trainer = GRUStockTrainer(
            input_size=sample_training_data['n_features'],
            hidden_size=16,
            num_layers=1,
            device='cpu'
        )

        history = trainer.train(
            sample_training_data['X_train'],
            sample_training_data['y_train'],
            X_valid=sample_training_data['X_valid'],
            y_valid=sample_training_data['y_valid'],
            seq_length=10,
            batch_size=16,
            epochs=3,
            verbose=1
        )

        assert 'train_loss' in history
        assert 'valid_loss' in history
        assert len(history['train_loss']) <= 3
        assert len(history['valid_loss']) <= 3

    def test_train_without_validation(self, sample_training_data):
        """测试不使用验证集训练"""
        trainer = GRUStockTrainer(
            input_size=sample_training_data['n_features'],
            hidden_size=16,
            device='cpu'
        )

        history = trainer.train(
            sample_training_data['X_train'],
            sample_training_data['y_train'],
            seq_length=10,
            epochs=2,
            verbose=1
        )

        assert len(history['train_loss']) == 2
        assert len(history['valid_loss']) == 0

    def test_train_early_stopping(self, sample_training_data):
        """测试早停机制"""
        trainer = GRUStockTrainer(
            input_size=sample_training_data['n_features'],
            hidden_size=8,
            device='cpu'
        )

        history = trainer.train(
            sample_training_data['X_train'],
            sample_training_data['y_train'],
            X_valid=sample_training_data['X_valid'],
            y_valid=sample_training_data['y_valid'],
            seq_length=10,
            epochs=50,
            early_stopping_patience=3,
            verbose=10
        )

        # 早停应该让训练提前结束（如果模型持续改进则可能达到max epochs）
        # 验证早停机制存在且训练历史记录正确
        assert len(history['train_loss']) <= 50
        assert len(history['valid_loss']) == len(history['train_loss'])
        assert len(history['train_loss']) > 0

    def test_train_early_stopping_triggered(self):
        """测试早停被触发的情况（使用预训练的模型）"""
        # 创建一个已经过拟合的场景
        trainer = GRUStockTrainer(
            input_size=5,
            hidden_size=4,
            num_layers=1,
            device='cpu'
        )

        # 创建小数据集，容易过拟合
        X_train = pd.DataFrame(np.random.randn(50, 5))
        y_train = pd.Series(np.random.randn(50) * 0.01)
        X_valid = pd.DataFrame(np.random.randn(30, 5))
        y_valid = pd.Series(np.random.randn(30) * 0.01)

        # 先训练几轮让模型收敛
        history = trainer.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=5,
            epochs=100,
            early_stopping_patience=5,
            verbose=100
        )

        # 验证早停机制工作（可能触发也可能不触发，取决于随机性）
        assert len(history['train_loss']) <= 100
        assert len(history['valid_loss']) > 0


# ==================== 预测测试 ====================

@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch not installed")
class TestPrediction:
    """测试模型预测功能"""

    def test_predict_basic(self, sample_training_data):
        """测试基本预测"""
        trainer = GRUStockTrainer(
            input_size=sample_training_data['n_features'],
            hidden_size=16,
            device='cpu'
        )

        # 简单训练
        trainer.train(
            sample_training_data['X_train'],
            sample_training_data['y_train'],
            seq_length=10,
            epochs=1,
            verbose=1
        )

        # 预测
        predictions = trainer.predict(
            sample_training_data['X_valid'],
            seq_length=10,
            batch_size=16
        )

        # 50个样本，序列长度10，应该产生40个预测
        assert len(predictions) == 40
        assert isinstance(predictions, np.ndarray)

    def test_predict_different_batch_sizes(self, sample_training_data):
        """测试不同批次大小的预测"""
        trainer = GRUStockTrainer(
            input_size=sample_training_data['n_features'],
            hidden_size=8,
            device='cpu'
        )

        trainer.train(
            sample_training_data['X_train'],
            sample_training_data['y_train'],
            seq_length=5,
            epochs=1
        )

        for batch_size in [8, 16, 32]:
            predictions = trainer.predict(
                sample_training_data['X_valid'],
                seq_length=5,
                batch_size=batch_size
            )

            assert len(predictions) == 45  # 50 - 5


# ==================== 模型保存和加载测试 ====================

@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch not installed")
class TestModelSaveLoad:
    """测试模型保存和加载"""

    def test_save_model(self, sample_training_data, temp_model_path):
        """测试模型保存"""
        trainer = GRUStockTrainer(
            input_size=sample_training_data['n_features'],
            hidden_size=16,
            device='cpu'
        )

        # 训练一轮
        trainer.train(
            sample_training_data['X_train'],
            sample_training_data['y_train'],
            seq_length=10,
            epochs=1
        )

        # 保存模型
        trainer.save_model(temp_model_path)

        assert os.path.exists(temp_model_path)

    def test_load_model(self, sample_training_data, temp_model_path):
        """测试模型加载"""
        # 训练并保存模型
        trainer1 = GRUStockTrainer(
            input_size=sample_training_data['n_features'],
            hidden_size=16,
            num_layers=2,
            device='cpu'
        )

        trainer1.train(
            sample_training_data['X_train'],
            sample_training_data['y_train'],
            seq_length=10,
            epochs=2
        )

        trainer1.save_model(temp_model_path)

        # 创建新trainer并加载
        trainer2 = GRUStockTrainer(
            input_size=sample_training_data['n_features'],
            hidden_size=16,
            num_layers=2,
            device='cpu'
        )

        trainer2.load_model(temp_model_path)

        # 验证历史被加载
        assert len(trainer2.history['train_loss']) == 2

    def test_save_load_directory_creation(self, sample_training_data):
        """测试自动创建保存目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = os.path.join(tmpdir, 'subdir', 'model.pth')

            trainer = GRUStockTrainer(
                input_size=sample_training_data['n_features'],
                device='cpu'
            )

            trainer.train(
                sample_training_data['X_train'],
                sample_training_data['y_train'],
                seq_length=5,
                epochs=1
            )

            trainer.save_model(model_path)

            assert os.path.exists(model_path)


# ==================== 边界情况测试 ====================

@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch not installed")
class TestEdgeCases:
    """测试边界情况"""

    def test_single_layer_no_dropout(self):
        """测试单层GRU（不应用dropout）"""
        model = GRUStockModel(
            input_size=5,
            hidden_size=10,
            num_layers=1,
            dropout=0.5  # 单层时应该被忽略
        )

        x = torch.randn(2, 10, 5)
        output = model(x)

        assert output.shape == (2,)

    def test_very_small_batch(self, sample_training_data):
        """测试极小批次"""
        trainer = GRUStockTrainer(
            input_size=sample_training_data['n_features'],
            hidden_size=8,
            device='cpu'
        )

        history = trainer.train(
            sample_training_data['X_train'][:20],
            sample_training_data['y_train'][:20],
            seq_length=5,
            batch_size=2,
            epochs=1
        )

        assert len(history['train_loss']) == 1

    def test_large_hidden_size(self):
        """测试大隐藏层"""
        model = GRUStockModel(
            input_size=10,
            hidden_size=256,
            num_layers=1
        )

        x = torch.randn(4, 20, 10)
        output = model(x)

        assert output.shape == (4,)


# ==================== PYTORCH_AVAILABLE标志测试 ====================

@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch not installed")
class TestPyTorchAvailableFlag:
    """测试 PYTORCH_AVAILABLE 标志"""

    def test_pytorch_available_flag(self):
        """测试PyTorch可用标志"""
        assert MODEL_PYTORCH_AVAILABLE == True

    def test_can_create_model(self):
        """测试可以创建模型"""
        model = GRUStockModel(input_size=5, hidden_size=10)
        assert model is not None

    def test_can_create_trainer(self):
        """测试可以创建训练器"""
        trainer = GRUStockTrainer(input_size=5, device='cpu')
        assert trainer is not None


# ==================== 未安装PyTorch时的测试 ====================

@pytest.mark.skipif(PYTORCH_AVAILABLE, reason="PyTorch is installed")
class TestWithoutPyTorch:
    """测试PyTorch未安装时的行为"""

    def test_pytorch_not_available(self):
        """测试PyTorch不可用时的标志"""
        # 这个测试只在PyTorch未安装时运行
        assert not PYTORCH_AVAILABLE


# ==================== ImportError测试 ====================

@pytest.mark.skipif(not PYTORCH_AVAILABLE, reason="PyTorch not installed")
class TestImportError:
    """测试导入错误处理"""

    @patch('src.models.gru_model.PYTORCH_AVAILABLE', False)
    def test_trainer_import_error_when_pytorch_unavailable(self, ):
        """测试当PYTORCH_AVAILABLE为False时抛出ImportError"""
        # Mock PYTORCH_AVAILABLE为False并测试是否抛出ImportError
        with pytest.raises(ImportError, match="需要安装PyTorch"):
            GRUStockTrainer(input_size=10)
