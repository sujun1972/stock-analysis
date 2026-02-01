#!/usr/bin/env python3
"""
市场中性策略回测示例

展示如何使用BacktestEngine进行多空对冲策略回测

示例包括:
1. 基础市场中性策略
2. 多空对冲降低市场风险
3. 融券成本分析
4. 市场中性vs纯多头对比

Author: Stock Analysis Core Team
Date: 2026-01-30
"""

import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger

from src.backtest.backtest_engine import BacktestEngine
from src.backtest.performance_analyzer import PerformanceAnalyzer
from src.backtest.short_selling import ShortSellingCosts


# ==================== 示例1: 基础市场中性策略 ====================

def example1_basic_market_neutral():
    """示例1: 基础市场中性策略回测"""
    logger.info("="*80)
    logger.info("示例1: 基础市场中性策略")
    logger.info("="*80)

    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=120, freq='D')
    stocks = [f'{i:06d}' for i in range(600000, 600030)]  # 30只股票

    logger.info(f"\n数据准备:")
    logger.info(f"  时间范围: {dates[0]} ~ {dates[-1]}")
    logger.info(f"  股票数量: {len(stocks)} 只")

    # 模拟价格数据（随机游走）
    price_data = {}
    for stock in stocks:
        base_price = 10.0 + np.random.rand() * 5
        returns = np.random.normal(0.0005, 0.02, len(dates))
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    # 模拟信号数据（分化的信号）
    # 前15只股票信号偏高（适合做多）
    # 后15只股票信号偏低（适合做空）
    signal_data = {}
    for i, stock in enumerate(stocks):
        if i < 15:
            # 做多候选：信号与未来收益正相关
            future_returns = prices_df[stock].pct_change(5).shift(-5)
            signals = future_returns * 100 + np.random.normal(2, 1, len(dates))
        else:
            # 做空候选：信号与未来收益负相关
            future_returns = prices_df[stock].pct_change(5).shift(-5)
            signals = -future_returns * 100 + np.random.normal(-2, 1, len(dates))

        signal_data[stock] = signals

    signals_df = pd.DataFrame(signal_data, index=dates)

    logger.info(f"\n信号统计:")
    logger.info(f"  信号均值: {signals_df.mean().mean():.2f}")
    logger.info(f"  信号标准差: {signals_df.std().mean():.2f}")

    # 创建回测引擎
    logger.info(f"\n回测配置:")
    engine = BacktestEngine(
        initial_capital=1000000,
        commission_rate=0.0003,
        stamp_tax_rate=0.001,
        slippage=0.001,
        verbose=True
    )

    logger.info(f"  初始资金: 1,000,000")
    logger.info(f"  佣金费率: 0.03%")
    logger.info(f"  印花税率: 0.1%")
    logger.info(f"  滑点: 0.1%")

    # 运行市场中性回测
    logger.info(f"\n策略参数:")
    logger.info(f"  做多数量: 10")
    logger.info(f"  做空数量: 10")
    logger.info(f"  调仓频率: 每周")
    logger.info(f"  持仓期: 5天")
    logger.info(f"  融券费率: 10%")

    results = engine.backtest_market_neutral(
        signals=signals_df,
        prices=prices_df,
        top_n=10,
        bottom_n=10,
        holding_period=5,
        rebalance_freq='W',
        margin_rate=0.10
    )

    # 分析结果
    logger.info(f"\n" + "="*80)
    logger.info("回测结果")
    logger.info("="*80)

    pv = results['portfolio_value']

    logger.info(f"\n组合价值:")
    logger.info(f"  初始资金: {pv['total'].iloc[0]:,.0f}")
    logger.info(f"  最终资产: {pv['total'].iloc[-1]:,.0f}")
    logger.info(f"  总收益: {pv['total'].iloc[-1] - pv['total'].iloc[0]:,.0f}")
    logger.info(f"  收益率: {(pv['total'].iloc[-1] / pv['total'].iloc[0] - 1) * 100:.2f}%")

    logger.info(f"\n多空持仓:")
    logger.info(f"  平均多头市值: {pv['long_value'].mean():,.0f}")
    logger.info(f"  平均空头市值: {pv['short_value'].mean():,.0f}")
    logger.info(f"  平均现金: {pv['cash'].mean():,.0f}")

    logger.info(f"\n融券成本:")
    logger.info(f"  累计融券利息: {pv['short_interest'].iloc[-1]:,.2f}")
    logger.info(f"  平均空头盈亏: {pv['short_pnl'].mean():,.0f}")

    # 绩效分析
    analyzer = PerformanceAnalyzer(returns=results['daily_returns'])
    metrics = analyzer.calculate_metrics()

    logger.info(f"\n绩效指标:")
    logger.info(f"  年化收益率: {metrics['annual_return']*100:.2f}%")
    logger.info(f"  年化波动率: {metrics['annual_volatility']*100:.2f}%")
    logger.info(f"  夏普比率: {metrics['sharpe_ratio']:.2f}")
    logger.info(f"  最大回撤: {metrics['max_drawdown']*100:.2f}%")
    logger.info(f"  Calmar比率: {metrics['calmar_ratio']:.2f}")

    logger.success("\n✓ 示例1完成\n")

    return results


# ==================== 示例2: 多空对冲降低市场风险 ====================

def example2_hedging_market_risk():
    """示例2: 演示市场中性策略如何降低市场风险"""
    logger.info("="*80)
    logger.info("示例2: 多空对冲降低市场风险")
    logger.info("="*80)

    # 创建有明显趋势的市场数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=120, freq='D')
    stocks = [f'{i:06d}' for i in range(600000, 600020)]

    # 模拟市场整体上涨20%
    market_trend = np.linspace(0, 0.20, len(dates))

    logger.info(f"\n市场环境:")
    logger.info(f"  市场趋势: 整体上涨20%")
    logger.info(f"  时间范围: {len(dates)}天")

    price_data = {}
    for stock in stocks:
        base_price = 10.0
        # 市场趋势 + 个股波动
        individual_returns = np.random.normal(0, 0.015, len(dates))
        combined_returns = market_trend / len(dates) + individual_returns
        prices = base_price * (1 + combined_returns).cumprod()
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    # 随机信号（模拟选股能力一般）
    signals_df = pd.DataFrame(
        np.random.randn(len(dates), len(stocks)),
        index=dates,
        columns=stocks
    )

    # 策略1: 纯多头
    logger.info(f"\n策略1: 纯多头")
    engine_long = BacktestEngine(
        initial_capital=1000000,
        verbose=False
    )

    results_long = engine_long.backtest_long_only(
        signals=signals_df,
        prices=prices_df,
        top_n=10,
        holding_period=5,
        rebalance_freq='W'
    )

    # 策略2: 市场中性
    logger.info(f"策略2: 市场中性")
    engine_neutral = BacktestEngine(
        initial_capital=1000000,
        verbose=False
    )

    results_neutral = engine_neutral.backtest_market_neutral(
        signals=signals_df,
        prices=prices_df,
        top_n=10,
        bottom_n=10,
        holding_period=5,
        rebalance_freq='W'
    )

    # 对比分析
    logger.info(f"\n" + "="*80)
    logger.info("策略对比")
    logger.info("="*80)

    # 收益对比
    pv_long = results_long['portfolio_value']['total']
    pv_neutral = results_neutral['portfolio_value']['total']

    return_long = (pv_long.iloc[-1] / pv_long.iloc[0] - 1) * 100
    return_neutral = (pv_neutral.iloc[-1] / pv_neutral.iloc[0] - 1) * 100

    logger.info(f"\n收益率:")
    logger.info(f"  纯多头: {return_long:>8.2f}%")
    logger.info(f"  市场中性: {return_neutral:>8.2f}%")

    # 风险对比
    analyzer_long = PerformanceAnalyzer(returns=results_long['daily_returns'])
    analyzer_neutral = PerformanceAnalyzer(returns=results_neutral['daily_returns'])
    metrics_long = analyzer_long.calculate_metrics()
    metrics_neutral = analyzer_neutral.calculate_metrics()

    logger.info(f"\n风险指标:")
    logger.info(f"  策略        年化波动率   最大回撤    Beta")
    logger.info(f"  纯多头      {metrics_long['annual_volatility']*100:>8.2f}%  {metrics_long['max_drawdown']*100:>8.2f}%    ~1.0")
    logger.info(f"  市场中性    {metrics_neutral['annual_volatility']*100:>8.2f}%  {metrics_neutral['max_drawdown']*100:>8.2f}%    ~0.0")

    logger.info(f"\n风险调整收益:")
    logger.info(f"  策略        夏普比率   Sortino比率")
    logger.info(f"  纯多头      {metrics_long['sharpe_ratio']:>8.2f}   {metrics_long['sortino_ratio']:>8.2f}")
    logger.info(f"  市场中性    {metrics_neutral['sharpe_ratio']:>8.2f}   {metrics_neutral['sortino_ratio']:>8.2f}")

    # 相关性分析
    logger.info(f"\n市场相关性:")
    market_return = prices_df.mean(axis=1).pct_change()

    corr_long = results_long['daily_returns'].corr(market_return)
    corr_neutral = results_neutral['daily_returns'].corr(market_return)

    logger.info(f"  纯多头与市场相关性: {corr_long:.3f} (高度相关)")
    logger.info(f"  市场中性与市场相关性: {corr_neutral:.3f} (低相关)")

    logger.info(f"\n结论:")
    logger.info(f"  - 在牛市中，纯多头受益于市场上涨，收益更高")
    logger.info(f"  - 市场中性策略通过对冲，大幅降低了市场风险")
    logger.info(f"  - 市场中性的波动率和最大回撤显著更低")
    logger.info(f"  - 市场中性适合追求绝对收益、规避市场风险的投资者")

    logger.success("\n✓ 示例2完成\n")


# ==================== 示例3: 融券成本敏感性分析 ====================

def example3_margin_cost_analysis():
    """示例3: 融券成本对策略收益的影响"""
    logger.info("="*80)
    logger.info("示例3: 融券成本敏感性分析")
    logger.info("="*80)

    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=250, freq='D')  # 1年数据
    stocks = [f'{i:06d}' for i in range(600000, 600020)]

    price_data = {}
    for stock in stocks:
        base_price = 10.0
        returns = np.random.normal(0.0003, 0.018, len(dates))
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    # 有预测能力的信号
    signal_data = {}
    for i, stock in enumerate(stocks):
        if i < 10:
            future_returns = prices_df[stock].pct_change(5).shift(-5)
            signals = future_returns * 100 + np.random.normal(1, 0.5, len(dates))
        else:
            future_returns = prices_df[stock].pct_change(5).shift(-5)
            signals = -future_returns * 100 + np.random.normal(-1, 0.5, len(dates))

        signal_data[stock] = signals

    signals_df = pd.DataFrame(signal_data, index=dates)

    # 测试不同融券费率
    margin_rates = [0.06, 0.08, 0.10, 0.12, 0.15]

    logger.info(f"\n测试不同融券费率: {[f'{r*100:.0f}%' for r in margin_rates]}")

    results_by_rate = {}

    for rate in margin_rates:
        engine = BacktestEngine(initial_capital=1000000, verbose=False)

        results = engine.backtest_market_neutral(
            signals=signals_df,
            prices=prices_df,
            top_n=5,
            bottom_n=5,
            holding_period=10,
            rebalance_freq='M',  # 月度调仓
            margin_rate=rate
        )

        results_by_rate[rate] = results

    # 分析结果
    logger.info(f"\n" + "="*80)
    logger.info("融券费率对收益的影响")
    logger.info("="*80)

    logger.info(f"\n融券费率   总收益率   年化收益   融券利息   利息占比")
    logger.info("-" * 60)

    for rate in margin_rates:
        results = results_by_rate[rate]
        pv = results['portfolio_value']

        total_return = (pv['total'].iloc[-1] / pv['total'].iloc[0] - 1) * 100
        annual_return = ((pv['total'].iloc[-1] / pv['total'].iloc[0]) ** (252/len(dates)) - 1) * 100
        total_interest = pv['short_interest'].iloc[-1]
        interest_pct = (total_interest / 1000000) * 100

        logger.info(
            f"  {rate*100:>4.0f}%     {total_return:>7.2f}%   {annual_return:>7.2f}%   "
            f"{total_interest:>9,.0f}   {interest_pct:>6.2f}%"
        )

    # 可视化利息累计
    logger.info(f"\n利息累计曲线分析:")

    for rate in [0.06, 0.10, 0.15]:
        results = results_by_rate[rate]
        pv = results['portfolio_value']

        logger.info(f"\n  融券费率 {rate*100:.0f}%:")
        logger.info(f"    第1个月利息: {pv['short_interest'].iloc[20]:>8,.0f}")
        logger.info(f"    第3个月利息: {pv['short_interest'].iloc[60]:>8,.0f}")
        logger.info(f"    第6个月利息: {pv['short_interest'].iloc[120]:>8,.0f}")
        logger.info(f"    全年利息: {pv['short_interest'].iloc[-1]:>8,.0f}")

    # 成本效率分析
    logger.info(f"\n成本效率分析:")

    low_rate_return = (results_by_rate[0.06]['portfolio_value']['total'].iloc[-1] / 1000000 - 1) * 100
    high_rate_return = (results_by_rate[0.15]['portfolio_value']['total'].iloc[-1] / 1000000 - 1) * 100
    return_diff = low_rate_return - high_rate_return

    logger.info(f"  6%费率收益率: {low_rate_return:.2f}%")
    logger.info(f"  15%费率收益率: {high_rate_return:.2f}%")
    logger.info(f"  收益差异: {return_diff:.2f}%")
    logger.info(f"\n  结论: 融券费率每增加1%，年化收益约下降{return_diff/9:.2f}%")

    logger.success("\n✓ 示例3完成\n")


# ==================== 示例4: 实际融券成本计算 ====================

def example4_real_world_margin_costs():
    """示例4: 真实融券交易成本计算"""
    logger.info("="*80)
    logger.info("示例4: 真实融券交易成本计算")
    logger.info("="*80)

    # 场景：融券1万股，价格10元，持有60天
    stock_code = '600000'
    shares = 10000
    entry_price = 10.0
    exit_price = 9.5  # 假设下跌5%
    holding_days = 60

    logger.info(f"\n交易场景:")
    logger.info(f"  股票代码: {stock_code}")
    logger.info(f"  融券股数: {shares:,} 股")
    logger.info(f"  融券价格: {entry_price:.2f} 元")
    logger.info(f"  平仓价格: {exit_price:.2f} 元")
    logger.info(f"  持有天数: {holding_days} 天")

    short_amount = shares * entry_price
    cover_amount = shares * exit_price

    logger.info(f"  融券金额: {short_amount:,.0f} 元")

    # 1. 融券开仓成本
    logger.info(f"\n" + "="*80)
    logger.info("1. 融券开仓成本（卖出）")
    logger.info("="*80)

    sell_costs = ShortSellingCosts.calculate_short_sell_cost(
        amount=short_amount,
        stock_code=stock_code,
        commission_rate=0.0003,
        min_commission=5.0
    )

    logger.info(f"  佣金: {sell_costs['commission']:>10,.2f} 元")
    logger.info(f"  印花税: {sell_costs['stamp_tax']:>10,.2f} 元 (无)")
    logger.info(f"  总成本: {sell_costs['total_cost']:>10,.2f} 元")

    # 2. 保证金要求
    logger.info(f"\n" + "="*80)
    logger.info("2. 保证金要求")
    logger.info("="*80)

    margin_50 = ShortSellingCosts.calculate_required_margin(short_amount, margin_ratio=0.5)
    margin_60 = ShortSellingCosts.calculate_required_margin(short_amount, margin_ratio=0.6)

    logger.info(f"  50%保证金: {margin_50:>10,.0f} 元")
    logger.info(f"  60%保证金: {margin_60:>10,.0f} 元")
    logger.info(f"\n  说明: 占用资金 = 保证金金额，影响资金使用效率")

    # 3. 融券利息
    logger.info(f"\n" + "="*80)
    logger.info("3. 融券利息（持有成本）")
    logger.info("="*80)

    interest_8 = ShortSellingCosts.calculate_margin_interest(short_amount, holding_days, 0.08)
    interest_10 = ShortSellingCosts.calculate_margin_interest(short_amount, holding_days, 0.10)
    interest_12 = ShortSellingCosts.calculate_margin_interest(short_amount, holding_days, 0.12)

    logger.info(f"  8%年化费率: {interest_8:>10,.2f} 元 (日均 {interest_8/holding_days:.2f} 元)")
    logger.info(f"  10%年化费率: {interest_10:>10,.2f} 元 (日均 {interest_10/holding_days:.2f} 元)")
    logger.info(f"  12%年化费率: {interest_12:>10,.2f} 元 (日均 {interest_12/holding_days:.2f} 元)")

    # 4. 买券还券成本
    logger.info(f"\n" + "="*80)
    logger.info("4. 买券还券成本（平仓）")
    logger.info("="*80)

    cover_costs = ShortSellingCosts.calculate_buy_to_cover_cost(
        amount=cover_amount,
        stock_code=stock_code,
        commission_rate=0.0003,
        min_commission=5.0,
        stamp_tax_rate=0.001
    )

    logger.info(f"  买入金额: {cover_amount:>10,.0f} 元")
    logger.info(f"  佣金: {cover_costs['commission']:>10,.2f} 元")
    logger.info(f"  印花税: {cover_costs['stamp_tax']:>10,.2f} 元 (有)")
    logger.info(f"  总成本: {cover_costs['total_cost']:>10,.2f} 元")

    # 5. 总盈亏计算
    logger.info(f"\n" + "="*80)
    logger.info("5. 总盈亏计算（10%费率）")
    logger.info("="*80)

    # 价格差收益
    price_pnl = (entry_price - exit_price) * shares

    # 总成本
    total_costs = (
        sell_costs['total_cost'] +
        interest_10 +
        cover_costs['total_cost']
    )

    # 净盈亏
    net_pnl = price_pnl - total_costs
    net_return = (net_pnl / short_amount) * 100

    logger.info(f"\n收益:")
    logger.info(f"  价格差收益: {price_pnl:>10,.2f} 元 ({(price_pnl/short_amount)*100:>6.2f}%)")

    logger.info(f"\n成本:")
    logger.info(f"  开仓成本: {sell_costs['total_cost']:>10,.2f} 元")
    logger.info(f"  融券利息: {interest_10:>10,.2f} 元")
    logger.info(f"  平仓成本: {cover_costs['total_cost']:>10,.2f} 元")
    logger.info(f"  总成本: {total_costs:>10,.2f} 元 ({(total_costs/short_amount)*100:>6.2f}%)")

    logger.info(f"\n净盈亏:")
    logger.info(f"  净盈利: {net_pnl:>10,.2f} 元")
    logger.info(f"  净收益率: {net_return:>10.2f}%")

    # 6. 盈亏平衡分析
    logger.info(f"\n" + "="*80)
    logger.info("6. 盈亏平衡分析")
    logger.info("="*80)

    # 成本占比
    cost_pct = (total_costs / short_amount) * 100

    logger.info(f"  总成本占融券金额: {cost_pct:.2f}%")
    logger.info(f"  盈亏平衡点: 价格需下跌 {cost_pct:.2f}% 以上")
    logger.info(f"  当前价格跌幅: {((entry_price - exit_price)/entry_price)*100:.2f}%")

    breakeven_price = entry_price * (1 - cost_pct / 100)
    logger.info(f"\n  融券价格: {entry_price:.2f} 元")
    logger.info(f"  盈亏平衡价: {breakeven_price:.2f} 元")
    logger.info(f"  当前价格: {exit_price:.2f} 元 ({'盈利' if exit_price < breakeven_price else '亏损'})")

    logger.success("\n✓ 示例4完成\n")


# ==================== 主函数 ====================

def main():
    """运行所有示例"""
    logger.info("\n" + "="*80)
    logger.info("市场中性策略回测示例集")
    logger.info("="*80)

    # 示例1: 基础市场中性策略
    example1_basic_market_neutral()

    # 示例2: 多空对冲降低市场风险
    example2_hedging_market_risk()

    # 示例3: 融券成本敏感性分析
    example3_margin_cost_analysis()

    # 示例4: 实际融券成本计算
    example4_real_world_margin_costs()

    logger.success("\n" + "="*80)
    logger.success("所有示例运行完成！")
    logger.success("="*80)

    logger.info(f"\n总结:")
    logger.info(f"  1. 市场中性策略通过多空对冲实现绝对收益")
    logger.info(f"  2. 融券成本（利息）是重要的成本因素")
    logger.info(f"  3. 费率越高、持仓时间越长，融券成本越高")
    logger.info(f"  4. A股融券费率通常8-12%，显著影响策略收益")
    logger.info(f"  5. 市场中性适合风险规避型、追求绝对收益的投资者")


if __name__ == "__main__":
    main()
