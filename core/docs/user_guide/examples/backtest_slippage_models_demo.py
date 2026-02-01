#!/usr/bin/env python3
"""
滑点模型使用示例

演示如何在回测中使用不同的滑点模型，以提升回测的真实性

示例包括:
1. 固定滑点 vs 高级滑点对比
2. 基于成交量的滑点（考虑流动性）
3. 市场冲击模型（最真实）
4. 不同策略的滑点敏感性分析

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

from src.backtest import (
    BacktestEngine,
    PerformanceAnalyzer,
    FixedSlippageModel,
    VolumeBasedSlippageModel,
    MarketImpactModel,
    create_slippage_model
)


def create_sample_data_with_volume(n_days=252, n_stocks=50):
    """
    创建包含成交量的示例数据

    返回:
        (prices, signals, volumes, volatilities)
    """
    logger.info(f"生成示例数据: {n_days}天 x {n_stocks}只股票")

    np.random.seed(42)

    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    stocks = [f'{600000+i:06d}' for i in range(n_stocks)]

    # 价格数据
    price_data = {}
    signal_data = {}
    volume_data = {}
    volatility_data = {}

    for i, stock in enumerate(stocks):
        base_price = 10.0 + i * 0.1
        trend = 0.0002 if i < n_stocks // 2 else -0.0001

        # 价格
        returns = np.random.normal(trend, 0.015, n_days)
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

        # 信号
        future_returns = (pd.Series(prices).shift(-5) / pd.Series(prices) - 1) * 100
        signals = future_returns + np.random.normal(0, 2.0, n_days)
        signal_data[stock] = signals.values

        # 成交量（股数）- 模拟流动性差异
        # 大盘股流动性好，小盘股流动性差
        if i < n_stocks // 3:
            # 大盘股：高流动性
            base_volume = 5000000 * (1 + np.random.rand())
        elif i < 2 * n_stocks // 3:
            # 中盘股：中等流动性
            base_volume = 1000000 * (1 + np.random.rand())
        else:
            # 小盘股：低流动性
            base_volume = 200000 * (1 + np.random.rand())

        volumes = base_volume * (1 + np.random.randn(n_days) * 0.3)
        volumes = np.abs(volumes)
        volume_data[stock] = volumes

        # 波动率（滚动20日标准差）
        vol_series = pd.Series(returns).rolling(20).std()
        vol_series = vol_series.fillna(0.015)  # 填充初始值
        volatility_data[stock] = vol_series.values

    prices_df = pd.DataFrame(price_data, index=dates)
    signals_df = pd.DataFrame(signal_data, index=dates)
    volumes_df = pd.DataFrame(volume_data, index=dates)
    volatilities_df = pd.DataFrame(volatility_data, index=dates)

    logger.info("数据特点:")
    logger.info(f"  大盘股(前1/3): 平均日成交量 {volumes_df.iloc[:, :n_stocks//3].mean().mean()/10000:.1f}万股")
    logger.info(f"  中盘股(中1/3): 平均日成交量 {volumes_df.iloc[:, n_stocks//3:2*n_stocks//3].mean().mean()/10000:.1f}万股")
    logger.info(f"  小盘股(后1/3): 平均日成交量 {volumes_df.iloc[:, 2*n_stocks//3:].mean().mean()/10000:.1f}万股")

    return prices_df, signals_df, volumes_df, volatilities_df


def example1_fixed_vs_advanced_slippage():
    """
    示例1: 固定滑点 vs 高级滑点对比

    展示高级滑点模型如何提升回测真实性
    """
    logger.info("\n" + "="*80)
    logger.info("示例1: 固定滑点 vs 高级滑点对比")
    logger.info("="*80)

    # 准备数据
    prices, signals, volumes, volatilities = create_sample_data_with_volume(n_days=252, n_stocks=50)

    # 配置
    backtest_config = {
        'initial_capital': 1000000,
        'top_n': 20,
        'holding_period': 5,
        'rebalance_freq': 'W'
    }

    # 测试不同滑点模型
    models_to_test = [
        ('固定滑点(千一)', FixedSlippageModel(slippage_pct=0.001)),
        ('基于成交量', VolumeBasedSlippageModel(base_slippage=0.0005, impact_coefficient=0.01)),
        ('市场冲击模型', MarketImpactModel(volatility_weight=0.5, volume_impact_alpha=0.5)),
    ]

    results_list = []

    for model_name, slippage_model in models_to_test:
        logger.info(f"\n测试: {model_name}")

        # 创建回测引擎
        engine = BacktestEngine(
            initial_capital=backtest_config['initial_capital'],
            slippage_model=slippage_model,  # 使用滑点模型
            verbose=False
        )

        # 设置市场数据（供高级模型使用）
        engine.set_market_data(
            volumes=volumes,
            volatilities=volatilities
        )

        # 运行回测
        results = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=backtest_config['top_n'],
            holding_period=backtest_config['holding_period'],
            rebalance_freq=backtest_config['rebalance_freq']
        )

        # 绩效分析
        analyzer = PerformanceAnalyzer(results['daily_returns'], risk_free_rate=0.03)
        metrics = analyzer.calculate_all_metrics(verbose=False)
        cost_metrics = results['cost_analysis']

        results_list.append({
            '滑点模型': model_name,
            '年化收益(%)': f"{metrics['annualized_return']*100:.2f}",
            '夏普比率': f"{metrics['sharpe_ratio']:.3f}",
            '最大回撤(%)': f"{metrics['max_drawdown']*100:.2f}",
            '总成本(元)': f"{cost_metrics['total_cost']:,.0f}",
            '滑点成本(元)': f"{cost_metrics['total_slippage']:,.0f}",
            '成本拖累(%)': f"{cost_metrics['cost_drag']*100:.2f}"
        })

    # 对比结果
    comparison_df = pd.DataFrame(results_list)

    logger.info("\n" + "="*80)
    logger.info("对比结果:")
    logger.info("="*80)
    logger.info("\n" + comparison_df.to_string(index=False))

    logger.info("\n分析:")
    logger.info("  固定滑点模型:")
    logger.info("    - 优点：简单，计算快")
    logger.info("    - 缺点：不考虑市场状况，可能低估大单成本")
    logger.info("  基于成交量模型:")
    logger.info("    - 优点：考虑流动性，大单滑点更高")
    logger.info("    - 适合：中大资金策略")
    logger.info("  市场冲击模型:")
    logger.info("    - 优点：最真实，考虑波动率和紧急度")
    logger.info("    - 适合：精确回测和学术研究")

    logger.success("\n✓ 示例1完成\n")

    return comparison_df


def example2_liquidity_impact():
    """
    示例2: 流动性对滑点的影响

    测试大盘股vs小盘股的滑点差异
    """
    logger.info("\n" + "="*80)
    logger.info("示例2: 流动性对滑点的影响")
    logger.info("="*80)

    # 准备数据
    prices, signals, volumes, volatilities = create_sample_data_with_volume(n_days=252, n_stocks=60)

    n_stocks = len(prices.columns)

    # 分组：大盘股 vs 小盘股
    large_cap_stocks = prices.columns[:n_stocks//3]  # 前1/3
    small_cap_stocks = prices.columns[2*n_stocks//3:]  # 后1/3

    logger.info(f"\n测试配置:")
    logger.info(f"  大盘股: {len(large_cap_stocks)}只（高流动性）")
    logger.info(f"  小盘股: {len(small_cap_stocks)}只（低流动性）")

    # 使用基于成交量的滑点模型
    slippage_model = VolumeBasedSlippageModel(
        base_slippage=0.0005,
        impact_coefficient=0.02
    )

    results_by_group = []

    for group_name, stock_list in [('大盘股', large_cap_stocks), ('小盘股', small_cap_stocks)]:
        logger.info(f"\n回测 {group_name}...")

        # 筛选数据
        group_prices = prices[stock_list]
        group_signals = signals[stock_list]
        group_volumes = volumes[stock_list]
        group_volatilities = volatilities[stock_list]

        # 回测
        engine = BacktestEngine(
            initial_capital=1000000,
            slippage_model=slippage_model,
            verbose=False
        )

        engine.set_market_data(
            volumes=group_volumes,
            volatilities=group_volatilities
        )

        results = engine.backtest_long_only(
            signals=group_signals,
            prices=group_prices,
            top_n=10,
            holding_period=5,
            rebalance_freq='W'
        )

        # 分析
        analyzer = PerformanceAnalyzer(results['daily_returns'], risk_free_rate=0.03)
        metrics = analyzer.calculate_all_metrics(verbose=False)
        cost_metrics = results['cost_analysis']

        results_by_group.append({
            '股票类型': group_name,
            '年化收益(%)': f"{metrics['annualized_return']*100:.2f}",
            '夏普比率': f"{metrics['sharpe_ratio']:.3f}",
            '总成本(元)': f"{cost_metrics['total_cost']:,.0f}",
            '滑点成本(元)': f"{cost_metrics['total_slippage']:,.0f}",
            '滑点占比(%)': f"{cost_metrics['slippage_pct']*100:.1f}",
            '成本拖累(%)': f"{cost_metrics['cost_drag']*100:.2f}"
        })

    comparison_df = pd.DataFrame(results_by_group)

    logger.info("\n" + "="*80)
    logger.info("对比结果:")
    logger.info("="*80)
    logger.info("\n" + comparison_df.to_string(index=False))

    logger.info("\n结论:")
    logger.info("  小盘股策略需要:")
    logger.info("    1. 使用高级滑点模型（考虑流动性）")
    logger.info("    2. 限制单只股票仓位")
    logger.info("    3. 降低调仓频率")
    logger.info("    4. 考虑分批建仓")

    logger.success("\n✓ 示例2完成\n")

    return comparison_df


def example3_order_size_sensitivity():
    """
    示例3: 订单规模敏感性分析

    测试不同选股数量下的滑点成本
    """
    logger.info("\n" + "="*80)
    logger.info("示例3: 订单规模敏感性分析")
    logger.info("="*80)

    # 准备数据
    prices, signals, volumes, volatilities = create_sample_data_with_volume(n_days=252, n_stocks=50)

    # 测试不同选股数量
    top_n_list = [5, 10, 20, 30]

    # 使用市场冲击模型
    slippage_model = MarketImpactModel(
        volatility_weight=0.5,
        volume_impact_alpha=0.5
    )

    results_list = []

    for top_n in top_n_list:
        logger.info(f"\n测试 top_n={top_n}...")

        engine = BacktestEngine(
            initial_capital=1000000,
            slippage_model=slippage_model,
            verbose=False
        )

        engine.set_market_data(volumes=volumes, volatilities=volatilities)

        results = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            top_n=top_n,
            holding_period=5,
            rebalance_freq='W'
        )

        analyzer = PerformanceAnalyzer(results['daily_returns'], risk_free_rate=0.03)
        metrics = analyzer.calculate_all_metrics(verbose=False)
        cost_metrics = results['cost_analysis']

        # 计算平均单只股票仓位
        avg_position = 1000000 / top_n

        results_list.append({
            '选股数量': top_n,
            '平均单只仓位(万)': f"{avg_position/10000:.1f}",
            '年化收益(%)': f"{metrics['annualized_return']*100:.2f}",
            '夏普比率': f"{metrics['sharpe_ratio']:.3f}",
            '总滑点(元)': f"{cost_metrics['total_slippage']:,.0f}",
            '滑点占比(%)': f"{cost_metrics['slippage_pct']*100:.1f}",
            '成本拖累(%)': f"{cost_metrics['cost_drag']*100:.2f}"
        })

    comparison_df = pd.DataFrame(results_list)

    logger.info("\n" + "="*80)
    logger.info("对比结果:")
    logger.info("="*80)
    logger.info("\n" + comparison_df.to_string(index=False))

    logger.info("\n规律:")
    logger.info("  选股数量少 → 单只仓位大 → 滑点成本高")
    logger.info("  选股数量多 → 单只仓位小 → 滑点成本低（但分散）")

    logger.info("\n优化建议:")
    logger.info("  1. 根据资金量选择合适的选股数")
    logger.info("  2. 小资金(< 100万): 5-10只")
    logger.info("  3. 中资金(100-500万): 10-20只")
    logger.info("  4. 大资金(> 500万): 20-50只")

    logger.success("\n✓ 示例3完成\n")

    return comparison_df


def example4_model_recommendation():
    """
    示例4: 滑点模型选择建议

    根据不同场景推荐合适的滑点模型
    """
    logger.info("\n" + "="*80)
    logger.info("示例4: 滑点模型选择建议")
    logger.info("="*80)

    logger.info("\n📊 滑点模型对比:")
    logger.info("\n1. 固定滑点模型 (FixedSlippageModel)")
    logger.info("   适用场景:")
    logger.info("     ✓ 快速回测原型")
    logger.info("     ✓ 大盘股策略（流动性充足）")
    logger.info("     ✓ 对精度要求不高")
    logger.info("   参数设置:")
    logger.info("     - 散户: slippage_pct=0.001 (千一)")
    logger.info("     - 机构: slippage_pct=0.0005 (万五)")

    logger.info("\n2. 基于成交量模型 (VolumeBasedSlippageModel)")
    logger.info("   适用场景:")
    logger.info("     ✓ 中大资金策略（100万+）")
    logger.info("     ✓ 需要考虑流动性")
    logger.info("     ✓ 小盘股策略")
    logger.info("   参数设置:")
    logger.info("     - base_slippage=0.0005 (基础滑点)")
    logger.info("     - impact_coefficient=0.01~0.02 (冲击系数)")
    logger.info("     - 需要成交量数据")

    logger.info("\n3. 市场冲击模型 (MarketImpactModel)")
    logger.info("   适用场景:")
    logger.info("     ✓ 精确回测")
    logger.info("     ✓ 学术研究")
    logger.info("     ✓ 大资金量化策略")
    logger.info("   参数设置:")
    logger.info("     - volatility_weight=0.5 (波动率权重)")
    logger.info("     - volume_impact_alpha=0.5 (冲击幂次)")
    logger.info("     - 需要成交量和波动率数据")

    logger.info("\n4. 买卖价差模型 (BidAskSpreadModel)")
    logger.info("   适用场景:")
    logger.info("     ✓ 高频策略")
    logger.info("     ✓ 有盘口数据")
    logger.info("     ✓ 日内交易")
    logger.info("   参数设置:")
    logger.info("     - base_spread=0.0002 (基础价差)")
    logger.info("     - 可选：提供盘口数据")

    logger.info("\n📌 选择决策树:")
    logger.info("  有成交量数据?")
    logger.info("    └─ 是 → 资金量大(>500万)?")
    logger.info("       └─ 是 → 市场冲击模型 (最精确)")
    logger.info("       └─ 否 → 基于成交量模型 (平衡)")
    logger.info("    └─ 否 → 固定滑点模型 (简单)")

    logger.info("\n💡 实战建议:")
    logger.info("  1. 开发阶段: 使用固定滑点快速迭代")
    logger.info("  2. 优化阶段: 切换到基于成交量模型")
    logger.info("  3. 上线前: 使用市场冲击模型做最终验证")
    logger.info("  4. 小资金: 滑点影响小，用固定模型即可")
    logger.info("  5. 大资金: 必须用高级模型，否则严重低估成本")

    logger.success("\n✓ 示例4完成\n")


def main():
    """运行所有示例"""
    logger.info("\n" + "📐"*40)
    logger.info("滑点模型使用示例")
    logger.info("📐"*40)

    try:
        # 示例1: 固定 vs 高级滑点
        comparison1 = example1_fixed_vs_advanced_slippage()

        # 示例2: 流动性影响
        comparison2 = example2_liquidity_impact()

        # 示例3: 订单规模敏感性
        comparison3 = example3_order_size_sensitivity()

        # 示例4: 模型选择建议
        example4_model_recommendation()

        # 总结
        logger.info("\n" + "="*80)
        logger.info("所有示例运行完成！")
        logger.info("="*80)

        logger.info("\n核心发现:")
        logger.info("  1. 高级滑点模型更真实，尤其对大资金策略")
        logger.info("  2. 小盘股滑点成本显著高于大盘股")
        logger.info("  3. 选股数量影响单只仓位，进而影响滑点")
        logger.info("  4. 不同场景需要选择合适的滑点模型")

        logger.info("\n实战价值:")
        logger.info("  ✓ 避免回测过度乐观（低估滑点）")
        logger.info("  ✓ 大资金策略必须考虑市场冲击")
        logger.info("  ✓ 小盘股策略需要特别关注流动性")
        logger.info("  ✓ 滑点模型是回测真实性的关键")

        logger.info("\n下一步:")
        logger.info("  1. 在真实数据上测试不同滑点模型")
        logger.info("  2. 根据资金量选择合适的模型")
        logger.info("  3. 持续优化滑点估计参数")

        logger.success("\n✅ 滑点模型示例运行成功！\n")

        return 0

    except Exception as e:
        logger.error(f"\n❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
