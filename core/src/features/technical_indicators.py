"""
技术指标计算模块（聚合模块 - 向后兼容）
包含常用技术指标的封装和扩展

本模块已重构为模块化设计，按指标类型拆分为：
- indicators.trend: 趋势指标 (MA, EMA, BBANDS)
- indicators.momentum: 动量指标 (RSI, MACD, KDJ, CCI)
- indicators.volatility: 波动率指标 (ATR, Volatility)
- indicators.volume: 成交量指标 (OBV, Volume MA)
- indicators.price_pattern: 价格形态指标

本文件保留原有的 TechnicalIndicators 类以保持向后兼容性。
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict
import warnings

# 尝试导入 loguru，如果不存在则使用 print 作为后备
try:
    from loguru import logger
    HAS_LOGGER = True
except ImportError:
    HAS_LOGGER = False
    # 创建简单的 logger 替代品
    class SimpleLogger:
        @staticmethod
        def debug(msg): pass  # 在生产环境中使用 debug 级别，不输出
        @staticmethod
        def info(msg): logger.info(f"{msg}")
        @staticmethod
        def warning(msg): logger.warning(f"WARNING: {msg}")
        @staticmethod
        def error(msg): logger.error(f"ERROR: {msg}")
    logger = SimpleLogger()

# 导入各个指标模块
from .indicators.base import BaseIndicator, talib, HAS_TALIB
from .indicators.trend import TrendIndicators
from .indicators.momentum import MomentumIndicators
from .indicators.volatility import VolatilityIndicators
from .indicators.volume import VolumeIndicators
from .indicators.price_pattern import PricePatternIndicators


warnings.filterwarnings('ignore')


class TechnicalIndicators(BaseIndicator):
    """
    技术指标计算器（聚合类）

    整合了所有类型的技术指标计算功能，保持向后兼容性。
    内部使用组合模式，将不同类型的指标分发到对应的专用模块。
    """

    def __init__(self, df: pd.DataFrame):
        """
        初始化技术指标计算器

        参数:
            df: 价格DataFrame，需包含 open, high, low, close, volume 列
        """
        super().__init__(df)

        # 创建各类指标计算器实例（共享同一个 df 引用）
        self._trend = None
        self._momentum = None
        self._volatility = None
        self._volume = None
        self._price_pattern = None

    def _get_trend_calculator(self) -> TrendIndicators:
        """懒加载趋势指标计算器"""
        if self._trend is None:
            self._trend = TrendIndicators(self.df)
        else:
            # 同步 df 状态
            self._trend.df = self.df
        return self._trend

    def _get_momentum_calculator(self) -> MomentumIndicators:
        """懒加载动量指标计算器"""
        if self._momentum is None:
            self._momentum = MomentumIndicators(self.df)
        else:
            self._momentum.df = self.df
        return self._momentum

    def _get_volatility_calculator(self) -> VolatilityIndicators:
        """懒加载波动率指标计算器"""
        if self._volatility is None:
            self._volatility = VolatilityIndicators(self.df)
        else:
            self._volatility.df = self.df
        return self._volatility

    def _get_volume_calculator(self) -> VolumeIndicators:
        """懒加载成交量指标计算器"""
        if self._volume is None:
            self._volume = VolumeIndicators(self.df)
        else:
            self._volume.df = self.df
        return self._volume

    def _get_price_pattern_calculator(self) -> PricePatternIndicators:
        """懒加载价格形态指标计算器"""
        if self._price_pattern is None:
            self._price_pattern = PricePatternIndicators(self.df)
        else:
            self._price_pattern.df = self.df
        return self._price_pattern

    # ==================== 趋势指标 ====================

    def add_ma(
        self,
        periods: list = [5, 10, 20, 60, 120, 250],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """添加移动平均线（MA）"""
        calc = self._get_trend_calculator()
        self.df = calc.add_ma(periods, price_col)
        return self.df

    def add_ema(
        self,
        periods: list = [12, 26, 50],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """添加指数移动平均线（EMA）"""
        calc = self._get_trend_calculator()
        self.df = calc.add_ema(periods, price_col)
        return self.df

    def add_bollinger_bands(
        self,
        period: int = 20,
        nbdevup: float = 2.0,
        nbdevdn: float = 2.0,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """添加布林带（Bollinger Bands）"""
        calc = self._get_trend_calculator()
        self.df = calc.add_bollinger_bands(period, nbdevup, nbdevdn, price_col)
        return self.df

    # ==================== 动量指标 ====================

    def add_rsi(
        self,
        periods: list = [6, 12, 24],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """添加相对强弱指数（RSI）"""
        calc = self._get_momentum_calculator()
        self.df = calc.add_rsi(periods, price_col)
        return self.df

    def add_macd(
        self,
        fastperiod: int = 12,
        slowperiod: int = 26,
        signalperiod: int = 9,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """添加MACD指标"""
        calc = self._get_momentum_calculator()
        self.df = calc.add_macd(fastperiod, slowperiod, signalperiod, price_col)
        return self.df

    def add_kdj(
        self,
        fastk_period: int = 9,
        slowk_period: int = 3,
        slowd_period: int = 3
    ) -> pd.DataFrame:
        """添加KDJ指标（随机指标）"""
        calc = self._get_momentum_calculator()
        self.df = calc.add_kdj(fastk_period, slowk_period, slowd_period)
        return self.df

    def add_cci(
        self,
        periods: list = [14, 28]
    ) -> pd.DataFrame:
        """添加CCI指标（商品通道指标）"""
        calc = self._get_momentum_calculator()
        self.df = calc.add_cci(periods)
        return self.df

    # ==================== 波动率指标 ====================

    def add_atr(
        self,
        periods: list = [14, 28]
    ) -> pd.DataFrame:
        """添加ATR指标（平均真实波幅）"""
        calc = self._get_volatility_calculator()
        self.df = calc.add_atr(periods)
        return self.df

    def add_volatility(
        self,
        periods: list = [5, 10, 20, 60],
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """添加历史波动率"""
        calc = self._get_volatility_calculator()
        self.df = calc.add_volatility(periods, price_col)
        return self.df

    # ==================== 成交量指标 ====================

    def add_obv(
        self,
        price_col: str = 'close',
        volume_col: str = 'vol'
    ) -> pd.DataFrame:
        """添加OBV指标（能量潮）"""
        calc = self._get_volume_calculator()
        self.df = calc.add_obv(price_col, volume_col)
        return self.df

    def add_volume_ma(
        self,
        periods: list = [5, 10, 20],
        volume_col: str = 'vol'
    ) -> pd.DataFrame:
        """添加成交量移动平均线"""
        calc = self._get_volume_calculator()
        self.df = calc.add_volume_ma(periods, volume_col)
        return self.df

    # ==================== 价格形态指标 ====================

    def add_price_patterns(self) -> pd.DataFrame:
        """添加价格形态特征"""
        calc = self._get_price_pattern_calculator()
        self.df = calc.add_price_patterns()
        return self.df

    # ==================== 综合指标 ====================

    def add_all_indicators(self) -> pd.DataFrame:
        """
        一键添加所有常用技术指标

        返回:
            添加所有指标的DataFrame
        """
        logger.debug("开始计算技术指标...")

        # 趋势指标
        self.add_ma([5, 10, 20, 60, 120, 250])
        self.add_ema([12, 26, 50])
        self.add_bollinger_bands()

        # 动量指标
        self.add_rsi([6, 12, 24])
        self.add_macd()
        self.add_kdj()
        self.add_cci()

        # 波动率指标
        self.add_atr()
        self.add_volatility([5, 10, 20, 60])

        # 成交量指标
        self.add_obv()
        self.add_volume_ma([5, 10, 20])

        # 价格形态
        self.add_price_patterns()

        feature_count = len(self.get_feature_names())
        logger.debug(f"技术指标计算完成，共生成 {feature_count} 个特征")

        return self.df

    def get_feature_names(self) -> list:
        """获取所有特征名称列表"""
        # 排除原始OHLCV列
        exclude_cols = ['open', 'high', 'low', 'close', 'vol', 'volume', 'amount']
        return [col for col in self.df.columns if col not in exclude_cols]

    def get_dataframe(self) -> pd.DataFrame:
        """获取包含所有指标的DataFrame"""
        return self.df


# ==================== 便捷函数 ====================

def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    便捷函数：一键计算所有技术指标

    参数:
        df: 价格DataFrame

    返回:
        包含所有技术指标的DataFrame
    """
    ti = TechnicalIndicators(df)
    return ti.add_all_indicators()


def calculate_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    便捷函数：计算基础技术指标（快速模式）

    参数:
        df: 价格DataFrame

    返回:
        包含基础技术指标的DataFrame
    """
    ti = TechnicalIndicators(df)

    ti.add_ma([5, 10, 20, 60])
    ti.add_rsi([14])
    ti.add_macd()
    ti.add_atr()
    ti.add_price_patterns()

    return ti.get_dataframe()


# ==================== 使用示例 ====================

if __name__ == "__main__":
    logger.info("技术指标模块测试\n")

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=300, freq='D')

    # 模拟价格数据
    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 300)
    prices = base_price * (1 + returns).cumprod()

    test_df = pd.DataFrame({
        'open': prices * (1 + np.random.uniform(-0.01, 0.01, 300)),
        'high': prices * (1 + np.random.uniform(0, 0.03, 300)),
        'low': prices * (1 + np.random.uniform(-0.03, 0, 300)),
        'close': prices,
        'vol': np.random.uniform(1000000, 10000000, 300)
    }, index=dates)

    logger.info("原始数据:")
    logger.info(test_df.head())
    logger.info(f"\n原始列数: {len(test_df.columns)}")

    # 计算技术指标
    ti = TechnicalIndicators(test_df)
    result_df = ti.add_all_indicators()

    logger.info("\n添加技术指标后:")
    logger.info(result_df.head())
    logger.info(f"\n总列数: {len(result_df.columns)}")
    logger.info(f"特征列数: {len(ti.get_feature_names())}")

    logger.info("\n特征列表:")
    for i, col in enumerate(ti.get_feature_names(), 1):
        logger.info(f"  {i:2d}. {col}")

    logger.info("\n最近5天数据示例:")
    logger.info(result_df[['close', 'MA5', 'MA20', 'RSI6', 'MACD', 'ATR14']].tail())
