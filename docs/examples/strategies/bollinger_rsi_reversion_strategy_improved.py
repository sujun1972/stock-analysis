"""
布林带 + RSI 均值回归策略（改进版）

修复了原版本的以下问题：
1. 配置参数访问方式（使用 custom_params）
2. 信号赋值方式（避免索引错误）
3. 优化了评分逻辑
4. 增加了数据验证
5. 添加了更详细的注释
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from core.strategies.base_strategy import BaseStrategy


class BollingerRSIReversionStrategy(BaseStrategy):
    """
    布林带 + RSI 均值回归策略

    该策略利用布林带确定价格的统计学边界，并结合 RSI 指标判断动能枯竭点。

    入场逻辑：
    - 股价触及布林带下轨 且 RSI < 30 (超卖)

    出场逻辑：
    - 股价触及布林带上轨 或 RSI > 70 (超买)

    数学原理：
    布林带边界计算：
    $$Upper = \mu + k \cdot \sigma$$
    $$Lower = \mu - k \cdot \sigma$$
    其中 $\mu$ 为20日均值，$k$ 为标准差倍数（通常为2）。
    """

    def __init__(self, name: str = "bollinger_rsi_reversion", config: Dict[str, Any] = None):
        """
        初始化策略配置

        Args:
            name: 策略名称
            config: 策略配置字典
        """
        # 定义默认配置
        default_config = {
            'name': 'BollingerRSIReversion',
            'description': '基于布林带和RSI的均值回归策略',
            'top_n': 10,                 # 评分最高的选股数量
            'holding_period': 5,         # 最短持仓期
            'rebalance_freq': 'D',       # 调仓频率

            # 策略特有参数
            'bb_window': 20,             # 布林带周期
            'bb_std': 2.0,               # 布林带标准差倍数
            'rsi_window': 14,            # RSI周期
            'rsi_lower': 30,             # RSI超卖阈值
            'rsi_upper': 70,             # RSI超买阈值
            'min_data_points': 120,      # 最少数据点数
        }

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
        计算股票评分：结合价格与下轨的距离及RSI的超卖程度

        评分逻辑：
        - 价格越接近（或低于）下轨，分数越高
        - RSI越低（越接近超卖），分数越高
        - 综合评分 = 布林带分数 * 0.5 + RSI分数 * 0.5

        Args:
            prices: 价格DataFrame (index=date, columns=stock_codes)
            features: 特征DataFrame
            date: 指定日期

        Returns:
            scores: 股票评分Series (分数越高，回归均值潜力越大)
        """
        if date is None:
            date = prices.index[-1]

        scores = pd.Series(0.0, index=prices.columns)

        # 获取参数（正确的方式）
        bb_window = self.config.custom_params.get('bb_window', 20)
        bb_std = self.config.custom_params.get('bb_std', 2.0)
        rsi_window = self.config.custom_params.get('rsi_window', 14)
        min_data = self.config.custom_params.get('min_data_points', 120)

        for stock in prices.columns:
            try:
                # 获取历史数据（避免未来数据泄露）
                series = prices[stock].loc[:date].dropna()
                if len(series) < min_data:
                    continue

                # 1. 计算布林带
                ma = series.rolling(window=bb_window).mean()
                std = series.rolling(window=bb_window).std()
                lower_band = ma - (std * bb_std)
                upper_band = ma + (std * bb_std)

                # 验证数据有效性
                if pd.isna(lower_band.iloc[-1]) or pd.isna(ma.iloc[-1]):
                    continue

                # 计算价格相对位置（0=下轨，0.5=中轨，1=上轨）
                current_price = series.iloc[-1]
                bb_width = upper_band.iloc[-1] - lower_band.iloc[-1]
                if bb_width <= 0:
                    continue

                price_position = (current_price - lower_band.iloc[-1]) / bb_width
                # 转换为分数：越接近下轨（price_position越小），分数越高
                bb_score = (1 - price_position) * 100  # 0-100分

                # 2. 计算RSI
                delta = series.diff()
                gain = delta.where(delta > 0, 0).rolling(window=rsi_window).mean()
                loss = -delta.where(delta < 0, 0).rolling(window=rsi_window).mean()
                rs = gain / (loss + 1e-9)
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]

                # 验证RSI有效性
                if pd.isna(current_rsi):
                    continue

                # RSI分数：越低（越接近超卖），分数越高
                rsi_score = 100 - current_rsi  # RSI=0时得100分，RSI=100时得0分

                # 3. 综合评分
                # 只有当价格接近下轨（bb_score > 50）且RSI较低（rsi_score > 30）时才给高分
                if price_position < 0.3 and current_rsi < 40:  # 筛选条件
                    scores[stock] = bb_score * 0.5 + rsi_score * 0.5
                else:
                    scores[stock] = 0.0  # 不符合条件的股票评分为0

            except Exception as e:
                # 出错时跳过该股票
                continue

        return scores

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        生成买入/卖出信号

        Args:
            prices: 价格DataFrame (index=date, columns=stock_codes)
            features: 特征DataFrame
            **kwargs: 其他参数

        Returns:
            signals: 信号DataFrame (1=买入, 0=持有, -1=卖出)
        """
        signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)

        # 获取配置参数（正确的方式）
        bb_window = self.config.custom_params.get('bb_window', 20)
        bb_std = self.config.custom_params.get('bb_std', 2.0)
        rsi_window = self.config.custom_params.get('rsi_window', 14)
        rsi_lower = self.config.custom_params.get('rsi_lower', 30)
        rsi_upper = self.config.custom_params.get('rsi_upper', 70)
        min_data = self.config.custom_params.get('min_data_points', 120)

        for stock in prices.columns:
            try:
                stock_prices = prices[stock].dropna()
                if len(stock_prices) < min_data:
                    continue

                # --- 向量化计算指标 ---
                # 计算布林带
                sma = stock_prices.rolling(window=bb_window).mean()
                std = stock_prices.rolling(window=bb_window).std()
                upper_band = sma + (std * bb_std)
                lower_band = sma - (std * bb_std)

                # 计算RSI
                delta = stock_prices.diff()
                gain = delta.where(delta > 0, 0).rolling(window=rsi_window).mean()
                loss = -delta.where(delta < 0, 0).rolling(window=rsi_window).mean()
                rs = gain / (loss + 1e-9)
                rsi = 100 - (100 / (1 + rs))

                # --- 生成信号逻辑 ---
                # 1. 买入条件：触碰下轨 且 RSI超卖
                buy_cond = (stock_prices <= lower_band) & (rsi < rsi_lower)

                # 2. 卖出条件：触碰上轨 或 RSI超买
                sell_cond = (stock_prices >= upper_band) | (rsi > rsi_upper)

                # 正确的信号赋值方式
                buy_dates = buy_cond[buy_cond].index
                sell_dates = sell_cond[sell_cond].index

                # 只赋值存在于signals索引中的日期
                buy_dates_valid = signals.index.intersection(buy_dates)
                sell_dates_valid = signals.index.intersection(sell_dates)

                signals.loc[buy_dates_valid, stock] = 1
                signals.loc[sell_dates_valid, stock] = -1

            except Exception as e:
                # 出错时跳过该股票
                continue

        return signals
