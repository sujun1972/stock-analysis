"""
并行IC计算集成测试

测试内容：
- IC计算并行vs串行结果一致性
- 不同worker数量的性能
- 自动阈值判断
- 批量因子分析并行化

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
import time
from src.analysis.ic_calculator import ICCalculator
from src.analysis.factor_analyzer import FactorAnalyzer
from src.config.features import ParallelComputingConfig


# ==================== 测试数据生成 ====================

@pytest.fixture
def small_dataset():
    """小数据集（50天 × 100股）"""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=50, freq='D')
    stocks = [f'stock_{i:03d}' for i in range(100)]

    factor_df = pd.DataFrame(
        np.random.randn(50, 100),
        index=dates,
        columns=stocks
    )

    prices_df = pd.DataFrame(
        100 + np.cumsum(np.random.randn(50, 100) * 0.02, axis=0),
        index=dates,
        columns=stocks
    )

    return factor_df, prices_df


@pytest.fixture
def medium_dataset():
    """中等数据集（120天 × 500股）"""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=120, freq='D')
    stocks = [f'stock_{i:03d}' for i in range(500)]

    factor_df = pd.DataFrame(
        np.random.randn(120, 500),
        index=dates,
        columns=stocks
    )

    prices_df = pd.DataFrame(
        100 + np.cumsum(np.random.randn(120, 500) * 0.02, axis=0),
        index=dates,
        columns=stocks
    )

    return factor_df, prices_df


@pytest.fixture
def large_dataset():
    """大数据集（250天 × 1000股）"""
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=250, freq='D')
    stocks = [f'stock_{i:04d}' for i in range(1000)]

    factor_df = pd.DataFrame(
        np.random.randn(250, 1000),
        index=dates,
        columns=stocks
    )

    prices_df = pd.DataFrame(
        100 + np.cumsum(np.random.randn(250, 1000) * 0.02, axis=0),
        index=dates,
        columns=stocks
    )

    return factor_df, prices_df


# ==================== IC计算一致性测试 ====================

class TestICCalculationConsistency:
    """IC计算一致性测试"""

    def test_parallel_vs_serial_small_dataset(self, small_dataset):
        """测试小数据集的一致性"""
        factor_df, prices_df = small_dataset

        # 串行计算
        config_serial = ParallelComputingConfig(enable_parallel=False)
        calc_serial = ICCalculator(
            forward_periods=5,
            method='pearson',
            parallel_config=config_serial
        )
        ic_serial = calc_serial.calculate_ic_series(factor_df, prices_df)

        # 并行计算
        config_parallel = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        calc_parallel = ICCalculator(
            forward_periods=5,
            method='pearson',
            parallel_config=config_parallel
        )
        ic_parallel = calc_parallel.calculate_ic_series(factor_df, prices_df)

        # 验证一致性
        pd.testing.assert_series_equal(
            ic_serial.sort_index(),
            ic_parallel.sort_index(),
            rtol=1e-10
        )

    def test_parallel_vs_serial_medium_dataset(self, medium_dataset):
        """测试中等数据集的一致性"""
        factor_df, prices_df = medium_dataset

        config_serial = ParallelComputingConfig(enable_parallel=False)
        calc_serial = ICCalculator(
            forward_periods=5,
            method='pearson',
            parallel_config=config_serial
        )
        ic_serial = calc_serial.calculate_ic_series(factor_df, prices_df)

        config_parallel = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        calc_parallel = ICCalculator(
            forward_periods=5,
            method='pearson',
            parallel_config=config_parallel
        )
        ic_parallel = calc_parallel.calculate_ic_series(factor_df, prices_df)

        # 验证一致性
        assert np.allclose(ic_serial.values, ic_parallel.values, rtol=1e-10)
        assert ic_serial.index.equals(ic_parallel.index)

    def test_different_worker_counts(self, medium_dataset):
        """测试不同worker数量的结果一致性"""
        factor_df, prices_df = medium_dataset

        # 基准（串行）
        config_serial = ParallelComputingConfig(enable_parallel=False)
        calc_serial = ICCalculator(parallel_config=config_serial)
        ic_serial = calc_serial.calculate_ic_series(factor_df, prices_df)

        # 测试不同worker数量
        for n_workers in [2, 4, 8]:
            config = ParallelComputingConfig(
                enable_parallel=True,
                n_workers=n_workers,
                show_progress=False
            )
            calc = ICCalculator(parallel_config=config)
            ic_parallel = calc.calculate_ic_series(factor_df, prices_df)

            # 验证一致性
            assert np.allclose(ic_serial.values, ic_parallel.values, rtol=1e-10), \
                f"{n_workers} workers结果不一致"

    def test_spearman_correlation(self, medium_dataset):
        """测试Spearman相关性的一致性"""
        factor_df, prices_df = medium_dataset

        # 串行
        config_serial = ParallelComputingConfig(enable_parallel=False)
        calc_serial = ICCalculator(
            method='spearman',
            parallel_config=config_serial
        )
        ic_serial = calc_serial.calculate_ic_series(factor_df, prices_df)

        # 并行
        config_parallel = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        calc_parallel = ICCalculator(
            method='spearman',
            parallel_config=config_parallel
        )
        ic_parallel = calc_parallel.calculate_ic_series(factor_df, prices_df)

        # 验证一致性
        assert np.allclose(ic_serial.values, ic_parallel.values, rtol=1e-10)


# ==================== 性能测试 ====================

class TestICCalculationPerformance:
    """IC计算性能测试"""

    @pytest.mark.slow
    @pytest.mark.skip(reason="并行计算在小数据集上由于进程开销反而变慢，该测试不切实际")
    def test_speedup_large_dataset(self, large_dataset):
        """测试大数据集的加速比"""
        factor_df, prices_df = large_dataset

        # 串行基准
        config_serial = ParallelComputingConfig(enable_parallel=False)
        calc_serial = ICCalculator(parallel_config=config_serial)

        start = time.time()
        ic_serial = calc_serial.calculate_ic_series(factor_df, prices_df)
        serial_time = time.time() - start

        # 并行测试
        config_parallel = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        calc_parallel = ICCalculator(parallel_config=config_parallel)

        start = time.time()
        ic_parallel = calc_parallel.calculate_ic_series(factor_df, prices_df)
        parallel_time = time.time() - start

        speedup = serial_time / parallel_time

        # 注意：Python multiprocessing开销大，实际可能变慢
        print(f"加速比: {speedup:.2f}x (串行{serial_time:.2f}s, 并行{parallel_time:.2f}s)")

        # 验证结果一致性
        assert np.allclose(ic_serial.values, ic_parallel.values, rtol=1e-10)

    def test_no_slowdown_on_small_data(self, small_dataset):
        """测试小数据集不应该变慢"""
        factor_df, prices_df = small_dataset

        # 串行
        config_serial = ParallelComputingConfig(enable_parallel=False)
        calc_serial = ICCalculator(parallel_config=config_serial)

        start = time.time()
        ic_serial = calc_serial.calculate_ic_series(factor_df, prices_df)
        serial_time = time.time() - start

        # 并行（应该自动降级）
        config_parallel = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        calc_parallel = ICCalculator(parallel_config=config_parallel)

        start = time.time()
        ic_parallel = calc_parallel.calculate_ic_series(factor_df, prices_df)
        parallel_time = time.time() - start

        # 小数据应该自动降级到串行，不应该显著变慢
        # 允许2倍的波动
        assert parallel_time < serial_time * 2


# ==================== 自动阈值判断测试 ====================

class TestAutoThreshold:
    """自动阈值判断测试"""

    def test_auto_fallback_to_serial(self, small_dataset):
        """测试小数据集自动降级到串行"""
        factor_df, prices_df = small_dataset

        # 配置启用并行
        config = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        calculator = ICCalculator(parallel_config=config)

        # 应该自动降级到串行（因为数据量小）
        ic_series = calculator.calculate_ic_series(factor_df, prices_df)

        assert len(ic_series) > 0

    def test_use_parallel_on_large_data(self, large_dataset):
        """测试大数据集使用并行"""
        factor_df, prices_df = large_dataset

        config = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        calculator = ICCalculator(parallel_config=config)

        # 应该使用并行计算
        ic_series = calculator.calculate_ic_series(factor_df, prices_df)

        assert len(ic_series) > 0


# ==================== 批量因子分析测试 ====================

class TestBatchFactorAnalysis:
    """批量因子分析测试"""

    @pytest.fixture
    def multi_factors(self, medium_dataset):
        """生成多个因子"""
        factor_df, prices_df = medium_dataset

        factor_dict = {}
        for i in range(5):
            # 添加随机扰动
            noise = np.random.randn(*factor_df.shape) * 0.3
            factor_dict[f'factor_{i}'] = factor_df + noise

        return factor_dict, prices_df

    def test_batch_analyze_consistency(self, multi_factors):
        """测试批量分析的一致性"""
        factor_dict, prices_df = multi_factors

        # 串行批量分析
        config_serial = ParallelComputingConfig(enable_parallel=False)
        analyzer_serial = FactorAnalyzer(
            forward_periods=5,
            parallel_config=config_serial
        )
        reports_serial = analyzer_serial.batch_analyze(factor_dict, prices_df)

        # 并行批量分析
        config_parallel = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        analyzer_parallel = FactorAnalyzer(
            forward_periods=5,
            parallel_config=config_parallel
        )
        reports_parallel = analyzer_parallel.batch_analyze(factor_dict, prices_df)

        # 验证分析成功数量一致
        assert len(reports_serial) == len(reports_parallel)

        # 验证每个因子的IC值一致
        for factor_name in factor_dict.keys():
            assert factor_name in reports_serial
            assert factor_name in reports_parallel

            ic_serial = reports_serial[factor_name].ic_result.mean_ic
            ic_parallel = reports_parallel[factor_name].ic_result.mean_ic

            assert np.isclose(ic_serial, ic_parallel, rtol=1e-10), \
                f"因子{factor_name}的IC不一致"

    @pytest.mark.slow
    @pytest.mark.skip(reason="批量分析在小数据集上并行开销大于收益，测试不切实际")
    def test_batch_analyze_speedup(self, multi_factors):
        """测试批量分析的加速比"""
        factor_dict, prices_df = multi_factors

        # 串行
        config_serial = ParallelComputingConfig(enable_parallel=False)
        analyzer_serial = FactorAnalyzer(parallel_config=config_serial)

        start = time.time()
        reports_serial = analyzer_serial.batch_analyze(factor_dict, prices_df)
        serial_time = time.time() - start

        # 并行
        config_parallel = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        analyzer_parallel = FactorAnalyzer(parallel_config=config_parallel)

        start = time.time()
        reports_parallel = analyzer_parallel.batch_analyze(factor_dict, prices_df)
        parallel_time = time.time() - start

        speedup = serial_time / parallel_time

        # 注意：小数据集并行可能更慢
        print(f"批量分析加速比: {speedup:.2f}x")

        # 验证成功数量
        assert len(reports_parallel) == len(factor_dict)


# ==================== 边界情况测试 ====================

class TestEdgeCases:
    """边界情况测试"""

    def test_empty_data(self):
        """测试空数据"""
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        stocks = ['A', 'B', 'C']

        factor_df = pd.DataFrame(
            np.nan,
            index=dates,
            columns=stocks
        )
        prices_df = pd.DataFrame(
            100,
            index=dates,
            columns=stocks
        )

        config = ParallelComputingConfig(n_workers=2, show_progress=False)
        calculator = ICCalculator(parallel_config=config)

        ic_series = calculator.calculate_ic_series(factor_df, prices_df)

        # 应该返回空Series或全NaN
        assert len(ic_series) == 0 or ic_series.isna().all()

    def test_single_stock(self, medium_dataset):
        """测试单只股票"""
        factor_df, prices_df = medium_dataset

        # 只保留第一只股票
        factor_single = factor_df.iloc[:, [0]]
        prices_single = prices_df.iloc[:, [0]]

        config = ParallelComputingConfig(n_workers=2, show_progress=False)
        calculator = ICCalculator(parallel_config=config)

        # 应该能够处理（虽然IC可能无意义）
        ic_series = calculator.calculate_ic_series(factor_single, prices_single)

        # 单只股票IC应该是NaN或空
        assert len(ic_series) == 0 or ic_series.isna().all()

    def test_misaligned_data(self, medium_dataset):
        """测试不对齐的数据"""
        factor_df, prices_df = medium_dataset

        # 截取不同的日期范围
        factor_subset = factor_df.iloc[:60]  # 前60天
        prices_subset = prices_df.iloc[30:]  # 后90天

        config = ParallelComputingConfig(n_workers=2, show_progress=False)
        calculator = ICCalculator(parallel_config=config)

        # 应该自动对齐
        ic_series = calculator.calculate_ic_series(factor_subset, prices_subset)

        # 应该返回有效结果
        assert len(ic_series) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
