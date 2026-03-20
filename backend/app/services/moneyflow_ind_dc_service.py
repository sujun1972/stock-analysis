"""板块资金流向业务逻辑层（东财概念及行业板块资金流向 DC）"""

from typing import Dict, List, Optional
from loguru import logger
from app.repositories.moneyflow_ind_dc_repository import MoneyflowIndDcRepository


class MoneyflowIndDcService:
    """板块资金流向业务逻辑层"""

    def __init__(self):
        self.repo = MoneyflowIndDcRepository()
        logger.debug("✓ MoneyflowIndDcService initialized")

    def get_moneyflow_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        content_type: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict:
        """获取板块资金流向数据"""
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        items = self.repo.get_by_date_range(
            start_date=start_date_fmt or '19900101',
            end_date=end_date_fmt or '29991231',
            content_type=content_type,
            ts_code=ts_code,
            limit=limit,
            offset=offset
        )

        total_count = self.repo.get_record_count(
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            content_type=content_type,
            ts_code=ts_code
        )

        statistics = self.repo.get_statistics(
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            content_type=content_type
        )

        # 单位换算：元 -> 亿元
        for item in items:
            for key in ['net_amount', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount']:
                if key in item and item[key]:
                    item[key] = round(item[key] / 100000000, 2)

        for key in ['avg_net', 'max_net', 'min_net', 'total_net', 'avg_elg', 'max_elg', 'avg_lg', 'max_lg']:
            if key in statistics and statistics[key]:
                statistics[key] = round(statistics[key] / 100000000, 2)

        return {"items": items, "statistics": statistics, "total": total_count, "limit": limit, "offset": offset}

    def get_latest_moneyflow(self, content_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """获取最新的板块资金流向数据"""
        items = self.repo.get_latest(content_type=content_type, limit=limit)

        # 单位换算：元 -> 亿元
        for item in items:
            for key in ['net_amount', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount']:
                if key in item and item[key]:
                    item[key] = round(item[key] / 100000000, 2)

        return items
