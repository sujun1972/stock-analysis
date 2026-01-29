"""
GRU模型完整单元测试
测试PyTorch GRU深度学习模型的数据集、模型、训练、预测、保存/加载等功能
目标：将覆盖率从14%提升至90%+
"""

import unittest
import pandas as pd
import numpy as np
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import warnings
import sys

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# 尝试导入PyTorch
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False

# 导入模型模块
from models.gru_model import PYTORCH_AVAILABLE as MODEL_PYTORCH_AVAILABLE

if MODEL_PYTORCH_AVAILABLE:
    from models.gru_model import (
        StockSequenceDataset,
        GRUStockModel,
        GRUStockTrainer
    )


@unittest.skipIf(not PYTORCH_AVAILABLE, "PyTorch未安装，跳过GRU模型测试")
class TestStockSequenceDataset(unittest.TestCase):
    """测试股票时序数据集类"""

    @classmethod
    def setUpClass(cls):
        """设置测试数据"""
        np.random.seed(42)
        cls.n_samples = 100
        cls.seq_length = 10
        cls.n_features = 5
        cls.sequences = np.random.randn(cls.n_samples, cls.seq_length, cls.n_features)
        cls.targets = np.random.randn(cls.n_samples)

    def test_01_dataset_initialization(self):
        """测试数据集初始化"""
        dataset = StockSequenceDataset(self.sequences, self.targets)
        self.assertIsInstance(dataset.sequences, torch.FloatTensor)
        self.assertIsInstance(dataset.targets, torch.FloatTensor)
        self.assertEqual(dataset.sequences.shape, (self.n_samples, self.seq_length, self.n_features))
        self.assertEqual(dataset.targets.shape, (self.n_samples,))

    def test_02_dataset_length(self):
        """测试数据集长度"""
        dataset = StockSequenceDataset(self.sequences, self.targets)
        self.assertEqual(len(dataset), self.n_samples)

    def test_03_dataset_getitem(self):
        """测试数据集索引访问"""
        dataset = StockSequenceDataset(self.sequences, self.targets)
        seq, target = dataset[0]
        self.assertEqual(seq.shape, (self.seq_length, self.n_features))
        self.assertIsInstance(seq, torch.Tensor)
        self.assertIsInstance(target, torch.Tensor)

    def test_04_dataset_dataloader_integration(self):
        """测试数据集与DataLoader集成"""
        dataset = StockSequenceDataset(self.sequences, self.targets)
        dataloader = DataLoader(dataset, batch_size=16, shuffle=False)
        batch_count = 0
        for sequences_batch, targets_batch in dataloader:
            batch_count += 1
            self.assertEqual(sequences_batch.shape[1], self.seq_length)
            self.assertEqual(sequences_batch.shape[2], self.n_features)
        expected_batches = (self.n_samples + 15) // 16
        self.assertEqual(batch_count, expected_batches)


@unittest.skipIf(not PYTORCH_AVAILABLE, "PyTorch未安装，跳过GRU模型测试")
class TestGRUStockModel(unittest.TestCase):
    """测试GRU股票预测模型"""

    def test_01_model_initialization(self):
        """测试模型初始化"""
        model = GRUStockModel(input_size=10, hidden_size=32, num_layers=2, dropout=0.2, bidirectional=False)
        self.assertEqual(model.input_size, 10)
        self.assertEqual(model.hidden_size, 32)
        self.assertEqual(model.num_layers, 2)
        self.assertFalse(model.bidirectional)
        self.assertIsNotNone(model.gru)
        self.assertIsNotNone(model.fc)

    def test_02_model_forward_unidirectional(self):
        """测试单向GRU前向传播"""
        model = GRUStockModel(input_size=8, hidden_size=16, num_layers=2, bidirectional=False)
        x = torch.randn(4, 20, 8)
        output = model(x)
        self.assertEqual(output.shape, (4,))
        self.assertFalse(torch.isnan(output).any())

    def test_03_model_forward_bidirectional(self):
        """测试双向GRU前向传播"""
        model = GRUStockModel(input_size=8, hidden_size=16, num_layers=2, bidirectional=True)
        x = torch.randn(4, 20, 8)
        output = model(x)
        self.assertEqual(output.shape, (4,))
        self.assertFalse(torch.isnan(output).any())

    def test_04_model_different_batch_sizes(self):
        """测试不同批次大小"""
        model = GRUStockModel(input_size=5, hidden_size=16, num_layers=1)
        for batch_size in [1, 4, 16, 32]:
            x = torch.randn(batch_size, 10, 5)
            output = model(x)
            self.assertEqual(output.shape, (batch_size,))


@unittest.skipIf(not PYTORCH_AVAILABLE, "PyTorch未安装，跳过GRU模型测试")
class TestGRUStockTrainer(unittest.TestCase):
    """测试GRU模型训练器"""

    @classmethod
    def setUpClass(cls):
        np.random.seed(42)
        torch.manual_seed(42)
        cls.n_samples = 200
        cls.n_features = 8
        cls.X = pd.DataFrame(np.random.randn(cls.n_samples, cls.n_features), 
                            columns=[f'feature_{i}' for i in range(cls.n_features)])
        cls.y = pd.Series(cls.X['feature_0'] * 0.5 + cls.X['feature_1'] * 0.3 + np.random.randn(cls.n_samples) * 0.1)
        split_idx = int(cls.n_samples * 0.7)
        cls.X_train, cls.X_valid = cls.X[:split_idx], cls.X[split_idx:]
        cls.y_train, cls.y_valid = cls.y[:split_idx], cls.y[split_idx:]
        cls.temp_dir = tempfile.mkdtemp()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temp_dir)

    def test_01_trainer_initialization(self):
        """测试训练器初始化"""
        trainer = GRUStockTrainer(input_size=self.n_features, hidden_size=32, num_layers=2, 
                                 dropout=0.2, learning_rate=0.001, device='cpu')
        self.assertEqual(trainer.device.type, 'cpu')
        self.assertIsNotNone(trainer.model)
        self.assertIsInstance(trainer.model, GRUStockModel)
        self.assertIn('train_loss', trainer.history)

    def test_02_create_sequences(self):
        """测试序列创建"""
        trainer = GRUStockTrainer(input_size=self.n_features, device='cpu')
        sequences, targets = trainer.create_sequences(self.X, self.y, seq_length=10)
        expected_samples = len(self.X) - 10
        self.assertEqual(sequences.shape, (expected_samples, 10, self.n_features))
        self.assertEqual(targets.shape, (expected_samples,))

    def test_03_create_sequences_different_lengths(self):
        """测试不同序列长度"""
        trainer = GRUStockTrainer(input_size=self.n_features, device='cpu')
        for seq_length in [5, 10, 20, 30]:
            sequences, targets = trainer.create_sequences(self.X, self.y, seq_length)
            self.assertEqual(len(sequences), len(self.X) - seq_length)

    def test_04_train_epoch(self):
        """测试单个epoch训练"""
        trainer = GRUStockTrainer(input_size=self.n_features, hidden_size=16, num_layers=1, device='cpu')
        sequences, targets = trainer.create_sequences(self.X_train, self.y_train, seq_length=10)
        dataset = StockSequenceDataset(sequences, targets)
        dataloader = DataLoader(dataset, batch_size=16, shuffle=True)
        loss = trainer.train_epoch(dataloader)
        self.assertIsInstance(loss, float)
        self.assertGreater(loss, 0)
        self.assertFalse(np.isnan(loss))

    def test_05_validate(self):
        """测试验证"""
        trainer = GRUStockTrainer(input_size=self.n_features, hidden_size=16, num_layers=1, device='cpu')
        sequences, targets = trainer.create_sequences(self.X_valid, self.y_valid, seq_length=10)
        dataset = StockSequenceDataset(sequences, targets)
        dataloader = DataLoader(dataset, batch_size=16, shuffle=False)
        loss = trainer.validate(dataloader)
        self.assertIsInstance(loss, float)
        self.assertGreater(loss, 0)

    def test_06_train_with_validation(self):
        """测试完整训练流程（带验证集）"""
        trainer = GRUStockTrainer(input_size=self.n_features, hidden_size=16, num_layers=1, 
                                 learning_rate=0.01, device='cpu')
        history = trainer.train(X_train=self.X_train, y_train=self.y_train, 
                               X_valid=self.X_valid, y_valid=self.y_valid,
                               seq_length=10, batch_size=16, epochs=5, verbose=5)
        self.assertIn('train_loss', history)
        self.assertIn('valid_loss', history)
        self.assertGreater(len(history['train_loss']), 0)

    def test_07_train_without_validation(self):
        """测试训练流程（无验证集）"""
        trainer = GRUStockTrainer(input_size=self.n_features, hidden_size=16, num_layers=1, device='cpu')
        history = trainer.train(X_train=self.X_train, y_train=self.y_train, X_valid=None, y_valid=None,
                               seq_length=10, batch_size=16, epochs=3, verbose=1)
        self.assertIn('train_loss', history)
        self.assertEqual(len(history['valid_loss']), 0)

    def test_08_early_stopping(self):
        """测试早停机制"""
        trainer = GRUStockTrainer(input_size=self.n_features, hidden_size=16, num_layers=1, device='cpu')
        history = trainer.train(X_train=self.X_train, y_train=self.y_train, 
                               X_valid=self.X_valid, y_valid=self.y_valid,
                               seq_length=10, batch_size=16, epochs=100, 
                               early_stopping_patience=2, verbose=-1)
        self.assertLess(len(history['train_loss']), 100)

    def test_09_predict(self):
        """测试预测"""
        trainer = GRUStockTrainer(input_size=self.n_features, hidden_size=16, num_layers=1, device='cpu')
        trainer.train(X_train=self.X_train, y_train=self.y_train, seq_length=10, 
                     batch_size=16, epochs=2, verbose=-1)
        predictions = trainer.predict(self.X_valid, seq_length=10)
        expected_length = len(self.X_valid) - 10
        self.assertEqual(len(predictions), expected_length)
        self.assertFalse(np.any(np.isnan(predictions)))

    def test_10_save_model(self):
        """测试模型保存"""
        trainer = GRUStockTrainer(input_size=self.n_features, hidden_size=16, num_layers=1, device='cpu')
        trainer.train(X_train=self.X_train, y_train=self.y_train, seq_length=10, 
                     batch_size=16, epochs=2, verbose=-1)
        model_path = Path(self.temp_dir) / 'test_gru_model.pth'
        trainer.save_model(str(model_path))
        self.assertTrue(model_path.exists())

    def test_11_load_model(self):
        """测试模型加载"""
        trainer1 = GRUStockTrainer(input_size=self.n_features, hidden_size=16, num_layers=1, device='cpu')
        trainer1.train(X_train=self.X_train, y_train=self.y_train, seq_length=10, 
                      batch_size=16, epochs=3, verbose=-1)
        predictions1 = trainer1.predict(self.X_valid, seq_length=10)
        model_path = Path(self.temp_dir) / 'test_gru_model.pth'
        trainer1.save_model(str(model_path))
        trainer2 = GRUStockTrainer(input_size=self.n_features, device='cpu')
        trainer2.load_model(str(model_path))
        predictions2 = trainer2.predict(self.X_valid, seq_length=10)
        np.testing.assert_array_almost_equal(predictions1, predictions2, decimal=5)


@unittest.skipIf(not PYTORCH_AVAILABLE, "PyTorch未安装，跳过GRU模型测试")
class TestGRUModelEdgeCases(unittest.TestCase):
    """GRU模型边界情况测试"""

    def test_01_small_dataset(self):
        """测试小数据集"""
        X_small = pd.DataFrame(np.random.randn(50, 5), columns=[f'f_{i}' for i in range(5)])
        y_small = pd.Series(np.random.randn(50))
        trainer = GRUStockTrainer(input_size=5, hidden_size=8, num_layers=1, device='cpu')
        history = trainer.train(X_train=X_small, y_train=y_small, seq_length=5, 
                               batch_size=8, epochs=2, verbose=-1)
        self.assertGreater(len(history['train_loss']), 0)

    def test_02_bidirectional_model(self):
        """测试双向GRU模型"""
        X = pd.DataFrame(np.random.randn(100, 5), columns=[f'f_{i}' for i in range(5)])
        y = pd.Series(np.random.randn(100))
        trainer = GRUStockTrainer(input_size=5, hidden_size=16, num_layers=2, 
                                 bidirectional=True, device='cpu')
        trainer.train(X_train=X, y_train=y, seq_length=10, batch_size=16, epochs=2, verbose=-1)
        predictions = trainer.predict(X, seq_length=10)
        self.assertEqual(len(predictions), len(X) - 10)


@unittest.skipIf(PYTORCH_AVAILABLE, "PyTorch已安装，跳过此测试")
class TestGRUModelWithoutPyTorch(unittest.TestCase):
    """测试PyTorch未安装时的处理"""

    def test_01_import_error_handling(self):
        """测试导入错误处理"""
        from models.gru_model import PYTORCH_AVAILABLE
        self.assertFalse(PYTORCH_AVAILABLE)


def run_tests():
    """运行测试"""
    warnings.filterwarnings('ignore')
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
