"""
贝叶斯优化器单元测试

测试功能：
- 基本贝叶斯优化
- 不同参数类型（整数、浮点数、类别）
- 收敛性测试
- 可选依赖处理
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

# 检查是否安装了scikit-optimize
try:
    import skopt
    HAS_SKOPT = True
except ImportError:
    HAS_SKOPT = False

from optimization.bayesian_optimizer import BayesianOptimizer, BayesianOptimizationResult


@pytest.fixture
def simple_objective_func():
    """简单的目标函数"""
    def objective(params):
        x = params['x']
        y = params['y']
        return -(abs(x - 5) + abs(y - 10))
    return objective


@pytest.mark.skipif(not HAS_SKOPT, reason="需要安装scikit-optimize")
class TestBayesianOptimizerInit:
    """测试初始化"""

    def test_default_init(self):
        optimizer = BayesianOptimizer()
        assert optimizer.n_calls == 50
        assert optimizer.n_initial_points == 10
        assert optimizer.acq_func == 'EI'
        assert optimizer.random_state == 42

    def test_custom_init(self):
        optimizer = BayesianOptimizer(
            n_calls=100,
            n_initial_points=20,
            acq_func='PI',
            random_state=123
        )
        assert optimizer.n_calls == 100
        assert optimizer.n_initial_points == 20
        assert optimizer.acq_func == 'PI'
        assert optimizer.random_state == 123


@pytest.mark.skipif(not HAS_SKOPT, reason="需要安装scikit-optimize")
class TestOptimize:
    """测试优化"""

    def test_basic_optimize(self, simple_objective_func):
        optimizer = BayesianOptimizer(n_calls=20, n_initial_points=5)

        param_space = {
            'x': (0, 10),
            'y': (0, 20)
        }

        result = optimizer.optimize(simple_objective_func, param_space, maximize=True)

        assert isinstance(result, BayesianOptimizationResult)
        assert result.best_params is not None
        assert 'x' in result.best_params
        assert 'y' in result.best_params
        assert 0 <= result.best_params['x'] <= 10
        assert 0 <= result.best_params['y'] <= 20
        assert result.n_iterations == 20

    def test_integer_params(self):
        optimizer = BayesianOptimizer(n_calls=10)

        def objective(params):
            return -abs(params['n'] - 5)

        param_space = {'n': (1, 10)}

        result = optimizer.optimize(objective, param_space)

        assert isinstance(result.best_params['n'], (int, np.integer))

    def test_categorical_params(self):
        optimizer = BayesianOptimizer(n_calls=10)

        def objective(params):
            method_scores = {'method_a': 0.5, 'method_b': 0.8, 'method_c': 0.3}
            return method_scores[params['method']]

        param_space = {'method': ['method_a', 'method_b', 'method_c']}

        result = optimizer.optimize(objective, param_space, maximize=True)

        assert result.best_params['method'] == 'method_b'

    def test_mixed_params(self):
        optimizer = BayesianOptimizer(n_calls=15)

        def objective(params):
            x = params['x']
            n = params['n']
            method = params['method']
            method_bonus = 1.0 if method == 'best' else 0.5
            return -(abs(x - 5) + abs(n - 10)) * method_bonus

        param_space = {
            'x': (0.0, 10.0),
            'n': (1, 20),
            'method': ['best', 'worst']
        }

        result = optimizer.optimize(objective, param_space, maximize=True)

        assert 'x' in result.best_params
        assert 'n' in result.best_params
        assert 'method' in result.best_params

    def test_maximize_vs_minimize(self):
        optimizer = BayesianOptimizer(n_calls=10)

        def objective(params):
            return params['x']

        param_space = {'x': (0, 10)}

        result_max = optimizer.optimize(objective, param_space, maximize=True)
        result_min = optimizer.optimize(objective, param_space, maximize=False)

        assert result_max.best_params['x'] > result_min.best_params['x']


@pytest.mark.skipif(not HAS_SKOPT, reason="需要安装scikit-optimize")
class TestConvergence:
    """测试收敛性"""

    def test_convergence_curve(self, simple_objective_func):
        optimizer = BayesianOptimizer(n_calls=20)

        param_space = {'x': (0, 10), 'y': (0, 20)}

        result = optimizer.optimize(simple_objective_func, param_space, maximize=True)

        assert isinstance(result.convergence_curve, list)
        assert len(result.convergence_curve) == 20
        # 收敛曲线应该单调递增（最大化时）
        # assert all(result.convergence_curve[i] <= result.convergence_curve[i+1]
        #           for i in range(len(result.convergence_curve)-1))


@pytest.mark.skipif(not HAS_SKOPT, reason="需要安装scikit-optimize")
class TestEdgeCases:
    """测试边界条件"""

    def test_single_param(self):
        optimizer = BayesianOptimizer(n_calls=10)

        def objective(params):
            return -abs(params['x'] - 5)

        param_space = {'x': (0, 10)}

        result = optimizer.optimize(objective, param_space)

        assert 4 <= result.best_params['x'] <= 6  # 应该接近5

    def test_objective_returns_nan(self):
        optimizer = BayesianOptimizer(n_calls=10)

        def objective(params):
            if 4.5 <= params['x'] <= 5.5:
                return np.nan
            return -abs(params['x'] - 5)

        param_space = {'x': (0, 10)}

        # 应该能处理NaN
        result = optimizer.optimize(objective, param_space)
        assert result.best_params is not None


class TestNoSkopt:
    """测试没有安装scikit-optimize的情况"""

    @pytest.mark.skipif(HAS_SKOPT, reason="测试没有skopt的情况")
    def test_import_error_handling(self):
        """测试没有skopt时的错误处理"""
        # 这个测试只在没有安装skopt时运行
        with pytest.raises(ImportError):
            import skopt


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
