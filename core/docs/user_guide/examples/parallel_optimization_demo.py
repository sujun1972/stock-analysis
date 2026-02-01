#!/usr/bin/env python3
"""
并行参数优化功能演示

演示如何使用 ParallelParameterOptimizer 进行并行参数优化。

运行方式:
    # 使用虚拟环境
    /path/to/venv/bin/python examples/parallel_optimization_demo.py

    # 或激活虚拟环境后
    python examples/parallel_optimization_demo.py

作者: Stock Analysis Team
创建: 2026-01-31
"""

import pandas as pd
import numpy as np
from loguru import logger
import time


# ==================== 示例1：并行网格搜索 ====================

def example1_parallel_grid_search():
    """示例1：并行网格搜索优化"""
    from src.optimization.parallel_optimizer import ParallelParameterOptimizer

    logger.info("\n" + "=" * 70)
    logger.info("示例1：并行网格搜索")
    logger.info("=" * 70)

    # 定义目标函数（模拟策略回测）
    def backtest_objective(params):
        lookback = params['lookback']
        top_n = params['top_n']

        # 模拟：最优参数为 lookback=20, top_n=50
        score = 1.5 - abs(lookback - 20) / 50.0 - abs(top_n - 50) / 100.0

        # 添加随机噪声
        np.random.seed(int(lookback * top_n) % 1000)
        score += np.random.randn() * 0.05

        return max(score, 0.0)

    # 创建优化器
    optimizer = ParallelParameterOptimizer(
        method='grid',
        n_workers=4,
        verbose=True
    )

    # 定义参数网格
    param_grid = {
        'lookback': [5, 10, 15, 20, 25, 30],
        'top_n': [20, 30, 40, 50, 60, 70]
    }

    logger.info(f"参数组合数: {6 * 6} = 36")

    # 执行优化
    result = optimizer.optimize(backtest_objective, param_grid)

    logger.success(f"\n{result}")
    logger.info(f"最优参数: lookback={result.best_params['lookback']}, top_n={result.best_params['top_n']}")


# ==================== 示例2：并行随机搜索 ====================

def example2_parallel_random_search():
    """示例2：并行随机搜索优化"""
    from src.optimization.parallel_optimizer import ParallelParameterOptimizer

    logger.info("\n" + "=" * 70)
    logger.info("示例2：并行随机搜索")
    logger.info("=" * 70)

    # 目标函数：最小化 (x-5)^2 + (y-3)^2
    def sphere_function(params):
        x = params['x']
        y = params['y']
        return -((x - 5)**2 + (y - 3)**2)  # 负号因为要最大化

    # 创建优化器
    optimizer = ParallelParameterOptimizer(
        method='random',
        n_workers=4,
        verbose=True
    )

    # 定义参数空间
    param_space = {
        'x': (0, 10),  # 浮点数范围
        'y': (0, 10)   # 浮点数范围
    }

    # 执行优化
    result = optimizer.optimize(
        sphere_function,
        param_space,
        maximize=True,
        n_iter=100
    )

    logger.success(f"\n{result}")
    logger.info(f"最优参数: x={result.best_params['x']:.4f}, y={result.best_params['y']:.4f}")
    logger.info(f"期望最优解: x=5.0, y=3.0")


# ==================== 示例3：贝叶斯优化（初始采样并行）====================

def example3_bayesian_optimization():
    """示例3：贝叶斯优化（并行初始采样）"""
    from src.optimization.parallel_optimizer import ParallelParameterOptimizer

    logger.info("\n" + "=" * 70)
    logger.info("示例3：贝叶斯优化（并行初始采样）")
    logger.info("=" * 70)

    # 复杂目标函数
    def complex_objective(params):
        x = params['x']
        y = params['y']

        # Rosenbrock 函数变种
        result = -((1 - x)**2 + 100 * (y - x**2)**2) / 1000.0

        # 添加噪声
        result += np.random.randn() * 0.01

        return result

    try:
        # 创建优化器
        optimizer = ParallelParameterOptimizer(
            method='bayesian',
            n_workers=4,
            verbose=True
        )

        # 定义参数空间
        param_space = {
            'x': (-2.0, 2.0),
            'y': (-1.0, 3.0)
        }

        # 执行优化
        result = optimizer.optimize(
            complex_objective,
            param_space,
            maximize=True,
            n_calls=30,
            n_initial_points=10
        )

        logger.success(f"\n{result}")
        logger.info(f"最优参数: x={result.best_params['x']:.4f}, y={result.best_params['y']:.4f}")

    except ImportError:
        logger.warning("scikit-optimize 未安装，跳过贝叶斯优化示例")


# ==================== 示例4：混合参数类型 ====================

def example4_mixed_parameter_types():
    """示例4：混合参数类型（整数、浮点、类别）"""
    from src.optimization.parallel_optimizer import ParallelParameterOptimizer

    logger.info("\n" + "=" * 70)
    logger.info("示例4：混合参数类型")
    logger.info("=" * 70)

    # 目标函数
    def mixed_objective(params):
        lookback = params['lookback']
        threshold = params['threshold']
        method = params['method']

        # 基础分数
        score = 1.0 - abs(lookback - 20) / 50.0

        # 阈值调整
        if method == 'pearson':
            score += (1.0 - abs(threshold - 0.5)) * 0.3
        elif method == 'spearman':
            score += (1.0 - abs(threshold - 0.3)) * 0.3
        else:
            score += (1.0 - abs(threshold - 0.7)) * 0.3

        return score

    # 随机搜索
    optimizer = ParallelParameterOptimizer(
        method='random',
        n_workers=4,
        verbose=True
    )

    # 混合参数空间
    param_space = {
        'lookback': (5, 50),                        # 整数
        'threshold': (0.0, 1.0),                    # 浮点数
        'method': ['pearson', 'spearman', 'kendall']  # 类别
    }

    result = optimizer.optimize(
        mixed_objective,
        param_space,
        n_iter=50
    )

    logger.success(f"\n{result}")
    logger.info(
        f"最优参数: lookback={result.best_params['lookback']}, "
        f"threshold={result.best_params['threshold']:.4f}, "
        f"method={result.best_params['method']}"
    )


# ==================== 示例5：使用便捷函数 ====================

def example5_convenience_functions():
    """示例5：使用便捷函数"""
    from src.optimization.parallel_optimizer import (
        parallel_grid_search,
        parallel_random_search
    )

    logger.info("\n" + "=" * 70)
    logger.info("示例5：使用便捷函数")
    logger.info("=" * 70)

    # 简单目标函数
    def simple_objective(params):
        x = params['x']
        return -(x - 7)**2

    # 1. 便捷网格搜索
    logger.info("\n[1] 便捷网格搜索...")
    param_grid = {'x': [5, 6, 7, 8, 9]}

    result1 = parallel_grid_search(
        simple_objective,
        param_grid,
        n_workers=2,
        verbose=False
    )

    logger.success(f"网格搜索最优: x={result1.best_params['x']}, score={result1.best_score:.4f}")

    # 2. 便捷随机搜索
    logger.info("\n[2] 便捷随机搜索...")
    param_space = {'x': (0, 15)}

    result2 = parallel_random_search(
        simple_objective,
        param_space,
        n_iter=30,
        n_workers=2,
        verbose=False
    )

    logger.success(f"随机搜索最优: x={result2.best_params['x']:.4f}, score={result2.best_score:.4f}")


# ==================== 示例6：串行 vs 并行性能对比 ====================

def example6_performance_comparison():
    """示例6：串行 vs 并行性能对比"""
    from src.optimization.parallel_optimizer import ParallelParameterOptimizer

    logger.info("\n" + "=" * 70)
    logger.info("示例6：串行 vs 并行性能对比")
    logger.info("=" * 70)

    # 耗时的目标函数
    def expensive_objective(params):
        x = params['x']
        y = params['y']

        # 模拟耗时计算
        time.sleep(0.01)

        return -(x**2 + y**2)

    # 参数空间
    param_grid = {
        'x': list(range(-10, 11, 2)),  # 11 个值
        'y': list(range(-10, 11, 2))   # 11 个值
    }

    logger.info(f"参数组合数: {11 * 11} = 121")

    # 串行优化
    logger.info("\n[1/2] 串行优化...")
    optimizer_serial = ParallelParameterOptimizer(
        method='grid',
        n_workers=1,
        verbose=False
    )

    start = time.time()
    result_serial = optimizer_serial.optimize(expensive_objective, param_grid)
    time_serial = time.time() - start

    logger.info(f"串行耗时: {time_serial:.2f}秒")

    # 并行优化
    logger.info("\n[2/2] 并行优化（4 workers）...")
    optimizer_parallel = ParallelParameterOptimizer(
        method='grid',
        n_workers=4,
        verbose=False
    )

    start = time.time()
    result_parallel = optimizer_parallel.optimize(expensive_objective, param_grid)
    time_parallel = time.time() - start

    logger.info(f"并行耗时: {time_parallel:.2f}秒")

    # 性能对比
    speedup = time_serial / time_parallel
    logger.success(f"\n⚡ 加速比: {speedup:.2f}x")

    # 验证结果一致
    assert result_serial.best_score == result_parallel.best_score
    logger.success("✓ 结果一致！")


# ==================== 示例7：实际回测参数优化 ====================

def example7_real_backtest_optimization():
    """示例7：实际回测参数优化"""
    from src.optimization.parallel_optimizer import ParallelParameterOptimizer
    from src.strategies.momentum_strategy import MomentumStrategy
    from src.backtest.backtest_engine import BacktestEngine

    logger.info("\n" + "=" * 70)
    logger.info("示例7：实际回测参数优化")
    logger.info("=" * 70)

    # 生成测试数据
    dates = pd.date_range('2020-01-01', periods=200, freq='D')
    stocks = [f'stock_{i}' for i in range(50)]

    np.random.seed(42)
    prices = 100 * (1 + np.random.randn(200, 50) * 0.02).cumprod(axis=0)
    prices_df = pd.DataFrame(prices, index=dates, columns=stocks)

    logger.info(f"数据形状: {prices_df.shape}")

    # 定义回测目标函数
    def backtest_objective(params):
        try:
            # 创建策略
            strategy = MomentumStrategy(
                name="MomentumStrategy",
                config=params
            )

            # 生成信号
            signals = strategy.generate_signals(prices_df)

            # 回测
            engine = BacktestEngine(verbose=False)
            result = engine.backtest_long_only(
                signals=signals,
                prices=prices_df,
                top_n=params.get('top_n', 20),
                holding_period=5,
                rebalance_freq='W'
            )

            # 返回夏普比率
            return result['metrics'].get('sharpe_ratio', 0.0)

        except Exception as e:
            logger.debug(f"回测失败: {e}")
            return 0.0

    # 网格搜索优化
    optimizer = ParallelParameterOptimizer(
        method='grid',
        n_workers=4,
        verbose=True
    )

    param_grid = {
        'lookback': [10, 15, 20, 25],
        'top_n': [15, 20, 25]
    }

    logger.info(f"开始优化（{4*3}=12 个组合）...")

    result = optimizer.optimize(backtest_objective, param_grid)

    logger.success(f"\n{result}")
    logger.info(f"最优夏普比率: {result.best_score:.4f}")
    logger.info(f"最优参数: {result.best_params}")


# ==================== 主函数 ====================

if __name__ == "__main__":
    import multiprocessing as mp

    logger.info("\n" + "=" * 70)
    logger.info("并行参数优化功能演示")
    logger.info("=" * 70)
    logger.info(f"系统CPU核心数: {mp.cpu_count()}")
    logger.info("=" * 70 + "\n")

    try:
        # 运行所有示例
        example1_parallel_grid_search()
        example2_parallel_random_search()
        example3_bayesian_optimization()
        example4_mixed_parameter_types()
        example5_convenience_functions()
        example6_performance_comparison()
        example7_real_backtest_optimization()

        logger.success("\n" + "=" * 70)
        logger.success("所有演示完成！")
        logger.success("=" * 70 + "\n")

    except Exception as e:
        logger.error(f"\n演示失败: {e}")
        import traceback
        traceback.print_exc()
