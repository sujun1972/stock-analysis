"""
ML策略回测示例 - 使用离场策略

演示如何使用 MLEntry + CompositeExitManager 进行回测

功能：
- ML模型入场策略
- 多种离场策略组合：止损、止盈、移动止损、持仓时长
- 反向入场离场（持有多头时出现做空信号）
- 风控离场

版本: v1.0.0
创建时间: 2026-02-13
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime
from loguru import logger

from src.backtest.backtest_engine import BacktestEngine
from src.ml.ml_entry import MLEntry
from src.ml.exit_strategy import (
    CompositeExitManager,
    StopLossExitStrategy,
    TakeProfitExitStrategy,
    TrailingStopExitStrategy,
    HoldingPeriodExitStrategy,
    create_default_exit_manager,
    create_conservative_exit_manager,
    create_aggressive_exit_manager
)


def generate_mock_market_data(
    stock_pool: list,
    start_date: str,
    end_date: str
) -> pd.DataFrame:
    """
    生成模拟市场数据（用于演示）

    实际使用时应该从数据库或数据源读取真实数据
    """
    dates = pd.date_range(start_date, end_date, freq='D')

    data = []
    for stock in stock_pool:
        base_price = np.random.uniform(10, 50)

        for date in dates:
            # 模拟价格波动
            noise = np.random.randn() * 0.02
            close = base_price * (1 + noise)

            data.append({
                'date': date,
                'stock_code': stock,
                'open': close * 0.99,
                'high': close * 1.01,
                'low': close * 0.98,
                'close': close,
                'volume': np.random.uniform(1000000, 10000000)
            })

            base_price = close  # 使用当前收盘价作为下一天的基准

    return pd.DataFrame(data)


def example_1_default_exit():
    """
    示例1: 使用默认离场管理器

    配置：
    - 止损 10%
    - 止盈 20%
    - 移动止损 5%
    - 最大持仓期 30天
    """
    logger.info("=" * 60)
    logger.info("示例1: 使用默认离场管理器")
    logger.info("=" * 60)

    # 准备数据
    stock_pool = ['600000.SH', '000001.SZ', '000002.SZ', '600036.SH', '601398.SH']
    start_date = '2024-01-01'
    end_date = '2024-03-31'

    market_data = generate_mock_market_data(stock_pool, start_date, end_date)

    # 注意：这里需要真实的训练好的模型
    # model_path = 'path/to/your/trained_model.pkl'
    # ml_entry = MLEntry(
    #     model_path=model_path,
    #     confidence_threshold=0.7,
    #     top_long=10,
    #     top_short=5,
    #     enable_short=True
    # )

    # 这里为了演示，假设我们已经有了 ml_entry 对象
    logger.warning("注意：需要提供真实的训练好的模型才能运行")
    logger.info("示例代码结构：")
    logger.info("  1. 创建 MLEntry 入场策略")
    logger.info("  2. 创建默认离场管理器")
    logger.info("  3. 运行回测")

    # 创建默认离场管理器
    exit_manager = create_default_exit_manager()

    logger.info(f"\n离场管理器配置:")
    summary = exit_manager.get_summary()
    logger.info(f"  策略数量: {summary['n_strategies']}")
    for s in summary['strategies']:
        logger.info(f"    - {s['name']} (优先级={s['priority']})")
    logger.info(f"  反向入场离场: {'启用' if summary['enable_reverse_entry'] else '禁用'}")
    logger.info(f"  风控离场: {'启用' if summary['enable_risk_control'] else '禁用'}")

    # 回测
    # engine = BacktestEngine(initial_capital=1000000)
    # result = engine.backtest_ml_strategy(
    #     ml_entry=ml_entry,
    #     stock_pool=stock_pool,
    #     market_data=market_data,
    #     start_date=start_date,
    #     end_date=end_date,
    #     rebalance_freq='W',
    #     exit_manager=exit_manager  # 传入离场管理器
    # )

    logger.success("✓ 示例1完成\n")


def example_2_custom_exit():
    """
    示例2: 自定义离场策略

    配置：
    - 严格止损 5%
    - 快速止盈 15%
    - 紧密移动止损 3%
    - 短期持仓 15天
    """
    logger.info("=" * 60)
    logger.info("示例2: 自定义离场策略组合")
    logger.info("=" * 60)

    # 创建自定义离场策略
    custom_strategies = [
        StopLossExitStrategy(stop_loss_pct=0.05, priority=10),       # 5%止损
        TakeProfitExitStrategy(take_profit_pct=0.15, priority=8),     # 15%止盈
        TrailingStopExitStrategy(trailing_stop_pct=0.03, priority=9), # 3%移动止损
        HoldingPeriodExitStrategy(max_holding_days=15, priority=3)    # 15天最大持仓
    ]

    exit_manager = CompositeExitManager(
        exit_strategies=custom_strategies,
        enable_reverse_entry=True,   # 启用反向入场离场
        enable_risk_control=True     # 启用风控离场
    )

    logger.info("自定义离场策略配置:")
    summary = exit_manager.get_summary()
    for s in summary['strategies']:
        logger.info(f"  - {s['name']} (优先级={s['priority']}, 类={s['class']})")

    logger.success("✓ 示例2完成\n")


def example_3_conservative_vs_aggressive():
    """
    示例3: 保守型 vs 激进型离场策略对比
    """
    logger.info("=" * 60)
    logger.info("示例3: 保守型 vs 激进型离场策略对比")
    logger.info("=" * 60)

    # 保守型
    conservative = create_conservative_exit_manager()
    logger.info("\n保守型离场策略:")
    for s in conservative.get_summary()['strategies']:
        logger.info(f"  - {s['name']} (优先级={s['priority']})")

    # 激进型
    aggressive = create_aggressive_exit_manager()
    logger.info("\n激进型离场策略:")
    for s in aggressive.get_summary()['strategies']:
        logger.info(f"  - {s['name']} (优先级={s['priority']})")

    logger.info("\n对比说明:")
    logger.info("  保守型: 更严格的止损(5%), 更快的止盈(15%), 更短的持仓期(20天)")
    logger.info("  激进型: 更宽松的止损(15%), 更高的止盈(30%), 更长的持仓期(60天)")

    logger.success("✓ 示例3完成\n")


def example_4_only_reverse_entry_exit():
    """
    示例4: 只使用反向入场离场（不使用其他离场策略）
    """
    logger.info("=" * 60)
    logger.info("示例4: 只使用反向入场离场")
    logger.info("=" * 60)

    # 创建空策略列表，只依赖反向入场
    exit_manager = CompositeExitManager(
        exit_strategies=[],              # 不使用任何主动离场策略
        enable_reverse_entry=True,       # 只启用反向入场离场
        enable_risk_control=False        # 不启用风控离场
    )

    logger.info("离场策略配置:")
    logger.info("  - 无主动离场策略")
    logger.info("  - 反向入场离场: 启用")
    logger.info("  - 风控离场: 禁用")
    logger.info("\n说明:")
    logger.info("  在这种配置下，只有当持有多头时出现做空信号（或持有空头时出现做多信号）")
    logger.info("  才会触发离场。这种策略完全依赖模型信号的方向性。")

    logger.success("✓ 示例4完成\n")


def example_5_no_exit_manager():
    """
    示例5: 不使用离场管理器（传统调仓式回测）
    """
    logger.info("=" * 60)
    logger.info("示例5: 不使用离场管理器（对比）")
    logger.info("=" * 60)

    logger.info("如果不传入 exit_manager 参数:")
    logger.info("  engine.backtest_ml_strategy(")
    logger.info("      ml_entry=ml_entry,")
    logger.info("      ...,")
    logger.info("      exit_manager=None  # 不使用离场管理器")
    logger.info("  )")
    logger.info("\n行为:")
    logger.info("  - 回测将使用传统的调仓式策略")
    logger.info("  - 每次调仓日，平掉不在新信号中的持仓")
    logger.info("  - 无法实现灵活的止盈止损")
    logger.info("  - 只能在固定的调仓日进行买卖")

    logger.success("✓ 示例5完成\n")


def example_6_exit_signal_priorities():
    """
    示例6: 离场信号优先级说明
    """
    logger.info("=" * 60)
    logger.info("示例6: 离场信号优先级机制")
    logger.info("=" * 60)

    logger.info("优先级规则（数字越大优先级越高）:")
    logger.info("  11 - 反向入场（最高优先级）")
    logger.info("  10 - 止损（风控）")
    logger.info("   9 - 移动止损（风控）")
    logger.info("   8 - 止盈")
    logger.info("   3 - 持仓时长")
    logger.info("\n执行顺序:")
    logger.info("  1. 如果检测到反向入场，立即离场，不再检查其他策略")
    logger.info("  2. 否则，按优先级从高到低检查各离场策略")
    logger.info("  3. 如果某个策略优先级≥8（风控级别），触发后立即离场")
    logger.info("  4. 否则，继续检查其他策略，最终选择优先级最高的")

    logger.info("\n示例场景:")
    logger.info("  股票A:")
    logger.info("    - 亏损12% → 触发止损（优先级10）")
    logger.info("    - 持仓35天 → 触发持仓时长（优先级3）")
    logger.info("    → 最终选择: 止损离场（优先级更高且≥8）")

    logger.success("✓ 示例6完成\n")


def main():
    """运行所有示例"""
    logger.info("\n" + "=" * 60)
    logger.info("ML策略回测 - 离场策略使用示例")
    logger.info("=" * 60 + "\n")

    example_1_default_exit()
    example_2_custom_exit()
    example_3_conservative_vs_aggressive()
    example_4_only_reverse_entry_exit()
    example_5_no_exit_manager()
    example_6_exit_signal_priorities()

    logger.info("=" * 60)
    logger.info("所有示例运行完成!")
    logger.info("=" * 60)
    logger.info("\n完整使用流程:")
    logger.info("  1. 训练ML模型 → 保存为 .pkl 文件")
    logger.info("  2. 创建 MLEntry 入场策略")
    logger.info("  3. 创建/选择离场管理器")
    logger.info("  4. 运行回测 backtest_ml_strategy()")
    logger.info("  5. 分析回测结果和离场统计")
    logger.info("\n关键参数:")
    logger.info("  - enable_reverse_entry: 是否启用反向入场离场")
    logger.info("  - enable_risk_control: 是否启用风控离场（止损/止盈）")
    logger.info("  - exit_strategies: 自定义离场策略列表")


if __name__ == "__main__":
    main()
