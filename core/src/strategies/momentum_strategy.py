"""
动量策略模块

基于价格动量选股：买入近期强势股，持有一段时间后卖出
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from loguru import logger

from .base_strategy import BaseStrategy
from .signal_generator import SignalGenerator


class MomentumStrategy(BaseStrategy):
    """
    动量策略

    核心逻辑：
    - 计算过去N日的收益率作为动量指标
    - 每期选择动量最高的top_n只股票买入
    - 持有holding_period天后卖出

    参数：
        lookback_period: 动量计算回看期（默认20天）
        top_n: 每期选择前N只股票（默认50只）
        holding_period: 持仓期（默认5天）
        use_log_return: 是否使用对数收益率（默认False）
        filter_negative: 是否过滤负动量股票（默认True）

    适用场景：
        - 趋势性行情
        - 市场整体上涨
        - 中短期交易

    风险提示：
        - 震荡市场可能频繁止损
        - 追高风险
        - 转势时可能出现较大回撤
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化动量策略

        Args:
            name: 策略名称
            config: 策略配置
        """
        # 设置默认参数
        default_config = {
            'lookback_period': 20,
            'top_n': 50,
            'holding_period': 5,
            'use_log_return': False,
            'filter_negative': True,
        }
        default_config.update(config)

        super().__init__(name, default_config)

        # 提取策略特有参数
        self.lookback_period = self.config.custom_params.get('lookback_period', 20)
        self.use_log_return = self.config.custom_params.get('use_log_return', False)
        self.filter_negative = self.config.custom_params.get('filter_negative', True)

        logger.info(f"动量策略参数: 回看期={self.lookback_period}, "
                   f"选股数={self.config.top_n}, "
                   f"持仓期={self.config.holding_period}")

    def calculate_momentum(
        self,
        prices: pd.DataFrame,
        lookback: Optional[int] = None
    ) -> pd.DataFrame:
        """
        计算动量指标

        Args:
            prices: 价格DataFrame
            lookback: 回看期（None则使用默认）

        Returns:
            momentum: 动量DataFrame
        """
        if lookback is None:
            lookback = self.lookback_period

        if self.use_log_return:
            # 对数收益率（适合长期）
            momentum = np.log(prices / prices.shift(lookback)) * 100
        else:
            # 简单收益率（适合短期）
            momentum = prices.pct_change(lookback) * 100

        return momentum

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        计算股票评分（实现基类抽象方法）

        评分 = 动量值（过去N日收益率）

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame（本策略不使用）
            date: 指定日期

        Returns:
            scores: 股票评分Series
        """
        # 计算动量
        momentum = self.calculate_momentum(prices)

        # 获取指定日期的评分
        if date is None:
            date = momentum.index[-1]

        scores = momentum.loc[date]

        # 过滤负动量（可选）
        if self.filter_negative:
            scores[scores < 0] = np.nan

        return scores

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        生成交易信号（实现基类抽象方法）

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame（可选）
            volumes: 成交量DataFrame（可选）
            **kwargs: 其他参数

        Returns:
            signals: 信号DataFrame
        """
        logger.info(f"\n生成动量策略信号...")

        # 1. 计算动量
        momentum = self.calculate_momentum(prices)

        # 2. 过滤负动量（如果开启）
        if self.filter_negative:
            momentum[momentum < 0] = np.nan

        # 3. 使用信号生成器生成排名信号
        signals = SignalGenerator.generate_rank_signals(
            scores=momentum,
            top_n=self.config.top_n
        )

        # 4. 过滤股票（价格、成交量等）
        if volumes is not None:
            for date in signals.index:
                try:
                    valid_stocks = self.filter_stocks(prices, volumes, date)
                    # 将不符合条件的股票信号设为0
                    invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
                    signals.loc[date, invalid_stocks] = 0
                except:
                    pass

        # 5. 验证信号
        signals = self.validate_signals(signals)

        logger.info(f"信号生成完成，总买入信号数: {(signals == 1).sum().sum()}")

        return signals

    def get_top_stocks(
        self,
        prices: pd.DataFrame,
        date: pd.Timestamp,
        n: Optional[int] = None
    ) -> pd.Series:
        """
        获取指定日期的top N股票

        Args:
            prices: 价格DataFrame
            date: 指定日期
            n: 选择前N只（None则使用默认）

        Returns:
            top_stocks: 股票代码和动量值的Series
        """
        if n is None:
            n = self.config.top_n

        scores = self.calculate_scores(prices, date=date)
        top_stocks = scores.nlargest(n)

        return top_stocks


# ==================== 使用示例 ====================

if __name__ == "__main__":
    from ..backtest.backtest_engine import BacktestEngine

    logger.info("动量策略测试\n")
    logger.info("=" * 60)

    # 1. 创建测试数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = [f'{i:06d}' for i in range(600000, 600010)]

    # 模拟价格数据（带趋势）
    base_price = 10.0
    price_data = {}
    for i, stock in enumerate(stocks):
        # 每只股票有不同的趋势
        trend = np.random.choice([0.001, 0.002, 0.003, -0.001, 0.0])
        noise = np.random.normal(0, 0.02, len(dates))
        returns = trend + noise
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    logger.info("测试数据:")
    logger.info(f"  日期范围: {dates[0]} ~ {dates[-1]}")
    logger.info(f"  股票数量: {len(stocks)}")
    logger.info(f"  交易日数: {len(dates)}")

    # 2. 创建动量策略
    logger.info("\n创建动量策略:")
    config = {
        'lookback_period': 10,
        'top_n': 3,
        'holding_period': 5,
        'use_log_return': False,
        'filter_negative': True,
    }

    strategy = MomentumStrategy('MOM10', config)
    logger.info(f"  策略: {strategy}")

    # 3. 生成信号
    logger.info("\n生成信号:")
    signals = strategy.generate_signals(prices_df)
    logger.info(f"  信号形状: {signals.shape}")
    logger.info(f"  买入信号总数: {(signals == 1).sum().sum()}")

    # 4. 查看最新选股
    logger.info("\n最新选股:")
    latest_date = dates[-1]
    top_stocks = strategy.get_top_stocks(prices_df, latest_date)
    for stock, momentum in top_stocks.items():
        logger.info(f"  {stock}: 动量={momentum:.2f}%")

    # 5. 回测
    logger.info("\n执行回测:")
    try:
        engine = BacktestEngine(
            initial_capital=1000000,
            commission_rate=0.0003,
            verbose=False
        )

        results = strategy.backtest(
            engine=engine,
            prices=prices_df
        )

        logger.info(f"\n回测结果:")
        logger.info(f"  初始资金: {engine.initial_capital:,.0f}")
        logger.info(f"  最终资金: {results['portfolio_value']['total'].iloc[-1]:,.0f}")
        logger.info(f"  总收益率: {(results['portfolio_value']['total'].iloc[-1] / engine.initial_capital - 1) * 100:.2f}%")

    except Exception as e:
        logger.error(f"回测失败: {e}")

    logger.success("\n✓ 动量策略测试完成")
