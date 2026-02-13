"""
自适应离场策略

根据市场波动性和持仓盈亏动态调整止盈止损参数的离场策略

特点:
- 低波动市场：更严格的止损，更快的止盈
- 高波动市场：更宽松的止损，更高的止盈目标
- 根据持仓时长动态调整策略

版本: v1.0.0
创建时间: 2026-02-13
"""
from typing import Optional, Dict
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger

from src.ml.exit_strategy import BaseExitStrategy, ExitSignal


class AdaptiveExitStrategy(BaseExitStrategy):
    """
    自适应离场策略

    根据以下因素动态调整离场条件:
    1. 市场波动性（ATR/价格波动）
    2. 持仓盈亏情况
    3. 持仓时长

    使用场景:
    - 希望在不同市场环境下采用不同风控策略
    - 需要根据盈利情况调整止盈目标
    - 想要避免在震荡市场中被频繁止损
    """

    def __init__(
        self,
        base_stop_loss: float = 0.08,
        base_take_profit: float = 0.15,
        volatility_window: int = 20,
        priority: int = 9
    ):
        """
        初始化

        Args:
            base_stop_loss: 基准止损比例 (默认 8%)
            base_take_profit: 基准止盈比例 (默认 15%)
            volatility_window: 波动性计算窗口 (默认 20天)
            priority: 优先级 (默认 9)
        """
        super().__init__(name='AdaptiveExit', priority=priority)

        self.base_stop_loss = base_stop_loss
        self.base_take_profit = base_take_profit
        self.volatility_window = volatility_window

        # 缓存波动性数据
        self.volatility_cache: Dict[str, float] = {}

        logger.info(
            f"初始化自适应离场策略: "
            f"止损={base_stop_loss:.1%}, 止盈={base_take_profit:.1%}, "
            f"波动窗口={volatility_window}天"
        )

    def should_exit(
        self,
        position: Dict,
        current_price: float,
        current_date: datetime,
        market_data: Optional[pd.DataFrame] = None
    ) -> Optional[ExitSignal]:
        """
        判断是否应该离场

        逻辑:
        1. 计算市场波动性
        2. 根据波动性调整止损/止盈参数
        3. 根据持仓时长微调参数
        4. 检查是否触发离场条件
        """
        stock_code = position['stock_code']
        entry_price = position['entry_price']
        entry_date = position.get('entry_date')
        pnl_pct = position.get('unrealized_pnl_pct', 0.0)

        # 1. 计算波动性
        volatility = self._calculate_volatility(
            stock_code, current_price, market_data
        )

        # 2. 计算持仓天数
        holding_days = 0
        if entry_date:
            if isinstance(entry_date, str):
                entry_date = pd.to_datetime(entry_date)
            if isinstance(current_date, str):
                current_date = pd.to_datetime(current_date)
            holding_days = (current_date - entry_date).days

        # 3. 动态调整参数
        adjusted_params = self._adjust_parameters(
            volatility, holding_days, pnl_pct
        )

        stop_loss = adjusted_params['stop_loss']
        take_profit = adjusted_params['take_profit']

        # 4. 检查止损
        if pnl_pct < -stop_loss:
            return ExitSignal(
                stock_code=stock_code,
                reason='risk_control',
                trigger='adaptive_stop_loss',
                priority=self.priority,
                metadata={
                    'base_stop_loss': self.base_stop_loss,
                    'adjusted_stop_loss': stop_loss,
                    'actual_loss': pnl_pct,
                    'volatility': volatility,
                    'holding_days': holding_days,
                    'adjustment_reason': adjusted_params['reason']
                }
            )

        # 5. 检查止盈
        if pnl_pct > take_profit:
            return ExitSignal(
                stock_code=stock_code,
                reason='strategy',
                trigger='adaptive_take_profit',
                priority=self.priority,
                metadata={
                    'base_take_profit': self.base_take_profit,
                    'adjusted_take_profit': take_profit,
                    'actual_profit': pnl_pct,
                    'volatility': volatility,
                    'holding_days': holding_days,
                    'adjustment_reason': adjusted_params['reason']
                }
            )

        return None

    def _calculate_volatility(
        self,
        stock_code: str,
        current_price: float,
        market_data: Optional[pd.DataFrame] = None
    ) -> float:
        """
        计算市场波动性

        方法:
        - 如果有市场数据，使用ATR（Average True Range）
        - 否则使用简化的价格波动率估算

        Returns:
            波动性系数 (0-1之间，0.5为中性)
        """
        # 检查缓存
        if stock_code in self.volatility_cache:
            return self.volatility_cache[stock_code]

        if market_data is None:
            # 简化估算：默认中等波动
            volatility = 0.5
        else:
            try:
                # 筛选当前股票的数据
                stock_data = market_data[
                    market_data['stock_code'] == stock_code
                ].copy()

                if len(stock_data) < self.volatility_window:
                    volatility = 0.5
                else:
                    # 计算最近N天的收益率标准差
                    stock_data = stock_data.sort_values('date').tail(
                        self.volatility_window
                    )
                    returns = stock_data['close'].pct_change().dropna()

                    if len(returns) > 0:
                        # 年化波动率
                        vol = returns.std() * np.sqrt(252)

                        # 归一化到 0-1 (假设年化波动率 0-50%)
                        volatility = min(vol / 0.5, 1.0)
                    else:
                        volatility = 0.5

            except Exception as e:
                logger.warning(f"计算波动性失败 {stock_code}: {e}")
                volatility = 0.5

        # 缓存结果
        self.volatility_cache[stock_code] = volatility

        return volatility

    def _adjust_parameters(
        self,
        volatility: float,
        holding_days: int,
        current_pnl_pct: float
    ) -> Dict:
        """
        根据市场条件动态调整参数

        规则:
        1. 低波动市场（< 0.3）：更严格止损，更快止盈
        2. 中等波动（0.3-0.7）：使用基准参数
        3. 高波动市场（> 0.7）：更宽松止损，更高止盈目标
        4. 持仓超过15天：逐步收紧止盈，放宽止损
        5. 盈利超过5%：将止损调整为保本或小盈

        Returns:
            {
                'stop_loss': 调整后的止损比例,
                'take_profit': 调整后的止盈比例,
                'reason': 调整原因
            }
        """
        stop_loss = self.base_stop_loss
        take_profit = self.base_take_profit
        reasons = []

        # 1. 根据波动性调整
        if volatility < 0.3:
            # 低波动：严格止损 (-20%), 快速止盈 (-30%)
            stop_loss *= 0.8
            take_profit *= 0.7
            reasons.append('低波动环境')
        elif volatility > 0.7:
            # 高波动：宽松止损 (+50%), 高目标止盈 (+50%)
            stop_loss *= 1.5
            take_profit *= 1.5
            reasons.append('高波动环境')
        else:
            reasons.append('中等波动环境')

        # 2. 根据持仓时长调整
        if holding_days > 15:
            # 持仓超过15天：收紧止盈 (-10% per 5 days)
            days_over = holding_days - 15
            take_profit_reduction = min(days_over // 5 * 0.1, 0.4)
            take_profit *= (1 - take_profit_reduction)

            # 放宽止损 (+5% per 5 days)
            stop_loss_increase = min(days_over // 5 * 0.05, 0.2)
            stop_loss *= (1 + stop_loss_increase)

            reasons.append(f'持仓{holding_days}天')

        # 3. 盈利保护
        if current_pnl_pct > 0.05:
            # 盈利超过5%：将止损调整为保本或小盈
            protected_stop_loss = min(
                stop_loss,
                current_pnl_pct * 0.3  # 保护30%的利润
            )

            if protected_stop_loss < stop_loss:
                stop_loss = protected_stop_loss
                reasons.append(f'盈利保护({current_pnl_pct:.1%})')

        # 4. 安全边界
        stop_loss = max(0.02, min(stop_loss, 0.25))  # 2%-25%
        take_profit = max(0.05, min(take_profit, 0.50))  # 5%-50%

        return {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'reason': ', '.join(reasons)
        }

    def reset_stock(self, stock_code: str):
        """清理缓存"""
        if stock_code in self.volatility_cache:
            del self.volatility_cache[stock_code]

    def __repr__(self) -> str:
        return (
            f"AdaptiveExitStrategy("
            f"stop_loss={self.base_stop_loss:.1%}, "
            f"take_profit={self.base_take_profit:.1%}, "
            f"vol_window={self.volatility_window})"
        )


# ==================== 使用示例 ====================

def create_adaptive_exit_manager():
    """创建自适应离场管理器"""
    from src.ml.exit_strategy import CompositeExitManager

    return CompositeExitManager(
        exit_strategies=[
            AdaptiveExitStrategy(
                base_stop_loss=0.08,
                base_take_profit=0.15,
                volatility_window=20,
                priority=9
            )
        ],
        enable_reverse_entry=True,
        enable_risk_control=True
    )


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("自适应离场策略测试")
    logger.info("=" * 60)

    # 创建策略
    strategy = AdaptiveExitStrategy(
        base_stop_loss=0.08,
        base_take_profit=0.15,
        volatility_window=20
    )

    # 模拟场景1：低波动 + 盈利
    logger.info("\n场景1: 低波动市场，盈利8%")
    position = {
        'stock_code': '600000.SH',
        'entry_price': 10.0,
        'entry_date': datetime(2024, 1, 1),
        'unrealized_pnl_pct': 0.08
    }

    # 模拟低波动数据
    market_data = pd.DataFrame({
        'stock_code': ['600000.SH'] * 25,
        'date': pd.date_range('2024-01-01', periods=25),
        'close': np.random.normal(10.0, 0.05, 25)  # 低波动
    })

    signal = strategy.should_exit(
        position=position,
        current_price=10.8,
        current_date=datetime(2024, 1, 20),
        market_data=market_data
    )

    if signal:
        logger.success(f"触发离场: {signal.trigger}")
        logger.info(f"  元数据: {signal.metadata}")
    else:
        logger.info("  未触发离场")

    # 场景2：高波动 + 亏损
    logger.info("\n场景2: 高波动市场，亏损10%")
    position = {
        'stock_code': '000001.SZ',
        'entry_price': 15.0,
        'entry_date': datetime(2024, 1, 1),
        'unrealized_pnl_pct': -0.10
    }

    # 模拟高波动数据
    market_data = pd.DataFrame({
        'stock_code': ['000001.SZ'] * 25,
        'date': pd.date_range('2024-01-01', periods=25),
        'close': np.random.normal(15.0, 0.8, 25)  # 高波动
    })

    signal = strategy.should_exit(
        position=position,
        current_price=13.5,
        current_date=datetime(2024, 1, 20),
        market_data=market_data
    )

    if signal:
        logger.success(f"触发离场: {signal.trigger}")
        logger.info(f"  元数据: {signal.metadata}")
    else:
        logger.info("  未触发离场（高波动下止损放宽）")

    logger.success("\n✓ 自适应离场策略测试完成")
