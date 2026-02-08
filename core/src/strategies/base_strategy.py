"""
策略基类模块

定义所有交易策略必须遵循的接口和通用功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from loguru import logger


@dataclass
class StrategyConfig:
    """
    策略配置数据类

    通用配置参数，所有策略都可以使用
    """
    # 基础参数
    name: str = "BaseStrategy"
    description: str = ""

    # 选股参数
    top_n: int = 50  # 每期选择前N只股票
    min_stocks: int = 10  # 最少持仓股票数
    max_stocks: int = 100  # 最多持仓股票数

    # 持仓参数
    holding_period: int = 5  # 最短持仓期（天）
    rebalance_freq: str = 'W'  # 调仓频率 ('D'=日, 'W'=周, 'M'=月)

    # 过滤参数
    min_price: float = 1.0  # 最低价格（过滤ST股票）
    max_price: float = 1000.0  # 最高价格
    min_volume: float = 1000000  # 最小成交量（防止流动性不足）

    # 风控参数
    max_position_pct: float = 0.2  # 单只股票最大仓位比例
    stop_loss_pct: float = -0.1  # 止损比例（-10%）
    take_profit_pct: float = 0.3  # 止盈比例（+30%）

    # 自定义参数（策略特有）
    custom_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'description': self.description,
            'top_n': self.top_n,
            'holding_period': self.holding_period,
            'rebalance_freq': self.rebalance_freq,
            **self.custom_params
        }


class BaseStrategy(ABC):
    """
    交易策略基类

    所有策略必须实现的方法：
    - generate_signals(): 生成交易信号
    - calculate_scores(): 计算股票评分

    可选方法：
    - filter_stocks(): 过滤不符合条件的股票
    - validate_signals(): 验证信号有效性
    - get_position_weights(): 计算持仓权重
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化策略

        Args:
            name: 策略名称
            config: 策略配置字典
        """
        self.name = name
        self.config = self._parse_config(config)
        self._signal_cache = {}  # 信号缓存

        # 元信息 (由加载器设置)
        self._config_id: Optional[int] = None         # 配置ID (方案1)
        self._strategy_id: Optional[int] = None       # AI策略ID (方案2)
        self._strategy_type: str = 'predefined'       # 'predefined' | 'configured' | 'dynamic'
        self._config_version: Optional[int] = None    # 配置版本
        self._code_hash: Optional[str] = None         # 代码哈希 (方案2)
        self._risk_level: str = 'safe'                # 风险等级

        logger.info(f"初始化策略: {self.name}")
        logger.debug(f"策略配置: {self.config.to_dict()}")

    def _parse_config(self, config: Dict[str, Any]) -> StrategyConfig:
        """
        解析配置字典为 StrategyConfig

        Args:
            config: 配置字典

        Returns:
            StrategyConfig 实例
        """
        # 提取通用参数
        common_params = {
            'name': config.get('name', self.__class__.__name__),
            'description': config.get('description', ''),
            'top_n': config.get('top_n', 50),
            'min_stocks': config.get('min_stocks', 10),
            'max_stocks': config.get('max_stocks', 100),
            'holding_period': config.get('holding_period', 5),
            'rebalance_freq': config.get('rebalance_freq', 'W'),
            'min_price': config.get('min_price', 1.0),
            'max_price': config.get('max_price', 1000.0),
            'min_volume': config.get('min_volume', 1000000),
            'max_position_pct': config.get('max_position_pct', 0.2),
            'stop_loss_pct': config.get('stop_loss_pct', -0.1),
            'take_profit_pct': config.get('take_profit_pct', 0.3),
        }

        # 提取自定义参数
        custom_params = {
            k: v for k, v in config.items()
            if k not in common_params
        }
        common_params['custom_params'] = custom_params

        return StrategyConfig(**common_params)

    @abstractmethod
    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        生成交易信号（必须实现）

        Args:
            prices: 价格DataFrame (index=date, columns=stock_codes, values=close_price)
            features: 特征DataFrame (可选)
            **kwargs: 其他参数

        Returns:
            signals: 信号DataFrame (index=date, columns=stock_codes)
                值: 1 = 买入, 0 = 持有, -1 = 卖出
        """
        pass

    @abstractmethod
    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        计算股票评分（必须实现）

        用于排序选股，分数越高越好

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame
            date: 指定日期（None表示最新日期）

        Returns:
            scores: 股票评分Series (index=stock_codes, values=scores)
        """
        pass

    def filter_stocks(
        self,
        prices: pd.DataFrame,
        volumes: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> List[str]:
        """
        过滤股票（可选实现）

        过滤掉不符合条件的股票：
        - 价格过低/过高
        - 成交量过小
        - 停牌股票

        Args:
            prices: 价格DataFrame
            volumes: 成交量DataFrame
            date: 指定日期

        Returns:
            符合条件的股票代码列表
        """
        if date is None:
            date = prices.index[-1]

        # 获取当日价格
        current_prices = prices.loc[date]

        # 价格过滤
        valid_stocks = current_prices[
            (current_prices >= self.config.min_price) &
            (current_prices <= self.config.max_price) &
            (current_prices.notna())
        ].index.tolist()

        # 成交量过滤
        if volumes is not None and date in volumes.index:
            current_volumes = volumes.loc[date]
            valid_volumes = current_volumes[
                (current_volumes >= self.config.min_volume) &
                (current_volumes.notna())
            ].index

            # 取交集
            valid_stocks = list(set(valid_stocks) & set(valid_volumes))

        logger.debug(f"{date}: 过滤后剩余 {len(valid_stocks)} 只股票")

        return valid_stocks

    def validate_signals(self, signals: pd.DataFrame) -> pd.DataFrame:
        """
        验证信号有效性（可选实现）

        检查信号是否符合约束：
        - 信号值必须在 [-1, 0, 1]
        - 同时买入的股票数不超过 max_stocks

        Args:
            signals: 原始信号DataFrame

        Returns:
            验证后的信号DataFrame
        """
        validated = signals.copy()

        # 1. 限制信号值范围
        validated = validated.clip(-1, 1)

        # 2. 限制同时持仓数量
        for date in validated.index:
            buy_signals = validated.loc[date][validated.loc[date] == 1]

            if len(buy_signals) > self.config.max_stocks:
                # 只保留评分最高的 max_stocks 只
                logger.warning(f"{date}: 买入信号 {len(buy_signals)} 只，超过限制 {self.config.max_stocks}，进行截断")

                # 需要配合 calculate_scores 使用
                # 这里简单处理：随机保留
                keep_stocks = buy_signals.sample(n=self.config.max_stocks).index
                validated.loc[date, ~validated.columns.isin(keep_stocks)] = 0

        return validated

    def get_position_weights(
        self,
        stocks: List[str],
        scores: Optional[pd.Series] = None,
        method: str = 'equal'
    ) -> Dict[str, float]:
        """
        计算持仓权重（可选实现）

        Args:
            stocks: 股票列表
            scores: 股票评分 (可选)
            method: 权重计算方法
                - 'equal': 等权重
                - 'score': 按评分加权
                - 'inverse_volatility': 按波动率倒数加权

        Returns:
            {stock_code: weight} 字典
        """
        if method == 'equal':
            # 等权重
            weight = 1.0 / len(stocks)
            weights = {stock: weight for stock in stocks}

        elif method == 'score' and scores is not None:
            # 按评分加权
            stock_scores = scores[stocks]
            # 归一化到 [0, 1]
            min_score = stock_scores.min()
            max_score = stock_scores.max()

            if max_score > min_score:
                normalized = (stock_scores - min_score) / (max_score - min_score)
            else:
                normalized = pd.Series(1.0, index=stocks)

            # 归一化权重
            total = normalized.sum()
            weights = (normalized / total).to_dict()

        else:
            # 默认等权重
            weight = 1.0 / len(stocks)
            weights = {stock: weight for stock in stocks}

        # 确保单只股票权重不超过限制
        max_weight = self.config.max_position_pct
        for stock in weights:
            if weights[stock] > max_weight:
                logger.warning(f"{stock} 权重 {weights[stock]:.2%} 超过限制 {max_weight:.2%}，进行截断")
                weights[stock] = max_weight

        # 重新归一化
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        return weights

    def backtest(
        self,
        engine,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> Dict:
        """
        执行回测（便捷方法）

        Args:
            engine: BacktestEngine 实例
            prices: 价格DataFrame
            features: 特征DataFrame
            **kwargs: 传递给 engine.backtest_long_only() 的参数

        Returns:
            回测结果字典
        """
        logger.info(f"\n开始回测策略: {self.name}")

        # 生成信号
        signals = self.generate_signals(prices, features)

        # 执行回测
        backtest_params = {
            'top_n': self.config.top_n,
            'holding_period': self.config.holding_period,
            'rebalance_freq': self.config.rebalance_freq,
        }
        backtest_params.update(kwargs)

        response = engine.backtest_long_only(
            signals=signals,
            prices=prices,
            **backtest_params
        )

        logger.success(f"✓ 回测完成: {self.name}")

        # 提取Response.data（兼容Response格式）
        if hasattr(response, 'data'):
            return response.data
        else:
            return response

    def get_metadata(self) -> Dict[str, Any]:
        """
        获取策略元信息

        Returns:
            完整的策略元数据
        """
        return {
            'name': self.name,
            'class': self.__class__.__name__,
            'strategy_type': self._strategy_type,
            'config_id': self._config_id,
            'strategy_id': self._strategy_id,
            'config_version': self._config_version,
            'code_hash': self._code_hash,
            'risk_level': self._risk_level,
            'config': self.config.to_dict() if hasattr(self.config, 'to_dict') else self.config,
        }

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息（保持向后兼容）

        Returns:
            策略信息字典
        """
        return {
            'name': self.name,
            'class': self.__class__.__name__,
            'config': self.config.to_dict(),
            'description': self.config.description or '暂无描述'
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', top_n={self.config.top_n})"


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 注意：BaseStrategy 是抽象类，不能直接实例化
    # 这里仅演示配置解析

    config = {
        'name': 'TestStrategy',
        'top_n': 30,
        'holding_period': 10,
        'lookback_period': 20,  # 自定义参数
        'threshold': 0.05  # 自定义参数
    }

    # 实际使用时，需要使用具体的策略类（如 MomentumStrategy）
    # strategy = MomentumStrategy('Test', config)

    logger.info("策略基类模块加载完成")
