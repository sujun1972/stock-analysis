"""
异常值检测器 - 检测和处理价格数据中的异常值

功能：
- IQR方法检测异常值
- Z-score方法检测异常值
- 单日暴涨暴跌检测
- 价格跳空检测
- 异常值处理（移除/截断/插值）

作者: AI Assistant
日期: 2026-01-30
"""

import pandas as pd
import numpy as np
from typing import Optional, Literal, Dict, Tuple, Union, Any
from loguru import logger
from scipy import stats


class OutlierDetector:
    """
    异常值检测器 - 检测价格数据中的异常值

    支持多种检测方法：
    - IQR (四分位距) 方法
    - Z-score (标准分数) 方法
    - 修正Z-score (MAD) 方法
    - 固定阈值方法（如单日涨跌幅>20%）

    用途：
    - 数据质量检查
    - 识别异常交易日
    - 清洗脏数据
    """

    def __init__(
        self,
        df: pd.DataFrame,
        price_cols: list = None,
        volume_col: str = None
    ):
        """
        初始化异常值检测器

        参数：
            df: 价格数据DataFrame
            price_cols: 价格列列表，默认 ['open', 'high', 'low', 'close']
            volume_col: 成交量列名，默认自动检测 'volume' 或 'vol'
        """
        self.df = df.copy()

        # 默认价格列
        if price_cols is None:
            price_cols = ['open', 'high', 'low', 'close']
        self.price_cols = [col for col in price_cols if col in df.columns]

        # 检测成交量列
        if volume_col is None:
            if 'volume' in df.columns:
                self.volume_col = 'volume'
            elif 'vol' in df.columns:
                self.volume_col = 'vol'
            else:
                self.volume_col = None
        else:
            self.volume_col = volume_col if volume_col in df.columns else None

        logger.debug(f"初始化异常值检测器: 价格列={self.price_cols}, 成交量列={self.volume_col}")

    def detect_by_iqr(
        self,
        column: str,
        multiplier: float = 3.0,
        use_returns: bool = True
    ) -> pd.Series:
        """
        使用IQR方法检测异常值

        IQR = Q3 - Q1
        异常值定义: < Q1 - multiplier*IQR 或 > Q3 + multiplier*IQR

        参数：
            column: 列名
            multiplier: IQR倍数（默认3.0，更宽松；1.5为严格）
            use_returns: 是否检测收益率异常（推荐）而非价格异常

        返回：
            布尔序列，True表示异常值
        """
        if column not in self.df.columns:
            logger.warning(f"列 '{column}' 不存在")
            return pd.Series(False, index=self.df.index)

        # 使用收益率检测（对价格序列更合适）
        if use_returns:
            data = self.df[column].pct_change()
            logger.debug(f"使用收益率检测异常值: {column}")
        else:
            data = self.df[column]

        # 计算IQR
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1

        # 计算边界
        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR

        # 检测异常值
        outliers = (data < lower_bound) | (data > upper_bound)

        outlier_count = outliers.sum()
        outlier_pct = (outlier_count / len(data)) * 100
        logger.info(
            f"IQR检测 [{column}]: 异常值={outlier_count} ({outlier_pct:.2f}%), "
            f"边界=[{lower_bound:.4f}, {upper_bound:.4f}]"
        )

        return outliers

    def detect_by_zscore(
        self,
        column: str,
        threshold: float = 3.0,
        use_returns: bool = True,
        use_modified: bool = False
    ) -> pd.Series:
        """
        使用Z-score方法检测异常值

        标准Z-score: (x - mean) / std
        修正Z-score (MAD): 0.6745 * (x - median) / MAD

        参数：
            column: 列名
            threshold: Z-score阈值（默认3.0）
            use_returns: 是否检测收益率异常
            use_modified: 是否使用修正Z-score（基于中位数，更鲁棒）

        返回：
            布尔序列，True表示异常值
        """
        if column not in self.df.columns:
            logger.warning(f"列 '{column}' 不存在")
            return pd.Series(False, index=self.df.index)

        # 使用收益率检测
        if use_returns:
            data = self.df[column].pct_change()
        else:
            data = self.df[column]

        # 修正Z-score（基于中位数绝对偏差MAD）
        if use_modified:
            median = data.median()
            mad = np.abs(data - median).median()

            if mad == 0:
                logger.warning(f"MAD为0，无法计算修正Z-score: {column}")
                return pd.Series(False, index=self.df.index)

            # 修正Z-score公式
            z_scores = 0.6745 * (data - median) / mad
            method = "修正Z-score"
        else:
            # 标准Z-score
            z_scores = (data - data.mean()) / data.std()
            method = "标准Z-score"

        # 检测异常值
        outliers = np.abs(z_scores) > threshold

        outlier_count = outliers.sum()
        outlier_pct = (outlier_count / len(data)) * 100
        logger.info(
            f"{method}检测 [{column}]: 异常值={outlier_count} ({outlier_pct:.2f}%), "
            f"阈值={threshold}"
        )

        return outliers

    def detect_price_jumps(
        self,
        threshold: float = 0.20,
        consecutive_days: int = 1
    ) -> pd.Series:
        """
        检测价格暴涨暴跌（如单日涨跌幅>20%）

        参数：
            threshold: 涨跌幅阈值（默认0.20即20%）
            consecutive_days: 连续异常天数（默认1天）

        返回：
            布尔序列，True表示异常涨跌
        """
        if 'close' not in self.df.columns:
            logger.warning("缺少'close'列，无法检测价格跳空")
            return pd.Series(False, index=self.df.index)

        # 计算收益率
        returns = self.df['close'].pct_change().abs()

        # 单日异常
        if consecutive_days == 1:
            jumps = returns > threshold
        else:
            # 连续N日异常
            jumps = returns.rolling(window=consecutive_days).apply(
                lambda x: (x > threshold).all()
            ).fillna(False).astype(bool)

        jump_count = jumps.sum()
        jump_pct = (jump_count / len(returns)) * 100

        logger.info(
            f"价格跳空检测: 异常={jump_count} ({jump_pct:.2f}%), "
            f"阈值={threshold*100:.1f}%, 连续天数={consecutive_days}"
        )

        return jumps

    def detect_volume_anomalies(
        self,
        method: Literal['iqr', 'zscore'] = 'zscore',
        threshold: float = 3.0
    ) -> pd.Series:
        """
        检测成交量异常

        参数：
            method: 检测方法 ('iqr' 或 'zscore')
            threshold: 阈值

        返回：
            布尔序列，True表示成交量异常
        """
        if self.volume_col is None or self.volume_col not in self.df.columns:
            logger.warning("缺少成交量列，无法检测成交量异常")
            return pd.Series(False, index=self.df.index)

        if method == 'iqr':
            return self.detect_by_iqr(
                self.volume_col,
                multiplier=threshold,
                use_returns=False  # 成交量直接检测
            )
        elif method == 'zscore':
            return self.detect_by_zscore(
                self.volume_col,
                threshold=threshold,
                use_returns=False,
                use_modified=True  # 成交量分布通常偏斜，用修正Z-score
            )
        else:
            logger.error(f"未知的检测方法: {method}")
            return pd.Series(False, index=self.df.index)

    def detect_all_outliers(
        self,
        price_method: Literal['iqr', 'zscore', 'both'] = 'both',
        price_threshold: float = 3.0,
        jump_threshold: float = 0.20,
        volume_method: Literal['iqr', 'zscore', 'none'] = 'zscore',
        volume_threshold: float = 3.0
    ) -> pd.DataFrame:
        """
        综合检测所有类型的异常值

        参数：
            price_method: 价格异常检测方法 ('iqr', 'zscore', 'both')
            price_threshold: 价格异常阈值
            jump_threshold: 价格跳空阈值（如0.20=20%）
            volume_method: 成交量异常检测方法 ('iqr', 'zscore', 'none')
            volume_threshold: 成交量异常阈值

        返回：
            包含各类异常标记的DataFrame
        """
        logger.info("开始综合异常值检测...")

        outliers_df = pd.DataFrame(index=self.df.index)

        # 1. 价格异常检测
        for col in self.price_cols:
            if col not in self.df.columns:
                continue

            if price_method in ['iqr', 'both']:
                outliers_df[f'{col}_outlier_iqr'] = self.detect_by_iqr(
                    col, multiplier=price_threshold, use_returns=True
                )

            if price_method in ['zscore', 'both']:
                outliers_df[f'{col}_outlier_zscore'] = self.detect_by_zscore(
                    col, threshold=price_threshold, use_returns=True, use_modified=True
                )

        # 2. 价格跳空检测
        outliers_df['price_jump'] = self.detect_price_jumps(threshold=jump_threshold)

        # 3. 成交量异常检测
        if volume_method != 'none':
            outliers_df['volume_outlier'] = self.detect_volume_anomalies(
                method=volume_method,
                threshold=volume_threshold
            )

        # 4. 汇总异常标记
        outlier_cols = [col for col in outliers_df.columns if 'outlier' in col or 'jump' in col]
        outliers_df['is_outlier'] = outliers_df[outlier_cols].any(axis=1)

        total_outliers = outliers_df['is_outlier'].sum()
        total_pct = (total_outliers / len(self.df)) * 100

        logger.info(f"综合异常检测完成: 总异常值={total_outliers} ({total_pct:.2f}%)")

        return outliers_df

    def get_outlier_summary(
        self,
        outliers_df: pd.DataFrame
    ) -> Dict[str, any]:
        """
        获取异常值检测摘要统计

        参数：
            outliers_df: detect_all_outliers() 返回的DataFrame

        返回：
            摘要统计字典
        """
        summary = {
            'total_records': len(self.df),
            'total_outliers': outliers_df['is_outlier'].sum(),
            'outlier_percentage': (outliers_df['is_outlier'].sum() / len(self.df)) * 100,
            'by_type': {}
        }

        # 各类型异常统计
        for col in outliers_df.columns:
            if col != 'is_outlier':
                count = outliers_df[col].sum()
                pct = (count / len(self.df)) * 100
                summary['by_type'][col] = {
                    'count': int(count),
                    'percentage': round(pct, 2)
                }

        # 异常值日期列表
        outlier_dates = self.df.index[outliers_df['is_outlier']].tolist()
        summary['outlier_dates'] = outlier_dates[:10]  # 只显示前10个

        if len(outlier_dates) > 10:
            summary['more_outliers'] = len(outlier_dates) - 10

        return summary

    # ==================== 异常值处理方法 ====================

    def remove_outliers(
        self,
        outliers: pd.Series,
        columns: list = None
    ) -> pd.DataFrame:
        """
        移除异常值（将异常值设置为NaN）

        参数：
            outliers: 布尔序列，True表示异常值
            columns: 要处理的列列表（默认所有价格列）

        返回：
            处理后的DataFrame
        """
        if columns is None:
            columns = self.price_cols

        df_cleaned = self.df.copy()

        for col in columns:
            if col in df_cleaned.columns:
                df_cleaned.loc[outliers, col] = np.nan

        removed_count = outliers.sum()
        logger.info(f"移除异常值: {removed_count} 行数据被设置为NaN")

        return df_cleaned

    def winsorize_outliers(
        self,
        outliers: pd.Series = None,
        columns: list = None,
        lower_percentile: float = 0.01,
        upper_percentile: float = 0.99
    ) -> pd.DataFrame:
        """
        缩尾处理（Winsorization）：将异常值替换为边界值

        参数：
            outliers: 布尔序列（可选，None则自动检测）
            columns: 要处理的列列表
            lower_percentile: 下边界百分位（默认1%）
            upper_percentile: 上边界百分位（默认99%）

        返回：
            处理后的DataFrame
        """
        if columns is None:
            columns = self.price_cols

        df_cleaned = self.df.copy()

        for col in columns:
            if col not in df_cleaned.columns:
                continue

            # 计算边界值
            lower_bound = df_cleaned[col].quantile(lower_percentile)
            upper_bound = df_cleaned[col].quantile(upper_percentile)

            # 缩尾处理
            df_cleaned[col] = df_cleaned[col].clip(lower=lower_bound, upper=upper_bound)

            logger.debug(
                f"缩尾处理 [{col}]: 边界=[{lower_bound:.2f}, {upper_bound:.2f}]"
            )

        logger.info(f"缩尾处理完成: {len(columns)} 列")

        return df_cleaned

    def interpolate_outliers(
        self,
        outliers: pd.Series,
        columns: list = None,
        method: Literal['linear', 'time', 'spline'] = 'linear'
    ) -> pd.DataFrame:
        """
        插值处理：使用插值法填充异常值

        参数：
            outliers: 布尔序列，True表示异常值
            columns: 要处理的列列表
            method: 插值方法 ('linear', 'time', 'spline')

        返回：
            处理后的DataFrame
        """
        if columns is None:
            columns = self.price_cols

        # 先移除异常值（设为NaN）
        df_cleaned = self.remove_outliers(outliers, columns)

        # 插值填充
        for col in columns:
            if col in df_cleaned.columns:
                df_cleaned[col] = df_cleaned[col].interpolate(method=method)

        filled_count = outliers.sum()
        logger.info(f"插值处理完成: {filled_count} 个异常值已插值 (方法={method})")

        return df_cleaned

    def handle_outliers(
        self,
        outliers: pd.Series,
        method: Literal['remove', 'winsorize', 'interpolate'] = 'interpolate',
        columns: list = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        统一的异常值处理接口

        参数：
            outliers: 布尔序列，True表示异常值
            method: 处理方法 ('remove', 'winsorize', 'interpolate')
            columns: 要处理的列列表
            **kwargs: 传递给具体方法的额外参数

        返回：
            处理后的DataFrame
        """
        if method == 'remove':
            return self.remove_outliers(outliers, columns)
        elif method == 'winsorize':
            return self.winsorize_outliers(outliers, columns, **kwargs)
        elif method == 'interpolate':
            return self.interpolate_outliers(outliers, columns, **kwargs)
        else:
            logger.error(f"未知的处理方法: {method}")
            return self.df.copy()


# ==================== 便捷函数 ====================


def detect_outliers(
    df: pd.DataFrame,
    method: Literal['iqr', 'zscore', 'both'] = 'both',
    threshold: float = 3.0,
    columns: list = None
) -> pd.DataFrame:
    """
    便捷函数：快速检测异常值

    参数：
        df: 价格数据DataFrame
        method: 检测方法
        threshold: 阈值
        columns: 要检测的列（默认 ['close']）

    返回：
        包含异常标记的DataFrame
    """
    if columns is None:
        columns = ['close']

    detector = OutlierDetector(df, price_cols=columns)
    return detector.detect_all_outliers(
        price_method=method,
        price_threshold=threshold
    )


def clean_outliers(
    df: pd.DataFrame,
    method: Literal['remove', 'winsorize', 'interpolate'] = 'interpolate',
    detection_method: Literal['iqr', 'zscore', 'both'] = 'both',
    threshold: float = 3.0,
    columns: list = None
) -> pd.DataFrame:
    """
    便捷函数：一键检测并清洗异常值

    参数：
        df: 价格数据DataFrame
        method: 处理方法
        detection_method: 检测方法
        threshold: 检测阈值
        columns: 要处理的列

    返回：
        清洗后的DataFrame
    """
    if columns is None:
        columns = ['open', 'high', 'low', 'close']

    detector = OutlierDetector(df, price_cols=columns)

    # 检测异常值
    outliers_df = detector.detect_all_outliers(
        price_method=detection_method,
        price_threshold=threshold
    )

    # 处理异常值
    df_cleaned = detector.handle_outliers(
        outliers_df['is_outlier'],
        method=method,
        columns=columns
    )

    return df_cleaned


# ==================== 使用示例 ====================


if __name__ == "__main__":
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')

    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)

    # 注入异常值
    returns[20] = 0.25  # 单日暴涨25%
    returns[50] = -0.22  # 单日暴跌22%

    prices = base_price * (1 + returns).cumprod()

    test_df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)

    print("=" * 60)
    print("异常值检测器测试")
    print("=" * 60)

    # 1. 检测异常值
    detector = OutlierDetector(test_df)
    outliers_df = detector.detect_all_outliers()

    print(f"\n检测到 {outliers_df['is_outlier'].sum()} 个异常值")
    print("\n异常值日期:")
    print(test_df.index[outliers_df['is_outlier']].tolist())

    # 2. 获取摘要
    summary = detector.get_outlier_summary(outliers_df)
    print(f"\n异常值摘要: {summary}")

    # 3. 处理异常值
    df_cleaned = detector.handle_outliers(
        outliers_df['is_outlier'],
        method='interpolate'
    )

    print(f"\n清洗前后对比:")
    print(f"清洗前NaN数量: {test_df.isnull().sum().sum()}")
    print(f"清洗后NaN数量: {df_cleaned.isnull().sum().sum()}")

    print("\n测试完成！")
