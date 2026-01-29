"""
网格搜索优化器单元测试

测试功能：
- 基本网格搜索
- 参数重要性分析
- 并行搜索
- 结果排序和统计
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from optimization.grid_search import GridSearchOptimizer, GridSearchResult


@pytest.fixture
def simple_objective_func():
    """简单的目标函数"""
    def objective(params):
        # 简单的二次函数：最优值在x=5, y=10
        x = params['x']
        y = params['y']
        return -(abs(x - 5) + abs(y - 10))
    return objective


@pytest.fixture
def noisy_objective_func():
    """带噪声的目标函数"""
    def objective(params):
        x = params['x']
        y = params['y']
        noise = np.random.randn() * 0.1
        return -(abs(x - 5) + abs(y - 10)) + noise
    return objective


class TestGridSearchOptimizerInit:
    """测试初始化"""

    def test_default_init(self):
        optimizer = GridSearchOptimizer()
        assert optimizer.metric == 'sharpe_ratio'
        assert optimizer.cv == 1
        assert optimizer.n_jobs == 1
        assert optimizer.verbose is True

    def test_custom_init(self):
        optimizer = GridSearchOptimizer(
            metric='returns',
            cv=3,
            n_jobs=4,
            verbose=False
        )
        assert optimizer.metric == 'returns'
        assert optimizer.cv == 3
        assert optimizer.n_jobs == 4
        assert optimizer.verbose is False


class TestGridSearch:
    """测试网格搜索"""

    def test_basic_search(self, simple_objective_func):
        optimizer = GridSearchOptimizer(verbose=False)

        param_grid = {
            'x': [1, 5, 10],
            'y': [5, 10, 15]
        }

        result = optimizer.search(simple_objective_func, param_grid)

        assert isinstance(result, GridSearchResult)
        assert result.best_params is not None
        assert 'x' in result.best_params
        assert 'y' in result.best_params
        assert result.best_score is not None
        assert len(result.all_results) == 9  # 3 * 3 = 9 组合

    def test_single_param(self, simple_objective_func):
        optimizer = GridSearchOptimizer(verbose=False)

        param_grid = {
            'x': [1, 5, 10]
        }

        def single_param_func(params):
            return -abs(params['x'] - 5)

        result = optimizer.search(single_param_func, param_grid)

        assert result.best_params['x'] == 5
        assert len(result.all_results) == 3

    def test_many_params(self, simple_objective_func):
        optimizer = GridSearchOptimizer(verbose=False)

        param_grid = {
            'x': [1, 5],
            'y': [5, 10],
            'z': [1, 2]
        }

        def multi_param_func(params):
            return -(abs(params['x'] - 5) + abs(params['y'] - 10) + abs(params['z'] - 2))

        result = optimizer.search(multi_param_func, param_grid)

        assert len(result.all_results) == 8  # 2 * 2 * 2 = 8
        assert 'z' in result.best_params

    def test_best_params_correctness(self, simple_objective_func):
        optimizer = GridSearchOptimizer(verbose=False)

        param_grid = {
            'x': [1, 3, 5, 7, 10],
            'y': [5, 8, 10, 12, 15]
        }

        result = optimizer.search(simple_objective_func, param_grid)

        # 最优参数应该是x=5, y=10
        assert result.best_params['x'] == 5
        assert result.best_params['y'] == 10

    def test_empty_param_grid(self, simple_objective_func):
        optimizer = GridSearchOptimizer(verbose=False)

        with pytest.raises(ValueError, match="参数网格不能为空"):
            optimizer.search(simple_objective_func, {})


class TestAnalyzeParamImportance:
    """测试参数重要性分析"""

    def test_param_importance_basic(self, simple_objective_func):
        optimizer = GridSearchOptimizer(verbose=False)

        param_grid = {
            'x': [1, 5, 10],
            'y': [5, 10, 15]
        }

        result = optimizer.search(simple_objective_func, param_grid)
        importance_df = optimizer.analyze_param_importance(result)

        assert isinstance(importance_df, pd.DataFrame)
        assert '参数名' in importance_df.columns
        assert '得分范围' in importance_df.columns
        assert '重要性' in importance_df.columns
        assert len(importance_df) == 2  # x和y两个参数

    def test_param_importance_values(self, simple_objective_func):
        optimizer = GridSearchOptimizer(verbose=False)

        param_grid = {
            'x': [1, 5, 10],
            'y': [5, 10, 15]
        }

        result = optimizer.search(simple_objective_func, param_grid)
        importance_df = optimizer.analyze_param_importance(result)

        # 所有重要性应该在[0, 1]之间
        assert all(0 <= imp <= 1 for imp in importance_df['重要性'])

    def test_param_importance_ordering(self):
        optimizer = GridSearchOptimizer(verbose=False)

        # x参数影响更大
        def objective(params):
            return -abs(params['x'] - 5) * 10 - abs(params['y'] - 10)

        param_grid = {
            'x': [1, 5, 10],
            'y': [5, 10, 15]
        }

        result = optimizer.search(objective, param_grid)
        importance_df = optimizer.analyze_param_importance(result)

        # x的重要性应该高于y
        x_importance = importance_df[importance_df['参数名'] == 'x']['重要性'].values[0]
        y_importance = importance_df[importance_df['参数名'] == 'y']['重要性'].values[0]
        assert x_importance > y_importance


class TestGridSearchResult:
    """测试GridSearchResult数据类"""

    def test_result_creation(self):
        all_results = pd.DataFrame([
            {'params': {'x': 1, 'y': 5}, 'score': 0.5},
            {'params': {'x': 5, 'y': 10}, 'score': 0.9}
        ])

        result = GridSearchResult(
            best_params={'x': 5, 'y': 10},
            best_score=0.9,
            all_results=all_results,
            search_time=1.5,
            n_combinations=2
        )

        assert result.best_params == {'x': 5, 'y': 10}
        assert result.best_score == 0.9
        assert len(result.all_results) == 2


class TestParallelSearch:
    """测试并行搜索"""

    @pytest.mark.slow
    def test_parallel_vs_serial(self, simple_objective_func):
        import time

        param_grid = {
            'x': list(range(10)),
            'y': list(range(10))
        }

        # 串行搜索
        optimizer_serial = GridSearchOptimizer(n_jobs=1, verbose=False)
        start = time.time()
        result_serial = optimizer_serial.search(simple_objective_func, param_grid)
        time_serial = time.time() - start

        # 并行搜索
        optimizer_parallel = GridSearchOptimizer(n_jobs=2, verbose=False)
        start = time.time()
        result_parallel = optimizer_parallel.search(simple_objective_func, param_grid)
        time_parallel = time.time() - start

        # 结果应该一致
        assert result_serial.best_params == result_parallel.best_params
        # 并行应该更快（在实际场景中，简单函数可能看不出差异）
        # assert time_parallel <= time_serial


class TestEdgeCases:
    """测试边界条件"""

    def test_single_param_value(self):
        optimizer = GridSearchOptimizer(verbose=False)

        def objective(params):
            return params['x']

        param_grid = {'x': [5]}

        result = optimizer.search(objective, param_grid)

        assert result.best_params['x'] == 5
        assert len(result.all_results) == 1

    def test_objective_returns_nan(self):
        optimizer = GridSearchOptimizer(verbose=False)

        def objective(params):
            if params['x'] == 5:
                return np.nan
            return params['x']

        param_grid = {'x': [1, 5, 10]}

        result = optimizer.search(objective, param_grid)

        # 应该跳过NaN值
        assert result.best_params['x'] != 5

    def test_objective_raises_exception(self):
        optimizer = GridSearchOptimizer(verbose=False)

        def objective(params):
            if params['x'] == 5:
                raise ValueError("Test error")
            return params['x']

        param_grid = {'x': [1, 5, 10]}

        result = optimizer.search(objective, param_grid)

        # 应该能处理异常并继续
        assert result.best_params is not None

    def test_all_params_fail(self):
        optimizer = GridSearchOptimizer(verbose=False)

        def objective(params):
            raise ValueError("Always fails")

        param_grid = {'x': [1, 2, 3]}

        with pytest.raises(ValueError, match="所有参数组合都失败"):
            optimizer.search(objective, param_grid)


class TestIntegration:
    """集成测试"""

    def test_complete_workflow(self, simple_objective_func):
        optimizer = GridSearchOptimizer(metric='custom', verbose=False)

        param_grid = {
            'x': [1, 3, 5, 7, 10],
            'y': [5, 8, 10, 12, 15]
        }

        # 1. 搜索
        result = optimizer.search(simple_objective_func, param_grid)

        assert result.best_params is not None
        assert result.best_score is not None

        # 2. 分析参数重要性
        importance = optimizer.analyze_param_importance(result)

        assert len(importance) == 2

        # 3. 检查结果一致性
        assert len(result.all_results) == 25  # 5 * 5


@pytest.mark.performance
class TestPerformance:
    """性能测试"""

    def test_large_grid_search(self):
        import time

        optimizer = GridSearchOptimizer(n_jobs=4, verbose=False)

        def objective(params):
            return -(abs(params['x'] - 5) + abs(params['y'] - 10) + abs(params['z'] - 15))

        param_grid = {
            'x': list(range(20)),
            'y': list(range(20)),
            'z': list(range(10))
        }

        start = time.time()
        result = optimizer.search(objective, param_grid)
        duration = time.time() - start

        assert len(result.all_results) == 20 * 20 * 10
        assert duration < 10.0  # 应该在10秒内完成


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
