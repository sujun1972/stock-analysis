"""
结果格式化器
负责格式化和展示评估结果
"""
from typing import Dict
from loguru import logger


class ResultFormatter:
    """结果格式化器：负责格式化和展示评估结果"""

    @staticmethod
    def print_metrics(metrics: Dict[str, float]) -> None:
        """
        打印评估指标

        Args:
            metrics: 指标字典
        """
        if not metrics:
            logger.info("没有可用的评估指标")
            return

        logger.info("\n" + "="*60)
        logger.info("模型评估指标")
        logger.info("="*60)

        # 分类显示
        regression_metrics = ['mse', 'rmse', 'mae', 'r2']
        ic_metrics = [
            'ic', 'rank_ic', 'ic_mean', 'ic_std', 'ic_ir',
            'ic_positive_rate', 'rank_ic_mean', 'rank_ic_std',
            'rank_ic_ir', 'rank_ic_positive_rate'
        ]
        return_metrics = ['long_return', 'short_return', 'long_short_return']

        # 传统回归指标
        if any(m in metrics for m in regression_metrics):
            logger.info("\n回归指标:")
            for metric in regression_metrics:
                if metric in metrics:
                    logger.info(f"  {metric.upper():12s}: {metrics[metric]:.6f}")

        # IC 指标
        if any(m in metrics for m in ic_metrics):
            logger.info("\nIC 指标:")
            for metric in ic_metrics:
                if metric in metrics:
                    logger.info(f"  {metric.upper():24s}: {metrics[metric]:.6f}")

        # 分组收益率
        group_metrics = sorted([k for k in metrics.keys() if k.startswith('group_')])
        if group_metrics:
            logger.info("\n分组收益率:")
            for metric in group_metrics:
                logger.info(f"  {metric:20s}: {metrics[metric]:.6f}")

        # 多空收益
        if any(m in metrics for m in return_metrics):
            logger.info("\n多空收益:")
            for metric in return_metrics:
                if metric in metrics:
                    logger.info(f"  {metric:20s}: {metrics[metric]:.6f}")

        # 其他指标
        other_metrics = [
            k for k in metrics.keys()
            if k not in regression_metrics + ic_metrics + return_metrics + group_metrics
        ]
        if other_metrics:
            logger.info("\n其他指标:")
            for metric in other_metrics:
                logger.info(f"  {metric:20s}: {metrics[metric]:.6f}")

        logger.info("="*60 + "\n")
