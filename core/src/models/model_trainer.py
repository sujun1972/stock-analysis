"""
统一模型训练器
提供统一接口训练和评估不同类型的模型
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple, Union
from pathlib import Path
import warnings
import json

warnings.filterwarnings('ignore')

from .lightgbm_model import LightGBMStockModel
from .model_evaluator import ModelEvaluator


class ModelTrainer:
    """统一模型训练器"""

    def __init__(
        self,
        model_type: str = 'lightgbm',
        model_params: dict = None,
        output_dir: str = 'data/models/saved'
    ):
        """
        初始化训练器

        参数:
            model_type: 模型类型 ('lightgbm', 'gru')
            model_params: 模型参数字典
            output_dir: 模型保存目录
        """
        self.model_type = model_type
        self.model_params = model_params or {}
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.evaluator = ModelEvaluator()
        self.training_history = {}

    def prepare_data(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        train_ratio: float = 0.7,
        valid_ratio: float = 0.15,
        remove_nan: bool = True
    ) -> Tuple:
        """
        准备训练数据

        参数:
            df: 完整数据DataFrame
            feature_cols: 特征列名列表
            target_col: 目标列名
            train_ratio: 训练集比例
            valid_ratio: 验证集比例
            remove_nan: 是否移除NaN值

        返回:
            (X_train, y_train, X_valid, y_valid, X_test, y_test)
        """
        print(f"\n准备数据...")
        print(f"原始数据: {len(df)} 行 × {len(df.columns)} 列")

        # 提取特征和目标
        X = df[feature_cols].copy()
        y = df[target_col].copy()

        # 移除NaN
        if remove_nan:
            valid_mask = ~(X.isna().any(axis=1) | y.isna())
            X = X[valid_mask]
            y = y[valid_mask]
            print(f"移除NaN后: {len(X)} 行")

        # 时间序列分割（不打乱顺序）
        n_samples = len(X)
        train_end = int(n_samples * train_ratio)
        valid_end = int(n_samples * (train_ratio + valid_ratio))

        X_train = X.iloc[:train_end]
        y_train = y.iloc[:train_end]

        X_valid = X.iloc[train_end:valid_end]
        y_valid = y.iloc[train_end:valid_end]

        X_test = X.iloc[valid_end:]
        y_test = y.iloc[valid_end:]

        print(f"\n数据分割:")
        print(f"  训练集: {len(X_train)} 样本 ({len(X_train)/n_samples*100:.1f}%)")
        print(f"  验证集: {len(X_valid)} 样本 ({len(X_valid)/n_samples*100:.1f}%)")
        print(f"  测试集: {len(X_test)} 样本 ({len(X_test)/n_samples*100:.1f}%)")
        print(f"  特征数: {len(feature_cols)}")

        return X_train, y_train, X_valid, y_valid, X_test, y_test

    def train_lightgbm(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None,
        early_stopping_rounds: int = 50,
        verbose_eval: int = 50
    ):
        """训练LightGBM模型"""
        print(f"\n训练LightGBM模型...")

        # 默认参数
        default_params = {
            'objective': 'regression',
            'metric': 'rmse',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'n_estimators': 500,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'verbose': -1
        }

        # 合并用户参数
        params = {**default_params, **self.model_params}

        # 创建模型
        self.model = LightGBMStockModel(**params)

        # 训练
        history = self.model.train(
            X_train, y_train,
            X_valid, y_valid,
            early_stopping_rounds=early_stopping_rounds,
            verbose_eval=verbose_eval
        )

        self.training_history = history

    def train_gru(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None,
        seq_length: int = 20,
        batch_size: int = 64,
        epochs: int = 100,
        early_stopping_patience: int = 10
    ):
        """训练GRU模型"""
        print(f"\n训练GRU模型...")

        try:
            from .gru_model import GRUStockTrainer
        except ImportError:
            raise ImportError("GRU模型需要PyTorch: pip install torch")

        # 默认参数
        default_params = {
            'input_size': len(X_train.columns),
            'hidden_size': 64,
            'num_layers': 2,
            'dropout': 0.2,
            'learning_rate': 0.001
        }

        # 合并用户参数
        params = {**default_params, **self.model_params}

        # 创建模型
        self.model = GRUStockTrainer(**params)

        # 训练
        history = self.model.train(
            X_train, y_train,
            X_valid, y_valid,
            seq_length=seq_length,
            batch_size=batch_size,
            epochs=epochs,
            early_stopping_patience=early_stopping_patience
        )

        self.training_history = history

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None,
        **kwargs
    ):
        """
        训练模型（自动根据model_type选择）

        参数:
            X_train: 训练特征
            y_train: 训练标签
            X_valid: 验证特征
            y_valid: 验证标签
            **kwargs: 其他训练参数
        """
        if self.model_type == 'lightgbm':
            self.train_lightgbm(X_train, y_train, X_valid, y_valid, **kwargs)
        elif self.model_type == 'gru':
            self.train_gru(X_train, y_train, X_valid, y_valid, **kwargs)
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")

    def evaluate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        dataset_name: str = 'test',
        verbose: bool = True
    ) -> Dict[str, float]:
        """
        评估模型

        参数:
            X: 特征
            y: 标签
            dataset_name: 数据集名称
            verbose: 是否打印结果

        返回:
            评估指标字典
        """
        if self.model is None:
            raise ValueError("模型未训练")

        print(f"\n评估 {dataset_name} 集...")

        # 预测
        if self.model_type == 'lightgbm':
            predictions = self.model.predict(X)
        elif self.model_type == 'gru':
            predictions = self.model.predict(X)
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")

        # 评估
        metrics = self.evaluator.evaluate_regression(
            predictions,
            y.values,
            verbose=verbose
        )

        return metrics

    def save_model(
        self,
        model_name: str,
        save_metrics: bool = True
    ):
        """
        保存模型

        参数:
            model_name: 模型名称
            save_metrics: 是否保存评估指标
        """
        if self.model is None:
            raise ValueError("模型未训练")

        # 模型文件路径
        if self.model_type == 'lightgbm':
            model_path = self.output_dir / f"{model_name}.txt"
        elif self.model_type == 'gru':
            model_path = self.output_dir / f"{model_name}.pth"
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")

        # 保存模型
        self.model.save_model(str(model_path))

        # 保存训练配置和指标
        if save_metrics:
            meta_path = self.output_dir / f"{model_name}_meta.json"
            meta_data = {
                'model_type': self.model_type,
                'model_params': self.model_params,
                'training_history': self.training_history,
                'evaluation_metrics': self.evaluator.get_metrics()
            }

            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta_data, f, indent=2, ensure_ascii=False)

            print(f"✓ 元数据已保存至: {meta_path}")

    def load_model(
        self,
        model_name: str
    ):
        """
        加载模型

        参数:
            model_name: 模型名称
        """
        # 加载元数据
        meta_path = self.output_dir / f"{model_name}_meta.json"
        if meta_path.exists():
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta_data = json.load(f)

            self.model_type = meta_data.get('model_type', self.model_type)
            self.model_params = meta_data.get('model_params', {})
            self.training_history = meta_data.get('training_history', {})

        # 加载模型
        if self.model_type == 'lightgbm':
            model_path = self.output_dir / f"{model_name}.txt"
            self.model = LightGBMStockModel()
            self.model.load_model(str(model_path))
        elif self.model_type == 'gru':
            from .gru_model import GRUStockTrainer
            model_path = self.output_dir / f"{model_name}.pth"
            self.model = GRUStockTrainer(**self.model_params)
            self.model.load_model(str(model_path))
        else:
            raise ValueError(f"不支持的模型类型: {self.model_type}")


# ==================== 便捷函数 ====================

def train_stock_model(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    model_type: str = 'lightgbm',
    model_params: dict = None,
    train_ratio: float = 0.7,
    valid_ratio: float = 0.15,
    save_path: str = None
) -> Tuple[object, Dict[str, float]]:
    """
    便捷函数：训练股票预测模型

    参数:
        df: 数据DataFrame
        feature_cols: 特征列
        target_col: 目标列
        model_type: 模型类型
        model_params: 模型参数
        train_ratio: 训练集比例
        valid_ratio: 验证集比例
        save_path: 保存路径

    返回:
        (训练器对象, 测试集评估指标)
    """
    # 创建训练器
    trainer = ModelTrainer(
        model_type=model_type,
        model_params=model_params
    )

    # 准备数据
    X_train, y_train, X_valid, y_valid, X_test, y_test = trainer.prepare_data(
        df, feature_cols, target_col,
        train_ratio=train_ratio,
        valid_ratio=valid_ratio
    )

    # 训练模型
    trainer.train(X_train, y_train, X_valid, y_valid)

    # 评估模型
    test_metrics = trainer.evaluate(X_test, y_test, dataset_name='test')

    # 保存模型
    if save_path:
        trainer.save_model(save_path)

    return trainer, test_metrics


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("模型训练器测试\n")

    # 创建测试数据
    np.random.seed(42)
    n_samples = 1000
    n_features = 20

    dates = pd.date_range('2020-01-01', periods=n_samples, freq='D')

    # 模拟特征
    features = {}
    for i in range(n_features):
        features[f'feature_{i}'] = np.random.randn(n_samples)

    # 模拟目标（未来5日收益率）
    target = (
        features['feature_0'] * 0.5 +
        features['feature_1'] * 0.3 +
        np.random.randn(n_samples) * 0.02
    )

    df = pd.DataFrame(features, index=dates)
    df['target'] = target

    print("测试数据:")
    print(f"  样本数: {len(df)}")
    print(f"  特征数: {n_features}")
    print(df.head())

    # 准备特征列表
    feature_cols = [f'feature_{i}' for i in range(n_features)]

    # 测试LightGBM
    print("\n" + "="*60)
    print("测试 LightGBM 模型")
    print("="*60)

    trainer_lgb = ModelTrainer(
        model_type='lightgbm',
        model_params={
            'learning_rate': 0.1,
            'n_estimators': 100,
            'num_leaves': 31
        }
    )

    X_train, y_train, X_valid, y_valid, X_test, y_test = trainer_lgb.prepare_data(
        df, feature_cols, 'target',
        train_ratio=0.7,
        valid_ratio=0.15
    )

    trainer_lgb.train(X_train, y_train, X_valid, y_valid, verbose_eval=20)

    # 评估
    test_metrics = trainer_lgb.evaluate(X_test, y_test, dataset_name='test')

    # 保存
    trainer_lgb.save_model('test_lgb_model')

    print("\n✓ 模型训练器测试完成")
