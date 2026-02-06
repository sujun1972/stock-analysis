"""
均线突破入场策略

当短期均线上穿长期均线时产生买入信号（金叉）
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.entry_strategy import EntryStrategy


class MABreakoutEntry(EntryStrategy):
    """
    均线突破入场策略

    策略逻辑:
    1. 计算短期、长期移动平均线
    2. 检测金叉: 短期MA上穿长期MA
    3. 对候选股票中出现金叉的股票生成买入信号

    适用场景:
    - 趋势跟踪
    - 捕捉突破行情
    - 趋势初期入场

    示例:
        entry = MABreakoutEntry(params={
            'short_window': 5,
            'long_window': 20,
            'lookback_for_cross': 1
        })

        signals = entry.generate_entry_signals(
            stocks=['600000.SH', '000001.SZ'],
            data=stock_data_dict,
            date=pd.Timestamp('2023-06-01')
        )

        # 输出: {'600000.SH': 0.5, '000001.SZ': 0.5}  (如果都有金叉)
    """

    @property
    def id(self) -> str:
        return "ma_breakout"

    @property
    def name(self) -> str:
        return "均线突破入场"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "short_window",
                "label": "短期均线周期",
                "type": "integer",
                "default": 5,
                "min": 2,
                "max": 50,
                "description": "短期移动平均线周期(天)"
            },
            {
                "name": "long_window",
                "label": "长期均线周期",
                "type": "integer",
                "default": 20,
                "min": 5,
                "max": 200,
                "description": "长期移动平均线周期(天)"
            },
            {
                "name": "lookback_for_cross",
                "label": "金叉检测回溯期",
                "type": "integer",
                "default": 1,
                "min": 1,
                "max": 5,
                "description": "检测过去N日内是否发生金叉"
            },
            {
                "name": "require_ma_trending_up",
                "label": "要求均线向上",
                "type": "boolean",
                "default": False,
                "description": "是否要求短期均线本身处于上升趋势"
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
        short_window = self.params.get("short_window", 5)
        long_window = self.params.get("long_window", 20)
        lookback = self.params.get("lookback_for_cross", 1)
        require_trending_up = self.params.get("require_ma_trending_up", False)

        # 验证参数合理性
        if short_window >= long_window:
            logger.warning(
                f"短期均线周期 ({short_window}) 应小于长期均线周期 ({long_window})，"
                "本次不生成任何信号"
            )
            return {}

        signals = {}

        logger.debug(
            f"均线突破入场: 检测 {len(stocks)} 只候选股票的金叉信号 "
            f"(MA{short_window}/{long_window}, lookback={lookback})"
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

            # 计算移动平均线
            try:
                ma_short = stock_data['close'].rolling(window=short_window).mean()
                ma_long = stock_data['close'].rolling(window=long_window).mean()
            except Exception as e:
                logger.warning(f"{stock}: 计算均线失败 - {e}")
                continue

            # 检查日期是否在数据范围内
            if date not in stock_data.index:
                logger.debug(f"{stock}: 日期 {date} 不在数据范围内，跳过")
                continue

            try:
                # 获取当前日期在索引中的位置
                current_idx = stock_data.index.get_loc(date)

                # 需要足够的历史数据来检测金叉
                if current_idx < lookback:
                    logger.debug(f"{stock}: 历史数据不足，跳过")
                    continue

                # 检查过去 lookback 日内是否发生金叉
                golden_cross_found = False

                for i in range(lookback):
                    check_idx = current_idx - i
                    prev_idx = check_idx - 1

                    if prev_idx < 0:
                        continue

                    # 获取均线值
                    ma_short_prev = ma_short.iloc[prev_idx]
                    ma_long_prev = ma_long.iloc[prev_idx]
                    ma_short_curr = ma_short.iloc[check_idx]
                    ma_long_curr = ma_long.iloc[check_idx]

                    # 检查是否有 NaN
                    if pd.isna([ma_short_prev, ma_long_prev, ma_short_curr, ma_long_curr]).any():
                        continue

                    # 金叉条件: 前一天短MA <= 长MA，当天短MA > 长MA
                    if ma_short_prev <= ma_long_prev and ma_short_curr > ma_long_curr:
                        # 如果要求均线向上，额外检查短期均线趋势
                        if require_trending_up:
                            if check_idx >= 2:
                                ma_short_prev2 = ma_short.iloc[check_idx - 2]
                                if pd.isna(ma_short_prev2) or ma_short_curr <= ma_short_prev2:
                                    continue

                        golden_cross_found = True
                        logger.debug(
                            f"{stock}: 在 {stock_data.index[check_idx].date()} 发生金叉 "
                            f"(MA{short_window}: {ma_short_prev:.2f} -> {ma_short_curr:.2f}, "
                            f"MA{long_window}: {ma_long_prev:.2f} -> {ma_long_curr:.2f})"
                        )
                        break

                if golden_cross_found:
                    signals[stock] = 1.0

            except (KeyError, IndexError) as e:
                logger.debug(f"{stock}: 处理失败 - {e}")
                continue

        # 等权分配
        if signals:
            weight = 1.0 / len(signals)
            signals = {stock: weight for stock in signals}
            logger.info(
                f"均线突破入场: 生成 {len(signals)} 个买入信号 "
                f"(候选股票数: {len(stocks)})"
            )
        else:
            logger.info(f"均线突破入场: 无买入信号 (候选股票数: {len(stocks)})")

        return signals
