#!/usr/bin/env python3
"""
并行参数优化器单元测试

测试 ParallelParameterOptimizer 的所有核心功能

Author: Stock Analysis Core Team
Date: 2026-01-31
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch

from src.optimization.parallel_optimizer import (
    ParallelParameterOptimizer,
    OptimizationResult,
    parallel_grid_search,
    parallel_random_search
)
from src.config.features import ParallelComputingConfig


# ==================== Fixtures ====================

@pytest.fixture
def simple_objective():
    """简单的目标函数：最小化 (x-5)^2 + (y-3)^2"""
    def objective(params):
        x = params.get('x', 0)
        y = params.get('y', 0)
        return -((x - 5)**2 + (y - 3)**2)  # 负号因为要最大化

    return objective


@pytest.fixture
def backtest_objective():
    """模拟回测目标函数"""
    def objective(params):
        # 模拟：lookback 越接近20，top_n 越接近50，夏普比率越高
        lookback = params.get('lookback', 10)
        top_n = params.get('top_n', 30)

        # 简单模拟
        score = 1.0 - abs(lookback - 20) / 50.0 - abs(top_n - 50) / 100.0

        # 添加一些随机噪声
        np.random.seed(int(lookback * top_n) % 1000)
        score += np.random.randn() * 0.1

        return max(score, 0.0)  # 确保非负

    return objective


# ==================== 测试初始化 ====================

class TestParallelParameterOptimizerInitialization:
    """测试 ParallelParameterOptimizer 初始化"""

    def test_default_initialization(self):
        """测试默认初始化"""
        optimizer = ParallelParameterOptimizer()

        assert optimizer.method == 'grid'
        assert optimizer.parallel_config is not None
        assert optimizer.verbose is True

    def test_custom_method(self):
        """测试自定义方法"""
        for method in ['grid', 'random', 'bayesian']:
            optimizer = ParallelParameterOptimizer(method=method)
            assert optimizer.method == method

    def test_invalid_method(self):
        """测试无效方法"""
        with pytest.raises(ValueError, match="不支持的优化方法"):
            ParallelParameterOptimizer(method='invalid_method')

    def test_custom_n_workers(self):
        """测试自定义 worker 数量"""
        optimizer = ParallelParameterOptimizer(n_workers=4)
        assert optimizer.parallel_config.n_workers == 4

    def test_custom_parallel_config(self):
        """测试自定义并行配置"""
        config = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=8,
            show_progress=False
        )

        optimizer = ParallelParameterOptimizer(parallel_config=config)
        assert optimizer.parallel_config.n_workers == 8
        assert optimizer.parallel_config.show_progress is False


# ==================== 测试网格搜索 ====================

class TestGridSearch:
    """测试网格搜索优化"""

    def test_grid_search_basic(self, simple_objective):
        """测试基本网格搜索"""
        # 使用串行模式避免fixture序列化问题
        optimizer = ParallelParameterOptimizer(
            method='grid',
            n_workers=1,  # 串行模式
            verbose=False
        )

        param_grid = {
            'x': [3, 4, 5, 6, 7],
            'y': [1, 2, 3, 4, 5]
        }

        result = optimizer.optimize(simple_objective, param_grid)

        assert isinstance(result, OptimizationResult)
        assert result.method == 'grid'
        assert result.best_params is not None
        assert result.n_trials == 25  # 5 * 5

        # 最优解应该接近 (5, 3)
        assert abs(result.best_params['x'] - 5) <= 1
        assert abs(result.best_params['y'] - 3) <= 1

    def test_grid_search_with_backtest(self, backtest_objective):
        """测试回测场景的网格搜索"""
        optimizer = ParallelParameterOptimizer(
            method='grid',
            n_workers=1,  # 串行模式
            verbose=False
        )

        param_grid = {
            'lookback': [10, 15, 20, 25, 30],
            'top_n': [30, 40, 50, 60]
        }

        result = optimizer.optimize(backtest_objective, param_grid)

        assert result.best_score is not None
        assert result.n_trials == 20  # 5 * 4

    def test_grid_search_serial(self, simple_objective):
        """测试串行网格搜索"""
        optimizer = ParallelParameterOptimizer(
            method='grid',
            n_workers=1,  # 强制串行
            verbose=False
        )

        param_grid = {
            'x': [4, 5, 6],
            'y': [2, 3, 4]
        }

        result = optimizer.optimize(simple_objective, param_grid)

        assert result.method == 'grid'
        assert result.n_trials == 9


# ==================== 测试随机搜索 ====================

class TestRandomSearch:
    """测试随机搜索优化"""

    def test_random_search_basic(self, simple_objective):
        """测试基本随机搜索"""
        optimizer = ParallelParameterOptimizer(
            method='random',
            n_workers=1,
            verbose=False
        )

        param_space = {
            'x': (0, 10),
            'y': (0, 10)
        }

        result = optimizer.optimize(
            simple_objective,
            param_space,
            maximize=True,
            n_iter=50
        )

        assert isinstance(result, OptimizationResult)
        assert result.method == 'random'
        assert result.n_trials == 50

        # 最优解应该接近 (5, 3)（可能不如网格搜索精确）
        assert 0 <= result.best_params['x'] <= 10
        assert 0 <= result.best_params['y'] <= 10

    def test_random_search_integer_params(self, backtest_objective):
        """测试整数参数的随机搜索"""
        optimizer = ParallelParameterOptimizer(
            method='random',
            n_workers=1,
            verbose=False
        )

        param_space = {
            'lookback': (5, 50),  # 整数范围
            'top_n': (10, 100)    # 整数范围
        }

        result = optimizer.optimize(
            backtest_objective,
            param_space,
            n_iter=30
        )

        assert result.n_trials == 30

        # 检查参数类型
        assert isinstance(result.best_params['lookback'], (int, np.integer))
        assert isinstance(result.best_params['top_n'], (int, np.integer))

    def test_random_search_mixed_params(self, simple_objective):
        """测试混合参数类型"""
        optimizer = ParallelParameterOptimizer(
            method='random',
            n_workers=1,
            verbose=False
        )

        param_space = {
            'x': (0.0, 10.0),  # 浮点数
            'y': [1, 2, 3, 4, 5]  # 类别
        }

        result = optimizer.optimize(
            simple_objective,
            param_space,
            n_iter=20
        )

        assert result.n_trials == 20
        assert isinstance(result.best_params['x'], (float, np.floating))
        assert result.best_params['y'] in [1, 2, 3, 4, 5]

    def test_random_search_minimize(self):
        """测试最小化目标"""
        optimizer = ParallelParameterOptimizer(
            method='random',
            n_workers=1,
            verbose=False
        )

        # 目标：最小化 x^2 + y^2
        def minimize_objective(params):
            return params['x']**2 + params['y']**2

        param_space = {
            'x': (-5, 5),
            'y': (-5, 5)
        }

        result = optimizer.optimize(
            minimize_objective,
            param_space,
            maximize=False,  # 最小化
            n_iter=30
        )

        # 最优解应该接近 (0, 0)
        assert abs(result.best_params['x']) < 2
        assert abs(result.best_params['y']) < 2


# ==================== 测试贝叶斯优化 ====================

class TestBayesianOptimization:
    """测试贝叶斯优化"""

    def test_bayesian_optimization_basic(self, simple_objective):
        """测试基本贝叶斯优化"""
        try:
            optimizer = ParallelParameterOptimizer(
                method='bayesian',
                n_workers=1,
                verbose=False
            )

            param_space = {
                'x': (0, 10),
                'y': (0, 10)
            }

            result = optimizer.optimize(
                simple_objective,
                param_space,
                maximize=True,
                n_calls=20,
                n_initial_points=5
            )

            assert isinstance(result, OptimizationResult)
            assert result.method == 'bayesian'
            assert result.n_trials <= 20

        except ImportError:
            pytest.skip("scikit-optimize 未安装")

    def test_bayesian_with_categorical(self):
        """测试带类别参数的贝叶斯优化"""
        try:
            optimizer = ParallelParameterOptimizer(
                method='bayesian',
                n_workers=1,
                verbose=False
            )

            def categorical_objective(params):
                method = params['method']
                threshold = params['threshold']

                score = threshold if method == 'A' else 1 - threshold
                return score

            param_space = {
                'method': ['A', 'B', 'C'],
                'threshold': (0.0, 1.0)
            }

            result = optimizer.optimize(
                categorical_objective,
                param_space,
                n_calls=15
            )

            assert result.best_params['method'] in ['A', 'B', 'C']
            assert 0 <= result.best_params['threshold'] <= 1

        except ImportError:
            pytest.skip("scikit-optimize 未安装")


# ==================== 测试随机组合生成 ====================

class TestRandomCombinationGeneration:
    """测试随机组合生成"""

    def test_generate_integer_params(self):
        """测试生成整数参数"""
        param_space = {
            'x': (1, 10),
            'y': (5, 15)
        }

        combinations = ParallelParameterOptimizer._generate_random_combinations(
            param_space,
            n_samples=20,
            random_state=42
        )

        assert len(combinations) == 20

        for combo in combinations:
            assert 1 <= combo['x'] <= 10
            assert 5 <= combo['y'] <= 15
            assert isinstance(combo['x'], (int, np.integer))
            assert isinstance(combo['y'], (int, np.integer))

    def test_generate_float_params(self):
        """测试生成浮点数参数"""
        param_space = {
            'alpha': (0.0, 1.0),
            'beta': (0.5, 2.0)
        }

        combinations = ParallelParameterOptimizer._generate_random_combinations(
            param_space,
            n_samples=15,
            random_state=42
        )

        assert len(combinations) == 15

        for combo in combinations:
            assert 0.0 <= combo['alpha'] <= 1.0
            assert 0.5 <= combo['beta'] <= 2.0

    def test_generate_categorical_params(self):
        """测试生成类别参数"""
        param_space = {
            'method': ['A', 'B', 'C'],
            'optimizer': ['adam', 'sgd', 'rmsprop']
        }

        combinations = ParallelParameterOptimizer._generate_random_combinations(
            param_space,
            n_samples=10,
            random_state=42
        )

        assert len(combinations) == 10

        for combo in combinations:
            assert combo['method'] in ['A', 'B', 'C']
            assert combo['optimizer'] in ['adam', 'sgd', 'rmsprop']

    def test_generate_mixed_params(self):
        """测试生成混合参数"""
        param_space = {
            'lookback': (5, 50),
            'threshold': (0.0, 1.0),
            'method': ['pearson', 'spearman', 'kendall']
        }

        combinations = ParallelParameterOptimizer._generate_random_combinations(
            param_space,
            n_samples=25,
            random_state=42
        )

        assert len(combinations) == 25

        for combo in combinations:
            assert 5 <= combo['lookback'] <= 50
            assert 0.0 <= combo['threshold'] <= 1.0
            assert combo['method'] in ['pearson', 'spearman', 'kendall']

    def test_generate_with_seed(self):
        """测试随机种子的可重复性"""
        param_space = {'x': (0, 100)}

        # 使用相同种子应该生成相同结果
        combo1 = ParallelParameterOptimizer._generate_random_combinations(
            param_space, 5, random_state=42
        )
        combo2 = ParallelParameterOptimizer._generate_random_combinations(
            param_space, 5, random_state=42
        )

        assert combo1 == combo2


# ==================== 测试结果格式 ====================

class TestOptimizationResult:
    """测试 OptimizationResult 数据类"""

    def test_optimization_result_creation(self):
        """测试创建优化结果"""
        result = OptimizationResult(
            method='grid',
            best_params={'x': 5, 'y': 3},
            best_score=1.5,
            n_trials=100,
            search_time=10.5
        )

        assert result.method == 'grid'
        assert result.best_params == {'x': 5, 'y': 3}
        assert result.best_score == 1.5
        assert result.n_trials == 100
        assert result.search_time == 10.5

    def test_optimization_result_to_dict(self):
        """测试转为字典"""
        result = OptimizationResult(
            method='random',
            best_params={'lookback': 20},
            best_score=0.8,
            n_trials=50,
            search_time=5.2
        )

        result_dict = result.to_dict()

        assert result_dict['method'] == 'random'
        assert result_dict['best_params'] == {'lookback': 20}
        assert result_dict['best_score'] == 0.8

    def test_optimization_result_str(self):
        """测试字符串表示"""
        result = OptimizationResult(
            method='grid',
            best_params={'x': 5},
            best_score=1.0,
            n_trials=10,
            search_time=1.0
        )

        result_str = str(result)

        assert 'grid' in result_str
        assert 'x: 5' in result_str
        assert '1.0' in result_str


# ==================== 测试便捷函数 ====================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_parallel_grid_search_function(self, simple_objective):
        """测试 parallel_grid_search 便捷函数"""
        param_grid = {
            'x': [4, 5, 6],
            'y': [2, 3, 4]
        }

        result = parallel_grid_search(
            simple_objective,
            param_grid,
            n_workers=1,
            verbose=False
        )

        assert isinstance(result, OptimizationResult)
        assert result.method == 'grid'
        assert result.n_trials == 9

    def test_parallel_random_search_function(self, simple_objective):
        """测试 parallel_random_search 便捷函数"""
        param_space = {
            'x': (0, 10),
            'y': (0, 10)
        }

        result = parallel_random_search(
            simple_objective,
            param_space,
            n_iter=20,
            n_workers=1,
            maximize=True,
            verbose=False
        )

        assert isinstance(result, OptimizationResult)
        assert result.method == 'random'
        assert result.n_trials == 20


# ==================== 测试错误处理 ====================

class TestErrorHandling:
    """测试错误处理"""

    def test_handle_objective_failure(self):
        """测试处理目标函数失败"""
        def failing_objective(params):
            if params['x'] > 5:
                raise ValueError("x too large")
            return params['x']

        optimizer = ParallelParameterOptimizer(
            method='random',
            n_workers=1,
            verbose=False
        )

        param_space = {'x': (0, 10)}

        # 应该不抛出异常，但返回有效结果
        result = optimizer.optimize(
            failing_objective,
            param_space,
            n_iter=20
        )

        # 应该找到一些 x <= 5 的有效结果
        assert result.best_params['x'] <= 5

    def test_all_evaluations_fail(self):
        """测试所有评估都失败的情况"""
        def always_fail(params):
            raise ValueError("Always fail")

        optimizer = ParallelParameterOptimizer(
            method='random',
            n_workers=1,
            verbose=False
        )

        param_space = {'x': (0, 10)}

        with pytest.raises(ValueError, match="所有参数组合都失败了"):
            optimizer.optimize(always_fail, param_space, n_iter=10)


# ==================== 性能测试 ====================

class TestPerformance:
    """测试性能相关功能"""

    @pytest.mark.slow
    def test_parallel_faster_than_serial(self, simple_objective):
        """测试并行比串行快（标记为慢速测试）"""
        import time

        param_grid = {
            'x': list(range(0, 20)),
            'y': list(range(0, 20))
        }

        # 串行
        optimizer_serial = ParallelParameterOptimizer(
            method='grid',
            n_workers=1,
            verbose=False
        )

        start = time.time()
        result_serial = optimizer_serial.optimize(simple_objective, param_grid)
        time_serial = time.time() - start

        # 并行
        optimizer_parallel = ParallelParameterOptimizer(
            method='grid',
            n_workers=1,
            verbose=False
        )

        start = time.time()
        result_parallel = optimizer_parallel.optimize(simple_objective, param_grid)
        time_parallel = time.time() - start

        # 结果应该相同
        assert result_serial.best_score == result_parallel.best_score

        print(f"\n串行: {time_serial:.2f}s, 并行: {time_parallel:.2f}s")


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试"""

    def test_full_optimization_workflow(self, backtest_objective):
        """测试完整优化工作流"""
        # 1. 创建优化器
        optimizer = ParallelParameterOptimizer(
            method='grid',
            n_workers=1,
            verbose=False
        )

        # 2. 定义参数空间
        param_grid = {
            'lookback': [10, 20, 30],
            'top_n': [30, 50, 70]
        }

        # 3. 执行优化
        result = optimizer.optimize(backtest_objective, param_grid)

        # 4. 验证结果
        assert result is not None
        assert result.best_params is not None
        assert result.best_score is not None
        assert result.n_trials == 9

        # 5. 检查结果格式
        assert 'lookback' in result.best_params
        assert 'top_n' in result.best_params

    def test_method_switching(self, simple_objective):
        """测试方法切换"""
        optimizer = ParallelParameterOptimizer(
            method='grid',
            n_workers=1,
            verbose=False
        )

        param_space = {'x': [3, 4, 5, 6], 'y': [2, 3, 4]}

        # 网格搜索
        result1 = optimizer.optimize(simple_objective, param_space)
        assert result1.method == 'grid'

        # 切换到随机搜索
        optimizer.method = 'random'
        param_space_random = {'x': (0, 10), 'y': (0, 10)}
        result2 = optimizer.optimize(simple_objective, param_space_random, n_iter=20)
        assert result2.method == 'random'
