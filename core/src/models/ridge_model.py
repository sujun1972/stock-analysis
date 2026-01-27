"""
Ridge线性回归模型
用于股票收益率预测的基准模型
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from typing import Optional, Dict, Tuple
import pickle
from pathlib import Path
from loguru import logger


class RidgeStockModel:
    """Ridge回归股票预测模型（基准模型）"""

    def __init__(
        self,
        alpha: float = 1.0,
        fit_intercept: bool = True,
        random_state: int = 42
    ):
        """
        初始化Ridge模型

        参数:
            alpha: 正则化强度
            fit_intercept: 是否拟合截距
            random_state: 随机种子
        """
        self.params = {
            'alpha': alpha,
            'fit_intercept': fit_intercept,
            'random_state': random_state
        }

        self.model = None
        self.feature_names = None
        self.feature_importance = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_valid: Optional[pd.DataFrame] = None,
        y_valid: Optional[pd.Series] = None
    ) -> Dict:
        """
        训练模型

        参数:
            X_train: 训练特征
            y_train: 训练标签
            X_valid: 验证特征（Ridge不需要，为了接口一致）
            y_valid: 验证标签（Ridge不需要，为了接口一致）

        返回:
            训练历史字典
        """
        logger.info(f"\n开始训练Ridge模型...")
        logger.info(f"训练集: {len(X_train)} 样本 × {len(X_train.columns)} 特征")

        # 保存特征名
        self.feature_names = X_train.columns.tolist()

        # 创建并训练模型
        self.model = Ridge(**self.params)
        self.model.fit(X_train, y_train)

        # 计算特征重要性（使用系数的绝对值）
        self.feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': np.abs(self.model.coef_)
        }).sort_values('importance', ascending=False)

        # 计算训练集指标
        y_train_pred = self.model.predict(X_train)
        train_ic = np.corrcoef(y_train, y_train_pred)[0, 1]
        train_mae = mean_absolute_error(y_train, y_train_pred)
        train_r2 = r2_score(y_train, y_train_pred)

        logger.success(f"✓ 训练完成")
        logger.info(f"  Train IC: {train_ic:.6f}")
        logger.info(f"  Train MAE: {train_mae:.6f}")
        logger.info(f"  Train R²: {train_r2:.6f}")

        history = {
            'train_ic': train_ic,
            'train_mae': train_mae,
            'train_r2': train_r2
        }

        # 如果提供验证集，计算验证集指标
        if X_valid is not None and y_valid is not None:
            y_valid_pred = self.model.predict(X_valid)
            valid_ic = np.corrcoef(y_valid, y_valid_pred)[0, 1]
            valid_mae = mean_absolute_error(y_valid, y_valid_pred)
            valid_r2 = r2_score(y_valid, y_valid_pred)

            logger.info(f"  Valid IC: {valid_ic:.6f}")
            logger.info(f"  Valid MAE: {valid_mae:.6f}")
            logger.info(f"  Valid R²: {valid_r2:.6f}")

            history.update({
                'valid_ic': valid_ic,
                'valid_mae': valid_mae,
                'valid_r2': valid_r2
            })

        return history

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        预测

        参数:
            X: 特征数据

        返回:
            预测值数组
        """
        if self.model is None:
            raise ValueError("模型未训练，请先调用train方法")

        return self.model.predict(X)

    def evaluate(
        self,
        X: pd.DataFrame,
        y: pd.Series
    ) -> Dict[str, float]:
        """
        评估模型

        参数:
            X: 特征数据
            y: 真实标签

        返回:
            评估指标字典
        """
        if self.model is None:
            raise ValueError("模型未训练，请先调用train方法")

        y_pred = self.predict(X)

        # 计算IC (Information Coefficient)
        ic = np.corrcoef(y, y_pred)[0, 1]

        # 计算Rank IC
        rank_ic = pd.Series(y).corr(pd.Series(y_pred), method='spearman')

        # 计算MAE
        mae = mean_absolute_error(y, y_pred)

        # 计算R²
        r2 = r2_score(y, y_pred)

        metrics = {
            'ic': ic,
            'rank_ic': rank_ic,
            'mae': mae,
            'r2': r2
        }

        return metrics

    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """
        获取特征重要性

        参数:
            top_n: 返回前N个重要特征

        返回:
            特征重要性DataFrame
        """
        if self.feature_importance is None:
            raise ValueError("模型未训练或特征重要性未计算")

        return self.feature_importance.head(top_n)

    def save(self, filepath: str):
        """
        保存模型

        参数:
            filepath: 保存路径
        """
        if self.model is None:
            raise ValueError("模型未训练，无法保存")

        # 确保目录存在
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        # 保存模型和元数据
        model_data = {
            'model': self.model,
            'params': self.params,
            'feature_names': self.feature_names,
            'feature_importance': self.feature_importance
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        logger.success(f"✓ Ridge模型已保存到: {filepath}")

    def load(self, filepath: str):
        """
        加载模型

        参数:
            filepath: 模型路径
        """
        if not Path(filepath).exists():
            raise FileNotFoundError(f"模型文件不存在: {filepath}")

        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.params = model_data['params']
        self.feature_names = model_data['feature_names']
        self.feature_importance = model_data['feature_importance']

        logger.success(f"✓ Ridge模型已加载: {filepath}")
