#!/usr/bin/env python3
"""
回测层基础使用示例

演示如何使用回测引擎进行策略回测、绩效分析和成本分析

Author: Stock Analysis Core Team
Date: 2026-01-30
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from loguru import logger

from src.backtest import BacktestEngine, PerformanceAnalyzer


def create_sample_data(n_days=252, n_stocks=50):
    """
    创建示例市场数据

    参数:
        n_days: 交易日数（默认252天=1年）
        n_stocks: 股票数量

    返回:
        (prices_df, signals_df): 价格和信号DataFrame
    """
    logger.info(f"生成示例数据: {n_days}天 x {n_stocks}只股票")

    np.random.seed(42)

    # 生成日期和股票代码
    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    stocks = [f'{600000+i:06d}' for i in range(n_stocks)]

    # 生成价格数据（随机游走 + 轻微上涨趋势）
    price_data = {}
    signal_data = {}

    for i, stock in enumerate(stocks):
        # 基础价格
        base_price = 10.0 + i * 0.1

        # 添加趋势（一半上涨，一半下跌）
        trend = 0.0002 if i < n_stocks // 2 else -0.0001

        # 随机收益率 + 趋势
        returns = np.random.normal(trend, 0.015, n_days)

        # 累积收益生成价格序列
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

        # 生成信号：基于动量 + 噪音
        # 使用未来5日收益作为"真实信号"，加上噪音模拟预测误差
        future_returns = (pd.Series(prices).shift(-5) / pd.Series(prices) - 1) * 100

        # 信号 = 真实信号 + 噪音（模拟预测能力）
        signal_noise = np.random.normal(0, 2.0, n_days)  # 噪音
        signals = future_returns + signal_noise

        signal_data[stock] = signals.values

    prices_df = pd.DataFrame(price_data, index=dates)
    signals_df = pd.DataFrame(signal_data, index=dates)

    logger.info(f"数据生成完成:")
    logger.info(f"  价格范围: {prices_df.min().min():.2f} ~ {prices_df.max().max():.2f}")
    logger.info(f"  信号范围: {signals_df.min().min():.2f} ~ {signals_df.max().max():.2f}")

    return prices_df, signals_df


def example1_basic_backtest():
    """
    示例1: 基础回测

    演示最简单的回测流程
    """
    logger.info("\n" + "="*80)
    logger.info("示例1: 基础回测")
    logger.info("="*80)

    # 1. 准备数据
    logger.info("\n1. 准备数据")
    prices, signals = create_sample_data(n_days=252, n_stocks=30)

    # 2. 创建回测引擎
    logger.info("\n2. 创建回测引擎")
    engine = BacktestEngine(
        initial_capital=1000000,  # 100万初始资金
        commission_rate=0.0003,   # 万三佣金
        stamp_tax_rate=0.001,     # 千一印花税
        slippage=0.001,           # 千一滑点
        verbose=True              # 打印详细信息
    )

    logger.info(f"  初始资金: {engine.initial_capital:,.0f} 元")
    logger.info(f"  佣金费率: {engine.commission_rate*10000:.1f} 万分之")
    logger.info(f"  印花税率: {engine.stamp_tax_rate*1000:.1f} 千分之")
    logger.info(f"  滑点: {engine.slippage*1000:.1f} 千分之")

    # 3. 运行回测
    logger.info("\n3. 运行回测")
    results = engine.backtest_long_only(
        signals=signals,
        prices=prices,
        top_n=10,              # 每期持有10只股票
        holding_period=5,      # 最短持有5天
        rebalance_freq='W'     # 每周调仓
    )

    # 4. 查看回测结果
    logger.info("\n4. 回测结果摘要")
    portfolio_value = results['portfolio_value']

    final_value = portfolio_value['total'].iloc[-1]
    total_return = (final_value / engine.initial_capital - 1) * 100

    logger.info(f"  初始资金: {engine.initial_capital:,.0f} 元")
    logger.info(f"  最终资产: {final_value:,.0f} 元")
    logger.info(f"  总收益: {final_value - engine.initial_capital:,.0f} 元")
    logger.info(f"  总收益率: {total_return:.2f}%")

    # 5. 绩效分析
    logger.info("\n5. 绩效分析")
    analyzer = PerformanceAnalyzer(
        returns=results['daily_returns'],
        risk_free_rate=0.03,
        periods_per_year=252
    )

    metrics = analyzer.calculate_all_metrics(verbose=True)

    # 6. 成本分析
    logger.info("\n6. 成本分析")
    cost_metrics = results['cost_analysis']

    logger.info(f"  总交易成本: {cost_metrics['total_cost']:,.2f} 元")
    logger.info(f"    - 佣金: {cost_metrics['total_commission']:,.2f} 元")
    logger.info(f"    - 印花税: {cost_metrics['total_stamp_tax']:,.2f} 元")
    logger.info(f"    - 滑点: {cost_metrics['total_slippage']:,.2f} 元")
    logger.info(f"  总交易次数: {cost_metrics['n_trades']} 次")
    logger.info(f"  年化换手率: {cost_metrics['annual_turnover_rate']:.2f}")
    logger.info(f"  成本拖累: {cost_metrics['cost_drag']*100:.2f}%")

    logger.success("\n✓ 示例1完成\n")

    return results, metrics


def example2_parameter_comparison():
    """
    示例2: 参数对比

    演示不同调仓频率的影响
    """
    logger.info("\n" + "="*80)
    logger.info("示例2: 调仓频率对比")
    logger.info("="*80)

    # 准备数据
    prices, signals = create_sample_data(n_days=252, n_stocks=30)

    # 测试不同调仓频率
    frequencies = {
        'D': '每日调仓',
        'W': '每周调仓',
        'M': '每月调仓'
    }

    results_comparison = []

    for freq, desc in frequencies.items():
        logger.info(f"\n测试 {desc} (频率={freq})")

        # 创建引擎
        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            slippage=0.001,
            verbose=False  # 关闭详细日志
        )

        # 运行回测
        holding_period = 1 if freq == 'D' else (5 if freq == 'W' else 20)

        results = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=10,
            holding_period=holding_period,
            rebalance_freq=freq
        )

        # 绩效分析
        analyzer = PerformanceAnalyzer(
            returns=results['daily_returns'],
            risk_free_rate=0.03
        )
        metrics = analyzer.calculate_all_metrics(verbose=False)
        cost_metrics = results['cost_analysis']

        # 收集结果
        results_comparison.append({
            '调仓频率': desc,
            '年化收益率(%)': f"{metrics['annualized_return']*100:.2f}",
            '夏普比率': f"{metrics['sharpe_ratio']:.4f}",
            '最大回撤(%)': f"{metrics['max_drawdown']*100:.2f}",
            '交易成本(元)': f"{cost_metrics['total_cost']:,.0f}",
            '交易次数': cost_metrics['n_trades'],
            '年化换手率': f"{cost_metrics['annual_turnover_rate']:.2f}",
            '成本拖累(%)': f"{cost_metrics['cost_drag']*100:.2f}"
        })

    # 输出对比表格
    logger.info("\n" + "="*80)
    logger.info("对比结果:")
    logger.info("="*80)

    comparison_df = pd.DataFrame(results_comparison)
    logger.info("\n" + comparison_df.to_string(index=False))

    logger.info("\n分析:")
    logger.info("  - 调仓频率越高，交易成本越高")
    logger.info("  - 需要在收益和成本之间找到平衡")
    logger.info("  - 通常周度调仓是较好的选择")

    logger.success("\n✓ 示例2完成\n")

    return comparison_df


def example3_with_benchmark():
    """
    示例3: 基准对比

    演示如何与基准指数对比
    """
    logger.info("\n" + "="*80)
    logger.info("示例3: 基准对比分析")
    logger.info("="*80)

    # 准备数据
    prices, signals = create_sample_data(n_days=252, n_stocks=30)

    # 生成基准收益（模拟沪深300指数）
    logger.info("\n1. 生成基准数据（模拟沪深300）")
    np.random.seed(123)
    benchmark_returns = pd.Series(
        np.random.normal(0.0003, 0.012, len(prices)),
        index=prices.index
    )

    logger.info(f"  基准平均日收益: {benchmark_returns.mean()*100:.4f}%")
    logger.info(f"  基准年化收益: {benchmark_returns.mean()*252*100:.2f}%")

    # 运行策略回测
    logger.info("\n2. 运行策略回测")
    engine = BacktestEngine(initial_capital=1000000, verbose=False)

    results = engine.backtest_long_only(
        signals=signals,
        prices=prices,
        top_n=10,
        holding_period=5,
        rebalance_freq='W'
    )

    # 绩效分析（含基准）
    logger.info("\n3. 绩效分析（相对基准）")
    analyzer = PerformanceAnalyzer(
        returns=results['daily_returns'],
        benchmark_returns=benchmark_returns,  # 传入基准
        risk_free_rate=0.03
    )

    metrics = analyzer.calculate_all_metrics(verbose=False)

    # 策略指标
    logger.info("\n策略表现:")
    logger.info(f"  年化收益率: {metrics['annualized_return']*100:>10.2f}%")
    logger.info(f"  夏普比率:   {metrics['sharpe_ratio']:>10.4f}")
    logger.info(f"  最大回撤:   {metrics['max_drawdown']*100:>10.2f}%")

    # 基准指标
    benchmark_analyzer = PerformanceAnalyzer(
        returns=benchmark_returns,
        risk_free_rate=0.03
    )
    benchmark_metrics = benchmark_analyzer.calculate_all_metrics(verbose=False)

    logger.info("\n基准表现:")
    logger.info(f"  年化收益率: {benchmark_metrics['annualized_return']*100:>10.2f}%")
    logger.info(f"  夏普比率:   {benchmark_metrics['sharpe_ratio']:>10.4f}")
    logger.info(f"  最大回撤:   {benchmark_metrics['max_drawdown']*100:>10.2f}%")

    # 相对指标
    logger.info("\n相对表现:")
    logger.info(f"  Alpha（超额收益）: {metrics['alpha']*100:>10.2f}%")
    logger.info(f"  Beta（系统风险）:  {metrics['beta']:>10.4f}")
    logger.info(f"  信息比率:          {metrics['information_ratio']:>10.4f}")

    # 解读
    logger.info("\n指标解读:")
    if metrics['alpha'] > 0:
        logger.info(f"  ✓ Alpha为正，策略跑赢基准 {metrics['alpha']*100:.2f}%")
    else:
        logger.info(f"  ✗ Alpha为负，策略跑输基准 {abs(metrics['alpha'])*100:.2f}%")

    if metrics['beta'] < 1:
        logger.info(f"  ✓ Beta < 1，策略波动低于市场")
    else:
        logger.info(f"  ✗ Beta > 1，策略波动高于市场")

    if metrics['information_ratio'] > 0.5:
        logger.info(f"  ✓ 信息比率 > 0.5，策略质量较高")
    else:
        logger.info(f"  ✗ 信息比率 < 0.5，策略需优化")

    logger.success("\n✓ 示例3完成\n")

    return metrics


def example4_cost_deep_dive():
    """
    示例4: 成本深度分析

    演示成本分析器的高级功能
    """
    logger.info("\n" + "="*80)
    logger.info("示例4: 成本深度分析")
    logger.info("="*80)

    # 准备数据
    prices, signals = create_sample_data(n_days=252, n_stocks=30)

    # 运行回测
    logger.info("\n1. 运行回测")
    engine = BacktestEngine(
        initial_capital=1000000,
        commission_rate=0.0003,
        stamp_tax_rate=0.001,
        slippage=0.001,
        verbose=False
    )

    results = engine.backtest_long_only(
        signals=signals,
        prices=prices,
        top_n=10,
        holding_period=5,
        rebalance_freq='W'
    )

    cost_analyzer = results['cost_analyzer']

    # 2. 按股票统计成本
    logger.info("\n2. 成本最高的5只股票:")
    cost_by_stock = cost_analyzer.calculate_cost_by_stock()

    top5_stocks = cost_by_stock.head(5)
    logger.info("\n" + top5_stocks.to_string())

    # 3. 成本时间序列
    logger.info("\n3. 累计成本趋势:")
    cost_over_time = cost_analyzer.calculate_cost_over_time()

    logger.info(f"  起始累计成本: {cost_over_time['cumulative_total_cost'].iloc[0]:,.2f} 元")
    logger.info(f"  最终累计成本: {cost_over_time['cumulative_total_cost'].iloc[-1]:,.2f} 元")
    logger.info(f"  平均每日成本: {cost_over_time['total_cost'].mean():,.2f} 元")

    # 4. 成本场景模拟
    logger.info("\n4. 成本场景模拟（如果成本减半/翻倍）:")
    scenarios = cost_analyzer.simulate_cost_scenarios(
        portfolio_values=results['portfolio_value']['total'],
        cost_multipliers=[0.5, 0.8, 1.0, 1.2, 1.5]
    )

    logger.info("\n" + scenarios.to_string(index=False))

    # 5. 成本影响分析
    logger.info("\n5. 成本影响分析:")
    cost_impact = cost_analyzer.calculate_cost_impact(
        portfolio_returns=results['daily_returns'],
        portfolio_values=results['portfolio_value']['total']
    )

    logger.info(f"  有成本收益率: {cost_impact['return_with_cost']*100:>10.2f}%")
    logger.info(f"  无成本收益率: {cost_impact['return_without_cost']*100:>10.2f}%")
    logger.info(f"  成本拖累:     {cost_impact['cost_drag']*100:>10.2f}%")
    logger.info(f"  成本/初始资金: {cost_impact['cost_to_capital_ratio']*100:>10.2f}%")

    if cost_impact['cost_to_profit_ratio'] < float('inf'):
        logger.info(f"  成本/总收益:   {cost_impact['cost_to_profit_ratio']*100:>10.2f}%")

    # 优化建议
    logger.info("\n6. 优化建议:")
    cost_metrics = results['cost_analysis']

    if cost_metrics['annual_turnover_rate'] > 5:
        logger.warning("  ⚠ 换手率过高 (>5)，建议降低调仓频率")

    if cost_metrics['cost_drag'] > 0.02:
        logger.warning("  ⚠ 成本拖累 >2%，建议优化交易策略")

    if cost_metrics['cost_to_profit_ratio'] > 0.3:
        logger.warning("  ⚠ 成本占收益 >30%，策略可能不可行")

    logger.success("\n✓ 示例4完成\n")

    return cost_by_stock, scenarios


def main():
    """运行所有示例"""
    logger.info("\n" + "🚀"*40)
    logger.info("回测层基础使用示例")
    logger.info("🚀"*40)

    try:
        # 示例1: 基础回测
        results1, metrics1 = example1_basic_backtest()

        # 示例2: 参数对比
        comparison = example2_parameter_comparison()

        # 示例3: 基准对比
        metrics3 = example3_with_benchmark()

        # 示例4: 成本深度分析
        cost_by_stock, scenarios = example4_cost_deep_dive()

        # 总结
        logger.info("\n" + "="*80)
        logger.info("所有示例运行完成！")
        logger.info("="*80)

        logger.info("\n你已学会:")
        logger.info("  ✓ 如何进行基础回测")
        logger.info("  ✓ 如何对比不同参数")
        logger.info("  ✓ 如何与基准对比")
        logger.info("  ✓ 如何深度分析成本")

        logger.info("\n下一步:")
        logger.info("  1. 查看 backtest_cost_optimization.py 学习成本优化")
        logger.info("  2. 查看 backtest_comparison_demo.py 学习多策略对比")
        logger.info("  3. 阅读 docs/BACKTEST_USAGE_GUIDE.md 了解更多细节")

        logger.success("\n✅ 所有示例运行成功！\n")

        return 0

    except Exception as e:
        logger.error(f"\n❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
