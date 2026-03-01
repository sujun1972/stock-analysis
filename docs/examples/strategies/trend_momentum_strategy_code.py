"""
趋势 + 动能：双重确认组合策略

策略原理：
这是最稳健的"顺势而为"方案。EMA（指数移动平均线）负责定义趋势，MACD负责捕捉爆发力。

指标组合：
- EMA (20, 60, 120)
- MACD (12, 26, 9)

入场逻辑：
1. 趋势过滤：股价位于 EMA 120 之上，且 EMA 20 > EMA 60（多头排列）
2. 动能触发：MACD 在零轴上方发生"金叉"或柱状图由负转正

核心理念：只有在大趋势向上时，才在动能转强的瞬间入场。
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from core.strategies.base_strategy import BaseStrategy


class TrendMomentumStrategy(BaseStrategy):
    """趋势+动能双重确认组合策略"""

    def __init__(self, name: str = "trend_momentum_strategy", config: Dict[str, Any] = None):
        """
        初始化策略

        Args:
            name: 策略名称
            config: 策略配置字典
        """
        # 默认配置
        default_config = {
            'name': 'TrendMomentumStrategy',
            'description': '基于EMA趋势过滤和MACD动能触发的双重确认入场策略',
            'top_n': 20,
            'holding_period': 5,
            'rebalance_freq': 'W',

            # EMA参数
            'ema_short': 20,
            'ema_mid': 60,
            'ema_long': 120,

            # MACD参数
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,

            # 入场条件参数
            'require_macd_above_zero': True,  # 要求MACD在零轴上方
            'enable_histogram_trigger': True,  # 启用柱状图触发
            'require_ema_alignment': True,  # 要求EMA多头排列

            # 离场条件参数
            'exit_on_macd_cross': True,  # MACD死叉离场
            'exit_on_ema_break': True,  # 跌破EMA60离场

            # 风险控制参数
            'min_volume_ratio': 0.8,  # 最小成交量倍数
        }

        # 合并用户配置
        if config:
            default_config.update(config)

        super().__init__(name, default_config)

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        计算股票评分（用于排序选股）

        评分逻辑：
        - 趋势强度：EMA排列程度
        - 动能强度：MACD值大小
        - 综合评分：趋势*0.6 + 动能*0.4

        Args:
            prices: 价格DataFrame (index=date, columns=stock_codes)
            features: 特征DataFrame (可选)
            date: 指定日期（None表示最新日期）

        Returns:
            scores: 股票评分Series (index=stock_codes, values=scores)
        """
        if date is None:
            date = prices.index[-1]

        scores = pd.Series(0.0, index=prices.columns)

        for stock in prices.columns:
            try:
                stock_prices = prices[stock].dropna()
                if len(stock_prices) < self.config.custom_params.get('ema_long', 120):
                    continue

                # 计算指标
                indicators = self._calculate_indicators_for_stock(stock_prices)

                if date not in indicators.index:
                    continue

                row = indicators.loc[date]

                # 评分维度1：趋势强度（EMA排列程度）
                ema_short = self.config.custom_params.get('ema_short', 20)
                ema_mid = self.config.custom_params.get('ema_mid', 60)
                ema_long = self.config.custom_params.get('ema_long', 120)

                trend_score = 0.0
                if row[f'EMA{ema_short}'] > row[f'EMA{ema_mid}']:
                    trend_score += 0.3
                if row[f'EMA{ema_mid}'] > row[f'EMA{ema_long}']:
                    trend_score += 0.3
                if row['close'] > row[f'EMA{ema_long}']:
                    trend_score += 0.4

                # 评分维度2：动能强度（MACD值）
                macd_score = 0.0
                if row['MACD'] > 0:
                    macd_score = min(row['MACD'] / 10.0, 1.0)  # 归一化到[0,1]

                # 综合评分
                scores[stock] = trend_score * 0.6 + macd_score * 0.4

            except Exception:
                continue

        return scores

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            prices: 价格DataFrame (index=date, columns=stock_codes, values=close_price)
            features: 特征DataFrame (可选)
            **kwargs: 其他参数

        Returns:
            signals: 信号DataFrame (index=date, columns=stock_codes)
                值: 1 = 买入, 0 = 持有, -1 = 卖出
        """
        # 初始化信号矩阵
        signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)

        # 逐个股票计算信号
        for stock in prices.columns:
            try:
                stock_prices = prices[stock].dropna()

                # 数据不足，跳过
                if len(stock_prices) < self.config.custom_params.get('ema_long', 120):
                    continue

                # 计算技术指标
                indicators = self._calculate_indicators_for_stock(stock_prices)

                # 生成买入信号
                buy_signals = self._generate_buy_signals(indicators)

                # 生成卖出信号
                sell_signals = self._generate_sell_signals(indicators)

                # 合并信号到主信号矩阵
                common_index = signals.index.intersection(indicators.index)
                signals.loc[common_index, stock] = 0  # 默认持有
                signals.loc[common_index[buy_signals.loc[common_index]], stock] = 1  # 买入
                signals.loc[common_index[sell_signals.loc[common_index]], stock] = -1  # 卖出

            except Exception as e:
                # 异常股票跳过
                continue

        return signals

    def _calculate_indicators_for_stock(self, prices: pd.Series) -> pd.DataFrame:
        """
        为单只股票计算技术指标

        Args:
            prices: 单只股票的价格序列

        Returns:
            indicators: 包含所有指标的DataFrame
        """
        df = pd.DataFrame({'close': prices})

        # ========== EMA 趋势指标 ==========
        ema_short = self.config.custom_params.get('ema_short', 20)
        ema_mid = self.config.custom_params.get('ema_mid', 60)
        ema_long = self.config.custom_params.get('ema_long', 120)

        df[f'EMA{ema_short}'] = df['close'].ewm(span=ema_short, adjust=False).mean()
        df[f'EMA{ema_mid}'] = df['close'].ewm(span=ema_mid, adjust=False).mean()
        df[f'EMA{ema_long}'] = df['close'].ewm(span=ema_long, adjust=False).mean()

        # ========== MACD 动能指标 ==========
        macd_fast = self.config.custom_params.get('macd_fast', 12)
        macd_slow = self.config.custom_params.get('macd_slow', 26)
        macd_signal = self.config.custom_params.get('macd_signal', 9)

        ema_fast = df['close'].ewm(span=macd_fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=macd_slow, adjust=False).mean()

        df['MACD'] = ema_fast - ema_slow
        df['MACD_SIGNAL'] = df['MACD'].ewm(span=macd_signal, adjust=False).mean()
        df['MACD_HIST'] = df['MACD'] - df['MACD_SIGNAL']

        # ========== 辅助信号 ==========
        # MACD��叉
        df['MACD_CROSS_UP'] = (
            (df['MACD'] > df['MACD_SIGNAL']) &
            (df['MACD'].shift(1) <= df['MACD_SIGNAL'].shift(1))
        )

        # MACD死叉
        df['MACD_CROSS_DOWN'] = (
            (df['MACD'] < df['MACD_SIGNAL']) &
            (df['MACD'].shift(1) >= df['MACD_SIGNAL'].shift(1))
        )

        # 柱状图由负转正
        df['HIST_TURN_POSITIVE'] = (
            (df['MACD_HIST'] > 0) &
            (df['MACD_HIST'].shift(1) <= 0)
        )

        # EMA多头排列
        df['EMA_BULLISH'] = df[f'EMA{ema_short}'] > df[f'EMA{ema_mid}']

        # 价格在长期均线上方
        df['ABOVE_LONG_EMA'] = df['close'] > df[f'EMA{ema_long}']

        return df

    def _generate_buy_signals(self, indicators: pd.DataFrame) -> pd.Series:
        """
        生成买入信号

        买入条件 (AND逻辑)：
        1. 趋势过滤：股价 > EMA120
        2. 多头排列：EMA20 > EMA60（可选）
        3. 动能触发：MACD金叉（零轴上方）或 柱状图由负转正

        Args:
            indicators: 指标DataFrame

        Returns:
            buy_signals: 买入信号Series (布尔值)
        """
        # 初始化条件
        conditions = pd.Series(True, index=indicators.index)

        # ========== 条件1: 趋势过滤 ==========
        conditions &= indicators['ABOVE_LONG_EMA']

        # ========== 条件2: 多头排列（可选）==========
        if self.config.custom_params.get('require_ema_alignment', True):
            conditions &= indicators['EMA_BULLISH']

        # ========== 条件3: 动能触发 ==========
        momentum_trigger = pd.Series(False, index=indicators.index)

        # 3.1 MACD金叉
        if self.config.custom_params.get('require_macd_above_zero', True):
            # 要求在零轴上方金叉
            macd_trigger = indicators['MACD_CROSS_UP'] & (indicators['MACD'] > 0)
        else:
            # 任意位置金叉
            macd_trigger = indicators['MACD_CROSS_UP']

        momentum_trigger |= macd_trigger

        # 3.2 柱状图由负转正（可选）
        if self.config.custom_params.get('enable_histogram_trigger', True):
            momentum_trigger |= indicators['HIST_TURN_POSITIVE']

        conditions &= momentum_trigger

        # 过滤前期无效数据
        ema_long = self.config.custom_params.get('ema_long', 120)
        conditions[:ema_long] = False

        return conditions

    def _generate_sell_signals(self, indicators: pd.DataFrame) -> pd.Series:
        """
        生成卖出信号

        卖出条件 (OR逻辑)：
        1. MACD死叉（可选）
        2. 股价跌破 EMA60（可选）

        Args:
            indicators: 指标DataFrame

        Returns:
            sell_signals: 卖出信号Series (布尔值)
        """
        # 初始化信号
        sell_signal = pd.Series(False, index=indicators.index)

        # ========== 离场条件1: MACD死叉 ==========
        if self.config.custom_params.get('exit_on_macd_cross', True):
            sell_signal |= indicators['MACD_CROSS_DOWN']

        # ========== 离场条件2: 跌破中期均线 ==========
        if self.config.custom_params.get('exit_on_ema_break', True):
            ema_mid = self.config.custom_params.get('ema_mid', 60)
            price_break_ema = (
                (indicators['close'] < indicators[f'EMA{ema_mid}']) &
                (indicators['close'].shift(1) >= indicators[f'EMA{ema_mid}'].shift(1))
            )
            sell_signal |= price_break_ema

        return sell_signal
