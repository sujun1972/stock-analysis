"""
多因子策略模块

结合多个Alpha因子进行选股
"""

from typing import Optional, Dict, Any, List
import pandas as pd
import numpy as np
from loguru import logger

from core.strategies.base_strategy import BaseStrategy
from core.strategies.signal_generator import SignalGenerator


class MultiFactorStrategy(BaseStrategy):
    """
    多因子策略

    核心逻辑:
    - 选择多个有效的Alpha因子
    - 对因子进行标准化处理
    - 加权组合得到综合评分
    - 选择评分最高的股票

    参数:
        factors: 因子列表 ['MOM20', 'REV5', 'VOLATILITY20']
        weights: 因子权重 [0.4, 0.3, 0.3]
        normalize_method: 标准化方法 ('rank'/'zscore'/'minmax')
        neutralize: 是否行业中性化(默认False)

    适用场景:
        - 所有市场环境
        - 分散单因子风险
        - 提高稳定性

    优势:
        - 因子分散,风险降低
        - 可以capture多种市场特征
        - 可调整因子权重适应不同市场
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化多因子策略

        Args:
            name: 策略名称
            config: 策略配置
        """
        default_config = {
            'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
            'weights': None,  # None表示等权重
            'normalize_method': 'rank',
            'top_n': 50,
            'holding_period': 5,
            'neutralize': False,
            'min_factor_coverage': 0.8,  # 最少需要80%因子有效
        }
        default_config.update(config)

        super().__init__(name, default_config)

        self.factors = self.config.custom_params.get('factors', [])
        self.weights = self.config.custom_params.get('weights')
        self.normalize_method = self.config.custom_params.get('normalize_method', 'rank')
        self.neutralize = self.config.custom_params.get('neutralize', False)
        self.min_factor_coverage = self.config.custom_params.get('min_factor_coverage', 0.8)

        # 如果没有指定权重,使用等权重
        if self.weights is None:
            self.weights = [1.0 / len(self.factors)] * len(self.factors)

        if len(self.weights) != len(self.factors):
            raise ValueError("因子权重数量必须与因子数量一致")

        logger.info(f"多因子策略: {len(self.factors)}个因子")
        for factor, weight in zip(self.factors, self.weights):
            logger.info(f"  {factor}: {weight:.2%}")

    def normalize_factor(
        self,
        factor: pd.Series,
        method: Optional[str] = None
    ) -> pd.Series:
        """
        标准化因子

        Args:
            factor: 因子Series
            method: 标准化方法

        Returns:
            normalized: 标准化后的因子
        """
        if method is None:
            method = self.normalize_method

        if method == 'rank':
            # 排名百分位(0-1)
            normalized = factor.rank(pct=True)

        elif method == 'zscore':
            # Z-score标准化
            mean = factor.mean()
            std = factor.std()
            normalized = (factor - mean) / (std + 1e-8)

        elif method == 'minmax':
            # Min-Max归一化(0-1)
            min_val = factor.min()
            max_val = factor.max()
            normalized = (factor - min_val) / (max_val - min_val + 1e-8)

        else:
            raise ValueError(f"不支持的标准化方法: {method}")

        return normalized

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        计算综合评分

        评分 = Σ(权重i × 标准化因子i)

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame(必需)
            date: 指定日期

        Returns:
            scores: 综合评分Series
        """
        if features is None:
            raise ValueError("多因子策略需要特征DataFrame")

        if date is None:
            date = features.index[-1]

        # 检查日期是否存在
        if date not in features.index:
            logger.warning(f"日期 {date} 不在特征DataFrame中")
            return pd.Series(dtype=float)

        # 提取各因子值
        factor_values = {}
        for factor in self.factors:
            # 支持MultiIndex列 (factor, stock)
            if isinstance(features.columns, pd.MultiIndex):
                # MultiIndex: 选择该因子的所有股票
                if factor in features.columns.get_level_values(0):
                    factor_values[factor] = features.loc[date, factor]
                else:
                    logger.warning(f"因子 {factor} 不在特征DataFrame中")
                    continue
            else:
                # 简单列索引
                if factor not in features.columns:
                    logger.warning(f"因子 {factor} 不在特征DataFrame中")
                    continue
                factor_values[factor] = features.loc[date, factor]

        if not factor_values:
            logger.error("没有可用的因子")
            return pd.Series(dtype=float)

        # 标准化
        normalized_factors = {}
        for factor_name, factor_series in factor_values.items():
            try:
                normalized = self.normalize_factor(factor_series.dropna())
                normalized_factors[factor_name] = normalized
            except Exception as e:
                logger.warning(f"标准化因子 {factor_name} 失败: {e}")
                continue

        if not normalized_factors:
            logger.error("没有成功标准化的因子")
            return pd.Series(dtype=float)

        # 加权组合
        # 确定股票列表(从第一个有效因子中获取)
        if normalized_factors:
            first_factor = list(normalized_factors.values())[0]
            stock_index = first_factor.index
        else:
            # 从features中提取股票列表
            if isinstance(features.columns, pd.MultiIndex):
                stock_index = features.columns.get_level_values(1).unique()
            else:
                stock_index = features.columns

        composite_score = pd.Series(0.0, index=stock_index)
        total_weight = 0.0

        for i, factor_name in enumerate(self.factors):
            if factor_name in normalized_factors:
                weight = self.weights[i]
                composite_score += normalized_factors[factor_name] * weight
                total_weight += weight

        # 归一化权重
        if total_weight > 0:
            composite_score = composite_score / total_weight

        # 过滤缺失值过多的股票
        factor_count = pd.DataFrame(normalized_factors).notna().sum(axis=1)
        min_factors = int(len(self.factors) * self.min_factor_coverage)
        valid_stocks = factor_count[factor_count >= min_factors].index
        composite_score[~composite_score.index.isin(valid_stocks)] = np.nan

        return composite_score

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame(必需)
            volumes: 成交量DataFrame
            **kwargs: 其他参数

        Returns:
            signals: 信号DataFrame
        """
        logger.info(f"\n生成多因子策略信号...")

        if features is None:
            raise ValueError("多因子策略需要特征DataFrame")

        # 1. 计算每日综合评分
        scores_dict = {}
        for date in features.index:
            try:
                scores = self.calculate_scores(prices, features, date)
                scores_dict[date] = scores
            except Exception as e:
                logger.warning(f"计算日期 {date} 评分失败: {e}")
                continue

        if not scores_dict:
            logger.error("没有成功计算的评分")
            return pd.DataFrame(0, index=prices.index, columns=prices.columns)

        # 转换为DataFrame
        scores_df = pd.DataFrame(scores_dict).T

        # 2. 生成排名信号(返回Response对象)
        signals_response = SignalGenerator.generate_rank_signals(
            scores=scores_df,
            top_n=self.config.top_n
        )

        # 检查信号生成结果并提取数据
        if not signals_response.is_success():
            raise ValueError(f"信号生成失败: {signals_response.error}")
        signals = signals_response.data

        # 3. 对齐到价格DataFrame的索引
        signals = signals.reindex(prices.index, fill_value=0)

        # 4. 过滤
        if volumes is not None:
            for date in signals.index:
                try:
                    valid_stocks = self.filter_stocks(prices, volumes, date)
                    invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
                    signals.loc[date, invalid_stocks] = 0
                except:
                    pass

        # 5. 验证
        signals = self.validate_signals(signals)

        logger.info(f"信号生成完成,总买入信号数: {(signals == 1).sum().sum()}")

        return signals

    def get_factor_weights(self) -> Dict[str, float]:
        """
        获取因子权重

        Returns:
            {factor_name: weight} 字典
        """
        return dict(zip(self.factors, self.weights))

    def update_weights(self, new_weights: List[float]):
        """
        更新因子权重

        Args:
            new_weights: 新权重列表
        """
        if len(new_weights) != len(self.factors):
            raise ValueError("权重数量必须与因子数量一致")

        self.weights = new_weights
        logger.info(f"更新因子权重:")
        for factor, weight in zip(self.factors, self.weights):
            logger.info(f"  {factor}: {weight:.2%}")

    def get_metadata(self) -> Dict[str, Any]:
        """获取策略元信息"""
        return {
            'name': self.name,
            'class_name': 'MultiFactor',
            'category': 'factor',
            'description': '综合多个因子进行选股',
            'parameters': {
                'factors': self.factors,
                'weights': self.weights,
                'normalize_method': self.normalize_method,
                'top_n': self.config.top_n,
                'holding_period': self.config.holding_period,
            },
            'risk_level': 'low',
        }
