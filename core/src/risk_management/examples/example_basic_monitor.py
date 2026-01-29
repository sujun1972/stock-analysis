"""
基础风险监控示例

展示如何使用风险监控器进行实时风险管理
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.risk_management import (
    RiskMonitor,
    VaRCalculator,
    DrawdownController,
    PositionSizer
)


def generate_sample_data():
    """生成模拟数据"""
    np.random.seed(42)

    # 1. 生成组合历史收益率（1年数据）
    portfolio_returns = pd.Series(
        np.random.normal(0.001, 0.02, 252),
        index=pd.date_range('2024-01-01', periods=252, freq='D')
    )

    # 2. 生成当前持仓
    positions = {
        '000001': {'shares': 10000, 'cost': 10.0},
        '600000': {'shares': 5000, 'cost': 20.0},
        '000002': {'shares': 8000, 'cost': 15.0},
        '601318': {'shares': 3000, 'cost': 50.0},
        '000858': {'shares': 6000, 'cost': 12.0}
    }

    # 3. 当前价格
    prices = {
        '000001': 11.5,
        '600000': 22.0,
        '000002': 14.5,
        '601318': 55.0,
        '000858': 13.5
    }

    # 4. 计算组合价值
    portfolio_value = sum(
        pos['shares'] * prices.get(stock, 0)
        for stock, pos in positions.items()
    )

    return portfolio_returns, positions, prices, portfolio_value


def example_1_basic_monitoring():
    """示例1：基础风险监控"""
    print("=" * 60)
    print("示例1：基础风险监控")
    print("=" * 60)

    # 1. 生成数据
    portfolio_returns, positions, prices, portfolio_value = generate_sample_data()

    # 2. 配置风险监控器
    config = {
        'max_drawdown': 0.15,       # 最大回撤15%
        'var_confidence': 0.95,      # 95%置信水平
        'max_position_pct': 0.20,    # 单只股票最大20%
        'target_volatility': 0.15    # 目标波动率15%
    }

    # 3. 初始化监控器
    monitor = RiskMonitor(config)

    # 4. 执行监控
    print(f"\n当前组合价值: {portfolio_value:,.2f}")
    print(f"持仓数量: {len(positions)}")

    result = monitor.monitor(
        portfolio_value=portfolio_value,
        portfolio_returns=portfolio_returns,
        positions=positions,
        prices=prices
    )

    # 5. 显示结果
    print(f"\n整体风险等级: {result['overall_risk_level'].upper()}")

    # VaR指标
    if result['risk_metrics'].get('var'):
        var_metrics = result['risk_metrics']['var']
        print("\nVaR指标:")
        print(f"  1日VaR: {var_metrics['var_1day']:.2%}")
        print(f"  5日VaR: {var_metrics['var_5day']:.2%}")
        print(f"  20日VaR: {var_metrics['var_20day']:.2%}")

    # 回撤指标
    if result['risk_metrics'].get('drawdown'):
        dd = result['risk_metrics']['drawdown']
        print("\n回撤指标:")
        print(f"  当前回撤: {dd['current_drawdown']:.2%}")
        print(f"  风险等级: {dd['risk_level']}")

    # 集中度指标
    if result['risk_metrics'].get('concentration'):
        conc = result['risk_metrics']['concentration']
        print("\n集中度指标:")
        print(f"  持仓数量: {conc['n_positions']}")
        print(f"  最大持仓: {conc['max_stock']} ({conc['max_position_pct']:.1%})")
        print(f"  前5集中度: {conc['top5_concentration']:.1%}")

    # 警报
    if result['alerts']:
        print("\n⚠️ 警报:")
        for alert in result['alerts']:
            print(f"  [{alert['level'].upper()}] {alert['message']}")

    # 建议
    print("\n建议:")
    for rec in result['recommendations']:
        print(f"  - {rec}")


def example_2_var_calculation():
    """示例2：VaR计算"""
    print("\n" + "=" * 60)
    print("示例2：VaR计算")
    print("=" * 60)

    # 生成数据
    portfolio_returns, _, _, _ = generate_sample_data()

    # 初始化VaR计算器
    var_calc = VaRCalculator(confidence_level=0.95)

    # 方法1：历史模拟法
    print("\n1. 历史模拟法:")
    result_hist = var_calc.calculate_historical_var(portfolio_returns, holding_period=1)
    print(f"   VaR: {result_hist['var']:.2%}")
    print(f"   CVaR: {result_hist['cvar']:.2%}")

    # 方法2：参数法
    print("\n2. 参数法（正态分布假设）:")
    result_param = var_calc.calculate_parametric_var(portfolio_returns, holding_period=1)
    print(f"   VaR: {result_param['var']:.2%}")
    print(f"   CVaR: {result_param['cvar']:.2%}")

    # 方法3：蒙特卡洛模拟
    print("\n3. 蒙特卡洛模拟:")
    result_mc = var_calc.calculate_monte_carlo_var(
        portfolio_returns,
        holding_period=1,
        n_simulations=10000
    )
    print(f"   VaR: {result_mc['var']:.2%}")
    print(f"   CVaR: {result_mc['cvar']:.2%}")

    # 比较不同方法
    print("\n4. 方法比较:")
    comparison = var_calc.compare_methods(portfolio_returns, holding_period=1)
    print(comparison.to_string(index=False))


def example_3_drawdown_control():
    """示例3：回撤控制"""
    print("\n" + "=" * 60)
    print("示例3：回撤控制")
    print("=" * 60)

    # 初始化回撤控制器
    controller = DrawdownController(
        max_drawdown=0.15,
        warning_threshold=0.80,
        alert_threshold=0.60
    )

    # 模拟组合价值变化
    print("\n模拟组合价值变化:")
    values = [1000000, 1050000, 1020000, 950000, 900000, 870000, 850000]

    for i, value in enumerate(values):
        result = controller.update(value)

        print(f"\nDay {i+1}: {value:,.0f}")
        print(f"  回撤: {result['current_drawdown']:.2%}")
        print(f"  风险等级: {result['risk_level']}")
        print(f"  建议动作: {result['action']}")

        if result['risk_level'] in ['warning', 'critical']:
            print(f"  ⚠️ {result['message']}")


def example_4_position_sizing():
    """示例4：仓位计算"""
    print("\n" + "=" * 60)
    print("示例4：仓位计算")
    print("=" * 60)

    sizer = PositionSizer()

    # 1. 等权重
    print("\n1. 等权重分配（5只股票）:")
    weights = sizer.calculate_equal_weight(5, max_position=0.25)
    for stock, weight in weights.items():
        print(f"   {stock}: {weight:.1%}")

    # 2. 凯利公式
    print("\n2. 凯利公式仓位:")
    print("   假设：胜率60%，平均赚3%，平均亏2%")
    kelly_pos = sizer.calculate_kelly_position(
        win_rate=0.6,
        avg_win=0.03,
        avg_loss=0.02,
        fractional_kelly=0.5
    )
    print(f"   建议仓位: {kelly_pos:.1%}")

    # 3. 风险平价
    print("\n3. 风险平价权重:")
    np.random.seed(42)
    returns_df = pd.DataFrame({
        'stock_A': np.random.normal(0.001, 0.02, 100),
        'stock_B': np.random.normal(0.0015, 0.03, 100),
        'stock_C': np.random.normal(0.0008, 0.015, 100)
    })

    rp_weights = sizer.calculate_risk_parity_weights(returns_df)
    for stock, weight in rp_weights.items():
        vol = returns_df[stock].std() * np.sqrt(252)
        print(f"   {stock}: {weight:.1%} (波动率: {vol:.1%})")

    # 4. 波动率目标
    print("\n4. 波动率目标调整:")
    scenarios = [
        (0.10, "波动率低"),
        (0.15, "波动率正常"),
        (0.20, "波动率高"),
        (0.30, "波动率很高")
    ]

    for vol, desc in scenarios:
        new_pos = sizer.calculate_volatility_target_position(
            current_volatility=vol,
            target_volatility=0.15,
            current_position=1.0
        )
        print(f"   {desc}({vol:.0%}): 建议仓位 {new_pos:.0%}")


def example_5_comprehensive_report():
    """示例5：综合风险报告"""
    print("\n" + "=" * 60)
    print("示例5：综合风险报告")
    print("=" * 60)

    # 生成数据
    portfolio_returns, positions, prices, portfolio_value = generate_sample_data()

    # 配置监控器
    config = {
        'max_drawdown': 0.15,
        'var_confidence': 0.95,
        'max_position_pct': 0.20,
        'target_volatility': 0.15
    }

    monitor = RiskMonitor(config)

    # 生成文本报告
    report = monitor.get_risk_report(
        portfolio_value, portfolio_returns, positions, prices
    )

    print("\n" + report)


if __name__ == '__main__':
    # 运行所有示例
    example_1_basic_monitoring()
    example_2_var_calculation()
    example_3_drawdown_control()
    example_4_position_sizing()
    example_5_comprehensive_report()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)
