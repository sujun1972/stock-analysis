"""
模型验证模块
提供交叉验证、稳定性测试、持久性测试等模型验证工具

职责:
- 时间序列交叉验证
- 模型稳定性测试
- 预测持久性验证
- 过拟合检测
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any
from loguru import logger
from dataclasses import dataclass

from .model_trainer import ModelTrainer, TrainingConfig, DataSplitConfig
from .model_evaluator import ModelEvaluator
from src.utils.response import Response


@dataclass
class CrossValidationConfig:
    """交叉验证配置"""
    n_splits: int = 5
    test_size: float = 0.15
    gap: int = 0  # 训练集和测试集之间的间隔（避免数据泄漏）
    verbose: bool = True


class TimeSeriesCrossValidator:
    """
    时间序列交叉验证器

    使用滑动窗口或扩展窗口进行时间序列交叉验证，避免未来数据泄漏

    Examples:
        >>> validator = TimeSeriesCrossValidator(n_splits=5)
        >>> result = validator.cross_validate(
        ...     df=data,
        ...     feature_cols=features,
        ...     target_col='target_return_5d',
        ...     model_type='lightgbm'
        ... )
        >>> print(f"平均 RMSE: {result.data['mean_rmse']:.4f}")
    """

    def __init__(self, config: Optional[CrossValidationConfig] = None):
        """
        初始化交叉验证器

        Args:
            config: 交叉验证配置
        """
        self.config = config or CrossValidationConfig()
        self.evaluator = ModelEvaluator()

    def cross_validate(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        model_type: str = 'lightgbm',
        model_params: Optional[Dict[str, Any]] = None,
        expanding_window: bool = True
    ) -> Response:
        """
        执行时间序列交叉验证

        Args:
            df: 输入数据 DataFrame
            feature_cols: 特征列名列表
            target_col: 目标列名
            model_type: 模型类型
            model_params: 模型参数
            expanding_window: True=扩展窗口，False=滑动窗口

        Returns:
            Response对象，成功时data包含:
            {
                'fold_results': 每折结果列表,
                'mean_rmse': 平均 RMSE,
                'std_rmse': RMSE 标准差,
                'mean_r2': 平均 R²,
                'std_r2': R² 标准差
            }
        """
        try:
            logger.info("="*60)
            logger.info(f"时间序列交叉验证 ({self.config.n_splits} 折)")
            logger.info("="*60)

            n_samples = len(df)
            test_size = int(n_samples * self.config.test_size)

            fold_results = []

            for fold in range(self.config.n_splits):
                logger.info(f"\n--- Fold {fold + 1}/{self.config.n_splits} ---")

                # 计算分割点
                if expanding_window:
                    # 扩展窗口：训练集逐渐增大
                    train_end = int(n_samples * (fold + 1) / (self.config.n_splits + 1))
                else:
                    # 滑动窗口：训练集大小固定
                    train_start = int(n_samples * fold / (self.config.n_splits + 1))
                    train_end = int(n_samples * (fold + 1) / (self.config.n_splits + 1))

                test_start = train_end + self.config.gap
                test_end = min(test_start + test_size, n_samples)

                # 检查数据量
                if expanding_window:
                    train_df = df.iloc[:train_end]
                else:
                    train_df = df.iloc[train_start:train_end]

                test_df = df.iloc[test_start:test_end]

                if len(train_df) < 100:
                    logger.warning(f"Fold {fold + 1}: 训练集样本不足 ({len(train_df)}), 跳过")
                    continue

                if len(test_df) < 10:
                    logger.warning(f"Fold {fold + 1}: 测试集样本不足 ({len(test_df)}), 跳过")
                    continue

                logger.info(f"训练集: {len(train_df)} 样本, 测试集: {len(test_df)} 样本")

                # 训练模型
                training_config = TrainingConfig(
                    model_type=model_type,
                    model_params=model_params or {}
                )

                trainer = ModelTrainer(config=training_config)

                # 准备数据（只在训练集上做分割）
                split_config = DataSplitConfig(train_ratio=0.85, valid_ratio=0.15)
                prepare_response = trainer.prepare_data(
                    train_df, feature_cols, target_col, split_config
                )

                if not prepare_response.is_success():
                    logger.error(f"Fold {fold + 1}: 数据准备失败")
                    continue

                data = prepare_response.data
                X_train = data['X_train']
                y_train = data['y_train']
                X_valid = data['X_valid']
                y_valid = data['y_valid']

                # 训练
                train_response = trainer.train(X_train, y_train, X_valid, y_valid)

                if not train_response.is_success():
                    logger.error(f"Fold {fold + 1}: 训练失败")
                    continue

                # 评估
                X_test = test_df[feature_cols]
                y_test = test_df[target_col]

                eval_response = trainer.evaluate(
                    X_test, y_test,
                    dataset_name=f'fold_{fold+1}',
                    verbose=self.config.verbose
                )

                if not eval_response.is_success():
                    logger.error(f"Fold {fold + 1}: 评估失败")
                    continue

                metrics = eval_response.data
                fold_results.append({
                    'fold': fold + 1,
                    'train_size': len(train_df),
                    'test_size': len(test_df),
                    'metrics': metrics
                })

            # 汇总结果
            if not fold_results:
                return Response.error(
                    error="所有折都失败",
                    error_code="CV_ALL_FOLDS_FAILED"
                )

            rmse_scores = [r['metrics']['rmse'] for r in fold_results]
            r2_scores = [r['metrics']['r2'] for r in fold_results]
            ic_scores = [r['metrics'].get('ic', 0) for r in fold_results]

            logger.info("\n" + "="*60)
            logger.info("交叉验证汇总")
            logger.info("="*60)
            logger.info(f"RMSE: {np.mean(rmse_scores):.6f} ± {np.std(rmse_scores):.6f}")
            logger.info(f"R²:   {np.mean(r2_scores):.6f} ± {np.std(r2_scores):.6f}")
            logger.info(f"IC:   {np.mean(ic_scores):.6f} ± {np.std(ic_scores):.6f}")
            logger.info("="*60)

            return Response.success(
                data={
                    'fold_results': fold_results,
                    'mean_rmse': float(np.mean(rmse_scores)),
                    'std_rmse': float(np.std(rmse_scores)),
                    'mean_r2': float(np.mean(r2_scores)),
                    'std_r2': float(np.std(r2_scores)),
                    'mean_ic': float(np.mean(ic_scores)),
                    'std_ic': float(np.std(ic_scores))
                },
                message="交叉验证完成",
                n_folds=len(fold_results),
                n_splits=self.config.n_splits
            )

        except Exception as e:
            logger.exception(f"交叉验证失败: {e}")
            return Response.error(
                error=f"交叉验证失败: {str(e)}",
                error_code="CV_ERROR"
            )


class ModelStabilityTester:
    """
    模型稳定性测试器

    测试模型在不同数据扰动下的稳定性
    """

    @staticmethod
    def test_prediction_stability(
        trainer: ModelTrainer,
        X: pd.DataFrame,
        n_perturbations: int = 10,
        noise_level: float = 0.01
    ) -> Response:
        """
        测试预测稳定性

        在特征上添加小扰动，观察预测结果的变化

        Args:
            trainer: 已训练的模型训练器
            X: 测试特征
            n_perturbations: 扰动次数
            noise_level: 噪声水平（相对于标准差）

        Returns:
            Response对象，成功时data包含稳定性指标
        """
        try:
            logger.info(f"测试预测稳定性 (扰动次数: {n_perturbations})")

            if trainer.model is None:
                return Response.error(
                    error="模型未训练",
                    error_code="MODEL_NOT_TRAINED"
                )

            # 原始预测
            original_pred = trainer.model.predict(X)

            # 添加扰动
            perturbations = []
            for i in range(n_perturbations):
                # 添加高斯噪声
                noise = np.random.randn(*X.shape) * X.std().values * noise_level
                X_perturbed = X + noise

                pred_perturbed = trainer.model.predict(X_perturbed)
                perturbations.append(pred_perturbed)

            perturbations = np.array(perturbations)

            # 计算稳定性指标
            pred_std = perturbations.std(axis=0).mean()
            pred_range = (perturbations.max(axis=0) - perturbations.min(axis=0)).mean()
            correlation = np.corrcoef(original_pred, perturbations.mean(axis=0))[0, 1]

            logger.info(f"预测标准差: {pred_std:.6f}")
            logger.info(f"预测范围: {pred_range:.6f}")
            logger.info(f"相关系数: {correlation:.6f}")

            return Response.success(
                data={
                    'pred_std': float(pred_std),
                    'pred_range': float(pred_range),
                    'correlation': float(correlation),
                    'is_stable': correlation > 0.95 and pred_std < 0.1
                },
                message="稳定性测试完成"
            )

        except Exception as e:
            logger.exception(f"稳定性测试失败: {e}")
            return Response.error(
                error=f"稳定性测试失败: {str(e)}",
                error_code="STABILITY_TEST_ERROR"
            )


class OverfittingDetector:
    """
    过拟合检测器

    通过比较训练集和测试集性能来检测过拟合
    """

    @staticmethod
    def detect_overfitting(
        train_metrics: Dict[str, float],
        test_metrics: Dict[str, float],
        rmse_threshold: float = 0.3,
        r2_threshold: float = 0.2
    ) -> Response:
        """
        检测过拟合

        Args:
            train_metrics: 训练集指标
            test_metrics: 测试集指标
            rmse_threshold: RMSE 差异阈值（相对）
            r2_threshold: R² 差异阈值（绝对）

        Returns:
            Response对象，成功时data包含过拟合检测结果
        """
        try:
            train_rmse = train_metrics.get('rmse', 0)
            test_rmse = test_metrics.get('rmse', 0)
            train_r2 = train_metrics.get('r2', 0)
            test_r2 = test_metrics.get('r2', 0)

            # 计算差异
            rmse_ratio = (test_rmse - train_rmse) / train_rmse if train_rmse > 0 else 0
            r2_diff = train_r2 - test_r2

            # 判断过拟合
            is_overfitting = (
                rmse_ratio > rmse_threshold or r2_diff > r2_threshold
            )

            severity = 'none'
            if is_overfitting:
                if rmse_ratio > rmse_threshold * 2 or r2_diff > r2_threshold * 2:
                    severity = 'severe'
                else:
                    severity = 'moderate'

            logger.info("过拟合检测:")
            logger.info(f"  RMSE 比率: {rmse_ratio:.2%}")
            logger.info(f"  R² 差异: {r2_diff:.4f}")
            logger.info(f"  过拟合: {severity}")

            return Response.success(
                data={
                    'is_overfitting': is_overfitting,
                    'severity': severity,
                    'rmse_ratio': float(rmse_ratio),
                    'r2_diff': float(r2_diff),
                    'train_rmse': train_rmse,
                    'test_rmse': test_rmse,
                    'train_r2': train_r2,
                    'test_r2': test_r2
                },
                message=f"过拟合检测完成: {severity}"
            )

        except Exception as e:
            logger.exception(f"过拟合检测失败: {e}")
            return Response.error(
                error=f"过拟合检测失败: {str(e)}",
                error_code="OVERFITTING_DETECT_ERROR"
            )


class PersistenceValidator:
    """
    预测持久性验证器

    测试模型预测是否仅仅是简单的持久性预测（即预测值 = 当前值）
    """

    @staticmethod
    def validate_persistence(
        predictions: np.ndarray,
        current_values: np.ndarray,
        correlation_threshold: float = 0.95
    ) -> Response:
        """
        验证预测是否过度依赖持久性

        Args:
            predictions: 模型预测值
            current_values: 当前值（基准）
            correlation_threshold: 相关系数阈值

        Returns:
            Response对象，成功时data包含持久性验证结果
        """
        try:
            correlation = np.corrcoef(predictions, current_values)[0, 1]

            is_persistence = correlation > correlation_threshold

            logger.info(f"持久性验证: 相关系数 = {correlation:.4f}")

            if is_persistence:
                logger.warning("⚠️  模型可能过度依赖持久性预测")

            return Response.success(
                data={
                    'is_persistence': is_persistence,
                    'correlation': float(correlation),
                    'threshold': correlation_threshold
                },
                message="持久性验证完成"
            )

        except Exception as e:
            logger.exception(f"持久性验证失败: {e}")
            return Response.error(
                error=f"持久性验证失败: {str(e)}",
                error_code="PERSISTENCE_VALIDATION_ERROR"
            )


# ==================== 便捷函数 ====================

def cross_validate_model(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    model_type: str = 'lightgbm',
    n_splits: int = 5,
    **model_params
) -> Response:
    """
    便捷函数：时间序列交叉验证

    Args:
        df: 数据 DataFrame
        feature_cols: 特征列
        target_col: 目标列
        model_type: 模型类型
        n_splits: 交叉验证折数
        **model_params: 模型参数

    Returns:
        Response对象

    Examples:
        >>> result = cross_validate_model(
        ...     df=data,
        ...     feature_cols=features,
        ...     target_col='target_return_5d',
        ...     n_splits=5
        ... )
        >>> print(f"平均 RMSE: {result.data['mean_rmse']:.4f}")
    """
    config = CrossValidationConfig(n_splits=n_splits)
    validator = TimeSeriesCrossValidator(config=config)

    return validator.cross_validate(
        df=df,
        feature_cols=feature_cols,
        target_col=target_col,
        model_type=model_type,
        model_params=model_params
    )
