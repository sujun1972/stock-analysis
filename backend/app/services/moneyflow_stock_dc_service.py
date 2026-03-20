"""个股资金流向业务逻辑层（东方财富DC）"""

from typing import Dict, Optional
from loguru import logger
from app.repositories.moneyflow_stock_dc_repository import MoneyflowStockDcRepository


class MoneyflowStockDcService:
    """个股资金流向业务逻辑层（DC）"""

    def __init__(self):
        self.repo = MoneyflowStockDcRepository()
        logger.debug("✓ MoneyflowStockDcService initialized")

    def get_moneyflow_data(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """获取个股资金流向数据"""
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        items = self.repo.get_by_date_range(
            start_date=start_date_fmt or '19900101',
            end_date=end_date_fmt or '29991231',
            ts_code=ts_code,
            limit=limit,
            offset=offset
        )

        total_count = self.repo.get_record_count(
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            ts_code=ts_code
        )

        statistics = self.repo.get_statistics(
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            ts_code=ts_code
        )

        # 单位换算：万元 -> 亿元
        for item in items:
            for key in ['net_amount', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount']:
                if key in item and item[key]:
                    item[key] = round(item[key] / 10000, 2)

        for key in ['avg_net', 'max_net', 'min_net', 'total_net', 'avg_elg', 'max_elg', 'avg_lg', 'max_lg']:
            if key in statistics and statistics[key]:
                statistics[key] = round(statistics[key] / 10000, 2)

        return {"items": items, "statistics": statistics, "total": total_count, "limit": limit, "offset": offset}

    def get_top_stocks(self, trade_date: Optional[str] = None, limit: int = 20) -> Dict:
        """获取主力资金流入排名前N的股票"""
        if trade_date:
            trade_date_fmt = trade_date.replace('-', '')
        else:
            trade_date_fmt = self.repo.get_latest_trade_date()

        if not trade_date_fmt:
            return {"items": [], "trade_date": None}

        items = self.repo.get_top_by_net_amount(trade_date=trade_date_fmt, limit=limit)

        # 单位换算：万元 -> 亿元
        for item in items:
            for key in ['net_amount', 'buy_elg_amount', 'buy_lg_amount']:
                if key in item and item[key]:
                    item[key] = round(item[key] / 10000, 2)

        return {"items": items, "trade_date": trade_date_fmt}
