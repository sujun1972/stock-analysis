"""
数据清洗器 (DataCleaner)

负责数据清洗、NaN处理和异常值处理
"""

import pandas as pd
import numpy as np
from typing import Dict
from utils.logger import get_logger

logger = get_logger(__name__)


class DataCleaner:
    """
    数据清洗器

    职责：
    - 处理无穷值
    - 移除NaN值
    - 处理极端值（分位数截断）
    - 统计清洗过程中的数据变化
    """

    def __init__(self, verbose: bool = True):
        """
        初始化数据清洗器

        Args:
            verbose: 是否输出详细日志
        """
        self.verbose = verbose
        self.stats = {
            'raw_samples': 0,
            'after_inf_removal': 0,
            'after_nan_removal': 0,
            'after_target_removal': 0,
            'final_samples': 0,
            'removed_inf': 0,
            'removed_nan': 0,
            'removed_target_nan': 0
        }

    def clean(
        self,
        df: pd.DataFrame,
        target_name: str,
        clip_quantile_low: float = 0.01,
        clip_quantile_high: float = 0.99
    ) -> pd.DataFrame:
        """
        清洗数据

        Args:
            df: 待清洗的DataFrame
            target_name: 目标列名
            clip_quantile_low: 下截断分位数
            clip_quantile_high: 上截断分位数

        Returns:
            清洗后的DataFrame
        """
        self.stats['raw_samples'] = len(df)
        self._log(f"数据清洗...")
        self._log(f"  原始样本: {len(df)}")

        # 1. 处理无穷值
        df = self._handle_inf_values(df)

        # 2. 移除特征全为NaN的行
        df = self._remove_feature_nan(df, target_name)

        # 3. 移除目标标签为NaN的行
        df = self._remove_target_nan(df, target_name)

        # 4. 处理极端值
        df = self._clip_outliers(df, target_name, clip_quantile_low, clip_quantile_high)

        self.stats['final_samples'] = len(df)

        self._log(f"  最终样本: {len(df)} 条 (保留 {len(df)/self.stats['raw_samples']*100:.1f}%)")

        logger.info(f"数据清洗完成: {self.stats['raw_samples']} → {self.stats['final_samples']} 样本")

        return df

    def _handle_inf_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理无穷值（替换为NaN）"""
        before = len(df)
        df = df.replace([np.inf, -np.inf], np.nan)
        after = len(df)

        self.stats['after_inf_removal'] = after
        self.stats['removed_inf'] = before - after

        if self.stats['removed_inf'] > 0:
            self._log(f"  处理无穷值: {self.stats['removed_inf']} 处")

        return df

    def _remove_feature_nan(self, df: pd.DataFrame, target_name: str) -> pd.DataFrame:
        """移除特征全为NaN的行（通常是前期指标计算不足）"""
        before = len(df)
        feature_cols = [col for col in df.columns if col != target_name]
        df = df.dropna(subset=feature_cols)
        after = len(df)

        self.stats['after_nan_removal'] = after
        self.stats['removed_nan'] = before - after

        self._log(f"  移除特征NaN: {self.stats['removed_nan']} 条")

        return df

    def _remove_target_nan(self, df: pd.DataFrame, target_name: str) -> pd.DataFrame:
        """移除目标标签为NaN的行（最后N天无未来数据）"""
        before = len(df)
        df = df.dropna(subset=[target_name])
        after = len(df)

        self.stats['after_target_removal'] = after
        self.stats['removed_target_nan'] = before - after

        self._log(f"  移除目标NaN: {self.stats['removed_target_nan']} 条")

        return df

    def _clip_outliers(
        self,
        df: pd.DataFrame,
        target_name: str,
        clip_quantile_low: float,
        clip_quantile_high: float
    ) -> pd.DataFrame:
        """
        处理极端值（使用分位数截断）

        Args:
            df: DataFrame
            target_name: 目标列名（不进行截断）
            clip_quantile_low: 下截断分位数
            clip_quantile_high: 上截断分位数

        Returns:
            截断后的DataFrame
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        numeric_cols = [col for col in numeric_cols if col != target_name]

        clipped_count = 0
        for col in numeric_cols:
            q_low = df[col].quantile(clip_quantile_low)
            q_high = df[col].quantile(clip_quantile_high)

            # 统计被截断的值
            before = df[col].copy()
            df[col] = df[col].clip(lower=q_low, upper=q_high)
            clipped_count += ((before < q_low) | (before > q_high)).sum()

        if clipped_count > 0:
            self._log(f"  极端值截断: {clipped_count} 处 ({clip_quantile_low:.2%} ~ {clip_quantile_high:.2%})")

        return df

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()

    def print_stats(self):
        """打印统计信息"""
        self._log("\n清洗统计:")
        self._log(f"  原始样本: {self.stats['raw_samples']}")
        self._log(f"  移除无穷值: {self.stats['removed_inf']}")
        self._log(f"  移除特征NaN: {self.stats['removed_nan']}")
        self._log(f"  移除目标NaN: {self.stats['removed_target_nan']}")
        self._log(f"  最终样本: {self.stats['final_samples']}")
        self._log(f"  数据保留率: {self.stats['final_samples']/self.stats['raw_samples']*100:.1f}%")

    def _log(self, message: str):
        """输出日志"""
        if self.verbose:
            print(message)
