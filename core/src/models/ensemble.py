"""
模型集成框架 (Model Ensemble Framework)

支持三种主流集成策略：
1. 加权平均集成 (Weighted Average) - 简单有效，支持权重优化
2. 投票法集成 (Voting) - 适合选股策略，降低极端预测
3. Stacking集成 (Stacking) - 使用元学习器，性能最优

设计特点:
- 统一接口：所有集成方法继承自 BaseEnsemble，实现 predict() 接口
- 灵活配置：支持自定义权重、元学习器、投票权重
- 自动优化：基于验证集自动优化权重（scipy.optimize）
- 错误处理：自定义异常类，完整的输入验证
- 日志记录：使用 loguru 记录关键操作

使用示例：
    from models import create_ensemble, WeightedAverageEnsemble

    # 快速创建
    ensemble = create_ensemble([model1, model2], method='weighted_average')

    # 优化权重
    ensemble.optimize_weights(X_valid, y_valid, metric='ic')

    # 预测
    predictions = ensemble.predict(X_test)
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any, Union, Tuple
from abc import ABC, abstractmethod
from pathlib import Path
import pickle
from loguru import logger
from scipy.optimize import minimize

try:
    from .lightgbm_model import LightGBMStockModel
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    LightGBMStockModel = None

from .ridge_model import RidgeStockModel

try:
    from .gru_model import GRUStockTrainer
    GRU_AVAILABLE = True
except ImportError:
    GRU_AVAILABLE = False


# ==================== 异常类 ====================

# 导入统一异常系统
from src.exceptions import ModelError

class EnsembleError(ModelError):
    """集成错误基类（迁移到统一异常系统）

    该异常类现在继承自统一异常系统的ModelError。
    支持错误代码和上下文信息。

    Examples:
        >>> raise EnsembleError(
        ...     "集成模型创建失败",
        ...     error_code="ENSEMBLE_CREATION_ERROR",
        ...     n_models=3,
        ...     ensemble_method="weighted_average"
        ... )
    """
    pass


class IncompatibleModelsError(EnsembleError):
    """模型不兼容错误（迁移到统一异常系统）

    当尝试集成不兼容的模型时抛出。

    Examples:
        >>> raise IncompatibleModelsError(
        ...     "模型输出维度不一致",
        ...     error_code="INCOMPATIBLE_MODELS",
        ...     model_1_output_shape=(100, 1),
        ...     model_2_output_shape=(100, 5),
        ...     reason="输出维度必须相同"
        ... )
    """
    pass


# ==================== 基础类 ====================

class BaseEnsemble(ABC):
    """集成模型抽象基类"""

    def __init__(
        self,
        models: List[Any],
        model_names: Optional[List[str]] = None
    ):
        """
        初始化集成模型

        Args:
            models: 模型列表（已训练）
            model_names: 模型名称列表
        """
        if not models:
            raise EnsembleError("模型列表不能为空")

        self.models = models
        self.n_models = len(models)

        # 自动生成模型名称
        if model_names is None:
            model_names = [f"model_{i}" for i in range(self.n_models)]

        if len(model_names) != self.n_models:
            raise EnsembleError(
                f"模型名称数量({len(model_names)})与模型数量({self.n_models})不匹配"
            )

        self.model_names = model_names
        logger.info(f"初始化集成模型: {self.n_models} 个子模型")

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        预测接口

        Args:
            X: 特征DataFrame

        Returns:
            预测值数组
        """
        pass

    def _validate_predictions(
        self,
        predictions_list: List[np.ndarray]
    ) -> None:
        """验证所有模型的预测形状一致"""
        if not predictions_list:
            raise EnsembleError("预测结果列表为空")

        first_shape = predictions_list[0].shape
        for i, pred in enumerate(predictions_list[1:], 1):
            if pred.shape != first_shape:
                raise IncompatibleModelsError(
                    f"模型 {i} 的预测形状 {pred.shape} 与第一个模型 {first_shape} 不一致"
                )

    def get_individual_predictions(
        self,
        X: pd.DataFrame
    ) -> Dict[str, np.ndarray]:
        """
        获取所有子模型的预测

        Args:
            X: 特征DataFrame

        Returns:
            {模型名称: 预测数组} 字典
        """
        predictions = {}
        for name, model in zip(self.model_names, self.models):
            pred = model.predict(X)
            predictions[name] = pred

        return predictions

    def save(self, filepath: str):
        """保存集成模型"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # 保存集成配置（不保存模型本身，只保存引用）
        config = {
            'ensemble_type': self.__class__.__name__,
            'model_names': self.model_names,
            'n_models': self.n_models,
        }

        # 子类可以添加额外配置
        config.update(self._get_save_config())

        with open(filepath, 'wb') as f:
            pickle.dump(config, f)

        logger.success(f"✓ 集成模型配置已保存至: {filepath}")

    @abstractmethod
    def _get_save_config(self) -> Dict:
        """获取子类特定的保存配置"""
        pass


# ==================== 加权平均集成 ====================

class WeightedAverageEnsemble(BaseEnsemble):
    """
    加权平均集成

    对所有模型的预测进行加权平均
    """

    def __init__(
        self,
        models: List[Any],
        weights: Optional[List[float]] = None,
        model_names: Optional[List[str]] = None
    ):
        """
        初始化加权平均集成

        Args:
            models: 模型列表
            weights: 权重列表（自动归一化）。None=等权重
            model_names: 模型名称列表
        """
        super().__init__(models, model_names)

        # 处理权重
        if weights is None:
            weights = [1.0 / self.n_models] * self.n_models
        else:
            if len(weights) != self.n_models:
                raise EnsembleError(
                    f"权重数量({len(weights)})与模型数量({self.n_models})不匹配"
                )
            # 归一化权重
            weights = np.array(weights)
            weights = weights / weights.sum()

        self.weights = weights

        logger.info("加权平均集成配置:")
        for name, w in zip(self.model_names, self.weights):
            logger.info(f"  {name}: {w:.4f}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        加权平均预测

        Args:
            X: 特征DataFrame

        Returns:
            预测值数组
        """
        predictions_list = []

        for model in self.models:
            pred = model.predict(X)
            predictions_list.append(pred)

        # 验证形状
        self._validate_predictions(predictions_list)

        # 加权平均
        predictions_array = np.array(predictions_list)  # (n_models, n_samples)
        weighted_pred = np.average(predictions_array, axis=0, weights=self.weights)

        return weighted_pred

    def optimize_weights(
        self,
        X_valid: pd.DataFrame,
        y_valid: pd.Series,
        metric: str = 'ic'
    ) -> np.ndarray:
        """
        优化权重以最大化验证集指标

        Args:
            X_valid: 验证特征
            y_valid: 验证标签
            metric: 优化指标 ('ic', 'rank_ic', 'mse')

        Returns:
            优化后的权重数组
        """
        logger.info(f"开始优化权重，目标指标: {metric}")

        # 获取所有模型的预测
        predictions_list = []
        for model in self.models:
            pred = model.predict(X_valid)
            predictions_list.append(pred)

        predictions_array = np.array(predictions_list)  # (n_models, n_samples)
        y_valid_array = y_valid.values

        # 定义目标函数
        def objective(weights):
            """目标函数：负的评估指标（因为要最小化）"""
            weighted_pred = np.average(predictions_array, axis=0, weights=weights)

            if metric == 'ic':
                # IC = Pearson相关系数
                score = np.corrcoef(weighted_pred, y_valid_array)[0, 1]
            elif metric == 'rank_ic':
                # Rank IC = Spearman相关系数
                from scipy.stats import spearmanr
                score, _ = spearmanr(weighted_pred, y_valid_array)
            elif metric == 'mse':
                # MSE（需要最小化，所以不取负）
                score = -np.mean((weighted_pred - y_valid_array) ** 2)
            else:
                raise ValueError(f"不支持的指标: {metric}")

            return -score  # 返回负值，因为 minimize 是最小化

        # 约束条件：权重和为1，每个权重>=0
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0, 1) for _ in range(self.n_models)]

        # 初始权重
        x0 = np.array([1.0 / self.n_models] * self.n_models)

        # 优化
        result = minimize(
            objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )

        if not result.success:
            logger.warning(f"权重优化未完全收敛: {result.message}")
        else:
            logger.success("✓ 权重优化成功")

        # 更新权重
        self.weights = result.x

        logger.info("优化后权重:")
        for name, w in zip(self.model_names, self.weights):
            logger.info(f"  {name}: {w:.4f}")

        # 计算优化后的指标
        optimal_score = -result.fun
        logger.info(f"优化后 {metric}: {optimal_score:.6f}")

        return self.weights

    def _get_save_config(self) -> Dict:
        return {'weights': self.weights.tolist()}


# ==================== 投票法集成 ====================

class VotingEnsemble(BaseEnsemble):
    """
    投票法集成（用于分类/选股）

    每个模型对股票进行排序，选择Top N，最终统计"票数"
    """

    def __init__(
        self,
        models: List[Any],
        model_names: Optional[List[str]] = None,
        voting_weights: Optional[List[float]] = None
    ):
        """
        初始化投票法集成

        Args:
            models: 模型列表
            model_names: 模型名称列表
            voting_weights: 投票权重（None=等权重）
        """
        super().__init__(models, model_names)

        if voting_weights is None:
            voting_weights = [1.0] * self.n_models
        else:
            if len(voting_weights) != self.n_models:
                raise EnsembleError(
                    f"投票权重数量({len(voting_weights)})与模型数量({self.n_models})不匹配"
                )

        self.voting_weights = voting_weights

        logger.info("投票法集成配置:")
        for name, w in zip(self.model_names, self.voting_weights):
            logger.info(f"  {name}: 权重={w:.2f}")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        投票法预测（返回加权投票分数）

        Args:
            X: 特征DataFrame

        Returns:
            投票分数数组（分数越高越好）
        """
        n_samples = len(X)
        voting_scores = np.zeros(n_samples)

        for model, weight in zip(self.models, self.voting_weights):
            # 获取预测并排序
            pred = model.predict(X)

            # 确保预测长度与样本数一致
            if len(pred) != n_samples:
                raise IncompatibleModelsError(
                    f"模型预测长度 {len(pred)} 与样本数 {n_samples} 不一致"
                )

            # 将预测值转换为排名分数（排名越高分数越高）
            # 使用 rank 方法：值越大排名越高
            ranks = pd.Series(pred).rank(ascending=False, method='average').values

            # 归一化到 [0, 1]
            if n_samples > 1:
                rank_scores = 1 - (ranks - 1) / (n_samples - 1)
            else:
                rank_scores = np.ones(n_samples)

            # 加权累加
            voting_scores += weight * rank_scores

        return voting_scores

    def select_top_n(
        self,
        X: pd.DataFrame,
        top_n: int,
        return_scores: bool = False
    ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
        """
        选择得票最高的 Top N 个样本

        Args:
            X: 特征DataFrame
            top_n: 选择数量
            return_scores: 是否返回分数

        Returns:
            如果 return_scores=False: Top N 的索引数组
            如果 return_scores=True: (索引数组, 分数数组)
        """
        scores = self.predict(X)
        top_indices = np.argsort(scores)[-top_n:][::-1]

        if return_scores:
            return top_indices, scores[top_indices]
        else:
            return top_indices

    def _get_save_config(self) -> Dict:
        return {'voting_weights': self.voting_weights}


# ==================== Stacking 集成 ====================

class StackingEnsemble(BaseEnsemble):
    """
    Stacking 集成

    第一层：多个基础模型
    第二层：元学习器（使用基础模型的预测作为特征）
    """

    def __init__(
        self,
        base_models: List[Any],
        meta_learner: Optional[Any] = None,
        model_names: Optional[List[str]] = None,
        use_original_features: bool = False
    ):
        """
        初始化 Stacking 集成

        Args:
            base_models: 基础模型列表（第一层）
            meta_learner: 元学习器（第二层）。None=使用Ridge
            model_names: 模型名称列表
            use_original_features: 是否将原始特征也传给元学习器
        """
        super().__init__(base_models, model_names)

        self.base_models = base_models
        self.use_original_features = use_original_features

        # 默认使用 Ridge 作为元学习器
        if meta_learner is None:
            meta_learner = RidgeStockModel(alpha=1.0)

        self.meta_learner = meta_learner
        self.is_meta_trained = False

        logger.info(f"Stacking集成配置:")
        logger.info(f"  基础模型: {self.n_models} 个")
        logger.info(f"  元学习器: {type(meta_learner).__name__}")
        logger.info(f"  使用原始特征: {use_original_features}")

    def train_meta_learner(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None
    ):
        """
        训练元学习器

        Args:
            X_train: 训练特征（用于生成基础模型预测）
            y_train: 训练标签
            X_valid: 验证特征（可选）
            y_valid: 验证标签（可选）
        """
        logger.info("\n训练 Stacking 元学习器...")

        # 第一层：获取所有基础模型的预测
        logger.info("生成基础模型预测...")
        base_predictions = []
        for name, model in zip(self.model_names, self.base_models):
            pred = model.predict(X_train)
            base_predictions.append(pred)
            logger.debug(f"  {name}: {pred.shape}")

        # 构建元特征
        meta_features = np.column_stack(base_predictions)

        # 如果使用原始特征，拼接
        if self.use_original_features:
            meta_features = np.hstack([meta_features, X_train.values])
            logger.debug(f"拼接原始特征后: {meta_features.shape}")

        meta_features_df = pd.DataFrame(meta_features)

        # 处理验证集
        meta_valid_df = None
        if X_valid is not None:
            base_valid_predictions = []
            for model in self.base_models:
                pred = model.predict(X_valid)
                base_valid_predictions.append(pred)

            meta_valid_features = np.column_stack(base_valid_predictions)

            if self.use_original_features:
                meta_valid_features = np.hstack([meta_valid_features, X_valid.values])

            meta_valid_df = pd.DataFrame(meta_valid_features)

        # 训练元学习器
        logger.info("训练元学习器...")
        self.meta_learner.train(
            meta_features_df, y_train,
            meta_valid_df, y_valid
        )

        self.is_meta_trained = True
        logger.success("✓ Stacking 元学习器训练完成")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Stacking 预测

        Args:
            X: 特征DataFrame

        Returns:
            预测值数组
        """
        if not self.is_meta_trained:
            raise EnsembleError("元学习器未训练，请先调用 train_meta_learner()")

        # 第一层：基础模型预测
        base_predictions = []
        for model in self.base_models:
            pred = model.predict(X)
            base_predictions.append(pred)

        # 构建元特征
        meta_features = np.column_stack(base_predictions)

        if self.use_original_features:
            meta_features = np.hstack([meta_features, X.values])

        meta_features_df = pd.DataFrame(meta_features)

        # 第二层：元学习器预测
        predictions = self.meta_learner.predict(meta_features_df)

        return predictions

    def _get_save_config(self) -> Dict:
        return {
            'use_original_features': self.use_original_features,
            'is_meta_trained': self.is_meta_trained
        }


# ==================== 便捷函数 ====================

def create_ensemble(
    models: List[Any],
    method: str = 'weighted_average',
    model_names: Optional[List[str]] = None,
    **kwargs
) -> BaseEnsemble:
    """
    便捷函数：创建集成模型

    Args:
        models: 模型列表
        method: 集成方法 ('weighted_average', 'voting', 'stacking')
        model_names: 模型名称列表
        **kwargs: 传递给具体集成类的参数

    Returns:
        集成模型实例

    示例:
        # 加权平均
        ensemble = create_ensemble(
            [model1, model2, model3],
            method='weighted_average',
            weights=[0.5, 0.3, 0.2]
        )

        # 投票法
        ensemble = create_ensemble(
            [model1, model2, model3],
            method='voting'
        )

        # Stacking
        ensemble = create_ensemble(
            [model1, model2, model3],
            method='stacking',
            meta_learner=ridge_model
        )
    """
    if method == 'weighted_average':
        return WeightedAverageEnsemble(models, model_names=model_names, **kwargs)
    elif method == 'voting':
        return VotingEnsemble(models, model_names=model_names, **kwargs)
    elif method == 'stacking':
        return StackingEnsemble(models, model_names=model_names, **kwargs)
    else:
        raise ValueError(
            f"不支持的集成方法: {method}。"
            f"支持的方法: 'weighted_average', 'voting', 'stacking'"
        )


# ==================== 使用示例 ====================

# ==================== 使用示例 ====================
# 完整示例请参考: examples/ensemble_example.py
# 单元测试请参考: tests/unit/test_ensemble.py
