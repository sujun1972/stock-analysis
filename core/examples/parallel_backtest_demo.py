#!/usr/bin/env python3
"""
并行回测功能演示

演示如何使用 ParallelBacktester 同时回测多个策略并对比结果。

运行方式:
    # 使用虚拟环境
    /path/to/venv/bin/python examples/parallel_backtest_demo.py

    # 或激活虚拟环境后
    python examples/parallel_backtest_demo.py

作者: Stock Analysis Team
创建: 2026-01-31
"""

import pandas as pd
import numpy as np
from loguru import logger
import time

# ==================== 示例1：基础并行回测 ====================

def example1_basic_parallel_backtest():
    """示例1：基础并行回测多个策略"""
    from src.backtest.parallel_backtester import ParallelBacktester
    from src.strategies.momentum_strategy import MomentumStrategy
    from src.strategies.mean_reversion_strategy import MeanReversionStrategy

    logger.info("\n" + "=" * 70)
    logger.info("示例1：基础并行回测多个策略")
    logger.info("=" * 70)

    # 1. 生成测试数据
    dates = pd.date_range('2020-01-01', periods=250, freq='D')
    stocks = [f'stock_{i}' for i in range(100)]

    np.random.seed(42)
    # 生成价格数据（带趋势和噪声）
    base_prices = 100
    returns = np.random.randn(250, 100) * 0.02
    prices = base_prices * (1 + returns).cumprod(axis=0)
    prices_df = pd.DataFrame(prices, index=dates, columns=stocks)

    logger.info(f"数据形状: {prices_df.shape}")

    # 2. 创建多个策略
    strategies = [
        MomentumStrategy(
            name="动量策略-20日",
            config={'lookback': 20, 'top_n': 20}
        ),
        MomentumStrategy(
            name="动量策略-10日",
            config={'lookback': 10, 'top_n': 20}
        ),
        MeanReversionStrategy(
            name="均值回归-15日",
            config={'lookback': 15, 'top_n': 20}
        )
    ]

    logger.info(f"策略数量: {len(strategies)}")

    # 3. 创建并行回测器
    backtester = ParallelBacktester(n_workers=4, show_progress=True)

    # 4. 执行并行回测
    start_time = time.time()

    results = backtester.run(
        strategies=strategies,
        prices=prices_df,
        initial_capital=1000000,
        commission_rate=0.0003,
        top_n=20,
        holding_period=5,
        rebalance_freq='W'
    )

    elapsed = time.time() - start_time

    logger.success(f"\n并行回测完成，耗时: {elapsed:.2f}秒")

    # 5. 生成对比报告
    report = backtester.generate_comparison_report(results)

    logger.info("\n对比报告已生成！")


# ==================== 示例2：串行 vs 并行性能对比 ====================

def example2_serial_vs_parallel():
    """示例2：对比串行和并行的性能差异"""
    from src.backtest.parallel_backtester import ParallelBacktester
    from src.strategies.momentum_strategy import MomentumStrategy
    from src.strategies.mean_reversion_strategy import MeanReversionStrategy
    from src.strategies.multi_factor_strategy import MultiFactorStrategy

    logger.info("\n" + "=" * 70)
    logger.info("示例2：串行 vs 并行性能对比")
    logger.info("=" * 70)

    # 生成数据
    dates = pd.date_range('2020-01-01', periods=200, freq='D')
    stocks = [f'stock_{i}' for i in range(80)]

    np.random.seed(42)
    prices = 100 * (1 + np.random.randn(200, 80) * 0.02).cumprod(axis=0)
    prices_df = pd.DataFrame(prices, index=dates, columns=stocks)

    # 创建多个策略
    strategies = [
        MomentumStrategy("动量-5日", {'lookback': 5, 'top_n': 15}),
        MomentumStrategy("动量-10日", {'lookback': 10, 'top_n': 15}),
        MomentumStrategy("动量-20日", {'lookback': 20, 'top_n': 15}),
        MeanReversionStrategy("均值回归-10日", {'lookback': 10, 'top_n': 15}),
        MeanReversionStrategy("均值回归-20日", {'lookback': 20, 'top_n': 15}),
    ]

    # 串行回测
    logger.info("\n[1/2] 串行回测...")
    backtester_serial = ParallelBacktester(n_workers=1, show_progress=False)

    start = time.time()
    results_serial = backtester_serial.run(
        strategies=strategies,
        prices=prices_df,
        top_n=15
    )
    time_serial = time.time() - start

    logger.info(f"串行耗时: {time_serial:.2f}秒")

    # 并行回测
    logger.info("\n[2/2] 并行回测（4 workers）...")
    backtester_parallel = ParallelBacktester(n_workers=4, show_progress=False)

    start = time.time()
    results_parallel = backtester_parallel.run(
        strategies=strategies,
        prices=prices_df,
        top_n=15
    )
    time_parallel = time.time() - start

    logger.info(f"并行耗时: {time_parallel:.2f}秒")

    # 性能对比
    speedup = time_serial / time_parallel
    logger.success(f"\n⚡ 加速比: {speedup:.2f}x")

    # 验证结果一致性
    logger.info("\n验证结果一致性...")
    consistent = True
    for name in results_serial.keys():
        score_serial = results_serial[name].get_metrics().get('sharpe_ratio', 0)
        score_parallel = results_parallel[name].get_metrics().get('sharpe_ratio', 0)

        if abs(score_serial - score_parallel) > 0.001:
            consistent = False
            logger.warning(f"{name}: 串行={score_serial:.4f}, 并行={score_parallel:.4f}")

    if consistent:
        logger.success("✓ 结果一致！")


# ==================== 示例3：使用便捷函数 ====================

def example3_convenience_function():
    """示例3：使用便捷函数快速回测"""
    from src.backtest.parallel_backtester import parallel_backtest
    from src.strategies.momentum_strategy import MomentumStrategy

    logger.info("\n" + "=" * 70)
    logger.info("示例3：使用便捷函数")
    logger.info("=" * 70)

    # 生成数据
    dates = pd.date_range('2020-01-01', periods=150, freq='D')
    stocks = [f'stock_{i}' for i in range(50)]

    np.random.seed(42)
    prices = 100 * (1 + np.random.randn(150, 50) * 0.015).cumprod(axis=0)
    prices_df = pd.DataFrame(prices, index=dates, columns=stocks)

    # 快速回测
    strategies = [
        MomentumStrategy("策略A", {'lookback': 10, 'top_n': 10}),
        MomentumStrategy("策略B", {'lookback': 20, 'top_n': 10})
    ]

    results = parallel_backtest(
        strategies=strategies,
        prices=prices_df,
        n_workers=2,
        show_progress=False,
        initial_capital=500000,
        top_n=10
    )

    logger.success(f"✓ 快速回测完成！成功: {sum(1 for r in results.values() if r.success)}/{len(results)}")


# ==================== 示例4：保存报告 ====================

def example4_save_report():
    """示例4：保存对比报告到文件"""
    from src.backtest.parallel_backtester import ParallelBacktester
    from src.strategies.momentum_strategy import MomentumStrategy
    import tempfile

    logger.info("\n" + "=" * 70)
    logger.info("示例4：保存对比报告")
    logger.info("=" * 70)

    # 生成数据
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    stocks = [f'stock_{i}' for i in range(30)]

    np.random.seed(42)
    prices = 100 * (1 + np.random.randn(100, 30) * 0.01).cumprod(axis=0)
    prices_df = pd.DataFrame(prices, index=dates, columns=stocks)

    # 回测
    strategies = [
        MomentumStrategy("策略1", {'lookback': 10}),
        MomentumStrategy("策略2", {'lookback': 15}),
        MomentumStrategy("策略3", {'lookback': 20})
    ]

    backtester = ParallelBacktester(n_workers=2, show_progress=False)

    results = backtester.run(
        strategies=strategies,
        prices=prices_df,
        top_n=10
    )

    # 保存报告
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = f"{tmpdir}/report.csv"
        backtester.save_comparison_report(results, csv_path, format='csv')

        logger.success(f"✓ 报告已保存: {csv_path}")

        # 读取验证
        report_df = pd.read_csv(csv_path)
        logger.info(f"报告行数: {len(report_df)}, 列数: {len(report_df.columns)}")


# ==================== 示例5：错误处理 ====================

def example5_error_handling():
    """示例5：演示错误处理"""
    from src.backtest.parallel_backtester import ParallelBacktester
    from src.strategies.momentum_strategy import MomentumStrategy

    logger.info("\n" + "=" * 70)
    logger.info("示例5：错误处理演示")
    logger.info("=" * 70)

    # 生成数据（包含一些 NaN）
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    stocks = [f'stock_{i}' for i in range(20)]

    np.random.seed(42)
    prices = 100 * (1 + np.random.randn(100, 20) * 0.015).cumprod(axis=0)
    prices_df = pd.DataFrame(prices, index=dates, columns=stocks)

    # 人为引入一些问题数据
    prices_df.iloc[50:55, :5] = np.nan

    logger.warning("数据包含 NaN 值，某些策略可能失败...")

    # 创建策略（包括一些可能失败的配置）
    strategies = [
        MomentumStrategy("正常策略", {'lookback': 10, 'top_n': 10}),
        MomentumStrategy("长周期策略", {'lookback': 50, 'top_n': 5}),  # 可能因数据不足失败
    ]

    backtester = ParallelBacktester(n_workers=2, show_progress=False, verbose=True)

    results = backtester.run(
        strategies=strategies,
        prices=prices_df,
        top_n=10
    )

    # 检查失败的策略
    failed = [name for name, r in results.items() if not r.success]
    successful = [name for name, r in results.items() if r.success]

    logger.info(f"\n成功: {len(successful)}, 失败: {len(failed)}")

    if failed:
        logger.warning(f"失败的策略: {failed}")

    # 即使有失败，仍然可以生成报告
    report = backtester.generate_comparison_report(results)
    logger.success("✓ 对比报告已生成（包含失败信息）")


# ==================== 示例6：自定义回测参数 ====================

def example6_custom_backtest_params():
    """示例6：自定义回测参数"""
    from src.backtest.parallel_backtester import ParallelBacktester
    from src.strategies.momentum_strategy import MomentumStrategy

    logger.info("\n" + "=" * 70)
    logger.info("示例6：自定义回测参数")
    logger.info("=" * 70)

    # 生成数据
    dates = pd.date_range('2020-01-01', periods=120, freq='D')
    stocks = [f'stock_{i}' for i in range(40)]

    np.random.seed(42)
    prices = 100 * (1 + np.random.randn(120, 40) * 0.018).cumprod(axis=0)
    prices_df = pd.DataFrame(prices, index=dates, columns=stocks)

    # 策略
    strategies = [
        MomentumStrategy("策略A", {'lookback': 15, 'top_n': 15}),
        MomentumStrategy("策略B", {'lookback': 25, 'top_n': 15})
    ]

    backtester = ParallelBacktester(n_workers=2, show_progress=False)

    # 自定义回测参数
    results = backtester.run(
        strategies=strategies,
        prices=prices_df,
        initial_capital=2000000,      # 自定义初始资金
        commission_rate=0.0002,       # 自定义佣金率
        stamp_tax_rate=0.001,         # 自定义印花税
        slippage=0.001,               # 自定义滑点
        top_n=15,                     # 选股数量
        holding_period=7,             # 持仓周期
        rebalance_freq='W'            # 调仓频率（周）
    )

    logger.success("✓ 自定义参数回测完成")

    # 显示摘要
    for name, result in results.items():
        if result.success:
            metrics = result.get_metrics()
            logger.info(
                f"{name}: "
                f"收益={metrics.get('total_return', 0)*100:.2f}%, "
                f"夏普={metrics.get('sharpe_ratio', 0):.2f}"
            )


# ==================== 主函数 ====================

if __name__ == "__main__":
    import multiprocessing as mp

    logger.info("\n" + "=" * 70)
    logger.info("并行回测功能演示")
    logger.info("=" * 70)
    logger.info(f"系统CPU核心数: {mp.cpu_count()}")
    logger.info("=" * 70 + "\n")

    try:
        # 运行所有示例
        example1_basic_parallel_backtest()
        example2_serial_vs_parallel()
        example3_convenience_function()
        example4_save_report()
        example5_error_handling()
        example6_custom_backtest_params()

        logger.success("\n" + "=" * 70)
        logger.success("所有演示完成！")
        logger.success("=" * 70 + "\n")

    except Exception as e:
        logger.error(f"\n演示失败: {e}")
        import traceback
        traceback.print_exc()
