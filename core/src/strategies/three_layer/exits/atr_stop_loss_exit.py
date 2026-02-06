"""
ATR动态止损退出策略

基于ATR（Average True Range）设置动态止损位
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position


class ATRStopLossExit(ExitStrategy):
    """
    ATR动态止损退出策略

    策略逻辑:
    1. 计算ATR指标（真实波动范围）
    2. 止损位 = 入场价 - ATR × 倍数
    3. 当前价格跌破止损位时卖出

    优势:
    - 适应市场波动：波动大时止损位宽松，波动小时止损位严格
    - 避免在正常波动中被止损
    - 适合趋势跟踪策略

    ATR (Average True Range):
    - TR (True Range) = max(high-low, |high-prev_close|, |low-prev_close|)
    - ATR = TR的移动平均（通常14日）
    - 值越大表示波动越剧烈

    示例:
        exit_strategy = ATRStopLossExit(params={
            'atr_period': 14,
            'atr_multiplier': 2.0
        })

        exit_signals = exit_strategy.generate_exit_signals(
            positions=positions_dict,
            data=stock_data_dict,
            date=pd.Timestamp('2023-06-01')
        )
        # 返回: ['600000.SH', '000001.SZ']  (触发止损的股票)
    """

    @property
    def id(self) -> str:
        return "atr_stop_loss"

    @property
    def name(self) -> str:
        return "ATR动态止损"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "atr_period",
                "label": "ATR周期",
                "type": "integer",
                "default": 14,
                "min": 5,
                "max": 50,
                "description": "ATR计算周期（天）"
            },
            {
                "name": "atr_multiplier",
                "label": "ATR倍数",
                "type": "float",
                "default": 2.0,
                "min": 0.5,
                "max": 5.0,
                "description": "止损位 = 入场价 - ATR × 倍数"
            }
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """
        生成退出信号

        参数:
            positions: 当前持仓字典 {股票代码: Position}
            data: 股票数据字典 {股票代码: OHLCV DataFrame}
            date: 当前日期

        返回:
            需要卖出的股票代码列表
        """
        atr_period = self.params.get("atr_period", 14)
        atr_multiplier = self.params.get("atr_multiplier", 2.0)

        exit_stocks = []

        logger.debug(
            f"ATR止损检查: {len(positions)} 个持仓 "
            f"(ATR{atr_period}, 倍数={atr_multiplier})"
        )

        for stock, position in positions.items():
            if stock not in data:
                logger.debug(f"{stock}: 数据缺失，跳过")
                continue

            stock_data = data[stock]

            # 验证数据包含必需的列
            required_cols = ['open', 'high', 'low', 'close']
            missing_cols = [col for col in required_cols if col not in stock_data.columns]
            if missing_cols:
                logger.warning(f"{stock}: 缺少列 {missing_cols}，跳过")
                continue

            # 计算ATR
            try:
                atr = self._calculate_atr(stock_data, atr_period)
            except Exception as e:
                logger.warning(f"{stock}: 计算ATR失败 - {e}")
                continue

            # 检查日期是否在数据范围内
            if date not in stock_data.index:
                logger.debug(f"{stock}: 日期 {date} 不在数据范围内，跳过")
                continue

            try:
                current_atr = atr.loc[date]

                # 检查是否为 NaN
                if pd.isna(current_atr):
                    logger.debug(f"{stock}: ATR为NaN，跳过")
                    continue

                current_price = position.current_price
                entry_price = position.entry_price

                # 计算止损位
                stop_loss_price = entry_price - (current_atr * atr_multiplier)

                # 检查是否触发止损
                if current_price < stop_loss_price:
                    exit_stocks.append(stock)
                    loss_pct = (current_price - entry_price) / entry_price * 100
                    logger.info(
                        f"{stock} 触发ATR止损: "
                        f"入场价={entry_price:.2f}, "
                        f"当前价={current_price:.2f}, "
                        f"ATR={current_atr:.2f}, "
                        f"止损位={stop_loss_price:.2f}, "
                        f"亏损={loss_pct:.2f}%"
                    )
                else:
                    logger.debug(
                        f"{stock}: 未触发止损 "
                        f"(当前价={current_price:.2f}, 止损位={stop_loss_price:.2f})"
                    )

            except (KeyError, IndexError) as e:
                logger.debug(f"{stock}: 处理失败 - {e}")
                continue

        if exit_stocks:
            logger.info(f"ATR止损: {len(exit_stocks)} 只股票触发卖出")
        else:
            logger.debug(f"ATR止损: 无股票触发卖出")

        return exit_stocks

    def _calculate_atr(self, stock_data: pd.DataFrame, period: int) -> pd.Series:
        """
        计算ATR指标

        参数:
            stock_data: OHLCV DataFrame
            period: ATR周期

        返回:
            ATR序列
        """
        high = stock_data['high']
        low = stock_data['low']
        close = stock_data['close']

        # True Range的三种计算方式
        # 1. 当日最高价 - 当日最低价
        tr1 = high - low
        # 2. |当日最高价 - 昨日收盘价|
        tr2 = abs(high - close.shift(1))
        # 3. |当日最低价 - 昨日收盘价|
        tr3 = abs(low - close.shift(1))

        # True Range = 三者最大值
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR = TR的移动平均
        atr = tr.rolling(window=period, min_periods=period).mean()

        return atr
