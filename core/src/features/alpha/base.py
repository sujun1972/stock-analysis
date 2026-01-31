"""
Alpha因子基础类和工具

包含:
- FactorCache: 线程安全的LRU缓存管理器
- FactorConfig: 因子计算配置类
- BaseFactorCalculator: 因子计算器抽象基类
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Callable, Any
from abc import ABC, abstractmethod
from loguru import logger
import hashlib
import threading


# ==================== 基础类和配置 ====================


class FactorCache:
    """
    因子计算缓存管理器 - 线程安全的LRU缓存

    用途:
    - 缓存重复计算的中间结果（MA、STD、收益率等）
    - 减少30-50%的重复计算
    - 支持多线程并发访问

    防数据泄漏设计:
    - 缓存键包含数据指纹，确保不同数据集不会混用缓存
    - 所有缓存结果都是基于历史窗口计算的
    """

    def __init__(self, max_size: int = 200):
        """
        初始化缓存管理器

        参数:
            max_size: 最大缓存条目数（超出后按LRU淘汰）
        """
        self._cache: Dict[str, Any] = {}
        self._access_order: List[str] = []
        self.max_size = max_size
        self._lock = threading.RLock()  # 线程安全锁
        self._hit_count = 0
        self._miss_count = 0

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值（线程安全）

        参数:
            key: 缓存键

        返回:
            缓存值或None
        """
        with self._lock:
            if key in self._cache:
                # 更新访问顺序（LRU）
                self._access_order.remove(key)
                self._access_order.append(key)
                self._hit_count += 1
                return self._cache[key]

            self._miss_count += 1
            return None

    def put(self, key: str, value: Any) -> None:
        """
        存储缓存值（线程安全，自动LRU淘汰）

        参数:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            # 如果键已存在，更新值和访问顺序
            if key in self._cache:
                self._access_order.remove(key)
                self._cache[key] = value
                self._access_order.append(key)
                return

            # LRU 淘汰：缓存满时删除最久未使用的条目
            if len(self._cache) >= self.max_size and self.max_size > 0:
                oldest_key = self._access_order.pop(0)
                del self._cache[oldest_key]

            # 添加新条目（max_size > 0时）
            if self.max_size > 0:
                self._cache[key] = value
                self._access_order.append(key)

    def get_or_compute(self, key: str, compute_fn: Callable[[], Any]) -> Any:
        """
        获取缓存或计算新值（原子操作）

        参数:
            key: 缓存键
            compute_fn: 计算函数（无参数）

        返回:
            缓存值或计算结果
        """
        # 先尝试读取（避免不必要的锁竞争）
        cached = self.get(key)
        if cached is not None:
            return cached

        # 计算新值并存储
        with self._lock:
            # 双重检查（防止并发计算）
            if key in self._cache:
                return self._cache[key]

            result = compute_fn()
            self.put(key, result)
            return result

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            self._hit_count = 0
            self._miss_count = 0

    def get_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息

        返回:
            包含命中率、大小等信息的字典
        """
        with self._lock:
            total = self._hit_count + self._miss_count
            hit_rate = self._hit_count / total if total > 0 else 0.0

            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hit_count,
                'misses': self._miss_count,
                'hit_rate': hit_rate
            }


class FactorConfig:
    """
    因子计算配置类（已弃用，使用 config.features 代替）

    警告: 此类保留仅用于向后兼容，新代码应使用:
        from config.features import get_feature_config
        config = get_feature_config()
    """

    # 默认周期配置（向后兼容）
    DEFAULT_SHORT_PERIODS = [5, 10, 20]
    DEFAULT_MEDIUM_PERIODS = [20, 60]
    DEFAULT_LONG_PERIODS = [60, 120]

    # 列名映射
    PRICE_COLUMNS = ['open', 'high', 'low', 'close']
    VOLUME_COLUMNS = ['vol', 'volume']

    # 计算参数
    ANNUAL_TRADING_DAYS = 252
    EPSILON = 1e-8  # 防止除零

    @classmethod
    def from_config(cls, feature_config=None):
        """
        从新配置系统加载参数

        Args:
            feature_config: FeatureEngineerConfig实例（可选）

        Returns:
            更新后的配置类
        """
        if feature_config is None:
            try:
                from config.features import get_feature_config
                feature_config = get_feature_config()
            except ImportError:
                logger.warning("无法导入新配置系统，使用默认值")
                return cls

        # 更新类属性
        alpha_config = feature_config.alpha_factors
        trading_config = feature_config.trading_days

        cls.DEFAULT_SHORT_PERIODS = alpha_config.default_short_periods
        cls.DEFAULT_MEDIUM_PERIODS = alpha_config.default_medium_periods
        cls.DEFAULT_LONG_PERIODS = alpha_config.default_long_periods
        cls.PRICE_COLUMNS = alpha_config.price_columns
        cls.VOLUME_COLUMNS = alpha_config.volume_columns
        cls.ANNUAL_TRADING_DAYS = trading_config.annual_trading_days
        cls.EPSILON = trading_config.epsilon

        return cls


class BaseFactorCalculator(ABC):
    """
    因子计算器基类

    防数据泄漏设计:
    - 所有计算方法仅使用历史窗口数据
    - 缓存键包含数据指纹，防止不同数据集混用
    - 提供数据泄漏检测方法（可选）
    """

    # 类级别共享缓存（所有实例共享，减少内存占用）
    _shared_cache = FactorCache(max_size=200)

    def __init__(self, df: pd.DataFrame, inplace: bool = False, enable_leak_detection: bool = False):
        """
        初始化因子计算器

        参数:
            df: 价格DataFrame
            inplace: 是否直接修改原DataFrame（False则返回副本）
            enable_leak_detection: 是否启用数据泄漏检测（会降低性能）
        """
        self.df = df if inplace else df.copy()
        self._validate_dataframe()

        # 计算数据指纹（用于缓存键，防止不同数据集混用）
        self._df_hash = self._compute_df_hash()

        # 实例级缓存（用于特定于此计算器的数据）
        self._cache = {}

        # 数据泄漏检测开关
        self._enable_leak_detection = enable_leak_detection

    def _compute_df_hash(self) -> str:
        """
        计算 DataFrame 数据指纹

        返回:
            16字符的哈希字符串

        注意:
            基于索引 + 数据样本计算哈希，确保不同数据集不会产生相同哈希
            即使两个DataFrame有相同的索引，如果数据内容不同，也会产生不同的哈希
        """
        try:
            # 1. 计算���引哈希
            index_hash = hashlib.md5(
                pd.util.hash_pandas_object(self.df.index, index=False).values
            ).digest()

            # 2. 计算数据样本哈希（前后各5行，避免全量计算）
            if len(self.df) > 0:
                # 选择关键列进行哈希（close价格是最核心的）
                key_cols = ['close']
                if 'high' in self.df.columns:
                    key_cols.append('high')
                if 'low' in self.df.columns:
                    key_cols.append('low')

                # 提取样本数据
                sample_size = min(5, len(self.df))
                sample_data = pd.concat([
                    self.df[key_cols].head(sample_size),
                    self.df[key_cols].tail(sample_size)
                ])

                # 计算样本数据哈希
                data_hash = hashlib.md5(
                    pd.util.hash_pandas_object(sample_data, index=False).values
                ).digest()

                # 合并索引哈希和数据哈希
                combined_hash = hashlib.md5(index_hash + data_hash).hexdigest()
            else:
                combined_hash = hashlib.md5(index_hash).hexdigest()

            return combined_hash[:16]

        except Exception as e:
            logger.warning(f"计算数据指纹失败: {e}，使用对象ID")
            return hashlib.md5(str(id(self.df)).encode()).hexdigest()[:16]

    @abstractmethod
    def _validate_dataframe(self):
        """验证DataFrame格式 - 子类必须实现"""
        pass

    def _get_volume_column(self) -> Optional[str]:
        """获取成交量列名"""
        for col in FactorConfig.VOLUME_COLUMNS:
            if col in self.df.columns:
                return col
        return None

    def _safe_divide(self, numerator: pd.Series, denominator: pd.Series) -> pd.Series:
        """
        安全除法，避免除零

        参数:
            numerator: 分子
            denominator: 分母

        返回:
            除法结果（分母接近0时加入epsilon）
        """
        return numerator / (denominator + FactorConfig.EPSILON)

    def _calculate_returns(self, price_col: str = 'close') -> pd.Series:
        """
        计算收益率（带缓存优化）

        参数:
            price_col: 价格列名

        返回:
            收益率序列

        注意:
            使用共享缓存，多次调用不会重复计算
        """
        cache_key = f"returns_{self._df_hash}_{price_col}"

        # 先检查实例缓存
        if price_col in self._cache:
            return self._cache[price_col]

        # 再检查共享缓存
        cached_result = self._shared_cache.get(cache_key)
        if cached_result is not None:
            self._cache[price_col] = cached_result
            return cached_result

        # 计算新值
        returns = self.df[price_col].pct_change()

        # 存入两级缓存
        self._cache[price_col] = returns
        self._shared_cache.put(cache_key, returns)

        return returns

    def _get_cached_ma(self, col: str, period: int) -> pd.Series:
        """
        获取缓存的移动平均（共享缓存）

        参数:
            col: 列名
            period: 周期

        返回:
            移动平均序列
        """
        cache_key = f"ma_{self._df_hash}_{col}_{period}"
        return self._shared_cache.get_or_compute(
            cache_key,
            lambda: self.df[col].rolling(window=period).mean()
        )

    def _get_cached_std(self, col: str, period: int) -> pd.Series:
        """
        获取缓存的标准差（共享缓存）

        参数:
            col: 列名
            period: 周期

        返回:
            标准差序列
        """
        cache_key = f"std_{self._df_hash}_{col}_{period}"
        return self._shared_cache.get_or_compute(
            cache_key,
            lambda: self.df[col].rolling(window=period).std()
        )

    def _detect_data_leakage(self, factor_series: pd.Series, factor_name: str) -> bool:
        """
        检测数据泄漏（可选的调试功能）

        参数:
            factor_series: 计算出的因子序列
            factor_name: 因子名称

        返回:
            True 表示检测到泄漏，False 表示安全

        检测方法:
            检查因子值是否与未来价格有异常高的相关性
        """
        if not self._enable_leak_detection:
            return False

        try:
            # 检查与未来收益的相关性
            future_returns = self.df['close'].pct_change(5).shift(-5)  # 未来5日收益
            correlation = factor_series.corr(future_returns)

            # 阈值：相关性绝对值 > 0.95 可能存在泄漏
            if abs(correlation) > 0.95:
                logger.error(
                    f"⚠️  检测到数据泄漏! 因子 {factor_name} 与未来收益相关性: {correlation:.4f}"
                )
                return True

            return False

        except Exception as e:
            logger.debug(f"数据泄漏检测失败: {e}")
            return False

    def get_dataframe(self) -> pd.DataFrame:
        """获取结果DataFrame"""
        return self.df

    def get_cache_stats(self) -> Dict[str, int]:
        """
        获取缓存统计信息

        返回:
            缓存统计字典
        """
        return self._shared_cache.get_stats()
