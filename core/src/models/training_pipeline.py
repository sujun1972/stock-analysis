"""
训练流程管理模块
提供端到端的模型训练管道，简化训练流程

职责:
- 端到端训练流程编排
- 自动化训练-验证-测试流程
- 模型保存和加载管理
- 训练日志记录
"""

import pandas as pd
from typing import Optional, Dict, List, Any
from pathlib import Path
from loguru import logger

from .model_trainer import (
    ModelTrainer, TrainingConfig, DataSplitConfig
)
from src.utils.response import Response


class TrainingPipeline:
    """
    训练流程管理器

    提供便捷的端到端训练接口，自动化数据准备、训练、评估和保存流程

    Examples:
        >>> pipeline = TrainingPipeline(model_type='lightgbm')
        >>> result = pipeline.run(
        ...     df=data,
        ...     feature_cols=features,
        ...     target_col='target_return_5d',
        ...     save_model_name='my_model'
        ... )
        >>> if result.is_success():
        ...     print(f"Test RMSE: {result.data['test_metrics']['rmse']:.4f}")
    """

    def __init__(
        self,
        model_type: str = 'lightgbm',
        model_params: Optional[Dict[str, Any]] = None,
        output_dir: str = 'data/models/saved',
        **training_kwargs
    ):
        """
        初始化训练管道

        Args:
            model_type: 模型类型 ('lightgbm', 'ridge', 'gru')
            model_params: 模型参数字典
            output_dir: 模型保存目录
            **training_kwargs: 其他训练参数（early_stopping_rounds, epochs 等）
        """
        self.model_type = model_type
        self.model_params = model_params or {}
        self.output_dir = Path(output_dir)
        self.training_kwargs = training_kwargs

        # 训练器（延迟初始化）
        self.trainer: Optional[ModelTrainer] = None

        # 训练结果
        self.results: Dict[str, Any] = {}

        logger.debug(f"初始化训练管道: model_type={model_type}")

    def run(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        train_ratio: float = 0.7,
        valid_ratio: float = 0.15,
        save_model_name: Optional[str] = None,
        save_metrics: bool = True,
        verbose: bool = True
    ) -> Response:
        """
        运行完整训练管道

        Args:
            df: 输入数据 DataFrame
            feature_cols: 特征列名列表
            target_col: 目标列名
            train_ratio: 训练集比例
            valid_ratio: 验证集比例
            save_model_name: 模型保存名称（None 则不保存）
            save_metrics: 是否保存评估指标
            verbose: 是否打印详细信息

        Returns:
            Response对象，成功时data包含:
            {
                'trainer': 训练器对象,
                'train_metrics': 训练集评估指标,
                'valid_metrics': 验证集评估指标,
                'test_metrics': 测试集评估指标,
                'model_path': 模型保存路径（如果保存）
            }
        """
        try:
            logger.info("="*60)
            logger.info(f"启动训练管道: {self.model_type.upper()} 模型")
            logger.info("="*60)

            # 1. 创建配置
            training_config = TrainingConfig(
                model_type=self.model_type,
                model_params=self.model_params,
                output_dir=str(self.output_dir),
                **self.training_kwargs
            )

            split_config = DataSplitConfig(
                train_ratio=train_ratio,
                valid_ratio=valid_ratio
            )

            # 2. 创建训练器
            self.trainer = ModelTrainer(config=training_config)

            # 3. 准备数据
            logger.info("\n[1/5] 准备数据...")
            prepare_response = self.trainer.prepare_data(
                df, feature_cols, target_col, split_config
            )

            if not prepare_response.is_success():
                return prepare_response

            data = prepare_response.data
            X_train = data['X_train']
            y_train = data['y_train']
            X_valid = data['X_valid']
            y_valid = data['y_valid']
            X_test = data['X_test']
            y_test = data['y_test']

            # 4. 训练模型
            logger.info("\n[2/5] 训练模型...")
            train_response = self.trainer.train(X_train, y_train, X_valid, y_valid)

            if not train_response.is_success():
                return train_response

            # 5. 评估模型（训练集、验证集、测试集）
            logger.info("\n[3/5] 评估模型...")

            train_eval = self.trainer.evaluate(
                X_train, y_train,
                dataset_name='train',
                verbose=verbose
            )
            if not train_eval.is_success():
                return train_eval

            valid_eval = self.trainer.evaluate(
                X_valid, y_valid,
                dataset_name='valid',
                verbose=verbose
            )
            if not valid_eval.is_success():
                return valid_eval

            test_eval = self.trainer.evaluate(
                X_test, y_test,
                dataset_name='test',
                verbose=verbose
            )
            if not test_eval.is_success():
                return test_eval

            # 6. 保存模型
            model_path = None
            if save_model_name:
                logger.info(f"\n[4/5] 保存模型: {save_model_name}")
                save_response = self.trainer.save_model(
                    save_model_name,
                    save_metrics=save_metrics
                )

                if not save_response.is_success():
                    logger.warning(f"模型保存失败: {save_response.error}")
                else:
                    model_path = save_response.data['model_path']
            else:
                logger.info("\n[4/5] 跳过模型保存")

            # 7. 汇总结果
            logger.info("\n[5/5] 训练管道完成")

            self.results = {
                'trainer': self.trainer,
                'train_metrics': train_eval.data,
                'valid_metrics': valid_eval.data,
                'test_metrics': test_eval.data,
                'model_path': model_path
            }

            # 打印摘要
            if verbose:
                self._print_summary()

            return Response.success(
                data=self.results,
                message="训练管道执行成功",
                model_type=self.model_type,
                model_path=model_path
            )

        except Exception as e:
            logger.exception(f"训练管道执行失败: {e}")
            return Response.error(
                error=f"训练管道失败: {str(e)}",
                error_code="PIPELINE_ERROR",
                model_type=self.model_type
            )

    def _print_summary(self) -> None:
        """打印训练结果摘要"""
        logger.info("\n" + "="*60)
        logger.info("训练结果摘要")
        logger.info("="*60)

        for dataset_name in ['train', 'valid', 'test']:
            metrics = self.results.get(f'{dataset_name}_metrics', {})
            if metrics:
                logger.info(f"\n{dataset_name.upper()} 集:")
                logger.info(f"  RMSE:  {metrics.get('rmse', 0):.6f}")
                logger.info(f"  MAE:   {metrics.get('mae', 0):.6f}")
                logger.info(f"  R²:    {metrics.get('r2', 0):.6f}")
                logger.info(f"  IC:    {metrics.get('ic', 0):.6f}")

        if self.results.get('model_path'):
            logger.info(f"\n模型已保存至: {self.results['model_path']}")

        logger.info("="*60)

    def load_and_evaluate(
        self,
        model_name: str,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str
    ) -> Response:
        """
        加载已保存的模型并评估

        Args:
            model_name: 模型名称
            df: 测试数据
            feature_cols: 特征列
            target_col: 目标列

        Returns:
            Response对象，成功时data包含评估指标
        """
        try:
            # 创建训练器
            training_config = TrainingConfig(
                model_type=self.model_type,
                output_dir=str(self.output_dir)
            )
            self.trainer = ModelTrainer(config=training_config)

            # 加载模型
            logger.info(f"加载模型: {model_name}")
            load_response = self.trainer.load_model(model_name)

            if not load_response.is_success():
                return load_response

            # 准备数据
            X = df[feature_cols]
            y = df[target_col]

            # 评估
            eval_response = self.trainer.evaluate(X, y, dataset_name='test')

            return eval_response

        except Exception as e:
            logger.exception(f"加载和评估失败: {e}")
            return Response.error(
                error=f"加载和评估失败: {str(e)}",
                error_code="LOAD_EVALUATE_ERROR",
                model_name=model_name
            )


# ==================== 便捷函数 ====================

def train_stock_model(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    model_type: str = 'lightgbm',
    model_params: Optional[Dict[str, Any]] = None,
    train_ratio: float = 0.7,
    valid_ratio: float = 0.15,
    save_path: Optional[str] = None,
    **training_kwargs
) -> Response:
    """
    便捷函数：一行代码训练股票预测模型

    Args:
        df: 数据 DataFrame
        feature_cols: 特征列名列表
        target_col: 目标列名
        model_type: 模型类型 ('lightgbm', 'ridge', 'gru')
        model_params: 模型参数字典
        train_ratio: 训练集比例
        valid_ratio: 验证集比例
        save_path: 模型保存名称（None 则不保存）
        **training_kwargs: 其他训练参数

    Returns:
        Response对象，成功时data包含训练结果

    Examples:
        >>> result = train_stock_model(
        ...     df=data,
        ...     feature_cols=features,
        ...     target_col='target_return_5d',
        ...     model_type='lightgbm',
        ...     save_path='my_lgb_model'
        ... )
        >>> if result.is_success():
        ...     print(f"Test RMSE: {result.data['test_metrics']['rmse']:.4f}")
    """
    pipeline = TrainingPipeline(
        model_type=model_type,
        model_params=model_params,
        **training_kwargs
    )

    return pipeline.run(
        df=df,
        feature_cols=feature_cols,
        target_col=target_col,
        train_ratio=train_ratio,
        valid_ratio=valid_ratio,
        save_model_name=save_path,
        save_metrics=True,
        verbose=True
    )
