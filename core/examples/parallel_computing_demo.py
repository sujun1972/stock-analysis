#!/usr/bin/env python3
"""
并行计算功能演示

演示如何使用并行计算优化加速IC计算和因子分析。

运行方式:
    # 使用虚拟环境
    /path/to/venv/bin/python examples/parallel_computing_demo.py

    # 或激活虚拟环境后
    python examples/parallel_computing_demo.py

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pandas as pd
import numpy as np
from loguru import logger

# 示例1：使用默认配置（自动启用并行）
def example1_auto_parallel():
    """示例1：默认配置，自动启用并行"""
    from src.analysis.ic_calculator import ICCalculator

    logger.info("\n" + "=" * 70)
    logger.info("示例1：使用默认配置（自动启用并行）")
    logger.info("=" * 70)

    # 生成测试数据
    dates = pd.date_range('2020-01-01', periods=250, freq='D')
    stocks = [f'stock_{i}' for i in range(500)]

    factor_df = pd.DataFrame(
        np.random.randn(250, 500),
        index=dates,
        columns=stocks
    )
    prices_df = pd.DataFrame(
        100 + np.cumsum(np.random.randn(250, 500) * 0.02, axis=0),
        index=dates,
        columns=stocks
    )

    # 使用默认配置
    calculator = ICCalculator(forward_periods=5)
    ic_series = calculator.calculate_ic_series(factor_df, prices_df)

    logger.success(f"✓ 计算完成！IC值数量: {len(ic_series)}")
    logger.info(f"  IC均值: {ic_series.mean():.6f}")
    logger.info(f"  IC标准差: {ic_series.std():.6f}")


# 示例2：显式控制并行配置
def example2_explicit_config():
    """示例2：显式控制并行配置"""
    from src.analysis.ic_calculator import ICCalculator
    from src.config.features import ParallelComputingConfig

    logger.info("\n" + "=" * 70)
    logger.info("示例2：显式控制并行配置（8 workers）")
    logger.info("=" * 70)

    # 生成测试数据
    dates = pd.date_range('2020-01-01', periods=250, freq='D')
    stocks = [f'stock_{i}' for i in range(500)]

    factor_df = pd.DataFrame(
        np.random.randn(250, 500),
        index=dates,
        columns=stocks
    )
    prices_df = pd.DataFrame(
        100 + np.cumsum(np.random.randn(250, 500) * 0.02, axis=0),
        index=dates,
        columns=stocks
    )

    # 创建并行配置
    config = ParallelComputingConfig(
        enable_parallel=True,
        n_workers=8,
        show_progress=True,
        chunk_size=50
    )

    calculator = ICCalculator(
        forward_periods=5,
        method='pearson',
        parallel_config=config
    )

    ic_series = calculator.calculate_ic_series(factor_df, prices_df)

    logger.success(f"✓ 计算完成！IC值数量: {len(ic_series)}")


# 示例3：批量因子分析
def example3_batch_analysis():
    """示例3：批量因子分析（自动并行）"""
    from src.analysis.factor_analyzer import FactorAnalyzer

    logger.info("\n" + "=" * 70)
    logger.info("示例3：批量因子分析（自动并行）")
    logger.info("=" * 70)

    # 生成测试数据
    dates = pd.date_range('2020-01-01', periods=120, freq='D')
    stocks = [f'stock_{i}' for i in range(300)]

    base_factor = pd.DataFrame(
        np.random.randn(120, 300),
        index=dates,
        columns=stocks
    )
    prices_df = pd.DataFrame(
        100 + np.cumsum(np.random.randn(120, 300) * 0.02, axis=0),
        index=dates,
        columns=stocks
    )

    # 生成10个因子（添加随机扰动）
    factor_dict = {}
    for i in range(10):
        noise = np.random.randn(*base_factor.shape) * 0.3
        factor_dict[f'factor_{i}'] = base_factor + noise

    logger.info(f"准备分析 {len(factor_dict)} 个因子...")

    # 批量分析（自动并行）
    analyzer = FactorAnalyzer(forward_periods=5)
    reports = analyzer.batch_analyze(factor_dict, prices_df)

    logger.success(f"✓ 批量分析完成！成功分析 {len(reports)} 个因子")

    # 打印前3个因子的IC
    logger.info("\n因子IC统计:")
    for i, (factor_name, report) in enumerate(list(reports.items())[:3]):
        ic_mean = report.ic_result.mean_ic
        ic_ir = report.ic_result.ic_ir
        logger.info(f"  {factor_name}: IC={ic_mean:.4f}, ICIR={ic_ir:.4f}")


# 示例4：全局配置
def example4_global_config():
    """示例4：设置全局并行配置"""
    from src.analysis.ic_calculator import ICCalculator
    from src.config.features import (
        get_feature_config,
        set_feature_config,
        FeatureEngineerConfig,
        ParallelComputingConfig
    )

    logger.info("\n" + "=" * 70)
    logger.info("示例4：设置全局并行配置")
    logger.info("=" * 70)

    # 设置全局配置
    feature_config = FeatureEngineerConfig(
        parallel_computing=ParallelComputingConfig(
            n_workers=4,
            show_progress=True
        )
    )
    set_feature_config(feature_config)

    logger.info("✓ 已设置全局并行配置（4 workers）")

    # 生成测试数据
    dates = pd.date_range('2020-01-01', periods=120, freq='D')
    stocks = [f'stock_{i}' for i in range(300)]

    factor_df = pd.DataFrame(
        np.random.randn(120, 300),
        index=dates,
        columns=stocks
    )
    prices_df = pd.DataFrame(
        100 + np.cumsum(np.random.randn(120, 300) * 0.02, axis=0),
        index=dates,
        columns=stocks
    )

    # 后续所有计算自动使用全局配置
    calculator = ICCalculator()  # 自动使用全局配置
    ic_series = calculator.calculate_ic_series(factor_df, prices_df)

    logger.success(f"✓ 计算完成（使用全局配置）！IC值数量: {len(ic_series)}")


# 示例5：禁用并行（调试模式）
def example5_debug_mode():
    """示例5：禁用并行用于调试"""
    from src.analysis.ic_calculator import ICCalculator
    from src.config.features import ParallelComputingConfig

    logger.info("\n" + "=" * 70)
    logger.info("示例5：禁用并行（调试模式）")
    logger.info("=" * 70)

    # 生成测试数据
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

    # 禁用并行（便于调试）
    config = ParallelComputingConfig(enable_parallel=False)
    calculator = ICCalculator(parallel_config=config)

    ic_series = calculator.calculate_ic_series(factor_df, prices_df)

    logger.success(f"✓ 串行计算完成！IC值数量: {len(ic_series)}")
    logger.info("  (调试模式：易于设置断点和追踪错误)")


# 示例6：使用便捷函数
def example6_convenience_functions():
    """示例6：使用便捷函数直接并行执行"""
    from src.utils.parallel_executor import parallel_map

    logger.info("\n" + "=" * 70)
    logger.info("示例6：使用便捷函数直接并行执行")
    logger.info("=" * 70)

    def compute_expensive_func(x):
        """模拟耗时计算"""
        import time
        time.sleep(0.01)
        return x ** 2

    # 使用便捷函数
    results = parallel_map(
        compute_expensive_func,
        range(20),
        n_workers=4,
        show_progress=True,
        desc="计算平方"
    )

    logger.success(f"✓ 并行计算完成！结果数量: {len(results)}")
    logger.info(f"  前5个结果: {results[:5]}")


if __name__ == "__main__":
    import multiprocessing as mp

    logger.info("\n" + "=" * 70)
    logger.info("并行计算功能演示")
    logger.info("=" * 70)
    logger.info(f"系统CPU核心数: {mp.cpu_count()}")
    logger.info("=" * 70 + "\n")

    try:
        # 运行所有示例
        example1_auto_parallel()
        example2_explicit_config()
        example3_batch_analysis()
        example4_global_config()
        example5_debug_mode()
        example6_convenience_functions()

        logger.success("\n" + "=" * 70)
        logger.success("所有演示完成！")
        logger.success("=" * 70 + "\n")

    except Exception as e:
        logger.error(f"\n演示失败: {e}")
        import traceback
        traceback.print_exc()
