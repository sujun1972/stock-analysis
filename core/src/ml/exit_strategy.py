"""
离场策略模块 (Exit Strategy Module)

提供完整的离场策略框架，支持多种离场触发机制和优先级管理。

## 核心概念

### 三层离场触发机制
1. **反向入场离场** (priority=11): 持有多头时出现做空信号，或持有空头时出现做多信号
2. **风险控制离场** (priority=8-10): 止损、移动止损等风控策略
3. **策略信号离场** (priority=3-7): 止盈、持仓时长等主动策略

### 优先级规则
- 数字越大优先级越高
- 当多个离场信号同时触发时，选择优先级最高的
- 反向入场 > 止损 > 移动止损 > 止盈 > 持仓时长

## 使用示例

```python
from src.ml.exit_strategy import (
    CompositeExitManager,
    StopLossExitStrategy,
    TakeProfitExitStrategy
)

# 创建组合离场管理器
exit_manager = CompositeExitManager([
    StopLossExitStrategy(stop_loss_pct=0.10, priority=10),
    TakeProfitExitStrategy(take_profit_pct=0.20, priority=8)
])

# 在回测中使用
result = engine.backtest_long_only(
    signals=signals,
    prices=prices,
    exit_manager=exit_manager
)
```

版本: v1.0.0
创建时间: 2026-02-13
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger


@dataclass
class ExitSignal:
    """
    离场信号数据类

    属性:
        stock_code: 股票代码
        reason: 离场原因 ('strategy', 'reverse_entry', 'risk_control')
        trigger: 具体触发条件 (如 'stop_loss', 'take_profit', 'holding_period')
        priority: 优先级 (1-10, 数字越大优先级越高)
        metadata: 附加元数据
    """
    stock_code: str
    reason: str  # 'strategy', 'reverse_entry', 'risk_control'
    trigger: str
    priority: int = 5
    metadata: Optional[Dict] = None

    def __repr__(self) -> str:
        return (
            f"ExitSignal({self.stock_code}, "
            f"reason={self.reason}, trigger={self.trigger}, "
            f"priority={self.priority})"
        )


class BaseExitStrategy(ABC):
    """
    离场策略基类

    所有离场策略必须继承此类并实现 should_exit() 方法
    """

    def __init__(self, name: str, priority: int = 5):
        """
        初始化离场策略

        Args:
            name: 策略名称
            priority: 优先级 (1-10)
        """
        self.name = name
        self.priority = priority

    @abstractmethod
    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """
        判断是否应该离场

        Args:
            position: 持仓信息
                {
                    'stock_code': str,
                    'shares': int,
                    'entry_price': float,
                    'entry_date': datetime,
                    'current_price': float,
                    'unrealized_pnl_pct': float
                }
            current_price: 当前价格
            current_date: 当前日期
            market_data: 市场数据（可选）

        Returns:
            ExitSignal if should exit, None otherwise
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', priority={self.priority})"


class StopLossExitStrategy(BaseExitStrategy):
    """
    止损离场策略

    当亏损超过阈值时触发离场
    """

    def __init__(self, stop_loss_pct: float = 0.10, priority: int = 10):
        """
        初始化

        Args:
            stop_loss_pct: 止损比例 (默认10%)
            priority: 优先级 (止损优先级最高，默认10)
        """
        super().__init__(name='StopLoss', priority=priority)
        self.stop_loss_pct = stop_loss_pct

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """止损检查"""
        pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        if pnl_pct < -self.stop_loss_pct:
            return ExitSignal(
                stock_code=position['stock_code'],
                reason='risk_control',
                trigger='stop_loss',
                priority=self.priority,
                metadata={
                    'stop_loss_pct': self.stop_loss_pct,
                    'actual_loss_pct': pnl_pct,
                    'entry_price': position['entry_price'],
                    'current_price': current_price
                }
            )

        return None


class TakeProfitExitStrategy(BaseExitStrategy):
    """
    止盈离场策略

    当盈利达到目标时触发离场
    """

    def __init__(self, take_profit_pct: float = 0.20, priority: int = 8):
        """
        初始化

        Args:
            take_profit_pct: 止盈比例 (默认20%)
            priority: 优先级
        """
        super().__init__(name='TakeProfit', priority=priority)
        self.take_profit_pct = take_profit_pct

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """止盈检查"""
        pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        if pnl_pct > self.take_profit_pct:
            return ExitSignal(
                stock_code=position['stock_code'],
                reason='strategy',
                trigger='take_profit',
                priority=self.priority,
                metadata={
                    'take_profit_pct': self.take_profit_pct,
                    'actual_profit_pct': pnl_pct,
                    'entry_price': position['entry_price'],
                    'current_price': current_price
                }
            )

        return None


class HoldingPeriodExitStrategy(BaseExitStrategy):
    """
    持仓时长离场策略

    当持仓天数达到上限时触发离场
    """

    def __init__(self, max_holding_days: int = 30, priority: int = 3):
        """
        初始化

        Args:
            max_holding_days: 最大持仓天数
            priority: 优先级
        """
        super().__init__(name='HoldingPeriod', priority=priority)
        self.max_holding_days = max_holding_days

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """持仓时长检查"""
        entry_date = position.get('entry_date')

        if entry_date is None:
            return None

        # 计算持仓天数
        if isinstance(entry_date, str):
            entry_date = pd.to_datetime(entry_date)
        if isinstance(current_date, str):
            current_date = pd.to_datetime(current_date)

        holding_days = (current_date - entry_date).days

        if holding_days >= self.max_holding_days:
            return ExitSignal(
                stock_code=position['stock_code'],
                reason='strategy',
                trigger='max_holding_period',
                priority=self.priority,
                metadata={
                    'max_holding_days': self.max_holding_days,
                    'actual_holding_days': holding_days,
                    'entry_date': entry_date,
                    'current_date': current_date
                }
            )

        return None


class TrailingStopExitStrategy(BaseExitStrategy):
    """
    移动止损离场策略

    跟踪最高价，当回撤超过阈值时触发离场
    """

    def __init__(self, trailing_stop_pct: float = 0.05, priority: int = 9):
        """
        初始化

        Args:
            trailing_stop_pct: 移动止损比例 (从最高点回撤，默认5%)
            priority: 优先级
        """
        super().__init__(name='TrailingStop', priority=priority)
        self.trailing_stop_pct = trailing_stop_pct

        # 记录每只股票的最高价
        self.peak_prices: Dict[str, float] = {}

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """移动止损检查"""
        stock_code = position['stock_code']
        entry_price = position['entry_price']

        # 更新最高价
        if stock_code not in self.peak_prices:
            self.peak_prices[stock_code] = max(entry_price, current_price)
        else:
            self.peak_prices[stock_code] = max(self.peak_prices[stock_code], current_price)

        peak_price = self.peak_prices[stock_code]

        # 计算从最高点的回撤
        drawdown_from_peak = (current_price - peak_price) / peak_price

        if drawdown_from_peak < -self.trailing_stop_pct:
            return ExitSignal(
                stock_code=stock_code,
                reason='risk_control',
                trigger='trailing_stop',
                priority=self.priority,
                metadata={
                    'trailing_stop_pct': self.trailing_stop_pct,
                    'drawdown_from_peak': drawdown_from_peak,
                    'peak_price': peak_price,
                    'current_price': current_price,
                    'entry_price': entry_price
                }
            )

        return None

    def reset_stock(self, stock_code: str):
        """重置某只股票的记录（离场后调用）"""
        if stock_code in self.peak_prices:
            del self.peak_prices[stock_code]


class CompositeExitManager:
    """
    复合离场管理器

    整合多个离场策略，并处理三种离场触发条件：
    1. 策略离场（技术指标等）
    2. 反向入场（持有多头时出现做空信号）
    3. 风控止损（止盈止损等）
    """

    def __init__(
        self,
        exit_strategies: Optional[List[BaseExitStrategy]] = None,
        enable_reverse_entry: bool = True,
        enable_risk_control: bool = True
    ):
        """
        初始化

        Args:
            exit_strategies: 离场策略列表
            enable_reverse_entry: 是否启用反向入场离场
            enable_risk_control: 是否启用风控离场
        """
        self.exit_strategies = exit_strategies or []
        self.enable_reverse_entry = enable_reverse_entry
        self.enable_risk_control = enable_risk_control

        # 按优先级排序
        self.exit_strategies.sort(key=lambda s: s.priority, reverse=True)

        logger.info(
            f"离场管理器初始化: {len(self.exit_strategies)} 个策略, "
            f"反向入场={'启用' if enable_reverse_entry else '禁用'}, "
            f"风控={'启用' if enable_risk_control else '禁用'}"
        )

    def add_strategy(self, strategy: BaseExitStrategy):
        """添加离场策略"""
        self.exit_strategies.append(strategy)
        self.exit_strategies.sort(key=lambda s: s.priority, reverse=True)
        logger.info(f"添加离场策略: {strategy}")

    def check_exit(
        self,
        positions: Dict[str, Dict],
        current_prices: Dict[str, float],
        current_date: datetime,
        entry_signals: Optional[Dict[str, Dict]] = None,
        market_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, ExitSignal]:
        """
        检查所有持仓，返回需要离场的股票

        Args:
            positions: 持仓字典
                {
                    'stock_code': {
                        'shares': int,
                        'entry_price': float,
                        'entry_date': datetime,
                        'current_price': float,
                        'unrealized_pnl_pct': float
                    }
                }
            current_prices: 当前价格字典 {stock_code: price}
            current_date: 当前日期
            entry_signals: 入场信号字典 (用于检测反向入场)
                {
                    'stock_code': {
                        'action': 'long' or 'short',
                        'weight': float
                    }
                }
            market_data: 市场数据

        Returns:
            需要离场的股票字典 {stock_code: ExitSignal}
        """
        exit_signals: Dict[str, ExitSignal] = {}

        for stock_code, position in positions.items():
            current_price = current_prices.get(stock_code)

            if current_price is None or current_price <= 0:
                logger.warning(f"{stock_code}: 当前价格无效，跳过离场检查")
                continue

            # 更新持仓信息
            position_with_price = position.copy()
            position_with_price['current_price'] = current_price

            # 计算未实现盈亏
            if 'unrealized_pnl_pct' not in position_with_price:
                entry_price = position.get('entry_price', current_price)
                position_with_price['unrealized_pnl_pct'] = (
                    (current_price - entry_price) / entry_price
                    if entry_price > 0 else 0.0
                )

            # 1. 检查反向入场离场（最高优先级）
            if self.enable_reverse_entry and entry_signals:
                reverse_signal = self._check_reverse_entry(
                    stock_code, position_with_price, entry_signals
                )
                if reverse_signal:
                    exit_signals[stock_code] = reverse_signal
                    continue  # 反向入场优先级最高，直接离场

            # 2. 检查各离场策略
            for strategy in self.exit_strategies:
                # 风控策略检查
                if not self.enable_risk_control and strategy.priority >= 8:
                    continue

                signal = strategy.should_exit(
                    position_with_price,
                    current_price,
                    current_date,
                    market_data
                )

                if signal:
                    # 如果已有信号，比较优先级
                    if stock_code in exit_signals:
                        if signal.priority > exit_signals[stock_code].priority:
                            exit_signals[stock_code] = signal
                    else:
                        exit_signals[stock_code] = signal

                    # 如果是高优先级信号（≥8），立即触发
                    if signal.priority >= 8:
                        break

        if exit_signals:
            logger.info(f"检测到 {len(exit_signals)} 个离场信号")
            for stock, signal in exit_signals.items():
                logger.debug(f"  {stock}: {signal.trigger} (优先级={signal.priority})")

        return exit_signals

    def _check_reverse_entry(
        self,
        stock_code: str,
        position: Dict,
        entry_signals: Dict[str, Dict]
    ) -> Optional[ExitSignal]:
        """
        检查反向入场离场

        规则：
        - 持有多头时，出现做空信号 → 离场
        - 持有空头时，出现做多信号 → 离场

        Args:
            stock_code: 股票代码
            position: 持仓信息
            entry_signals: 入场信号字典

        Returns:
            ExitSignal if reverse entry detected, None otherwise
        """
        if stock_code not in entry_signals:
            return None

        entry_signal = entry_signals[stock_code]
        entry_action = entry_signal.get('action')

        # 判断持仓类型（假设都是多头，如果有空头需要额外字段）
        position_type = position.get('position_type', 'long')

        # 多头持仓 + 做空信号 = 离场
        if position_type == 'long' and entry_action == 'short':
            return ExitSignal(
                stock_code=stock_code,
                reason='reverse_entry',
                trigger='short_signal_on_long_position',
                priority=11,  # 反向入场优先级最高
                metadata={
                    'position_type': position_type,
                    'reverse_action': entry_action,
                    'entry_weight': entry_signal.get('weight', 0)
                }
            )

        # 空头持仓 + 做多信号 = 离场
        if position_type == 'short' and entry_action == 'long':
            return ExitSignal(
                stock_code=stock_code,
                reason='reverse_entry',
                trigger='long_signal_on_short_position',
                priority=11,
                metadata={
                    'position_type': position_type,
                    'reverse_action': entry_action,
                    'entry_weight': entry_signal.get('weight', 0)
                }
            )

        return None

    def on_position_closed(self, stock_code: str):
        """
        持仓关闭时的清理工作

        某些策略（如移动止损）需要重置状态
        """
        for strategy in self.exit_strategies:
            if hasattr(strategy, 'reset_stock'):
                strategy.reset_stock(stock_code)

    def get_summary(self) -> Dict:
        """获取离场管理器摘要"""
        return {
            'n_strategies': len(self.exit_strategies),
            'strategies': [
                {
                    'name': s.name,
                    'class': s.__class__.__name__,
                    'priority': s.priority
                }
                for s in self.exit_strategies
            ],
            'enable_reverse_entry': self.enable_reverse_entry,
            'enable_risk_control': self.enable_risk_control
        }


# ==================== 预定义配置 ====================

def create_default_exit_manager() -> CompositeExitManager:
    """
    创建默认离场管理器

    包含：
    - 止损 10%
    - 止盈 20%
    - 移动止损 5%
    - 最大持仓期 30天
    """
    strategies = [
        StopLossExitStrategy(stop_loss_pct=0.10, priority=10),
        TakeProfitExitStrategy(take_profit_pct=0.20, priority=8),
        TrailingStopExitStrategy(trailing_stop_pct=0.05, priority=9),
        HoldingPeriodExitStrategy(max_holding_days=30, priority=3)
    ]

    return CompositeExitManager(
        exit_strategies=strategies,
        enable_reverse_entry=True,
        enable_risk_control=True
    )


def create_conservative_exit_manager() -> CompositeExitManager:
    """
    创建保守型离场管理器

    特点：更严格的止损，更快的止盈
    """
    strategies = [
        StopLossExitStrategy(stop_loss_pct=0.05, priority=10),  # 5%止损
        TakeProfitExitStrategy(take_profit_pct=0.15, priority=8),  # 15%止盈
        TrailingStopExitStrategy(trailing_stop_pct=0.03, priority=9),  # 3%移动止损
        HoldingPeriodExitStrategy(max_holding_days=20, priority=3)  # 20天最大持仓
    ]

    return CompositeExitManager(
        exit_strategies=strategies,
        enable_reverse_entry=True,
        enable_risk_control=True
    )


def create_aggressive_exit_manager() -> CompositeExitManager:
    """
    创建激进型离场管理器

    特点：更宽松的止损，更高的止盈目标
    """
    strategies = [
        StopLossExitStrategy(stop_loss_pct=0.15, priority=10),  # 15%止损
        TakeProfitExitStrategy(take_profit_pct=0.30, priority=8),  # 30%止盈
        TrailingStopExitStrategy(trailing_stop_pct=0.08, priority=9),  # 8%移动止损
        HoldingPeriodExitStrategy(max_holding_days=60, priority=3)  # 60天最大持仓
    ]

    return CompositeExitManager(
        exit_strategies=strategies,
        enable_reverse_entry=True,
        enable_risk_control=True
    )


# ==================== 使用示例 ====================

if __name__ == "__main__":
    logger.info("离场策略模块测试\n")

    # 创建离场管理器
    exit_manager = create_default_exit_manager()

    logger.info("离场管理器配置:")
    summary = exit_manager.get_summary()
    logger.info(f"  策略数量: {summary['n_strategies']}")
    for s in summary['strategies']:
        logger.info(f"    - {s['name']} (优先级={s['priority']})")

    # 模拟持仓
    positions = {
        '600000.SH': {
            'stock_code': '600000.SH',
            'shares': 1000,
            'entry_price': 10.0,
            'entry_date': datetime(2024, 1, 1),
            'unrealized_pnl_pct': -0.12  # 亏损12%
        },
        '000001.SZ': {
            'stock_code': '000001.SZ',
            'shares': 2000,
            'entry_price': 15.0,
            'entry_date': datetime(2024, 1, 1),
            'unrealized_pnl_pct': 0.25  # 盈利25%
        }
    }

    current_prices = {
        '600000.SH': 8.8,  # 下跌12%
        '000001.SZ': 18.75  # 上涨25%
    }

    current_date = datetime(2024, 1, 15)

    # 检查离场
    logger.info("\n检查离场信号:")
    exit_signals = exit_manager.check_exit(
        positions=positions,
        current_prices=current_prices,
        current_date=current_date
    )

    for stock, signal in exit_signals.items():
        logger.info(f"  {stock}: {signal.trigger} (原因={signal.reason}, 优先级={signal.priority})")
        if signal.metadata:
            logger.info(f"    元数据: {signal.metadata}")

    logger.success("\n✓ 离场策略模块测试完成")
