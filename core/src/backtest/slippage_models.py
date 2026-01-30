"""
滑点模型

提供多种滑点计算方法，从简单的固定滑点到复杂的市场冲击模型

滑点类型:
1. FixedSlippageModel - 固定比例滑点（最简单）
2. VolumeBasedSlippageModel - 基于成交量的滑点（考虑流动性）
3. MarketImpactModel - 市场冲击成本模型（最真实）
4. BidAskSpreadModel - 买卖价差模型（适合高频）

Author: Stock Analysis Core Team
Date: 2026-01-30
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Dict
from loguru import logger


class SlippageModel(ABC):
    """滑点模型基类"""

    @abstractmethod
    def calculate_slippage(
        self,
        order_size: float,
        price: float,
        is_buy: bool,
        **kwargs
    ) -> float:
        """
        计算滑点

        参数:
            order_size: 订单金额（元）
            price: 参考价格
            is_buy: 是否买入
            **kwargs: 其他参数（如成交量、波动率等）

        返回:
            滑点金额（元）
        """
        pass

    @abstractmethod
    def get_actual_price(
        self,
        order_size: float,
        reference_price: float,
        is_buy: bool,
        **kwargs
    ) -> float:
        """
        计算实际成交价格

        参数:
            order_size: 订单金额（元）
            reference_price: 参考价格（如开盘价）
            is_buy: 是否买入
            **kwargs: 其他参数

        返回:
            实际成交价格
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class FixedSlippageModel(SlippageModel):
    """
    固定滑点模型

    最简单的滑点模型，使用固定比例计算滑点

    适用场景:
        - 快速回测
        - 流动性好的大盘股
        - 对真实性要求不高的场景

    示例:
        >>> model = FixedSlippageModel(slippage_pct=0.001)  # 千一滑点
        >>> actual_price = model.get_actual_price(
        ...     order_size=10000,
        ...     reference_price=10.0,
        ...     is_buy=True
        ... )
        >>> print(actual_price)  # 10.01 (买入时向上滑点)
    """

    def __init__(self, slippage_pct: float = 0.001):
        """
        初始化固定滑点模型

        参数:
            slippage_pct: 滑点比例（默认0.001=千一）
        """
        self.slippage_pct = slippage_pct

    def calculate_slippage(
        self,
        order_size: float,
        price: float,
        is_buy: bool,
        **kwargs
    ) -> float:
        """计算滑点金额"""
        return order_size * self.slippage_pct

    def get_actual_price(
        self,
        order_size: float,
        reference_price: float,
        is_buy: bool,
        **kwargs
    ) -> float:
        """计算实际成交价格"""
        if is_buy:
            # 买入时价格向上滑点
            return reference_price * (1 + self.slippage_pct)
        else:
            # 卖出时价格向下滑点
            return reference_price * (1 - self.slippage_pct)

    def __repr__(self) -> str:
        return f"FixedSlippageModel(slippage_pct={self.slippage_pct})"


class VolumeBasedSlippageModel(SlippageModel):
    """
    基于成交量的滑点模型

    考虑订单规模占成交量的比例，规模越大滑点越大

    滑点计算:
        participation_rate = order_size / avg_volume
        slippage_pct = base_slippage + impact_coefficient * sqrt(participation_rate)

    适用场景:
        - 需要考虑流动性的回测
        - 大资金策略
        - 小盘股策略

    示例:
        >>> model = VolumeBasedSlippageModel(
        ...     base_slippage=0.0005,
        ...     impact_coefficient=0.01
        ... )
        >>> actual_price = model.get_actual_price(
        ...     order_size=100000,
        ...     reference_price=10.0,
        ...     is_buy=True,
        ...     avg_volume=10000000  # 日均成交量1000万
        ... )
    """

    def __init__(
        self,
        base_slippage: float = 0.0005,
        impact_coefficient: float = 0.01,
        max_slippage: float = 0.05
    ):
        """
        初始化基于成交量的滑点模型

        参数:
            base_slippage: 基础滑点（默认万五）
            impact_coefficient: 冲击系数（默认0.01）
            max_slippage: 最大滑点（默认5%，防止异常值）
        """
        self.base_slippage = base_slippage
        self.impact_coefficient = impact_coefficient
        self.max_slippage = max_slippage

    def calculate_slippage(
        self,
        order_size: float,
        price: float,
        is_buy: bool,
        avg_volume: Optional[float] = None,
        **kwargs
    ) -> float:
        """
        计算滑点金额

        参数:
            order_size: 订单金额
            price: 参考价格
            is_buy: 是否买入
            avg_volume: 平均成交金额（日均）

        返回:
            滑点金额
        """
        if avg_volume is None or avg_volume <= 0:
            # 如果没有成交量数据，使用基础滑点
            slippage_pct = self.base_slippage
        else:
            # 计算参与率（订单占日均成交量的比例）
            participation_rate = order_size / avg_volume

            # 滑点 = 基础滑点 + 冲击系数 * sqrt(参与率)
            # 使用平方根是经典的市场冲击模型（Almgren-Chriss模型）
            slippage_pct = self.base_slippage + self.impact_coefficient * np.sqrt(participation_rate)

            # 限制最大滑点
            slippage_pct = min(slippage_pct, self.max_slippage)

        return order_size * slippage_pct

    def get_actual_price(
        self,
        order_size: float,
        reference_price: float,
        is_buy: bool,
        avg_volume: Optional[float] = None,
        **kwargs
    ) -> float:
        """计算实际成交价格"""
        if avg_volume is None or avg_volume <= 0:
            slippage_pct = self.base_slippage
        else:
            participation_rate = order_size / avg_volume
            slippage_pct = self.base_slippage + self.impact_coefficient * np.sqrt(participation_rate)
            slippage_pct = min(slippage_pct, self.max_slippage)

        if is_buy:
            return reference_price * (1 + slippage_pct)
        else:
            return reference_price * (1 - slippage_pct)

    def __repr__(self) -> str:
        return (f"VolumeBasedSlippageModel(base={self.base_slippage}, "
                f"impact={self.impact_coefficient}, max={self.max_slippage})")


class MarketImpactModel(SlippageModel):
    """
    市场冲击成本模型

    考虑多种因素的综合滑点模型，包括:
    - 订单规模（相对日均成交量）
    - 市场波动率
    - 价格水平
    - 订单紧急程度

    基于研究文献的实证模型:
        slippage = sigma * (order_size / adv)^alpha * urgency_factor

    其中:
        - sigma: 市场波动率
        - adv: 平均日成交量 (Average Daily Volume)
        - alpha: 幂次（通常0.5-0.6）
        - urgency_factor: 紧急度因子（立即成交=高，可分批=低）

    适用场景:
        - 高精度回测
        - 大资金量化策略
        - 学术研究

    示例:
        >>> model = MarketImpactModel(
        ...     volatility_weight=0.5,
        ...     volume_impact_alpha=0.5,
        ...     urgency_factor=1.0
        ... )
        >>> actual_price = model.get_actual_price(
        ...     order_size=100000,
        ...     reference_price=10.0,
        ...     is_buy=True,
        ...     avg_volume=10000000,
        ...     volatility=0.02  # 日波动率2%
        ... )
    """

    def __init__(
        self,
        volatility_weight: float = 0.5,
        volume_impact_alpha: float = 0.5,
        urgency_factor: float = 1.0,
        max_slippage: float = 0.1
    ):
        """
        初始化市场冲击模型

        参数:
            volatility_weight: 波动率权重（默认0.5）
            volume_impact_alpha: 成交量冲击幂次（默认0.5）
            urgency_factor: 紧急度因子（默认1.0，范围0.5-2.0）
            max_slippage: 最大滑点（默认10%）
        """
        self.volatility_weight = volatility_weight
        self.volume_impact_alpha = volume_impact_alpha
        self.urgency_factor = urgency_factor
        self.max_slippage = max_slippage

    def calculate_slippage(
        self,
        order_size: float,
        price: float,
        is_buy: bool,
        avg_volume: Optional[float] = None,
        volatility: Optional[float] = None,
        **kwargs
    ) -> float:
        """
        计算滑点金额

        参数:
            order_size: 订单金额
            price: 参考价格
            is_buy: 是否买入
            avg_volume: 平均成交金额
            volatility: 日波动率

        返回:
            滑点金额
        """
        # 默认值
        if avg_volume is None or avg_volume <= 0:
            avg_volume = order_size * 100  # 假设订单占日成交1%

        if volatility is None or volatility <= 0:
            volatility = 0.02  # 默认日波动率2%

        # 计算参与率
        participation_rate = order_size / avg_volume

        # 市场冲击公式
        # slippage = volatility * (participation_rate ^ alpha) * urgency_factor
        volume_impact = participation_rate ** self.volume_impact_alpha

        slippage_pct = (
            self.volatility_weight * volatility * volume_impact * self.urgency_factor
        )

        # 限制最大滑点
        slippage_pct = min(slippage_pct, self.max_slippage)

        return order_size * slippage_pct

    def get_actual_price(
        self,
        order_size: float,
        reference_price: float,
        is_buy: bool,
        avg_volume: Optional[float] = None,
        volatility: Optional[float] = None,
        **kwargs
    ) -> float:
        """计算实际成交价格"""
        # 计算滑点金额
        slippage_amount = self.calculate_slippage(
            order_size=order_size,
            price=reference_price,
            is_buy=is_buy,
            avg_volume=avg_volume,
            volatility=volatility
        )

        # 滑点比例
        slippage_pct = slippage_amount / order_size if order_size > 0 else 0

        if is_buy:
            return reference_price * (1 + slippage_pct)
        else:
            return reference_price * (1 - slippage_pct)

    def __repr__(self) -> str:
        return (f"MarketImpactModel(vol_weight={self.volatility_weight}, "
                f"alpha={self.volume_impact_alpha}, urgency={self.urgency_factor})")


class BidAskSpreadModel(SlippageModel):
    """
    买卖价差模型

    基于盘口买卖价差的滑点模型

    滑点计算:
        - 买入: 以卖一价成交，滑点 = (ask_price - mid_price)
        - 卖出: 以买一价成交，滑点 = (mid_price - bid_price)
        - 中间价: mid_price = (ask_price + bid_price) / 2

    如果没有盘口数据，使用估算:
        spread_pct = base_spread + volatility * spread_volatility_factor

    适用场景:
        - 高频策略回测
        - 有盘口数据的场景
        - 日内交易

    示例:
        >>> model = BidAskSpreadModel(base_spread=0.0002)
        >>> actual_price = model.get_actual_price(
        ...     order_size=10000,
        ...     reference_price=10.0,
        ...     is_buy=True,
        ...     bid_price=9.99,
        ...     ask_price=10.01
        ... )
        >>> print(actual_price)  # 10.01 (买入以卖一价成交)
    """

    def __init__(
        self,
        base_spread: float = 0.0002,
        spread_volatility_factor: float = 0.1
    ):
        """
        初始化买卖价差模型

        参数:
            base_spread: 基础价差（默认万二）
            spread_volatility_factor: 价差波动率因子（默认0.1）
        """
        self.base_spread = base_spread
        self.spread_volatility_factor = spread_volatility_factor

    def calculate_slippage(
        self,
        order_size: float,
        price: float,
        is_buy: bool,
        bid_price: Optional[float] = None,
        ask_price: Optional[float] = None,
        volatility: Optional[float] = None,
        **kwargs
    ) -> float:
        """
        计算滑点金额

        参数:
            order_size: 订单金额
            price: 参考价格（中间价）
            is_buy: 是否买入
            bid_price: 买一价
            ask_price: 卖一价
            volatility: 波动率（用于估算价差）

        返回:
            滑点金额
        """
        if bid_price is not None and ask_price is not None:
            # 有盘口数据
            mid_price = (bid_price + ask_price) / 2

            if is_buy:
                # 买入以卖一价成交
                slippage_per_share = ask_price - mid_price
            else:
                # 卖出以买一价成交
                slippage_per_share = mid_price - bid_price

            # 计算总滑点
            shares = order_size / price if price > 0 else 0
            return slippage_per_share * shares

        else:
            # 没有盘口数据，估算价差
            if volatility is None:
                volatility = 0.02  # 默认2%

            # 估算价差 = 基础价差 + 波动率因子
            spread_pct = self.base_spread + volatility * self.spread_volatility_factor

            # 滑点为半个价差
            slippage_pct = spread_pct / 2

            return order_size * slippage_pct

    def get_actual_price(
        self,
        order_size: float,
        reference_price: float,
        is_buy: bool,
        bid_price: Optional[float] = None,
        ask_price: Optional[float] = None,
        volatility: Optional[float] = None,
        **kwargs
    ) -> float:
        """计算实际成交价格"""
        if bid_price is not None and ask_price is not None:
            # 有盘口数据
            if is_buy:
                return ask_price  # 买入以卖一价成交
            else:
                return bid_price  # 卖出以买一价成交
        else:
            # 没有盘口数据，估算
            if volatility is None:
                volatility = 0.02

            spread_pct = self.base_spread + volatility * self.spread_volatility_factor
            half_spread = spread_pct / 2

            if is_buy:
                return reference_price * (1 + half_spread)
            else:
                return reference_price * (1 - half_spread)

    def __repr__(self) -> str:
        return f"BidAskSpreadModel(base_spread={self.base_spread})"


# ==================== 工厂函数 ====================

def create_slippage_model(model_type: str, **params) -> SlippageModel:
    """
    创建滑点模型的工厂函数

    参数:
        model_type: 模型类型
            - 'fixed': 固定滑点
            - 'volume': 基于成交量
            - 'market_impact': 市场冲击
            - 'bid_ask': 买卖价差
        **params: 模型参数

    返回:
        滑点模型实例

    示例:
        >>> model = create_slippage_model('fixed', slippage_pct=0.001)
        >>> model = create_slippage_model('volume', base_slippage=0.0005)
    """
    models = {
        'fixed': FixedSlippageModel,
        'volume': VolumeBasedSlippageModel,
        'market_impact': MarketImpactModel,
        'bid_ask': BidAskSpreadModel
    }

    if model_type not in models:
        raise ValueError(
            f"未知的滑点模型类型: {model_type}. "
            f"可选: {list(models.keys())}"
        )

    return models[model_type](**params)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    logger.info("滑点模型测试\n")

    # 测试参数
    order_size = 100000  # 10万元订单
    reference_price = 10.0
    avg_volume = 10000000  # 日均成交1000万
    volatility = 0.02  # 日波动率2%

    logger.info("测试场景:")
    logger.info(f"  订单金额: {order_size:,.0f} 元")
    logger.info(f"  参考价格: {reference_price:.2f} 元")
    logger.info(f"  日均成交量: {avg_volume:,.0f} 元")
    logger.info(f"  日波动率: {volatility*100:.1f}%")
    logger.info(f"  参与率: {order_size/avg_volume*100:.2f}%")

    # 1. 固定滑点
    logger.info("\n1. 固定滑点模型（千一）:")
    model1 = FixedSlippageModel(slippage_pct=0.001)

    buy_price1 = model1.get_actual_price(order_size, reference_price, is_buy=True)
    sell_price1 = model1.get_actual_price(order_size, reference_price, is_buy=False)

    logger.info(f"  买入价: {buy_price1:.4f} (滑点 {(buy_price1-reference_price)/reference_price*10000:.1f} bps)")
    logger.info(f"  卖出价: {sell_price1:.4f} (滑点 {(reference_price-sell_price1)/reference_price*10000:.1f} bps)")

    # 2. 基于成交量
    logger.info("\n2. 基于成交量滑点模型:")
    model2 = VolumeBasedSlippageModel(base_slippage=0.0005, impact_coefficient=0.01)

    buy_price2 = model2.get_actual_price(
        order_size, reference_price, is_buy=True, avg_volume=avg_volume
    )
    sell_price2 = model2.get_actual_price(
        order_size, reference_price, is_buy=False, avg_volume=avg_volume
    )

    logger.info(f"  买入价: {buy_price2:.4f} (滑点 {(buy_price2-reference_price)/reference_price*10000:.1f} bps)")
    logger.info(f"  卖出价: {sell_price2:.4f} (滑点 {(reference_price-sell_price2)/reference_price*10000:.1f} bps)")

    # 3. 市场冲击
    logger.info("\n3. 市场冲击模型:")
    model3 = MarketImpactModel(volatility_weight=0.5, volume_impact_alpha=0.5)

    buy_price3 = model3.get_actual_price(
        order_size, reference_price, is_buy=True,
        avg_volume=avg_volume, volatility=volatility
    )
    sell_price3 = model3.get_actual_price(
        order_size, reference_price, is_buy=False,
        avg_volume=avg_volume, volatility=volatility
    )

    logger.info(f"  买入价: {buy_price3:.4f} (滑点 {(buy_price3-reference_price)/reference_price*10000:.1f} bps)")
    logger.info(f"  卖出价: {sell_price3:.4f} (滑点 {(reference_price-sell_price3)/reference_price*10000:.1f} bps)")

    # 4. 买卖价差
    logger.info("\n4. 买卖价差模型:")
    model4 = BidAskSpreadModel(base_spread=0.0002)

    bid_price = 9.99
    ask_price = 10.01

    buy_price4 = model4.get_actual_price(
        order_size, reference_price, is_buy=True,
        bid_price=bid_price, ask_price=ask_price
    )
    sell_price4 = model4.get_actual_price(
        order_size, reference_price, is_buy=False,
        bid_price=bid_price, ask_price=ask_price
    )

    logger.info(f"  盘口: 买一={bid_price:.2f}, 卖一={ask_price:.2f}")
    logger.info(f"  买入价: {buy_price4:.4f} (以卖一价成交)")
    logger.info(f"  卖出价: {sell_price4:.4f} (以买一价成交)")

    # 对比
    logger.info("\n对比总结:")
    logger.info("  模型              买入价   买入滑点(bps)")
    logger.info("  " + "-" * 45)
    logger.info(f"  固定滑点         {buy_price1:.4f}   {(buy_price1-reference_price)/reference_price*10000:>6.1f}")
    logger.info(f"  基于成交量       {buy_price2:.4f}   {(buy_price2-reference_price)/reference_price*10000:>6.1f}")
    logger.info(f"  市场冲击         {buy_price3:.4f}   {(buy_price3-reference_price)/reference_price*10000:>6.1f}")
    logger.info(f"  买卖价差         {buy_price4:.4f}   {(buy_price4-reference_price)/reference_price*10000:>6.1f}")

    logger.success("\n✓ 滑点模型测试完成")
