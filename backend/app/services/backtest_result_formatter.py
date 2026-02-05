"""
回测结果格式化器
负责优化和格式化回测结果以便传输
"""

from typing import Dict, List

import pandas as pd


class BacktestResultFormatter:
    """
    回测结果格式化器

    职责：
    - K线数据优化（降采样）
    - 净值曲线优化
    - 信号点提取
    - 数据格式转换
    """

    def __init__(self):
        """初始化格式化器"""

    def optimize_kline_data(self, df: pd.DataFrame, max_points: int = 1000) -> List[Dict]:
        """
        优化K线数据传输（降采样）

        Args:
            df: K线数据DataFrame
            max_points: 最大数据点数

        Returns:
            K线数据列表
        """
        # 如果数据量小于阈值，直接返回
        if len(df) <= max_points:
            return self._df_to_kline_list(df)

        # 否则采样最近 max_points 条
        sampled = df.tail(max_points)
        return self._df_to_kline_list(sampled)

    def optimize_equity_curve(self, df: pd.DataFrame, max_points: int = 500) -> List[Dict]:
        """
        优化净值曲线数据传输

        Args:
            df: 净值曲线DataFrame（需包含 'total' 列）
            max_points: 最大数据点数

        Returns:
            净值曲线数据列表
        """
        # 如果数据量小于阈值，直接返回
        if len(df) <= max_points:
            return [
                {"date": idx.strftime("%Y-%m-%d"), "value": float(row["total"])}
                for idx, row in df.iterrows()
            ]

        # 否则等间隔采样
        step = len(df) // max_points
        sampled = df.iloc[::step]

        return [
            {"date": idx.strftime("%Y-%m-%d"), "value": float(row["total"])}
            for idx, row in sampled.iterrows()
        ]

    def extract_signal_points(self, trades: List[Dict]) -> Dict:
        """
        提取买卖信号点

        Args:
            trades: 交易记录列表

        Returns:
            {'buy': [...], 'sell': [...]} 格式的信号点
        """
        buy_points = []
        sell_points = []

        for trade in trades:
            if trade["type"] == "buy":
                buy_points.append({"date": trade["date"], "price": trade["price"]})
            elif trade["type"] == "sell":
                sell_points.append({"date": trade["date"], "price": trade["price"]})

        return {"buy": buy_points, "sell": sell_points}

    def format_portfolio_value(self, portfolio_value: pd.DataFrame) -> List[Dict]:
        """
        格式化组合净值数据

        Args:
            portfolio_value: 组合净值DataFrame

        Returns:
            格式化后的净值列表
        """
        return [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "total": float(row["total"]),
                "cash": float(row["cash"]),
                "holdings": float(row["holdings"]),
            }
            for idx, row in portfolio_value.iterrows()
        ]

    def _df_to_kline_list(self, df: pd.DataFrame) -> List[Dict]:
        """
        转换DataFrame为K线列表

        Args:
            df: K线DataFrame

        Returns:
            K线数据列表
        """
        result = []
        for idx, row in df.iterrows():
            item = {
                "date": idx.strftime("%Y-%m-%d"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            }

            # 添加技术指标（如果存在）
            indicator_columns = [
                "MA5",
                "MA20",
                "MA60",
                "MACD",
                "MACD_SIGNAL",
                "MACD_HIST",
                "KDJ_K",
                "KDJ_D",
                "KDJ_J",
                "RSI6",
                "RSI12",
                "RSI24",
                "BOLL_UPPER",
                "BOLL_MIDDLE",
                "BOLL_LOWER",
            ]

            for col in indicator_columns:
                if col in row.index:
                    value = row[col]
                    item[col] = float(value) if pd.notna(value) else None

            result.append(item)

        return result
