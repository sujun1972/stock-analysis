"""
超参数调优模块
提供网格搜索、随机搜索和贝叶斯优化等超参数调优工具

职责:
- 网格搜索（Grid Search）
- 随机搜索（Random Search）
- 贝叶斯优化（Bayesian Optimization，可选）
- 超参数重要性分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable
from loguru import logger
from dataclasses import dataclass
import itertools
from pathlib import Path
import json

from .model_trainer import ModelTrainer, TrainingConfig, DataSplitConfig
from src.utils.response import Response


@dataclass
class TuningConfig:
    """超参数调优配置"""
    n_trials: int = 20  # 随机搜索试验次数
    cv_splits: int = 3  # 交叉验证折数
    scoring_metric: str = 'rmse'  # 评分指标（rmse, r2, ic）
    verbose: bool = True
    save_results: bool = True
    output_dir: str = 'data/models/tuning_results'


class GridSearchTuner:
    """
    网格搜索调优器

    遍历所有超参数组合，找到最优配置

    Examples:
        >>> param_grid = {
        ...     'learning_rate': [0.01, 0.05, 0.1],
        ...     'num_leaves': [31, 63, 127]
        ... }
        >>> tuner = GridSearchTuner()
        >>> result = tuner.tune(
        ...     df=data,
        ...     feature_cols=features,
        ...     target_col='target_return_5d',
        ...     model_type='lightgbm',
        ...     param_grid=param_grid
        ... )
        >>> best_params = result.data['best_params']
    """

    def __init__(self, config: Optional[TuningConfig] = None):
        """初始化网格搜索调优器"""
        self.config = config or TuningConfig()
        self.results: List[Dict[str, Any]] = []

    def tune(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        model_type: str,
        param_grid: Dict[str, List[Any]],
        base_params: Optional[Dict[str, Any]] = None
    ) -> Response:
        """
        执行网格搜索

        Args:
            df: 输入数据
            feature_cols: 特征列
            target_col: 目标列
            model_type: 模型类型
            param_grid: 参数网格 {参数名: [候选值列表]}
            base_params: 基础参数（不调优的参数）

        Returns:
            Response对象，成功时data包含:
            {
                'best_params': 最优参数,
                'best_score': 最优得分,
                'all_results': 所有试验结果
            }
        """
        try:
            logger.info("="*60)
            logger.info(f"网格搜索超参数调优 - {model_type.upper()}")
            logger.info("="*60)

            # 生成参数组合
            param_names = list(param_grid.keys())
            param_values = list(param_grid.values())
            param_combinations = list(itertools.product(*param_values))

            n_combinations = len(param_combinations)
            logger.info(f"参数网格: {param_grid}")
            logger.info(f"总组合数: {n_combinations}")

            base_params = base_params or {}
            self.results = []

            # 准备数据（一次性准备）
            split_config = DataSplitConfig(train_ratio=0.7, valid_ratio=0.15)

            for idx, param_combo in enumerate(param_combinations, 1):
                # 构建参数字典
                params = {**base_params}
                for name, value in zip(param_names, param_combo):
                    params[name] = value

                logger.info(f"\n[{idx}/{n_combinations}] 测试参数: {params}")

                # 训练和评估
                score, metrics = self._evaluate_params(
                    df, feature_cols, target_col,
                    model_type, params, split_config
                )

                # 记录结果
                self.results.append({
                    'params': params,
                    'score': score,
                    'metrics': metrics
                })

                if self.config.verbose:
                    logger.info(f"  {self.config.scoring_metric.upper()}: {score:.6f}")

            # 找到最优参数
            best_result = self._get_best_result()

            logger.info("\n" + "="*60)
            logger.info("网格搜索完成")
            logger.info("="*60)
            logger.info(f"最优参数: {best_result['params']}")
            logger.info(f"最优得分: {best_result['score']:.6f}")

            # 保存结果
            if self.config.save_results:
                self._save_results(model_type, 'grid_search')

            return Response.success(
                data={
                    'best_params': best_result['params'],
                    'best_score': best_result['score'],
                    'best_metrics': best_result['metrics'],
                    'all_results': self.results
                },
                message="网格搜索完成",
                n_trials=n_combinations
            )

        except Exception as e:
            logger.exception(f"网格搜索失败: {e}")
            return Response.error(
                error=f"网格搜索失败: {str(e)}",
                error_code="GRID_SEARCH_ERROR"
            )

    def _evaluate_params(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        model_type: str,
        params: Dict[str, Any],
        split_config: DataSplitConfig
    ) -> Tuple[float, Dict[str, float]]:
        """评估单组参数"""
        try:
            # 创建训练器
            training_config = TrainingConfig(
                model_type=model_type,
                model_params=params
            )
            trainer = ModelTrainer(config=training_config)

            # 准备数据
            prepare_response = trainer.prepare_data(
                df, feature_cols, target_col, split_config
            )

            if not prepare_response.is_success():
                return float('inf'), {}

            data = prepare_response.data
            X_train = data['X_train']
            y_train = data['y_train']
            X_valid = data['X_valid']
            y_valid = data['y_valid']

            # 训练
            train_response = trainer.train(X_train, y_train, X_valid, y_valid)

            if not train_response.is_success():
                return float('inf'), {}

            # 评估
            eval_response = trainer.evaluate(X_valid, y_valid, verbose=False)

            if not eval_response.is_success():
                return float('inf'), {}

            metrics = eval_response.data

            # 提取评分
            if self.config.scoring_metric == 'rmse':
                score = metrics['rmse']
            elif self.config.scoring_metric == 'r2':
                score = -metrics['r2']  # 负号，因为我们要最小化
            elif self.config.scoring_metric == 'ic':
                score = -metrics.get('ic', 0)
            else:
                score = metrics['rmse']

            return score, metrics

        except Exception as e:
            logger.error(f"参数评估失败: {e}")
            return float('inf'), {}

    def _get_best_result(self) -> Dict[str, Any]:
        """获取最优结果"""
        if not self.results:
            raise ValueError("没有有效的试验结果")

        # 按得分排序（升序）
        sorted_results = sorted(self.results, key=lambda x: x['score'])
        return sorted_results[0]

    def _save_results(self, model_type: str, method: str) -> None:
        """保存调优结果"""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{model_type}_{method}_results.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"调优结果已保存至: {output_file}")


class RandomSearchTuner:
    """
    随机搜索调优器

    随机采样超参数组合，比网格搜索更高效

    Examples:
        >>> param_distributions = {
        ...     'learning_rate': (0.01, 0.3, 'log'),
        ...     'num_leaves': (20, 150, 'int')
        ... }
        >>> tuner = RandomSearchTuner(n_trials=20)
        >>> result = tuner.tune(
        ...     df=data,
        ...     feature_cols=features,
        ...     target_col='target_return_5d',
        ...     model_type='lightgbm',
        ...     param_distributions=param_distributions
        ... )
    """

    def __init__(self, config: Optional[TuningConfig] = None):
        """初始化随机搜索调优器"""
        self.config = config or TuningConfig()
        self.results: List[Dict[str, Any]] = []

    def tune(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        model_type: str,
        param_distributions: Dict[str, Tuple[Any, Any, str]],
        base_params: Optional[Dict[str, Any]] = None
    ) -> Response:
        """
        执行随机搜索

        Args:
            df: 输入数据
            feature_cols: 特征列
            target_col: 目标列
            model_type: 模型类型
            param_distributions: 参数分布 {参数名: (最小值, 最大值, 类型)}
                类型: 'uniform', 'log', 'int'
            base_params: 基础参数

        Returns:
            Response对象
        """
        try:
            logger.info("="*60)
            logger.info(f"随机搜索超参数调优 - {model_type.upper()}")
            logger.info("="*60)
            logger.info(f"参数分布: {param_distributions}")
            logger.info(f"试验次数: {self.config.n_trials}")

            base_params = base_params or {}
            self.results = []

            split_config = DataSplitConfig(train_ratio=0.7, valid_ratio=0.15)

            for trial in range(self.config.n_trials):
                # 随机采样参数
                params = {**base_params}
                for param_name, (low, high, dist_type) in param_distributions.items():
                    if dist_type == 'uniform':
                        params[param_name] = np.random.uniform(low, high)
                    elif dist_type == 'log':
                        params[param_name] = np.exp(np.random.uniform(np.log(low), np.log(high)))
                    elif dist_type == 'int':
                        params[param_name] = np.random.randint(low, high + 1)
                    else:
                        params[param_name] = np.random.uniform(low, high)

                logger.info(f"\n[{trial + 1}/{self.config.n_trials}] 测试参数: {params}")

                # 评估
                score, metrics = self._evaluate_params(
                    df, feature_cols, target_col,
                    model_type, params, split_config
                )

                self.results.append({
                    'trial': trial + 1,
                    'params': params,
                    'score': score,
                    'metrics': metrics
                })

                if self.config.verbose:
                    logger.info(f"  {self.config.scoring_metric.upper()}: {score:.6f}")

            # 找到最优参数
            best_result = self._get_best_result()

            logger.info("\n" + "="*60)
            logger.info("随机搜索完成")
            logger.info("="*60)
            logger.info(f"最优参数: {best_result['params']}")
            logger.info(f"最优得分: {best_result['score']:.6f}")

            # 保存结果
            if self.config.save_results:
                self._save_results(model_type, 'random_search')

            return Response.success(
                data={
                    'best_params': best_result['params'],
                    'best_score': best_result['score'],
                    'best_metrics': best_result['metrics'],
                    'all_results': self.results
                },
                message="随机搜索完成",
                n_trials=self.config.n_trials
            )

        except Exception as e:
            logger.exception(f"随机搜索失败: {e}")
            return Response.error(
                error=f"随机搜索失败: {str(e)}",
                error_code="RANDOM_SEARCH_ERROR"
            )

    def _evaluate_params(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str,
        model_type: str,
        params: Dict[str, Any],
        split_config: DataSplitConfig
    ) -> Tuple[float, Dict[str, float]]:
        """评估单组参数（同 GridSearchTuner）"""
        try:
            training_config = TrainingConfig(
                model_type=model_type,
                model_params=params
            )
            trainer = ModelTrainer(config=training_config)

            prepare_response = trainer.prepare_data(
                df, feature_cols, target_col, split_config
            )

            if not prepare_response.is_success():
                return float('inf'), {}

            data = prepare_response.data
            X_train = data['X_train']
            y_train = data['y_train']
            X_valid = data['X_valid']
            y_valid = data['y_valid']

            train_response = trainer.train(X_train, y_train, X_valid, y_valid)

            if not train_response.is_success():
                return float('inf'), {}

            eval_response = trainer.evaluate(X_valid, y_valid, verbose=False)

            if not eval_response.is_success():
                return float('inf'), {}

            metrics = eval_response.data

            if self.config.scoring_metric == 'rmse':
                score = metrics['rmse']
            elif self.config.scoring_metric == 'r2':
                score = -metrics['r2']
            elif self.config.scoring_metric == 'ic':
                score = -metrics.get('ic', 0)
            else:
                score = metrics['rmse']

            return score, metrics

        except Exception as e:
            logger.error(f"参数评估失败: {e}")
            return float('inf'), {}

    def _get_best_result(self) -> Dict[str, Any]:
        """获取最优结果"""
        if not self.results:
            raise ValueError("没有有效的试验结果")

        sorted_results = sorted(self.results, key=lambda x: x['score'])
        return sorted_results[0]

    def _save_results(self, model_type: str, method: str) -> None:
        """保存调优结果"""
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / f"{model_type}_{method}_results.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        logger.info(f"调优结果已保存至: {output_file}")


class HyperparameterAnalyzer:
    """
    超参数重要性分析器

    分析不同超参数对模型性能的影响
    """

    @staticmethod
    def analyze_importance(
        tuning_results: List[Dict[str, Any]],
        top_k: int = 10
    ) -> Response:
        """
        分析超参数重要性

        Args:
            tuning_results: 调优结果列表
            top_k: 显示 top k 个最佳结果

        Returns:
            Response对象，包含参数重要性分析
        """
        try:
            if not tuning_results:
                return Response.error(
                    error="调优结果为空",
                    error_code="EMPTY_RESULTS"
                )

            # 按得分排序
            sorted_results = sorted(tuning_results, key=lambda x: x['score'])

            logger.info("\n" + "="*60)
            logger.info(f"Top {top_k} 参数组合")
            logger.info("="*60)

            for i, result in enumerate(sorted_results[:top_k], 1):
                logger.info(f"\n#{i}: Score = {result['score']:.6f}")
                logger.info(f"  参数: {result['params']}")

            # 分析参数范围
            param_names = list(sorted_results[0]['params'].keys())
            param_stats = {}

            for param_name in param_names:
                values = [r['params'][param_name] for r in sorted_results[:top_k]]

                if isinstance(values[0], (int, float)):
                    param_stats[param_name] = {
                        'mean': float(np.mean(values)),
                        'std': float(np.std(values)),
                        'min': float(np.min(values)),
                        'max': float(np.max(values))
                    }

            logger.info("\n" + "="*60)
            logger.info("Top 参数统计")
            logger.info("="*60)
            for param_name, stats in param_stats.items():
                logger.info(f"\n{param_name}:")
                logger.info(f"  平均: {stats['mean']:.4f}")
                logger.info(f"  标准差: {stats['std']:.4f}")
                logger.info(f"  范围: [{stats['min']:.4f}, {stats['max']:.4f}]")

            return Response.success(
                data={
                    'top_results': sorted_results[:top_k],
                    'param_stats': param_stats
                },
                message="参数重要性分析完成"
            )

        except Exception as e:
            logger.exception(f"参数重要性分析失败: {e}")
            return Response.error(
                error=f"参数重要性分析失败: {str(e)}",
                error_code="IMPORTANCE_ANALYSIS_ERROR"
            )


# ==================== 便捷函数 ====================

def tune_hyperparameters(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    model_type: str = 'lightgbm',
    method: str = 'random',
    param_space: Optional[Dict[str, Any]] = None,
    n_trials: int = 20
) -> Response:
    """
    便捷函数：超参数调优

    Args:
        df: 数据 DataFrame
        feature_cols: 特征列
        target_col: 目标列
        model_type: 模型类型
        method: 调优方法 ('grid', 'random')
        param_space: 参数空间
        n_trials: 试验次数（随机搜索）

    Returns:
        Response对象

    Examples:
        >>> result = tune_hyperparameters(
        ...     df=data,
        ...     feature_cols=features,
        ...     target_col='target_return_5d',
        ...     method='random',
        ...     n_trials=20
        ... )
        >>> best_params = result.data['best_params']
    """
    config = TuningConfig(n_trials=n_trials)

    # 默认参数空间（LightGBM）
    if param_space is None and model_type == 'lightgbm':
        if method == 'grid':
            param_space = {
                'learning_rate': [0.01, 0.05, 0.1],
                'num_leaves': [31, 63, 127],
                'max_depth': [5, 7, 10]
            }
        else:  # random
            param_space = {
                'learning_rate': (0.01, 0.3, 'log'),
                'num_leaves': (20, 150, 'int'),
                'max_depth': (5, 15, 'int')
            }

    if method == 'grid':
        tuner = GridSearchTuner(config=config)
        return tuner.tune(
            df=df,
            feature_cols=feature_cols,
            target_col=target_col,
            model_type=model_type,
            param_grid=param_space
        )
    elif method == 'random':
        tuner = RandomSearchTuner(config=config)
        return tuner.tune(
            df=df,
            feature_cols=feature_cols,
            target_col=target_col,
            model_type=model_type,
            param_distributions=param_space
        )
    else:
        return Response.error(
            error=f"不支持的调优方法: {method}",
            error_code="UNSUPPORTED_TUNING_METHOD"
        )
