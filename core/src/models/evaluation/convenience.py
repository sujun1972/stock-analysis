"""
便捷函数
提供快速评估的便捷接口
"""
import numpy as np
from typing import Optional, Dict
from loguru import logger

from .config import EvaluationConfig
from .evaluator import ModelEvaluator
from .exceptions import InvalidInputError


def evaluate_model(
    predictions: np.ndarray,
    actual_returns: np.ndarray,
    evaluation_type: str = 'regression',
    config: Optional[EvaluationConfig] = None,
    verbose: bool = True
) -> Dict[str, float]:
    """
    便捷函数：评估模型

    Args:
        predictions: 预测值
        actual_returns: 实际收益率
        evaluation_type: 评估类型 ('regression', 'ranking')
        config: 评估配置
        verbose: 是否打印结果

    Returns:
        评估指标字典

    Raises:
        ValueError: 不支持的评估类型
        InvalidInputError: 输入数据无效
    """
    evaluator = ModelEvaluator(config=config)

    if evaluation_type == 'regression':
        return evaluator.evaluate_regression(predictions, actual_returns, verbose=verbose)
    elif evaluation_type == 'ranking':
        # 仅计算排名相关指标
        logger.info("开始排名评估...")
        metrics = {
            'rank_ic': evaluator.calculator.calculate_rank_ic(predictions, actual_returns)
        }
        long_short = evaluator.calculator.calculate_long_short_return(
            predictions, actual_returns,
            top_pct=evaluator.config.top_pct,
            bottom_pct=evaluator.config.bottom_pct
        )
        metrics.update(long_short)

        if verbose:
            evaluator.formatter.print_metrics(metrics)

        return metrics
    else:
        raise ValueError(f"不支持的评估类型: {evaluation_type}，支持: 'regression', 'ranking'")
