"""
数据分割器 (DataSplitter)

负责时间序列分割、特征缩放和样本平衡
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from imblearn.over_sampling import SMOTE, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler
from collections import Counter
from utils.logger import get_logger
from utils.decorators import timer

logger = get_logger(__name__)


class DataSplitter:
    """
    数据分割器

    职责：
    - 时间序列分割（train/valid/test）
    - 特征缩放（Standard/Robust/MinMax）
    - 样本平衡（Oversample/Undersample/SMOTE）
    """

    def __init__(self, scaler_type: str = 'robust', verbose: bool = True):
        """
        初始化数据分割器

        Args:
            scaler_type: 特征缩放类型 ('standard', 'robust', 'minmax')
            verbose: 是否输出详细日志
        """
        self.scaler_type = scaler_type
        self.verbose = verbose
        self.scaler = None

    @timer
    def split_and_prepare(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        train_ratio: float = 0.7,
        valid_ratio: float = 0.15,
        scale_features: bool = True,
        balance_samples: bool = False,
        balance_method: str = 'undersample',
        balance_threshold: float = 0.0,
        fit_scaler: bool = True
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        """
        分割和准备数据（一步完成）

        Args:
            X: 特征DataFrame
            y: 目标Series
            train_ratio: 训练集比例
            valid_ratio: 验证集比例
            scale_features: 是否缩放特征
            balance_samples: 是否平衡样本
            balance_method: 平衡方法 ('oversample', 'undersample', 'smote')
            balance_threshold: 分类阈值（收益率>threshold为涨）
            fit_scaler: 是否拟合scaler（True=训练模式，False=推理模式）

        Returns:
            (X_train, y_train, X_valid, y_valid, X_test, y_test)
        """
        self._log(f"数据分割与准备...")

        # 1. 时间序列分割
        X_train, y_train, X_valid, y_valid, X_test, y_test = self._split_time_series(
            X, y, train_ratio, valid_ratio
        )

        # 2. 特征缩放
        if scale_features:
            self._log(f"\n特征缩放 ({self.scaler_type})...")
            X_train, X_valid, X_test = self._scale_features(
                X_train, X_valid, X_test, fit=fit_scaler
            )

        # 3. 样本平衡（仅在训练集）
        if balance_samples:
            self._log(f"\n样本平衡 ({balance_method})...")
            X_train, y_train = self._balance_samples(
                X_train, y_train, method=balance_method, threshold=balance_threshold
            )

        self._log("\n数据准备完成:")
        self._log(f"  训练集: {len(X_train)} 样本")
        self._log(f"  验证集: {len(X_valid)} 样本")
        self._log(f"  测试集: {len(X_test)} 样本")
        self._log(f"  特征数: {len(X_train.columns)}")

        logger.info(f"数据分割完成: 训练={len(X_train)}, 验证={len(X_valid)}, 测试={len(X_test)}")

        return X_train, y_train, X_valid, y_valid, X_test, y_test

    def _split_time_series(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        train_ratio: float,
        valid_ratio: float
    ) -> Tuple:
        """时间序列分割（不打乱顺序）"""
        n_samples = len(X)
        train_end = int(n_samples * train_ratio)
        valid_end = int(n_samples * (train_ratio + valid_ratio))

        X_train = X.iloc[:train_end]
        y_train = y.iloc[:train_end]

        X_valid = X.iloc[train_end:valid_end]
        y_valid = y.iloc[train_end:valid_end]

        X_test = X.iloc[valid_end:]
        y_test = y.iloc[valid_end:]

        self._log(f"  训练集: {len(X_train)} ({train_ratio*100:.0f}%)")
        self._log(f"  验证集: {len(X_valid)} ({valid_ratio*100:.0f}%)")
        self._log(f"  测试集: {len(X_test)} ({(1-train_ratio-valid_ratio)*100:.0f}%)")

        return X_train, y_train, X_valid, y_valid, X_test, y_test

    def _scale_features(
        self,
        X_train: pd.DataFrame,
        X_valid: pd.DataFrame,
        X_test: pd.DataFrame,
        fit: bool = True
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        特征缩放

        Args:
            fit: True=拟合scaler（训练模式），False=使用已有scaler（推理模式）
        """
        # 选择scaler
        scaler_class = {
            'standard': StandardScaler,
            'robust': RobustScaler,
            'minmax': MinMaxScaler
        }[self.scaler_type]

        if fit:
            # 训练模式：在训练集上拟合scaler
            self.scaler = scaler_class()
            X_train_scaled = self.scaler.fit_transform(X_train)
        else:
            # 推理模式：使用已有scaler
            if self.scaler is None:
                raise ValueError(f"Scaler 未拟合，请先以fit=True模式运行")
            X_train_scaled = self.scaler.transform(X_train)

        # 对验证集和测试集使用同一个scaler
        X_valid_scaled = self.scaler.transform(X_valid)
        X_test_scaled = self.scaler.transform(X_test)

        # 转换回DataFrame
        X_train = pd.DataFrame(X_train_scaled, columns=X_train.columns, index=X_train.index)
        X_valid = pd.DataFrame(X_valid_scaled, columns=X_valid.columns, index=X_valid.index)
        X_test = pd.DataFrame(X_test_scaled, columns=X_test.columns, index=X_test.index)

        self._log(f"  缩放方法: {self.scaler_type}")
        self._log(f"  缩放后范围: [{X_train.values.min():.4f}, {X_train.values.max():.4f}]")

        return X_train, X_valid, X_test

    def _balance_samples(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        method: str = 'undersample',
        threshold: float = 0.0
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        样本平衡（仅在训练集）

        优化：使用向量化索引映射替代O(n²)循环查找

        Args:
            method: 平衡方法 ('oversample', 'undersample', 'smote')
            threshold: 分类阈值（收益率>threshold为涨）

        Returns:
            (平衡后的X, y)
        """
        # 将回归问题转为分类（涨/跌）
        y_binary = (y > threshold).astype(int)

        # 统计类别分布
        class_counts = Counter(y_binary)
        self._log(f"  原始分布: 跌={class_counts[0]}, 涨={class_counts[1]}")

        # 计算不平衡比例
        minority_class = min(class_counts, key=class_counts.get)
        majority_class = max(class_counts, key=class_counts.get)
        imbalance_ratio = class_counts[majority_class] / class_counts[minority_class]

        if imbalance_ratio < 1.5:
            self._log(f"  样本基本平衡 (比例={imbalance_ratio:.2f})，跳过重采样")
            return X, y

        # 应用重采样策略
        try:
            sampler = self._get_sampler(method, class_counts, minority_class)

            # 重采样
            X_resampled, y_binary_resampled = sampler.fit_resample(X, y_binary)

            # 恢复回归目标值（使用向量化索引映射，避免O(n²)）
            y_resampled = self._map_resampled_targets(X, y, X_resampled)

            # 重置索引
            X_resampled = pd.DataFrame(X_resampled, columns=X.columns)
            X_resampled.index = range(len(X_resampled))
            y_resampled.index = range(len(y_resampled))

            # 统计重采样后的分布
            y_binary_resampled = (y_resampled > threshold).astype(int)
            new_class_counts = Counter(y_binary_resampled)
            self._log(f"  重采样后: 跌={new_class_counts[0]}, 涨={new_class_counts[1]}")
            self._log(f"  样本总数: {len(X)} → {len(X_resampled)}")

            return X_resampled, y_resampled

        except Exception as e:
            logger.warning(f"重采样失败: {e}，返回原始数据")
            self._log(f"  重采样失败: {e}，返回原始数据")
            return X, y

    def _get_sampler(self, method: str, class_counts: Dict, minority_class: int):
        """获取采样器"""
        if method == 'oversample':
            return RandomOverSampler(random_state=42)
        elif method == 'undersample':
            return RandomUnderSampler(random_state=42)
        elif method == 'smote':
            # SMOTE需要样本数 > k_neighbors
            k_neighbors = min(5, class_counts[minority_class] - 1)
            if k_neighbors < 1:
                self._log("  样本太少，使用RandomOverSampler替代SMOTE")
                return RandomOverSampler(random_state=42)
            else:
                return SMOTE(k_neighbors=k_neighbors, random_state=42)
        else:
            raise ValueError(f"不支持的平衡方法: {method}")

    def _map_resampled_targets(
        self,
        X_original: pd.DataFrame,
        y_original: pd.Series,
        X_resampled: pd.DataFrame
    ) -> pd.Series:
        """
        映射重采样后的目标值（优化版本，避免O(n²)）

        使用向量化方法和索引哈希表快速查找
        """
        # 创建原始数据的哈希索引（使用行的哈希值）
        X_orig_array = X_original.values
        y_orig_array = y_original.values

        # 为每行创建唯一哈希（使用部分列以提升性能）
        hash_map = {}
        for i, row in enumerate(X_orig_array):
            # 使用前10个特征的值作为哈希键（权衡速度和准确性）
            row_key = tuple(np.round(row[:min(10, len(row))], decimals=6))
            hash_map[row_key] = i

        # 映射重采样样本
        resampled_indices = []
        X_resamp_array = X_resampled.values

        for row in X_resamp_array:
            row_key = tuple(np.round(row[:min(10, len(row))], decimals=6))
            if row_key in hash_map:
                resampled_indices.append(hash_map[row_key])
            else:
                # 回退：使用全特征精确匹配（罕见情况）
                full_key = tuple(np.round(row, decimals=6))
                # 线性搜索（仅在哈希碰撞时）
                for i, orig_row in enumerate(X_orig_array):
                    if np.allclose(orig_row, row, atol=1e-6):
                        resampled_indices.append(i)
                        break

        return pd.Series(y_orig_array[resampled_indices])

    def get_scaler(self) -> Optional[object]:
        """获取scaler对象（用于保存和加载）"""
        return self.scaler

    def set_scaler(self, scaler: object):
        """设置scaler对象（从保存的模型加载）"""
        self.scaler = scaler

    def _log(self, message: str):
        """输出日志"""
        if self.verbose:
            print(message)
