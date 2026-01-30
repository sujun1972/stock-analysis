"""
融券（做空）成本计算模块

A股融券成本包括:
1. 融券费率（年化）
2. 佣金（与买入相同）
3. 印花税（只在买入还券时收取）
4. 滑点

Author: Stock Analysis Core Team
Date: 2026-01-30
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class ShortSellingCosts:
    """融券成本计算"""

    # A股融券费率（年化）
    MARGIN_RATE_LOW = 0.08      # 8% (低)
    MARGIN_RATE_MEDIUM = 0.10   # 10% (中)
    MARGIN_RATE_HIGH = 0.12     # 12% (高)
    MARGIN_RATE_DEFAULT = 0.10  # 默认10%

    # 保证金比例
    MARGIN_RATIO = 0.5  # 50%保证金

    @classmethod
    def calculate_margin_interest(
        cls,
        amount: float,
        days: int,
        annual_rate: float = None
    ) -> float:
        """
        计算融券利息

        参数:
            amount: 融券金额
            days: 融券天数
            annual_rate: 年化费率（None=默认10%）

        返回:
            融券利息
        """
        if annual_rate is None:
            annual_rate = cls.MARGIN_RATE_DEFAULT

        # 利息 = 融券金额 × 年化费率 × (天数/360)
        # 注意：A股融券计息天数按360天/年
        interest = amount * annual_rate * (days / 360)

        return interest

    @classmethod
    def calculate_required_margin(
        cls,
        short_amount: float,
        margin_ratio: float = None
    ) -> float:
        """
        计算所需保证金

        参数:
            short_amount: 融券金额
            margin_ratio: 保证金比例（None=默认50%）

        返回:
            所需保证金
        """
        if margin_ratio is None:
            margin_ratio = cls.MARGIN_RATIO

        return short_amount * margin_ratio

    @classmethod
    def calculate_short_sell_cost(
        cls,
        amount: float,
        stock_code: str = None,
        commission_rate: float = 0.0003,
        min_commission: float = 5.0
    ) -> Dict[str, float]:
        """
        计算融券卖出成本（开仓）

        参数:
            amount: 卖出金额
            stock_code: 股票代码
            commission_rate: 佣金率
            min_commission: 最小佣金

        返回:
            成本明细字典
        """
        # 佣金
        commission = max(amount * commission_rate, min_commission)

        # 融券卖出时只有佣金，无印花税
        total_cost = commission

        return {
            'commission': commission,
            'stamp_tax': 0.0,  # 融券卖出无印花税
            'total_cost': total_cost
        }

    @classmethod
    def calculate_buy_to_cover_cost(
        cls,
        amount: float,
        stock_code: str = None,
        commission_rate: float = 0.0003,
        min_commission: float = 5.0,
        stamp_tax_rate: float = 0.001
    ) -> Dict[str, float]:
        """
        计算买券还券成本（平仓）

        参数:
            amount: 买入金额
            stock_code: 股票代码
            commission_rate: 佣金率
            min_commission: 最小佣金
            stamp_tax_rate: 印花税率

        返回:
            成本明细字典
        """
        # 佣金
        commission = max(amount * commission_rate, min_commission)

        # 印花税（买券还券时收取）
        stamp_tax = amount * stamp_tax_rate

        total_cost = commission + stamp_tax

        return {
            'commission': commission,
            'stamp_tax': stamp_tax,
            'total_cost': total_cost
        }


class ShortPosition:
    """融券持仓"""

    def __init__(
        self,
        stock_code: str,
        shares: int,
        entry_price: float,
        entry_date: datetime,
        margin_rate: float = ShortSellingCosts.MARGIN_RATE_DEFAULT
    ):
        """
        初始化融券持仓

        参数:
            stock_code: 股票代码
            shares: 融券股数
            entry_price: 融券价格
            entry_date: 融券日期
            margin_rate: 融券费率（年化）
        """
        self.stock_code = stock_code
        self.shares = shares
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.margin_rate = margin_rate

        # 初始融券金额
        self.initial_amount = shares * entry_price

    def calculate_margin_interest_to_date(self, current_date: datetime) -> float:
        """
        计算截至当前日期的融券利息

        参数:
            current_date: 当前日期

        返回:
            累计利息
        """
        # 计算持有天数
        days = (current_date - self.entry_date).days

        # 计算利息
        interest = ShortSellingCosts.calculate_margin_interest(
            amount=self.initial_amount,
            days=days,
            annual_rate=self.margin_rate
        )

        return interest

    def calculate_profit_loss(
        self,
        current_price: float,
        current_date: datetime
    ) -> Dict[str, float]:
        """
        计算盈亏（包含利息）

        参数:
            current_price: 当前价格
            current_date: 当前日期

        返回:
            盈亏明细
        """
        # 价格差收益（融券是价格下跌盈利）
        price_pnl = (self.entry_price - current_price) * self.shares

        # 融券利息成本
        interest_cost = self.calculate_margin_interest_to_date(current_date)

        # 净盈亏 = 价格差收益 - 利息成本
        net_pnl = price_pnl - interest_cost

        return {
            'price_pnl': price_pnl,
            'interest_cost': interest_cost,
            'net_pnl': net_pnl,
            'return_pct': net_pnl / self.initial_amount if self.initial_amount > 0 else 0
        }

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'stock_code': self.stock_code,
            'shares': self.shares,
            'entry_price': self.entry_price,
            'entry_date': self.entry_date,
            'margin_rate': self.margin_rate,
            'initial_amount': self.initial_amount
        }


# ==================== 使用示例 ====================

if __name__ == "__main__":
    logger.info("融券成本计算测试\n")

    # 测试1: 融券利息计算
    logger.info("1. 融券利息计算:")
    amount = 100000  # 10万元
    days = 30  # 持有30天

    interest = ShortSellingCosts.calculate_margin_interest(
        amount=amount,
        days=days,
        annual_rate=0.10  # 10%年化
    )

    logger.info(f"  融券金额: {amount:,.0f} 元")
    logger.info(f"  持有天数: {days} 天")
    logger.info(f"  年化费率: 10%")
    logger.info(f"  融券利息: {interest:,.2f} 元")
    logger.info(f"  日均利息: {interest/days:.2f} 元/天")

    # 测试2: 保证金计算
    logger.info("\n2. 保证金计算:")
    short_amount = 100000
    margin = ShortSellingCosts.calculate_required_margin(short_amount)

    logger.info(f"  融券金额: {short_amount:,.0f} 元")
    logger.info(f"  保证金比例: 50%")
    logger.info(f"  所需保证金: {margin:,.0f} 元")

    # 测试3: 融券开仓成本
    logger.info("\n3. 融券开仓成本（卖出）:")
    short_sell_cost = ShortSellingCosts.calculate_short_sell_cost(
        amount=100000,
        commission_rate=0.0003
    )

    logger.info(f"  卖出金额: 100,000 元")
    logger.info(f"  佣金: {short_sell_cost['commission']:.2f} 元")
    logger.info(f"  印花税: {short_sell_cost['stamp_tax']:.2f} 元 (无)")
    logger.info(f"  总成本: {short_sell_cost['total_cost']:.2f} 元")

    # 测试4: 买券还券成本
    logger.info("\n4. 买券还券成本（平仓）:")
    cover_cost = ShortSellingCosts.calculate_buy_to_cover_cost(
        amount=95000,  # 假设价格下跌到9.5元
        commission_rate=0.0003,
        stamp_tax_rate=0.001
    )

    logger.info(f"  买入金额: 95,000 元")
    logger.info(f"  佣金: {cover_cost['commission']:.2f} 元")
    logger.info(f"  印花税: {cover_cost['stamp_tax']:.2f} 元")
    logger.info(f"  总成本: {cover_cost['total_cost']:.2f} 元")

    # 测试5: 融券持仓盈亏
    logger.info("\n5. 融券持仓盈亏计算:")

    # 创建融券持仓
    entry_date = datetime(2023, 1, 1)
    current_date = datetime(2023, 2, 1)  # 持有31天

    position = ShortPosition(
        stock_code='600000',
        shares=10000,
        entry_price=10.0,
        entry_date=entry_date,
        margin_rate=0.10
    )

    # 计算盈亏（假设价格跌到9.0）
    pnl = position.calculate_profit_loss(
        current_price=9.0,
        current_date=current_date
    )

    logger.info(f"  股票: {position.stock_code}")
    logger.info(f"  融券: {position.shares} 股 @ {position.entry_price:.2f} 元")
    logger.info(f"  当前价: 9.00 元")
    logger.info(f"  持有天数: {(current_date - entry_date).days} 天")
    logger.info(f"\n  盈亏分析:")
    logger.info(f"    价格差收益: {pnl['price_pnl']:>10,.2f} 元")
    logger.info(f"    融券利息: {pnl['interest_cost']:>10,.2f} 元")
    logger.info(f"    净盈亏: {pnl['net_pnl']:>10,.2f} 元")
    logger.info(f"    收益率: {pnl['return_pct']*100:>10.2f}%")

    # 测试6: 不同价格下的盈亏
    logger.info("\n6. 盈亏敏感性分析:")
    logger.info("  当前价  价格PnL   利息    净PnL   收益率")
    logger.info("  " + "-" * 50)

    for price in [11.0, 10.5, 10.0, 9.5, 9.0, 8.5]:
        pnl = position.calculate_profit_loss(price, current_date)
        logger.info(
            f"  {price:>5.1f}   {pnl['price_pnl']:>8,.0f}  "
            f"{pnl['interest_cost']:>6,.0f}  {pnl['net_pnl']:>8,.0f}  "
            f"{pnl['return_pct']*100:>6.2f}%"
        )

    logger.success("\n✓ 融券成本计算测试完成")
