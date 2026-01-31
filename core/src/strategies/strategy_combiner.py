"""
策略组合器模块

将多个策略的信号组合成最终信号
"""

from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np
from loguru import logger

from .base_strategy import BaseStrategy
from .signal_generator import SignalGenerator


class StrategyCombiner:
    """
    策略组合器

    支持多种组合方法：
    - 投票法（多数决定）
    - 加权平均
    - AND逻辑（全部同意才买入）
    - OR逻辑（任意一个同意就买入）

    使用示例：
        combiner = StrategyCombiner([strategy1, strategy2, strategy3])
        combined_signals = combiner.combine(prices, features, method='vote')
    """

    def __init__(
        self,
        strategies: List[BaseStrategy],
        weights: Optional[List[float]] = None,
        names: Optional[List[str]] = None
    ):
        """
        初始化策略组合器

        Args:
            strategies: 策略列表
            weights: 权重列表（可选，默认等权重）
            names: 策略名称列表（可选）
        """
        if not strategies:
            raise ValueError("策略列表不能为空")

        self.strategies = strategies
        self.n_strategies = len(strategies)

        # 权重
        if weights is None:
            self.weights = [1.0 / self.n_strategies] * self.n_strategies
        else:
            if len(weights) != self.n_strategies:
                raise ValueError("权重数量必须与策略数量一致")
            # 归一化
            total = sum(weights)
            self.weights = [w / total for w in weights]

        # 名称
        if names is None:
            self.names = [s.name for s in strategies]
        else:
            self.names = names

        logger.info(f"初始化策略组合器: {self.n_strategies}个策略")
        for name, weight in zip(self.names, self.weights):
            logger.info(f"  {name}: {weight:.2%}")

    def generate_individual_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None
    ) -> List[pd.DataFrame]:
        """
        生成各个策略的信号

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame
            volumes: 成交量DataFrame

        Returns:
            signals_list: 信号DataFrame列表
        """
        signals_list = []

        for i, strategy in enumerate(self.strategies):
            logger.info(f"\n[{i+1}/{self.n_strategies}] 生成策略信号: {self.names[i]}")

            try:
                signals = strategy.generate_signals(
                    prices=prices,
                    features=features,
                    volumes=volumes
                )
                signals_list.append(signals)

            except Exception as e:
                logger.error(f"策略 {self.names[i]} 信号生成失败: {e}")
                # 创建空信号
                empty_signals = pd.DataFrame(
                    0,
                    index=prices.index,
                    columns=prices.columns
                )
                signals_list.append(empty_signals)

        return signals_list

    def combine(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        method: str = 'vote',
        precomputed_signals: Optional[List[pd.DataFrame]] = None
    ) -> pd.DataFrame:
        """
        组合策略信号

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame
            volumes: 成交量DataFrame
            method: 组合方法 ('vote'/'weighted'/'and'/'or')
            precomputed_signals: 预先计算的信号列表（可选）

        Returns:
            combined_signals: 组合后的信号DataFrame
        """
        logger.info(f"\n开始组合策略信号，方法: {method}")

        # 1. 获取各策略信号
        if precomputed_signals is not None:
            signals_list = precomputed_signals
        else:
            signals_list = self.generate_individual_signals(prices, features, volumes)

        # 2. 使用信号生成器组合
        response = SignalGenerator.combine_signals(
            signal_list=signals_list,
            weights=self.weights,
            method=method
        )

        # 处理Response
        if response.is_success():
            combined = response.data
            logger.success(f"✓ 策略组合完成，买入信号数: {(combined == 1).sum().sum()}")
            return combined
        else:
            logger.error(f"策略组合失败: {response.error}")
            # 返回空信号
            return pd.DataFrame(
                0,
                index=prices.index,
                columns=prices.columns
            )

    def analyze_agreement(
        self,
        signals_list: List[pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        分析策略一致性

        Args:
            signals_list: 信号列表

        Returns:
            分析结果字典
        """
        # 统计买入信号数量
        buy_counts = [
            (signals == 1).sum().sum()
            for signals in signals_list
        ]

        # 计算策略间相关性
        correlations = {}
        for i in range(self.n_strategies):
            for j in range(i + 1, self.n_strategies):
                # 展平为一维
                sig_i = signals_list[i].values.flatten()
                sig_j = signals_list[j].values.flatten()

                # 计算相关系数
                valid = ~(np.isnan(sig_i) | np.isnan(sig_j))
                if valid.sum() > 0:
                    corr = np.corrcoef(sig_i[valid], sig_j[valid])[0, 1]
                    correlations[f"{self.names[i]}-{self.names[j]}"] = corr

        # 统计重叠信号
        # 找出所有策略都同意买入的股票数量
        all_signals = np.stack([s.values for s in signals_list])
        unanimous_buy = (all_signals == 1).all(axis=0).sum()

        return {
            'buy_counts': dict(zip(self.names, buy_counts)),
            'correlations': correlations,
            'unanimous_buy': int(unanimous_buy),
            'avg_correlation': np.mean(list(correlations.values())) if correlations else 0
        }

    def update_weights(self, new_weights: List[float]):
        """
        更新策略权重

        Args:
            new_weights: 新权重列表
        """
        if len(new_weights) != self.n_strategies:
            raise ValueError("权重数量必须与策略数量一致")

        # 归一化
        total = sum(new_weights)
        self.weights = [w / total for w in new_weights]

        logger.info("更新策略权重:")
        for name, weight in zip(self.names, self.weights):
            logger.info(f"  {name}: {weight:.2%}")

    def get_strategy_info(self) -> List[Dict[str, Any]]:
        """
        获取所有策略信息

        Returns:
            策略信息列表
        """
        return [
            {
                'name': name,
                'weight': weight,
                'class': type(strategy).__name__,
                'config': strategy.config.to_dict()
            }
            for name, weight, strategy in zip(self.names, self.weights, self.strategies)
        ]


# ==================== 使用示例 ====================

if __name__ == "__main__":
    from .momentum_strategy import MomentumStrategy
    from .mean_reversion_strategy import MeanReversionStrategy

    logger.info("策略组合器测试\n")
    logger.info("=" * 60)

    # 创建测试数据
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    stocks = [f'{i:06d}' for i in range(600000, 600005)]

    price_data = {}
    for stock in stocks:
        base_price = 10.0
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    logger.info("创建策略:")

    # 1. 创建多个策略
    mom_strategy = MomentumStrategy('MOM10', {
        'lookback_period': 10,
        'top_n': 2,
        'holding_period': 5
    })

    mr_strategy = MeanReversionStrategy('MR10', {
        'lookback_period': 10,
        'z_score_threshold': -1.5,
        'top_n': 2,
        'holding_period': 5
    })

    logger.info(f"  策略1: {mom_strategy}")
    logger.info(f"  策略2: {mr_strategy}")

    # 2. 创建组合器
    logger.info("\n创建组合器:")
    combiner = StrategyCombiner(
        strategies=[mom_strategy, mr_strategy],
        weights=[0.6, 0.4]
    )

    # 3. 组合信号
    logger.info("\n组合信号:")
    combined = combiner.combine(
        prices=prices_df,
        method='weighted'
    )

    logger.info(f"  组合信号形状: {combined.shape}")
    logger.info(f"  买入信号数: {(combined == 1).sum().sum()}")

    # 4. 分析一致性
    logger.info("\n分析策略一致性:")
    signals_list = combiner.generate_individual_signals(prices_df)
    analysis = combiner.analyze_agreement(signals_list)

    logger.info(f"  各策略买入信号数: {analysis['buy_counts']}")
    logger.info(f"  策略相关性: {analysis['correlations']}")
    logger.info(f"  所有策略一致买入: {analysis['unanimous_buy']} 次")

    logger.success("\n✓ 策略组合器测试完成")
