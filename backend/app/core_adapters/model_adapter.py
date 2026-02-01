"""
机器学习模型适配器 (Model Adapter)

将 Core 的机器学习模块包装为异步方法，供 FastAPI 使用。

核心功能:
- 异步模型训练 (GRU, LightGBM, Ridge 等)
- 异步模型预测
- 异步模型评估
- 异步超参数调优
- 模型版本管理

作者: Backend Team
创建日期: 2026-02-01
版本: 1.0.0
"""

import asyncio
import sys
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# 添加 core 项目到 Python 路径
core_path = Path(__file__).parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

# 导入 Core 模块
from src.models.model_trainer import ModelTrainer
from src.models.lightgbm_model import LightGBMStockModel
from src.models.ridge_model import RidgeStockModel
from src.models.model_evaluator import ModelEvaluator
from src.models.hyperparameter_tuner import HyperparameterTuner
from src.models.model_registry import ModelRegistry
from src.models.ensemble import ModelEnsemble
from src.exceptions import ModelError, ModelTrainingError


class ModelAdapter:
    """
    Core 机器学习模块的异步适配器

    包装 Core 的模型训练、评估、预测功能，将同步方法转换为异步方法。

    示例:
        >>> adapter = ModelAdapter()
        >>> model = await adapter.train_model(
        ...     X_train, y_train, X_test, y_test,
        ...     model_type='LightGBM'
        ... )
        >>> predictions = await adapter.predict(model, X_test)
    """

    def __init__(self, model_dir: Optional[Path] = None):
        """
        初始化模型适配器

        Args:
            model_dir: 模型保存目录
        """
        self.model_dir = model_dir or Path("./models")
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # 模型注册表
        self.registry = ModelRegistry(str(self.model_dir))

        # 缓存已加载的模型
        self._loaded_models = {}

    async def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: Optional[pd.DataFrame] = None,
        y_test: Optional[pd.Series] = None,
        model_type: str = 'LightGBM',
        model_params: Optional[Dict[str, Any]] = None,
        save_model: bool = True,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步训练模型

        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_test: 测试特征
            y_test: 测试标签
            model_type: 模型类型 (LightGBM/Ridge/GRU)
            model_params: 模型参数
            save_model: 是否保存模型
            model_name: 模型名称

        Returns:
            训练结果字典，包含:
                - model: 训练好的模型实例
                - train_metrics: 训练集指标
                - test_metrics: 测试集指标
                - feature_importance: 特征重要性
                - training_time: 训练时间

        Raises:
            ModelTrainingError: 模型训练错误
        """
        def _train():
            trainer = ModelTrainer(
                model_type=model_type,
                model_params=model_params or {}
            )

            # 训练模型
            start_time = datetime.now()
            model = trainer.train(X_train, y_train, X_test, y_test)
            training_time = (datetime.now() - start_time).total_seconds()

            # 评估模型
            train_metrics = trainer.evaluate(model, X_train, y_train)
            test_metrics = None
            if X_test is not None and y_test is not None:
                test_metrics = trainer.evaluate(model, X_test, y_test)

            # 获取特征重要性 (如果支持)
            feature_importance = None
            if hasattr(model, 'feature_importances_'):
                feature_importance = pd.Series(
                    model.feature_importances_,
                    index=X_train.columns
                ).sort_values(ascending=False)

            # 保存模型
            model_path = None
            if save_model:
                if model_name is None:
                    model_name = f"{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                model_path = self.model_dir / f"{model_name}.pkl"
                trainer.save_model(model, str(model_path))

                # 注册模型
                self.registry.register_model(
                    name=model_name,
                    model_type=model_type,
                    model_path=str(model_path),
                    metrics=test_metrics or train_metrics,
                    params=model_params
                )

            return {
                'model': model,
                'model_name': model_name,
                'model_path': str(model_path) if model_path else None,
                'train_metrics': train_metrics,
                'test_metrics': test_metrics,
                'feature_importance': feature_importance,
                'training_time': training_time
            }

        return await asyncio.to_thread(_train)

    async def predict(
        self,
        model: Any,
        X: pd.DataFrame
    ) -> np.ndarray:
        """
        异步模型预测

        Args:
            model: 模型实例
            X: 特征 DataFrame

        Returns:
            预测结果数组

        Raises:
            ModelError: 预测错误
        """
        def _predict():
            if hasattr(model, 'predict'):
                return model.predict(X)
            else:
                raise ModelError(
                    "模型没有 predict 方法",
                    error_code="INVALID_MODEL"
                )

        return await asyncio.to_thread(_predict)

    async def load_model(
        self,
        model_name: str
    ) -> Any:
        """
        异步加载模型

        Args:
            model_name: 模型名称

        Returns:
            模型实例

        Raises:
            ModelError: 模型加载错误
        """
        # 检查缓存
        if model_name in self._loaded_models:
            return self._loaded_models[model_name]

        def _load():
            model_info = self.registry.get_model(model_name)
            if model_info is None:
                raise ModelError(
                    f"模型不存在: {model_name}",
                    error_code="MODEL_NOT_FOUND"
                )

            model_path = model_info['model_path']
            trainer = ModelTrainer(model_type=model_info['model_type'])
            model = trainer.load_model(model_path)

            # 缓存模型
            self._loaded_models[model_name] = model
            return model

        return await asyncio.to_thread(_load)

    async def evaluate_model(
        self,
        model: Any,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Dict[str, float]:
        """
        异步模型评估

        Args:
            model: 模型实例
            X: 特征 DataFrame
            y: 真实标签

        Returns:
            评估指标字典，包含:
                - mse: 均方误差
                - rmse: 均方根误差
                - mae: 平均绝对误差
                - r2: R² 分数
                - ic: IC (信息系数)
                - rank_ic: Rank IC

        Raises:
            ModelError: 评估错误
        """
        def _evaluate():
            evaluator = ModelEvaluator(model)
            return evaluator.evaluate(X, y)

        return await asyncio.to_thread(_evaluate)

    async def tune_hyperparameters(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        model_type: str = 'LightGBM',
        param_space: Optional[Dict[str, Any]] = None,
        n_trials: int = 50,
        metric: str = 'rmse'
    ) -> Dict[str, Any]:
        """
        异步超参数调优

        Args:
            X_train: 训练特征
            y_train: 训练标签
            X_val: 验证特征
            y_val: 验证标签
            model_type: 模型类型
            param_space: 参数空间
            n_trials: 优化次数
            metric: 优化指标

        Returns:
            调优结果字典，包含:
                - best_params: 最优参数
                - best_score: 最优分数
                - best_model: 最优模型
                - optimization_history: 优化历史

        Raises:
            ModelError: 调优错误
        """
        def _tune():
            tuner = HyperparameterTuner(
                model_type=model_type,
                param_space=param_space
            )

            result = tuner.tune(
                X_train=X_train,
                y_train=y_train,
                X_val=X_val,
                y_val=y_val,
                n_trials=n_trials,
                metric=metric
            )

            return result

        return await asyncio.to_thread(_tune)

    async def create_ensemble(
        self,
        models: List[Any],
        method: str = 'voting',
        weights: Optional[List[float]] = None
    ) -> Any:
        """
        异步创建集成模型

        Args:
            models: 模型列表
            method: 集成方法 (voting/stacking/blending)
            weights: 模型权重

        Returns:
            集成模型实例

        Raises:
            ModelError: 集成创建错误
        """
        def _create():
            ensemble = ModelEnsemble(
                models=models,
                method=method,
                weights=weights
            )
            return ensemble

        return await asyncio.to_thread(_create)

    async def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        model_type: str = 'LightGBM',
        model_params: Optional[Dict[str, Any]] = None,
        n_folds: int = 5
    ) -> Dict[str, Any]:
        """
        异步交叉验证

        Args:
            X: 特征 DataFrame
            y: 标签 Series
            model_type: 模型类型
            model_params: 模型参数
            n_folds: 折数

        Returns:
            交叉验证结果字典，包含:
                - mean_score: 平均分数
                - std_score: 分数标准差
                - fold_scores: 各折分数
                - models: 各折模型

        Raises:
            ModelError: 交叉验证错误
        """
        def _cross_validate():
            from sklearn.model_selection import KFold
            kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)

            fold_scores = []
            models = []

            for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X)):
                X_train_fold = X.iloc[train_idx]
                y_train_fold = y.iloc[train_idx]
                X_val_fold = X.iloc[val_idx]
                y_val_fold = y.iloc[val_idx]

                trainer = ModelTrainer(
                    model_type=model_type,
                    model_params=model_params or {}
                )

                model = trainer.train(X_train_fold, y_train_fold)
                metrics = trainer.evaluate(model, X_val_fold, y_val_fold)

                fold_scores.append(metrics.get('rmse', 0.0))
                models.append(model)

            return {
                'mean_score': np.mean(fold_scores),
                'std_score': np.std(fold_scores),
                'fold_scores': fold_scores,
                'models': models
            }

        return await asyncio.to_thread(_cross_validate)

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        异步列出所有已注册的模型

        Returns:
            模型列表
        """
        def _list():
            return self.registry.list_models()

        return await asyncio.to_thread(_list)

    async def delete_model(self, model_name: str) -> bool:
        """
        异步删除模型

        Args:
            model_name: 模型名称

        Returns:
            是否删除成功
        """
        def _delete():
            # 从缓存中移除
            if model_name in self._loaded_models:
                del self._loaded_models[model_name]

            # 从注册表中删除
            return self.registry.delete_model(model_name)

        return await asyncio.to_thread(_delete)

    async def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        异步获取模型信息

        Args:
            model_name: 模型名称

        Returns:
            模型信息字典
        """
        def _get_info():
            return self.registry.get_model(model_name)

        return await asyncio.to_thread(_get_info)
