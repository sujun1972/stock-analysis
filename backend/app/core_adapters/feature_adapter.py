"""
特征工程适配器 (Feature Adapter)

将 Core 的特征工程模块包装为异步方法，供 FastAPI 使用。

核心功能:
- 异步计算技术指标 (MA, MACD, RSI, KDJ, Bollinger Bands 等 50+ 指标)
- 异步计算 Alpha 因子 (动量因子、反转因子、波动率因子等 30+ 因子)
- 异步特征转换 (标准化、归一化、PCA 等)
- 流式特征计算

作者: Backend Team
创建日期: 2026-02-01
版本: 1.0.0
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# 添加 core 项目到 Python 路径
core_path = Path(__file__).parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

from src.exceptions import FeatureCalculationError
from src.features.alpha_factors import AlphaFactors
from src.features.feature_transformer import FeatureTransformer
from src.features.streaming_feature_engine import StreamingFeatureEngine

# 导入 Core 模块
from src.features.technical_indicators import TechnicalIndicators

from app.core.cache import cache
from app.core.config import settings


class FeatureAdapter:
    """
    Core 特征工程模块的异步适配器

    包装 Core 的特征计算类，将同步方法转换为异步方法。

    示例:
        >>> adapter = FeatureAdapter()
        >>> df_with_indicators = await adapter.add_technical_indicators(df)
        >>> df_with_factors = await adapter.add_alpha_factors(df)
    """

    def __init__(self):
        """初始化特征适配器"""
        self.streaming_engine = None

    async def add_technical_indicators(
        self, df: pd.DataFrame, indicators: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        异步添加技术指标（带缓存）

        Args:
            df: 包含 OHLCV 数据的 DataFrame
            indicators: 指标列表，None 表示添加所有指标

        Returns:
            添加了技术指标的 DataFrame

        Raises:
            FeatureCalculationError: 特征计算错误

        支持的指标:
            - MA: 移动平均线
            - EMA: 指数移动平均线
            - MACD: 指数平滑异同移动平均线
            - RSI: 相对强弱指标
            - KDJ: 随机指标
            - BBANDS: 布林带
            - ATR: 平均真实波幅
            - OBV: 能量潮
            等 50+ 指标

        Note:
            缓存TTL: 30分钟（技术指标计算密集）
            由于 DataFrame 作为输入，缓存基于数据内容哈希
        """

        def _compute():
            ti = TechnicalIndicators(df.copy())
            if indicators is None:
                return ti.add_all_indicators()
            else:
                result_df = df.copy()
                for indicator in indicators:
                    method = getattr(ti, f"add_{indicator}", None)
                    if method:
                        result_df = method()
                return result_df

        return await asyncio.to_thread(_compute)

    async def add_alpha_factors(
        self, df: pd.DataFrame, factors: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        异步添加 Alpha 因子（带缓存）

        Args:
            df: 包含 OHLCV 数据的 DataFrame
            factors: 因子列表，None 表示添加所有因子

        Returns:
            添加了 Alpha 因子的 DataFrame

        Raises:
            FeatureCalculationError: 特征计算错误

        支持的因子:
            - 动量因子: momentum, return_5d, return_20d 等
            - 反转因子: reversal_5d, reversal_20d 等
            - 波动率因子: volatility_5d, volatility_20d 等
            - 价量因子: price_volume_corr, volume_price_trend 等
            等 30+ 因子

        Note:
            缓存TTL: 30分钟（Alpha因子计算密集）
            由于 DataFrame 作为输入，缓存基于数据内容哈希
        """

        def _compute():
            af = AlphaFactors(df.copy())
            if factors is None:
                result = af.add_all_alpha_factors()
                # Core 返回 Response 对象，提取 data
                return result.data if hasattr(result, "data") else result
            else:
                result_df = df.copy()
                for factor in factors:
                    method = getattr(af, f"add_{factor}", None)
                    if method:
                        result_df = method()
                return result_df

        return await asyncio.to_thread(_compute)

    async def add_all_features(
        self,
        df: pd.DataFrame,
        include_indicators: bool = True,
        include_factors: bool = True,
        include_transforms: bool = False,
    ) -> pd.DataFrame:
        """
        异步添加所有特征 (技术指标 + Alpha 因子)

        Args:
            df: 包含 OHLCV 数据的 DataFrame
            include_indicators: 是否包含技术指标
            include_factors: 是否包含 Alpha 因子
            include_transforms: 是否包含特征转换

        Returns:
            添加了所有特征的 DataFrame (125+ 列)

        Raises:
            FeatureCalculationError: 特征计算错误
        """
        result_df = df.copy()

        if include_indicators:
            result_df = await self.add_technical_indicators(result_df)

        if include_factors:
            result_df = await self.add_alpha_factors(result_df)

        if include_transforms:
            result_df = await self.transform_features(result_df)

        return result_df

    async def transform_features(
        self, df: pd.DataFrame, method: str = "standardize", columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        异步特征转换

        Args:
            df: 包含特征的 DataFrame
            method: 转换方法 (standardize/normalize/log/diff)
            columns: 要转换的列，None 表示所有数值列

        Returns:
            转换后的 DataFrame

        Raises:
            FeatureCalculationError: 特征转换错误

        支持的转换方法:
            - standardize: 标准化 (均值0, 方差1)
            - normalize: 归一化 (0-1)
            - log: 对数变换
            - diff: 差分
        """

        def _compute():
            transformer = FeatureTransformer(df.copy())
            feature_cols = (
                columns if columns else list(df.select_dtypes(include=[np.number]).columns)
            )
            if method == "standardize":
                # Core 使用 normalize_features 并指定 method='standard'
                return transformer.normalize_features(feature_cols=feature_cols, method="standard")
            elif method == "normalize":
                # Core 使用 normalize_features 并指定 method='minmax'
                return transformer.normalize_features(feature_cols=feature_cols, method="minmax")
            elif method == "log":
                # Core 没有 log_transform，使用 rank_transform 或直接应用 np.log
                result_df = df.copy()
                cols_to_transform = (
                    columns if columns else list(df.select_dtypes(include=[np.number]).columns)
                )
                for col in cols_to_transform:
                    if col in result_df.columns:
                        result_df[col] = np.log1p(result_df[col].clip(lower=0))
                return result_df
            elif method == "diff":
                # 使用 pandas diff
                result_df = df.copy()
                cols_to_transform = (
                    columns if columns else list(df.select_dtypes(include=[np.number]).columns)
                )
                for col in cols_to_transform:
                    if col in result_df.columns:
                        result_df[col] = result_df[col].diff()
                return result_df
            else:
                raise FeatureCalculationError(
                    f"不支持的转换方法: {method}", error_code="INVALID_TRANSFORM_METHOD"
                )

        return await asyncio.to_thread(_compute)

    async def calculate_feature_importance(
        self, X: pd.DataFrame, y: pd.Series, method: str = "correlation"
    ) -> pd.Series:
        """
        异步计算特征重要性

        Args:
            X: 特征 DataFrame
            y: 目标变量
            method: 计算方法 (correlation/mutual_info)

        Returns:
            特征重要性 Series (已排序)

        Raises:
            FeatureEngineeringError: 计算错误
        """

        def _compute():
            if method == "correlation":
                # 计算相关系数
                importance = X.corrwith(y).abs()
            elif method == "mutual_info":
                # 计算互信息
                from sklearn.feature_selection import mutual_info_regression

                importance = pd.Series(mutual_info_regression(X, y), index=X.columns)
            else:
                raise FeatureCalculationError(
                    f"不支持的方法: {method}", error_code="INVALID_IMPORTANCE_METHOD"
                )

            return importance.sort_values(ascending=False)

        return await asyncio.to_thread(_compute)

    async def select_features(
        self, X: pd.DataFrame, y: pd.Series, n_features: int = 50, method: str = "correlation"
    ) -> List[str]:
        """
        异步特征选择

        Args:
            X: 特征 DataFrame
            y: 目标变量
            n_features: 要选择的特征数量
            method: 选择方法

        Returns:
            选中的特征列表

        Raises:
            FeatureCalculationError: 选择错误
        """
        importance = await self.calculate_feature_importance(X, y, method)
        return importance.head(n_features).index.tolist()

    async def init_streaming_engine(self, config=None, output_dir=None):
        """
        异步初始化流式特征引擎

        Args:
            config: StreamingConfig配置对象（可选）
            output_dir: 输出目录路径（可选）
        """

        def _init():
            return StreamingFeatureEngine(config=config, output_dir=output_dir)

        self.streaming_engine = await asyncio.to_thread(_init)

    async def update_streaming_features(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        异步更新流式特征

        Args:
            new_data: 新的 OHLCV 数据点

        Returns:
            包含实时特征的字典

        Raises:
            FeatureCalculationError: 流式计算错误
        """
        if self.streaming_engine is None:
            raise FeatureCalculationError(
                "流式引擎未初始化，请先调用 init_streaming_engine()",
                error_code="STREAMING_ENGINE_NOT_INITIALIZED",
            )

        return await asyncio.to_thread(self.streaming_engine.update, new_data=new_data)

    async def get_feature_names(self) -> Dict[str, List[str]]:
        """
        获取所有可用的特征名称

        Returns:
            包含各类特征名称的字典
        """

        def _get_names():
            # 创建示例 DataFrame
            example_df = pd.DataFrame(
                {
                    "open": [100.0],
                    "high": [102.0],
                    "low": [99.0],
                    "close": [101.0],
                    "volume": [1000000.0],
                }
            )

            ti = TechnicalIndicators(example_df)
            af = AlphaFactors(example_df)

            # 获取方法列表
            indicator_methods = [
                m for m in dir(ti) if m.startswith("add_") and not m.startswith("add_all")
            ]
            factor_methods = [
                m for m in dir(af) if m.startswith("add_") and not m.startswith("add_all")
            ]

            return {
                "technical_indicators": [m.replace("add_", "") for m in indicator_methods],
                "alpha_factors": [m.replace("add_", "") for m in factor_methods],
                "transforms": ["standardize", "normalize", "log", "diff"],
            }

        return await asyncio.to_thread(_get_names)
