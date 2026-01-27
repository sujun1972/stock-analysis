"""
回测引擎核心模块
实现向量化回测，支持A股T+1交易规则
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple, Callable
from datetime import datetime
import warnings
from loguru import logger

warnings.filterwarnings('ignore')

from ..config.trading_rules import (
    TradingCosts,
    PriceLimitRules,
    T_PLUS_N,
    MarketType
)


class BacktestEngine:
    """向量化回测引擎"""

    def __init__(
        self,
        initial_capital: float = 1000000.0,
        commission_rate: float = None,
        stamp_tax_rate: float = None,
        min_commission: float = None,
        slippage: float = 0.0,
        verbose: bool = True
    ):
        """
        初始化回测引擎

        参数:
            initial_capital: 初始资金
            commission_rate: 佣金费率（None则使用默认配置）
            stamp_tax_rate: 印花税率（None则使用默认配置）
            min_commission: 最小佣金（None则使用默认配置）
            slippage: 滑点（比例）
            verbose: 是否打印详细信息
        """
        self.initial_capital = initial_capital
        self.verbose = verbose

        # 交易成本
        self.commission_rate = commission_rate or TradingCosts.CommissionRates.DEFAULT
        self.stamp_tax_rate = stamp_tax_rate or TradingCosts.STAMP_TAX_RATE
        self.min_commission = min_commission or TradingCosts.MIN_COMMISSION
        self.slippage = slippage

        # 回测结果
        self.portfolio_value = None
        self.positions = None
        self.trades = None
        self.daily_returns = None
        self.metrics = {}

    def calculate_trading_cost(
        self,
        amount: float,
        is_buy: bool,
        stock_code: str = None
    ) -> float:
        """
        计算交易成本

        参数:
            amount: 交易金额
            is_buy: 是否买入
            stock_code: 股票代码（用于判断交易所）

        返回:
            交易成本
        """
        if is_buy:
            costs = TradingCosts.calculate_buy_cost(
                amount,
                stock_code=stock_code,
                commission_rate=self.commission_rate,
                min_commission=self.min_commission
            )
        else:
            costs = TradingCosts.calculate_sell_cost(
                amount,
                stock_code=stock_code,
                commission_rate=self.commission_rate,
                min_commission=self.min_commission,
                stamp_tax_rate=self.stamp_tax_rate
            )

        return costs['total_cost']

    def backtest_long_only(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        top_n: int = 50,
        holding_period: int = 5,
        rebalance_freq: str = 'W'
    ) -> Dict:
        """
        纯多头回测（等权重选股策略）

        参数:
            signals: 信号DataFrame (index=date, columns=stock_codes, values=signal_scores)
            prices: 价格DataFrame (index=date, columns=stock_codes, values=close_price)
            top_n: 每期选择前N只股票
            holding_period: 最短持仓期（天）
            rebalance_freq: 调仓频率 ('D'=日, 'W'=周, 'M'=月)

        返回:
            回测结果字典
        """
        logger.info(f"\n开始回测...")
        logger.info(f"初始资金: {self.initial_capital:,.0f}")
        logger.info(f"选股数量: {top_n}")
        logger.info(f"调仓频率: {rebalance_freq}")
        logger.info(f"持仓期: {holding_period}天")

        # 对齐数据
        common_dates = signals.index.intersection(prices.index)
        common_stocks = signals.columns.intersection(prices.columns)

        signals = signals.loc[common_dates, common_stocks]
        prices = prices.loc[common_dates, common_stocks]

        logger.info(f"\n数据范围:")
        logger.info(f"  交易日期: {len(common_dates)} 天 ({common_dates[0]} ~ {common_dates[-1]})")
        logger.info(f"  股票数量: {len(common_stocks)} 只")

        # 初始化
        dates = signals.index
        n_days = len(dates)
        cash = self.initial_capital
        portfolio_values = []
        positions_history = []

        # 当前持仓 {stock_code: {'shares': 100, 'entry_price': 10.0, 'entry_date': date}}
        current_positions = {}

        # 调仓日期
        if rebalance_freq == 'D':
            rebalance_dates = dates
        elif rebalance_freq == 'W':
            rebalance_dates = dates[dates.to_series().dt.dayofweek == 0]  # 每周一
        elif rebalance_freq == 'M':
            rebalance_dates = dates[dates.to_series().dt.is_month_start]  # 每月初
        else:
            raise ValueError(f"不支持的调仓频率: {rebalance_freq}")

        logger.info(f"\n调仓次数: {len(rebalance_dates)} 次")

        # 回测主循环
        for i, date in enumerate(dates):
            # 计算当前持仓市值
            holdings_value = 0
            for stock, pos in current_positions.items():
                if stock in prices.columns:
                    current_price = prices.loc[date, stock]
                    if not np.isnan(current_price):
                        holdings_value += pos['shares'] * current_price

            # 总资产
            total_value = cash + holdings_value
            portfolio_values.append({
                'date': date,
                'cash': cash,
                'holdings': holdings_value,
                'total': total_value
            })

            # 记录持仓
            positions_history.append({
                'date': date,
                'positions': current_positions.copy()
            })

            # 检查是否调仓日
            if date in rebalance_dates:
                # 卖出不在新组合中的股票 + 持有期已满的股票
                today_signals = signals.loc[date].dropna()
                top_stocks = today_signals.nlargest(top_n).index.tolist()

                stocks_to_sell = []
                for stock, pos in current_positions.items():
                    # 计算持有天数
                    entry_idx = dates.get_loc(pos['entry_date'])
                    current_idx = dates.get_loc(date)
                    holding_days = current_idx - entry_idx

                    # 卖出条件：不在新组合中 或 持仓期已满
                    if stock not in top_stocks or holding_days >= holding_period:
                        stocks_to_sell.append(stock)

                # 执行卖出（T+1: 今日决定，次日执行）
                if i < n_days - 1:  # 确保次日存在
                    next_date = dates[i + 1]

                    for stock in stocks_to_sell:
                        pos = current_positions[stock]
                        if stock in prices.columns:
                            # 次日开盘价卖出
                            sell_price = prices.loc[next_date, stock]
                            if not np.isnan(sell_price):
                                # 考虑滑点
                                actual_price = sell_price * (1 - self.slippage)

                                # 卖出金额
                                sell_amount = pos['shares'] * actual_price

                                # 计算卖出交易成本
                                cost = self.calculate_trading_cost(sell_amount, is_buy=False, stock_code=stock)

                                # 更新现金
                                cash += (sell_amount - cost)

                                # 移除持仓
                                del current_positions[stock]

                # 买入新股票
                if i < n_days - 1:
                    next_date = dates[i + 1]

                    # 可用于买入的股票（不在当前持仓中）
                    stocks_to_buy = [s for s in top_stocks if s not in current_positions]

                    if stocks_to_buy:
                        # 平均分配资金
                        capital_per_stock = cash / len(stocks_to_buy)

                        for stock in stocks_to_buy:
                            if stock in prices.columns:
                                # 次日开盘价买入
                                buy_price = prices.loc[next_date, stock]
                                if not np.isnan(buy_price) and buy_price > 0:
                                    # 考虑滑点
                                    actual_price = buy_price * (1 + self.slippage)

                                    # 计算可买股数（A股最小100股）
                                    max_shares = int(capital_per_stock / actual_price / 100) * 100

                                    if max_shares >= 100:
                                        # 买入金额
                                        buy_amount = max_shares * actual_price

                                        # 计算买入交易成本
                                        cost = self.calculate_trading_cost(buy_amount, is_buy=True, stock_code=stock)

                                        # 检查资金是否充足
                                        if cash >= (buy_amount + cost):
                                            # 更新现金
                                            cash -= (buy_amount + cost)

                                            # 添加持仓
                                            current_positions[stock] = {
                                                'shares': max_shares,
                                                'entry_price': actual_price,
                                                'entry_date': next_date
                                            }

        # 保存结果
        self.portfolio_value = pd.DataFrame(portfolio_values).set_index('date')
        self.positions = positions_history

        # 计算收益率
        self.daily_returns = self.portfolio_value['total'].pct_change()

        logger.info(f"\n回测完成")
        logger.info(f"最终资产: {self.portfolio_value['total'].iloc[-1]:,.0f}")
        logger.info(f"总收益率: {(self.portfolio_value['total'].iloc[-1] / self.initial_capital - 1) * 100:.2f}%")

        return {
            'portfolio_value': self.portfolio_value,
            'positions': self.positions,
            'daily_returns': self.daily_returns
        }

    def backtest_market_neutral(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        top_n: int = 20,
        bottom_n: int = 20
    ) -> Dict:
        """
        市场中性策略回测（多空对冲）

        参数:
            signals: 信号DataFrame
            prices: 价格DataFrame
            top_n: 做多前N只
            bottom_n: 做空后N只

        返回:
            回测结果字典
        """
        # TODO: 实现市场中性策略
        # A股融券成本高，暂不实现
        raise NotImplementedError("A股市场融券成本高，暂不支持市场中性策略")

    def get_portfolio_value(self) -> pd.DataFrame:
        """获取组合净值曲线"""
        if self.portfolio_value is None:
            raise ValueError("请先运行回测")
        return self.portfolio_value

    def get_daily_returns(self) -> pd.Series:
        """获取每日收益率"""
        if self.daily_returns is None:
            raise ValueError("请先运行回测")
        return self.daily_returns

    def get_positions(self) -> List[Dict]:
        """获取持仓历史"""
        if self.positions is None:
            raise ValueError("请先运行回测")
        return self.positions


# ==================== 使用示例 ====================

if __name__ == "__main__":
    logger.info("回测引擎测试\n")

    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = [f'{i:06d}' for i in range(600000, 600010)]  # 10只股票

    # 模拟价格数据（随机游走）
    price_data = {}
    for stock in stocks:
        base_price = 10.0
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    # 模拟信号数据（带一定预测能力）
    signal_data = {}
    for stock in stocks:
        # 信号与未来收益有一定相关性
        # 修复：使用正确的未来收益计算方法
        future_returns = (prices_df[stock].shift(-5) / prices_df[stock] - 1) * 100
        signals = future_returns + np.random.normal(0, 0.01, len(dates))
        signal_data[stock] = signals

    signals_df = pd.DataFrame(signal_data, index=dates)

    logger.info("测试数据:")
    logger.info(f"  日期范围: {dates[0]} ~ {dates[-1]}")
    logger.info(f"  股票数量: {len(stocks)}")
    logger.info(f"  交易日数: {len(dates)}")

    # 创建回测引擎
    logger.info("\n初始化回测引擎:")
    engine = BacktestEngine(
        initial_capital=1000000,
        verbose=True
    )

    # 运行回测
    logger.info("\n运行回测:")
    results = engine.backtest_long_only(
        signals=signals_df,
        prices=prices_df,
        top_n=5,
        holding_period=5,
        rebalance_freq='W'
    )

    # 查看结果
    logger.info("\n组合净值:")
    logger.info(results['portfolio_value'].tail())

    logger.success("\n✓ 回测引擎测试完成")
