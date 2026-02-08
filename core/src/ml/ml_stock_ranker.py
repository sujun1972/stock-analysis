"""
ML股票评分排名工具
对齐文档: core/docs/ml/mlstockranker.md

功能:
- 从大股票池中筛选高潜力股票
- 基于ML模型预测进行综合评分
- 支持灵活的评分策略和筛选条件

版本: v1.0.0
创建时间: 2026-02-08
"""
from typing import List, Dict, Optional, Literal
import pandas as pd
import numpy as np

from src.ml.trained_model import TrainedModel


ScoringMethod = Literal['simple', 'sharpe', 'risk_adjusted']


class MLStockRanker:
    """
    ML股票评分排名工具

    用于从大股票池中筛选高潜力股票。

    评分方法:
    - 'simple': expected_return × confidence
    - 'sharpe': (expected_return / volatility) × confidence
    - 'risk_adjusted': expected_return × confidence / volatility

    使用示例:
        >>> ranker = MLStockRanker(
        ...     model_path='models/ranker.pkl',
        ...     scoring_method='sharpe'
        ... )
        >>> rankings = ranker.rank(
        ...     stock_pool=all_a_stocks,  # 3000+
        ...     market_data=data,
        ...     date='2024-01-01',
        ...     return_top_n=100
        ... )
        >>> # 返回格式: {'600000.SH': 0.85, '000001.SZ': 0.78, ...}
    """

    def __init__(
        self,
        model_path: str,
        scoring_method: ScoringMethod = 'simple',
        min_confidence: float = 0.0,
        min_expected_return: float = 0.0
    ):
        """
        初始化

        Args:
            model_path: 模型路径 (pkl文件)
            scoring_method: 评分方法 ('simple', 'sharpe', 'risk_adjusted')
            min_confidence: 最小置信度阈值 (0-1), 低于该值的股票会被过滤
            min_expected_return: 最小预期收益率阈值

        Raises:
            FileNotFoundError: 如果模型文件不存在
            ValueError: 如果参数值无效
        """
        # 加载模型
        self.model: TrainedModel = TrainedModel.load(model_path)

        # 验证参数
        if scoring_method not in ['simple', 'sharpe', 'risk_adjusted']:
            raise ValueError(
                f"scoring_method must be 'simple', 'sharpe', or 'risk_adjusted', "
                f"got {scoring_method}"
            )

        if not 0 <= min_confidence <= 1:
            raise ValueError(
                f"min_confidence must be between 0 and 1, got {min_confidence}"
            )

        # 设置参数
        self.scoring_method = scoring_method
        self.min_confidence = min_confidence
        self.min_expected_return = min_expected_return

    def rank(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        date: str,
        return_top_n: Optional[int] = 100,
        descending: bool = True
    ) -> Dict[str, float]:
        """
        对股票池进行评分排名

        Args:
            stock_pool: 股票池 (待评分股票列表)
            market_data: 市场数据 (包含OHLCV)
            date: 评分日期 (格式: 'YYYY-MM-DD')
            return_top_n: 返回Top N股票 (None表示返回全部)
            descending: 是否降序排列 (True=从高到低)

        Returns:
            Dict[str, float]: {stock_code: score}
                评分已按照descending参数排序

        Raises:
            ValueError: 如果stock_pool为空或数据不足
        """
        if not stock_pool:
            raise ValueError("stock_pool cannot be empty")

        # 1. 模型预测
        predictions = self.model.predict(stock_pool, market_data, date)

        if len(predictions) == 0:
            return {}

        # 2. 过滤低质量股票
        predictions = self._filter_stocks(predictions)

        if len(predictions) == 0:
            return {}

        # 3. 计算综合评分
        predictions['score'] = self._calculate_scores(predictions)

        # 4. 排序
        predictions = predictions.sort_values('score', ascending=not descending)

        # 5. 返回Top N
        if return_top_n is not None:
            predictions = predictions.head(return_top_n)

        return predictions['score'].to_dict()

    def rank_dataframe(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        date: str,
        return_top_n: Optional[int] = 100,
        descending: bool = True
    ) -> pd.DataFrame:
        """
        对股票池进行评分排名 (返回详细信息)

        Args:
            stock_pool: 股票池
            market_data: 市场数据
            date: 评分日期
            return_top_n: 返回Top N股票 (None表示返回全部)
            descending: 是否降序排列

        Returns:
            pd.DataFrame: 排名结果
                columns: ['score', 'expected_return', 'confidence', 'volatility']
                index: stock_code (按评分排序)

        Raises:
            ValueError: 如果stock_pool为空或数据不足
        """
        if not stock_pool:
            raise ValueError("stock_pool cannot be empty")

        # 1. 模型预测
        predictions = self.model.predict(stock_pool, market_data, date)

        if len(predictions) == 0:
            return pd.DataFrame()

        # 2. 过滤低质量股票
        predictions = self._filter_stocks(predictions)

        if len(predictions) == 0:
            return pd.DataFrame()

        # 3. 计算综合评分
        predictions['score'] = self._calculate_scores(predictions)

        # 4. 排序
        predictions = predictions.sort_values('score', ascending=not descending)

        # 5. 返回Top N
        if return_top_n is not None:
            predictions = predictions.head(return_top_n)

        # 6. 选择返回列
        return predictions[['score', 'expected_return', 'confidence', 'volatility']]

    def _filter_stocks(self, predictions: pd.DataFrame) -> pd.DataFrame:
        """
        过滤低质量股票

        Args:
            predictions: 模型预测结果

        Returns:
            pd.DataFrame: 过滤后的预测结果
        """
        mask = (
            (predictions['expected_return'] >= self.min_expected_return) &
            (predictions['confidence'] >= self.min_confidence) &
            (predictions['volatility'] > 0)  # 避免除零
        )
        return predictions[mask].copy()

    def _calculate_scores(self, predictions: pd.DataFrame) -> pd.Series:
        """
        计算综合评分

        Args:
            predictions: 模型预测结果
                columns: ['expected_return', 'volatility', 'confidence']

        Returns:
            pd.Series: 评分序列
        """
        if self.scoring_method == 'simple':
            # 简单评分: expected_return × confidence
            scores = (
                predictions['expected_return'] *
                predictions['confidence']
            )

        elif self.scoring_method == 'sharpe':
            # 夏普评分: (expected_return / volatility) × confidence
            scores = (
                (predictions['expected_return'] / predictions['volatility']) *
                predictions['confidence']
            )

        elif self.scoring_method == 'risk_adjusted':
            # 风险调整评分: expected_return × confidence / volatility
            scores = (
                predictions['expected_return'] *
                predictions['confidence'] /
                predictions['volatility']
            )

        else:
            raise ValueError(f"Unknown scoring_method: {self.scoring_method}")

        # 处理无效值
        scores = scores.replace([np.inf, -np.inf], np.nan).fillna(0)

        return scores

    def batch_rank(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        dates: List[str],
        return_top_n: Optional[int] = 100
    ) -> Dict[str, Dict[str, float]]:
        """
        批量评分 (多个日期)

        Args:
            stock_pool: 股票池
            market_data: 市场数据
            dates: 日期列表
            return_top_n: 每个日期返回Top N股票

        Returns:
            Dict[str, Dict[str, float]]: {date: {stock_code: score}}

        Example:
            >>> results = ranker.batch_rank(
            ...     stock_pool=['600000.SH', '000001.SZ'],
            ...     market_data=data,
            ...     dates=['2024-01-01', '2024-01-02', '2024-01-03'],
            ...     return_top_n=10
            ... )
            >>> results['2024-01-01']
            >>> # {'600000.SH': 0.85, '000001.SZ': 0.78}
        """
        results = {}

        for date in dates:
            try:
                rankings = self.rank(
                    stock_pool=stock_pool,
                    market_data=market_data,
                    date=date,
                    return_top_n=return_top_n
                )
                results[date] = rankings
            except Exception as e:
                # 记录错误但继续处理其他日期
                print(f"Warning: Failed to rank stocks for {date}: {e}")
                results[date] = {}

        return results

    def get_top_stocks(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        date: str,
        top_n: int = 10
    ) -> List[str]:
        """
        获取Top N股票列表 (辅助方法)

        Args:
            stock_pool: 股票池
            market_data: 市场数据
            date: 评分日期
            top_n: 返回数量

        Returns:
            List[str]: 股票代码列表 (按评分降序)
        """
        rankings = self.rank(
            stock_pool=stock_pool,
            market_data=market_data,
            date=date,
            return_top_n=top_n,
            descending=True
        )

        return list(rankings.keys())

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"MLStockRanker("
            f"model={self.model.config.model_type}, "
            f"scoring_method='{self.scoring_method}', "
            f"min_confidence={self.min_confidence}, "
            f"min_expected_return={self.min_expected_return}"
            f")"
        )
