"""
RSI超卖入场策略

当RSI指标进入超卖区间时产生买入信号
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.entry_strategy import EntryStrategy


class RSIOversoldEntry(EntryStrategy):
    """
    RSI超卖入场策略

    策略逻辑:
    1. 计算RSI指标
    2. 检测超卖: RSI < 阈值(默认30)
    3. 对超卖股票生成买入信号

    适用场景:
    - 捕捉超卖反弹
    - 逆向策略
    - 短期交易

    RSI (Relative Strength Index):
    - RSI > 70: 超买区间
    - RSI < 30: 超卖区间
    - RSI = 50: 中性

    示例:
        entry = RSIOversoldEntry(params={
            'rsi_period': 14,
            'oversold_threshold': 30.0,
            'require_rsi_turning_up': False
        })

        signals = entry.generate_entry_signals(
            stocks=['600000.SH', '000001.SZ'],
            data=stock_data_dict,
            date=pd.Timestamp('2023-06-01')
        )
    """

    @property
    def id(self) -> str:
        return "rsi_oversold"

    @property
    def name(self) -> str:
        return "RSI超卖入场"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "rsi_period",
                "label": "RSI周期",
                "type": "integer",
                "default": 14,
                "min": 5,
                "max": 50,
                "description": "RSI计算周期(天)"
            },
            {
                "name": "oversold_threshold",
                "label": "超卖阈值",
                "type": "float",
                "default": 30.0,
                "min": 10.0,
                "max": 40.0,
                "description": "RSI低于此值视为超卖"
            },
            {
                "name": "require_rsi_turning_up",
                "label": "要求RSI回升",
                "type": "boolean",
                "default": False,
                "description": "是否要求RSI从底部开始回升(避免下跌途中入场)"
            },
            {
                "name": "min_rsi",
                "label": "RSI下限",
                "type": "float",
                "default": 5.0,
                "min": 0.0,
                "max": 20.0,
                "description": "过滤极端低RSI值(可能是异常数据)"
            }
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """
        生成入场信号

        参数:
            stocks: 候选股票列表
            data: 股票数据字典 {股票代码: OHLCV DataFrame}
            date: 当前日期

        返回:
            {股票代码: 买入权重} 字典
        """
        rsi_period = self.params.get("rsi_period", 14)
        oversold_threshold = self.params.get("oversold_threshold", 30.0)
        require_turning_up = self.params.get("require_rsi_turning_up", False)
        min_rsi = self.params.get("min_rsi", 5.0)

        signals = {}

        logger.debug(
            f"RSI超卖入场: 检测 {len(stocks)} 只候选股票 "
            f"(RSI{rsi_period}, 阈值={oversold_threshold}, "
            f"要求回升={require_turning_up})"
        )

        for stock in stocks:
            if stock not in data:
                logger.debug(f"{stock}: 数据缺失，跳过")
                continue

            stock_data = data[stock]

            # 验证数据包含必需的列
            if 'close' not in stock_data.columns:
                logger.warning(f"{stock}: 缺少 'close' 列，跳过")
                continue

            # 计算RSI
            try:
                rsi = self._calculate_rsi(stock_data['close'], rsi_period)
            except Exception as e:
                logger.warning(f"{stock}: 计算RSI失败 - {e}")
                continue

            # 检查日期是否在数据范围内
            if date not in stock_data.index:
                logger.debug(f"{stock}: 日期 {date} 不在数据范围内，跳过")
                continue

            try:
                current_rsi = rsi.loc[date]

                # 检查是否为 NaN
                if pd.isna(current_rsi):
                    logger.debug(f"{stock}: RSI为NaN，跳过")
                    continue

                # 检测超卖
                is_oversold = min_rsi <= current_rsi < oversold_threshold

                if not is_oversold:
                    continue

                # 如果要求RSI回升，检查趋势
                if require_turning_up:
                    current_idx = stock_data.index.get_loc(date)
                    if current_idx < 1:
                        logger.debug(f"{stock}: 历史数据不足，跳过")
                        continue

                    prev_rsi = rsi.iloc[current_idx - 1]

                    if pd.isna(prev_rsi) or current_rsi <= prev_rsi:
                        logger.debug(
                            f"{stock}: RSI未回升 "
                            f"(前: {prev_rsi:.2f}, 当前: {current_rsi:.2f})，跳过"
                        )
                        continue

                signals[stock] = 1.0
                logger.debug(f"{stock}: RSI超卖信号 (RSI={current_rsi:.2f})")

            except (KeyError, IndexError) as e:
                logger.debug(f"{stock}: 处理失败 - {e}")
                continue

        # 等权分配
        if signals:
            weight = 1.0 / len(signals)
            signals = {stock: weight for stock in signals}
            logger.info(
                f"RSI超卖入场: 生成 {len(signals)} 个买入信号 "
                f"(候选股票数: {len(stocks)})"
            )
        else:
            logger.info(f"RSI超卖入场: 无买入信号 (候选股票数: {len(stocks)})")

        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """
        计算RSI指标

        参数:
            prices: 价格序列
            period: RSI周期

        返回:
            RSI序列
        """
        # 计算价格变化
        delta = prices.diff()

        # 分离涨跌
        gain = delta.where(delta > 0, 0.0)  # 上涨
        loss = -delta.where(delta < 0, 0.0)  # 下跌(取绝对值)

        # 计算平均涨跌幅 (使用简单移动平均)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        # 计算RS (Relative Strength)
        rs = avg_gain / avg_loss

        # 计算RSI
        # RSI = 100 - (100 / (1 + RS))
        rsi = 100.0 - (100.0 / (1.0 + rs))

        return rsi
