"""
数据可用性配置
定义各种数据类型在Tushare API中的可用性范围
"""

from datetime import datetime
from typing import Optional

class DataAvailabilityConfig:
    """
    配置各数据类型的API支持范围
    """

    # 数据类型的最大支持日期
    # None表示支持当前日期，字符串表示最大支持到的日期
    DATA_MAX_DATE = {
        # 支持2026年数据的接口
        "daily_basic": None,      # 每日指标，支持当前日期
        "moneyflow": None,         # 资金流向，支持当前日期

        # 仅支持到2025年底的接口
        "margin_detail": "20251231",  # 融资融券，仅支持到2025年底
        "adj_factor": "20251231",  # 复权因子，仅支持到2025年底
        "block_trade": "20251231", # 大宗交易，仅支持到2025年底
    }

    @classmethod
    def should_use_date(cls, data_type: str, calculated_date: str) -> Optional[str]:
        """
        判断是否应该使用计算的日期

        Args:
            data_type: 数据类型
            calculated_date: 计算得到的日期 (YYYYMMDD格式)

        Returns:
            应该使用的日期，None表示不传日期参数
        """
        max_date = cls.DATA_MAX_DATE.get(data_type, None)

        # 如果没有配置或支持当前日期，直接使用计算的日期
        if max_date is None:
            return calculated_date

        # 如果计算的日期超过最大支持日期，返回None（不传日期参数）
        if calculated_date > max_date:
            return None

        return calculated_date

    @classmethod
    def get_description(cls, data_type: str, calculated_date: str) -> str:
        """
        获取日期处理的描述信息

        Args:
            data_type: 数据类型
            calculated_date: 计算得到的日期

        Returns:
            描述信息
        """
        max_date = cls.DATA_MAX_DATE.get(data_type, None)

        if max_date is None:
            return f"{data_type}: 支持当前日期，使用 {calculated_date}"

        if calculated_date > max_date:
            return f"{data_type}: 当前日期{calculated_date}超出API支持范围（最大{max_date}），不指定日期参数获取最新可用数据"

        return f"{data_type}: 日期{calculated_date}在支持范围内，正常使用"