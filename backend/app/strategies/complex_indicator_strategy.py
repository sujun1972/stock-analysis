"""
复合指标策略
基于多维度技术指标组合的量化策略
"""

from typing import List

import numpy as np
import pandas as pd
from loguru import logger
from src.features import TechnicalIndicators

from .base_strategy import BaseStrategy, ParameterType, StrategyParameter


class ComplexIndicatorStrategy(BaseStrategy):
    """
    复合指标策略

    多维度信号组合:
    - 趋势维度: ADX (趋势强度) + SuperTrend
    - 超买超卖维度: RSI 或 StochRSI
    - 量价维度: OBV (能量潮) 或 MFI (资金流量指标)
    - 波动维度: ATR (用于动态止损)

    买入条件 (多因子AND逻辑):
    - Price > MA200 (长期趋势向上)
    - RSI < rsi_oversold (超卖区域)
    - OBV 向上 (资金流入)
    - ADX > adx_threshold (趋势足够强)
    - SuperTrend 为多头

    卖出条件:
    - Price < MA200 (趋势转弱)
    - RSI > rsi_overbought (超买区域)
    - OBV 向下 (资金流出)
    - SuperTrend 转为空头
    """

    @property
    def name(self) -> str:
        return "复合指标策略"

    @property
    def description(self) -> str:
        return "基于趋势、超买超卖、量价、波动四个维度的多因子组合策略"

    @property
    def version(self) -> str:
        return "1.0.0"

    @classmethod
    def get_parameters(cls) -> List[StrategyParameter]:
        """定义策略参数"""
        return [
            # 趋势维度参数
            StrategyParameter(
                name="ma_period",
                label="长期均线周期",
                type=ParameterType.INTEGER,
                default=200,
                min_value=50,
                max_value=300,
                step=10,
                description="用于判断长期趋势的移动平均线周期",
                category="趋势",
            ),
            StrategyParameter(
                name="adx_period",
                label="ADX周期",
                type=ParameterType.INTEGER,
                default=14,
                min_value=7,
                max_value=30,
                step=1,
                description="平均趋向指数计算周期",
                category="趋势",
            ),
            StrategyParameter(
                name="adx_threshold",
                label="ADX阈值",
                type=ParameterType.FLOAT,
                default=25.0,
                min_value=15.0,
                max_value=40.0,
                step=1.0,
                description="ADX > 阈值表示趋势足够强",
                category="趋势",
            ),
            StrategyParameter(
                name="supertrend_period",
                label="SuperTrend周期",
                type=ParameterType.INTEGER,
                default=10,
                min_value=7,
                max_value=20,
                step=1,
                description="SuperTrend指标计算周期",
                category="趋势",
            ),
            StrategyParameter(
                name="supertrend_multiplier",
                label="SuperTrend倍数",
                type=ParameterType.FLOAT,
                default=3.0,
                min_value=1.0,
                max_value=5.0,
                step=0.5,
                description="SuperTrend的ATR倍数",
                category="趋势",
            ),
            # 超买超卖维度参数
            StrategyParameter(
                name="rsi_period",
                label="RSI周期",
                type=ParameterType.INTEGER,
                default=14,
                min_value=7,
                max_value=30,
                step=1,
                description="相对强弱指标计算周期",
                category="超买超卖",
            ),
            StrategyParameter(
                name="rsi_oversold",
                label="RSI超卖线",
                type=ParameterType.FLOAT,
                default=30.0,
                min_value=20.0,
                max_value=40.0,
                step=5.0,
                description="RSI < 超卖线视为超卖",
                category="超买超卖",
            ),
            StrategyParameter(
                name="rsi_overbought",
                label="RSI超买线",
                type=ParameterType.FLOAT,
                default=70.0,
                min_value=60.0,
                max_value=80.0,
                step=5.0,
                description="RSI > 超买线视为超买",
                category="超买超卖",
            ),
            # 量价维度参数
            StrategyParameter(
                name="use_obv",
                label="使用OBV指标",
                type=ParameterType.BOOLEAN,
                default=True,
                description="是否使用能量潮指标",
                category="量价",
            ),
            StrategyParameter(
                name="mfi_period",
                label="MFI周期",
                type=ParameterType.INTEGER,
                default=14,
                min_value=7,
                max_value=30,
                step=1,
                description="资金流量指标计算周期",
                category="量价",
            ),
            # 波动维度参数
            StrategyParameter(
                name="atr_period",
                label="ATR周期",
                type=ParameterType.INTEGER,
                default=14,
                min_value=7,
                max_value=30,
                step=1,
                description="平均真实波幅计算周期",
                category="波动",
            ),
            StrategyParameter(
                name="stop_loss_atr_multiplier",
                label="止损ATR倍数",
                type=ParameterType.FLOAT,
                default=2.0,
                min_value=1.0,
                max_value=5.0,
                step=0.5,
                description="动态止损 = 当前价 - ATR × 倍数",
                category="风险控制",
            ),
            # 信号强度要求
            StrategyParameter(
                name="min_signal_strength",
                label="最小信号强度",
                type=ParameterType.INTEGER,
                default=3,
                min_value=2,
                max_value=5,
                step=1,
                description="至少满足几个条件才产生信号",
                category="信号过滤",
            ),
        ]

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        生成交易信号

        参数:
            data: OHLCV数据，列名必须为小写 (open, high, low, close, volume)

        返回:
            信号序列 (1=买入, -1=卖出, 0=持有)
        """
        logger.info(f"开始生成复合指标信号，数据长度: {len(data)}")

        # 复制数据避免修改原始数据
        df = data.copy()

        # 确保列名为小写
        df.columns = df.columns.str.lower()

        # 计算所有技术指标
        df = self._calculate_indicators(df)

        # 初始化信号
        signals = pd.Series(0, index=df.index)

        # 生成买入信号
        buy_signals = self._generate_buy_signals(df)
        signals[buy_signals] = 1

        # 生成卖出信号
        sell_signals = self._generate_sell_signals(df)
        signals[sell_signals] = -1

        logger.info(f"信号生成完成: 买入={buy_signals.sum()}, 卖出={sell_signals.sum()}")

        return signals

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """使用 TechnicalIndicators 计算所有技术指标"""

        # 获取参数
        ma_period = self.params.get("ma_period", 200)
        rsi_period = self.params.get("rsi_period", 14)
        adx_period = self.params.get("adx_period", 14)
        atr_period = self.params.get("atr_period", 14)
        use_obv = self.params.get("use_obv", True)

        # 使用 TechnicalIndicators 类计算指标
        ti = TechnicalIndicators(df)

        # 1. 趋势指标
        # MA均线
        df = ti.add_ma(periods=[ma_period, 20])

        # 2. 超买超卖指标
        # RSI（注意：add_rsi使用periods列表参数）
        df = ti.add_rsi(periods=[rsi_period])
        # 重命名为通用RSI列名
        df["RSI"] = df[f"RSI{rsi_period}"]

        # 3. 量价指标
        # OBV (能量潮) - 指定 volume 列名
        if use_obv:
            df = ti.add_obv(volume_col="volume")
            # OBV移动平均
            if "OBV" in df.columns:
                df["OBV_MA"] = df["OBV"].rolling(window=20).mean()

        # 4. 波动指标
        # ATR (平均真实波幅)
        df = ti.add_atr(periods=[atr_period])

        # 布林带
        df = ti.add_bollinger_bands()

        # ADX (趋势强度) - 手动计算简化版
        # 使用价格变动作为趋势强度的代理
        df["ADX"] = df["close"].pct_change().abs().rolling(window=adx_period).mean() * 100

        # SuperTrend (简化版 - 使用ATR)
        atr_col = f"ATR{atr_period}"
        if atr_col in df.columns:
            multiplier = self.params.get("supertrend_multiplier", 3.0)
            hl_avg = (df["high"] + df["low"]) / 2
            upperband = hl_avg + (multiplier * df[atr_col])
            lowerband = hl_avg - (multiplier * df[atr_col])

            supertrend = np.zeros(len(df))
            for i in range(1, len(df)):
                if df["close"].iloc[i] > upperband.iloc[i - 1]:
                    supertrend[i] = 1  # 多头
                elif df["close"].iloc[i] < lowerband.iloc[i - 1]:
                    supertrend[i] = -1  # 空头
                else:
                    supertrend[i] = supertrend[i - 1]  # 保持
            df["SuperTrend"] = supertrend

        return df

    def _generate_buy_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        生成买入信号 - 多因子AND逻辑

        买入条件:
        1. Price > MA200 (长期趋势向上)
        2. RSI < oversold (超卖)
        3. OBV > OBV_MA (资金流入)
        4. ADX > threshold (趋势足够强)
        5. SuperTrend = 1 (多头趋势)
        """
        ma_period = self.params.get("ma_period", 200)
        rsi_oversold = self.params.get("rsi_oversold", 30.0)
        adx_threshold = self.params.get("adx_threshold", 25.0)
        min_strength = self.params.get("min_signal_strength", 3)

        # 初始化条件计数器
        conditions_met = pd.Series(0, index=df.index)

        # 条件1: 价格在长期均线之上
        if f"MA{ma_period}" in df.columns:
            condition1 = df["close"] > df[f"MA{ma_period}"]
            conditions_met += condition1.astype(int)

        # 条件2: RSI超卖
        if "RSI" in df.columns:
            condition2 = df["RSI"] < rsi_oversold
            conditions_met += condition2.astype(int)

        # 条件3: OBV向上（资金流入）
        if "OBV" in df.columns and "OBV_MA" in df.columns:
            condition3 = df["OBV"] > df["OBV_MA"]
            conditions_met += condition3.astype(int)

        # 条件4: ADX足够强
        if "ADX" in df.columns:
            condition4 = df["ADX"] > adx_threshold
            conditions_met += condition4.astype(int)

        # 条件5: SuperTrend多头
        if "SuperTrend" in df.columns:
            condition5 = df["SuperTrend"] == 1
            conditions_met += condition5.astype(int)

        # 满足最小信号强度要求
        buy_signals = conditions_met >= min_strength

        return buy_signals

    def _generate_sell_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        生成卖出信号

        卖出条件:
        1. Price < MA200 (趋势转弱)
        2. RSI > overbought (超买)
        3. OBV < OBV_MA (资金流出)
        4. SuperTrend = -1 (空头趋势)
        """
        ma_period = self.params.get("ma_period", 200)
        rsi_overbought = self.params.get("rsi_overbought", 70.0)
        min_strength = self.params.get("min_signal_strength", 3)

        # 初始化条件计数器
        conditions_met = pd.Series(0, index=df.index)

        # 条件1: 价格跌破长期均线
        if f"MA{ma_period}" in df.columns:
            condition1 = df["close"] < df[f"MA{ma_period}"]
            conditions_met += condition1.astype(int)

        # 条件2: RSI超买
        if "RSI" in df.columns:
            condition2 = df["RSI"] > rsi_overbought
            conditions_met += condition2.astype(int)

        # 条件3: OBV向下（资金流出）
        if "OBV" in df.columns and "OBV_MA" in df.columns:
            condition3 = df["OBV"] < df["OBV_MA"]
            conditions_met += condition3.astype(int)

        # 条件4: SuperTrend空头
        if "SuperTrend" in df.columns:
            condition4 = df["SuperTrend"] == -1
            conditions_met += condition4.astype(int)

        # 满足最小信号强度要求
        sell_signals = conditions_met >= min_strength

        return sell_signals
