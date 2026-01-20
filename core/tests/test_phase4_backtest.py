#!/usr/bin/env python3
"""
Phase 4 回测引擎测试脚本
测试回测引擎、绩效分析器和持仓管理器功能
"""

import sys
import os
from pathlib import Path
from typing import Tuple
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.backtest.backtest_engine import BacktestEngine
from src.backtest.performance_analyzer import PerformanceAnalyzer
from src.backtest.position_manager import PositionManager, Position

import pandas as pd
import numpy as np


def create_test_market_data(n_days: int = 100, n_stocks: int = 10) -> Tuple:
    """创建测试市场数据"""
    np.random.seed(42)

    dates = pd.date_range('2023-01-01', periods=n_days, freq='D')
    stocks = [f'{600000+i:06d}' for i in range(n_stocks)]

    # 模拟价格数据（随机游走 + 趋势）
    price_data = {}
    signal_data = {}

    for i, stock in enumerate(stocks):
        base_price = 10.0 + i * 0.5
        # 价格有一定趋势
        trend = np.linspace(0, 0.2, n_days)
        returns = np.random.normal(0, 0.015, n_days) + trend / n_days
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

        # 信号与未来5日收益有相关性（模拟预测能力）
        future_returns = pd.Series(prices).pct_change(5).shift(-5)
        signals = future_returns + np.random.normal(0, 0.01, n_days)
        signal_data[stock] = signals.values

    prices_df = pd.DataFrame(price_data, index=dates)
    signals_df = pd.DataFrame(signal_data, index=dates)

    return prices_df, signals_df, stocks


def test_position_manager():
    """测试持仓管理器"""
    print("\n" + "="*60)
    print("测试1: 持仓管理器")
    print("="*60)

    # 创建持仓管理器
    print("\n1.1 初始化持仓管理器")
    manager = PositionManager(
        initial_capital=1000000,
        max_position_pct=0.2,
        max_single_loss_pct=0.05
    )

    print(f"  初始资金: {manager.cash:,.0f}")
    assert manager.cash == 1000000, "初始资金不正确"

    # 添加持仓
    print("\n1.2 添加持仓")
    manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 50)
    manager.add_position('000001', 2000, 15.0, datetime(2023, 1, 2), 75)

    print(f"  持仓数量: {len(manager.positions)}")
    print(f"  剩余现金: {manager.cash:,.0f}")

    assert len(manager.positions) == 2, "持仓数量不正确"
    assert manager.has_position('600000'), "持仓检查失败"

    # 计算总资产
    print("\n1.3 计算总资产")
    current_prices = {'600000': 11.0, '000001': 14.5}
    total_value = manager.calculate_total_value(current_prices)

    print(f"  总资产: {total_value:,.0f}")
    assert total_value > manager.initial_capital * 0.95, "总资产计算异常"

    # 持仓权重
    print("\n1.4 计算持仓权重")
    weights = manager.calculate_position_weights(current_prices)

    for stock, weight in weights.items():
        print(f"  {stock}: {weight*100:.2f}%")

    assert sum(weights.values()) <= 1.0, "权重和超过100%"

    # 卖出持仓
    print("\n1.5 卖出持仓")
    pnl = manager.remove_position('600000', 500, 11.0, 25)

    print(f"  实现盈亏: {pnl:,.0f}")
    print(f"  剩余现金: {manager.cash:,.0f}")

    assert pnl is not None, "盈亏计算失败"

    # 持仓摘要
    print("\n1.6 持仓摘要")
    summary = manager.get_summary(current_prices)

    print(f"  持仓数量: {summary['position_count']}")
    print(f"  总收益率: {summary['total_return']*100:.2f}%")

    print("\n✅ 测试1通过")


def test_performance_analyzer():
    """测试绩效分析器"""
    print("\n" + "="*60)
    print("测试2: 绩效分析器")
    print("="*60)

    # 创建测试收益率
    np.random.seed(42)
    n_days = 252

    strategy_returns = pd.Series(
        np.random.normal(0.001, 0.015, n_days),
        index=pd.date_range('2023-01-01', periods=n_days, freq='D')
    )

    benchmark_returns = pd.Series(
        np.random.normal(0.0005, 0.012, n_days),
        index=pd.date_range('2023-01-01', periods=n_days, freq='D')
    )

    print(f"\n2.1 数据准备:")
    print(f"  交易日数: {n_days}")

    # 创建分析器
    print("\n2.2 创建绩效分析器")
    analyzer = PerformanceAnalyzer(
        returns=strategy_returns,
        benchmark_returns=benchmark_returns,
        risk_free_rate=0.03,
        periods_per_year=252
    )

    # 收益指标
    print("\n2.3 计算收益指标")
    total_return = analyzer.total_return()
    ann_return = analyzer.annualized_return()

    print(f"  总收益率: {total_return*100:.2f}%")
    print(f"  年化收益率: {ann_return*100:.2f}%")

    assert -1 <= total_return <= 10, "总收益率异常"

    # 风险指标
    print("\n2.4 计算风险指标")
    volatility = analyzer.volatility()
    max_dd = analyzer.max_drawdown()

    print(f"  波动率: {volatility*100:.2f}%")
    print(f"  最大回撤: {max_dd*100:.2f}%")

    assert 0 <= volatility <= 1, "波动率异常"
    assert -1 <= max_dd <= 0, "最大回撤异常"

    # 风险调整收益
    print("\n2.5 计算风险调整收益")
    sharpe = analyzer.sharpe_ratio()
    sortino = analyzer.sortino_ratio()

    print(f"  夏普比率: {sharpe:.4f}")
    print(f"  索提诺比率: {sortino:.4f}")

    # 全面分析
    print("\n2.6 全面绩效分析")
    metrics = analyzer.calculate_all_metrics(verbose=False)

    print(f"  计算指标数: {len(metrics)}")

    required_metrics = ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']
    for metric in required_metrics:
        assert metric in metrics, f"缺少指标: {metric}"

    print("\n✅ 测试2通过")


def test_backtest_engine():
    """测试回测引擎"""
    print("\n" + "="*60)
    print("测试3: 回测引擎")
    print("="*60)

    # 创建测试数据
    print("\n3.1 准备市场数据")
    prices_df, signals_df, stocks = create_test_market_data(n_days=100, n_stocks=10)

    print(f"  交易日数: {len(prices_df)}")
    print(f"  股票数量: {len(stocks)}")

    # 创建回测引擎
    print("\n3.2 初始化回测引擎")
    engine = BacktestEngine(
        initial_capital=1000000,
        verbose=False
    )

    print(f"  初始资金: {engine.initial_capital:,.0f}")

    # 运行回测
    print("\n3.3 运行回测")
    results = engine.backtest_long_only(
        signals=signals_df,
        prices=prices_df,
        top_n=5,
        holding_period=5,
        rebalance_freq='W'
    )

    print(f"  回测完成")

    # 检查结果
    print("\n3.4 检查回测结果")
    portfolio_value = results['portfolio_value']
    daily_returns = results['daily_returns']

    print(f"  交易日数: {len(portfolio_value)}")
    print(f"  最终资产: {portfolio_value['total'].iloc[-1]:,.0f}")
    print(f"  总收益率: {(portfolio_value['total'].iloc[-1] / engine.initial_capital - 1) * 100:.2f}%")

    assert len(portfolio_value) == len(prices_df), "回测天数不匹配"
    assert portfolio_value['total'].iloc[-1] > 0, "最终资产为负"

    # 绩效分析
    print("\n3.5 绩效分析")
    analyzer = PerformanceAnalyzer(
        returns=daily_returns,
        risk_free_rate=0.03,
        periods_per_year=252
    )

    metrics = analyzer.calculate_all_metrics(verbose=False)

    print(f"  夏普比率: {metrics['sharpe_ratio']:.4f}")
    print(f"  最大回撤: {metrics['max_drawdown']*100:.2f}%")
    print(f"  胜率: {metrics['win_rate']*100:.2f}%")

    print("\n✅ 测试3通过")


def test_integrated_backtest():
    """测试完整回测流程"""
    print("\n" + "="*60)
    print("测试4: 完整回测流程")
    print("="*60)

    # 创建市场数据
    print("\n4.1 准备数据")
    prices_df, signals_df, stocks = create_test_market_data(n_days=252, n_stocks=20)

    print(f"  时间跨度: 1年 ({len(prices_df)}天)")
    print(f"  股票池: {len(stocks)}只")

    # 回测配置
    backtest_config = {
        'initial_capital': 1000000,
        'top_n': 10,
        'holding_period': 10,
        'rebalance_freq': 'W'
    }

    print(f"\n4.2 回测配置:")
    print(f"  初始资金: {backtest_config['initial_capital']:,.0f}")
    print(f"  选股数量: {backtest_config['top_n']}")
    print(f"  持仓期: {backtest_config['holding_period']}天")
    print(f"  调仓频率: 每周")

    # 运行回测
    print("\n4.3 运行回测")
    engine = BacktestEngine(
        initial_capital=backtest_config['initial_capital'],
        verbose=False
    )

    results = engine.backtest_long_only(
        signals=signals_df,
        prices=prices_df,
        top_n=backtest_config['top_n'],
        holding_period=backtest_config['holding_period'],
        rebalance_freq=backtest_config['rebalance_freq']
    )

    # 绩效分析
    print("\n4.4 绩效分析")
    analyzer = PerformanceAnalyzer(
        returns=results['daily_returns'],
        risk_free_rate=0.03,
        periods_per_year=252
    )

    metrics = analyzer.calculate_all_metrics(verbose=True)

    # 验证关键指标
    print("\n4.5 验证关键指标")
    assert metrics['total_return'] > -0.5, "总收益率过低"
    assert abs(metrics['max_drawdown']) < 0.8, "最大回撤过大"
    assert 0 < metrics['win_rate'] < 1, "胜率异常"

    print("  ✓ 所有指标正常")

    # 输出关键指标
    print(f"\n4.6 关键指标摘要:")
    print(f"  年化收益率: {metrics['annualized_return']*100:.2f}%")
    print(f"  夏普比率: {metrics['sharpe_ratio']:.4f}")
    print(f"  最大回撤: {metrics['max_drawdown']*100:.2f}%")
    print(f"  胜率: {metrics['win_rate']*100:.2f}%")
    print(f"  盈亏比: {metrics['profit_factor']:.2f}")

    print("\n✅ 测试4通过")


def main():
    """运行所有测试"""
    print("\n" + "📊"*30)
    print("Phase 4: 回测引擎测试")
    print("📊"*30)

    try:
        # 运行各项测试
        test_position_manager()
        test_performance_analyzer()
        test_backtest_engine()
        test_integrated_backtest()

        print("\n" + "="*60)
        print("✅ 所有测试通过！Phase 4 回测引擎运行正常")
        print("="*60 + "\n")

        return 0

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
