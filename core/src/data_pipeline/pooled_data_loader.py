"""
池化数据加载器
支持多股票数据的纵向堆叠(Stacking)
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional
from src.database.db_manager import get_database, DatabaseManager
from src.data_pipeline.feature_engineer import FeatureEngineer
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PooledDataLoader:
    """
    池化数据加载器

    功能：
    - 加载多只股票的数据
    - 纵向堆叠(Vertical Stacking)
    - 保持时间序列顺序
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        verbose: bool = True
    ):
        """
        初始化池化数据加载器

        参数:
            db_manager: 数据库管理器
            verbose: 是否输出详细日志
        """
        self.db = db_manager or get_database()
        self.verbose = verbose

    def load_pooled_data(
        self,
        symbol_list: List[str],
        start_date: str,
        end_date: str,
        target_period: int = 10
    ) -> Tuple[pd.DataFrame, int, List[str]]:
        """
        加载并池化多只股票的数据

        参数:
            symbol_list: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            target_period: 目标预测周期

        返回:
            (pooled_df, total_samples, successful_symbols)
        """
        if self.verbose:
            logger.info(f"开始加载池化数据: {len(symbol_list)} 只股票")

        pooled_data = []
        successful_symbols = []
        failed_symbols = []

        for i, symbol in enumerate(symbol_list):
            try:
                # 加载原始数据
                df_raw = self.db.load_daily_data(symbol, start_date, end_date)

                if len(df_raw) < 100:
                    if self.verbose:
                        logger.warning(f"[{i+1}/{len(symbol_list)}] {symbol}: 数据不足({len(df_raw)}条)，跳过")
                    failed_symbols.append(symbol)
                    continue

                # 计算特征
                fe = FeatureEngineer(verbose=False)
                df_features = fe.compute_all_features(df_raw, target_period=target_period)

                # 添加股票代码列
                df_features['stock_code'] = symbol

                pooled_data.append(df_features)
                successful_symbols.append(symbol)

                if self.verbose:
                    logger.info(f"[{i+1}/{len(symbol_list)}] {symbol}: {len(df_features)} 条数据")

            except Exception as e:
                if self.verbose:
                    logger.error(f"[{i+1}/{len(symbol_list)}] {symbol}: 错误 - {e}")
                failed_symbols.append(symbol)
                continue

        if len(pooled_data) == 0:
            raise ValueError("没有成功加载任何股票数据")

        # 纵向拼接
        pooled_df = pd.concat(pooled_data, axis=0, ignore_index=True)

        if self.verbose:
            logger.info(f"池化完成: 总样本 {len(pooled_df)} 条")
            logger.info(f"成功: {len(successful_symbols)} 只, 失败: {len(failed_symbols)} 只")
            if len(failed_symbols) > 0 and len(failed_symbols) <= 5:
                logger.warning(f"失败的股票: {failed_symbols}")

        return pooled_df, len(pooled_df), successful_symbols

    def prepare_pooled_training_data(
        self,
        pooled_df: pd.DataFrame,
        target_col: str,
        train_ratio: float = 0.7,
        valid_ratio: float = 0.15
    ) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, List[str]]:
        """
        准备池化训练数据（时间序列分割）

        参数:
            pooled_df: 池化后的DataFrame
            target_col: 目标列名
            train_ratio: 训练集比例
            valid_ratio: 验证集比例

        返回:
            (X_train, y_train, X_valid, y_valid, X_test, y_test, feature_cols)
        """
        # 选择特征（排除target和stock_code）
        feature_cols = [c for c in pooled_df.columns
                        if not c.startswith('target_') and c != 'stock_code']

        if self.verbose:
            logger.info(f"特征列数: {len(feature_cols)}")

        # 删除缺失值
        df_clean = pooled_df[feature_cols + [target_col]].dropna()

        if self.verbose:
            logger.info(f"清洗后样本: {len(df_clean)} 条")

        X = df_clean[feature_cols]
        y = df_clean[target_col]

        # 时间序列分割（保持顺序）
        n = len(X)
        train_end = int(n * train_ratio)
        valid_end = int(n * (train_ratio + valid_ratio))

        X_train = X.iloc[:train_end]
        y_train = y.iloc[:train_end]

        X_valid = X.iloc[train_end:valid_end]
        y_valid = y.iloc[train_end:valid_end]

        X_test = X.iloc[valid_end:]
        y_test = y.iloc[valid_end:]

        if self.verbose:
            logger.info(f"数据分割:")
            logger.info(f"  训练集: {len(X_train)} 样本 ({len(X_train)/n*100:.1f}%)")
            logger.info(f"  验证集: {len(X_valid)} 样本 ({len(X_valid)/n*100:.1f}%)")
            logger.info(f"  测试集: {len(X_test)} 样本 ({len(X_test)/n*100:.1f}%)")

        return X_train, y_train, X_valid, y_valid, X_test, y_test, feature_cols
