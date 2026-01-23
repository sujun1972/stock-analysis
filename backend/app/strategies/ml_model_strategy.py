"""
机器学习模型策略
使用训练好的ML模型预测值生成交易信号
"""

from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger
from pathlib import Path
import pickle

from .base_strategy import BaseStrategy, StrategyParameter, ParameterType


class MLModelStrategy(BaseStrategy):
    """
    机器学习模型策略
    根据ML模型的预测值生成买卖信号
    """

    @property
    def name(self) -> str:
        return "机器学习模型策略"

    @property
    def description(self) -> str:
        return "使用训练好的机器学习模型预测未来收益率，根据预测值生成交易信号"

    @property
    def version(self) -> str:
        return "1.0.0"

    @classmethod
    def get_parameters(cls) -> List[StrategyParameter]:
        return [
            StrategyParameter(
                name="model_id",
                label="模型ID",
                type=ParameterType.SELECT,
                default="",
                description="使用的机器学习模型ID",
                category="model"
            ),
            StrategyParameter(
                name="model_type",
                label="模型类型",
                type=ParameterType.SELECT,
                default="lightgbm",
                options=[
                    {"label": "LightGBM", "value": "lightgbm"},
                    {"label": "GRU", "value": "gru"}
                ],
                description="机器学习模型类型",
                category="model"
            ),
            StrategyParameter(
                name="target_period",
                label="预测周期",
                type=ParameterType.INTEGER,
                default=5,
                min_value=1,
                max_value=30,
                description="预测未来N天的收益率",
                category="model"
            ),
            StrategyParameter(
                name="buy_threshold",
                label="买入阈值(%)",
                type=ParameterType.FLOAT,
                default=1.0,
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                description="预测收益率超过此值时买入",
                category="signal"
            ),
            StrategyParameter(
                name="sell_threshold",
                label="卖出阈值(%)",
                type=ParameterType.FLOAT,
                default=-1.0,
                min_value=-10.0,
                max_value=0.0,
                step=0.1,
                description="预测收益率低于此值时卖出",
                category="signal"
            ),
            StrategyParameter(
                name="commission",
                label="交易佣金率",
                type=ParameterType.FLOAT,
                default=0.0003,
                min_value=0.0,
                max_value=0.01,
                step=0.0001,
                description="交易佣金费率",
                category="cost"
            ),
            StrategyParameter(
                name="slippage",
                label="滑点率",
                type=ParameterType.FLOAT,
                default=0.001,
                min_value=0.0,
                max_value=0.05,
                step=0.0001,
                description="价格滑点费率",
                category="cost"
            ),
            StrategyParameter(
                name="position_size",
                label="仓位比例",
                type=ParameterType.FLOAT,
                default=1.0,
                min_value=0.1,
                max_value=1.0,
                step=0.1,
                description="每次开仓使用的资金比例",
                category="risk"
            ),
            StrategyParameter(
                name="stop_loss",
                label="止损比例",
                type=ParameterType.FLOAT,
                default=0.05,
                min_value=0.01,
                max_value=0.20,
                step=0.01,
                description="止损比例(5%表示下跌5%时止损)",
                category="risk"
            ),
            StrategyParameter(
                name="take_profit",
                label="止盈比例",
                type=ParameterType.FLOAT,
                default=0.10,
                min_value=0.01,
                max_value=0.50,
                step=0.01,
                description="止盈比例(10%表示上涨10%时止盈)",
                category="risk"
            ),
        ]

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)

        # 从参数中提取模型信息
        self.model_id = self.params.get('model_id', '')
        self.model_type = self.params.get('model_type', 'lightgbm')
        self.target_period = self.params.get('target_period', 5)

        # 交易参数
        self.buy_threshold = self.params.get('buy_threshold', 1.0)
        self.sell_threshold = self.params.get('sell_threshold', -1.0)

        # 成本参数
        self.commission = self.params.get('commission', 0.0003)
        self.slippage = self.params.get('slippage', 0.001)

        # 风控参数
        self.position_size = self.params.get('position_size', 1.0)
        self.stop_loss = self.params.get('stop_loss', 0.05)
        self.take_profit = self.params.get('take_profit', 0.10)

        # 模型缓存
        self.model = None
        self.model_dir = Path('data/models/saved')

        logger.info(
            f"初始化ML模型策略: model_id={self.model_id}, "
            f"buy_threshold={self.buy_threshold}%, sell_threshold={self.sell_threshold}%"
        )

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        根据ML模型预测生成交易信号

        参数:
            data: 价格数据DataFrame (必须包含 open, high, low, close, volume)

        返回:
            交易信号序列 (1=买入, -1=卖出, 0=持有)
        """
        logger.info(f"使用ML模型生成交易信号: model_id={self.model_id}")

        # 初始化信号序列
        signals = pd.Series(0, index=data.index)

        try:
            # 加载模型
            if not self.model_id:
                logger.warning("未指定model_id，使用简单移动平均策略作为替代")
                return self._generate_fallback_signals(data)

            # 尝试加载模型
            model = self._load_model_from_disk()
            if model is None:
                logger.warning(f"无法加载模型 {self.model_id}，使用简单移动平均策略作为替代")
                return self._generate_fallback_signals(data)

            # 生成预测
            predictions = self._generate_predictions(model, data)

            if predictions is None or len(predictions) == 0:
                logger.warning("模型预测失败，使用简单移动平均策略作为替代")
                return self._generate_fallback_signals(data)

            # 根据预测值生成信号
            # 预测上涨 > buy_threshold: 买入信号
            # 预测下跌 < sell_threshold: 卖出信号
            buy_signals = predictions > self.buy_threshold
            sell_signals = predictions < self.sell_threshold

            signals[buy_signals] = 1
            signals[sell_signals] = -1

            # 添加止损止盈逻辑
            signals = self._apply_risk_management(signals, data)

            logger.info(
                f"信号生成完成: 买入={buy_signals.sum()}, "
                f"卖出={sell_signals.sum()}, 持有={len(signals) - buy_signals.sum() - sell_signals.sum()}"
            )

            return signals

        except Exception as e:
            logger.error(f"生成ML信号失败: {e}")
            logger.warning("使用简单移动平均策略作为替代")
            return self._generate_fallback_signals(data)

    def _load_model_from_disk(self):
        """从磁盘加载模型"""
        try:
            model_path = self.model_dir / f"{self.model_id}.pkl"
            if not model_path.exists():
                logger.warning(f"模型文件不存在: {model_path}")
                return None

            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"成功加载模型: {model_path}")
            return model

        except Exception as e:
            logger.error(f"加载模型失败: {e}")
            return None

    def _generate_predictions(self, model, data: pd.DataFrame) -> Optional[pd.Series]:
        """
        使用模型生成预测

        TODO: 这里需要根据实际的模型API进行调整
        目前返回模拟数据
        """
        try:
            # 这里应该调用实际的模型预测方法
            # 例如: predictions = model.predict(features)

            # 临时方案：返回随机预测值作为演示
            logger.warning("使用模拟预测数据（待实现真实模型预测）")
            np.random.seed(42)
            predictions = pd.Series(
                np.random.randn(len(data)) * 2,  # 模拟预测收益率 (%)
                index=data.index
            )

            return predictions

        except Exception as e:
            logger.error(f"模型预测失败: {e}")
            return None

    def _generate_fallback_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        回退策略：使用简单的移动平均交叉策略
        当ML模型不可用时使用
        """
        logger.info("使用回退策略：MA5/MA20交叉")
        signals = pd.Series(0, index=data.index)

        # 计算移动平均线
        ma5 = data['close'].rolling(window=5).mean()
        ma20 = data['close'].rolling(window=20).mean()

        # 金叉：MA5上穿MA20 -> 买入
        golden_cross = (ma5 > ma20) & (ma5.shift(1) <= ma20.shift(1))
        signals[golden_cross] = 1

        # 死叉：MA5下穿MA20 -> 卖出
        death_cross = (ma5 < ma20) & (ma5.shift(1) >= ma20.shift(1))
        signals[death_cross] = -1

        return signals

    def _apply_risk_management(
        self,
        signals: pd.Series,
        data: pd.DataFrame
    ) -> pd.Series:
        """
        应用止损止盈逻辑

        参数:
            signals: 原始信号
            data: 价格数据

        返回:
            调整后的信号
        """
        adjusted_signals = signals.copy()

        # 跟踪持仓状态
        position = 0
        entry_price = 0.0

        for i, date in enumerate(data.index):
            current_price = data.loc[date, 'close']

            # 如果有持仓，检查止损止盈
            if position > 0:
                # 计算盈亏比例
                pnl_ratio = (current_price - entry_price) / entry_price

                # 触发止损
                if pnl_ratio <= -self.stop_loss:
                    adjusted_signals.iloc[i] = -1
                    position = 0
                    logger.debug(f"触发止损: date={date}, pnl={pnl_ratio:.2%}")

                # 触发止盈
                elif pnl_ratio >= self.take_profit:
                    adjusted_signals.iloc[i] = -1
                    position = 0
                    logger.debug(f"触发止盈: date={date}, pnl={pnl_ratio:.2%}")

            # 更新持仓状态
            if adjusted_signals.iloc[i] == 1:
                position = 1
                entry_price = current_price
            elif adjusted_signals.iloc[i] == -1:
                position = 0

        return adjusted_signals
