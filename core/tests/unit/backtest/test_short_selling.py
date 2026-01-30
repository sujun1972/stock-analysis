#!/usr/bin/env python3
"""
融券成本计算单元测试

测试融券利息、保证金、开仓平仓成本计算

Author: Stock Analysis Core Team
Date: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backtest.short_selling import ShortSellingCosts, ShortPosition


class TestShortSellingCosts:
    """测试融券成本计算"""

    def test_margin_interest_calculation(self):
        """测试融券利息计算"""
        # 10万元，持有30天，10%年化
        interest = ShortSellingCosts.calculate_margin_interest(
            amount=100000,
            days=30,
            annual_rate=0.10
        )

        # 预期：100000 * 0.10 * (30/360) = 833.33
        expected = 100000 * 0.10 * (30 / 360)
        assert abs(interest - expected) < 0.01

    def test_margin_interest_different_rates(self):
        """测试不同费率"""
        amount = 100000
        days = 30

        # 低费率8%
        low_rate = ShortSellingCosts.calculate_margin_interest(
            amount, days, ShortSellingCosts.MARGIN_RATE_LOW
        )

        # 高费率12%
        high_rate = ShortSellingCosts.calculate_margin_interest(
            amount, days, ShortSellingCosts.MARGIN_RATE_HIGH
        )

        assert high_rate > low_rate
        assert abs(high_rate / low_rate - 1.5) < 0.01  # 12% / 8% = 1.5

    def test_margin_interest_default_rate(self):
        """测试默认费率（10%）"""
        interest = ShortSellingCosts.calculate_margin_interest(
            amount=100000,
            days=30,
            annual_rate=None  # 使用默认
        )

        expected = 100000 * 0.10 * (30 / 360)
        assert abs(interest - expected) < 0.01

    def test_required_margin(self):
        """测试保证金计算"""
        short_amount = 100000

        # 默认50%保证金
        margin = ShortSellingCosts.calculate_required_margin(short_amount)
        assert margin == 50000

        # 自定义保证金比例
        margin_custom = ShortSellingCosts.calculate_required_margin(
            short_amount,
            margin_ratio=0.6
        )
        assert margin_custom == 60000

    def test_short_sell_cost(self):
        """测试融券卖出成本"""
        amount = 100000

        costs = ShortSellingCosts.calculate_short_sell_cost(
            amount=amount,
            commission_rate=0.0003,
            min_commission=5.0
        )

        # 应该只有佣金，无印花税
        assert costs['stamp_tax'] == 0.0
        assert costs['commission'] == amount * 0.0003
        assert costs['total_cost'] == costs['commission']

    def test_short_sell_min_commission(self):
        """测试最小佣金限制"""
        # 小额交易
        small_amount = 10000

        costs = ShortSellingCosts.calculate_short_sell_cost(
            amount=small_amount,
            commission_rate=0.0003,
            min_commission=5.0
        )

        # 佣金应该是最小值
        assert costs['commission'] == 5.0

    def test_buy_to_cover_cost(self):
        """测试买券还券成本"""
        amount = 100000

        costs = ShortSellingCosts.calculate_buy_to_cover_cost(
            amount=amount,
            commission_rate=0.0003,
            min_commission=5.0,
            stamp_tax_rate=0.001
        )

        # 应该有佣金和印花税
        expected_commission = amount * 0.0003
        expected_stamp_tax = amount * 0.001

        assert costs['commission'] == expected_commission
        assert costs['stamp_tax'] == expected_stamp_tax
        assert costs['total_cost'] == expected_commission + expected_stamp_tax

    def test_cover_vs_sell_cost_difference(self):
        """测试买券还券与卖出成本的差异"""
        amount = 100000

        # 融券卖出（开仓）
        sell_cost = ShortSellingCosts.calculate_short_sell_cost(amount)

        # 买券还券（平仓）
        cover_cost = ShortSellingCosts.calculate_buy_to_cover_cost(amount)

        # 买券还券成本更高（因为有印花税）
        assert cover_cost['total_cost'] > sell_cost['total_cost']
        assert cover_cost['stamp_tax'] > 0
        assert sell_cost['stamp_tax'] == 0


class TestShortPosition:
    """测试融券持仓"""

    def test_initialization(self):
        """测试持仓初始化"""
        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            margin_rate=0.10
        )

        assert pos.stock_code == '600000'
        assert pos.shares == 10000
        assert pos.entry_price == 10.0
        assert pos.initial_amount == 100000

    def test_margin_interest_accumulation(self):
        """测试利息累计"""
        entry_date = datetime(2023, 1, 1)
        current_date = datetime(2023, 2, 1)  # 31天后

        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=entry_date,
            margin_rate=0.10
        )

        interest = pos.calculate_margin_interest_to_date(current_date)

        # 预期：100000 * 0.10 * (31/360)
        expected = 100000 * 0.10 * (31 / 360)
        assert abs(interest - expected) < 0.01

    def test_profit_when_price_falls(self):
        """测试价格下跌时盈利"""
        entry_date = datetime(2023, 1, 1)
        current_date = datetime(2023, 1, 31)

        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=entry_date,
            margin_rate=0.10
        )

        # 价格跌到9.0
        pnl = pos.calculate_profit_loss(
            current_price=9.0,
            current_date=current_date
        )

        # 价格差收益：(10.0 - 9.0) * 10000 = 10000
        assert pnl['price_pnl'] == 10000

        # 利息成本
        expected_interest = 100000 * 0.10 * (30 / 360)
        assert abs(pnl['interest_cost'] - expected_interest) < 0.01

        # 净盈亏 = 价格收益 - 利息
        assert abs(pnl['net_pnl'] - (10000 - expected_interest)) < 0.01

    def test_loss_when_price_rises(self):
        """测试价格上涨时亏损"""
        entry_date = datetime(2023, 1, 1)
        current_date = datetime(2023, 1, 31)

        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=entry_date,
            margin_rate=0.10
        )

        # 价格涨到11.0
        pnl = pos.calculate_profit_loss(
            current_price=11.0,
            current_date=current_date
        )

        # 价格差亏损：(10.0 - 11.0) * 10000 = -10000
        assert pnl['price_pnl'] == -10000

        # 净盈亏 = 价格亏损 - 利息（双重损失）
        assert pnl['net_pnl'] < -10000

    def test_return_percentage(self):
        """测试收益率计算"""
        entry_date = datetime(2023, 1, 1)
        current_date = datetime(2023, 1, 31)

        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=entry_date,
            margin_rate=0.10
        )

        # 价格跌10%到9.0
        pnl = pos.calculate_profit_loss(9.0, current_date)

        # 收益率应该接近10%（略低于10%因为有利息成本）
        assert 0.09 < pnl['return_pct'] < 0.10

    def test_interest_increases_over_time(self):
        """测试利息随时间增加"""
        entry_date = datetime(2023, 1, 1)

        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=entry_date,
            margin_rate=0.10
        )

        # 30天后
        pnl_30d = pos.calculate_profit_loss(
            current_price=10.0,
            current_date=datetime(2023, 1, 31)
        )

        # 60天后
        pnl_60d = pos.calculate_profit_loss(
            current_price=10.0,
            current_date=datetime(2023, 3, 2)
        )

        # 60天利息应该是30天的约2倍
        assert pnl_60d['interest_cost'] > pnl_30d['interest_cost']
        assert abs(pnl_60d['interest_cost'] / pnl_30d['interest_cost'] - 2.0) < 0.1

    def test_to_dict(self):
        """测试转换为字典"""
        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            margin_rate=0.10
        )

        pos_dict = pos.to_dict()

        assert pos_dict['stock_code'] == '600000'
        assert pos_dict['shares'] == 10000
        assert pos_dict['entry_price'] == 10.0
        assert pos_dict['margin_rate'] == 0.10
        assert pos_dict['initial_amount'] == 100000


class TestRealWorldScenarios:
    """测试真实场景"""

    def test_short_position_complete_cycle(self):
        """测试完整的融券周期"""
        # 开仓
        entry_date = datetime(2023, 1, 1)
        entry_price = 10.0
        shares = 10000

        pos = ShortPosition(
            stock_code='600000',
            shares=shares,
            entry_price=entry_price,
            entry_date=entry_date,
            margin_rate=0.10
        )

        # 卖出成本
        short_amount = shares * entry_price
        sell_costs = ShortSellingCosts.calculate_short_sell_cost(
            amount=short_amount,
            commission_rate=0.0003,
            min_commission=5.0
        )

        # 持有30天后平仓（价格跌到9.5）
        close_date = datetime(2023, 1, 31)
        close_price = 9.5

        # 买券还券成本
        cover_amount = shares * close_price
        cover_costs = ShortSellingCosts.calculate_buy_to_cover_cost(
            amount=cover_amount,
            commission_rate=0.0003,
            min_commission=5.0,
            stamp_tax_rate=0.001
        )

        # 计算盈亏
        pnl = pos.calculate_profit_loss(close_price, close_date)

        # 总成本
        total_costs = sell_costs['total_cost'] + cover_costs['total_cost']

        # 净收益 = 价格差收益 - 利息 - 交易成本
        net_profit = pnl['net_pnl'] - total_costs

        # 验证：应该盈利（价格下跌了5%，利息和成本大约1%）
        assert net_profit > 0
        assert net_profit > 4000  # 应该有4%左右的净收益

    def test_high_margin_rate_impact(self):
        """测试高融券费率的影响"""
        entry_date = datetime(2023, 1, 1)
        close_date = datetime(2023, 4, 1)  # 持有90天

        # 低费率8%
        pos_low = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=entry_date,
            margin_rate=0.08
        )

        # 高费率12%
        pos_high = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=entry_date,
            margin_rate=0.12
        )

        # 价格不变（只看利息影响）
        pnl_low = pos_low.calculate_profit_loss(10.0, close_date)
        pnl_high = pos_high.calculate_profit_loss(10.0, close_date)

        # 高费率利息更多
        assert pnl_high['interest_cost'] > pnl_low['interest_cost']
        assert pnl_high['net_pnl'] < pnl_low['net_pnl']

        # 验证比例关系
        assert abs(pnl_high['interest_cost'] / pnl_low['interest_cost'] - 1.5) < 0.01

    def test_small_profit_eaten_by_costs(self):
        """测试小幅盈利被成本吃掉的场景"""
        entry_date = datetime(2023, 1, 1)
        close_date = datetime(2023, 3, 1)  # 60天

        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=entry_date,
            margin_rate=0.10
        )

        # 价格仅下跌1%到9.9
        pnl = pos.calculate_profit_loss(9.9, close_date)

        # 价格差收益：1%
        price_gain_pct = pnl['price_pnl'] / pos.initial_amount

        # 利息成本占比
        interest_cost_pct = pnl['interest_cost'] / pos.initial_amount

        # 利息可能已经吃掉大部分收益
        assert price_gain_pct > 0
        assert interest_cost_pct > 0
        assert pnl['net_pnl'] < pnl['price_pnl']

        # 60天，10%年化 ≈ 1.67%成本，可能导致净亏损
        expected_interest_pct = 0.10 * (60 / 360)
        assert abs(interest_cost_pct - expected_interest_pct) < 0.001


class TestEdgeCases:
    """测试边界情况"""

    def test_zero_days_holding(self):
        """测试持有0天"""
        date = datetime(2023, 1, 1)

        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=date,
            margin_rate=0.10
        )

        # 同一天
        interest = pos.calculate_margin_interest_to_date(date)
        assert interest == 0

    def test_one_year_holding(self):
        """测试持有一年"""
        entry_date = datetime(2023, 1, 1)
        close_date = datetime(2024, 1, 1)  # 365天

        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=entry_date,
            margin_rate=0.10
        )

        interest = pos.calculate_margin_interest_to_date(close_date)

        # 一年利息应该接近10%（但按360天计）
        # 365/360 * 10% * 100000 = 10138.89
        expected = 100000 * 0.10 * (365 / 360)
        assert abs(interest - expected) < 0.01

    def test_very_high_margin_rate(self):
        """测试极高融券费率"""
        pos = ShortPosition(
            stock_code='600000',
            shares=10000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            margin_rate=0.20  # 20%年化（极高）
        )

        # 持有180天
        close_date = datetime(2023, 7, 1)
        pnl = pos.calculate_profit_loss(10.0, close_date)

        # 计算实际天数
        actual_days = (close_date - datetime(2023, 1, 1)).days
        # 利息应该是本金的 (20% * actual_days/360)
        expected_interest = 100000 * 0.20 * (actual_days / 360)
        assert abs(pnl['interest_cost'] - expected_interest) < 0.01


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
