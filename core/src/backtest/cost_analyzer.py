"""
交易成本分析器

提供详细的交易成本分析功能，包括：
- 交易成本记录和统计（佣金、印花税、滑点）
- 换手率计算（年化/总）
- 成本影响分析（成本拖累、占比）
- 按股票和时间维度统计成本
- 成本场景模拟

Author: Stock Analysis Core Team
Date: 2026-01-29
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import warnings
from loguru import logger

warnings.filterwarnings('ignore')


class Trade:
    """单笔交易记录"""

    def __init__(
        self,
        date: datetime,
        stock_code: str,
        action: str,  # 'buy' or 'sell'
        shares: int,
        price: float,
        commission: float,
        stamp_tax: float,
        slippage: float,
        total_cost: float
    ):
        """
        初始化交易记录

        参数:
            date: 交易日期
            stock_code: 股票代码
            action: 买入/卖出
            shares: 股数
            price: 成交价格
            commission: 佣金
            stamp_tax: 印花税
            slippage: 滑点成本
            total_cost: 总成本
        """
        self.date = date
        self.stock_code = stock_code
        self.action = action
        self.shares = shares
        self.price = price
        self.commission = commission
        self.stamp_tax = stamp_tax
        self.slippage = slippage
        self.total_cost = total_cost
        self.trade_value = shares * price

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'date': self.date,
            'stock_code': self.stock_code,
            'action': self.action,
            'shares': self.shares,
            'price': self.price,
            'trade_value': self.trade_value,
            'commission': self.commission,
            'stamp_tax': self.stamp_tax,
            'slippage': self.slippage,
            'total_cost': self.total_cost,
            'cost_ratio': self.total_cost / self.trade_value if self.trade_value > 0 else 0
        }


class TradingCostAnalyzer:
    """交易成本分析器"""

    def __init__(self):
        """初始化成本分析器"""
        self.trades: List[Trade] = []
        self.metrics = {}

    def add_trade(self, trade: Trade):
        """添加交易记录"""
        self.trades.append(trade)

    def add_trade_from_dict(
        self,
        date: datetime,
        stock_code: str,
        action: str,
        shares: int,
        price: float,
        commission: float,
        stamp_tax: float = 0.0,
        slippage: float = 0.0
    ):
        """从参数创建并添加交易记录"""
        total_cost = commission + stamp_tax + slippage
        trade = Trade(
            date=date,
            stock_code=stock_code,
            action=action,
            shares=shares,
            price=price,
            commission=commission,
            stamp_tax=stamp_tax,
            slippage=slippage,
            total_cost=total_cost
        )
        self.add_trade(trade)

    def get_trades_dataframe(self) -> pd.DataFrame:
        """获取交易记录DataFrame"""
        if not self.trades:
            return pd.DataFrame()

        trades_data = [trade.to_dict() for trade in self.trades]
        df = pd.DataFrame(trades_data)
        df = df.set_index('date')
        return df

    def calculate_total_costs(self) -> Dict[str, float]:
        """
        计算总成本

        返回:
            {
                'total_commission': 总佣金,
                'total_stamp_tax': 总印花税,
                'total_slippage': 总滑点成本,
                'total_cost': 总成本
            }
        """
        if not self.trades:
            return {
                'total_commission': 0.0,
                'total_stamp_tax': 0.0,
                'total_slippage': 0.0,
                'total_cost': 0.0
            }

        total_commission = sum(t.commission for t in self.trades)
        total_stamp_tax = sum(t.stamp_tax for t in self.trades)
        total_slippage = sum(t.slippage for t in self.trades)
        total_cost = sum(t.total_cost for t in self.trades)

        return {
            'total_commission': total_commission,
            'total_stamp_tax': total_stamp_tax,
            'total_slippage': total_slippage,
            'total_cost': total_cost
        }

    def calculate_turnover_rate(
        self,
        portfolio_values: pd.Series,
        period: str = 'annual'
    ) -> float:
        """
        计算换手率

        参数:
            portfolio_values: 组合净值序列
            period: 'annual'（年化）或 'total'（总换手率）

        返回:
            换手率
        """
        if not self.trades:
            return 0.0

        # 计算总交易额（买入+卖出）
        total_trade_value = sum(t.trade_value for t in self.trades)

        # 平均资产
        avg_portfolio_value = portfolio_values.mean()

        if avg_portfolio_value == 0:
            return 0.0

        # 总换手率
        total_turnover = total_trade_value / avg_portfolio_value

        if period == 'annual':
            # 年化换手率
            n_days = len(portfolio_values)
            n_years = n_days / 252  # 假设一年252个交易日
            if n_years > 0:
                return total_turnover / n_years
            else:
                return total_turnover
        else:
            return total_turnover

    def calculate_cost_by_stock(self) -> pd.DataFrame:
        """
        按股票统计成本

        返回:
            各股票的成本统计DataFrame
        """
        if not self.trades:
            return pd.DataFrame()

        # 按股票分组
        stock_costs = {}
        for trade in self.trades:
            if trade.stock_code not in stock_costs:
                stock_costs[trade.stock_code] = {
                    'trade_count': 0,
                    'total_value': 0.0,
                    'total_cost': 0.0,
                    'commission': 0.0,
                    'stamp_tax': 0.0,
                    'slippage': 0.0
                }

            stock_costs[trade.stock_code]['trade_count'] += 1
            stock_costs[trade.stock_code]['total_value'] += trade.trade_value
            stock_costs[trade.stock_code]['total_cost'] += trade.total_cost
            stock_costs[trade.stock_code]['commission'] += trade.commission
            stock_costs[trade.stock_code]['stamp_tax'] += trade.stamp_tax
            stock_costs[trade.stock_code]['slippage'] += trade.slippage

        # 转换为DataFrame
        df = pd.DataFrame.from_dict(stock_costs, orient='index')
        df['cost_ratio'] = df['total_cost'] / df['total_value']
        df = df.sort_values('total_cost', ascending=False)

        return df

    def calculate_cost_over_time(self) -> pd.DataFrame:
        """
        计算成本时间序列

        返回:
            成本时间序列DataFrame (按日累计)
        """
        if not self.trades:
            return pd.DataFrame()

        # 转换为DataFrame
        trades_df = self.get_trades_dataframe()

        # 按日期分组累计
        daily_costs = trades_df.groupby(trades_df.index).agg({
            'commission': 'sum',
            'stamp_tax': 'sum',
            'slippage': 'sum',
            'total_cost': 'sum',
            'trade_value': 'sum'
        })

        # 计算累计值
        daily_costs['cumulative_commission'] = daily_costs['commission'].cumsum()
        daily_costs['cumulative_stamp_tax'] = daily_costs['stamp_tax'].cumsum()
        daily_costs['cumulative_slippage'] = daily_costs['slippage'].cumsum()
        daily_costs['cumulative_total_cost'] = daily_costs['total_cost'].cumsum()

        return daily_costs

    def calculate_cost_impact(
        self,
        portfolio_returns: pd.Series,
        portfolio_values: pd.Series
    ) -> Dict[str, float]:
        """
        计算成本对收益的影响

        参数:
            portfolio_returns: 组合收益率序列
            portfolio_values: 组合净值序列

        返回:
            成本影响指标字典
        """
        if not self.trades or len(portfolio_values) == 0:
            return {}

        # 总收益
        total_return = (portfolio_values.iloc[-1] - portfolio_values.iloc[0]) / portfolio_values.iloc[0]

        # 总成本
        total_costs = self.calculate_total_costs()
        total_cost = total_costs['total_cost']

        # 成本占初始资金比例
        cost_to_capital_ratio = total_cost / portfolio_values.iloc[0]

        # 成本占收益比例
        gross_profit = (portfolio_values.iloc[-1] - portfolio_values.iloc[0])
        if gross_profit > 0:
            cost_to_profit_ratio = total_cost / gross_profit
        else:
            cost_to_profit_ratio = np.inf

        # 无成本情况下的收益率
        no_cost_return = (portfolio_values.iloc[-1] + total_cost - portfolio_values.iloc[0]) / portfolio_values.iloc[0]

        # 成本拖累（收益率下降）
        cost_drag = no_cost_return - total_return

        return {
            'total_cost': total_cost,
            'cost_to_capital_ratio': cost_to_capital_ratio,
            'cost_to_profit_ratio': cost_to_profit_ratio,
            'cost_drag': cost_drag,
            'return_with_cost': total_return,
            'return_without_cost': no_cost_return
        }

    def simulate_cost_scenarios(
        self,
        portfolio_values: pd.Series,
        cost_multipliers: List[float] = [0.5, 0.8, 1.0, 1.5, 2.0]
    ) -> pd.DataFrame:
        """
        模拟不同成本场景下的收益

        参数:
            portfolio_values: 组合净值序列
            cost_multipliers: 成本倍数列表（1.0=当前成本，0.5=减半，2.0=翻倍）

        返回:
            各场景下的收益对比DataFrame
        """
        if not self.trades or len(portfolio_values) == 0:
            return pd.DataFrame()

        # 计算总成本
        total_costs = self.calculate_total_costs()
        base_total_cost = total_costs['total_cost']

        initial_value = portfolio_values.iloc[0]
        final_value = portfolio_values.iloc[-1]

        scenarios = []
        for multiplier in cost_multipliers:
            scenario_cost = base_total_cost * multiplier
            scenario_final_value = final_value + (base_total_cost - scenario_cost)
            scenario_return = (scenario_final_value - initial_value) / initial_value

            scenarios.append({
                'cost_multiplier': multiplier,
                'total_cost': scenario_cost,
                'final_value': scenario_final_value,
                'total_return': scenario_return,
                'annualized_return': (1 + scenario_return) ** (252 / len(portfolio_values)) - 1
            })

        df = pd.DataFrame(scenarios)
        return df

    def analyze_all(
        self,
        portfolio_returns: pd.Series,
        portfolio_values: pd.Series,
        verbose: bool = True
    ) -> Dict:
        """
        综合分析所有成本指标

        参数:
            portfolio_returns: 组合收益率序列
            portfolio_values: 组合净值序列
            verbose: 是否打印结果

        返回:
            完整的成本分析结果
        """
        if not self.trades:
            logger.warning("没有交易记录，无法进行成本分析")
            return {}

        # 1. 总成本
        total_costs = self.calculate_total_costs()

        # 2. 换手率
        annual_turnover = self.calculate_turnover_rate(portfolio_values, period='annual')
        total_turnover = self.calculate_turnover_rate(portfolio_values, period='total')

        # 3. 交易统计
        n_trades = len(self.trades)
        n_buy_trades = sum(1 for t in self.trades if t.action == 'buy')
        n_sell_trades = sum(1 for t in self.trades if t.action == 'sell')
        avg_cost_per_trade = total_costs['total_cost'] / n_trades if n_trades > 0 else 0

        # 4. 成本影响
        cost_impact = self.calculate_cost_impact(portfolio_returns, portfolio_values)

        # 5. 成本构成比例
        total_cost = total_costs['total_cost']
        if total_cost > 0:
            commission_pct = total_costs['total_commission'] / total_cost
            stamp_tax_pct = total_costs['total_stamp_tax'] / total_cost
            slippage_pct = total_costs['total_slippage'] / total_cost
        else:
            commission_pct = stamp_tax_pct = slippage_pct = 0.0

        self.metrics = {
            # 总成本
            'total_cost': total_cost,
            'total_commission': total_costs['total_commission'],
            'total_stamp_tax': total_costs['total_stamp_tax'],
            'total_slippage': total_costs['total_slippage'],

            # 成本构成
            'commission_pct': commission_pct,
            'stamp_tax_pct': stamp_tax_pct,
            'slippage_pct': slippage_pct,

            # 换手率
            'annual_turnover_rate': annual_turnover,
            'total_turnover_rate': total_turnover,

            # 交易统计
            'n_trades': n_trades,
            'n_buy_trades': n_buy_trades,
            'n_sell_trades': n_sell_trades,
            'avg_cost_per_trade': avg_cost_per_trade,

            # 成本影响
            'cost_to_capital_ratio': cost_impact.get('cost_to_capital_ratio', 0),
            'cost_to_profit_ratio': cost_impact.get('cost_to_profit_ratio', 0),
            'cost_drag': cost_impact.get('cost_drag', 0),
            'return_with_cost': cost_impact.get('return_with_cost', 0),
            'return_without_cost': cost_impact.get('return_without_cost', 0)
        }

        if verbose:
            self.print_analysis()

        return self.metrics

    def print_analysis(self):
        """打印成本分析报告"""
        if not self.metrics:
            logger.warning("请先运行 analyze_all()")
            return

        logger.info("\n" + "="*60)
        logger.info("交易成本分析报告")
        logger.info("="*60)

        logger.info("\n📊 总成本:")
        logger.info(f"  总成本:             {self.metrics['total_cost']:>15,.2f} 元")
        logger.info(f"    - 佣金:           {self.metrics['total_commission']:>15,.2f} 元 ({self.metrics['commission_pct']*100:>5.1f}%)")
        logger.info(f"    - 印花税:         {self.metrics['total_stamp_tax']:>15,.2f} 元 ({self.metrics['stamp_tax_pct']*100:>5.1f}%)")
        logger.info(f"    - 滑点:           {self.metrics['total_slippage']:>15,.2f} 元 ({self.metrics['slippage_pct']*100:>5.1f}%)")

        logger.info("\n📈 换手率:")
        logger.info(f"  年化换手率:         {self.metrics['annual_turnover_rate']:>15.2f}")
        logger.info(f"  总换手率:           {self.metrics['total_turnover_rate']:>15.2f}")

        logger.info("\n🔄 交易统计:")
        logger.info(f"  总交易次数:         {self.metrics['n_trades']:>15.0f} 次")
        logger.info(f"    - 买入次数:       {self.metrics['n_buy_trades']:>15.0f} 次")
        logger.info(f"    - 卖出次数:       {self.metrics['n_sell_trades']:>15.0f} 次")
        logger.info(f"  平均每笔成本:       {self.metrics['avg_cost_per_trade']:>15,.2f} 元")

        logger.info("\n💰 成本影响:")
        logger.info(f"  成本占初始资金:     {self.metrics['cost_to_capital_ratio']*100:>15.2f}%")
        if self.metrics['cost_to_profit_ratio'] != np.inf:
            logger.info(f"  成本占总收益:       {self.metrics['cost_to_profit_ratio']*100:>15.2f}%")
        else:
            logger.info(f"  成本占总收益:       {'N/A (亏损)':>15}")
        logger.info(f"  成本拖累:           {self.metrics['cost_drag']*100:>15.2f}%")
        logger.info(f"  有成本收益率:       {self.metrics['return_with_cost']*100:>15.2f}%")
        logger.info(f"  无成本收益率:       {self.metrics['return_without_cost']*100:>15.2f}%")

        logger.info("="*60 + "\n")

    def get_metrics(self) -> Dict:
        """获取所有指标"""
        return self.metrics.copy()


