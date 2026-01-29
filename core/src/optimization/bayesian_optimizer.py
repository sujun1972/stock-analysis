"""
贝叶斯优化器（Bayesian Optimization）

智能搜索参数空间，适用于：
- 参数空间较大的情况
- 目标函数计算昂贵
- 需要快速找到近似最优解

使用高斯过程（Gaussian Process）建模目标函数
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Callable, Tuple
from loguru import logger
from dataclasses import dataclass
import time
import warnings

warnings.filterwarnings('ignore')


@dataclass
class BayesianOptimizationResult:
    """贝叶斯优化结果数据类"""
    best_params: Dict[str, Any]
    best_score: float
    optimization_history: pd.DataFrame
    n_iterations: int
    search_time: float

    def __str__(self) -> str:
        params_str = '\n'.join([f"  {k}: {v}" for k, v in self.best_params.items()])
        return (
            f"贝叶斯优化结果:\n"
            f"最优参数:\n{params_str}\n"
            f"最优得分: {self.best_score:.4f}\n"
            f"迭代次数: {self.n_iterations}\n"
            f"耗时: {self.search_time:.2f}秒"
        )


class BayesianOptimizer:
    """
    贝叶斯优化器

    基于scikit-optimize (skopt)实现
    使用高斯过程建模 + 期望改进（Expected Improvement）采样
    """

    def __init__(
        self,
        n_calls: int = 50,
        n_initial_points: int = 10,
        acq_func: str = 'EI',
        random_state: int = 42
    ):
        """
        初始化贝叶斯优化器

        Args:
            n_calls: 总迭代次数（函数调用次数）
            n_initial_points: 随机初始化点数量
            acq_func: 采集函数 ('EI'=期望改进, 'PI'=改进概率, 'LCB'=置信下界)
            random_state: 随机种子
        """
        self.n_calls = n_calls
        self.n_initial_points = n_initial_points
        self.acq_func = acq_func
        self.random_state = random_state

        logger.info(
            f"初始化贝叶斯优化器: n_calls={n_calls}, "
            f"初始点={n_initial_points}, 采集函数={acq_func}"
        )

    def optimize(
        self,
        objective_func: Callable,
        param_space: Dict[str, Tuple],
        maximize: bool = True
    ) -> BayesianOptimizationResult:
        """
        执行贝叶斯优化

        Args:
            objective_func: 目标函数，接受参数字典，返回得分
            param_space: 参数空间定义，如:
                {
                    'lookback': (5, 50),  # 整数范围
                    'threshold': (0.0, 1.0),  # 浮点数范围
                    'method': ['pearson', 'spearman']  # 类别选择
                }
            maximize: 是否最大化（False则最小化）

        Returns:
            BayesianOptimizationResult对象
        """
        try:
            from skopt import gp_minimize
            from skopt.space import Real, Integer, Categorical
            from skopt.utils import use_named_args

            logger.info("开始贝叶斯优化...")
            start_time = time.time()

            # 构建skopt参数空间
            dimensions = []
            param_names = []

            for param_name, param_range in param_space.items():
                param_names.append(param_name)

                if isinstance(param_range, (list, tuple)) and not isinstance(param_range[0], (int, float)):
                    # 类别参数
                    dimensions.append(Categorical(param_range, name=param_name))
                elif isinstance(param_range[0], int):
                    # 整数参数
                    dimensions.append(Integer(param_range[0], param_range[1], name=param_name))
                else:
                    # 浮点数参数
                    dimensions.append(Real(param_range[0], param_range[1], name=param_name))

            # 定义优化目标（skopt只支持最小化，需要转换）
            @use_named_args(dimensions)
            def objective(**params):
                score = objective_func(params)

                # 转换为最小化问题
                if maximize:
                    return -score
                else:
                    return score

            # 执行优化
            result = gp_minimize(
                objective,
                dimensions,
                n_calls=self.n_calls,
                n_initial_points=self.n_initial_points,
                acq_func=self.acq_func,
                random_state=self.random_state,
                verbose=False
            )

            # 提取最优参数
            best_params = dict(zip(param_names, result.x))
            best_score = -result.fun if maximize else result.fun

            # 整理优化历史
            history = pd.DataFrame({
                'iteration': range(len(result.func_vals)),
                'score': -result.func_vals if maximize else result.func_vals,
                'best_so_far': np.minimum.accumulate(-result.func_vals if maximize else result.func_vals)
            })

            search_time = time.time() - start_time

            opt_result = BayesianOptimizationResult(
                best_params=best_params,
                best_score=best_score,
                optimization_history=history,
                n_iterations=len(result.func_vals),
                search_time=search_time
            )

            logger.success(
                f"贝叶斯优化完成: 最优得分={best_score:.4f}, "
                f"迭代次数={len(result.func_vals)}, 耗时={search_time:.2f}秒"
            )

            return opt_result

        except ImportError:
            logger.error(
                "scikit-optimize未安装，请安装: pip install scikit-optimize"
            )
            raise
        except Exception as e:
            logger.error(f"贝叶斯优化失败: {e}")
            raise

    def plot_convergence(
        self,
        result: BayesianOptimizationResult,
        save_path: Optional[str] = None
    ):
        """
        绘制收敛曲线

        Args:
            result: 优化结果
            save_path: 保存路径（可选）
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib
            matplotlib.use('Agg')

            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            logger.info("绘制贝叶斯优化收敛曲线...")

            fig, ax = plt.subplots(figsize=(10, 6))

            history = result.optimization_history

            # 绘制每次迭代的得分
            ax.scatter(
                history['iteration'],
                history['score'],
                alpha=0.5,
                label='迭代得分',
                s=30
            )

            # 绘制最优得分曲线
            ax.plot(
                history['iteration'],
                history['best_so_far'],
                color='red',
                linewidth=2,
                label='历史最优'
            )

            ax.set_xlabel('迭代次数', fontsize=12)
            ax.set_ylabel('得分', fontsize=12)
            ax.set_title('贝叶斯优化收敛曲线', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"收敛曲线已保存: {save_path}")
            else:
                plt.savefig('/tmp/bayesian_convergence.png', dpi=300, bbox_inches='tight')
                logger.info("收敛曲线已保存: /tmp/bayesian_convergence.png")

            plt.close()

        except ImportError:
            logger.warning("matplotlib未安装，跳过绘图")
        except Exception as e:
            logger.error(f"绘制收敛曲线失败: {e}")


