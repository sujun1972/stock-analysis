"""
回测组合管理器
负责管理回测过程中的持仓状态（多头/空头）、计算市值、持仓查询
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

from .short_selling import ShortPosition


class BacktestPortfolio:
    """回测组合管理器"""

    def __init__(self, initial_cash: float):
        """
        初始化组合管理器

        参数:
            initial_cash: 初始现金
        """
        self.cash = initial_cash
        self.initial_cash = initial_cash

        # 多头持仓 {stock_code: {'shares': 100, 'entry_price': 10.0, 'entry_date': date}}
        self.long_positions: Dict[str, Dict[str, Any]] = {}

        # 空头持仓 {stock_code: ShortPosition对象}
        self.short_positions: Dict[str, ShortPosition] = {}

    def add_long_position(
        self,
        stock_code: str,
        shares: int,
        entry_price: float,
        entry_date: datetime
    ):
        """
        添加多头持仓（支持仓位累加）

        如果股票已存在持仓，则累加股数并使用加权平均法计算新的成本价。
        这样可以正确处理多次买入同一只股票的场景。

        Args:
            stock_code: 股票代码
            shares: 新增股数
            entry_price: 本次买入价格
            entry_date: 本次买入日期

        Example:
            # 第一次买入: 1000股 @ 10元，成本价=10元
            portfolio.add_long_position('600000.SH', 1000, 10.0, date1)

            # 第二次买入: 500股 @ 12元，成本价=(1000*10 + 500*12)/1500 = 10.67元
            portfolio.add_long_position('600000.SH', 500, 12.0, date2)
        """
        if stock_code in self.long_positions:
            # 已存在持仓，累加并计算加权平均成本
            existing = self.long_positions[stock_code]
            old_shares = existing['shares']
            old_price = existing['entry_price']

            new_total_shares = old_shares + shares
            # 加权平均成本公式: (原持仓成本 + 新增成本) / 总股数
            new_avg_price = (old_shares * old_price + shares * entry_price) / new_total_shares

            self.long_positions[stock_code] = {
                'shares': new_total_shares,
                'entry_price': new_avg_price,
                'entry_date': existing['entry_date']  # 保持最早的入场日期
            }
        else:
            # 新建持仓
            self.long_positions[stock_code] = {
                'shares': shares,
                'entry_price': entry_price,
                'entry_date': entry_date
            }

    def remove_long_position(self, stock_code: str):
        """移除多头持仓"""
        if stock_code in self.long_positions:
            del self.long_positions[stock_code]

    def get_long_position(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取多头持仓"""
        return self.long_positions.get(stock_code)

    def has_long_position(self, stock_code: str) -> bool:
        """检查是否持有多头"""
        return stock_code in self.long_positions

    def add_short_position(
        self,
        stock_code: str,
        shares: int,
        entry_price: float,
        entry_date: datetime,
        margin_rate: float
    ):
        """添加空头持仓"""
        self.short_positions[stock_code] = ShortPosition(
            stock_code=stock_code,
            shares=shares,
            entry_price=entry_price,
            entry_date=entry_date,
            margin_rate=margin_rate
        )

    def remove_short_position(self, stock_code: str):
        """移除空头持仓"""
        if stock_code in self.short_positions:
            del self.short_positions[stock_code]

    def get_short_position(self, stock_code: str) -> Optional[ShortPosition]:
        """获取空头持仓"""
        return self.short_positions.get(stock_code)

    def has_short_position(self, stock_code: str) -> bool:
        """检查是否持有空头"""
        return stock_code in self.short_positions

    def calculate_long_holdings_value(
        self,
        prices: pd.DataFrame,
        date: datetime
    ) -> float:
        """
        计算多头持仓市值

        参数:
            prices: 价格DataFrame (index=date, columns=stock_codes)
            date: 当前日期

        返回:
            多头持仓市值
        """
        holdings_value = 0.0

        for stock, pos in self.long_positions.items():
            if stock in prices.columns:
                current_price = prices.loc[date, stock]
                if not np.isnan(current_price):
                    holdings_value += pos['shares'] * current_price

        return holdings_value

    def calculate_short_metrics(
        self,
        prices: pd.DataFrame,
        date: datetime
    ) -> Dict[str, float]:
        """
        计算空头持仓指标

        参数:
            prices: 价格DataFrame
            date: 当前日期

        返回:
            {'value': 空头市值, 'pnl': 盈亏, 'interest': 利息}
        """
        short_value = 0.0
        short_pnl_total = 0.0
        short_interest_total = 0.0

        for stock, short_pos in self.short_positions.items():
            if stock in prices.columns:
                current_price = prices.loc[date, stock]
                if not np.isnan(current_price):
                    short_value += short_pos.shares * current_price
                    pnl = short_pos.calculate_profit_loss(current_price, date)
                    short_pnl_total += pnl['net_pnl']
                    short_interest_total += pnl['interest_cost']

        return {
            'value': short_value,
            'pnl': short_pnl_total,
            'interest': short_interest_total
        }

    def get_long_stocks_to_sell(
        self,
        top_stocks: List[str],
        current_date: datetime,
        holding_period: int,
        all_dates: pd.DatetimeIndex
    ) -> List[str]:
        """
        获取需要卖出的多头股票列表

        参数:
            top_stocks: 新的选股列表
            current_date: 当前日期
            holding_period: 最短持仓期
            all_dates: 所有交易日期

        返回:
            需要卖出的股票代码列表
        """
        stocks_to_sell = []

        for stock, pos in self.long_positions.items():
            entry_idx = all_dates.get_loc(pos['entry_date'])
            current_idx = all_dates.get_loc(current_date)
            holding_days = current_idx - entry_idx

            # 卖出条件：不在新组合 或 持仓期已满
            if stock not in top_stocks or holding_days >= holding_period:
                stocks_to_sell.append(stock)

        return stocks_to_sell

    def get_short_stocks_to_cover(
        self,
        bottom_stocks: List[str],
        current_date: datetime,
        holding_period: int,
        all_dates: pd.DatetimeIndex
    ) -> List[str]:
        """
        获取需要平仓的空头股票列表

        参数:
            bottom_stocks: 新的做空列表
            current_date: 当前日期
            holding_period: 最短持仓期
            all_dates: 所有交易日期

        返回:
            需要平仓的股票代码列表
        """
        stocks_to_cover = []

        for stock, short_pos in self.short_positions.items():
            entry_idx = all_dates.get_loc(short_pos.entry_date)
            current_idx = all_dates.get_loc(current_date)
            holding_days = current_idx - entry_idx

            # 平仓条件：不在新组合 或 持仓期已满
            if stock not in bottom_stocks or holding_days >= holding_period:
                stocks_to_cover.append(stock)

        return stocks_to_cover

    def get_stocks_to_buy(
        self,
        top_stocks: List[str]
    ) -> List[str]:
        """获取需要买入的股票列表（不在当前持仓中）"""
        return [s for s in top_stocks if s not in self.long_positions]

    def get_stocks_to_short(
        self,
        bottom_stocks: List[str]
    ) -> List[str]:
        """获取需要做空的股票列表（不在当前空仓中）"""
        return [s for s in bottom_stocks if s not in self.short_positions]

    def update_cash(self, amount: float):
        """
        更新现金

        参数:
            amount: 金额变化（正数=增加，负数=减少）
        """
        self.cash += amount

    def get_cash(self) -> float:
        """获取当前现金"""
        return self.cash

    def get_long_position_count(self) -> int:
        """获取多头持仓数量"""
        return len(self.long_positions)

    def get_short_position_count(self) -> int:
        """获取空头持仓数量"""
        return len(self.short_positions)

    def get_total_value(
        self,
        prices: pd.DataFrame,
        date: datetime
    ) -> Dict[str, float]:
        """
        计算总资产（用于多空策略）

        参数:
            prices: 价格DataFrame
            date: 当前日期

        返回:
            {'cash': 现金, 'long_value': 多头市值, 'short_value': 空头市值,
             'short_pnl': 空头盈亏, 'total': 总资产}
        """
        long_value = self.calculate_long_holdings_value(prices, date)
        short_metrics = self.calculate_short_metrics(prices, date)

        total_value = self.cash + long_value + short_metrics['pnl']

        return {
            'cash': self.cash,
            'long_value': long_value,
            'short_value': short_metrics['value'],
            'short_pnl': short_metrics['pnl'],
            'short_interest': short_metrics['interest'],
            'total': total_value
        }

    def get_positions_snapshot(self) -> Dict[str, Any]:
        """
        获取当前持仓快照

        返回:
            持仓快照字典
        """
        return {
            'long_positions': self.long_positions.copy(),
            'short_positions': {k: v.to_dict() for k, v in self.short_positions.items()}
        }

    def get_long_only_snapshot(self) -> Dict[str, Any]:
        """
        获取纯多头持仓快照（用于long_only策略）

        返回:
            持仓快照字典
        """
        return {
            'positions': self.long_positions.copy()
        }

    def buy(
        self,
        stock_code: str,
        shares: int,
        price: float,
        commission_rate: float,
        date: datetime
    ) -> bool:
        """
        买入股票（支持资金检查）

        Args:
            stock_code: 股票代码
            shares: 买入数量
            price: 买入价格
            commission_rate: 佣金费率
            date: 买入日期

        Returns:
            bool: True表示买入成功，False表示资金不足

        Note:
            - 买入前会检查资金是否充足（成本 = 股数 * 价格 * (1 + 佣金费率)）
            - 买入成功后会自动扣除现金并更新持仓（支持仓位累加）
            - 资金不足时返回False，不会执行任何操作
        """
        cost = shares * price * (1 + commission_rate)
        if cost > self.cash:
            logger.warning(f"资金不足：需要 {cost:.2f}，可用 {self.cash:.2f}")
            return False

        self.cash -= cost
        self.add_long_position(stock_code, shares, price, date)
        return True

    def sell(
        self,
        stock_code: str,
        shares: int,
        price: float,
        commission_rate: float
    ):
        """
        简化版卖出方法（用于三层架构回测）

        参数:
            stock_code: 股票代码
            shares: 卖出数量
            price: 卖出价格
            commission_rate: 佣金费率（包含印花税）
        """
        if stock_code not in self.long_positions:
            logger.warning(f"卖出失败：未持有 {stock_code}")
            return

        amount = shares * price
        cost = amount * commission_rate
        net_amount = amount - cost

        self.cash += net_amount
        self.remove_long_position(stock_code)

    def update_prices(self, current_prices: pd.Series):
        """
        更新持仓价格（用于计算浮动盈亏）

        参数:
            current_prices: 当前价格Series (index=stock_codes)
        """
        for stock_code, position in self.long_positions.items():
            if stock_code in current_prices.index:
                current_price = current_prices[stock_code]
                if not pd.isna(current_price):
                    # 更新浮动盈亏
                    shares = position['shares']
                    entry_price = position['entry_price']
                    position['current_price'] = current_price
                    position['unrealized_pnl'] = (current_price - entry_price) * shares
                    position['unrealized_pnl_pct'] = (current_price - entry_price) / entry_price * 100

    def get_total_equity(self) -> float:
        """
        获取总资产（现金 + 持仓市值）

        返回:
            总资产
        """
        holdings_value = sum(
            pos.get('shares', 0) * pos.get('current_price', pos.get('entry_price', 0))
            for pos in self.long_positions.values()
        )
        return self.cash + holdings_value
