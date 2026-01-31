"""
网格搜索优化器

遍历所有参数组合，找到最优参数：
- 支持多参数搜索
- 并行计算加速
- 自动生成参数重要性分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
from loguru import logger
from itertools import product
from dataclasses import dataclass
import time
import warnings

warnings.filterwarnings('ignore')


# ==================== 模块级函数（支持序列化）====================

def _evaluate_single_params_wrapper(args: Tuple) -> Dict:
    """
    评估单个参数组合的包装函数（模块级，支持multiprocessing序列化）

    Args:
        args: (参数字典, 目标函数, 是否详细日志) 元组

    Returns:
        {'params': params, 'score': score} 字典
    """
    params, objective_func, verbose_debug = args
    try:
        score = objective_func(params)
        return {'params': params, 'score': score}
    except Exception as e:
        if verbose_debug:
            logger.debug(f"参数{params}评估失败: {e}")
        return {'params': params, 'score': np.nan}


@dataclass
class GridSearchResult:
    """网格搜索结果数据类"""
    best_params: Dict[str, Any]  # 最优参数
    best_score: float  # 最优得分
    all_results: pd.DataFrame  # 所有结果
    search_time: float  # 搜索耗时
    n_combinations: int  # 总组合数

    def __str__(self) -> str:
        params_str = '\n'.join([f"  {k}: {v}" for k, v in self.best_params.items()])
        return (
            f"网格搜索结果:\n"
            f"最优参数:\n{params_str}\n"
            f"最优得分: {self.best_score:.4f}\n"
            f"搜索组合数: {self.n_combinations}\n"
            f"耗时: {self.search_time:.2f}秒"
        )


class GridSearchOptimizer:
    """
    网格搜索优化器

    用法：
        适用于参数空间较小的情况（< 1000组合）
        优点：遍历完整，不会遗漏最优解
        缺点：参数多时计算量大
    """

    def __init__(
        self,
        metric: str = 'sharpe_ratio',
        cv: int = 1,
        n_jobs: int = 1,
        verbose: bool = True
    ):
        """
        初始化网格搜索优化器

        Args:
            metric: 优化指标 ('sharpe_ratio', 'total_return', 'max_drawdown', etc.)
            cv: 交叉验证折数（1=不使用交叉验证）
            n_jobs: 并行任务数（1=串行，-1=全部CPU核心）
            verbose: 是否显示进度
        """
        self.metric = metric
        self.cv = cv
        self.n_jobs = n_jobs
        self.verbose = verbose

        logger.info(f"初始化网格搜索: 指标={metric}, CV={cv}, 并行={n_jobs}")

    def search(
        self,
        objective_func: Callable,
        param_grid: Dict[str, List[Any]],
        data: Optional[Dict] = None
    ) -> GridSearchResult:
        """
        执行网格搜索

        Args:
            objective_func: 目标函数，接受参数字典，返回得分
                示例: def objective(params): return strategy.backtest(**params)['sharpe_ratio']
            param_grid: 参数网格，如 {'lookback': [10, 20, 30], 'top_n': [30, 50]}
            data: 额外数据（可选）

        Returns:
            GridSearchResult对象
        """
        if not param_grid:
            raise ValueError("参数网格不能为空")

        logger.info("开始网格搜索...")
        start_time = time.time()

        # 生成所有参数组合
        param_combinations = self._generate_combinations(param_grid)
        n_combinations = len(param_combinations)

        logger.info(f"总参数组合数: {n_combinations}")

        # 评估所有组合
        results = []

        if self.n_jobs == 1:
            # 串行执行
            results = self._search_serial(objective_func, param_combinations)
        else:
            # 并行执行
            results = self._search_parallel(objective_func, param_combinations)

        # 整理结果
        results_df = pd.DataFrame(results)

        # 找到最优参数（排除NaN）
        valid_results = results_df[results_df['score'].notna()]
        if len(valid_results) == 0:
            raise ValueError("所有参数组合都失败了")

        best_idx = valid_results['score'].idxmax()
        best_params = valid_results.loc[best_idx, 'params']
        best_score = valid_results.loc[best_idx, 'score']

        search_time = time.time() - start_time

        result = GridSearchResult(
            best_params=best_params,
            best_score=best_score,
            all_results=results_df,
            search_time=search_time,
            n_combinations=n_combinations
        )

        logger.success(f"网格搜索完成: 最优得分={best_score:.4f}, 耗时={search_time:.2f}秒")

        return result

    def _generate_combinations(
        self,
        param_grid: Dict[str, List[Any]]
    ) -> List[Dict[str, Any]]:
        """生成所有参数组合"""
        keys = param_grid.keys()
        values = param_grid.values()

        combinations = [
            dict(zip(keys, v)) for v in product(*values)
        ]

        return combinations

    def _search_serial(
        self,
        objective_func: Callable,
        param_combinations: List[Dict]
    ) -> List[Dict]:
        """串行搜索"""
        results = []

        for i, params in enumerate(param_combinations):
            if self.verbose and (i + 1) % 10 == 0:
                logger.info(f"进度: {i+1}/{len(param_combinations)}")

            try:
                score = objective_func(params)

                results.append({
                    'params': params,
                    'score': score
                })

            except Exception as e:
                logger.debug(f"参数{params}评估失败: {e}")
                results.append({
                    'params': params,
                    'score': np.nan
                })

        return results

    def _search_parallel(
        self,
        objective_func: Callable,
        param_combinations: List[Dict]
    ) -> List[Dict]:
        """并行搜索（使用统一并行框架）"""
        try:
            from src.utils.parallel_executor import ParallelExecutor
            from src.config.features import ParallelComputingConfig

            logger.info(f"使用统一并行框架搜索（{self.n_jobs} workers）...")

            # 创建并行配置
            config = ParallelComputingConfig(
                enable_parallel=True,
                n_workers=self.n_jobs,
                show_progress=self.verbose,
                parallel_backend='multiprocessing'  # 网格搜索用多进程
            )

            # 准备任务（包装目标函数和参数）
            tasks = [(params, objective_func, False) for params in param_combinations]

            # 使用 ParallelExecutor
            try:
                with ParallelExecutor(config) as executor:
                    results = executor.map(
                        _evaluate_single_params_wrapper,
                        tasks,
                        desc="网格搜索",
                        ignore_errors=False  # 改为 False，让序列化错误直接抛出
                    )

                # 检查结果完整性
                if len(results) != len(param_combinations):
                    logger.warning(
                        f"并行搜索返回结果不完整 ({len(results)}/{len(param_combinations)})，回退到串行搜索"
                    )
                    return self._search_serial(objective_func, param_combinations)

                return results

            except Exception as e:
                error_msg = str(e)
                # 检查是否是序列化错误
                if "Can't pickle" in error_msg or "Can't get local object" in error_msg:
                    logger.warning(f"目标函数无法序列化，回退到串行搜索")
                else:
                    logger.warning(f"并行搜索失败({e})，回退到串行搜索")
                return self._search_serial(objective_func, param_combinations)

        except ImportError as e:
            logger.warning(f"并行框架导入失败({e})，回退到串行搜索")
            return self._search_serial(objective_func, param_combinations)

    def analyze_param_importance(
        self,
        search_result: GridSearchResult
    ) -> pd.DataFrame:
        """
        分析参数重要性

        Args:
            search_result: 网格搜索结果

        Returns:
            参数重要性DataFrame
        """
        logger.info("分析参数重要性...")

        results_df = search_result.all_results.copy()

        # 提取参数列
        param_cols = list(search_result.best_params.keys())

        # 为每个参数计算重要性
        importance_list = []

        for param in param_cols:
            # 提取该参数的所有值
            param_values = results_df['params'].apply(lambda x: x[param])
            results_df[f'param_{param}'] = param_values

            # 计算该参数不同取值的平均得分
            param_scores = results_df.groupby(f'param_{param}')['score'].agg(['mean', 'std', 'count'])

            # 计算得分范围（作为重要性度量）
            score_range = param_scores['mean'].max() - param_scores['mean'].min()

            importance_list.append({
                '参数名': param,
                '得分范围': score_range,
                '平均得分': param_scores['mean'].mean(),
                '最优值': search_result.best_params[param]
            })

        importance_df = pd.DataFrame(importance_list).sort_values('得分范围', ascending=False)

        # 计算重要性（归一化得分范围）
        max_range = importance_df['得分范围'].max()
        if max_range > 0:
            importance_df['重要性'] = importance_df['得分范围'] / max_range
        else:
            importance_df['重要性'] = 0.0

        logger.success("参数重要性分析完成")

        return importance_df

    def plot_param_sensitivity(
        self,
        search_result: GridSearchResult,
        param_name: str,
        save_path: Optional[str] = None
    ):
        """
        绘制参数敏感性曲线

        Args:
            search_result: 搜索结果
            param_name: 参数名称
            save_path: 保存路径（可选）
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')

            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            logger.info(f"绘制参数敏感性曲线: {param_name}")

            results_df = search_result.all_results.copy()

            # 提取参数值
            param_values = results_df['params'].apply(lambda x: x[param_name])
            results_df['param_value'] = param_values

            # 按参数值分组统计
            param_stats = results_df.groupby('param_value')['score'].agg(['mean', 'std', 'count'])
            param_stats = param_stats.sort_index()

            # 绘图
            fig, ax = plt.subplots(figsize=(10, 6))

            ax.plot(param_stats.index, param_stats['mean'], marker='o', linewidth=2, markersize=8)
            ax.fill_between(
                param_stats.index,
                param_stats['mean'] - param_stats['std'],
                param_stats['mean'] + param_stats['std'],
                alpha=0.3
            )

            # 标记最优值
            best_value = search_result.best_params[param_name]
            ax.axvline(x=best_value, color='red', linestyle='--', label=f'最优值={best_value}')

            ax.set_xlabel(param_name, fontsize=12)
            ax.set_ylabel(self.metric, fontsize=12)
            ax.set_title(f'{param_name}参数敏感性分析', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"参数敏感性图已保存: {save_path}")
            else:
                plt.savefig(f'/tmp/param_sensitivity_{param_name}.png', dpi=300, bbox_inches='tight')
                logger.info(f"参数敏感性图已保存: /tmp/param_sensitivity_{param_name}.png")

            plt.close()

        except ImportError:
            logger.warning("matplotlib未安装，跳过绘图")
        except Exception as e:
            logger.error(f"绘制参数敏感性图失败: {e}")


