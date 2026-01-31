#!/usr/bin/env python3
"""
统一并行参数优化器

提供统一接口，支持多种优化方法的并行执行：
1. 并行网格搜索
2. 并行随机搜索
3. 并行贝叶斯优化（初始采样阶段）

作者: Stock Analysis Team
创建: 2026-01-31
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Callable, Optional, Tuple, Union
from dataclasses import dataclass
from loguru import logger
import time
import warnings

warnings.filterwarnings('ignore')

from src.utils.parallel_executor import ParallelExecutor
from src.config.features import ParallelComputingConfig
from src.optimization.grid_search import GridSearchOptimizer, GridSearchResult
from src.optimization.bayesian_optimizer import BayesianOptimizer, BayesianOptimizationResult


# ==================== 数据类 ====================

@dataclass
class OptimizationResult:
    """
    统一的优化结果

    兼容不同优化方法的结果格式
    """
    method: str  # 优化方法
    best_params: Dict[str, Any]  # 最优参数
    best_score: float  # 最优得分
    n_trials: int  # 试验次数
    search_time: float  # 搜索耗时
    all_results: Optional[pd.DataFrame] = None  # 所有结果
    optimization_history: Optional[pd.DataFrame] = None  # 优化历史（贝叶斯）

    def __str__(self) -> str:
        params_str = '\n'.join([f"  {k}: {v}" for k, v in self.best_params.items()])
        return (
            f"优化方法: {self.method}\n"
            f"最优参数:\n{params_str}\n"
            f"最优得分: {self.best_score:.4f}\n"
            f"试验次数: {self.n_trials}\n"
            f"耗时: {self.search_time:.2f}秒"
        )

    def to_dict(self) -> Dict:
        """转为字典"""
        return {
            'method': self.method,
            'best_params': self.best_params,
            'best_score': self.best_score,
            'n_trials': self.n_trials,
            'search_time': self.search_time
        }


# ==================== 核心类 ====================

class ParallelParameterOptimizer:
    """
    统一的并行参数优化器

    核心功能：
    1. 支持多种优化方法（网格、随机、贝叶斯）
    2. 统一使用 ParallelExecutor 进行并行计算
    3. 提供一致的接口和结果格式

    Example:
        >>> # 网格搜索
        >>> optimizer = ParallelParameterOptimizer(method='grid', n_workers=8)
        >>> param_space = {'lookback': [10, 20, 30], 'top_n': [30, 50]}
        >>> result = optimizer.optimize(objective_func, param_space)
        >>>
        >>> # 随机搜索
        >>> optimizer = ParallelParameterOptimizer(method='random', n_workers=8)
        >>> param_space = {'lookback': (5, 50), 'threshold': (0.0, 1.0)}
        >>> result = optimizer.optimize(objective_func, param_space, n_iter=100)
        >>>
        >>> # 贝叶斯优化
        >>> optimizer = ParallelParameterOptimizer(method='bayesian', n_workers=4)
        >>> result = optimizer.optimize(objective_func, param_space, n_calls=50)
    """

    def __init__(
        self,
        method: str = 'grid',
        n_workers: int = -1,
        parallel_config: Optional[ParallelComputingConfig] = None,
        verbose: bool = True,
        **optimizer_kwargs
    ):
        """
        初始化优化器

        Args:
            method: 优化方法 ('grid', 'random', 'bayesian')
            n_workers: 并行worker数量（-1=自动检测）
            parallel_config: 并行配置（可选，优先级最高）
            verbose: 是否显示详细日志
            **optimizer_kwargs: 传递给底层优化器的参数
        """
        if method not in ['grid', 'random', 'bayesian']:
            raise ValueError(
                f"不支持的优化方法: {method}。"
                f"支持的方法: grid, random, bayesian"
            )

        self.method = method
        self.n_workers = n_workers
        self.verbose = verbose
        self.optimizer_kwargs = optimizer_kwargs

        if parallel_config is None:
            parallel_config = ParallelComputingConfig(
                enable_parallel=True,
                n_workers=n_workers,
                show_progress=verbose,
                parallel_backend='multiprocessing'
            )

        self.parallel_config = parallel_config

        if verbose:
            logger.info(
                f"初始化并行优化器: method={method}, "
                f"n_workers={parallel_config.n_workers}"
            )

    def optimize(
        self,
        objective_func: Callable,
        param_space: Dict,
        maximize: bool = True,
        **kwargs
    ) -> OptimizationResult:
        """
        执行参数优化

        Args:
            objective_func: 目标函数，接受参数字典，返回得分
            param_space: 参数空间
                - 网格搜索: {'param1': [v1, v2, v3], 'param2': [v1, v2]}
                - 随机/贝叶斯: {'param1': (min, max), 'param2': [cat1, cat2]}
            maximize: 是否最大化目标函数（默认True）
            **kwargs: 额外参数
                - n_iter: 随机搜索迭代次数
                - n_calls: 贝叶斯优化调用次数
                - n_initial_points: 贝叶斯优化初始点数

        Returns:
            OptimizationResult对象
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"开始{self.method}参数优化")
        logger.info(f"{'='*70}\n")

        if self.method == 'grid':
            return self._optimize_grid(objective_func, param_space, **kwargs)
        elif self.method == 'random':
            return self._optimize_random(objective_func, param_space, maximize, **kwargs)
        elif self.method == 'bayesian':
            return self._optimize_bayesian(objective_func, param_space, maximize, **kwargs)
        else:
            raise ValueError(f"不支持的优化方法: {self.method}")

    def _optimize_grid(
        self,
        objective_func: Callable,
        param_grid: Dict,
        **kwargs
    ) -> OptimizationResult:
        """
        网格搜索优化

        Args:
            objective_func: 目标函数
            param_grid: 参数网格
            **kwargs: 额外参数

        Returns:
            OptimizationResult
        """
        # 使用改造后的 GridSearchOptimizer
        optimizer = GridSearchOptimizer(
            n_jobs=self.n_workers,
            verbose=self.verbose,
            **self.optimizer_kwargs
        )

        grid_result = optimizer.search(objective_func, param_grid)

        # 转换为统一格式
        result = OptimizationResult(
            method='grid',
            best_params=grid_result.best_params,
            best_score=grid_result.best_score,
            n_trials=grid_result.n_combinations,
            search_time=grid_result.search_time,
            all_results=grid_result.all_results
        )

        logger.success(f"\n网格搜索完成: {result}")

        return result

    def _optimize_random(
        self,
        objective_func: Callable,
        param_space: Dict,
        maximize: bool = True,
        n_iter: int = 50,
        **kwargs
    ) -> OptimizationResult:
        """
        随机搜索优化（并行版本）

        Args:
            objective_func: 目标函数
            param_space: 参数空间
            maximize: 是否最大化
            n_iter: 迭代次数
            **kwargs: 额外参数

        Returns:
            OptimizationResult
        """
        logger.info(f"开始并行随机搜索（{n_iter} 次迭代）...")
        start_time = time.time()

        # 生成随机参数组合
        param_combinations = self._generate_random_combinations(
            param_space,
            n_iter
        )

        # 并行评估
        def evaluate(params):
            try:
                score = objective_func(params)
                return {'params': params, 'score': score}
            except Exception as e:
                logger.debug(f"参数评估失败: {e}")
                return {'params': params, 'score': np.nan}

        try:
            with ParallelExecutor(self.parallel_config) as executor:
                results_list = executor.map(
                    evaluate,
                    param_combinations,
                    desc="随机搜索",
                    ignore_errors=True
                )
        except Exception as e:
            logger.warning(f"并行执行失败({e})，降级到串行")
            results_list = [evaluate(p) for p in param_combinations]

        # 整理结果
        results_df = pd.DataFrame(results_list)

        # 过滤有效结果
        valid_results = results_df[results_df['score'].notna()]

        if len(valid_results) == 0:
            raise ValueError("所有参数组合都失败了")

        # 找到最优
        if maximize:
            best_idx = valid_results['score'].idxmax()
        else:
            best_idx = valid_results['score'].idxmin()

        best_params = valid_results.loc[best_idx, 'params']
        best_score = valid_results.loc[best_idx, 'score']

        search_time = time.time() - start_time

        result = OptimizationResult(
            method='random',
            best_params=best_params,
            best_score=best_score,
            n_trials=n_iter,
            search_time=search_time,
            all_results=results_df
        )

        logger.success(f"\n随机搜索完成: {result}")

        return result

    def _optimize_bayesian(
        self,
        objective_func: Callable,
        param_space: Dict,
        maximize: bool = True,
        n_calls: int = 50,
        n_initial_points: int = 10,
        **kwargs
    ) -> OptimizationResult:
        """
        贝叶斯优化（初始点并行采样）

        注：贝叶斯优化的主循环本质上是串行的（高斯过程需要顺序更新），
        但初始随机采样阶段可以并行。

        Args:
            objective_func: 目标函数
            param_space: 参数空间
            maximize: 是否最大化
            n_calls: 总调用次数
            n_initial_points: 初始随机采样点数
            **kwargs: 额外参数

        Returns:
            OptimizationResult
        """
        logger.info("开始贝叶斯优化（初始采样并行）...")

        # 如果初始点数大于1且启用并行，则并行执行初始采样
        if n_initial_points > 1 and self.n_workers > 1:
            logger.info(f"并行执行初始 {n_initial_points} 个采样点...")

            # 生成初始随机点
            initial_combinations = self._generate_random_combinations(
                param_space,
                n_initial_points
            )

            # 并行评估初始点
            def evaluate(params):
                try:
                    return objective_func(params)
                except Exception as e:
                    logger.warning(f"初始点评估失败: {e}")
                    return np.nan

            try:
                with ParallelExecutor(self.parallel_config) as executor:
                    initial_scores = executor.map(
                        evaluate,
                        initial_combinations,
                        desc="初始采样",
                        ignore_errors=True
                    )
            except Exception as e:
                logger.warning(f"并行初始采样失败({e})，降级到串行")
                initial_scores = [evaluate(p) for p in initial_combinations]

            logger.info(f"初始采样完成，有效点数: {sum(1 for s in initial_scores if not np.isnan(s))}")

        # 使用标准贝叶斯优化器执行主循环
        optimizer = BayesianOptimizer(
            n_calls=n_calls,
            n_initial_points=n_initial_points,
            **self.optimizer_kwargs
        )

        bayesian_result = optimizer.optimize(
            objective_func,
            param_space,
            maximize=maximize
        )

        # 转换为统一格式
        result = OptimizationResult(
            method='bayesian',
            best_params=bayesian_result.best_params,
            best_score=bayesian_result.best_score,
            n_trials=bayesian_result.n_iterations,
            search_time=bayesian_result.search_time,
            optimization_history=bayesian_result.optimization_history
        )

        logger.success(f"\n贝叶斯优化完成: {result}")

        return result

    @staticmethod
    def _generate_random_combinations(
        param_space: Dict,
        n_samples: int,
        random_state: int = None
    ) -> List[Dict]:
        """
        生成随机参数组合

        Args:
            param_space: 参数空间
            n_samples: 采样数量
            random_state: 随机种子

        Returns:
            参数组合列表
        """
        if random_state is not None:
            np.random.seed(random_state)

        combinations = []

        for _ in range(n_samples):
            params = {}

            for param_name, param_range in param_space.items():
                if isinstance(param_range, list):
                    # 类别参数
                    params[param_name] = np.random.choice(param_range)

                elif isinstance(param_range, tuple) and len(param_range) == 2:
                    # 数值范围
                    min_val, max_val = param_range

                    if isinstance(min_val, int) and isinstance(max_val, int):
                        # 整数参数
                        params[param_name] = np.random.randint(min_val, max_val + 1)
                    else:
                        # 浮点数参数
                        params[param_name] = np.random.uniform(min_val, max_val)

                else:
                    raise ValueError(
                        f"不支持的参数范围格式: {param_name}={param_range}。"
                        f"应为 list（类别）或 tuple（范围）"
                    )

            combinations.append(params)

        return combinations

    def compare_methods(
        self,
        objective_func: Callable,
        param_space: Dict,
        methods: Optional[List[str]] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        对比不同优化方法的效果

        Args:
            objective_func: 目标函数
            param_space: 参数空间
            methods: 要对比的方法列表（None=全部）
            **kwargs: 传递给各方法的参数

        Returns:
            对比结果 DataFrame
        """
        if methods is None:
            methods = ['grid', 'random', 'bayesian']

        logger.info(f"\n{'='*70}")
        logger.info(f"对比优化方法: {methods}")
        logger.info(f"{'='*70}\n")

        results_list = []

        for method in methods:
            try:
                # 临时切换方法
                original_method = self.method
                self.method = method

                result = self.optimize(objective_func, param_space, **kwargs)

                results_list.append({
                    '方法': method,
                    '最优得分': result.best_score,
                    '试验次数': result.n_trials,
                    '耗时(秒)': round(result.search_time, 2),
                    '最优参数': str(result.best_params)
                })

                # 恢复原方法
                self.method = original_method

            except Exception as e:
                logger.error(f"方法 {method} 失败: {e}")

        # 创建对比表
        comparison_df = pd.DataFrame(results_list)

        logger.info("\n" + "="*70)
        logger.info("优化方法对比结果")
        logger.info("="*70)
        logger.info(f"\n{comparison_df.to_string(index=False)}\n")

        return comparison_df


# ==================== 便捷函数 ====================

def parallel_grid_search(
    objective_func: Callable,
    param_grid: Dict,
    n_workers: int = -1,
    verbose: bool = True
) -> OptimizationResult:
    """
    便捷函数：并行网格搜索

    Args:
        objective_func: 目标函数
        param_grid: 参数网格
        n_workers: worker数量
        verbose: 是否显示详细日志

    Returns:
        OptimizationResult

    Example:
        >>> param_grid = {'lookback': [10, 20, 30], 'top_n': [30, 50]}
        >>> result = parallel_grid_search(my_objective, param_grid, n_workers=8)
    """
    optimizer = ParallelParameterOptimizer(
        method='grid',
        n_workers=n_workers,
        verbose=verbose
    )

    return optimizer.optimize(objective_func, param_grid)


def parallel_random_search(
    objective_func: Callable,
    param_space: Dict,
    n_iter: int = 50,
    n_workers: int = -1,
    maximize: bool = True,
    verbose: bool = True
) -> OptimizationResult:
    """
    便捷函数：并行随机搜索

    Args:
        objective_func: 目标函数
        param_space: 参数空间
        n_iter: 迭代次数
        n_workers: worker数量
        maximize: 是否最大化
        verbose: 是否显示详细日志

    Returns:
        OptimizationResult

    Example:
        >>> param_space = {'lookback': (5, 50), 'threshold': (0.0, 1.0)}
        >>> result = parallel_random_search(my_objective, param_space, n_iter=100, n_workers=8)
    """
    optimizer = ParallelParameterOptimizer(
        method='random',
        n_workers=n_workers,
        verbose=verbose
    )

    return optimizer.optimize(objective_func, param_space, maximize=maximize, n_iter=n_iter)
