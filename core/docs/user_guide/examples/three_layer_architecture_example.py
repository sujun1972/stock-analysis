"""
三层架构基类使用示例

本文件演示如何使用三层架构基类创建具体的策略实现。

这是一个最小示例，展示了基类的使用方法。
完整的策略实现将在任务 T2-T4 中完成。
"""

from typing import Any, Dict, List
import pandas as pd
from src.strategies.three_layer import (
    StockSelector,
    EntryStrategy,
    ExitStrategy,
    StrategyComposer,
    SelectorParameter,
    Position,
)


# ============================================================================
# 示例 1: 简单的选股器实现
# ============================================================================

class SimpleTopNSelector(StockSelector):
    """简单的 Top N 选股器示例"""

    @property
    def name(self) -> str:
        return "简单 Top N 选股器"

    @property
    def id(self) -> str:
        return "simple_top_n"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="top_n",
                label="选股数量",
                type="integer",
                default=10,
                min_value=1,
                max_value=100,
                description="选择前 N 只股票"
            )
        ]

    def select(self, date: pd.Timestamp, market_data: pd.DataFrame) -> List[str]:
        """选择当日收盘价最高的前 N 只股票"""
        top_n = self.params.get("top_n", 10)

        try:
            current_prices = market_data.loc[date].dropna()
            selected = current_prices.nlargest(top_n).index.tolist()
            print(f"[{date.date()}] 选股完成: {len(selected)} 只股票")
            return selected
        except KeyError:
            print(f"[{date.date()}] 数据不存在，返回空列表")
            return []


# ============================================================================
# 示例 2: 简单的入场策略实现
# ============================================================================

class SimpleImmediateEntry(EntryStrategy):
    """简单的立即入场策略示例"""

    @property
    def name(self) -> str:
        return "简单立即入场"

    @property
    def id(self) -> str:
        return "simple_immediate"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "max_positions",
                "label": "最大持仓数",
                "type": "integer",
                "default": 5,
                "min": 1,
                "max": 50,
                "description": "最多同时持有的股票数量"
            }
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """对所有候选股票生成等权买入信号"""
        max_positions = self.params.get("max_positions", 5)

        # 限制持仓数量
        selected_stocks = stocks[:max_positions]

        if selected_stocks:
            weight = 1.0 / len(selected_stocks)
            signals = {stock: weight for stock in selected_stocks}
            print(f"[{date.date()}] 入场信号: {len(signals)} 只股票，每只权重 {weight:.2%}")
            return signals
        else:
            return {}


# ============================================================================
# 示例 3: 简单的退出策略实现
# ============================================================================

class SimpleFixedStopLossExit(ExitStrategy):
    """简单的固定止损退出策略示例"""

    @property
    def name(self) -> str:
        return "简单固定止损"

    @property
    def id(self) -> str:
        return "simple_fixed_stop"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "stop_loss_pct",
                "label": "止损百分比",
                "type": "float",
                "default": -5.0,
                "min": -20.0,
                "max": -1.0,
                "description": "亏损达到此百分比时卖出"
            }
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """检查止损条件"""
        exit_stocks = []
        stop_loss_pct = self.params.get("stop_loss_pct", -5.0)

        for stock, position in positions.items():
            if position.unrealized_pnl_pct <= stop_loss_pct:
                exit_stocks.append(stock)
                print(
                    f"[{date.date()}] {stock} 触发止损: "
                    f"{position.unrealized_pnl_pct:.2f}% <= {stop_loss_pct:.2f}%"
                )

        return exit_stocks


# ============================================================================
# 示例 4: 使用策略组合器
# ============================================================================

def demo_strategy_composer():
    """演示策略组合器的使用"""
    print("\n" + "="*70)
    print("三层架构策略组合器演示")
    print("="*70 + "\n")

    # 创建三层策略
    selector = SimpleTopNSelector(params={'top_n': 20})
    entry = SimpleImmediateEntry(params={'max_positions': 10})
    exit_strategy = SimpleFixedStopLossExit(params={'stop_loss_pct': -5.0})

    # 组合策略
    composer = StrategyComposer(
        selector=selector,
        entry=entry,
        exit_strategy=exit_strategy,
        rebalance_freq='W'
    )

    print("1. 策略组合信息")
    print("-" * 70)
    print(f"组合名称: {composer.get_strategy_combination_name()}")
    print(f"组合ID: {composer.get_strategy_combination_id()}")
    print()

    print("2. 策略元数据")
    print("-" * 70)
    metadata = composer.get_metadata()
    print(f"选股器: {metadata['selector']['name']} (ID: {metadata['selector']['id']})")
    print(f"  参数: {metadata['selector']['current_params']}")
    print(f"入场策略: {metadata['entry']['name']} (ID: {metadata['entry']['id']})")
    print(f"  参数: {metadata['entry']['current_params']}")
    print(f"退出策略: {metadata['exit']['name']} (ID: {metadata['exit']['id']})")
    print(f"  参数: {metadata['exit']['current_params']}")
    print(f"选股频率: {metadata['rebalance_freq']}")
    print()

    print("3. 验证策略组合")
    print("-" * 70)
    validation = composer.validate()
    if validation['valid']:
        print("✅ 策略组合有效")
    else:
        print("❌ 策略组合无效:")
        for error in validation['errors']:
            print(f"  - {error}")
    print()

    print("4. 所有参数")
    print("-" * 70)
    all_params = composer.get_all_parameters()
    for key, value in all_params.items():
        print(f"{key}: {value}")
    print()


# ============================================================================
# 示例 5: 参数验证演示
# ============================================================================

def demo_parameter_validation():
    """演示参数验证功能"""
    print("\n" + "="*70)
    print("参数验证演示")
    print("="*70 + "\n")

    print("1. 正确的参数")
    print("-" * 70)
    try:
        selector = SimpleTopNSelector(params={'top_n': 50})
        print(f"✅ 创建成功: {selector}")
    except ValueError as e:
        print(f"❌ 创建失败: {e}")
    print()

    print("2. 参数超出范围")
    print("-" * 70)
    try:
        selector = SimpleTopNSelector(params={'top_n': 500})  # 超过最大值100
        print(f"✅ 创建成功: {selector}")
    except ValueError as e:
        print(f"❌ 创建失败: {e}")
    print()

    print("3. 未知参数")
    print("-" * 70)
    try:
        selector = SimpleTopNSelector(params={'unknown_param': 123})
        print(f"✅ 创建成功: {selector}")
    except ValueError as e:
        print(f"❌ 创建失败: {e}")
    print()

    print("4. 错误的参数类型")
    print("-" * 70)
    try:
        selector = SimpleTopNSelector(params={'top_n': "50"})  # 应该是整数
        print(f"✅ 创建成功: {selector}")
    except ValueError as e:
        print(f"❌ 创建失败: {e}")
    print()


# ============================================================================
# 主函数
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Core v3.0 三层架构基类使用示例")
    print("="*70)

    # 演示策略组合器
    demo_strategy_composer()

    # 演示参数验证
    demo_parameter_validation()

    print("\n" + "="*70)
    print("演示完成")
    print("="*70 + "\n")
    print("注意：")
    print("  - 这只是基类的使用示例")
    print("  - 完整的策略实现将在任务 T2-T4 中完成")
    print("  - MomentumSelector, MABreakoutEntry, ATRStopLossExit 等将在后续实现")
    print()
