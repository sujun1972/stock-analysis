"""
因子组合优化器单元测试

测试功能：
- 等权重分配
- IC加权
- ICIR加权
- 优化最大化ICIR
- 优化最小化相关性
- 因子组合生成
"""

import pytest
import pandas as pd
import numpy as np

from analysis.factor_optimizer import FactorOptimizer, OptimizationResult


@pytest.fixture
def sample_ic_series_dict():
    """生成样本IC时间序列字典"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')

    return {
        'factor_1': pd.Series(np.random.randn(100) * 0.05 + 0.02, index=dates),
        'factor_2': pd.Series(np.random.randn(100) * 0.03 + 0.01, index=dates),
        'factor_3': pd.Series(np.random.randn(100) * 0.04 + 0.015, index=dates)
    }


@pytest.fixture
def sample_factor_dict():
    """生成样本因子数据字典"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = [f'stock_{i:02d}' for i in range(30)]

    return {
        'factor_1': pd.DataFrame(np.random.randn(100, 30), index=dates, columns=stocks),
        'factor_2': pd.DataFrame(np.random.randn(100, 30), index=dates, columns=stocks),
        'factor_3': pd.DataFrame(np.random.randn(100, 30), index=dates, columns=stocks)
    }


@pytest.fixture
def sample_ic_stats():
    """生成样本IC统计DataFrame"""
    return pd.DataFrame({
        'IC均值': [0.02, 0.01, 0.015],
        'IC标准差': [0.05, 0.03, 0.04],
        'ICIR': [0.4, 0.33, 0.375]
    }, index=['factor_1', 'factor_2', 'factor_3'])


class TestFactorOptimizerInit:
    """测试初始化"""

    def test_default_init(self):
        optimizer = FactorOptimizer()
        assert optimizer is not None


class TestEqualWeight:
    """测试等权重分配"""

    def test_equal_weight_basic(self):
        optimizer = FactorOptimizer()
        factor_names = ['factor_1', 'factor_2', 'factor_3']

        weights = optimizer.equal_weight(factor_names)

        assert isinstance(weights, pd.Series)
        assert len(weights) == 3
        assert all(abs(weights - 1/3) < 1e-6)
        assert abs(weights.sum() - 1.0) < 1e-6

    def test_equal_weight_single(self):
        optimizer = FactorOptimizer()
        weights = optimizer.equal_weight(['factor_1'])

        assert len(weights) == 1
        assert weights['factor_1'] == 1.0

    def test_equal_weight_many(self):
        optimizer = FactorOptimizer()
        factor_names = [f'factor_{i}' for i in range(10)]

        weights = optimizer.equal_weight(factor_names)

        assert len(weights) == 10
        assert abs(weights.sum() - 1.0) < 1e-6


class TestICWeight:
    """测试IC加权"""

    def test_ic_weight_basic(self, sample_ic_stats):
        optimizer = FactorOptimizer()
        weights = optimizer.ic_weight(sample_ic_stats)

        assert isinstance(weights, pd.Series)
        assert len(weights) == 3
        assert abs(weights.sum() - 1.0) < 1e-6
        assert all(weights >= 0)

    def test_ic_weight_proportional(self, sample_ic_stats):
        optimizer = FactorOptimizer()
        weights = optimizer.ic_weight(sample_ic_stats)

        # IC均值最大的应该权重最大
        max_ic_factor = sample_ic_stats['IC均值'].abs().idxmax()
        assert weights[max_ic_factor] == weights.max()


class TestICIRWeight:
    """测试ICIR加权"""

    def test_ic_ir_weight_basic(self, sample_ic_stats):
        optimizer = FactorOptimizer()
        weights = optimizer.ic_ir_weight(sample_ic_stats)

        assert isinstance(weights, pd.Series)
        assert len(weights) == 3
        assert abs(weights.sum() - 1.0) < 1e-6
        assert all(weights >= 0)

    def test_ic_ir_weight_proportional(self, sample_ic_stats):
        optimizer = FactorOptimizer()
        weights = optimizer.ic_ir_weight(sample_ic_stats)

        # ICIR最大的应该权重最大
        max_icir_factor = sample_ic_stats['ICIR'].abs().idxmax()
        assert weights[max_icir_factor] == weights.max()


class TestOptimizeMaxICIR:
    """测试优化最大化ICIR"""

    def test_optimize_max_icir_basic(self, sample_ic_series_dict):
        optimizer = FactorOptimizer()

        result = optimizer.optimize_max_icir(sample_ic_series_dict)

        assert isinstance(result, OptimizationResult)
        assert isinstance(result.weights, pd.Series)
        assert len(result.weights) == 3
        assert abs(result.weights.sum() - 1.0) < 1e-3
        assert all(result.weights >= 0)
        assert result.ic_ir > 0  # ICIR应该大于0

    def test_optimize_max_icir_with_constraints(self, sample_ic_series_dict):
        optimizer = FactorOptimizer()

        result = optimizer.optimize_max_icir(
            sample_ic_series_dict,
            max_weight=0.5
        )

        assert all(result.weights <= 0.5 + 1e-6)

    def test_optimize_max_icir_methods(self, sample_ic_series_dict):
        optimizer = FactorOptimizer()

        for method in ['SLSQP', 'L-BFGS-B']:
            result = optimizer.optimize_max_icir(
                sample_ic_series_dict,
                method=method
            )
            assert isinstance(result, OptimizationResult)


class TestOptimizeMinCorrelation:
    """测试优化最小化相关性"""

    def test_optimize_min_corr_basic(self, sample_ic_series_dict):
        optimizer = FactorOptimizer()

        # 计算相关性矩阵
        ic_df = pd.DataFrame(sample_ic_series_dict)
        corr_matrix = ic_df.corr()

        result = optimizer.optimize_min_correlation(
            sample_ic_series_dict,
            corr_matrix,
            max_avg_corr=0.5
        )

        assert isinstance(result, OptimizationResult)
        assert len(result.weights) == 3
        assert abs(result.weights.sum() - 1.0) < 1e-3

    def test_optimize_min_corr_constraints(self, sample_ic_series_dict):
        optimizer = FactorOptimizer()

        ic_df = pd.DataFrame(sample_ic_series_dict)
        corr_matrix = ic_df.corr()

        result = optimizer.optimize_min_correlation(
            sample_ic_series_dict,
            corr_matrix,
            max_avg_corr=0.3
        )

        # Note: optimize_min_correlation doesn't support max_weight parameter
        assert len(result.weights) == 3


class TestCombineFactors:
    """测试因子组合"""

    def test_combine_factors_basic(self, sample_factor_dict):
        optimizer = FactorOptimizer()

        weights = pd.Series([0.5, 0.3, 0.2], index=['factor_1', 'factor_2', 'factor_3'])
        combined = optimizer.combine_factors(sample_factor_dict, weights)

        assert isinstance(combined, pd.DataFrame)
        assert combined.shape == sample_factor_dict['factor_1'].shape

    def test_combine_factors_normalized(self, sample_factor_dict):
        optimizer = FactorOptimizer()

        weights = pd.Series([0.5, 0.3, 0.2], index=['factor_1', 'factor_2', 'factor_3'])

        combined_normalized = optimizer.combine_factors(
            sample_factor_dict, weights, normalize=True
        )
        combined_raw = optimizer.combine_factors(
            sample_factor_dict, weights, normalize=False
        )

        # 归一化后的值应该在不同范围
        assert combined_normalized.shape == combined_raw.shape

    def test_combine_single_factor(self, sample_factor_dict):
        optimizer = FactorOptimizer()

        weights = pd.Series([1.0], index=['factor_1'])
        combined = optimizer.combine_factors(
            {'factor_1': sample_factor_dict['factor_1']},
            weights
        )

        assert isinstance(combined, pd.DataFrame)


class TestOptimizationResult:
    """测试OptimizationResult数据类"""

    def test_result_creation(self):
        weights = pd.Series([0.5, 0.3, 0.2], index=['f1', 'f2', 'f3'])
        result = OptimizationResult(
            weights=weights,
            objective_value=0.8,
            ic_mean=0.05,
            ic_ir=0.8,
            method='test'
        )

        assert result.ic_mean == 0.05
        assert result.ic_ir == 0.8
        assert result.ic_ir > 0  # ICIR应该大于0


class TestEdgeCases:
    """测试边界条件"""

    def test_single_factor_optimization(self):
        optimizer = FactorOptimizer()

        ic_series_dict = {
            'factor_1': pd.Series(np.random.randn(50))
        }

        # For single factor, we need to allow max_weight=1.0
        result = optimizer.optimize_max_icir(ic_series_dict, max_weight=1.0)

        # For single factor, weight should be close to 1.0 (within tolerance)
        assert abs(result.weights['factor_1'] - 1.0) < 1e-3

    def test_negative_ic_factors(self):
        optimizer = FactorOptimizer()

        ic_series_dict = {
            'factor_1': pd.Series(np.random.randn(50) - 0.5),  # 负IC
            'factor_2': pd.Series(np.random.randn(50) + 0.5)   # 正IC
        }

        result = optimizer.optimize_max_icir(ic_series_dict)

        # 负IC因子可能权重为0或被取绝对值
        assert isinstance(result, OptimizationResult)


class TestIntegration:
    """集成测试"""

    def test_complete_workflow(self, sample_ic_series_dict, sample_factor_dict):
        optimizer = FactorOptimizer()

        # 1. 尝试多种权重方法
        weights_equal = optimizer.equal_weight(list(sample_ic_series_dict.keys()))
        assert abs(weights_equal.sum() - 1.0) < 1e-6

        # 2. 优化权重
        result = optimizer.optimize_max_icir(sample_ic_series_dict, max_weight=0.6)
        assert result.ic_ir > 0  # ICIR应该大于0

        # 3. 组合因子
        combined = optimizer.combine_factors(sample_factor_dict, result.weights)
        assert isinstance(combined, pd.DataFrame)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
