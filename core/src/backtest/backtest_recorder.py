"""
回测数据记录器
负责记录组合净值曲线、持仓历史、计算收益率
"""

import pandas as pd
from typing import List, Dict, Any
from datetime import datetime


class BacktestRecorder:
    """回测数据记录器"""

    def __init__(self):
        """初始化记录器"""
        self.portfolio_values: List[Dict[str, Any]] = []
        self.positions_history: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []  # 交易记录
        self.equity_curve: List[Dict[str, Any]] = []  # 净值曲线（简化版）

    def record_portfolio_value(
        self,
        date: datetime,
        cash: float,
        holdings: float,
        total: float
    ):
        """
        记录组合净值（用于long_only策略）

        参数:
            date: 日期
            cash: 现金
            holdings: 持仓市值
            total: 总资产
        """
        self.portfolio_values.append({
            'date': date,
            'cash': cash,
            'holdings': holdings,
            'total': total
        })

    def record_market_neutral_value(
        self,
        date: datetime,
        cash: float,
        long_value: float,
        short_value: float,
        short_pnl: float,
        short_interest: float,
        total: float
    ):
        """
        记录市场中性组合净值

        参数:
            date: 日期
            cash: 现金
            long_value: 多头市值
            short_value: 空头市值
            short_pnl: 空头盈亏
            short_interest: 融券利息
            total: 总资产
        """
        self.portfolio_values.append({
            'date': date,
            'cash': cash,
            'long_value': long_value,
            'short_value': short_value,
            'short_pnl': short_pnl,
            'short_interest': short_interest,
            'total': total
        })

    def record_positions(
        self,
        date: datetime,
        positions: Dict[str, Any]
    ):
        """
        记录持仓快照

        参数:
            date: 日期
            positions: 持仓字典
        """
        self.positions_history.append({
            'date': date,
            **positions
        })

    def get_portfolio_value_df(self) -> pd.DataFrame:
        """
        获取组合净值DataFrame

        返回:
            组合净值DataFrame (index=date)
        """
        if not self.portfolio_values:
            return pd.DataFrame()

        return pd.DataFrame(self.portfolio_values).set_index('date')

    def get_positions_history(self) -> List[Dict]:
        """
        获取持仓历史

        返回:
            持仓历史列表
        """
        return self.positions_history

    def calculate_daily_returns(self) -> pd.Series:
        """
        计算每日收益率

        返回:
            每日收益率Series
        """
        portfolio_df = self.get_portfolio_value_df()

        if portfolio_df.empty:
            return pd.Series()

        return portfolio_df['total'].pct_change()

    def get_summary(self, initial_capital: float) -> Dict[str, Any]:
        """
        获取回测摘要

        参数:
            initial_capital: 初始资金

        返回:
            摘要字典
        """
        portfolio_df = self.get_portfolio_value_df()

        if portfolio_df.empty:
            return {}

        final_value = portfolio_df['total'].iloc[-1]
        total_return = (final_value / initial_capital - 1)

        summary = {
            'n_days': len(portfolio_df),
            'initial_capital': initial_capital,
            'final_value': float(final_value),
            'total_return': float(total_return),
            'start_date': portfolio_df.index[0],
            'end_date': portfolio_df.index[-1]
        }

        # 如果是市场中性策略，额外返回融券利息
        if 'short_interest' in portfolio_df.columns:
            summary['total_short_interest'] = float(portfolio_df['short_interest'].iloc[-1])

        return summary

    def record_equity(self, date: datetime, equity: float):
        """
        记录净值（用于三层架构回测）

        参数:
            date: 日期
            equity: 总净值
        """
        self.equity_curve.append({
            'date': date,
            'equity': equity
        })

    def record_trade(
        self,
        date: datetime,
        stock_code: str,
        direction: str,
        shares: int,
        price: float
    ):
        """
        记录交易（用于三层架构回测）

        参数:
            date: 交易日期
            stock_code: 股票代码
            direction: 交易方向 ('buy' 或 'sell')
            shares: 交易数量
            price: 交易价格
        """
        self.trades.append({
            'date': date,
            'stock_code': stock_code,
            'direction': direction,
            'shares': shares,
            'price': price,
            'amount': shares * price
        })

    def get_equity_curve(self) -> pd.Series:
        """
        获取净值曲线（用于三层架构回测）

        返回:
            净值曲线Series (index=date, values=equity)
        """
        if not self.equity_curve:
            return pd.Series()

        df = pd.DataFrame(self.equity_curve)
        return df.set_index('date')['equity']

    def get_trades_df(self) -> pd.DataFrame:
        """
        获取交易记录DataFrame

        返回:
            交易记录DataFrame
        """
        if not self.trades:
            return pd.DataFrame()

        return pd.DataFrame(self.trades)

    def clear(self):
        """清空所有记录"""
        self.portfolio_values.clear()
        self.positions_history.clear()
        self.trades.clear()
        self.equity_curve.clear()
