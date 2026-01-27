"""
GRU时序模型（深度学习模型）
用于股票时序数据的收益率预测
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
import warnings
import pickle
from pathlib import Path
from loguru import logger

warnings.filterwarnings('ignore')

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    logger.warning("警告: PyTorch未安装，GRU模型不可用")


if PYTORCH_AVAILABLE:
    class StockSequenceDataset(Dataset):
        """股票时序数据集"""

        def __init__(
            self,
            sequences: np.ndarray,
            targets: np.ndarray
        ):
            """
            初始化数据集

            参数:
                sequences: (N, T, F) - N个样本，T个时间步，F个特征
                targets: (N,) - N个目标值
            """
            self.sequences = torch.FloatTensor(sequences)
            self.targets = torch.FloatTensor(targets)

        def __len__(self):
            return len(self.sequences)

        def __getitem__(self, idx):
            return self.sequences[idx], self.targets[idx]


    class GRUStockModel(nn.Module):
        """GRU股票预测模型"""

        def __init__(
            self,
            input_size: int,
            hidden_size: int = 64,
            num_layers: int = 2,
            dropout: float = 0.2,
            bidirectional: bool = False
        ):
            """
            初始化GRU模型

            参数:
                input_size: 输入特征维度
                hidden_size: 隐藏层维度
                num_layers: GRU层数
                dropout: Dropout比例
                bidirectional: 是否双向GRU
            """
            super(GRUStockModel, self).__init__()

            self.input_size = input_size
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.bidirectional = bidirectional

            # GRU层
            self.gru = nn.GRU(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                dropout=dropout if num_layers > 1 else 0,
                batch_first=True,
                bidirectional=bidirectional
            )

            # 全连接层
            fc_input_size = hidden_size * 2 if bidirectional else hidden_size
            self.fc = nn.Sequential(
                nn.Linear(fc_input_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_size, 1)
            )

        def forward(self, x):
            """
            前向传播

            参数:
                x: (batch_size, seq_len, input_size)

            返回:
                预测值: (batch_size, 1)
            """
            # GRU输出
            # output: (batch_size, seq_len, hidden_size * num_directions)
            # hidden: (num_layers * num_directions, batch_size, hidden_size)
            output, hidden = self.gru(x)

            # 取最后一个时间步的输出
            if self.bidirectional:
                # 拼接前向和后向的最后隐藏状态
                hidden = torch.cat((hidden[-2], hidden[-1]), dim=1)
            else:
                hidden = hidden[-1]

            # 全连接层
            out = self.fc(hidden)

            return out.squeeze(-1)


class GRUStockTrainer:
    """GRU模型训练器"""

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        bidirectional: bool = False,
        learning_rate: float = 0.001,
        device: str = None
    ):
        """
        初始化训练器

        参数:
            input_size: 输入特征维度
            hidden_size: 隐藏层维度
            num_layers: GRU层数
            dropout: Dropout比例
            bidirectional: 是否双向
            learning_rate: 学习率
            device: 设备 ('cpu', 'cuda', 'mps')
        """
        if not PYTORCH_AVAILABLE:
            raise ImportError("需要安装PyTorch: pip install torch")

        # 设备选择
        if device is None:
            if torch.cuda.is_available():
                device = 'cuda'
            elif torch.backends.mps.is_available():
                device = 'mps'
            else:
                device = 'cpu'

        self.device = torch.device(device)
        logger.info(f"使用设备: {self.device}")

        # 创建模型
        self.model = GRUStockModel(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            bidirectional=bidirectional
        ).to(self.device)

        # 优化器和损失函数
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.MSELoss()

        # 训练历史
        self.history = {
            'train_loss': [],
            'valid_loss': []
        }

    def create_sequences(
        self,
        data: pd.DataFrame,
        target: pd.Series,
        seq_length: int = 20
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        创建时序序列

        参数:
            data: 特征DataFrame
            target: 目标Series
            seq_length: 序列长度

        返回:
            (sequences, targets)
        """
        sequences = []
        targets = []

        data_array = data.values
        target_array = target.values

        for i in range(len(data) - seq_length):
            seq = data_array[i:i + seq_length]
            tgt = target_array[i + seq_length]

            sequences.append(seq)
            targets.append(tgt)

        return np.array(sequences), np.array(targets)

    def train_epoch(
        self,
        train_loader: 'DataLoader'
    ) -> float:
        """训练一个epoch"""
        self.model.train()
        total_loss = 0

        for sequences, targets in train_loader:
            sequences = sequences.to(self.device)
            targets = targets.to(self.device)

            # 前向传播
            predictions = self.model(sequences)
            loss = self.criterion(predictions, targets)

            # 反向传播
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            total_loss += loss.item()

        return total_loss / len(train_loader)

    def validate(
        self,
        valid_loader: 'DataLoader'
    ) -> float:
        """验证"""
        self.model.eval()
        total_loss = 0

        with torch.no_grad():
            for sequences, targets in valid_loader:
                sequences = sequences.to(self.device)
                targets = targets.to(self.device)

                predictions = self.model(sequences)
                loss = self.criterion(predictions, targets)

                total_loss += loss.item()

        return total_loss / len(valid_loader)

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None,
        seq_length: int = 20,
        batch_size: int = 64,
        epochs: int = 100,
        early_stopping_patience: int = 10,
        verbose: int = 10
    ) -> Dict:
        """
        训练模型

        参数:
            X_train: 训练特征
            y_train: 训练标签
            X_valid: 验证特征
            y_valid: 验证标签
            seq_length: 序列长度
            batch_size: 批次大小
            epochs: 训练轮数
            early_stopping_patience: 早停耐心值
            verbose: 输出间隔

        返回:
            训练历史
        """
        logger.info(f"\n开始训练GRU模型...")
        logger.info(f"序列长度: {seq_length}, 批次大小: {batch_size}, 训练轮数: {epochs}")

        # 创建序列
        logger.info("\n创建训练序列...")
        X_train_seq, y_train_seq = self.create_sequences(X_train, y_train, seq_length)
        logger.info(f"训练序列: {X_train_seq.shape}")

        # 创建数据加载器
        train_dataset = StockSequenceDataset(X_train_seq, y_train_seq)
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True
        )

        # 验证集
        valid_loader = None
        if X_valid is not None and y_valid is not None:
            logger.info("创建验证序列...")
            X_valid_seq, y_valid_seq = self.create_sequences(X_valid, y_valid, seq_length)
            logger.info(f"验证序列: {X_valid_seq.shape}")

            valid_dataset = StockSequenceDataset(X_valid_seq, y_valid_seq)
            valid_loader = DataLoader(
                valid_dataset,
                batch_size=batch_size,
                shuffle=False
            )

        # 训练循环
        best_valid_loss = float('inf')
        patience_counter = 0

        for epoch in range(epochs):
            train_loss = self.train_epoch(train_loader)
            self.history['train_loss'].append(train_loss)

            # 验证
            if valid_loader is not None:
                valid_loss = self.validate(valid_loader)
                self.history['valid_loss'].append(valid_loss)

                # 早停
                if valid_loss < best_valid_loss:
                    best_valid_loss = valid_loss
                    patience_counter = 0
                else:
                    patience_counter += 1

                if patience_counter >= early_stopping_patience:
                    logger.info(f"\nEarly stopping at epoch {epoch + 1}")
                    break

                # 输出
                if (epoch + 1) % verbose == 0:
                    logger.info(f"Epoch {epoch + 1}/{epochs} - "
                          f"Train Loss: {train_loss:.6f}, "
                          f"Valid Loss: {valid_loss:.6f}")
            else:
                if (epoch + 1) % verbose == 0:
                    logger.info(f"Epoch {epoch + 1}/{epochs} - Train Loss: {train_loss:.6f}")

        logger.success(f"\n✓ 训练完成")

        return self.history

    def predict(
        self,
        X: pd.DataFrame,
        seq_length: int = 20,
        batch_size: int = 64
    ) -> np.ndarray:
        """
        预测

        参数:
            X: 特征DataFrame
            seq_length: 序列长度
            batch_size: 批次大小

        返回:
            预测值数组
        """
        self.model.eval()

        # 创建序列（使用0作为占位符目标）
        sequences, _ = self.create_sequences(
            X,
            pd.Series(np.zeros(len(X))),
            seq_length
        )

        # 创建数据加载器
        dataset = StockSequenceDataset(sequences, np.zeros(len(sequences)))
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

        # 预测
        predictions = []
        with torch.no_grad():
            for sequences, _ in loader:
                sequences = sequences.to(self.device)
                preds = self.model(sequences)
                predictions.extend(preds.cpu().numpy())

        return np.array(predictions)

    def save_model(
        self,
        model_path: str
    ):
        """保存模型"""
        model_path = Path(model_path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存模型权重
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'model_config': {
                'input_size': self.model.input_size,
                'hidden_size': self.model.hidden_size,
                'num_layers': self.model.num_layers,
                'bidirectional': self.model.bidirectional
            },
            'history': self.history
        }, model_path)

        logger.success(f"✓ 模型已保存至: {model_path}")

    def load_model(
        self,
        model_path: str
    ):
        """加载模型"""
        checkpoint = torch.load(model_path, map_location=self.device)

        # 重建模型
        config = checkpoint['model_config']
        self.model = GRUStockModel(
            input_size=config['input_size'],
            hidden_size=config['hidden_size'],
            num_layers=config['num_layers'],
            bidirectional=config['bidirectional']
        ).to(self.device)

        # 加载权重
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.history = checkpoint.get('history', {'train_loss': [], 'valid_loss': []})

        logger.success(f"✓ 模型已加载: {model_path}")


# ==================== 使用示例 ====================

if __name__ == "__main__":
    if not PYTORCH_AVAILABLE:
        logger.info("PyTorch未安装，无法运行测试")
        exit(1)

    logger.info("GRU模型测试\n")

    # 创建测试数据
    np.random.seed(42)
    n_samples = 1000
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
    X_train, X_valid = X[:split_idx], X[split_idx:]
    y_train, y_valid = y[:split_idx], y[split_idx:]

    logger.info("数据准备:")
    logger.info(f"  训练集: {len(X_train)} 样本")
    logger.info(f"  验证集: {len(X_valid)} 样本")
    logger.info(f"  特征数: {len(X.columns)}")

    # 训练模型
    logger.info("\n训练GRU模型:")
    trainer = GRUStockTrainer(
        input_size=n_features,
        hidden_size=32,
        num_layers=2,
        dropout=0.2,
        learning_rate=0.001
    )

    history = trainer.train(
        X_train, y_train,
        X_valid, y_valid,
        seq_length=20,
        batch_size=32,
        epochs=50,
        early_stopping_patience=5,
        verbose=10
    )

    # 预测
    logger.info("\n预测:")
    y_pred_train = trainer.predict(X_train, seq_length=20)
    y_pred_valid = trainer.predict(X_valid, seq_length=20)

    logger.info(f"训练集预测数量: {len(y_pred_train)}")
    logger.info(f"验证集预测数量: {len(y_pred_valid)}")

    # 保存和加载
    logger.info("\n保存模型:")
    trainer.save_model('test_gru_model.pth')

    logger.success("\n✓ GRU模型测试完成")
