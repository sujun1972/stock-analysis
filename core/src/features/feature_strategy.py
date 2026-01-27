"""
特征策略模式实现

通过策略模式实现可组合的特征计算，提供灵活的特征工程能力。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger
from functools import wraps
import warnings


# ==================== 异常类 ====================

class FeatureComputationError(Exception):
    """特征计算错误"""
    pass


class InvalidDataError(Exception):
    """无效数据错误"""
    pass


# ==================== 装饰器 ====================

def validate_ohlcv_data(required_cols: Optional[List[str]] = None):
    """
    验证OHLCV数据的装饰器

    Args:
        required_cols: 必需的列名列表，默认为 ['open', 'high', 'low', 'close', 'volume']
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, df: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
            if df is None or df.empty:
                raise InvalidDataError("输入 DataFrame 为空")

            cols_to_check = required_cols or ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in cols_to_check if col not in df.columns]

            if missing_cols:
                raise InvalidDataError(
                    f"DataFrame 缺少必需列: {missing_cols}。"
                    f"当前列: {list(df.columns)}"
                )

            # 检查数据量是否足够
            if len(df) < 2:
                logger.warning(f"数据量不足（{len(df)} 行），某些指标可能无法计算")

            return func(self, df, *args, **kwargs)
        return wrapper
    return decorator


def safe_compute(feature_name: str):
    """
    安全计算装饰器，捕获计算异常

    Args:
        feature_name: 特征名称，用于日志
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"计算 {feature_name} 时出错: {str(e)}")
                raise FeatureComputationError(f"计算 {feature_name} 失败: {str(e)}") from e
        return wrapper
    return decorator


# ==================== 辅助函数 ====================

def safe_divide(numerator: pd.Series, denominator: pd.Series, fill_value: float = 0.0) -> pd.Series:
    """
    安全除法，处理除零情况

    Args:
        numerator: 分子
        denominator: 分母
        fill_value: 除零时的填充值

    Returns:
        计算结果
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = numerator / denominator
        result = result.replace([np.inf, -np.inf], fill_value)
        result = result.fillna(fill_value)
    return result


def merge_configs(default_config: Dict[str, Any], user_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    合并默认配置和用户配置

    Args:
        default_config: 默认配置
        user_config: 用户配置

    Returns:
        合并后的配置
    """
    if user_config is None:
        return default_config.copy()

    merged = default_config.copy()
    merged.update(user_config)
    return merged


class FeatureStrategy(ABC):
    """
    特征策略抽象基类

    所有特征策略都必须继承此类并实现 compute 方法
    """

    # 子类应该定义默认配置
    DEFAULT_CONFIG: Dict[str, Any] = {}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化特征策略

        Args:
            config: 策略配置字典，会与 DEFAULT_CONFIG 合并
        """
        self.config = merge_configs(self.DEFAULT_CONFIG, config)
        self._validate_config()
        self._feature_cache: Optional[List[str]] = None

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算特征

        Args:
            df: 输入数据 (必须包含 OHLCV 数据)

        Returns:
            添加了新特征的 DataFrame

        Raises:
            InvalidDataError: 输入数据无效
            FeatureComputationError: 特征计算失败
        """
        pass

    def _validate_config(self) -> None:
        """
        验证配置（子类可选实现）

        Raises:
            ValueError: 配置无效
        """
        pass

    @property
    def feature_names(self) -> List[str]:
        """
        返回该策略生成的特征名称列表

        使用缓存提高性能
        """
        if self._feature_cache is None:
            self._feature_cache = self._get_feature_names()
        return self._feature_cache

    @abstractmethod
    def _get_feature_names(self) -> List[str]:
        """子类实现：返回特征名称列表"""
        pass

    def get_required_columns(self) -> List[str]:
        """
        返回该策略所需的列名

        Returns:
            必需列名列表
        """
        return ['open', 'high', 'low', 'close', 'volume']

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

    Example:
        >>> strategy = TechnicalIndicatorStrategy(config={'ma': [5, 10], 'rsi': [14]})
        >>> result_df = strategy.compute(df)
        >>> print(strategy.feature_names)
        ['MA_5', 'MA_10', 'RSI_14']
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
        # 验证周期参数
        for key in ['ma', 'ema', 'rsi', 'atr', 'cci']:
            if key in self.config:
                if not isinstance(self.config[key], list):
                    raise ValueError(f"{key} 配置必须是列表")
                if not all(isinstance(p, int) and p > 0 for p in self.config[key]):
                    raise ValueError(f"{key} 周期必须是正整数")

        # 验证元组参数
        for key in ['macd', 'kdj', 'boll']:
            if key in self.config:
                if not isinstance(self.config[key], list):
                    raise ValueError(f"{key} 配置必须是列表")
                for params in self.config[key]:
                    if not isinstance(params, tuple):
                        raise ValueError(f"{key} 参数必须是元组")

    @validate_ohlcv_data()
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标

        Args:
            df: 包含 OHLCV 数据的 DataFrame

        Returns:
            添加了技术指标的 DataFrame

        Raises:
            InvalidDataError: 输入数据无效
            FeatureComputationError: 指标计算失败
        """
        result_df = df.copy()

        try:
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

        except Exception as e:
            logger.error(f"技术指标计算失败: {str(e)}")
            raise FeatureComputationError(f"技术指标计算失败: {str(e)}") from e

    def _get_feature_names(self) -> List[str]:
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
    @safe_compute("RSI")
    def _calculate_rsi(series: pd.Series, period: int) -> pd.Series:
        """
        计算RSI (相对强弱指标)

        Args:
            series: 价格序列
            period: 计算周期

        Returns:
            RSI 值序列
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # 使用安全除法避免除零
        rs = safe_divide(gain, loss, fill_value=0)
        rsi = 100 - safe_divide(100, (1 + rs), fill_value=50)

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
    @safe_compute("KDJ")
    def _calculate_kdj(df: pd.DataFrame, n: int, m1: int, m2: int):
        """
        计算KDJ指标

        Args:
            df: 包含 high, low, close 的 DataFrame
            n: RSV 计算周期
            m1: K 值平滑参数
            m2: D 值平滑参数

        Returns:
            (K, D, J) 三个序列的元组
        """
        low_list = df['low'].rolling(window=n).min()
        high_list = df['high'].rolling(window=n).max()

        # 使用安全除法计算 RSV
        rsv = safe_divide(df['close'] - low_list, high_list - low_list, fill_value=0) * 100

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
    @safe_compute("CCI")
    def _calculate_cci(df: pd.DataFrame, period: int) -> pd.Series:
        """
        计算CCI (商品通道指标)

        Args:
            df: 包含 high, low, close 的 DataFrame
            period: 计算周期

        Returns:
            CCI 值序列
        """
        tp = (df['high'] + df['low'] + df['close']) / 3
        ma = tp.rolling(window=period).mean()
        md = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())

        # 使用安全除法
        cci = safe_divide(tp - ma, 0.015 * md, fill_value=0)
        return cci


class AlphaFactorStrategy(FeatureStrategy):
    """
    Alpha因子特征策略

    支持的因子:
    - momentum: 动量因子 (价格动量)
    - reversal: 反转因子 (短期反转效应)
    - volatility: 波动率因子 (价格波动性)
    - volume: 成交量因子 (成交量异常)
    - correlation: 相关性因子 (价格-成交量关系)

    Example:
        >>> strategy = AlphaFactorStrategy(config={'momentum': [5, 20], 'volatility': [20]})
        >>> result_df = strategy.compute(df)
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
        # 验证周期参数
        for key in ['momentum', 'reversal', 'volatility', 'volume']:
            if key in self.config:
                if not isinstance(self.config[key], list):
                    raise ValueError(f"{key} 配置必须是列表")
                if not all(isinstance(p, int) and p > 0 for p in self.config[key]):
                    raise ValueError(f"{key} 周期必须是正整数")

        # 验证相关性参数
        if 'correlation' in self.config:
            if not isinstance(self.config['correlation'], list):
                raise ValueError("correlation 配置必须是列表")
            for params in self.config['correlation']:
                if not isinstance(params, tuple) or len(params) != 2:
                    raise ValueError("correlation 参数必须是包含两个元素的元组")

    @validate_ohlcv_data()
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算Alpha因子

        Args:
            df: 包含 OHLCV 数据的 DataFrame

        Returns:
            添加了 Alpha 因子的 DataFrame

        Raises:
            InvalidDataError: 输入数据无效
            FeatureComputationError: 因子计算失败
        """
        result_df = df.copy()

        try:
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
                    result_df[f'VOLUME_RATIO_{period}'] = safe_divide(
                        result_df['volume'], avg_vol, fill_value=1.0
                    )

            # Correlation - 价格-成交量相关性
            if 'correlation' in self.config:
                for short, long in self.config['correlation']:
                    result_df[f'PRICE_VOL_CORR_{short}_{long}'] = result_df['close'].rolling(
                        window=long
                    ).corr(result_df['volume'])

            logger.debug(f"AlphaFactorStrategy generated {len(self.feature_names)} features")
            return result_df

        except Exception as e:
            logger.error(f"Alpha因子计算失败: {str(e)}")
            raise FeatureComputationError(f"Alpha因子计算失败: {str(e)}") from e

    def _get_feature_names(self) -> List[str]:
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
    - returns: 收益率 (简单收益率)
    - log_returns: 对数收益率 (连续复利收益率)
    - price_position: 价格位置 (价格在区间的相对位置)
    - ohlc_features: OHLC关系特征 (K线形态特征)

    Example:
        >>> strategy = PriceTransformStrategy(config={'returns': [1, 5], 'ohlc_features': True})
        >>> result_df = strategy.compute(df)
    """

    DEFAULT_CONFIG = {
        'returns': [1, 3, 5, 10, 20],
        'log_returns': [1, 5, 20],
        'price_position': [5, 20, 60],
        'ohlc_features': True,
    }

    def _validate_config(self) -> None:
        """验证配置"""
        # 验证周期参数
        for key in ['returns', 'log_returns', 'price_position']:
            if key in self.config:
                if not isinstance(self.config[key], list):
                    raise ValueError(f"{key} 配置必须是列表")
                if not all(isinstance(p, int) and p > 0 for p in self.config[key]):
                    raise ValueError(f"{key} 周期必须是正整数")

    @validate_ohlcv_data()
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算价格转换特征

        Args:
            df: 包含 OHLCV 数据的 DataFrame

        Returns:
            添加了价格转换特征的 DataFrame

        Raises:
            InvalidDataError: 输入数据无效
            FeatureComputationError: 特征计算失败
        """
        result_df = df.copy()

        try:
            # Returns - 收益率
            if 'returns' in self.config:
                for period in self.config['returns']:
                    result_df[f'RETURN_{period}D'] = result_df['close'].pct_change(period)

            # Log Returns - 对数收益率
            if 'log_returns' in self.config:
                for period in self.config['log_returns']:
                    shifted_close = result_df['close'].shift(period)
                    result_df[f'LOG_RETURN_{period}D'] = np.log(
                        safe_divide(result_df['close'], shifted_close, fill_value=1.0)
                    )

            # Price Position - 价格位置
            if 'price_position' in self.config:
                for period in self.config['price_position']:
                    rolling_min = result_df['close'].rolling(window=period).min()
                    rolling_max = result_df['close'].rolling(window=period).max()
                    result_df[f'PRICE_POSITION_{period}'] = safe_divide(
                        result_df['close'] - rolling_min,
                        rolling_max - rolling_min,
                        fill_value=0.5
                    )

            # OHLC Features - OHLC关系特征
            if self.config.get('ohlc_features', False):
                # 实体大小（收盘-开盘）
                result_df['BODY_SIZE'] = safe_divide(
                    result_df['close'] - result_df['open'],
                    result_df['open'],
                    fill_value=0
                )

                # 上影线大小
                result_df['UPPER_SHADOW'] = safe_divide(
                    result_df['high'] - result_df[['open', 'close']].max(axis=1),
                    result_df['open'],
                    fill_value=0
                )

                # 下影线大小
                result_df['LOWER_SHADOW'] = safe_divide(
                    result_df[['open', 'close']].min(axis=1) - result_df['low'],
                    result_df['open'],
                    fill_value=0
                )

                # 日内振幅
                result_df['INTRADAY_RANGE'] = safe_divide(
                    result_df['high'] - result_df['low'],
                    result_df['open'],
                    fill_value=0
                )

            logger.debug(f"PriceTransformStrategy generated {len(self.feature_names)} features")
            return result_df

        except Exception as e:
            logger.error(f"价格转换特征计算失败: {str(e)}")
            raise FeatureComputationError(f"价格转换特征计算失败: {str(e)}") from e

    def _get_feature_names(self) -> List[str]:
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

    将多个特征策略组合在一起，按顺序执行。
    优点：
    1. 可以灵活组合不同的特征策略
    2. 支持策略的动态添加和移除
    3. 统一的接口，便于使用

    Example:
        >>> tech_strategy = TechnicalIndicatorStrategy(config={'ma': [5, 20]})
        >>> alpha_strategy = AlphaFactorStrategy(config={'momentum': [5]})
        >>> composite = CompositeFeatureStrategy([tech_strategy, alpha_strategy])
        >>> result_df = composite.compute(df)

    Attributes:
        strategies: 策略列表
        inplace: 是否在原始DataFrame上修改（优化内存使用）
    """

    def __init__(self, strategies: List[FeatureStrategy], inplace: bool = False):
        """
        初始化组合策略

        Args:
            strategies: 策略列表
            inplace: 是否在原始DataFrame上修改（默认False，会复制数据）

        Raises:
            ValueError: 策略列表为空或包含无效策略
        """
        if not strategies:
            raise ValueError("策略列表不能为空")

        if not all(isinstance(s, FeatureStrategy) for s in strategies):
            raise ValueError("所有元素必须是 FeatureStrategy 实例")

        self.strategies = strategies
        self.inplace = inplace
        super().__init__(config={})

    @validate_ohlcv_data()
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        依次执行所有策略

        Args:
            df: 输入数据

        Returns:
            添加了所有特征的 DataFrame

        Raises:
            FeatureComputationError: 某个策略执行失败
        """
        # 根据 inplace 参数决定是否复制
        result_df = df if self.inplace else df.copy()

        failed_strategies = []

        for i, strategy in enumerate(self.strategies):
            try:
                logger.debug(
                    f"执行策略 [{i+1}/{len(self.strategies)}]: {strategy.__class__.__name__}"
                )
                # 对于第一个策略之后，使用 inplace=True 避免多次复制
                if i == 0:
                    result_df = strategy.compute(result_df)
                else:
                    # 直接在 result_df 上操作，避免复制
                    temp_result = strategy.compute(result_df)
                    # 只复制新增的列
                    new_cols = [col for col in temp_result.columns if col not in result_df.columns]
                    for col in new_cols:
                        result_df[col] = temp_result[col]

            except Exception as e:
                logger.error(f"策略 {strategy.__class__.__name__} 执行失败: {str(e)}")
                failed_strategies.append(strategy.__class__.__name__)
                # 根据配置决定是否继续执行
                # 这里选择继续执行其他策略
                continue

        if failed_strategies:
            logger.warning(f"以下策略执行失败: {failed_strategies}")

        logger.info(
            f"CompositeFeatureStrategy 执行完成: "
            f"{len(self.strategies)} 个策略, "
            f"生成 {len(self.feature_names)} 个特征, "
            f"失败 {len(failed_strategies)} 个"
        )
        return result_df

    def _get_feature_names(self) -> List[str]:
        """返回所有策略的特征名称"""
        all_features = []
        for strategy in self.strategies:
            all_features.extend(strategy.feature_names)
        return all_features

    def add_strategy(self, strategy: FeatureStrategy) -> None:
        """
        添加新策略

        Args:
            strategy: 要添加的策略
        """
        if not isinstance(strategy, FeatureStrategy):
            raise ValueError("必须是 FeatureStrategy 实例")

        self.strategies.append(strategy)
        # 清除缓存
        self._feature_cache = None
        logger.debug(f"添加策略: {strategy.__class__.__name__}")

    def remove_strategy(self, strategy_class: type) -> bool:
        """
        移除指定类型的策略

        Args:
            strategy_class: 策略类

        Returns:
            是否成功移除
        """
        original_len = len(self.strategies)
        self.strategies = [s for s in self.strategies if not isinstance(s, strategy_class)]

        if len(self.strategies) < original_len:
            # 清除缓存
            self._feature_cache = None
            logger.debug(f"移除策略: {strategy_class.__name__}")
            return True

        return False

    def get_strategy(self, strategy_class: type) -> Optional[FeatureStrategy]:
        """
        获取指定类型的策略实例

        Args:
            strategy_class: 策略类

        Returns:
            策略实例，如果不存在返回 None
        """
        for strategy in self.strategies:
            if isinstance(strategy, strategy_class):
                return strategy
        return None

    def __repr__(self) -> str:
        strategy_names = [s.__class__.__name__ for s in self.strategies]
        return f"CompositeFeatureStrategy(strategies={strategy_names}, inplace={self.inplace})"


# ==================== 便捷函数 ====================

def create_default_feature_pipeline(inplace: bool = False) -> CompositeFeatureStrategy:
    """
    创建默认的特征流水线

    包含完整的技术指标、Alpha因子和价格转换特征。
    适用于完整的特征工程场景。

    Args:
        inplace: 是否在原始DataFrame上修改（优化内存）

    Returns:
        组合特征策略，包含约125+特征

    Example:
        >>> pipeline = create_default_feature_pipeline()
        >>> result_df = pipeline.compute(df)
        >>> print(f"生成 {len(pipeline.feature_names)} 个特征")
    """
    return CompositeFeatureStrategy(
        strategies=[
            TechnicalIndicatorStrategy(),
            AlphaFactorStrategy(),
            PriceTransformStrategy(),
        ],
        inplace=inplace
    )


def create_minimal_feature_pipeline(inplace: bool = False) -> CompositeFeatureStrategy:
    """
    创建最小特征流水线（快速计算）

    仅包含最常用的指标，计算速度快，内存占用少。
    适用于快速回测或资源受限的场景。

    Args:
        inplace: 是否在原始DataFrame上修改（优化内存）

    Returns:
        组合特征策略，包含约15个特征

    Example:
        >>> pipeline = create_minimal_feature_pipeline(inplace=True)
        >>> result_df = pipeline.compute(df)
    """
    return CompositeFeatureStrategy(
        strategies=[
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
        ],
        inplace=inplace
    )


def create_custom_feature_pipeline(
    technical_config: Optional[Dict[str, Any]] = None,
    alpha_config: Optional[Dict[str, Any]] = None,
    price_config: Optional[Dict[str, Any]] = None,
    inplace: bool = False,
) -> CompositeFeatureStrategy:
    """
    创建自定义特征流水线

    根据提供的配置灵活组合策略。如果某个配置为 None，
    则不包含对应的策略。如果提供空字典 {}，则使用默认配置。

    Args:
        technical_config: 技术指标配置，None表示不包含，{}表示使用默认配置
        alpha_config: Alpha因子配置，None表示不包含，{}表示使用默认配置
        price_config: 价格转换配置，None表示不包含，{}表示使用默认配置
        inplace: 是否在原始DataFrame上修改（优化内存）

    Returns:
        组合特征策略

    Example:
        >>> # 只使用技术指标和价格转换
        >>> pipeline = create_custom_feature_pipeline(
        ...     technical_config={'ma': [5, 10, 20]},
        ...     price_config={'returns': [1, 5, 10]},
        ...     alpha_config=None  # 不包含 Alpha 因子
        ... )

        >>> # 全部使用默认配置
        >>> pipeline = create_custom_feature_pipeline(
        ...     technical_config={},
        ...     alpha_config={},
        ...     price_config={}
        ... )
    """
    strategies = []

    if technical_config is not None:
        strategies.append(TechnicalIndicatorStrategy(config=technical_config))

    if alpha_config is not None:
        strategies.append(AlphaFactorStrategy(config=alpha_config))

    if price_config is not None:
        strategies.append(PriceTransformStrategy(config=price_config))

    if not strategies:
        logger.warning("没有提供任何策略配置，返回空的组合策略")

    return CompositeFeatureStrategy(strategies, inplace=inplace)


# ==================== 导出 ====================

__all__ = [
    # 异常类
    'FeatureComputationError',
    'InvalidDataError',
    # 基类
    'FeatureStrategy',
    # 策略类
    'TechnicalIndicatorStrategy',
    'AlphaFactorStrategy',
    'PriceTransformStrategy',
    'CompositeFeatureStrategy',
    # 便捷函数
    'create_default_feature_pipeline',
    'create_minimal_feature_pipeline',
    'create_custom_feature_pipeline',
    # 辅助函数
    'safe_divide',
    'merge_configs',
]
