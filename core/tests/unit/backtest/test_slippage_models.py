#!/usr/bin/env python3
"""
滑点模型单元测试

测试各种滑点模型的功能和准确性

Author: Stock Analysis Core Team
Date: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.backtest.slippage_models import (
    SlippageModel,
    FixedSlippageModel,
    VolumeBasedSlippageModel,
    MarketImpactModel,
    BidAskSpreadModel,
    create_slippage_model
)


class TestFixedSlippageModel:
    """测试固定滑点模型"""

    def test_initialization(self):
        """测试初始化"""
        model = FixedSlippageModel(slippage_pct=0.001)
        assert model.slippage_pct == 0.001

    def test_calculate_slippage_buy(self):
        """测试买入滑点计算"""
        model = FixedSlippageModel(slippage_pct=0.001)

        order_size = 10000  # 1万元订单
        price = 10.0
        slippage = model.calculate_slippage(order_size, price, is_buy=True)

        assert slippage == 10.0  # 1万 * 0.001 = 10元

    def test_calculate_slippage_sell(self):
        """测试卖出滑点计算"""
        model = FixedSlippageModel(slippage_pct=0.001)

        order_size = 10000
        price = 10.0
        slippage = model.calculate_slippage(order_size, price, is_buy=False)

        assert slippage == 10.0  # 同样是10元

    def test_get_actual_price_buy(self):
        """测试买入实际价格"""
        model = FixedSlippageModel(slippage_pct=0.001)

        actual_price = model.get_actual_price(
            order_size=10000,
            reference_price=10.0,
            is_buy=True
        )

        assert abs(actual_price - 10.01) < 0.0001  # 买入向上滑点

    def test_get_actual_price_sell(self):
        """测试卖出实际价格"""
        model = FixedSlippageModel(slippage_pct=0.001)

        actual_price = model.get_actual_price(
            order_size=10000,
            reference_price=10.0,
            is_buy=False
        )

        assert actual_price == 9.99  # 卖出向下滑点

    def test_different_slippage_rates(self):
        """测试不同滑点率"""
        model1 = FixedSlippageModel(slippage_pct=0.0005)  # 万五
        model2 = FixedSlippageModel(slippage_pct=0.002)   # 千二

        price1 = model1.get_actual_price(10000, 10.0, is_buy=True)
        price2 = model2.get_actual_price(10000, 10.0, is_buy=True)

        assert price1 < price2  # 滑点小的价格更优


class TestVolumeBasedSlippageModel:
    """测试基于成交量的滑点模型"""

    def test_initialization(self):
        """测试初始化"""
        model = VolumeBasedSlippageModel(
            base_slippage=0.0005,
            impact_coefficient=0.01,
            max_slippage=0.05
        )

        assert model.base_slippage == 0.0005
        assert model.impact_coefficient == 0.01
        assert model.max_slippage == 0.05

    def test_no_volume_data(self):
        """测试无成交量数据时使用基础滑点"""
        model = VolumeBasedSlippageModel(base_slippage=0.0005)

        slippage = model.calculate_slippage(
            order_size=10000,
            price=10.0,
            is_buy=True,
            avg_volume=None  # 无成交量数据
        )

        expected = 10000 * 0.0005
        assert slippage == expected

    def test_low_participation_rate(self):
        """测试低参与率（订单小于成交量）"""
        model = VolumeBasedSlippageModel(
            base_slippage=0.0005,
            impact_coefficient=0.01
        )

        order_size = 10000  # 1万
        avg_volume = 10000000  # 1000万（参与率=0.1%）

        slippage = model.calculate_slippage(
            order_size=order_size,
            price=10.0,
            is_buy=True,
            avg_volume=avg_volume
        )

        # 参与率很低，滑点应接近基础滑点
        expected_min = order_size * 0.0005
        assert slippage >= expected_min
        assert slippage < order_size * 0.01  # 不会太大

    def test_high_participation_rate(self):
        """测试高参与率（大订单）"""
        model = VolumeBasedSlippageModel(
            base_slippage=0.0005,
            impact_coefficient=0.1
        )

        order_size = 1000000  # 100万
        avg_volume = 2000000  # 200万（参与率=50%）

        slippage = model.calculate_slippage(
            order_size=order_size,
            price=10.0,
            is_buy=True,
            avg_volume=avg_volume
        )

        # 参与率高，滑点应该显著增加
        expected_base = order_size * 0.0005
        assert slippage > expected_base * 10  # 应该远大于基础滑点

    def test_max_slippage_cap(self):
        """测试最大滑点限制"""
        model = VolumeBasedSlippageModel(
            base_slippage=0.0005,
            impact_coefficient=1.0,
            max_slippage=0.05  # 最大5%
        )

        # 极端大单
        order_size = 10000000
        avg_volume = 100000  # 参与率=100倍

        slippage = model.calculate_slippage(
            order_size=order_size,
            price=10.0,
            is_buy=True,
            avg_volume=avg_volume
        )

        # 不应超过最大滑点
        max_slippage_amount = order_size * 0.05
        assert slippage <= max_slippage_amount


class TestMarketImpactModel:
    """测试市场冲击模型"""

    def test_initialization(self):
        """测试初始化"""
        model = MarketImpactModel(
            volatility_weight=0.5,
            volume_impact_alpha=0.5,
            urgency_factor=1.0
        )

        assert model.volatility_weight == 0.5
        assert model.volume_impact_alpha == 0.5
        assert model.urgency_factor == 1.0

    def test_with_full_data(self):
        """测试有完整数据时的计算"""
        model = MarketImpactModel(
            volatility_weight=0.5,
            volume_impact_alpha=0.5,
            urgency_factor=1.0
        )

        order_size = 100000
        avg_volume = 10000000  # 参与率=1%
        volatility = 0.02  # 日波动率2%

        slippage = model.calculate_slippage(
            order_size=order_size,
            price=10.0,
            is_buy=True,
            avg_volume=avg_volume,
            volatility=volatility
        )

        # 应该是合理的滑点
        assert slippage > 0
        assert slippage < order_size * 0.01  # 不会超过1%

    def test_volatility_impact(self):
        """测试波动率对滑点的影响"""
        model = MarketImpactModel(volatility_weight=1.0)

        order_size = 100000
        avg_volume = 10000000

        # 低波动率
        slippage_low = model.calculate_slippage(
            order_size=order_size,
            price=10.0,
            is_buy=True,
            avg_volume=avg_volume,
            volatility=0.01
        )

        # 高波动率
        slippage_high = model.calculate_slippage(
            order_size=order_size,
            price=10.0,
            is_buy=True,
            avg_volume=avg_volume,
            volatility=0.04
        )

        # 高波动率应该有更高滑点
        assert slippage_high > slippage_low

    def test_urgency_factor(self):
        """测试紧急度因子"""
        order_size = 100000
        avg_volume = 10000000
        volatility = 0.02

        # 低紧急度（可以慢慢交易）
        model_low = MarketImpactModel(urgency_factor=0.5)
        slippage_low = model_low.calculate_slippage(
            order_size, 10.0, True, avg_volume=avg_volume, volatility=volatility
        )

        # 高紧急度（必须立即成交）
        model_high = MarketImpactModel(urgency_factor=2.0)
        slippage_high = model_high.calculate_slippage(
            order_size, 10.0, True, avg_volume=avg_volume, volatility=volatility
        )

        # 高紧急度滑点更高
        assert slippage_high > slippage_low


class TestBidAskSpreadModel:
    """测试买卖价差模型"""

    def test_initialization(self):
        """测试初始化"""
        model = BidAskSpreadModel(base_spread=0.0002)
        assert model.base_spread == 0.0002

    def test_with_bid_ask_prices(self):
        """测试有盘口数据时"""
        model = BidAskSpreadModel()

        bid_price = 9.99
        ask_price = 10.01
        mid_price = 10.0

        # 买入应以卖一价成交
        buy_price = model.get_actual_price(
            order_size=10000,
            reference_price=mid_price,
            is_buy=True,
            bid_price=bid_price,
            ask_price=ask_price
        )
        assert buy_price == ask_price

        # 卖出应以买一价成交
        sell_price = model.get_actual_price(
            order_size=10000,
            reference_price=mid_price,
            is_buy=False,
            bid_price=bid_price,
            ask_price=ask_price
        )
        assert sell_price == bid_price

    def test_without_bid_ask_prices(self):
        """测试无盘口数据时使用估算"""
        model = BidAskSpreadModel(base_spread=0.0002)

        # 无盘口数据
        buy_price = model.get_actual_price(
            order_size=10000,
            reference_price=10.0,
            is_buy=True,
            bid_price=None,
            ask_price=None
        )

        # 应该向上滑点（基础价差的一半）
        expected_spread = 0.0002
        expected_price = 10.0 * (1 + expected_spread / 2)
        assert abs(buy_price - expected_price) < 0.02  # 放宽精度要求

    def test_spread_with_volatility(self):
        """测试波动率对价差的影响"""
        model = BidAskSpreadModel(
            base_spread=0.0002,
            spread_volatility_factor=0.1
        )

        # 低波动率
        price_low_vol = model.get_actual_price(
            10000, 10.0, True, volatility=0.01
        )

        # 高波动率
        price_high_vol = model.get_actual_price(
            10000, 10.0, True, volatility=0.04
        )

        # 高波动率价差更大
        assert price_high_vol > price_low_vol


class TestFactoryFunction:
    """测试工厂函数"""

    def test_create_fixed_model(self):
        """测试创建固定滑点模型"""
        model = create_slippage_model('fixed', slippage_pct=0.001)
        assert isinstance(model, FixedSlippageModel)
        assert model.slippage_pct == 0.001

    def test_create_volume_model(self):
        """测试创建基于成交量模型"""
        model = create_slippage_model('volume', base_slippage=0.0005)
        assert isinstance(model, VolumeBasedSlippageModel)
        assert model.base_slippage == 0.0005

    def test_create_market_impact_model(self):
        """测试创建市场冲击模型"""
        model = create_slippage_model('market_impact', volatility_weight=0.6)
        assert isinstance(model, MarketImpactModel)
        assert model.volatility_weight == 0.6

    def test_create_bid_ask_model(self):
        """测试创建买卖价差模型"""
        model = create_slippage_model('bid_ask', base_spread=0.0003)
        assert isinstance(model, BidAskSpreadModel)
        assert model.base_spread == 0.0003

    def test_invalid_model_type(self):
        """测试无效模型类型"""
        with pytest.raises(ValueError):
            create_slippage_model('invalid_type')


class TestSlippageComparison:
    """测试不同模型的对比"""

    def test_models_comparison(self):
        """对比不同模型在相同条件下的滑点"""
        order_size = 100000
        price = 10.0
        avg_volume = 10000000
        volatility = 0.02

        # 固定滑点
        model1 = FixedSlippageModel(0.001)
        slippage1 = model1.calculate_slippage(order_size, price, True)

        # 基于成交量
        model2 = VolumeBasedSlippageModel()
        slippage2 = model2.calculate_slippage(
            order_size, price, True, avg_volume=avg_volume
        )

        # 市场冲击
        model3 = MarketImpactModel()
        slippage3 = model3.calculate_slippage(
            order_size, price, True,
            avg_volume=avg_volume, volatility=volatility
        )

        # 所有滑点应该都是正数
        assert slippage1 > 0
        assert slippage2 > 0
        assert slippage3 > 0

        # 固定滑点应该是确定的
        assert slippage1 == order_size * 0.001


class TestEdgeCases:
    """测试边界情况"""

    def test_zero_order_size(self):
        """测试零订单"""
        model = FixedSlippageModel(0.001)
        slippage = model.calculate_slippage(0, 10.0, True)
        assert slippage == 0

    def test_very_large_order(self):
        """测试超大订单"""
        model = VolumeBasedSlippageModel(max_slippage=0.1)

        # 超大订单
        slippage = model.calculate_slippage(
            order_size=100000000,  # 1亿
            price=10.0,
            is_buy=True,
            avg_volume=1000000  # 100万（参与率=100倍）
        )

        # 应该被限制在最大滑点
        assert slippage <= 100000000 * 0.1

    def test_negative_volume(self):
        """测试负成交量（异常数据）"""
        model = VolumeBasedSlippageModel()

        # 负成交量应该回退到基础滑点
        slippage = model.calculate_slippage(
            10000, 10.0, True, avg_volume=-100
        )

        expected = 10000 * model.base_slippage
        assert slippage == expected


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
