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
            # 使用torch.from_numpy避免在macOS上的段错误
            # 确保输入是float32类型的numpy数组
            sequences = np.asarray(sequences, dtype=np.float32)
            targets = np.asarray(targets, dtype=np.float32)

            self.sequences = torch.from_numpy(sequences).float()
            self.targets = torch.from_numpy(targets).float()

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
    """GRU模型训练器（支持GPU加速）"""

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.2,
        bidirectional: bool = False,
        learning_rate: float = 0.001,
        device: str = None,
        use_gpu: bool = True,
        batch_size: int = None,
        num_workers: int = 4
    ):
        """
        初始化训练器（支持GPU加速）

        参数:
            input_size: 输入特征维度
            hidden_size: 隐藏层维度
            num_layers: GRU层数
            dropout: Dropout比例
            bidirectional: 是否双向
            learning_rate: 学习率
            device: 设备 ('cpu', 'cuda', 'mps'，None表示自动选择)
            use_gpu: 是否优先使用GPU（默认True）
            batch_size: 批次大小（None表示自动计算）
            num_workers: DataLoader工作进程数（默认4）
        """
        if not PYTORCH_AVAILABLE:
            raise ImportError("需要安装PyTorch: pip install torch")

        # macOS上使用多进程DataLoader可能导致段错误，强制设为0
        import platform
        if platform.system() == 'Darwin' and num_workers > 0:
            logger.warning(f"检测到macOS系统，将num_workers从{num_workers}设为0以避免多进程问题")
            num_workers = 0

        # 尝试导入GPU管理器
        try:
            from src.utils.gpu_utils import gpu_manager
            self.gpu_manager = gpu_manager
        except ImportError:
            self.gpu_manager = None
            logger.warning("GPU管理器未安装")

        # 设备选择（优先使用GPU管理器）
        if device is None:
            if self.gpu_manager is not None:
                device = self.gpu_manager.get_device(prefer_gpu=use_gpu)
            elif use_gpu and torch.cuda.is_available():
                device = 'cuda'
            elif use_gpu and torch.backends.mps.is_available():
                # MPS在RNN训练中数值不稳定，建议使用CPU
                logger.warning("检测到MPS设备，但GRU/RNN在MPS上可能数值不稳定")
                logger.warning("建议使用use_gpu=False强制使用CPU，或等待PyTorch MPS优化")
                device = 'mps'
            else:
                device = 'cpu'

        self.device = torch.device(device)
        logger.info(f"🚀 GRU模型使用设备: {self.device}")

        # 创建模型并移到设备
        self.model = GRUStockModel(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            bidirectional=bidirectional
        ).to(self.device)

        # 自动计算批次大小
        if batch_size is None and 'cuda' in str(self.device) and self.gpu_manager is not None:
            # 估算模型大小
            model_size_mb = sum(
                p.numel() * p.element_size()
                for p in self.model.parameters()
            ) / (1024 ** 2)

            # 估算样本大小（假设序列长度20）
            sample_size_mb = (input_size * 20 * 4) / (1024 ** 2)

            self.batch_size = self.gpu_manager.get_optimal_batch_size(
                model_size_mb, sample_size_mb
            )
            logger.info(f"自动设置批次大小: {self.batch_size}")
        else:
            self.batch_size = batch_size or 64

        self.num_workers = num_workers

        # 优化器和损失函数
        # PyTorch 2.10在macOS上Adam优化器存在段错误问题，使用SGD with momentum
        import platform
        if platform.system() == 'Darwin':
            logger.warning("检测到macOS系统，使用SGD优化器代替Adam避免段错误")
            self.optimizer = optim.SGD(
                self.model.parameters(),
                lr=learning_rate,
                momentum=0.9
            )
        else:
            self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)

        self.criterion = nn.MSELoss()

        # 学习率调度器
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5
        )

        # 混合精度训练（针对较新的GPU）
        self.use_amp = 'cuda' in str(self.device) and torch.cuda.get_device_capability()[0] >= 7
        self.scaler = torch.cuda.amp.GradScaler() if self.use_amp else None

        if self.use_amp:
            logger.info("✨ 启用混合精度训练（AMP）")

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
        """训练一个epoch（GPU优化版）"""
        self.model.train()
        total_loss = 0
        num_batches = 0

        for sequences, targets in train_loader:
            sequences = sequences.to(self.device, non_blocking=True)
            targets = targets.to(self.device, non_blocking=True)

            self.optimizer.zero_grad(set_to_none=True)  # 更高效的梯度清零

            if self.use_amp:
                # 混合精度训练
                with torch.cuda.amp.autocast():
                    predictions = self.model(sequences)
                    loss = self.criterion(predictions, targets)

                self.scaler.scale(loss).backward()
                self.scaler.step(self.optimizer)
                self.scaler.update()
            else:
                # 标准训练
                predictions = self.model(sequences)
                loss = self.criterion(predictions, targets)

                # 检查loss是否有效
                if not torch.isfinite(loss):
                    logger.warning(f"检测到无效loss值: {loss.item()}，跳过此批次")
                    continue

                loss.backward()
                self.optimizer.step()

            total_loss += loss.item()
            num_batches += 1

        # 防止除零错误
        return total_loss / num_batches if num_batches > 0 else 0.0

    def validate(
        self,
        valid_loader: 'DataLoader'
    ) -> float:
        """验证（GPU优化版）"""
        self.model.eval()
        total_loss = 0
        num_batches = 0

        with torch.no_grad():
            for sequences, targets in valid_loader:
                sequences = sequences.to(self.device, non_blocking=True)
                targets = targets.to(self.device, non_blocking=True)

                predictions = self.model(sequences)
                loss = self.criterion(predictions, targets)

                total_loss += loss.item()
                num_batches += 1

        # 防止除零错误
        return total_loss / num_batches if num_batches > 0 else 0.0

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None,
        seq_length: int = 20,
        batch_size: int = None,
        epochs: int = 100,
        early_stopping_patience: int = 10,
        verbose: int = 10
    ) -> Dict:
        """
        训练模型（GPU优化版）

        参数:
            X_train: 训练特征
            y_train: 训练标签
            X_valid: 验证特征
            y_valid: 验证标签
            seq_length: 序列长度
            batch_size: 批次大小（None表示使用初始化时的自动批次）
            epochs: 训练轮数
            early_stopping_patience: 早停耐心值
            verbose: 输出间隔

        返回:
            训练历史
        """
        # 使用自动批次大小或指定批次
        batch_size = batch_size or self.batch_size

        logger.info(f"\n开始训练GRU模型...")
        logger.info(f"序列长度: {seq_length}, 批次大小: {batch_size}, 训练轮数: {epochs}")

        # 创建序列
        logger.info("\n创建训练序列...")
        X_train_seq, y_train_seq = self.create_sequences(X_train, y_train, seq_length)
        logger.info(f"训练序列: {X_train_seq.shape}")

        # 创建数据加载器（GPU优化）
        # macOS上pin_memory可能导致段错误，仅在CUDA设备上启用
        use_pin_memory = ('cuda' in str(self.device) and torch.cuda.is_available())

        train_dataset = StockSequenceDataset(X_train_seq, y_train_seq)
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=self.num_workers,
            pin_memory=use_pin_memory
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
                shuffle=False,
                num_workers=self.num_workers,
                pin_memory=use_pin_memory
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

                # 学习率调整
                self.scheduler.step(valid_loss)

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
                if verbose > 0 and (epoch + 1) % verbose == 0:
                    logger.info(f"Epoch {epoch + 1}/{epochs} - "
                          f"Train Loss: {train_loss:.6f}, "
                          f"Valid Loss: {valid_loss:.6f}")
            else:
                if verbose > 0 and (epoch + 1) % verbose == 0:
                    logger.info(f"Epoch {epoch + 1}/{epochs} - Train Loss: {train_loss:.6f}")

            # 定期清理GPU缓存
            if 'cuda' in str(self.device) and (epoch + 1) % 20 == 0 and self.gpu_manager is not None:
                self.gpu_manager.clear_cache()

        logger.success(f"\n✓ 训练完成")

        return self.history

    def predict(
        self,
        X: pd.DataFrame,
        seq_length: int = 20,
        batch_size: int = None
    ) -> np.ndarray:
        """
        预测（GPU优化版）

        参数:
            X: 特征DataFrame
            seq_length: 序列长度
            batch_size: 批次大小（None表示使用自动批次的2倍）

        返回:
            预测值数组
        """
        self.model.eval()

        # 推理可用更大批次
        batch_size = batch_size or (self.batch_size * 2)

        # 创建序列（使用0作为占位符目标）
        sequences, _ = self.create_sequences(
            X,
            pd.Series(np.zeros(len(X))),
            seq_length
        )

        # 创建数据加载器（GPU优化）
        # macOS上pin_memory可能导致段错误，仅在CUDA设备上启用
        use_pin_memory = ('cuda' in str(self.device) and torch.cuda.is_available())

        dataset = StockSequenceDataset(sequences, np.zeros(len(sequences)))
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=self.num_workers,
            pin_memory=use_pin_memory
        )

        # 预测
        predictions = []
        with torch.no_grad():
            for sequences, _ in loader:
                sequences = sequences.to(self.device, non_blocking=True)
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

        # 重新创建optimizer以匹配新模型
        self.optimizer = optim.Adam(self.model.parameters())
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
