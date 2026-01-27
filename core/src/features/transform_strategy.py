"""
特征转换策略模式实现

通过策略模式实现可组合的特征转换，提供灵活的数据预处理能力。

## 架构设计

### 核心类
- `TransformStrategy`: 抽象基类，定义转换策略接口
- `PriceChangeTransformStrategy`: 价格变动率转换（用于时序模型）
- `NormalizationStrategy`: 标准化和归一化转换
- `TimeFeatureStrategy`: 时间特征提取
- `StatisticalFeatureStrategy`: 统计特征（滞后、滚动）
- `CompositeTransformStrategy`: 组合转换策略

### 设计模式
1. **策略模式**: 不同转换策略的封装
2. **装饰器模式**: 数据验证、错误处理
3. **组合模式**: 支持策略的组合和嵌套
4. **工厂模式**: 便捷函数创建常用管道

### 使用示例

```python
# 1. 使用预定义管道（推荐）
pipeline = create_default_transform_pipeline()
result = pipeline.transform(df)

# 2. 自定义单一策略
strategy = NormalizationStrategy(config={'method': 'robust'})
result = strategy.transform(df)

# 3. 组合多个策略
composite = CompositeTransformStrategy([
    PriceChangeTransformStrategy(),
    NormalizationStrategy(),
    TimeFeatureStrategy()
])
result = composite.transform(df)
```

作者: Stock Analysis Team
更新: 2026-01-27
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union, Callable
import pandas as pd
import numpy as np
from pathlib import Path
import pickle
from loguru import logger
from functools import wraps
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler


# ==================== 类型别名 ====================

ConfigDict = Dict[str, Any]
ScalerType = Union[StandardScaler, RobustScaler, MinMaxScaler]


# ==================== 异常类 ====================

class TransformError(Exception):
    """转换错误基类"""
    pass


class InvalidDataError(TransformError):
    """无效数据错误"""
    pass


class ScalerNotFoundError(TransformError):
    """Scaler未找到错误"""
    pass


# ==================== 装饰器 ====================

def validate_dataframe(min_rows: int = 2) -> Callable:
    """
    验证DataFrame的装饰器

    Args:
        min_rows: 最小行数要求

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, df: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
            if df is None or df.empty:
                raise InvalidDataError("输入 DataFrame 为空")

            if len(df) < min_rows:
                logger.warning(f"数据量不足（{len(df)} 行），某些转换可能无法完成")

            return func(self, df, *args, **kwargs)
        return wrapper
    return decorator


def safe_transform(transform_name: str) -> Callable:
    """
    安全转换装饰器，捕获异常并记录日志

    Args:
        transform_name: 转换名称

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"执行 {transform_name} 转换时出错: {str(e)}", exc_info=True)
                raise TransformError(f"{transform_name} 转换失败: {str(e)}") from e
        return wrapper
    return decorator


# ==================== 辅助函数 ====================

def safe_divide(numerator: pd.Series, denominator: pd.Series, fill_value: float = 0.0) -> pd.Series:
    """
    安全除法，处理除零和无穷值

    Args:
        numerator: 分子
        denominator: 分母
        fill_value: 填充值

    Returns:
        计算结果
    """
    result = numerator / (denominator + 1e-10)
    result = result.replace([np.inf, -np.inf], fill_value)
    result = result.fillna(fill_value)
    return result


def merge_configs(default_config: ConfigDict, user_config: Optional[ConfigDict]) -> ConfigDict:
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


# ==================== 抽象基类 ====================

class TransformStrategy(ABC):
    """
    转换策略抽象基类

    所有转换策略都必须继承此类并实现 transform 方法
    """

    DEFAULT_CONFIG: ConfigDict = {}

    def __init__(self, config: Optional[ConfigDict] = None):
        """
        初始化转换策略

        Args:
            config: 策略配置字典
        """
        self.config = merge_configs(self.DEFAULT_CONFIG, config)
        self._validate_config()
        self._feature_cache: Optional[List[str]] = None

    @abstractmethod
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        执行特征转换

        Args:
            df: 输入 DataFrame

        Returns:
            转换后的 DataFrame

        Raises:
            InvalidDataError: 输入数据无效
            TransformError: 转换失败
        """
        pass

    def _validate_config(self) -> None:
        """验证配置（子类可选实现）"""
        pass

    @property
    def feature_names(self) -> List[str]:
        """返回该策略生成的特征名称列表"""
        if self._feature_cache is None:
            self._feature_cache = self._get_feature_names()
        return self._feature_cache

    @abstractmethod
    def _get_feature_names(self) -> List[str]:
        """子类实现：返回特征名称列表"""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self.config})"


# ==================== 具体策略类 ====================

class PriceChangeTransformStrategy(TransformStrategy):
    """
    价格变动率转换策略

    用于时间序列模型（GRU/LSTM）的输入准备。
    支持：
    - 价格变动率矩阵（回看窗口）
    - 多时间尺度收益率
    - OHLC 衍生特征

    Example:
        >>> strategy = PriceChangeTransformStrategy(config={'lookback_days': 20})
        >>> result_df = strategy.transform(df)
    """

    DEFAULT_CONFIG = {
        'lookback_days': 20,
        'price_col': 'close',
        'return_periods': [1, 3, 5, 10, 20],
        'include_log_returns': True,
        'include_ohlc_features': True,
    }

    @validate_dataframe(min_rows=2)
    @safe_transform("价格变动率")
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行价格变动率转换"""
        result_df = df.copy()

        # 1. 价格变动率矩阵
        if 'lookback_days' in self.config:
            result_df = self._create_price_change_matrix(result_df)

        # 2. 多时间尺度收益率
        if 'return_periods' in self.config:
            result_df = self._create_multi_timeframe_returns(result_df)

        # 3. OHLC特征
        if self.config.get('include_ohlc_features', False):
            result_df = self._create_ohlc_features(result_df)

        logger.debug(f"PriceChangeTransformStrategy generated {len(self.feature_names)} features")
        return result_df

    def _create_price_change_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建价格变动率矩阵"""
        lookback_days = self.config['lookback_days']
        price_col = self.config['price_col']

        price_changes = df[price_col].pct_change()

        for i in range(1, lookback_days + 1):
            df[f'PRICE_CHG_T-{i}'] = price_changes.shift(i) * 100

        return df

    def _create_multi_timeframe_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建多时间尺度收益率"""
        price_col = self.config['price_col']
        periods = self.config['return_periods']

        for period in periods:
            # 简单收益率
            df[f'RETURN_{period}D'] = df[price_col].pct_change(period) * 100

            # 对数收益率
            if self.config.get('include_log_returns', False):
                df[f'LOG_RETURN_{period}D'] = np.log(
                    df[price_col] / df[price_col].shift(period)
                ) * 100

        return df

    def _create_ohlc_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """创建OHLC衍生特征"""
        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            logger.warning("缺少OHLC列，跳过OHLC特征创建")
            return df

        # 价格位置
        df['PRICE_POSITION_DAILY'] = safe_divide(
            df['close'] - df['low'],
            df['high'] - df['low']
        ) * 100

        # 实体强度
        df['BODY_STRENGTH'] = safe_divide(
            df['close'] - df['open'],
            df['high'] - df['low']
        ) * 100

        # 上影线比例
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        df['UPPER_SHADOW_RATIO'] = safe_divide(
            upper_shadow,
            df['high'] - df['low']
        ) * 100

        # 下影线比例
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        df['LOWER_SHADOW_RATIO'] = safe_divide(
            lower_shadow,
            df['high'] - df['low']
        ) * 100

        return df

    def _get_feature_names(self) -> List[str]:
        """返回特征名称列表"""
        features = []

        # 价格变动率矩阵
        if 'lookback_days' in self.config:
            lookback = self.config['lookback_days']
            features.extend([f'PRICE_CHG_T-{i}' for i in range(1, lookback + 1)])

        # 收益率
        if 'return_periods' in self.config:
            for period in self.config['return_periods']:
                features.append(f'RETURN_{period}D')
                if self.config.get('include_log_returns', False):
                    features.append(f'LOG_RETURN_{period}D')

        # OHLC特征
        if self.config.get('include_ohlc_features', False):
            features.extend([
                'PRICE_POSITION_DAILY',
                'BODY_STRENGTH',
                'UPPER_SHADOW_RATIO',
                'LOWER_SHADOW_RATIO'
            ])

        return features


class NormalizationStrategy(TransformStrategy):
    """
    标准化转换策略

    支持多种标准化方法：
    - standard: 标准化（均值0，标准差1）
    - robust: 鲁棒标准化（中位数和四分位数）
    - minmax: 最小-最大归一化（0-1范围）
    - rank: 排名转换

    支持 Scaler 的持久化和加载。

    Example:
        >>> strategy = NormalizationStrategy(config={'method': 'robust'})
        >>> result_df = strategy.transform(df)
        >>> strategy.save_scalers('models/scalers.pkl')
    """

    DEFAULT_CONFIG = {
        'method': 'robust',
        'feature_cols': None,  # None表示自动检测数值列
        'fit': True,
        'rank_transform': False,
        'rank_window': None,
    }

    def __init__(self, config: Optional[ConfigDict] = None):
        super().__init__(config)
        self.scalers: Dict[str, ScalerType] = {}

    @validate_dataframe(min_rows=2)
    @safe_transform("标准化")
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """执行标准化转换"""
        result_df = df.copy()

        # 确定要标准化的列
        feature_cols = self._get_feature_columns(result_df)

        if not feature_cols:
            logger.warning("没有找到需要标准化的列")
            return result_df

        # 标准化
        if self.config.get('method') in ['standard', 'robust', 'minmax']:
            result_df = self._normalize_features(result_df, feature_cols)

        # 排名转换
        if self.config.get('rank_transform', False):
            result_df = self._rank_transform(result_df, feature_cols)

        logger.debug(f"NormalizationStrategy processed {len(feature_cols)} columns")
        return result_df

    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """获取需要标准化的列"""
        if self.config['feature_cols'] is not None:
            return [col for col in self.config['feature_cols'] if col in df.columns]

        # 自动检测数值列
        return df.select_dtypes(include=[np.number]).columns.tolist()

    def _normalize_features(self, df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
        """标准化特征"""
        method = self.config['method']
        fit = self.config['fit']

        # 选择scaler类型
        scaler_mapping = {
            'standard': StandardScaler,
            'robust': RobustScaler,
            'minmax': MinMaxScaler
        }

        scaler_class = scaler_mapping.get(method)
        if scaler_class is None:
            raise ValueError(f"不支持的标准化方法: {method}")

        for col in feature_cols:
            if col not in df.columns:
                logger.warning(f"列 '{col}' 不存在，跳过")
                continue

            # 处理无效值
            valid_mask = np.isfinite(df[col])
            if not valid_mask.all():
                logger.debug(f"列 '{col}' 包含 {(~valid_mask).sum()} 个无效值")

            scaler_key = f"{col}_{method}"

            # 拟合或使用已有scaler
            if fit:
                scaler = scaler_class()
                valid_data = df.loc[valid_mask, [col]]
                if len(valid_data) > 0:
                    scaler.fit(valid_data)
                    self.scalers[scaler_key] = scaler
                else:
                    logger.warning(f"列 '{col}' 无有效数据，跳过")
                    continue
            else:
                if scaler_key not in self.scalers:
                    raise ScalerNotFoundError(f"找不到列 '{col}' 的 {method} scaler")
                scaler = self.scalers[scaler_key]

            # 转换
            if valid_mask.sum() > 0:
                transformed = scaler.transform(df.loc[valid_mask, [col]])
                df.loc[valid_mask, f'{col}_NORM'] = transformed.flatten()

        return df

    def _rank_transform(self, df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
        """排名转换"""
        window = self.config.get('rank_window')

        for col in feature_cols:
            if col not in df.columns:
                continue

            if window is None:
                # 全局排名
                df[f'{col}_PCT_RANK'] = df[col].rank(pct=True)
            else:
                # 滚动排名
                df[f'{col}_PCT_RANK'] = df[col].rolling(window=window).apply(
                    lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) == window else np.nan,
                    raw=False
                )

        return df

    def save_scalers(self, file_path: Union[str, Path]) -> bool:
        """保存scalers到文件"""
        try:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'wb') as f:
                pickle.dump(self.scalers, f)

            logger.info(f"Scalers 已保存到 {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存 scalers 失败: {e}", exc_info=True)
            return False

    def load_scalers(self, file_path: Union[str, Path]) -> bool:
        """从文件加载scalers"""
        try:
            file_path = Path(file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"Scaler 文件不存在: {file_path}")

            with open(file_path, 'rb') as f:
                self.scalers = pickle.load(f)

            logger.info(f"已从 {file_path} 加载 {len(self.scalers)} 个 scalers")
            return True
        except Exception as e:
            logger.error(f"加载 scalers 失败: {e}", exc_info=True)
            return False

    def _get_feature_names(self) -> List[str]:
        """返回特征名称列表"""
        features = []

        # 标准化后的列名
        if self.config['feature_cols'] is not None:
            features.extend([f'{col}_NORM' for col in self.config['feature_cols']])

        # 排名列
        if self.config.get('rank_transform', False) and self.config['feature_cols'] is not None:
            features.extend([f'{col}_PCT_RANK' for col in self.config['feature_cols']])

        return features


class TimeFeatureStrategy(TransformStrategy):
    """
    时间特征提取策略

    从 DatetimeIndex 中提取时间相关特征：
    - 星期几
    - 月份、季度
    - 月初/月末、季度初/季度末、年初/年末标志

    Example:
        >>> strategy = TimeFeatureStrategy()
        >>> result_df = strategy.transform(df)
    """

    DEFAULT_CONFIG = {
        'include_day_of_week': True,
        'include_month': True,
        'include_quarter': True,
        'include_period_flags': True,
    }

    @validate_dataframe(min_rows=1)
    @safe_transform("时间特征")
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """提取时间特征"""
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning("DataFrame索引不是DatetimeIndex，跳过时间特征")
            return df

        result_df = df.copy()

        # 星期几
        if self.config.get('include_day_of_week', True):
            result_df['DAY_OF_WEEK'] = result_df.index.dayofweek

        # 月份
        if self.config.get('include_month', True):
            result_df['MONTH'] = result_df.index.month

        # 季度
        if self.config.get('include_quarter', True):
            result_df['QUARTER'] = result_df.index.quarter

        # 周期标志
        if self.config.get('include_period_flags', True):
            result_df['IS_MONTH_START'] = result_df.index.is_month_start.astype(int)
            result_df['IS_MONTH_END'] = result_df.index.is_month_end.astype(int)
            result_df['IS_QUARTER_START'] = result_df.index.is_quarter_start.astype(int)
            result_df['IS_QUARTER_END'] = result_df.index.is_quarter_end.astype(int)
            result_df['IS_YEAR_START'] = result_df.index.is_year_start.astype(int)
            result_df['IS_YEAR_END'] = result_df.index.is_year_end.astype(int)

        logger.debug(f"TimeFeatureStrategy generated {len(self.feature_names)} features")
        return result_df

    def _get_feature_names(self) -> List[str]:
        """返回特征名称列表"""
        features = []

        if self.config.get('include_day_of_week', True):
            features.append('DAY_OF_WEEK')

        if self.config.get('include_month', True):
            features.append('MONTH')

        if self.config.get('include_quarter', True):
            features.append('QUARTER')

        if self.config.get('include_period_flags', True):
            features.extend([
                'IS_MONTH_START', 'IS_MONTH_END',
                'IS_QUARTER_START', 'IS_QUARTER_END',
                'IS_YEAR_START', 'IS_YEAR_END'
            ])

        return features


class StatisticalFeatureStrategy(TransformStrategy):
    """
    统计特征策略

    支持：
    - 滞后特征（Lag）
    - 滚动统计特征（Mean、Std、Max、Min等）

    Example:
        >>> strategy = StatisticalFeatureStrategy(config={
        ...     'lag_periods': [1, 5, 10],
        ...     'rolling_windows': [5, 20]
        ... })
        >>> result_df = strategy.transform(df)
    """

    DEFAULT_CONFIG = {
        'feature_cols': ['close'],  # 需要计算统计特征的列
        'lag_periods': [1, 2, 3, 5, 10],
        'rolling_windows': [5, 10, 20],
        'rolling_funcs': ['mean', 'std', 'max', 'min'],
    }

    @validate_dataframe(min_rows=2)
    @safe_transform("统计特征")
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算统计特征"""
        result_df = df.copy()
        feature_cols = self.config['feature_cols']

        # 滞后特征
        if 'lag_periods' in self.config:
            result_df = self._create_lag_features(result_df, feature_cols)

        # 滚动统计特征
        if 'rolling_windows' in self.config:
            result_df = self._create_rolling_features(result_df, feature_cols)

        logger.debug(f"StatisticalFeatureStrategy generated {len(self.feature_names)} features")
        return result_df

    def _create_lag_features(self, df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
        """创建滞后特征"""
        lags = self.config['lag_periods']

        for col in feature_cols:
            if col not in df.columns:
                logger.warning(f"列 '{col}' 不存在，跳过")
                continue

            for lag in lags:
                df[f'{col}_LAG{lag}'] = df[col].shift(lag)

        return df

    def _create_rolling_features(self, df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
        """创建滚动统计特征"""
        windows = self.config['rolling_windows']
        funcs = self.config['rolling_funcs']

        # 函数映射
        func_mapping = {
            'mean': lambda r: r.mean(),
            'std': lambda r: r.std(),
            'max': lambda r: r.max(),
            'min': lambda r: r.min(),
            'median': lambda r: r.median(),
            'skew': lambda r: r.skew(),
            'kurt': lambda r: r.kurt()
        }

        for col in feature_cols:
            if col not in df.columns:
                logger.warning(f"列 '{col}' 不存在，跳过")
                continue

            for window in windows:
                rolling = df[col].rolling(window=window)

                for func in funcs:
                    if func not in func_mapping:
                        logger.warning(f"不支持的统计函数: {func}")
                        continue

                    try:
                        df[f'{col}_ROLL{window}_{func.upper()}'] = func_mapping[func](rolling)
                    except Exception as e:
                        logger.error(f"计算 {col} 的滚动{func}特征时出错: {e}")
                        continue

        return df

    def _get_feature_names(self) -> List[str]:
        """返回特征名称列表"""
        features = []
        feature_cols = self.config['feature_cols']

        # 滞后特征
        if 'lag_periods' in self.config:
            for col in feature_cols:
                for lag in self.config['lag_periods']:
                    features.append(f'{col}_LAG{lag}')

        # 滚动特征
        if 'rolling_windows' in self.config:
            for col in feature_cols:
                for window in self.config['rolling_windows']:
                    for func in self.config['rolling_funcs']:
                        features.append(f'{col}_ROLL{window}_{func.upper()}')

        return features


class CompositeTransformStrategy(TransformStrategy):
    """
    组合转换策略

    将多个转换策略组合在一起，按顺序执行。

    Example:
        >>> strategies = [
        ...     PriceChangeTransformStrategy(),
        ...     TimeFeatureStrategy(),
        ...     NormalizationStrategy()
        ... ]
        >>> composite = CompositeTransformStrategy(strategies)
        >>> result_df = composite.transform(df)
    """

    def __init__(self, strategies: List[TransformStrategy], inplace: bool = False):
        """
        初始化组合策略

        Args:
            strategies: 策略列表
            inplace: 是否在原始DataFrame上修改
        """
        if not strategies:
            raise ValueError("策略列表不能为空")

        if not all(isinstance(s, TransformStrategy) for s in strategies):
            raise ValueError("所有元素必须是 TransformStrategy 实例")

        self.strategies = strategies
        self.inplace = inplace
        super().__init__(config={})

    @validate_dataframe(min_rows=1)
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """依次执行所有策略"""
        result_df = df if self.inplace else df.copy()
        failed_strategies = []

        for i, strategy in enumerate(self.strategies):
            try:
                logger.debug(f"执行策略 [{i+1}/{len(self.strategies)}]: {strategy.__class__.__name__}")
                result_df = strategy.transform(result_df)
            except Exception as e:
                logger.error(f"策略 {strategy.__class__.__name__} 执行失败: {str(e)}")
                failed_strategies.append(strategy.__class__.__name__)
                continue

        if failed_strategies:
            logger.warning(f"以下策略执行失败: {failed_strategies}")

        logger.info(
            f"CompositeTransformStrategy 执行完成: "
            f"{len(self.strategies)} 个策略, "
            f"失败 {len(failed_strategies)} 个"
        )

        return result_df

    def _get_feature_names(self) -> List[str]:
        """返回所有策略的特征名称"""
        all_features = []
        for strategy in self.strategies:
            all_features.extend(strategy.feature_names)
        return all_features

    def add_strategy(self, strategy: TransformStrategy) -> None:
        """添加新策略"""
        if not isinstance(strategy, TransformStrategy):
            raise ValueError("必须是 TransformStrategy 实例")

        self.strategies.append(strategy)
        self._feature_cache = None
        logger.debug(f"添加策略: {strategy.__class__.__name__}")

    def remove_strategy(self, strategy_class: type) -> bool:
        """移除指定类型的策略"""
        original_len = len(self.strategies)
        self.strategies = [s for s in self.strategies if not isinstance(s, strategy_class)]

        if len(self.strategies) < original_len:
            self._feature_cache = None
            logger.debug(f"移除策略: {strategy_class.__name__}")
            return True

        return False

    def __repr__(self) -> str:
        strategy_names = [s.__class__.__name__ for s in self.strategies]
        return f"CompositeTransformStrategy(strategies={strategy_names}, inplace={self.inplace})"


# ==================== 便捷函数（工厂方法）====================

def create_default_transform_pipeline(inplace: bool = False) -> CompositeTransformStrategy:
    """
    创建默认的转换流水线

    包含完整的特征转换功能，适用于大多数场景。

    Args:
        inplace: 是否在原始DataFrame上修改

    Returns:
        组合转换策略

    Example:
        >>> pipeline = create_default_transform_pipeline()
        >>> result_df = pipeline.transform(df)
    """
    return CompositeTransformStrategy(
        strategies=[
            PriceChangeTransformStrategy(),
            TimeFeatureStrategy(),
            StatisticalFeatureStrategy(),
        ],
        inplace=inplace
    )


def create_ml_transform_pipeline(
    normalize_method: str = 'robust',
    inplace: bool = False
) -> CompositeTransformStrategy:
    """
    创建机器学习专用转换流水线

    包含价格转换、时间特征和标准化。

    Args:
        normalize_method: 标准化方法 ('standard', 'robust', 'minmax')
        inplace: 是否在原始DataFrame上修改

    Returns:
        组合转换策略
    """
    return CompositeTransformStrategy(
        strategies=[
            PriceChangeTransformStrategy(),
            TimeFeatureStrategy(),
            NormalizationStrategy(config={'method': normalize_method}),
        ],
        inplace=inplace
    )


# ==================== 导出 ====================

__all__ = [
    # 异常类
    'TransformError',
    'InvalidDataError',
    'ScalerNotFoundError',
    # 基类
    'TransformStrategy',
    # 策略类
    'PriceChangeTransformStrategy',
    'NormalizationStrategy',
    'TimeFeatureStrategy',
    'StatisticalFeatureStrategy',
    'CompositeTransformStrategy',
    # 便捷函数
    'create_default_transform_pipeline',
    'create_ml_transform_pipeline',
    # 辅助函数
    'safe_divide',
    'merge_configs',
]
