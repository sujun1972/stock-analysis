"""
特征策略模式实现

通过策略模式实现可组合的特征计算，提供灵活的特征工程能力。

## 架构设计

### 核心类
- `FeatureStrategy`: 抽象基类，定义特征策略接口
- `TechnicalIndicatorStrategy`: 技术指标策略（MA、RSI、MACD 等）
- `AlphaFactorStrategy`: Alpha 因子策略（动量、反转、波动率等）
- `PriceTransformStrategy`: 价格转换策略（收益率、价格位置等）
- `CompositeFeatureStrategy`: 组合策略，支持多策略组合

### 异常类
- `FeatureComputationError`: 特征计算错误
- `InvalidDataError`: 输入数据无效

### 设计模式
1. **策略模式**: 不同特征计算策略的封装
2. **装饰器模式**: 数据验证、错误处理、安全计算
3. **组合模式**: 支持策略的组合和嵌套
4. **工厂模式**: 便捷函数创建常用管道

### 使用示例

```python
# 1. 使用预定义管道（推荐）
pipeline = create_default_feature_pipeline()
result = pipeline.compute(df)

# 2. 自定义单一策略
strategy = TechnicalIndicatorStrategy(config={'ma': [5, 10, 20]})
result = strategy.compute(df)

# 3. 组合多个策略
composite = CompositeFeatureStrategy([
    TechnicalIndicatorStrategy(config={'ma': [5, 20]}),
    AlphaFactorStrategy(config={'momentum': [5]})
])
result = composite.compute(df)

# 4. 动态管理策略
composite.add_strategy(PriceTransformStrategy())
composite.remove_strategy(AlphaFactorStrategy)
```

### 性能优化
- 特征名称缓存
- `inplace` 参数减少内存复制
- 安全除法避免无穷值
- 配置驱动的特征生成

### 版本历史
- v2.0: 添加异常处理、数据验证、配置优化
- v1.0: 初始版本

作者: Stock Analysis Team
更新: 2026-01-27
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Callable
import pandas as pd
import numpy as np
from loguru import logger
from functools import wraps

# 导入技术指标计算器
try:
    from .indicators_calculator import (
        safe_divide,
        calculate_rsi,
        calculate_macd,
        calculate_kdj,
        calculate_boll,
        calculate_atr,
        calculate_obv,
        calculate_cci
    )
except ImportError:
    # 直接执行时的fallback
    from indicators_calculator import (
        safe_divide,
        calculate_rsi,
        calculate_macd,
        calculate_kdj,
        calculate_boll,
        calculate_atr,
        calculate_obv,
        calculate_cci
    )


# ==================== 类型别名 ====================

ConfigDict = Dict[str, Any]  # 配置字典类型
PeriodList = List[int]  # 周期列表类型
TupleParams = List[tuple]  # 元组参数列表类型


# ==================== 异常类 ====================

# 导入统一异常系统
from src.exceptions import FeatureCalculationError, DataValidationError

# 向后兼容：保留旧异常名称作为别名
class FeatureComputationError(FeatureCalculationError):
    """特征计算错误（向后兼容别名）

    该异常类现在继承自统一异常系统的FeatureCalculationError。
    支持错误代码和上下文信息。

    Migration Note:
        旧代码: raise FeatureComputationError("计算失败")
        新代码: raise FeatureComputationError(
                    "计算失败",
                    error_code="FEATURE_CALC_ERROR",
                    feature_name="MA_20",
                    stock_code="000001"
                )

    Examples:
        >>> raise FeatureComputationError(
        ...     "MA计算失败",
        ...     error_code="MA_CALCULATION_ERROR",
        ...     period=20,
        ...     data_length=10,
        ...     reason="数据点不足"
        ... )
    """
    pass


class InvalidDataError(DataValidationError):
    """无效数据错误（向后兼容别名）

    该异常类现在继承自统一异常系统的DataValidationError。
    支持错误代码和上下文信息。

    Migration Note:
        旧代码: raise InvalidDataError("DataFrame为空")
        新代码: raise InvalidDataError(
                    "DataFrame为空",
                    error_code="EMPTY_DATAFRAME",
                    expected_rows=">0",
                    actual_rows=0
                )

    Examples:
        >>> raise InvalidDataError(
        ...     "缺少必需列",
        ...     error_code="MISSING_REQUIRED_COLUMNS",
        ...     required_columns=['open', 'high', 'low', 'close'],
        ...     actual_columns=df.columns.tolist(),
        ...     missing_columns=['volume']
        ... )
    """
    pass


# ==================== 装饰器 ====================

def validate_ohlcv_data(required_cols: Optional[List[str]] = None) -> Callable:
    """
    验证OHLCV数据的装饰器

    检查输入 DataFrame 是否包含必需的列，并验证数据量是否充足。

    Args:
        required_cols: 必需的列名列表，默认为 ['open', 'high', 'low', 'close', 'volume']

    Returns:
        装饰器函数

    Raises:
        InvalidDataError: DataFrame 为空或缺少必需列

    Example:
        >>> @validate_ohlcv_data(['open', 'high', 'low', 'close'])
        >>> def my_compute(self, df: pd.DataFrame) -> pd.DataFrame:
        ...     return df
    """
    def decorator(func: Callable) -> Callable:
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


def safe_compute(feature_name: str) -> Callable:
    """
    安全计算装饰器，捕获计算异常

    用于包装指标计算方法，提供统一的错误处理和日志记录。

    Args:
        feature_name: 特征名称，用于日志和错误消息

    Returns:
        装饰器函数

    Raises:
        FeatureComputationError: 计算过程中发生错误

    Example:
        >>> @safe_compute("RSI")
        >>> def calculate_rsi(series: pd.Series, period: int) -> pd.Series:
        ...     return series  # 实际计算逻辑
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"计算 {feature_name} 时出错: {str(e)}")
                raise FeatureComputationError(f"计算 {feature_name} 失败: {str(e)}") from e
        return wrapper
    return decorator


# ==================== 辅助函数 ====================
# 注意：safe_divide 已移至 indicators_calculator.py

def merge_configs(default_config: ConfigDict, user_config: Optional[ConfigDict]) -> ConfigDict:
    """
    合并默认配置和用户配置

    如果用户配置为 None，返回默认配置的副本。
    否则，将用户配置覆盖到默认配置上。

    Args:
        default_config: 默认配置字典
        user_config: 用户配置字典，可以为 None

    Returns:
        合并后的配置字典

    Example:
        >>> default = {'ma': [5, 10], 'rsi': [14]}
        >>> user = {'ma': [20, 60]}
        >>> merged = merge_configs(default, user)
        >>> logger.info(f"{merged}")
        {'ma': [20, 60], 'rsi': [14]}
    """
    if user_config is None:
        return default_config.copy()

    merged = default_config.copy()
    merged.update(user_config)
    return merged


def validate_period_config(config: ConfigDict, keys: List[str], config_name: str = "配置") -> None:
    """
    验证周期配置参数

    检查指定的配置键是否为正整数列表。

    Args:
        config: 配置字典
        keys: 需要验证的配置键列表
        config_name: 配置名称（用于错误消息）

    Raises:
        ValueError: 配置类型错误或周期不是正整数

    Example:
        >>> config = {'ma': [5, 10, 20], 'rsi': [14]}
        >>> validate_period_config(config, ['ma', 'rsi'], "MyStrategy")
        # 验证通过，无返回值
    """
    for key in keys:
        if key in config:
            if not isinstance(config[key], list):
                raise ValueError(f"{config_name} 中的 {key} 必须是列表类型")
            if not all(isinstance(p, int) and p > 0 for p in config[key]):
                raise ValueError(f"{config_name} 中的 {key} 周期必须是正整数")


def validate_tuple_config(
    config: ConfigDict,
    keys: List[str],
    expected_length: Optional[int] = None,
    config_name: str = "配置"
) -> None:
    """
    验证元组配置参数

    检查指定的配置键是否为元组列表，并可选地验证元组长度。

    Args:
        config: 配置字典
        keys: 需要验证的配置键列表
        expected_length: 期望的元组长度（None 表示不检查长度）
        config_name: 配置名称（用于错误消息）

    Raises:
        ValueError: 配置类型错误或元组长度不匹配

    Example:
        >>> config = {'macd': [(12, 26, 9)], 'correlation': [(5, 20)]}
        >>> validate_tuple_config(config, ['macd'], expected_length=3, config_name="MyStrategy")
        # 验证通过，无返回值
    """
    for key in keys:
        if key in config:
            if not isinstance(config[key], list):
                raise ValueError(f"{config_name} 中的 {key} 必须是列表类型")

            for params in config[key]:
                if not isinstance(params, tuple):
                    raise ValueError(f"{config_name} 中的 {key} 参数必须是元组")

                if expected_length is not None and len(params) != expected_length:
                    raise ValueError(
                        f"{config_name} 中的 {key} 参数必须包含 {expected_length} 个元素，"
                        f"实际为 {len(params)} 个"
                    )


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
        >>> logger.info(f"{strategy.feature_names}")
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
        validate_period_config(
            self.config,
            ['ma', 'ema', 'rsi', 'atr', 'cci'],
            "TechnicalIndicatorStrategy"
        )
        validate_tuple_config(
            self.config,
            ['macd', 'kdj', 'boll'],
            config_name="TechnicalIndicatorStrategy"
        )

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
                    result_df[f'RSI_{period}'] = calculate_rsi(result_df['close'], period)

            # MACD
            if 'macd' in self.config:
                for fast, slow, signal in self.config['macd']:
                    macd, signal_line, hist = calculate_macd(result_df['close'], fast, slow, signal)
                    result_df[f'MACD_{fast}_{slow}'] = macd
                    result_df[f'MACD_SIGNAL_{fast}_{slow}'] = signal_line
                    result_df[f'MACD_HIST_{fast}_{slow}'] = hist

            # KDJ
            if 'kdj' in self.config:
                for n, m1, m2 in self.config['kdj']:
                    k, d, j = calculate_kdj(result_df, n, m1, m2)
                    result_df[f'KDJ_K_{n}'] = k
                    result_df[f'KDJ_D_{n}'] = d
                    result_df[f'KDJ_J_{n}'] = j

            # BOLL - 布林带
            if 'boll' in self.config:
                for period, std_num in self.config['boll']:
                    upper, middle, lower = calculate_boll(result_df['close'], period, std_num)
                    result_df[f'BOLL_UPPER_{period}'] = upper
                    result_df[f'BOLL_MIDDLE_{period}'] = middle
                    result_df[f'BOLL_LOWER_{period}'] = lower

            # ATR - 平均真实波幅
            if 'atr' in self.config:
                for period in self.config['atr']:
                    result_df[f'ATR_{period}'] = calculate_atr(result_df, period)

            # OBV - 能量潮
            if self.config.get('obv', False):
                result_df['OBV'] = calculate_obv(result_df)

            # CCI - 商品通道指标
            if 'cci' in self.config:
                for period in self.config['cci']:
                    result_df[f'CCI_{period}'] = calculate_cci(result_df, period)

            logger.debug(f"TechnicalIndicatorStrategy generated {len(self.feature_names)} features")
            return result_df

        except Exception as e:
            logger.error(f"技术指标计算失败: {str(e)}")
            raise FeatureComputationError(f"技术指标计算失败: {str(e)}") from e

    def _get_feature_names(self) -> List[str]:
        """返回特征名称列表（使用配置驱动生成）"""
        features = []

        # 单参数指标
        single_param_indicators = {
            'ma': 'MA_{}',
            'ema': 'EMA_{}',
            'rsi': 'RSI_{}',
            'atr': 'ATR_{}',
            'cci': 'CCI_{}'
        }

        for key, template in single_param_indicators.items():
            if key in self.config:
                features.extend([template.format(p) for p in self.config[key]])

        # MACD (多输出)
        if 'macd' in self.config:
            for fast, slow, _ in self.config['macd']:
                features.extend([
                    f'MACD_{fast}_{slow}',
                    f'MACD_SIGNAL_{fast}_{slow}',
                    f'MACD_HIST_{fast}_{slow}'
                ])

        # KDJ (多输出)
        if 'kdj' in self.config:
            for n, _, _ in self.config['kdj']:
                features.extend([f'KDJ_K_{n}', f'KDJ_D_{n}', f'KDJ_J_{n}'])

        # BOLL (多输出)
        if 'boll' in self.config:
            for period, _ in self.config['boll']:
                features.extend([
                    f'BOLL_UPPER_{period}',
                    f'BOLL_MIDDLE_{period}',
                    f'BOLL_LOWER_{period}'
                ])

        # OBV (布尔配置)
        if self.config.get('obv', False):
            features.append('OBV')

        return features

    # 注意：所有指标计算方法已移至 indicators_calculator.py 模块


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
        validate_period_config(
            self.config,
            ['momentum', 'reversal', 'volatility', 'volume'],
            "AlphaFactorStrategy"
        )
        validate_tuple_config(
            self.config,
            ['correlation'],
            expected_length=2,
            config_name="AlphaFactorStrategy"
        )

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
        """返回特征名称列表（使用配置驱动生成）"""
        features = []

        # 单参数因子
        single_param_factors = {
            'momentum': 'MOMENTUM_{}',
            'reversal': 'REVERSAL_{}',
            'volatility': 'VOLATILITY_{}',
            'volume': 'VOLUME_RATIO_{}'
        }

        for key, template in single_param_factors.items():
            if key in self.config:
                features.extend([template.format(p) for p in self.config[key]])

        # 相关性因子 (双参数)
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
        validate_period_config(
            self.config,
            ['returns', 'log_returns', 'price_position'],
            "PriceTransformStrategy"
        )

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
        """返回特征名称列表（使用配置驱动生成）"""
        features = []

        # 单参数特征
        single_param_features = {
            'returns': 'RETURN_{}D',
            'log_returns': 'LOG_RETURN_{}D',
            'price_position': 'PRICE_POSITION_{}'
        }

        for key, template in single_param_features.items():
            if key in self.config:
                features.extend([template.format(p) for p in self.config[key]])

        # OHLC 特征组
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
        >>> logger.info(f"生成 {len(pipeline.feature_names)} 个特征")
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
    'validate_period_config',
    'validate_tuple_config',
]
