"""
数据流水线（Data Pipeline）
作为数据库和模型之间的桥梁，自动化数据获取、特征工程、标签生成、数据清洗和样本平衡
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, List, Dict, Union
from pathlib import Path
import warnings
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from imblearn.over_sampling import SMOTE, RandomOverSampler
from imblearn.under_sampling import RandomUnderSampler
from collections import Counter

warnings.filterwarnings('ignore')

from database.db_manager import DatabaseManager
from features.technical_indicators import TechnicalIndicators
from features.alpha_factors import AlphaFactors
from features.feature_transformer import FeatureTransformer


class DataPipeline:
    """
    数据流水线
    自动化处理从数据库读取到模型训练数据准备的全流程
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        target_periods: Union[int, List[int]] = 5,
        scaler_type: str = 'robust',
        cache_features: bool = True,
        cache_dir: str = 'data/pipeline_cache',
        verbose: bool = True
    ):
        """
        初始化数据流水线

        参数:
            db_manager: 数据库管理器实例（None则自动创建）
            target_periods: 预测周期（天数），支持单个或多个
            scaler_type: 特征缩放类型 ('standard', 'robust', 'minmax')
            cache_features: 是否缓存计算好的特征
            cache_dir: 缓存目录
            verbose: 是否输出详细日志
        """
        self.db = db_manager if db_manager else DatabaseManager()
        self.target_periods = [target_periods] if isinstance(target_periods, int) else target_periods
        self.scaler_type = scaler_type
        self.cache_features = cache_features
        self.cache_dir = Path(cache_dir)
        self.verbose = verbose

        if self.cache_features:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 缓存的scaler对象
        self.scalers = {}
        self.feature_names = []
        self.target_name = None

        # 统计信息
        self.stats = {
            'raw_samples': 0,
            'after_nan_removal': 0,
            'after_target_removal': 0,
            'final_samples': 0,
            'removed_nan': 0,
            'removed_target_nan': 0,
            'resampled': False
        }

    def log(self, message: str):
        """输出日志"""
        if self.verbose:
            print(message)

    # ==================== 核心方法 ====================

    def get_training_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        target_period: Optional[int] = None,
        use_cache: bool = True,
        force_refresh: bool = False
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        获取训练数据（自动化流转）

        参数:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            target_period: 预测周期（None则使用初始化时的第一个周期）
            use_cache: 是否使用缓存
            force_refresh: 强制刷新缓存

        返回:
            (特征DataFrame, 目标Series)
        """
        self.log(f"\n{'='*60}")
        self.log(f"数据流水线: {symbol} ({start_date} ~ {end_date})")
        self.log(f"{'='*60}")

        # 确定目标周期
        target_period = target_period or self.target_periods[0]
        self.target_name = f'target_{target_period}d_return'

        # 1. 检查缓存
        cache_file = self._get_cache_path(symbol, start_date, end_date, target_period)
        if use_cache and not force_refresh and cache_file.exists():
            self.log("\n✓ 从缓存加载数据...")
            return self._load_from_cache(cache_file)

        # 2. 从数据库读取原始数据
        self.log("\n[1/7] 从数据库读取原始数据...")
        df = self._load_raw_data(symbol, start_date, end_date)

        # 3. 计算技术指标
        self.log("\n[2/7] 计算技术指标...")
        df = self._calculate_technical_indicators(df)

        # 4. 计算Alpha因子
        self.log("\n[3/7] 计算Alpha因子...")
        df = self._calculate_alpha_factors(df)

        # 5. 特征转换
        self.log("\n[4/7] 进行特征转换...")
        df = self._apply_feature_transformation(df)

        # 6. 创建目标标签
        self.log(f"\n[5/7] 创建目标标签 (未来{target_period}日收益率)...")
        df = self._create_target(df, target_period)

        # 7. 数据清洗
        self.log("\n[6/7] 数据清洗...")
        df = self._clean_data(df)

        # 8. 分离特征和目标
        X, y = self._separate_features_target(df)

        # 9. 缓存结果
        if self.cache_features:
            self._save_to_cache(X, y, cache_file)

        self.log(f"\n{'='*60}")
        self._print_stats()
        self.log(f"{'='*60}\n")

        return X, y

    def prepare_for_model(
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
    ) -> Tuple:
        """
        为模型准备数据（缩放、平衡、分割）

        参数:
            X: 特征DataFrame
            y: 目标Series
            train_ratio: 训练集比例
            valid_ratio: 验证集比例
            scale_features: 是否缩放特征
            balance_samples: 是否平衡样本
            balance_method: 平衡方法 ('oversample', 'undersample', 'smote')
            balance_threshold: 分类阈值（收益率>threshold为涨）
            fit_scaler: 是否拟合scaler（True=训练模式，False=推理模式）

        返回:
            (X_train, y_train, X_valid, y_valid, X_test, y_test)
        """
        self.log(f"\n{'='*60}")
        self.log("为模型准备数据...")
        self.log(f"{'='*60}")

        # 1. 时间序列分割（不打乱顺序）
        self.log("\n[7/7] 分割训练/验证/测试集...")
        X_train, y_train, X_valid, y_valid, X_test, y_test = self._split_data(
            X, y, train_ratio, valid_ratio
        )

        # 2. 特征缩放
        if scale_features:
            self.log(f"\n特征缩放 ({self.scaler_type})...")
            X_train, X_valid, X_test = self._scale_features(
                X_train, X_valid, X_test, fit=fit_scaler
            )

        # 3. 样本平衡（仅在训练集）
        if balance_samples:
            self.log(f"\n样本平衡 ({balance_method})...")
            X_train, y_train = self._balance_samples(
                X_train, y_train, method=balance_method, threshold=balance_threshold
            )

        self.log("\n数据准备完成:")
        self.log(f"  训练集: {len(X_train)} 样本")
        self.log(f"  验证集: {len(X_valid)} 样本")
        self.log(f"  测试集: {len(X_test)} 样本")
        self.log(f"  特征数: {len(X_train.columns)}")

        return X_train, y_train, X_valid, y_valid, X_test, y_test

    # ==================== 内部方法 ====================

    def _load_raw_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从数据库读取原始数据"""
        df = self.db.load_daily_data(symbol, start_date, end_date)

        if df is None or len(df) == 0:
            raise ValueError(f"无法获取股票 {symbol} 的数据")

        self.stats['raw_samples'] = len(df)
        self.log(f"  原始数据: {len(df)} 条记录")

        # 确保索引是日期
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            else:
                raise ValueError("数据缺少日期索引")

        # 排序
        df = df.sort_index()

        return df

    def _calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
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

        # 记录特征名（技术指标）
        technical_features = [col for col in df.columns if col not in
                             ['open', 'high', 'low', 'close', 'volume', 'amount']]

        self.log(f"  技术指标: {len(technical_features)} 个")

        return df

    def _calculate_alpha_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算Alpha因子"""
        af = AlphaFactors(df)

        # 添加常用Alpha因子
        af.add_momentum_factors([5, 10, 20, 60, 120])
        af.add_reversal_factors([1, 3, 5], [20, 60])
        af.add_volatility_factors([5, 10, 20, 60])
        af.add_volume_factors([5, 10, 20])
        af.add_trend_strength([20, 60])

        df = af.get_dataframe()

        # 记录特征名（Alpha因子）
        alpha_features = af.get_factor_names()

        self.log(f"  Alpha因子: {len(alpha_features)} 个")

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

        self.log(f"  转换特征: 添加时间尺度收益率、OHLC、时间特征")

        return df

    def _create_target(self, df: pd.DataFrame, target_period: int) -> pd.DataFrame:
        """
        创建目标标签（未来N日收益率）

        参数:
            df: DataFrame
            target_period: 预测周期（天数）

        返回:
            包含目标标签的DataFrame
        """
        # 计算未来N日收益率
        df[self.target_name] = df['close'].pct_change(target_period).shift(-target_period) * 100

        # 统计
        valid_targets = df[self.target_name].notna().sum()
        self.log(f"  目标标签: {self.target_name}")
        self.log(f"  有效样本: {valid_targets} / {len(df)}")
        self.log(f"  目标均值: {df[self.target_name].mean():.4f}%")
        self.log(f"  目标标准差: {df[self.target_name].std():.4f}%")

        return df

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        数据清洗（处理NaN和Inf）

        A股特殊情况：
        - 停牌会导致成交量为0，某些指标变为NaN
        - 涨跌停会导致某些指标异常
        """
        initial_count = len(df)

        # 1. 处理无穷值（替换为NaN）
        df = df.replace([np.inf, -np.inf], np.nan)

        # 2. 移除特征全为NaN的行（通常是前期指标计算不足）
        before_nan = len(df)
        df = df.dropna(subset=[col for col in df.columns if col != self.target_name])
        after_nan = len(df)

        self.stats['after_nan_removal'] = after_nan
        self.stats['removed_nan'] = before_nan - after_nan

        self.log(f"  移除特征NaN: {self.stats['removed_nan']} 条")

        # 3. 移除目标标签为NaN的行（最后N天无未来数据）
        before_target = len(df)
        df = df.dropna(subset=[self.target_name])
        after_target = len(df)

        self.stats['after_target_removal'] = after_target
        self.stats['removed_target_nan'] = before_target - after_target

        self.log(f"  移除目标NaN: {self.stats['removed_target_nan']} 条")

        # 4. 处理剩余的极端值（使用分位数截断）
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        numeric_cols = [col for col in numeric_cols if col != self.target_name]

        for col in numeric_cols:
            q1 = df[col].quantile(0.01)
            q99 = df[col].quantile(0.99)
            df[col] = df[col].clip(lower=q1, upper=q99)

        self.stats['final_samples'] = len(df)

        self.log(f"  最终样本: {len(df)} 条 (保留 {len(df)/initial_count*100:.1f}%)")

        return df

    def _separate_features_target(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """分离特征和目标"""
        # 排除的列（原始价格、成交量等）
        exclude_cols = [
            'open', 'high', 'low', 'close', 'volume', 'amount',
            self.target_name
        ]

        # 特征列
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        self.feature_names = feature_cols

        X = df[feature_cols].copy()
        y = df[self.target_name].copy()

        self.log(f"\n特征数量: {len(feature_cols)}")
        self.log(f"目标变量: {self.target_name}")

        return X, y

    def _split_data(
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

        self.log(f"  训练集: {len(X_train)} ({train_ratio*100:.0f}%)")
        self.log(f"  验证集: {len(X_valid)} ({valid_ratio*100:.0f}%)")
        self.log(f"  测试集: {len(X_test)} ({(1-train_ratio-valid_ratio)*100:.0f}%)")

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

        参数:
            fit: True=拟合scaler（训练模式），False=使用已有scaler（推理模式）
        """
        # 选择scaler
        scaler_class = {
            'standard': StandardScaler,  # 标准化（均值0，方差1）
            'robust': RobustScaler,      # 鲁棒缩放（对异常值不敏感）
            'minmax': MinMaxScaler       # 归一化到[0, 1]
        }[self.scaler_type]

        if fit:
            # 训练模式：在训练集上拟合scaler
            scaler = scaler_class()
            X_train_scaled = scaler.fit_transform(X_train)
            self.scalers[self.scaler_type] = scaler
        else:
            # 推理模式：使用已有scaler
            if self.scaler_type not in self.scalers:
                raise ValueError(f"Scaler '{self.scaler_type}' 未拟合，请先以fit=True模式运行")
            scaler = self.scalers[self.scaler_type]
            X_train_scaled = scaler.transform(X_train)

        # 对验证集和测试集使用��一个scaler
        X_valid_scaled = scaler.transform(X_valid)
        X_test_scaled = scaler.transform(X_test)

        # 转换回DataFrame
        X_train = pd.DataFrame(X_train_scaled, columns=X_train.columns, index=X_train.index)
        X_valid = pd.DataFrame(X_valid_scaled, columns=X_valid.columns, index=X_valid.index)
        X_test = pd.DataFrame(X_test_scaled, columns=X_test.columns, index=X_test.index)

        self.log(f"  缩放方法: {self.scaler_type}")
        self.log(f"  缩放后范围: [{X_train.values.min():.4f}, {X_train.values.max():.4f}]")

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

        参数:
            method: 平衡方法
                - 'oversample': 过采样（复制少数类）
                - 'undersample': 欠采样（减少多数类）
                - 'smote': SMOTE合成少数类样本
            threshold: 分类阈值（收益率>threshold为涨，否则为跌）

        返回:
            (平衡后的X, y)
        """
        # 将回归问题转为分类（涨/跌）
        y_binary = (y > threshold).astype(int)

        # 统计类别分布
        class_counts = Counter(y_binary)
        self.log(f"  原始分布: 跌={class_counts[0]}, 涨={class_counts[1]}")

        # 计算不平衡比例
        minority_class = min(class_counts, key=class_counts.get)
        majority_class = max(class_counts, key=class_counts.get)
        imbalance_ratio = class_counts[majority_class] / class_counts[minority_class]

        if imbalance_ratio < 1.5:
            self.log(f"  样本基本平衡 (比例={imbalance_ratio:.2f})，跳过重采样")
            return X, y

        # 应用重采样策略
        try:
            if method == 'oversample':
                sampler = RandomOverSampler(random_state=42)
            elif method == 'undersample':
                sampler = RandomUnderSampler(random_state=42)
            elif method == 'smote':
                # SMOTE需要样本数 > k_neighbors
                k_neighbors = min(5, class_counts[minority_class] - 1)
                if k_neighbors < 1:
                    self.log("  样本太少，使用RandomOverSampler替代SMOTE")
                    sampler = RandomOverSampler(random_state=42)
                else:
                    sampler = SMOTE(k_neighbors=k_neighbors, random_state=42)
            else:
                raise ValueError(f"不支持的平衡方法: {method}")

            # 重采样
            X_resampled, y_binary_resampled = sampler.fit_resample(X, y_binary)

            # 恢复回归目标值（根据索引映射）
            # 注意：过采样会复制样本，需要从原始y中获取对应的值
            original_indices = X.index.tolist()
            resampled_indices = []

            for i in range(len(X_resampled)):
                # 找到最接近的原始样本
                row = X_resampled.iloc[i]
                for orig_idx in original_indices:
                    if np.allclose(X.loc[orig_idx].values, row.values, atol=1e-6):
                        resampled_indices.append(orig_idx)
                        break

            y_resampled = y.loc[resampled_indices]

            # 重置索引
            X_resampled = pd.DataFrame(X_resampled, columns=X.columns)
            X_resampled.index = range(len(X_resampled))
            y_resampled.index = range(len(y_resampled))

            # 统计重采样后的分布
            y_binary_resampled = (y_resampled > threshold).astype(int)
            new_class_counts = Counter(y_binary_resampled)
            self.log(f"  重采样后: 跌={new_class_counts[0]}, 涨={new_class_counts[1]}")
            self.log(f"  样本总数: {len(X)} → {len(X_resampled)}")

            self.stats['resampled'] = True

            return X_resampled, y_resampled

        except Exception as e:
            self.log(f"  重采样失败: {e}，返回原始数据")
            return X, y

    # ==================== 缓存管理 ====================

    def _get_cache_path(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        target_period: int
    ) -> Path:
        """生成缓存文件路径"""
        filename = f"{symbol}_{start_date}_{end_date}_T{target_period}.parquet"
        return self.cache_dir / filename

    def _save_to_cache(self, X: pd.DataFrame, y: pd.Series, cache_file: Path):
        """保存到缓存"""
        try:
            # 合并X和y
            df_cache = X.copy()
            df_cache[self.target_name] = y

            # 保存为Parquet格式（高效）
            df_cache.to_parquet(cache_file, compression='gzip')

            self.log(f"\n✓ 缓存已保存: {cache_file.name}")
        except Exception as e:
            self.log(f"\n✗ 缓存保存失败: {e}")

    def _load_from_cache(self, cache_file: Path) -> Tuple[pd.DataFrame, pd.Series]:
        """从缓存加载"""
        df_cache = pd.read_parquet(cache_file)

        X = df_cache.drop(columns=[self.target_name])
        y = df_cache[self.target_name]

        self.feature_names = X.columns.tolist()

        self.log(f"  数据形状: {X.shape}")
        self.log(f"  特征数量: {len(self.feature_names)}")

        return X, y

    def clear_cache(self, symbol: Optional[str] = None):
        """
        清除缓存

        参数:
            symbol: 股票代码（None则清除所有）
        """
        if symbol:
            pattern = f"{symbol}_*.parquet"
        else:
            pattern = "*.parquet"

        cache_files = list(self.cache_dir.glob(pattern))

        for file in cache_files:
            file.unlink()

        self.log(f"已清除 {len(cache_files)} 个缓存文件")

    # ==================== 工具方法 ====================

    def _print_stats(self):
        """打印统计信息"""
        self.log("\n统计信息:")
        self.log(f"  原始样本: {self.stats['raw_samples']}")
        self.log(f"  移除特征NaN: {self.stats['removed_nan']}")
        self.log(f"  移除目标NaN: {self.stats['removed_target_nan']}")
        self.log(f"  最终样本: {self.stats['final_samples']}")
        self.log(f"  数据保留率: {self.stats['final_samples']/self.stats['raw_samples']*100:.1f}%")

    def get_feature_names(self) -> List[str]:
        """获取特征名列表"""
        return self.feature_names.copy()

    def get_scaler(self) -> Optional[object]:
        """获取scaler对象（用于保存和加载）"""
        return self.scalers.get(self.scaler_type)

    def set_scaler(self, scaler: object):
        """设置scaler对象（从保存的模型加载）"""
        self.scalers[self.scaler_type] = scaler

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()


# ==================== 便捷函数 ====================

def create_pipeline(
    target_period: int = 5,
    scaler_type: str = 'robust',
    verbose: bool = True
) -> DataPipeline:
    """
    便捷函数：创建数据流水线

    参数:
        target_period: 预测周期（天数）
        scaler_type: 缩放类型
        verbose: 是否输出日志

    返回:
        DataPipeline实例
    """
    return DataPipeline(
        target_periods=target_period,
        scaler_type=scaler_type,
        verbose=verbose
    )


def get_full_training_data(
    symbol: str,
    start_date: str,
    end_date: str,
    target_period: int = 5,
    train_ratio: float = 0.7,
    valid_ratio: float = 0.15,
    scale_features: bool = True,
    balance_samples: bool = False,
    scaler_type: str = 'robust'
) -> Tuple:
    """
    便捷函数：一键获取完整训练数据（从数据库到模型就绪）

    参数:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        target_period: 预测周期
        train_ratio: 训练集比例
        valid_ratio: 验证集比例
        scale_features: 是否缩放特征
        balance_samples: 是否平衡样本
        scaler_type: 缩放类型

    返回:
        (X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline)
    """
    # 创建流水线
    pipeline = DataPipeline(
        target_periods=target_period,
        scaler_type=scaler_type,
        verbose=True
    )

    # 获取数据
    X, y = pipeline.get_training_data(symbol, start_date, end_date, target_period)

    # 准备数据
    X_train, y_train, X_valid, y_valid, X_test, y_test = pipeline.prepare_for_model(
        X, y,
        train_ratio=train_ratio,
        valid_ratio=valid_ratio,
        scale_features=scale_features,
        balance_samples=balance_samples
    )

    return X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline


# ==================== 使用示例 ====================

if __name__ == "__main__":
    print("数据流水线测试\n")

    # 示例1：基础使用
    print("="*60)
    print("示例1: 基础使用")
    print("="*60)

    pipeline = DataPipeline(
        target_periods=5,
        scaler_type='robust',
        verbose=True
    )

    # 获取训练数据
    X, y = pipeline.get_training_data(
        symbol='000001',
        start_date='20200101',
        end_date='20231231'
    )

    print(f"\n特征形状: {X.shape}")
    print(f"目标形状: {y.shape}")
    print(f"特征列表 (前10个): {pipeline.get_feature_names()[:10]}")

    # 准备模型数据
    X_train, y_train, X_valid, y_valid, X_test, y_test = pipeline.prepare_for_model(
        X, y,
        train_ratio=0.7,
        valid_ratio=0.15,
        scale_features=True,
        balance_samples=True,
        balance_method='undersample'
    )

    print("\n示例2: 一键获取完整数据")
    print("="*60)

    # 一键获取
    result = get_full_training_data(
        symbol='600519',
        start_date='20200101',
        end_date='20231231',
        target_period=10,
        scale_features=True,
        balance_samples=True
    )

    X_train, y_train, X_valid, y_valid, X_test, y_test, pipeline = result

    print(f"\n训练集: {len(X_train)} 样本")
    print(f"验证集: {len(X_valid)} 样本")
    print(f"测试集: {len(X_test)} 样本")

    print("\n✓ 数据流水线测试完成")
