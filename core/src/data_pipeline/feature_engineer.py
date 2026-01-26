"""
特征工程器 (FeatureEngineer)

负责计算技术指标、Alpha因子和特征转换
"""

import pandas as pd
import numpy as np
from typing import List, Optional
from src.features.technical_indicators import TechnicalIndicators
from src.features.alpha_factors import AlphaFactors
from src.features.feature_transformer import FeatureTransformer
from src.exceptions import FeatureComputationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureEngineer:
    """
    特征工程器

    职责：
    - 计算技术指标
    - 计算Alpha因子
    - 特征转换（多时间尺度、OHLC、时间特征）
    - 特征去价格化
    - 创建目标标签
    """

    def __init__(self, verbose: bool = True):
        """
        初始化特征工程器

        Args:
            verbose: 是否输出详细日志
        """
        self.verbose = verbose
        self.feature_names = []

    def compute_all_features(
        self,
        df: pd.DataFrame,
        target_period: int
    ) -> pd.DataFrame:
        """
        计算所有特征

        Args:
            df: 原始数据 DataFrame
            target_period: 预测周期（天数）

        Returns:
            包含所有特征和目标标签的 DataFrame

        Raises:
            FeatureComputationError: 特征计算失败
        """
        try:
            # 1. 技术指标
            self._log("计算技术指标...")
            df = self._compute_technical_indicators(df)

            # 2. Alpha因子
            self._log("计算Alpha因子...")
            df = self._compute_alpha_factors(df)

            # 3. 特征转换
            self._log("特征转换...")
            df = self._apply_feature_transformation(df)

            # 4. 特征去价格化
            self._log("特征去价格化...")
            df = self._deprice_features(df)

            # 5. 创建目标标签
            target_name = f'target_{target_period}d_return'
            self._log(f"创建目标标签: {target_name}")
            df = self._create_target(df, target_period, target_name)

            logger.info(f"特征工程完成: {len(df.columns)} 列，{len(df)} 行")

            return df

        except Exception as e:
            logger.error(f"特征计算失败: {e}")
            raise FeatureComputationError(f"特征计算失败: {e}")

    def _compute_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        ti = TechnicalIndicators(df)

        # 添加常用技术指标
        ti.add_ma([5, 10, 20, 60, 120, 250])
        ti.add_ema([12, 26, 50])
        ti.add_rsi([6, 12, 24])
        ti.add_macd()
        ti.add_kdj()
        ti.add_bollinger_bands()
        ti.add_atr([14, 28])
        ti.add_obv()
        ti.add_cci([14, 28])

        df = ti.get_dataframe()

        # 统计技术指标数量
        technical_features = [
            col for col in df.columns
            if col not in ['open', 'high', 'low', 'close', 'volume', 'amount']
        ]
        self._log(f"  技术指标: {len(technical_features)} 个")

        return df

    def _compute_alpha_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算Alpha因子"""
        af = AlphaFactors(df)

        # 添加常用Alpha因子
        af.add_momentum_factors([5, 10, 20, 60, 120])
        af.add_reversal_factors([1, 3, 5], [20, 60])
        af.add_volatility_factors([5, 10, 20, 60])
        af.add_volume_factors([5, 10, 20])
        af.add_trend_strength([20, 60])

        df = af.get_dataframe()

        alpha_features = af.get_factor_names()
        self._log(f"  Alpha因子: {len(alpha_features)} 个")

        return df

    def _apply_feature_transformation(self, df: pd.DataFrame) -> pd.DataFrame:
        """应用特征转换"""
        ft = FeatureTransformer(df)

        # 多时间尺度收益率
        ft.create_multi_timeframe_returns([1, 3, 5, 10, 20])

        # OHLC特征
        ft.create_ohlc_features()

        # 时间特征
        ft.add_time_features()

        df = ft.get_dataframe()

        self._log(f"  转换特征: 时间尺度收益率、OHLC、时间特征")

        return df

    def _deprice_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        特征去价格化：将绝对价格特征转换为相对比例
        防止数据泄露，确保模型学习的是价格关系而非绝对价格
        """
        current_close = df['close']
        features_to_drop = []

        # MA类指标 → 价格偏离度比例
        for period in [5, 10, 20, 60, 120, 250]:
            ma_col = f'MA{period}'
            if ma_col in df.columns:
                df[f'CLOSE_TO_MA{period}_RATIO'] = (current_close / df[ma_col] - 1) * 100
                features_to_drop.append(ma_col)

        # EMA类指标 → 价格偏离度比例
        for period in [12, 26, 50]:
            ema_col = f'EMA{period}'
            if ema_col in df.columns:
                df[f'CLOSE_TO_EMA{period}_RATIO'] = (current_close / df[ema_col] - 1) * 100
                features_to_drop.append(ema_col)

        # BOLL类指标 → 价格偏离度比例
        for comp in ['UPPER', 'MIDDLE', 'LOWER']:
            boll_col = f'BOLL_{comp}'
            if boll_col in df.columns:
                df[f'CLOSE_TO_BOLL_{comp}_RATIO'] = (current_close / df[boll_col] - 1) * 100
                features_to_drop.append(boll_col)

        # ATR类指标 → 相对波动率百分比
        for period in [14, 28]:
            atr_col = f'ATR{period}'
            atr_pct_col = f'ATR{period}_PCT'
            if atr_col in df.columns:
                if atr_pct_col not in df.columns:
                    df[atr_pct_col] = (df[atr_col] / current_close) * 100
                features_to_drop.append(atr_col)

        # 删除绝对价格特征
        df = df.drop(columns=[col for col in features_to_drop if col in df.columns])
        self._log(f"    去价格化: 转换 {len(features_to_drop)} 个特征")

        return df

    def _create_target(
        self,
        df: pd.DataFrame,
        target_period: int,
        target_name: str
    ) -> pd.DataFrame:
        """
        创建目标标签（未来N日收益率）

        Args:
            df: DataFrame
            target_period: 预测周期（天数）
            target_name: 目标列名

        Returns:
            包含目标标签的DataFrame

        Note:
            使用正确的前瞻计算避免数据泄露：
            target[t] = (close[t+N] / close[t] - 1) * 100
            其中 shift(-N) 获取未来N天的价格，确保时间对齐正确
        """
        # 计算未来N日收益率（正确的前瞻计算）
        df[target_name] = (df['close'].shift(-target_period) / df['close'] - 1) * 100

        # 统计
        valid_targets = df[target_name].notna().sum()
        self._log(f"  目标标签: {target_name}")
        self._log(f"  有效样本: {valid_targets} / {len(df)}")
        self._log(f"  目标均值: {df[target_name].mean():.4f}%")
        self._log(f"  目标标准差: {df[target_name].std():.4f}%")

        return df

    def _log(self, message: str):
        """输出日志"""
        if self.verbose:
            logger.info(message)
