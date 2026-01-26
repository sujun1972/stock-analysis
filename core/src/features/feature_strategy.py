"""
特征策略模式实现

通过策略模式实现可组合的特征计算，提供灵活的特征工程能力。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
import pandas as pd
import numpy as np
from loguru import logger


class FeatureStrategy(ABC):
    """
    特征策略抽象基类

    所有特征策略都必须继承此类并实现 compute 方法
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化特征策略

        Args:
            config: 策略配置字典
        """
        self.config = config or {}
        self._validate_config()

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算特征

        Args:
            df: 输入数据 (必须包含 OHLCV 数据)

        Returns:
            添加了新特征的 DataFrame
        """
        pass

    def _validate_config(self) -> None:
        """验证配置（子类可选实现）"""
        pass

    @property
    @abstractmethod
    def feature_names(self) -> List[str]:
        """返回该策略生成的特征名称列表"""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self.config})"


class TechnicalIndicatorStrategy(FeatureStrategy):
    """
    技术指标特征策略

    支持的指标:
    - ma: 移动平均线
    - ema: 指数移动平均线
    - rsi: 相对强弱指标
    - macd: MACD指标
    - kdj: KDJ指标
    - boll: 布林带
    - atr: 平均真实波幅
    - obv: 能量潮
    - cci: 商品通道指标
    """

    DEFAULT_CONFIG = {
        'ma': [5, 10, 20, 60],
        'ema': [12, 26],
        'rsi': [6, 14],
        'macd': [(12, 26, 9)],
        'kdj': [(9, 3, 3)],
        'boll': [(20, 2)],
        'atr': [14],
        'obv': True,
        'cci': [14],
    }

    def _validate_config(self) -> None:
        """验证配置"""
        if not self.config:
            self.config = self.DEFAULT_CONFIG.copy()

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        result_df = df.copy()

        # MA - 移动平均线
        if 'ma' in self.config:
            for period in self.config['ma']:
                result_df[f'MA_{period}'] = result_df['close'].rolling(window=period).mean()

        # EMA - 指数移动平均线
        if 'ema' in self.config:
            for period in self.config['ema']:
                result_df[f'EMA_{period}'] = result_df['close'].ewm(span=period, adjust=False).mean()

        # RSI - 相对强弱指标
        if 'rsi' in self.config:
            for period in self.config['rsi']:
                result_df[f'RSI_{period}'] = self._calculate_rsi(result_df['close'], period)

        # MACD
        if 'macd' in self.config:
            for fast, slow, signal in self.config['macd']:
                macd, signal_line, hist = self._calculate_macd(result_df['close'], fast, slow, signal)
                result_df[f'MACD_{fast}_{slow}'] = macd
                result_df[f'MACD_SIGNAL_{fast}_{slow}'] = signal_line
                result_df[f'MACD_HIST_{fast}_{slow}'] = hist

        # KDJ
        if 'kdj' in self.config:
            for n, m1, m2 in self.config['kdj']:
                k, d, j = self._calculate_kdj(result_df, n, m1, m2)
                result_df[f'KDJ_K_{n}'] = k
                result_df[f'KDJ_D_{n}'] = d
                result_df[f'KDJ_J_{n}'] = j

        # BOLL - 布林带
        if 'boll' in self.config:
            for period, std_num in self.config['boll']:
                upper, middle, lower = self._calculate_boll(result_df['close'], period, std_num)
                result_df[f'BOLL_UPPER_{period}'] = upper
                result_df[f'BOLL_MIDDLE_{period}'] = middle
                result_df[f'BOLL_LOWER_{period}'] = lower

        # ATR - 平均真实波幅
        if 'atr' in self.config:
            for period in self.config['atr']:
                result_df[f'ATR_{period}'] = self._calculate_atr(result_df, period)

        # OBV - 能量潮
        if self.config.get('obv', False):
            result_df['OBV'] = self._calculate_obv(result_df)

        # CCI - 商品通道指标
        if 'cci' in self.config:
            for period in self.config['cci']:
                result_df[f'CCI_{period}'] = self._calculate_cci(result_df, period)

        logger.debug(f"TechnicalIndicatorStrategy generated {len(self.feature_names)} features")
        return result_df

    @property
    def feature_names(self) -> List[str]:
        """返回特征名称列表"""
        features = []

        if 'ma' in self.config:
            features.extend([f'MA_{p}' for p in self.config['ma']])
        if 'ema' in self.config:
            features.extend([f'EMA_{p}' for p in self.config['ema']])
        if 'rsi' in self.config:
            features.extend([f'RSI_{p}' for p in self.config['rsi']])
        if 'macd' in self.config:
            for fast, slow, _ in self.config['macd']:
                features.extend([
                    f'MACD_{fast}_{slow}',
                    f'MACD_SIGNAL_{fast}_{slow}',
                    f'MACD_HIST_{fast}_{slow}'
                ])
        if 'kdj' in self.config:
            for n, _, _ in self.config['kdj']:
                features.extend([f'KDJ_K_{n}', f'KDJ_D_{n}', f'KDJ_J_{n}'])
        if 'boll' in self.config:
            for period, _ in self.config['boll']:
                features.extend([
                    f'BOLL_UPPER_{period}',
                    f'BOLL_MIDDLE_{period}',
                    f'BOLL_LOWER_{period}'
                ])
        if 'atr' in self.config:
            features.extend([f'ATR_{p}' for p in self.config['atr']])
        if self.config.get('obv', False):
            features.append('OBV')
        if 'cci' in self.config:
            features.extend([f'CCI_{p}' for p in self.config['cci']])

        return features

    # ========== 指标计算辅助方法 ==========

    @staticmethod
    def _calculate_rsi(series: pd.Series, period: int) -> pd.Series:
        """计算RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def _calculate_macd(series: pd.Series, fast: int, slow: int, signal: int):
        """计算MACD"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        hist = macd - signal_line
        return macd, signal_line, hist

    @staticmethod
    def _calculate_kdj(df: pd.DataFrame, n: int, m1: int, m2: int):
        """计算KDJ"""
        low_list = df['low'].rolling(window=n).min()
        high_list = df['high'].rolling(window=n).max()
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        k = rsv.ewm(com=m1 - 1, adjust=False).mean()
        d = k.ewm(com=m2 - 1, adjust=False).mean()
        j = 3 * k - 2 * d
        return k, d, j

    @staticmethod
    def _calculate_boll(series: pd.Series, period: int, std_num: float):
        """计算布林带"""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()
        upper = middle + std_num * std
        lower = middle - std_num * std
        return upper, middle, lower

    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int) -> pd.Series:
        """计算ATR"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    @staticmethod
    def _calculate_obv(df: pd.DataFrame) -> pd.Series:
        """计算OBV"""
        obv = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        return obv

    @staticmethod
    def _calculate_cci(df: pd.DataFrame, period: int) -> pd.Series:
        """计算CCI"""
        tp = (df['high'] + df['low'] + df['close']) / 3
        ma = tp.rolling(window=period).mean()
        md = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        cci = (tp - ma) / (0.015 * md)
        return cci


class AlphaFactorStrategy(FeatureStrategy):
    """
    Alpha因子特征策略

    支持的因子:
    - momentum: 动量因子
    - reversal: 反转因子
    - volatility: 波动率因子
    - volume: 成交量因子
    - correlation: 相关性因子
    """

    DEFAULT_CONFIG = {
        'momentum': [5, 10, 20],
        'reversal': [1, 3],
        'volatility': [5, 20],
        'volume': [5, 20],
        'correlation': [(5, 20)],
    }

    def _validate_config(self) -> None:
        """验证配置"""
        if not self.config:
            self.config = self.DEFAULT_CONFIG.copy()

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算Alpha因子"""
        result_df = df.copy()

        # Momentum - 动量因子
        if 'momentum' in self.config:
            for period in self.config['momentum']:
                result_df[f'MOMENTUM_{period}'] = result_df['close'].pct_change(period)

        # Reversal - 反转因子
        if 'reversal' in self.config:
            for period in self.config['reversal']:
                result_df[f'REVERSAL_{period}'] = -result_df['close'].pct_change(period)

        # Volatility - 波动率因子
        if 'volatility' in self.config:
            for period in self.config['volatility']:
                result_df[f'VOLATILITY_{period}'] = result_df['close'].pct_change().rolling(
                    window=period
                ).std()

        # Volume - 成交量因子
        if 'volume' in self.config:
            for period in self.config['volume']:
                avg_vol = result_df['volume'].rolling(window=period).mean()
                result_df[f'VOLUME_RATIO_{period}'] = result_df['volume'] / avg_vol

        # Correlation - 价格-成交量相关性
        if 'correlation' in self.config:
            for short, long in self.config['correlation']:
                result_df[f'PRICE_VOL_CORR_{short}_{long}'] = result_df['close'].rolling(
                    window=long
                ).corr(result_df['volume'])

        logger.debug(f"AlphaFactorStrategy generated {len(self.feature_names)} features")
        return result_df

    @property
    def feature_names(self) -> List[str]:
        """返回特征名称列表"""
        features = []

        if 'momentum' in self.config:
            features.extend([f'MOMENTUM_{p}' for p in self.config['momentum']])
        if 'reversal' in self.config:
            features.extend([f'REVERSAL_{p}' for p in self.config['reversal']])
        if 'volatility' in self.config:
            features.extend([f'VOLATILITY_{p}' for p in self.config['volatility']])
        if 'volume' in self.config:
            features.extend([f'VOLUME_RATIO_{p}' for p in self.config['volume']])
        if 'correlation' in self.config:
            for short, long in self.config['correlation']:
                features.append(f'PRICE_VOL_CORR_{short}_{long}')

        return features


class PriceTransformStrategy(FeatureStrategy):
    """
    价格转换特征策略

    支持的转换:
    - returns: 收益率
    - log_returns: 对数收益率
    - price_position: 价格位置
    - ohlc_features: OHLC关系特征
    """

    DEFAULT_CONFIG = {
        'returns': [1, 3, 5, 10, 20],
        'log_returns': [1, 5, 20],
        'price_position': [5, 20, 60],
        'ohlc_features': True,
    }

    def _validate_config(self) -> None:
        """验证配置"""
        if not self.config:
            self.config = self.DEFAULT_CONFIG.copy()

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算价格转换特征"""
        result_df = df.copy()

        # Returns - 收益率
        if 'returns' in self.config:
            for period in self.config['returns']:
                result_df[f'RETURN_{period}D'] = result_df['close'].pct_change(period)

        # Log Returns - 对数收益率
        if 'log_returns' in self.config:
            for period in self.config['log_returns']:
                result_df[f'LOG_RETURN_{period}D'] = np.log(
                    result_df['close'] / result_df['close'].shift(period)
                )

        # Price Position - 价格位置
        if 'price_position' in self.config:
            for period in self.config['price_position']:
                rolling_min = result_df['close'].rolling(window=period).min()
                rolling_max = result_df['close'].rolling(window=period).max()
                result_df[f'PRICE_POSITION_{period}'] = (
                    (result_df['close'] - rolling_min) / (rolling_max - rolling_min)
                )

        # OHLC Features - OHLC关系特征
        if self.config.get('ohlc_features', False):
            # 实体大小（收盘-开盘）
            result_df['BODY_SIZE'] = (result_df['close'] - result_df['open']) / result_df['open']

            # 上影线大小
            result_df['UPPER_SHADOW'] = (
                result_df['high'] - result_df[['open', 'close']].max(axis=1)
            ) / result_df['open']

            # 下影线大小
            result_df['LOWER_SHADOW'] = (
                result_df[['open', 'close']].min(axis=1) - result_df['low']
            ) / result_df['open']

            # 日内振幅
            result_df['INTRADAY_RANGE'] = (result_df['high'] - result_df['low']) / result_df['open']

        logger.debug(f"PriceTransformStrategy generated {len(self.feature_names)} features")
        return result_df

    @property
    def feature_names(self) -> List[str]:
        """返回特征名称列表"""
        features = []

        if 'returns' in self.config:
            features.extend([f'RETURN_{p}D' for p in self.config['returns']])
        if 'log_returns' in self.config:
            features.extend([f'LOG_RETURN_{p}D' for p in self.config['log_returns']])
        if 'price_position' in self.config:
            features.extend([f'PRICE_POSITION_{p}' for p in self.config['price_position']])
        if self.config.get('ohlc_features', False):
            features.extend(['BODY_SIZE', 'UPPER_SHADOW', 'LOWER_SHADOW', 'INTRADAY_RANGE'])

        return features


class CompositeFeatureStrategy(FeatureStrategy):
    """
    组合特征策略

    将多个特征策略组合在一起，按顺序执行
    """

    def __init__(self, strategies: List[FeatureStrategy]):
        """
        初始化组合策略

        Args:
            strategies: 策略列表
        """
        self.strategies = strategies
        super().__init__(config={})

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """依次执行所有策略"""
        result_df = df.copy()

        for strategy in self.strategies:
            logger.debug(f"Executing strategy: {strategy.__class__.__name__}")
            result_df = strategy.compute(result_df)

        logger.info(
            f"CompositeFeatureStrategy executed {len(self.strategies)} strategies, "
            f"generated {len(self.feature_names)} features"
        )
        return result_df

    @property
    def feature_names(self) -> List[str]:
        """返回所有策略的特征名称"""
        all_features = []
        for strategy in self.strategies:
            all_features.extend(strategy.feature_names)
        return all_features

    def __repr__(self) -> str:
        strategy_names = [s.__class__.__name__ for s in self.strategies]
        return f"CompositeFeatureStrategy(strategies={strategy_names})"


# ==================== 便捷函数 ====================

def create_default_feature_pipeline() -> CompositeFeatureStrategy:
    """
    创建默认的特征流水线

    Returns:
        组合特征策略
    """
    return CompositeFeatureStrategy([
        TechnicalIndicatorStrategy(),
        AlphaFactorStrategy(),
        PriceTransformStrategy(),
    ])


def create_minimal_feature_pipeline() -> CompositeFeatureStrategy:
    """
    创建最小特征流水线（快速计算）

    Returns:
        组合特征策略
    """
    return CompositeFeatureStrategy([
        TechnicalIndicatorStrategy(config={
            'ma': [5, 20],
            'rsi': [14],
        }),
        AlphaFactorStrategy(config={
            'momentum': [5, 20],
            'volatility': [20],
        }),
        PriceTransformStrategy(config={
            'returns': [1, 5],
            'ohlc_features': True,
        }),
    ])


def create_custom_feature_pipeline(
    technical_config: Optional[Dict[str, Any]] = None,
    alpha_config: Optional[Dict[str, Any]] = None,
    price_config: Optional[Dict[str, Any]] = None,
) -> CompositeFeatureStrategy:
    """
    创建自定义特征流水线

    Args:
        technical_config: 技术指标配置
        alpha_config: Alpha因子配置
        price_config: 价格转换配置

    Returns:
        组合特征策略
    """
    strategies = []

    if technical_config is not None:
        strategies.append(TechnicalIndicatorStrategy(config=technical_config))

    if alpha_config is not None:
        strategies.append(AlphaFactorStrategy(config=alpha_config))

    if price_config is not None:
        strategies.append(PriceTransformStrategy(config=price_config))

    return CompositeFeatureStrategy(strategies)


# ==================== 导出 ====================

__all__ = [
    'FeatureStrategy',
    'TechnicalIndicatorStrategy',
    'AlphaFactorStrategy',
    'PriceTransformStrategy',
    'CompositeFeatureStrategy',
    'create_default_feature_pipeline',
    'create_minimal_feature_pipeline',
    'create_custom_feature_pipeline',
]
