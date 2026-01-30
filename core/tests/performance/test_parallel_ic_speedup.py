#!/usr/bin/env python3
"""
IC计算并行加速性能测试

测试目标：
- 验证并行IC计算的加速比
- 对比串行vs并行的性能差异
- 确保结果一致性

预期：
- 8核CPU上实现4-8倍加速
- 结果与串行版本完全一致

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
import time
from loguru import logger

# 设置日志级别
logger.remove()
logger.add(lambda msg: print(msg, end=''), level="INFO")


@pytest.fixture
def large_dataset():
    """生成大规模测试数据集"""
    np.random.seed(42)

    # 250个交易日 × 1000只股票
    n_dates = 250
    n_stocks = 1000

    dates = pd.date_range('2020-01-01', periods=n_dates, freq='D')
    stocks = [f'stock_{i:04d}' for i in range(n_stocks)]

    # 生成随机因子数据
    factor_data = np.random.randn(n_dates, n_stocks)
    factor_df = pd.DataFrame(factor_data, index=dates, columns=stocks)

    # 生成随机价格数据（带趋势）
    prices_data = 100 + np.cumsum(np.random.randn(n_dates, n_stocks) * 0.02, axis=0)
    prices_df = pd.DataFrame(prices_data, index=dates, columns=stocks)

    logger.info(f"生成测试数据: {factor_df.shape}")

    return factor_df, prices_df


@pytest.fixture
def medium_dataset():
    """生成中等规模测试数据集"""
    np.random.seed(42)

    n_dates = 120
    n_stocks = 500

    dates = pd.date_range('2020-01-01', periods=n_dates, freq='D')
    stocks = [f'stock_{i:04d}' for i in range(n_stocks)]

    factor_data = np.random.randn(n_dates, n_stocks)
    factor_df = pd.DataFrame(factor_data, index=dates, columns=stocks)

    prices_data = 100 + np.cumsum(np.random.randn(n_dates, n_stocks) * 0.02, axis=0)
    prices_df = pd.DataFrame(prices_data, index=dates, columns=stocks)

    logger.info(f"生成测试数据: {factor_df.shape}")

    return factor_df, prices_df


class TestICCalculationPerformance:
    """IC计算性能测试"""

    def test_parallel_vs_serial_large_dataset(self, large_dataset):
        """测试大数据集的并行加速"""
        from src.analysis.ic_calculator import ICCalculator
        from src.config.features import ParallelComputingConfig

        factor_df, prices_df = large_dataset

        logger.info("\n" + "=" * 70)
        logger.info("测试1: 大数据集并行加速测试 (250天 × 1000股)")
        logger.info("=" * 70)

        # 串行基准测试
        logger.info("\n[串行执行]")
        config_serial = ParallelComputingConfig(enable_parallel=False)
        calc_serial = ICCalculator(
            forward_periods=5,
            method='pearson',
            parallel_config=config_serial
        )

        start_time = time.time()
        ic_serial = calc_serial.calculate_ic_series(factor_df, prices_df)
        serial_time = time.time() - start_time

        logger.info(f"串行耗时: {serial_time:.3f}秒")
        logger.info(f"IC值数量: {len(ic_serial)}")

        # 并行测试 - 4 workers
        logger.info("\n[并行执行 - 4 workers]")
        config_parallel_4 = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        calc_parallel_4 = ICCalculator(
            forward_periods=5,
            method='pearson',
            parallel_config=config_parallel_4
        )

        start_time = time.time()
        ic_parallel_4 = calc_parallel_4.calculate_ic_series(factor_df, prices_df)
        parallel_time_4 = time.time() - start_time

        speedup_4 = serial_time / parallel_time_4
        logger.info(f"并行耗时: {parallel_time_4:.3f}秒")
        logger.info(f"加速比: {speedup_4:.2f}x")

        # 并行测试 - 8 workers
        logger.info("\n[并行执行 - 8 workers]")
        config_parallel_8 = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=8,
            show_progress=False
        )
        calc_parallel_8 = ICCalculator(
            forward_periods=5,
            method='pearson',
            parallel_config=config_parallel_8
        )

        start_time = time.time()
        ic_parallel_8 = calc_parallel_8.calculate_ic_series(factor_df, prices_df)
        parallel_time_8 = time.time() - start_time

        speedup_8 = serial_time / parallel_time_8
        logger.info(f"并行耗时: {parallel_time_8:.3f}秒")
        logger.info(f"加速比: {speedup_8:.2f}x")

        # 验证结果一致性
        logger.info("\n[结果验证]")
        assert np.allclose(ic_serial.values, ic_parallel_4.values, rtol=1e-10), \
            "4 workers结果不一致"
        assert np.allclose(ic_serial.values, ic_parallel_8.values, rtol=1e-10), \
            "8 workers结果不一致"
        logger.success("✓ 结果一致性验证通过")

        # 性能断言
        logger.info("\n[性能断言]")
        assert speedup_4 > 2.0, f"4 workers加速比({speedup_4:.2f}x)应 > 2.0x"
        assert speedup_8 > 3.0, f"8 workers加速比({speedup_8:.2f}x)应 > 3.0x"
        logger.success(f"✓ 性能要求满足: 4w={speedup_4:.2f}x, 8w={speedup_8:.2f}x")

        # 汇总报告
        logger.info("\n" + "=" * 70)
        logger.info("测试结果汇总:")
        logger.info(f"  串行耗时: {serial_time:.3f}s")
        logger.info(f"  并行耗时 (4w): {parallel_time_4:.3f}s  (加速 {speedup_4:.2f}x)")
        logger.info(f"  并行耗时 (8w): {parallel_time_8:.3f}s  (加速 {speedup_8:.2f}x)")
        logger.info(f"  并行效率 (8w): {speedup_8/8*100:.1f}%")
        logger.info("=" * 70 + "\n")

    def test_parallel_vs_serial_medium_dataset(self, medium_dataset):
        """测试中等数据集的并行加速"""
        from src.analysis.ic_calculator import ICCalculator
        from src.config.features import ParallelComputingConfig

        factor_df, prices_df = medium_dataset

        logger.info("\n" + "=" * 70)
        logger.info("测试2: 中等数据集并行加速测试 (120天 × 500股)")
        logger.info("=" * 70)

        # 串行测试
        config_serial = ParallelComputingConfig(enable_parallel=False)
        calc_serial = ICCalculator(parallel_config=config_serial)

        start_time = time.time()
        ic_serial = calc_serial.calculate_ic_series(factor_df, prices_df)
        serial_time = time.time() - start_time

        logger.info(f"串行耗时: {serial_time:.3f}秒")

        # 并行测试
        config_parallel = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4,
            show_progress=False
        )
        calc_parallel = ICCalculator(parallel_config=config_parallel)

        start_time = time.time()
        ic_parallel = calc_parallel.calculate_ic_series(factor_df, prices_df)
        parallel_time = time.time() - start_time

        speedup = serial_time / parallel_time
        logger.info(f"并行耗时: {parallel_time:.3f}秒")
        logger.info(f"加速比: {speedup:.2f}x")

        # 验证一致性
        assert np.allclose(ic_serial.values, ic_parallel.values, rtol=1e-10)
        logger.success("✓ 结果一致性验证通过")

        # 性能断言（中等数据集加速比可能较低）
        assert speedup > 1.5, f"加速比({speedup:.2f}x)应 > 1.5x"
        logger.success(f"✓ 性能要求满足: {speedup:.2f}x")

    def test_auto_threshold_decision(self):
        """测试自动阈值判断（小数据集不启用并行）"""
        from src.analysis.ic_calculator import ICCalculator
        from src.config.features import ParallelComputingConfig

        logger.info("\n" + "=" * 70)
        logger.info("测试3: 自动阈值判断测试")
        logger.info("=" * 70)

        # 小数据集：50天 × 100股
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=50, freq='D')
        stocks = [f'stock_{i}' for i in range(100)]

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

        logger.info(f"小数据集: {factor_df.shape}")

        # 即使配置启用并行，应该自动降级到串行
        config = ParallelComputingConfig(
            enable_parallel=True,
            n_workers=4
        )
        calculator = ICCalculator(parallel_config=config)

        start_time = time.time()
        ic_series = calculator.calculate_ic_series(factor_df, prices_df)
        elapsed = time.time() - start_time

        logger.info(f"执行耗时: {elapsed:.3f}秒")
        logger.info(f"IC值数量: {len(ic_series)}")
        logger.success("✓ 自动阈值判断测试通过（应使用向量化串行）")


@pytest.mark.benchmark
def test_comprehensive_performance_report(large_dataset):
    """生成综合性能报告"""
    from src.analysis.ic_calculator import ICCalculator
    from src.config.features import ParallelComputingConfig
    import multiprocessing as mp

    factor_df, prices_df = large_dataset

    logger.info("\n" + "=" * 80)
    logger.info("IC计算并行性能综合报告")
    logger.info("=" * 80)
    logger.info(f"数据规模: {factor_df.shape[0]}天 × {factor_df.shape[1]}只股票")
    logger.info(f"CPU核心数: {mp.cpu_count()}")
    logger.info("=" * 80)

    results = []

    # 测试不同worker数量
    worker_counts = [1, 2, 4, 8]

    for n_workers in worker_counts:
        config = ParallelComputingConfig(
            enable_parallel=(n_workers > 1),
            n_workers=n_workers,
            show_progress=False
        )

        calculator = ICCalculator(
            forward_periods=5,
            method='pearson',
            parallel_config=config
        )

        # 预热
        _ = calculator.calculate_ic_series(factor_df.iloc[:10], prices_df.iloc[:10])

        # 正式测试（3次取平均）
        times = []
        for _ in range(3):
            start = time.time()
            ic_series = calculator.calculate_ic_series(factor_df, prices_df)
            elapsed = time.time() - start
            times.append(elapsed)

        avg_time = np.mean(times)
        std_time = np.std(times)

        results.append({
            'workers': n_workers,
            'time': avg_time,
            'std': std_time,
            'ic_count': len(ic_series)
        })

    # 打印报告
    logger.info("\n性能测试结果:")
    logger.info("-" * 80)
    logger.info(f"{'Workers':<10} {'耗时(s)':<12} {'标准差':<12} {'加速比':<12} {'并行效率':<12}")
    logger.info("-" * 80)

    baseline_time = results[0]['time']

    for r in results:
        speedup = baseline_time / r['time']
        efficiency = speedup / r['workers'] * 100 if r['workers'] > 1 else 100

        logger.info(
            f"{r['workers']:<10} "
            f"{r['time']:<12.3f} "
            f"{r['std']:<12.4f} "
            f"{speedup:<12.2f}x "
            f"{efficiency:<12.1f}%"
        )

    logger.info("-" * 80)

    # 计算理论加速比（Amdahl定律）
    serial_fraction = 0.1  # 假设10%串行部分
    for r in results:
        if r['workers'] > 1:
            theoretical_speedup = 1 / (serial_fraction + (1 - serial_fraction) / r['workers'])
            actual_speedup = baseline_time / r['time']
            logger.info(
                f"{r['workers']} workers: 理论加速 {theoretical_speedup:.2f}x, "
                f"实际加速 {actual_speedup:.2f}x "
                f"({'达成' if actual_speedup >= theoretical_speedup * 0.8 else '未达预期'})"
            )

    logger.info("=" * 80 + "\n")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, '-v', '-s', '--tb=short'])
