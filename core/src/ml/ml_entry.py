"""
ML入场策略
对齐文档: core/docs/ml/README.md (阶段3)

功能:
- 使用训练好的模型生成交易信号
- 支持做多/做空双向交易
- 基于置信度和夏普比率的权重计算
- 灵活的信号筛选策略

版本: v1.0.0
创建时间: 2026-02-08
"""
from typing import List, Dict, Optional
import pandas as pd
import numpy as np

from src.ml.trained_model import TrainedModel


class MLEntry:
    """
    机器学习入场策略

    工作流程:
    1. 模型预测 → expected_return + confidence
    2. 筛选做多候选 (expected_return > 0 & confidence > threshold)
    3. 筛选做空候选 (expected_return < 0 & confidence > threshold)
    4. 计算权重 (sharpe × confidence)
    5. 归一化权重

    使用示例:
        >>> strategy = MLEntry(
        ...     model_path='models/ml_model.pkl',
        ...     confidence_threshold=0.7,
        ...     top_long=20,
        ...     top_short=10
        ... )
        >>> signals = strategy.generate_signals(
        ...     stock_pool=['600000.SH', '000001.SZ'],
        ...     market_data=data,
        ...     date='2024-01-15'
        ... )
        >>> # 返回格式:
        >>> # {
        >>> #     '600000.SH': {'action': 'long', 'weight': 0.15},
        >>> #     '000001.SZ': {'action': 'short', 'weight': 0.10}
        >>> # }
    """

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.7,
        top_long: int = 20,
        top_short: int = 10,
        enable_short: bool = False,
        min_expected_return: float = 0.0
    ):
        """
        初始化

        Args:
            model_path: 模型路径 (pkl文件)
            confidence_threshold: 置信度阈值 (0-1), 低于该值的信号会被过滤
            top_long: 做多股票数量
            top_short: 做空股票数量
            enable_short: 是否启用做空 (默认False)
            min_expected_return: 最小预期收益率阈值 (默认0.0)

        Raises:
            FileNotFoundError: 如果模型文件不存在
            ValueError: 如果参数值无效
        """
        # 加载模型
        self.model: TrainedModel = TrainedModel.load(model_path)

        # 验证参数
        if not 0 <= confidence_threshold <= 1:
            raise ValueError(f"confidence_threshold must be between 0 and 1, got {confidence_threshold}")

        if top_long < 0:
            raise ValueError(f"top_long must be non-negative, got {top_long}")

        if top_short < 0:
            raise ValueError(f"top_short must be non-negative, got {top_short}")

        # 设置参数
        self.confidence_threshold = confidence_threshold
        self.top_long = top_long
        self.top_short = top_short
        self.enable_short = enable_short
        self.min_expected_return = min_expected_return

    def generate_signals(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> Dict[str, Dict]:
        """
        生成入场信号

        Args:
            stock_pool: 股票池 (待选股票列表)
            market_data: 市场数据 (包含OHLCV)
            date: 交易日期 (格式: 'YYYY-MM-DD')

        Returns:
            Dict[str, Dict]: 交易信号字典
                {
                    'stock_code': {
                        'action': 'long' or 'short',
                        'weight': 0.xx,
                        'expected_return': 0.xx,
                        'confidence': 0.xx
                    }
                }

        Raises:
            ValueError: 如果stock_pool为空或数据不足
        """
        if not stock_pool:
            raise ValueError("stock_pool cannot be empty")

        # 1. 模型预测
        predictions = self.model.predict(stock_pool, market_data, date)

        if len(predictions) == 0:
            return {}

        # 2. 筛选做多候选
        long_candidates = self._filter_long_candidates(predictions)

        # 3. 筛选做空候选
        short_candidates = self._filter_short_candidates(predictions)

        # 4. 合并信号
        signals = self._merge_signals(long_candidates, short_candidates)

        # 5. 归一化权重
        signals = self._normalize_weights(signals)

        return signals

    def _filter_long_candidates(
        self,
        predictions: pd.DataFrame
    ) -> pd.DataFrame:
        """
        筛选做多候选股票

        Args:
            predictions: 模型预测结果 (columns: expected_return, volatility, confidence)

        Returns:
            pd.DataFrame: 做多候选 (按权重降序排列)
        """
        # 筛选条件
        mask = (
            (predictions['expected_return'] > self.min_expected_return) &
            (predictions['confidence'] > self.confidence_threshold) &
            (predictions['volatility'] > 0)  # 避免除零
        )

        candidates = predictions[mask].copy()

        if len(candidates) == 0:
            return pd.DataFrame()

        # 计算夏普比率
        candidates['sharpe'] = (
            candidates['expected_return'] / candidates['volatility']
        )

        # 计算权重 (sharpe × confidence)
        candidates['weight'] = (
            candidates['sharpe'] * candidates['confidence']
        )

        # 取Top N
        candidates = candidates.nlargest(self.top_long, 'weight')

        return candidates

    def _filter_short_candidates(
        self,
        predictions: pd.DataFrame
    ) -> pd.DataFrame:
        """
        筛选做空候选股票

        Args:
            predictions: 模型预测结果

        Returns:
            pd.DataFrame: 做空候选 (按权重降序排列)
        """
        if not self.enable_short or self.top_short == 0:
            return pd.DataFrame()

        # 筛选条件
        mask = (
            (predictions['expected_return'] < -self.min_expected_return) &
            (predictions['confidence'] > self.confidence_threshold) &
            (predictions['volatility'] > 0)
        )

        candidates = predictions[mask].copy()

        if len(candidates) == 0:
            return pd.DataFrame()

        # 计算夏普比率 (使用绝对值)
        candidates['sharpe'] = (
            abs(candidates['expected_return']) / candidates['volatility']
        )

        # 计算权重
        candidates['weight'] = (
            candidates['sharpe'] * candidates['confidence']
        )

        # 取Top N
        candidates = candidates.nlargest(self.top_short, 'weight')

        return candidates

    def _merge_signals(
        self,
        long_candidates: pd.DataFrame,
        short_candidates: pd.DataFrame
    ) -> Dict[str, Dict]:
        """
        合并做多和做空信号

        Args:
            long_candidates: 做多候选
            short_candidates: 做空候选

        Returns:
            Dict[str, Dict]: 合并后的信号
        """
        signals = {}

        # 添加做多信号
        for stock, row in long_candidates.iterrows():
            signals[stock] = {
                'action': 'long',
                'weight': row['weight'],
                'expected_return': row['expected_return'],
                'confidence': row['confidence']
            }

        # 添加做空信号
        for stock, row in short_candidates.iterrows():
            signals[stock] = {
                'action': 'short',
                'weight': row['weight'],
                'expected_return': row['expected_return'],
                'confidence': row['confidence']
            }

        return signals

    def _normalize_weights(
        self,
        signals: Dict[str, Dict]
    ) -> Dict[str, Dict]:
        """
        归一化权重 (使所有权重之和为1)

        Args:
            signals: 原始信号

        Returns:
            Dict[str, Dict]: 归一化后的信号
        """
        if not signals:
            return signals

        # 计算总权重
        total_weight = sum(s['weight'] for s in signals.values())

        if total_weight == 0 or not np.isfinite(total_weight):
            # 如果总权重为0或无效,均分权重
            equal_weight = 1.0 / len(signals)
            for stock in signals:
                signals[stock]['weight'] = equal_weight
        else:
            # 归一化
            for stock in signals:
                signals[stock]['weight'] /= total_weight

        return signals

    def get_top_stocks(
        self,
        stock_pool: List[str],
        market_data: pd.DataFrame,
        date: str,
        top_n: int = 10,
        action: str = 'long'
    ) -> List[str]:
        """
        获取Top N股票列表 (辅助方法)

        Args:
            stock_pool: 股票池
            market_data: 市场数据
            date: 交易日期
            top_n: 返回数量
            action: 'long' 或 'short'

        Returns:
            List[str]: 股票代码列表 (按权重降序)

        Raises:
            ValueError: 如果action参数无效
        """
        if action not in ['long', 'short']:
            raise ValueError(f"action must be 'long' or 'short', got {action}")

        signals = self.generate_signals(stock_pool, market_data, date)

        # 筛选指定action的股票
        filtered = {
            stock: info
            for stock, info in signals.items()
            if info['action'] == action
        }

        # 按权重排序
        sorted_stocks = sorted(
            filtered.items(),
            key=lambda x: x[1]['weight'],
            reverse=True
        )

        # 返回Top N股票代码
        return [stock for stock, _ in sorted_stocks[:top_n]]

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"MLEntry("
            f"model={self.model.config.model_type}, "
            f"confidence_threshold={self.confidence_threshold}, "
            f"top_long={self.top_long}, "
            f"top_short={self.top_short}, "
            f"enable_short={self.enable_short}"
            f")"
        )
