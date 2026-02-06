"""
LightGBM 股票排序模型训练工具

本工具用于训练 LightGBM 排序模型，用于 MLSelector 的 lightgbm_ranker 模式。

核心功能：
1. 准备训练数据（特征计算 + 标签构建）
2. 训练 LightGBM Ranker 模型
3. 模型评估和保存
4. 超参数调优

作者: Core MLSelector Team
日期: 2026-02-06
版本: v1.0
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


class StockRankerTrainer:
    """
    LightGBM 股票排序模型训练器

    主要功能：
    1. 特征工程：计算技术指标特征
    2. 标签构建：基于未来收益率构建排序标签
    3. 模型训练：使用 LightGBM Ranker
    4. 模型评估：NDCG、MAP 等排序指标
    """

    def __init__(
        self,
        feature_names: Optional[List[str]] = None,
        label_forward_days: int = 5,
        label_threshold: float = 0.02
    ):
        """
        初始化训练器

        Args:
            feature_names: 特征名称列表（默认使用 MLSelector 默认特征）
            label_forward_days: 未来收益率计算周期（天）
            label_threshold: 收益率阈值（用于分档）
        """
        self.feature_names = feature_names or self._get_default_features()
        self.label_forward_days = label_forward_days
        self.label_threshold = label_threshold

        logger.info(
            f"StockRankerTrainer 初始化: "
            f"features={len(self.feature_names)}, "
            f"forward_days={label_forward_days}, "
            f"threshold={label_threshold}"
        )

    def prepare_training_data(
        self,
        prices: pd.DataFrame,
        start_date: str,
        end_date: str,
        sample_freq: str = 'W'
    ) -> Tuple[pd.DataFrame, pd.Series, np.ndarray]:
        """
        准备训练数据

        Args:
            prices: 价格数据 DataFrame(index=日期, columns=股票代码)
            start_date: 训练数据起始日期
            end_date: 训练数据结束日期
            sample_freq: 采样频率（'D'=日, 'W'=周, 'M'=月）

        Returns:
            (X, y, groups):
                - X: 特征矩阵 DataFrame
                - y: 标签序列（相关性评分）
                - groups: 分组信息（每个日期的样本数量）

        标签构建策略：
            未来N日收益率 -> 分档评分（0-4分）
            - 评分 4: 收益率 > 2 * threshold (强买)
            - 评分 3: 收益率 > threshold
            - 评分 2: 收益率 > 0
            - 评分 1: 收益率 > -threshold
            - 评分 0: 收益率 <= -threshold (强卖)
        """
        logger.info(f"准备训练数据: {start_date} ~ {end_date}")

        # 筛选日期范围
        prices_filtered = prices.loc[start_date:end_date]

        # 采样日期
        sample_dates = self._get_sample_dates(
            prices_filtered.index, sample_freq
        )
        logger.info(f"采样日期数: {len(sample_dates)}")

        # 准备数据
        feature_list = []
        label_list = []
        groups = []

        for date in sample_dates:
            try:
                # 计算特征
                features = self._calculate_features_at_date(
                    date, prices
                )

                # 计算标签
                labels = self._calculate_labels_at_date(
                    date, prices
                )

                # 合并特征和标签
                merged = features.join(labels, how='inner')
                merged = merged.dropna()

                if len(merged) == 0:
                    continue

                # 添加到列表
                feature_list.append(merged[self.feature_names])
                label_list.append(merged['label'])
                groups.append(len(merged))

                logger.debug(
                    f"日期 {date}: {len(merged)} 只股票, "
                    f"标签均值={merged['label'].mean():.2f}"
                )

            except Exception as e:
                logger.warning(f"日期 {date} 处理失败: {e}")
                continue

        if not feature_list:
            raise ValueError("没有成功处理的数据，请检查输入")

        # 合并所有数据
        X = pd.concat(feature_list, axis=0)
        y = pd.concat(label_list, axis=0)
        groups_array = np.array(groups)

        logger.info(
            f"训练数据准备完成: "
            f"样本数={len(X)}, 特征数={len(X.columns)}, "
            f"日期数={len(groups)}"
        )

        return X, y, groups_array

    def train_model(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        groups_train: np.ndarray,
        model_params: Optional[Dict] = None
    ):
        """
        训练 LightGBM Ranker 模型

        Args:
            X_train: 训练特征矩阵
            y_train: 训练标签
            groups_train: 训练分组信息
            model_params: 模型超参数（可选）

        Returns:
            训练好的 LightGBM 模型
        """
        try:
            import lightgbm as lgb
        except ImportError:
            raise ImportError(
                "需要安装 lightgbm: pip install lightgbm"
            )

        logger.info("开始训练 LightGBM Ranker 模型")

        # 默认参数
        default_params = {
            'objective': 'lambdarank',
            'metric': 'ndcg',
            'ndcg_eval_at': [5, 10, 20],
            'n_estimators': 100,
            'learning_rate': 0.05,
            'max_depth': 6,
            'num_leaves': 31,
            'min_child_samples': 20,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'verbose': -1
        }

        # 合并用户参数
        if model_params:
            default_params.update(model_params)

        # 创建模型
        model = lgb.LGBMRanker(**default_params)

        # 训练模型
        model.fit(
            X_train,
            y_train,
            group=groups_train,
            eval_set=[(X_train, y_train)],
            eval_group=[groups_train],
            eval_metric='ndcg',
            callbacks=[
                lgb.log_evaluation(period=10),
                lgb.early_stopping(stopping_rounds=20, verbose=False)
            ]
        )

        logger.info(
            f"模型训练完成: "
            f"最佳迭代={model.best_iteration_}, "
            f"最佳得分={model.best_score_}"
        )

        # 打印特征重要性
        self._print_feature_importance(model, X_train.columns)

        return model

    def evaluate_model(
        self,
        model,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        groups_test: np.ndarray
    ) -> Dict[str, float]:
        """
        评估模型性能

        Args:
            model: 训练好的模型
            X_test: 测试特征矩阵
            y_test: 测试标签
            groups_test: 测试分组信息

        Returns:
            评估指标字典
        """
        logger.info("评估模型性能")

        # 预测评分
        y_pred = model.predict(X_test)

        # 计算排序指标
        metrics = {}

        # NDCG
        try:
            import lightgbm as lgb
            from sklearn.metrics import ndcg_score

            # 按组计�� NDCG
            start_idx = 0
            ndcg_scores = []

            for group_size in groups_test:
                end_idx = start_idx + group_size

                y_true_group = y_test.iloc[start_idx:end_idx].values.reshape(1, -1)
                y_pred_group = y_pred[start_idx:end_idx].reshape(1, -1)

                # 计算 NDCG@10
                k = min(10, group_size)
                ndcg = ndcg_score(y_true_group, y_pred_group, k=k)
                ndcg_scores.append(ndcg)

                start_idx = end_idx

            metrics['ndcg@10'] = np.mean(ndcg_scores)

        except Exception as e:
            logger.warning(f"NDCG 计算失败: {e}")

        # 打印评估结果
        logger.info(f"模型评估结果: {metrics}")

        return metrics

    def save_model(self, model, model_path: str):
        """
        保存训练好的模型

        Args:
            model: 训练好的模型
            model_path: 模型保存路径
        """
        try:
            import joblib
            joblib.dump(model, model_path)
            logger.info(f"模型已保存: {model_path}")

        except Exception as e:
            logger.error(f"模型保存失败: {e}")
            raise

    def _calculate_features_at_date(
        self,
        date: pd.Timestamp,
        prices: pd.DataFrame
    ) -> pd.DataFrame:
        """
        计算指定日期的特征矩阵

        Args:
            date: 计算日期
            prices: 价格数据

        Returns:
            特征矩阵 DataFrame(index=股票代码, columns=特征名)
        """
        from src.strategies.three_layer.selectors.ml_selector import MLSelector

        # 创建临时 MLSelector 用于特征计算
        temp_selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'features': ','.join(self.feature_names)
        })

        # 获取有效股票
        valid_stocks = prices.loc[date].dropna().index.tolist()

        # 计算特征
        features = temp_selector._calculate_features(
            date, prices, valid_stocks
        )

        return features

    def _calculate_labels_at_date(
        self,
        date: pd.Timestamp,
        prices: pd.DataFrame
    ) -> pd.Series:
        """
        计算指定日期的标签

        标签 = 未来N日收益率的分档评分（0-4分）

        Args:
            date: 计算日期
            prices: 价格数据

        Returns:
            标签序列 Series(index=股票代码, values=评分)
        """
        # 计算未来收益率
        future_returns = prices.pct_change(self.label_forward_days).shift(
            -self.label_forward_days
        )

        try:
            returns_at_date = future_returns.loc[date]
        except KeyError:
            return pd.Series(dtype=float)

        # 分档评分
        labels = pd.Series(index=returns_at_date.index, dtype=float, name='label')

        for stock in returns_at_date.index:
            ret = returns_at_date[stock]

            if pd.isna(ret):
                labels[stock] = np.nan
                continue

            # 5档评分
            if ret > 2 * self.label_threshold:
                labels[stock] = 4  # 强买
            elif ret > self.label_threshold:
                labels[stock] = 3  # 买入
            elif ret > 0:
                labels[stock] = 2  # 中性偏多
            elif ret > -self.label_threshold:
                labels[stock] = 1  # 中性偏空
            else:
                labels[stock] = 0  # 卖出

        return labels

    def _get_sample_dates(
        self,
        all_dates: pd.DatetimeIndex,
        freq: str
    ) -> pd.DatetimeIndex:
        """
        获取采样日期

        Args:
            all_dates: 所有日期
            freq: 采样频率（'D', 'W', 'M'）

        Returns:
            采样后的日期列表
        """
        if freq == 'D':
            return all_dates
        elif freq == 'W':
            # 每周采样（周五）
            return all_dates[all_dates.dayofweek == 4]
        elif freq == 'M':
            # 每月采样（月末）
            # 注意：pandas 2.2+ 'M' 已弃用，使用 'ME' (Month End)
            return all_dates.to_series().resample('ME').last().index
        else:
            logger.warning(f"未知采样频率: {freq}，使用日频")
            return all_dates

    def _print_feature_importance(self, model, feature_names: pd.Index):
        """打印特征重要性"""
        importance = model.feature_importances_
        feature_importance = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)

        logger.info(f"\n特征重要性 Top 10:\n{feature_importance.head(10)}")

    def _get_default_features(self) -> List[str]:
        """获取默认特征集（与 MLSelector 一致）"""
        return [
            # 动量类
            'momentum_5d',
            'momentum_10d',
            'momentum_20d',
            'momentum_60d',

            # 技术指标
            'rsi_14d',
            'rsi_28d',

            # 波动率
            'volatility_20d',
            'volatility_60d',

            # 均线偏离度
            'ma_cross_20d',
            'ma_cross_60d',

            # ATR
            'atr_14d',
        ]


def main():
    """
    主函数：完整的模型训练流程示例

    使用方法：
        python train_stock_ranker_lgbm.py
    """
    import argparse

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='训练 LightGBM 股票排序模型')
    parser.add_argument(
        '--data-path',
        type=str,
        required=True,
        help='价格数据文件路径（CSV格式）'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default='2020-01-01',
        help='训练数据起始日期'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        default='2023-12-31',
        help='训练数据结束日期'
    )
    parser.add_argument(
        '--test-start-date',
        type=str,
        default='2024-01-01',
        help='测试数据起始日期'
    )
    parser.add_argument(
        '--test-end-date',
        type=str,
        default='2024-06-30',
        help='测试数据结束日期'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='./models/stock_ranker_lgbm.pkl',
        help='模型输出路径'
    )
    parser.add_argument(
        '--sample-freq',
        type=str,
        default='W',
        choices=['D', 'W', 'M'],
        help='采样频率（D=日, W=周, M=月）'
    )

    args = parser.parse_args()

    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan> - "
               "<level>{message}</level>",
        level="INFO"
    )

    try:
        # 1. 加载数据
        logger.info(f"加载数据: {args.data_path}")
        prices = pd.read_csv(args.data_path, index_col=0, parse_dates=True)
        logger.info(f"数据形状: {prices.shape}")

        # 2. 创建训练器
        trainer = StockRankerTrainer(
            label_forward_days=5,
            label_threshold=0.02
        )

        # 3. 准备训练数据
        X_train, y_train, groups_train = trainer.prepare_training_data(
            prices=prices,
            start_date=args.start_date,
            end_date=args.end_date,
            sample_freq=args.sample_freq
        )

        # 4. 准备测试数据
        X_test, y_test, groups_test = trainer.prepare_training_data(
            prices=prices,
            start_date=args.test_start_date,
            end_date=args.test_end_date,
            sample_freq=args.sample_freq
        )

        # 5. 训练模型
        model = trainer.train_model(
            X_train=X_train,
            y_train=y_train,
            groups_train=groups_train
        )

        # 6. 评估模型
        metrics = trainer.evaluate_model(
            model=model,
            X_test=X_test,
            y_test=y_test,
            groups_test=groups_test
        )

        # 7. 保存模型
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        trainer.save_model(model, str(output_path))

        logger.info("=" * 60)
        logger.info("模型训练流程完成！")
        logger.info(f"模型保存路径: {output_path}")
        logger.info(f"测试集性能: {metrics}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"训练流程失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
