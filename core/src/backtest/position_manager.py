"""
持仓管理器
管理股票持仓、计算权重、风险控制
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')


class Position:
    """单个持仓"""

    def __init__(
        self,
        stock_code: str,
        shares: int,
        entry_price: float,
        entry_date: datetime,
        entry_cost: float = 0.0
    ):
        """
        初始化持仓

        参数:
            stock_code: 股票代码
            shares: 持仓股数
            entry_price: 买入价格
            entry_date: 买入日期
            entry_cost: 买入成本
        """
        self.stock_code = stock_code
        self.shares = shares
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.entry_cost = entry_cost

    def market_value(self, current_price: float) -> float:
        """计算当前市值"""
        return self.shares * current_price

    def profit_loss(self, current_price: float) -> float:
        """计算盈亏（绝对值）"""
        return (current_price - self.entry_price) * self.shares - self.entry_cost

    def profit_loss_pct(self, current_price: float) -> float:
        """计算盈亏比例"""
        cost_basis = self.entry_price * self.shares + self.entry_cost
        if cost_basis > 0:
            return self.profit_loss(current_price) / cost_basis
        else:
            return 0.0

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'shares': self.shares,
            'entry_price': self.entry_price,
            'entry_date': self.entry_date,
            'entry_cost': self.entry_cost
        }


class PositionManager:
    """持仓管理器"""

    def __init__(
        self,
        initial_capital: float,
        max_position_pct: float = 0.2,
        max_single_loss_pct: float = 0.05,
        min_position_value: float = 10000.0
    ):
        """
        初始化持仓管理器

        参数:
            initial_capital: 初始资金
            max_position_pct: 单只股票最大仓位比例
            max_single_loss_pct: 单只股票最大亏损比例（止损）
            min_position_value: 最小持仓市值
        """
        self.initial_capital = initial_capital
        self.max_position_pct = max_position_pct
        self.max_single_loss_pct = max_single_loss_pct
        self.min_position_value = min_position_value

        # 当前持仓 {stock_code: Position}
        self.positions: Dict[str, Position] = {}

        # 现金
        self.cash = initial_capital

    def add_position(
        self,
        stock_code: str,
        shares: int,
        entry_price: float,
        entry_date: datetime,
        entry_cost: float = 0.0
    ):
        """
        添加持仓

        参数:
            stock_code: 股票代码
            shares: 股数
            entry_price: 买入价
            entry_date: 买入日期
            entry_cost: 交易成本
        """
        if stock_code in self.positions:
            # 加仓：更新平均成本
            old_pos = self.positions[stock_code]
            total_shares = old_pos.shares + shares
            total_cost = (old_pos.shares * old_pos.entry_price + old_pos.entry_cost +
                         shares * entry_price + entry_cost)
            avg_price = (total_cost - old_pos.entry_cost - entry_cost) / total_shares

            self.positions[stock_code] = Position(
                stock_code=stock_code,
                shares=total_shares,
                entry_price=avg_price,
                entry_date=old_pos.entry_date,  # 保留原始日期
                entry_cost=old_pos.entry_cost + entry_cost
            )
        else:
            # 新建仓位
            self.positions[stock_code] = Position(
                stock_code=stock_code,
                shares=shares,
                entry_price=entry_price,
                entry_date=entry_date,
                entry_cost=entry_cost
            )

        # 扣除现金
        self.cash -= (shares * entry_price + entry_cost)

    def remove_position(
        self,
        stock_code: str,
        shares: int,
        exit_price: float,
        exit_cost: float = 0.0
    ) -> Optional[float]:
        """
        减少/清空持仓

        参数:
            stock_code: 股票代码
            shares: 卖出股数
            exit_price: 卖出价
            exit_cost: 交易成本

        返回:
            实现盈亏（None表示无此持仓）
        """
        if stock_code not in self.positions:
            return None

        pos = self.positions[stock_code]

        if shares >= pos.shares:
            # 全部卖出
            sell_shares = pos.shares
            realized_pnl = pos.profit_loss(exit_price) - exit_cost
            del self.positions[stock_code]
        else:
            # 部分卖出
            sell_shares = shares
            pnl_per_share = (exit_price - pos.entry_price)
            realized_pnl = pnl_per_share * sell_shares - exit_cost

            # 更新持仓
            pos.shares -= sell_shares
            # 成本按比例减少
            pos.entry_cost = pos.entry_cost * (pos.shares / (pos.shares + sell_shares))

        # 增加现金
        self.cash += (sell_shares * exit_price - exit_cost)

        return realized_pnl

    def get_position(self, stock_code: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(stock_code)

    def has_position(self, stock_code: str) -> bool:
        """检查是否持有"""
        return stock_code in self.positions

    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions.copy()

    def calculate_total_value(self, prices: Dict[str, float]) -> float:
        """
        计算总资产

        参数:
            prices: {股票代码: 当前价格} 字典

        返回:
            总资产
        """
        holdings_value = sum(
            pos.market_value(prices.get(stock, pos.entry_price))
            for stock, pos in self.positions.items()
        )
        return self.cash + holdings_value

    def calculate_position_weights(self, prices: Dict[str, float]) -> Dict[str, float]:
        """
        计算各持仓权重

        参数:
            prices: {股票代码: 当前价格} 字典

        返回:
            {股票代码: 权重} 字典
        """
        total_value = self.calculate_total_value(prices)

        if total_value == 0:
            return {}

        weights = {}
        for stock, pos in self.positions.items():
            current_price = prices.get(stock, pos.entry_price)
            market_value = pos.market_value(current_price)
            weights[stock] = market_value / total_value

        return weights

    def check_stop_loss(self, prices: Dict[str, float]) -> List[str]:
        """
        检查止损

        参数:
            prices: {股票代码: 当前价格} 字典

        返回:
            需要止损的股票代码列表
        """
        stop_loss_stocks = []

        for stock, pos in self.positions.items():
            current_price = prices.get(stock)
            if current_price is None:
                continue

            loss_pct = pos.profit_loss_pct(current_price)

            if loss_pct < -self.max_single_loss_pct:
                stop_loss_stocks.append(stock)

        return stop_loss_stocks

    def check_position_limit(self, prices: Dict[str, float]) -> List[str]:
        """
        检查仓位限制

        参数:
            prices: {股票代码: 当前价格} 字典

        返回:
            超过仓位限制的股票代码列表
        """
        total_value = self.calculate_total_value(prices)
        overlimit_stocks = []

        for stock, pos in self.positions.items():
            current_price = prices.get(stock, pos.entry_price)
            market_value = pos.market_value(current_price)
            weight = market_value / total_value if total_value > 0 else 0

            if weight > self.max_position_pct:
                overlimit_stocks.append(stock)

        return overlimit_stocks

    def calculate_available_capital(
        self,
        prices: Dict[str, float],
        reserve_ratio: float = 0.05
    ) -> float:
        """
        计算可用于开仓的资金

        参数:
            prices: 当前价格字典
            reserve_ratio: 保留现金比例

        返回:
            可用资金
        """
        total_value = self.calculate_total_value(prices)
        min_reserve = total_value * reserve_ratio

        available = self.cash - min_reserve

        return max(0, available)

    def get_summary(self, prices: Dict[str, float]) -> Dict:
        """
        获取持仓摘要

        参数:
            prices: 当前价格字典

        返回:
            持仓摘要字典
        """
        total_value = self.calculate_total_value(prices)
        weights = self.calculate_position_weights(prices)

        # 计算总盈亏
        total_pnl = sum(
            pos.profit_loss(prices.get(stock, pos.entry_price))
            for stock, pos in self.positions.items()
        )

        summary = {
            'cash': self.cash,
            'holdings_value': total_value - self.cash,
            'total_value': total_value,
            'position_count': len(self.positions),
            'total_pnl': total_pnl,
            'total_return': (total_value - self.initial_capital) / self.initial_capital,
            'positions': {
                stock: {
                    'shares': pos.shares,
                    'entry_price': pos.entry_price,
                    'current_price': prices.get(stock, pos.entry_price),
                    'market_value': pos.market_value(prices.get(stock, pos.entry_price)),
                    'weight': weights.get(stock, 0),
                    'pnl': pos.profit_loss(prices.get(stock, pos.entry_price)),
                    'pnl_pct': pos.profit_loss_pct(prices.get(stock, pos.entry_price))
                }
                for stock, pos in self.positions.items()
            }
        }

        return summary


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("持仓管理器测试\n")

    # 创建持仓管理器
    manager = PositionManager(
        initial_capital=1000000,
        max_position_pct=0.2,
        max_single_loss_pct=0.05
    )

    print("初始状态:")
    print(f"  初始资金: {manager.cash:,.0f}")

    # 买入股票
    print("\n买入股票:")
    manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 50)
    manager.add_position('000001', 2000, 15.0, datetime(2023, 1, 2), 75)
    print(f"  持仓数量: {len(manager.positions)}")
    print(f"  剩余现金: {manager.cash:,.0f}")

    # 当前价格
    current_prices = {
        '600000': 11.0,
        '000001': 14.5
    }

    # 计算总资产
    total_value = manager.calculate_total_value(current_prices)
    print(f"\n总资产: {total_value:,.0f}")

    # 持仓权重
    weights = manager.calculate_position_weights(current_prices)
    print("\n持仓权重:")
    for stock, weight in weights.items():
        print(f"  {stock}: {weight*100:.2f}%")

    # 持仓摘要
    summary = manager.get_summary(current_prices)
    print("\n持仓摘要:")
    print(f"  现金: {summary['cash']:,.0f}")
    print(f"  持仓市值: {summary['holdings_value']:,.0f}")
    print(f"  总资产: {summary['total_value']:,.0f}")
    print(f"  总盈亏: {summary['total_pnl']:,.0f}")
    print(f"  总收益率: {summary['total_return']*100:.2f}%")

    # 卖出股票
    print("\n卖出股票:")
    pnl = manager.remove_position('600000', 500, 11.0, 25)
    print(f"  实现盈亏: {pnl:,.0f}")
    print(f"  剩余现金: {manager.cash:,.0f}")

    print("\n✓ 持仓管理器测试完成")
