"""
大盘资金流向业务逻辑层（东方财富DC）

提供大盘主力资金流向数据业务逻辑处理，包含数据查询、统计分析等功能。
数据源：东方财富大盘资金流向
"""

from typing import Dict, Optional
from loguru import logger

from app.repositories.moneyflow_mkt_dc_repository import MoneyflowMktDcRepository


class MoneyflowMktDcService:
    """大盘资金流向业务逻辑层"""

    def __init__(self):
        self.repo = MoneyflowMktDcRepository()
        logger.debug("✓ MoneyflowMktDcService initialized")

    def get_moneyflow_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """获取大盘资金流向数据（带分页和统计）"""
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        items = self.repo.get_by_date_range(
            start_date=start_date_fmt or '19900101',
            end_date=end_date_fmt or '29991231',
            limit=limit,
            offset=offset
        )

        total_count = self.repo.get_record_count(
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        statistics = self.repo.get_statistics(
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        # 单位换算：元 -> 亿元
        for item in items:
            for key in ['net_amount', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount']:
                if key in item and item[key]:
                    item[key] = round(item[key] / 100000000, 2)

        for key in ['avg_net', 'max_net', 'min_net', 'total_net', 'avg_elg', 'max_elg', 'avg_lg', 'max_lg']:
            if key in statistics and statistics[key]:
                statistics[key] = round(statistics[key] / 100000000, 2)

        return {
            "items": items,
            "statistics": statistics,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }

    def get_latest_moneyflow(self) -> Optional[Dict]:
        """获取最新的大盘资金流向数据"""
        data = self.repo.get_latest()

        if not data:
            return None

        # 单位换算：元 -> 亿元
        for key in ['net_amount', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount']:
            if key in data and data[key]:
                data[key] = round(data[key] / 100000000, 2)

        return data
