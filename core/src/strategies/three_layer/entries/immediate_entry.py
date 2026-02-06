"""
立即入场策略

对所有候选股票立即产生买入信号(用于测试和简单策略)
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.entry_strategy import EntryStrategy


class ImmediateEntry(EntryStrategy):
    """
    立即入场策略

    策略逻辑:
    对选股器选出的所有股票立即产生买入信号，无需等待特定技术形态

    适用场景:
    - 测试选股器效果
    - 简单的买入持有策略
    - 基准策略对比
    - 当选股器已经做了充分筛选时

    示例:
        entry = ImmediateEntry(params={
            'max_stocks': 10,
            'min_stocks': 5
        })

        signals = entry.generate_entry_signals(
            stocks=['600000.SH', '000001.SZ', '000002.SZ'],
            data=stock_data_dict,
            date=pd.Timestamp('2023-06-01')
        )

        # 输出: {'600000.SH': 0.33, '000001.SZ': 0.33, '000002.SZ': 0.33}
    """

    @property
    def id(self) -> str:
        return "immediate"

    @property
    def name(self) -> str:
        return "立即入场"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "max_stocks",
                "label": "最大买入数量",
                "type": "integer",
                "default": 10,
                "min": 1,
                "max": 100,
                "description": "限制同时买入的股票数量"
            },
            {
                "name": "min_stocks",
                "label": "最小买入数量",
                "type": "integer",
                "default": 1,
                "min": 0,
                "max": 50,
                "description": "候选股票数少于此值时不生成信号"
            },
            {
                "name": "validate_data",
                "label": "验证数据有效性",
                "type": "boolean",
                "default": True,
                "description": "是否验证股票数据的有效性(跳过数据缺失的股票)"
            }
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """
        生成入场信号: 对所有候选股票产生等权买入信号

        参数:
            stocks: 候选股票列表
            data: 股票数据字典 {股票代码: OHLCV DataFrame}
            date: 当前日期

        返回:
            {股票代码: 买入权重} 字典
        """
        max_stocks = self.params.get("max_stocks", 10)
        min_stocks = self.params.get("min_stocks", 1)
        validate_data = self.params.get("validate_data", True)

        logger.debug(
            f"立即入场: 处理 {len(stocks)} 只候选股票 "
            f"(max={max_stocks}, min={min_stocks})"
        )

        # 如果候选股票太少，不生成信号
        if len(stocks) < min_stocks:
            logger.info(
                f"立即入场: 候选股票数({len(stocks)})少于最小要求({min_stocks})，"
                "不生成信号"
            )
            return {}

        # 选择有效股票
        valid_stocks = []

        if validate_data:
            # 验证数据有效性
            for stock in stocks:
                if stock not in data:
                    logger.debug(f"{stock}: 数据缺失，跳过")
                    continue

                stock_data = data[stock]

                # 验证数据包含必需的列
                if 'close' not in stock_data.columns:
                    logger.debug(f"{stock}: 缺少 'close' 列，跳过")
                    continue

                # 验证日期存在
                if date not in stock_data.index:
                    logger.debug(f"{stock}: 日期 {date} 不在数据范围内，跳过")
                    continue

                # 验证价格有效
                try:
                    close_price = stock_data.loc[date, 'close']
                    if pd.isna(close_price) or close_price <= 0:
                        logger.debug(f"{stock}: 价格无效 ({close_price})，跳过")
                        continue
                except (KeyError, IndexError):
                    logger.debug(f"{stock}: 获取价格失败，跳过")
                    continue

                valid_stocks.append(stock)
        else:
            # 不验证，直接使用所有候选股票
            valid_stocks = stocks.copy()

        # 限制买入数量
        if len(valid_stocks) > max_stocks:
            selected_stocks = valid_stocks[:max_stocks]
            logger.debug(
                f"候选股票数({len(valid_stocks)})超过上限({max_stocks})，"
                f"仅选择前{max_stocks}只"
            )
        else:
            selected_stocks = valid_stocks

        # 再次检查是否满足最小数量要求
        if len(selected_stocks) < min_stocks:
            logger.info(
                f"立即入场: 有效股票数({len(selected_stocks)})少于最小要求({min_stocks})，"
                "不生成信号"
            )
            return {}

        # 等权分配
        if selected_stocks:
            weight = 1.0 / len(selected_stocks)
            signals = {stock: weight for stock in selected_stocks}
            logger.info(
                f"立即入场: 生成 {len(signals)} 个买入信号 "
                f"(候选: {len(stocks)}, 有效: {len(valid_stocks)})"
            )
        else:
            signals = {}
            logger.info(f"立即入场: 无有效股票，不生成信号")

        return signals
