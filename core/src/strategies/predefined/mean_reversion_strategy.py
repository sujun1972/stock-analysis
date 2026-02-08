"""
均值回归策略模块

基于均值回归效应：买入短期超跌股票，等待反弹后卖出
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from loguru import logger

from ..base_strategy import BaseStrategy
from ..signal_generator import SignalGenerator


class MeanReversionStrategy(BaseStrategy):
    """
    均值回归策略

    核心逻辑：
    - 计算股价相对于移动平均线的偏离度（Z-score）
    - 选择偏离度最大（超跌）的股票买入
    - 等待价格回归均线后卖出

    参数：
        lookback_period: 均线计算周期（默认20天）
        z_score_threshold: Z-score阈值（默认-2.0，即低于均线2个标准差）
        top_n: 每期选择前N只股票
        holding_period: 持仓期

    适用场景：
        - 震荡市场
        - 个股短期超买超卖
        - 均值回归明显的股票

    风险提示：
        - 趋势市场可能持续下跌
        - 价值陷阱（基本面恶化导致的下跌）
        - 需要设置严格止损
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化均值回归策略

        Args:
            name: 策略名称
            config: 策略配置
        """
        default_config = {
            'lookback_period': 20,
            'z_score_threshold': -2.0,
            'top_n': 30,
            'holding_period': 5,
            'use_bollinger': False,  # 是否使用布林带
            'bollinger_window': 20,
            'bollinger_std': 2.0,
        }
        default_config.update(config)

        super().__init__(name, default_config)

        self.lookback_period = self.config.custom_params.get('lookback_period', 20)
        self.z_score_threshold = self.config.custom_params.get('z_score_threshold', -2.0)
        self.use_bollinger = self.config.custom_params.get('use_bollinger', False)
        self.bollinger_window = self.config.custom_params.get('bollinger_window', 20)
        self.bollinger_std = self.config.custom_params.get('bollinger_std', 2.0)

        logger.info(f"均值回归策略参数: 回看期={self.lookback_period}, "
                   f"Z-score阈值={self.z_score_threshold}")

    def calculate_z_score(
        self,
        prices: pd.DataFrame,
        lookback: Optional[int] = None
    ) -> pd.DataFrame:
        """
        计算Z-score（标准化偏离度）

        Z-score = (当前价 - 移动平均) / 标准差

        Args:
            prices: 价格DataFrame
            lookback: 回看期

        Returns:
            z_scores: Z-score DataFrame
        """
        if lookback is None:
            lookback = self.lookback_period

        # 计算移动平均
        ma = prices.rolling(window=lookback).mean()

        # 计算标准差
        std = prices.rolling(window=lookback).std()

        # 计算Z-score
        z_scores = (prices - ma) / (std + 1e-8)  # 加小值防止除零

        return z_scores

    def calculate_bollinger_position(
        self,
        prices: pd.DataFrame
    ) -> pd.DataFrame:
        """
        计算价格在布林带中的位置

        Position = (当前价 - 下轨) / (上轨 - 下轨)
        - 接近0：触及下轨（超卖）
        - 接近1：触及上轨（超买）

        Args:
            prices: 价格DataFrame

        Returns:
            positions: 位置DataFrame（0-1之间）
        """
        # 中轨（移动平均）
        ma = prices.rolling(window=self.bollinger_window).mean()

        # 标准差
        std = prices.rolling(window=self.bollinger_window).std()

        # 上下轨
        upper = ma + self.bollinger_std * std
        lower = ma - self.bollinger_std * std

        # 计算位置
        positions = (prices - lower) / (upper - lower + 1e-8)

        return positions

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        计算股票评分

        评分 = -Z-score（Z-score越低，超跌越严重，评分越高）
        或
        评分 = 1 - Bollinger Position（越接近下轨，评分越高）

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame
            date: 指定日期

        Returns:
            scores: 股票评分Series
        """
        if self.use_bollinger:
            # 使用布林带
            positions = self.calculate_bollinger_position(prices)
            # 反转：越接近下轨（0）评分越高
            raw_scores = 1 - positions
        else:
            # 使用Z-score
            z_scores = self.calculate_z_score(prices)
            # 反转：Z-score越低（越超跌）评分越高
            raw_scores = -z_scores

        if date is None:
            date = raw_scores.index[-1]

        scores = raw_scores.loc[date]

        # 只保留超卖的股票（Z-score < threshold 或 Position < 0.2）
        if self.use_bollinger:
            scores[scores < 0.8] = np.nan  # Position > 0.2 的过滤掉
        else:
            # 原始Z-score，只保留低于阈值的
            original_z = -scores
            scores[original_z > self.z_score_threshold] = np.nan

        return scores

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame
            volumes: 成交量DataFrame
            **kwargs: 其他参数

        Returns:
            signals: 信号DataFrame
        """
        logger.info(f"\n生成均值回归策略信号...")

        # 1. 计算评分
        if self.use_bollinger:
            positions = self.calculate_bollinger_position(prices)
            scores = 1 - positions
        else:
            z_scores = self.calculate_z_score(prices)
            scores = -z_scores

        # 2. 使用信号生成器生成排名信号（返回Response对象）
        signals_response = SignalGenerator.generate_rank_signals(
            scores=scores,
            top_n=self.config.top_n
        )

        # 检查信号生成结果并提取数据
        if not signals_response.is_success():
            raise ValueError(f"信号生成失败: {signals_response.error}")
        signals = signals_response.data

        # 3. 过滤
        if volumes is not None:
            for date in signals.index:
                try:
                    valid_stocks = self.filter_stocks(prices, volumes, date)
                    invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
                    signals.loc[date, invalid_stocks] = 0
                except:
                    pass

        # 4. 验证
        signals = self.validate_signals(signals)

        logger.info(f"信号生成完成，总买入信号数: {(signals == 1).sum().sum()}")

        return signals


# ==================== 使用示例 ====================

if __name__ == "__main__":
    logger.info("均值回归策略测试\n")
    logger.info("=" * 60)

    # 创建测试数据（震荡市场）
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = [f'{i:06d}' for i in range(600000, 600010)]

    # 模拟震荡价格（围绕10元上下波动）
    price_data = {}
    for stock in stocks:
        # 基础价格 + 正弦波 + 噪声
        t = np.arange(len(dates))
        trend = 10 + 2 * np.sin(t * 2 * np.pi / 20)  # 20日周期的震荡
        noise = np.random.normal(0, 0.5, len(dates))
        prices = trend + noise
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    logger.info("测试数据:")
    logger.info(f"  日期范围: {dates[0]} ~ {dates[-1]}")
    logger.info(f"  股票数量: {len(stocks)}")
    logger.info(f"  价格模式: 震荡（围绕10元波动）")

    # 创建策略
    logger.info("\n创建均值回归策略:")
    config = {
        'lookback_period': 10,
        'z_score_threshold': -1.5,
        'top_n': 3,
        'holding_period': 3,
    }

    strategy = MeanReversionStrategy('MR10', config)

    # 生成信号
    logger.info("\n生成信号:")
    signals = strategy.generate_signals(prices_df)
    logger.info(f"  买入信号总数: {(signals == 1).sum().sum()}")

    # 查看最新Z-scores
    logger.info("\n最新Z-scores:")
    z_scores = strategy.calculate_z_score(prices_df)
    latest_z = z_scores.iloc[-1].sort_values()
    logger.info(f"  最超卖的3只股票:")
    for stock, z in latest_z.head(3).items():
        logger.info(f"    {stock}: Z-score={z:.2f}")

    logger.success("\n✓ 均值回归策略测试完成")
