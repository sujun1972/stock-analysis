"""
Alpha因子库（量化选股因子）
包含动量、反转、波动率、成交量等常用Alpha因子

重构版本特性:
- 模块化设计：不同类型的因子拆分为独立计算器
- 性能优化：缓存机制、向量化计算
- 统一日志：使用loguru替代print
- 完善的错误处理和类型提示
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Callable
from abc import ABC, abstractmethod
from functools import lru_cache
from loguru import logger


# ==================== 基础类和配置 ====================


class FactorConfig:
    """因子计算配置类"""

    # 默认周期配置
    DEFAULT_SHORT_PERIODS = [5, 10, 20]
    DEFAULT_MEDIUM_PERIODS = [20, 60]
    DEFAULT_LONG_PERIODS = [60, 120]

    # 列名映射
    PRICE_COLUMNS = ['open', 'high', 'low', 'close']
    VOLUME_COLUMNS = ['vol', 'volume']

    # 计算参数
    ANNUAL_TRADING_DAYS = 252
    EPSILON = 1e-8  # 防止除零


class BaseFactorCalculator(ABC):
    """因子计算器基类"""

    def __init__(self, df: pd.DataFrame, inplace: bool = False):
        """
        初始化因子计算器

        参数:
            df: 价格DataFrame
            inplace: 是否直接修改原DataFrame（False则返回副本）
        """
        self.df = df if inplace else df.copy()
        self._validate_dataframe()
        self._cache = {}

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
        """安全除法，避免除零"""
        return numerator / (denominator + FactorConfig.EPSILON)

    def _calculate_returns(self, price_col: str = 'close') -> pd.Series:
        """计算收益率（带缓存）"""
        if price_col not in self._cache:
            self._cache[price_col] = self.df[price_col].pct_change()
        return self._cache[price_col]

    def get_dataframe(self) -> pd.DataFrame:
        """获取结果DataFrame"""
        return self.df


# ==================== 动量因子计算器 ====================


class MomentumFactorCalculator(BaseFactorCalculator):
    """动量因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

    def add_momentum_factors(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加动量因子（价格动量）

        参数:
            periods: 周期列表，默认使用配置值
            price_col: 价格列名

        返回:
            添加动量因子的DataFrame
        """
        if periods is None:
            periods = FactorConfig.DEFAULT_SHORT_PERIODS + FactorConfig.DEFAULT_LONG_PERIODS

        logger.debug(f"计算动量因子，周期: {periods}")

        for period in periods:
            try:
                # 简单收益率动量
                self.df[f'MOM{period}'] = self.df[price_col].pct_change(period) * 100

                # 对数收益率动量
                self.df[f'MOM_LOG{period}'] = (
                    np.log(self.df[price_col] / self.df[price_col].shift(period)) * 100
                )

            except Exception as e:
                logger.error(f"计算动量因子 MOM{period} 失败: {e}")

        return self.df

    def add_relative_strength(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加相对强度因子（价格相对于均线的位置）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加相对强度因子的DataFrame
        """
        if periods is None:
            periods = FactorConfig.DEFAULT_MEDIUM_PERIODS

        logger.debug(f"计算相对强度因子，周期: {periods}")

        for period in periods:
            try:
                ma = self.df[price_col].rolling(window=period).mean()
                # 价格相对于均线的偏离度
                self.df[f'RS{period}'] = self._safe_divide(
                    self.df[price_col] - ma, ma
                ) * 100

            except Exception as e:
                logger.error(f"计算相对强度因子 RS{period} 失败: {e}")

        return self.df

    def add_acceleration(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加加速度因子（动量的变化率）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加加速度因子的DataFrame
        """
        if periods is None:
            periods = FactorConfig.DEFAULT_SHORT_PERIODS

        logger.debug(f"计算加速度因子，周期: {periods}")

        for period in periods:
            try:
                momentum = self.df[price_col].pct_change(period)
                # 动量的变化（加速度）
                self.df[f'ACC{period}'] = momentum - momentum.shift(period)

            except Exception as e:
                logger.error(f"计算加速度因子 ACC{period} 失败: {e}")

        return self.df

    def calculate_all(self) -> pd.DataFrame:
        """计算所有动量类因子"""
        self.add_momentum_factors()
        self.add_relative_strength()
        self.add_acceleration()
        return self.df


# ==================== 反转因子计算器 ====================


class ReversalFactorCalculator(BaseFactorCalculator):
    """反转因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

    def add_reversal_factors(
        self,
        short_periods: List[int] = None,
        long_periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加反转因子（短期反转效应）

        参数:
            short_periods: 短期周期列表
            long_periods: 长期周期列表
            price_col: 价格列名

        返回:
            添加反转因子的DataFrame
        """
        if short_periods is None:
            short_periods = [1, 3, 5]
        if long_periods is None:
            long_periods = FactorConfig.DEFAULT_MEDIUM_PERIODS

        logger.debug(f"计算反转因子，短期周期: {short_periods}, 长期周期: {long_periods}")

        # 短期反转（负向动量）
        for period in short_periods:
            try:
                self.df[f'REV{period}'] = -self.df[price_col].pct_change(period) * 100
            except Exception as e:
                logger.error(f"计算短期反转因子 REV{period} 失败: {e}")

        # 长期反转（均值回归）
        for period in long_periods:
            try:
                ma = self.df[price_col].rolling(window=period).mean()
                std = self.df[price_col].rolling(window=period).std()
                # Z-score（标准化偏离度）
                self.df[f'ZSCORE{period}'] = self._safe_divide(ma - self.df[price_col], std)
            except Exception as e:
                logger.error(f"计算Z-score因子 ZSCORE{period} 失败: {e}")

        return self.df

    def add_overnight_reversal(self) -> pd.DataFrame:
        """
        添加隔夜反转因子（开盘价相对于前收盘的跳空）

        返回:
            添加隔夜反转因子的DataFrame
        """
        if 'open' not in self.df.columns:
            logger.warning("找不到'open'列，跳过隔夜反转因子")
            return self.df

        logger.debug("计算隔夜反转因子")

        try:
            # 隔夜收益率（开盘-前收盘）
            self.df['OVERNIGHT_RET'] = self._safe_divide(
                self.df['open'] - self.df['close'].shift(1),
                self.df['close'].shift(1)
            ) * 100

            # 日内收益率（收盘-开盘）
            self.df['INTRADAY_RET'] = self._safe_divide(
                self.df['close'] - self.df['open'],
                self.df['open']
            ) * 100

            # 隔夜反转强度（隔夜收益的负值）
            self.df['OVERNIGHT_REV'] = -self.df['OVERNIGHT_RET']

        except Exception as e:
            logger.error(f"计算隔夜反转因子失败: {e}")

        return self.df

    def calculate_all(self) -> pd.DataFrame:
        """计算所有反转类因子"""
        self.add_reversal_factors()
        self.add_overnight_reversal()
        return self.df


# ==================== 波动率因子计算器 ====================


class VolatilityFactorCalculator(BaseFactorCalculator):
    """波动率因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

    def add_volatility_factors(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加波动率因子

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加波动率因子的DataFrame
        """
        if periods is None:
            periods = FactorConfig.DEFAULT_SHORT_PERIODS + [60]

        logger.debug(f"计算波动率因子，周期: {periods}")

        returns = self._calculate_returns(price_col)

        for period in periods:
            try:
                # 历史波动率（年化）
                self.df[f'VOLATILITY{period}'] = (
                    returns.rolling(window=period).std() *
                    np.sqrt(FactorConfig.ANNUAL_TRADING_DAYS) * 100
                )

                # 波动率偏度（衡量极端波动）
                self.df[f'VOLSKEW{period}'] = returns.rolling(window=period).skew()

            except Exception as e:
                logger.error(f"计算波动率因子 VOLATILITY{period} 失败: {e}")

        return self.df

    def add_high_low_volatility(
        self,
        periods: List[int] = None
    ) -> pd.DataFrame:
        """
        添加高低价波动率因子（Parkinson波动率）

        参数:
            periods: 周期列表

        返回:
            添加高低价波动率因子的DataFrame
        """
        if 'high' not in self.df.columns or 'low' not in self.df.columns:
            logger.warning("找不到'high'或'low'列，跳过高低价波动率因子")
            return self.df

        if periods is None:
            periods = [10, 20]

        logger.debug(f"计算Parkinson波动率因子，周期: {periods}")

        for period in periods:
            try:
                # Parkinson波动率（基于高低价）
                hl_ratio = np.log(self._safe_divide(self.df['high'], self.df['low'])) ** 2
                self.df[f'PARKINSON_VOL{period}'] = (
                    np.sqrt(hl_ratio.rolling(window=period).mean() / (4 * np.log(2))) *
                    np.sqrt(FactorConfig.ANNUAL_TRADING_DAYS) * 100
                )

            except Exception as e:
                logger.error(f"计算Parkinson波动率 PARKINSON_VOL{period} 失败: {e}")

        return self.df

    def calculate_all(self) -> pd.DataFrame:
        """计算所有波动率类因子"""
        self.add_volatility_factors()
        self.add_high_low_volatility()
        return self.df


# ==================== 成交量因子计算器 ====================


class VolumeFactorCalculator(BaseFactorCalculator):
    """成交量因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

        vol_col = self._get_volume_column()
        if vol_col is None:
            logger.warning("找不到成交量列，部分功能将不可用")

    def add_volume_factors(
        self,
        periods: List[int] = None,
        volume_col: str = None
    ) -> pd.DataFrame:
        """
        添加成交量因子

        参数:
            periods: 周期列表
            volume_col: 成交量列名（自动检测）

        返回:
            添加成交量因子的DataFrame
        """
        if volume_col is None:
            volume_col = self._get_volume_column()

        if volume_col is None or volume_col not in self.df.columns:
            logger.warning(f"找不到成交量列'{volume_col}'，跳过成交量因子")
            return self.df

        if periods is None:
            periods = FactorConfig.DEFAULT_SHORT_PERIODS

        logger.debug(f"计算成交量因子，周期: {periods}")

        for period in periods:
            try:
                # 成交量变化率
                self.df[f'VOLUME_CHG{period}'] = (
                    self.df[volume_col].pct_change(period) * 100
                )

                # 成交量相对强度
                vol_ma = self.df[volume_col].rolling(window=period).mean()
                self.df[f'VOLUME_RATIO{period}'] = self._safe_divide(
                    self.df[volume_col], vol_ma
                )

                # 成交量标准化（Z-score）
                vol_std = self.df[volume_col].rolling(window=period).std()
                self.df[f'VOLUME_ZSCORE{period}'] = self._safe_divide(
                    self.df[volume_col] - vol_ma, vol_std
                )

            except Exception as e:
                logger.error(f"计算成交量因子 VOLUME{period} 失败: {e}")

        return self.df

    def add_price_volume_correlation(
        self,
        periods: List[int] = None,
        price_col: str = 'close',
        volume_col: str = None
    ) -> pd.DataFrame:
        """
        添加价量相关性因子

        参数:
            periods: 周期列表
            price_col: 价格列名
            volume_col: 成交量列名

        返回:
            添加价量相关性因子的DataFrame
        """
        if volume_col is None:
            volume_col = self._get_volume_column()

        if volume_col is None or volume_col not in self.df.columns:
            logger.warning(f"找不到成交量列'{volume_col}'，跳过价量相关性因子")
            return self.df

        if periods is None:
            periods = FactorConfig.DEFAULT_MEDIUM_PERIODS

        logger.debug(f"计算价量相关性因子，周期: {periods}")

        price_ret = self._calculate_returns(price_col)

        for period in periods:
            try:
                # 价格收益率与成交量的相关系数
                self.df[f'PV_CORR{period}'] = (
                    price_ret.rolling(window=period).corr(self.df[volume_col])
                )

            except Exception as e:
                logger.error(f"计算价量相关性 PV_CORR{period} 失败: {e}")

        return self.df

    def calculate_all(self) -> pd.DataFrame:
        """计算所有成交量类因子"""
        self.add_volume_factors()
        self.add_price_volume_correlation()
        return self.df


# ==================== 趋势强度因子计算器 ====================


class TrendFactorCalculator(BaseFactorCalculator):
    """趋势强度因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

    def add_trend_strength(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加趋势强度因子（基于线性回归）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加趋势强度因子的DataFrame
        """
        if periods is None:
            periods = FactorConfig.DEFAULT_MEDIUM_PERIODS

        logger.debug(f"计算趋势强度因子，周期: {periods}")

        for period in periods:
            try:
                # 线性回归斜率
                self.df[f'TREND{period}'] = (
                    self.df[price_col].rolling(window=period).apply(
                        lambda x: np.polyfit(np.arange(len(x)), x, 1)[0]
                        if len(x) == period else np.nan,
                        raw=True
                    )
                )

                # R-squared（趋势拟合度）
                self.df[f'TREND_R2_{period}'] = (
                    self.df[price_col].rolling(window=period).apply(
                        self._calc_r2_factory(period),
                        raw=True
                    )
                )

            except Exception as e:
                logger.error(f"计算趋势强度因子 TREND{period} 失败: {e}")

        return self.df

    @staticmethod
    def _calc_r2_factory(period: int) -> Callable:
        """R-squared计算工厂函数"""
        def calc_r2(prices):
            if len(prices) != period:
                return np.nan
            try:
                x = np.arange(len(prices))
                slope, intercept = np.polyfit(x, prices, 1)
                y_pred = slope * x + intercept
                ss_res = np.sum((prices - y_pred) ** 2)
                ss_tot = np.sum((prices - np.mean(prices)) ** 2)
                return 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            except:
                return np.nan
        return calc_r2

    def add_breakout_factors(
        self,
        periods: List[int] = None,
        price_col: str = 'close'
    ) -> pd.DataFrame:
        """
        添加突破因子（新高新低）

        参数:
            periods: 周期列表
            price_col: 价格列名

        返回:
            添加突破因子的DataFrame
        """
        if periods is None:
            periods = FactorConfig.DEFAULT_MEDIUM_PERIODS

        logger.debug(f"计算突破因子，周期: {periods}")

        for period in periods:
            try:
                # 创新高因子（当前价相对于N日最高价）
                high_max = self.df[price_col].rolling(window=period).max()
                self.df[f'BREAKOUT_HIGH{period}'] = self._safe_divide(
                    self.df[price_col] - high_max, high_max
                ) * 100

                # 创新低因子（当前价相对于N日最低价）
                low_min = self.df[price_col].rolling(window=period).min()
                self.df[f'BREAKOUT_LOW{period}'] = self._safe_divide(
                    self.df[price_col] - low_min, low_min
                ) * 100

                # 价格在区间中的位置（0-100）
                self.df[f'PRICE_POSITION{period}'] = self._safe_divide(
                    self.df[price_col] - low_min, high_max - low_min
                ) * 100

            except Exception as e:
                logger.error(f"计算突破因子 BREAKOUT{period} 失败: {e}")

        return self.df

    def calculate_all(self) -> pd.DataFrame:
        """计算所有趋势类因子"""
        self.add_trend_strength()
        self.add_breakout_factors()
        return self.df


# ==================== 流动性因子计算器 ====================


class LiquidityFactorCalculator(BaseFactorCalculator):
    """流动性因子计算器"""

    def _validate_dataframe(self):
        """验证必需的列"""
        if 'close' not in self.df.columns:
            raise ValueError("DataFrame缺少必需的列: close")

    def add_liquidity_factors(
        self,
        periods: List[int] = None,
        volume_col: str = None
    ) -> pd.DataFrame:
        """
        添加流动性因子（Amihud非流动性指标）

        参数:
            periods: 周期列表
            volume_col: 成交量列名

        返回:
            添加流动性因子的DataFrame
        """
        if volume_col is None:
            volume_col = self._get_volume_column()

        if volume_col is None or volume_col not in self.df.columns:
            logger.warning(f"找不到成交量列'{volume_col}'，跳过流动性因子")
            return self.df

        if periods is None:
            periods = [20]

        logger.debug(f"计算流动性因子，周期: {periods}")

        # 日收益率绝对值
        returns = self.df['close'].pct_change().abs()

        for period in periods:
            try:
                # Amihud非流动性 = |收益率| / 成交量
                amihud = self._safe_divide(returns, self.df[volume_col])
                self.df[f'ILLIQUIDITY{period}'] = (
                    amihud.rolling(window=period).mean() * 1e6  # 放大倍数
                )

            except Exception as e:
                logger.error(f"计算流动性因子 ILLIQUIDITY{period} 失败: {e}")

        return self.df

    def calculate_all(self) -> pd.DataFrame:
        """计算所有流动性类因子"""
        self.add_liquidity_factors()
        return self.df


# ==================== 主要的Alpha因子类 ====================


class AlphaFactors:
    """Alpha因子主类 - 整合所有类型的因子计算器"""

    def __init__(self, df: pd.DataFrame, inplace: bool = False):
        """
        初始化Alpha因子计算器

        参数:
            df: 价格DataFrame，需包含 close 列，可选包含 open, high, low, volume/vol 列
            inplace: 是否直接修改原DataFrame
        """
        self.df = df if inplace else df.copy()
        self._validate_dataframe()

        # 初始化各类因子计算器
        self.momentum = MomentumFactorCalculator(self.df, inplace=True)
        self.reversal = ReversalFactorCalculator(self.df, inplace=True)
        self.volatility = VolatilityFactorCalculator(self.df, inplace=True)
        self.volume = VolumeFactorCalculator(self.df, inplace=True)
        self.trend = TrendFactorCalculator(self.df, inplace=True)
        self.liquidity = LiquidityFactorCalculator(self.df, inplace=True)

    def _validate_dataframe(self):
        """验证DataFrame格式"""
        required_cols = ['close']
        missing_cols = [col for col in required_cols if col not in self.df.columns]

        if missing_cols:
            raise ValueError(f"DataFrame缺少必需的列: {missing_cols}")

    # ==================== 便捷方法：直接调用各计算器 ====================

    def add_momentum_factors(self, **kwargs) -> pd.DataFrame:
        """添加动量因子"""
        return self.momentum.add_momentum_factors(**kwargs)

    def add_relative_strength(self, **kwargs) -> pd.DataFrame:
        """添加相对强度因子"""
        return self.momentum.add_relative_strength(**kwargs)

    def add_acceleration(self, **kwargs) -> pd.DataFrame:
        """添加加速度因子"""
        return self.momentum.add_acceleration(**kwargs)

    def add_reversal_factors(self, **kwargs) -> pd.DataFrame:
        """添加反转因子"""
        return self.reversal.add_reversal_factors(**kwargs)

    def add_overnight_reversal(self) -> pd.DataFrame:
        """添加隔夜反转因子"""
        return self.reversal.add_overnight_reversal()

    def add_volatility_factors(self, **kwargs) -> pd.DataFrame:
        """添加波动率因子"""
        return self.volatility.add_volatility_factors(**kwargs)

    def add_high_low_volatility(self, **kwargs) -> pd.DataFrame:
        """添加高低价波动率因子"""
        return self.volatility.add_high_low_volatility(**kwargs)

    def add_volume_factors(self, **kwargs) -> pd.DataFrame:
        """添加成交量因子"""
        return self.volume.add_volume_factors(**kwargs)

    def add_price_volume_correlation(self, **kwargs) -> pd.DataFrame:
        """添加价量相关性因子"""
        return self.volume.add_price_volume_correlation(**kwargs)

    def add_trend_strength(self, **kwargs) -> pd.DataFrame:
        """添加趋势强度因子"""
        return self.trend.add_trend_strength(**kwargs)

    def add_breakout_factors(self, **kwargs) -> pd.DataFrame:
        """添加突破因子"""
        return self.trend.add_breakout_factors(**kwargs)

    def add_liquidity_factors(self, **kwargs) -> pd.DataFrame:
        """添加流动性因子"""
        return self.liquidity.add_liquidity_factors(**kwargs)

    # ==================== 综合方法 ====================

    def add_all_alpha_factors(self) -> pd.DataFrame:
        """
        一键添加所有Alpha因子

        返回:
            添加所有Alpha因子的DataFrame
        """
        logger.info("开始计算所有Alpha因子...")

        try:
            # 动量类因子
            self.momentum.calculate_all()

            # 反转类因子
            self.reversal.calculate_all()

            # 波动率类因子
            self.volatility.calculate_all()

            # 成交量类因子
            self.volume.calculate_all()

            # 趋势类因子
            self.trend.calculate_all()

            # 流动性因子
            self.liquidity.calculate_all()

            factor_count = len(self.get_factor_names())
            logger.info(f"Alpha因子计算完成，共 {len(self.df.columns)} 列，因子数: {factor_count}")

        except Exception as e:
            logger.error(f"计算Alpha因子时发生错误: {e}")
            raise

        return self.df

    def get_factor_names(self) -> List[str]:
        """
        获取所有因子名称列表

        返回:
            因子名称列表
        """
        # 排除原始OHLCV列
        exclude_cols = {'open', 'high', 'low', 'close', 'vol', 'volume', 'amount'}
        return [col for col in self.df.columns if col not in exclude_cols]

    def get_dataframe(self) -> pd.DataFrame:
        """
        获取包含所有因子的DataFrame

        返回:
            包含所有因子的DataFrame
        """
        return self.df

    def get_factor_summary(self) -> Dict[str, int]:
        """
        获取因子分类统计

        返回:
            各类因子数量的字典
        """
        factor_names = self.get_factor_names()

        summary = {
            '动量类': sum(1 for f in factor_names if f.startswith(('MOM', 'RS', 'ACC'))),
            '反转类': sum(1 for f in factor_names if f.startswith(('REV', 'ZSCORE', 'OVERNIGHT'))),
            '波动率类': sum(1 for f in factor_names if 'VOL' in f or 'PARKINSON' in f),
            '成交量类': sum(1 for f in factor_names if f.startswith('VOLUME') or f.startswith('PV')),
            '趋势类': sum(1 for f in factor_names if f.startswith(('TREND', 'BREAKOUT', 'PRICE_POS'))),
            '流动性类': sum(1 for f in factor_names if f.startswith('ILLIQUIDITY')),
            '其他': 0
        }

        # 计算其他类别
        total_categorized = sum(summary.values())
        summary['其他'] = len(factor_names) - total_categorized

        return summary


# ==================== 便捷函数 ====================


def calculate_all_alpha_factors(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    便捷函数：一键计算所有Alpha因子

    参数:
        df: 价格DataFrame
        inplace: 是否直接修改原DataFrame

    返回:
        包含所有Alpha因子的DataFrame
    """
    af = AlphaFactors(df, inplace=inplace)
    return af.add_all_alpha_factors()


def calculate_momentum_factors(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    便捷函数：仅计算动量相关因子

    参数:
        df: 价格DataFrame
        inplace: 是否直接修改原DataFrame

    返回:
        包含动量因子的DataFrame
    """
    af = AlphaFactors(df, inplace=inplace)
    return af.momentum.calculate_all()


def calculate_reversal_factors(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    便捷函数：仅计算反转相关因子

    参数:
        df: 价格DataFrame
        inplace: 是否直接修改原DataFrame

    返回:
        包含反转因子的DataFrame
    """
    af = AlphaFactors(df, inplace=inplace)
    return af.reversal.calculate_all()


# ==================== 使用示例 ====================


if __name__ == "__main__":
    from loguru import logger

    # 配置日志
    logger.remove()
    logger.add(lambda msg: logger.info(msg, end=''), level="INFO")

    logger.info("Alpha因子模块测试\n")
    logger.info("=" * 60)

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

    logger.info("\n原始数据:")
    logger.info(test_df.head())
    logger.info(f"\n原始列数: {len(test_df.columns)}")

    # 计算Alpha因子
    logger.info("\n" + "=" * 60)
    af = AlphaFactors(test_df)
    result_df = af.add_all_alpha_factors()

    logger.info("\n添加Alpha因子后:")
    logger.info(result_df.head())
    logger.info(f"\n总列数: {len(result_df.columns)}")
    logger.info(f"因子列数: {len(af.get_factor_names())}")

    # 显示因子分类统计
    logger.info("\n因子分类统计:")
    summary = af.get_factor_summary()
    for category, count in summary.items():
        logger.info(f"  {category}: {count}")

    logger.info("\n所有因子列表:")
    for i, col in enumerate(af.get_factor_names(), 1):
        logger.info(f"  {i:2d}. {col}")

    logger.info("\n最近5天数据示例:")
    sample_cols = ['close', 'MOM20', 'REV5', 'VOLATILITY20', 'VOLUME_RATIO5', 'TREND20']
    available_cols = [col for col in sample_cols if col in result_df.columns]
    logger.info(result_df[available_cols].tail())

    logger.info("\n" + "=" * 60)
    logger.info("测试完成！")
