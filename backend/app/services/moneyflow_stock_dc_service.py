"""个股资金流向业务逻辑层（东方财富DC）"""

from datetime import datetime
from typing import Dict, Optional
from loguru import logger
from app.repositories.moneyflow_stock_dc_repository import MoneyflowStockDcRepository

# 允许排序的字段白名单（防 SQL 注入）
SORTABLE_COLUMNS = {'net_amount', 'pct_change', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount', 'close'}


class MoneyflowStockDcService:
    """个股资金流向业务逻辑层（DC）"""

    def __init__(self):
        self.repo = MoneyflowStockDcRepository()
        logger.debug("✓ MoneyflowStockDcService initialized")

    def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认交易日期：优先今天，否则回退到表中最新交易日。

        Returns:
            日期字符串 YYYY-MM-DD，无数据时返回 None
        """
        today = datetime.now().strftime('%Y%m%d')
        if self.repo.exists_by_date(today):
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = self.repo.get_latest_trade_date()
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    def get_moneyflow_data(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        page: int = 1,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> Dict:
        """获取个股资金流向数据"""
        # 日期格式处理
        if trade_date:
            trade_date_fmt = trade_date.replace('-', '')
            start_date_fmt = trade_date_fmt
            end_date_fmt = trade_date_fmt
            resolved_date = trade_date
        else:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None
            resolved_date = self.resolve_default_trade_date()
            if resolved_date and not start_date and not end_date:
                trade_date_fmt = resolved_date.replace('-', '')
                start_date_fmt = trade_date_fmt
                end_date_fmt = trade_date_fmt

        offset = (page - 1) * limit

        # 排序白名单校验
        validated_sort_by = sort_by if sort_by in SORTABLE_COLUMNS else None
        validated_sort_order = sort_order if sort_order in ('asc', 'desc') else None

        items = self.repo.get_by_date_range(
            start_date=start_date_fmt or '19900101',
            end_date=end_date_fmt or '29991231',
            ts_code=ts_code,
            limit=limit,
            offset=offset,
            sort_by=validated_sort_by,
            sort_order=validated_sort_order,
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

        # 单位换算：万元 -> 亿元（明细数据）
        for item in items:
            for key in ['net_amount', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount']:
                if key in item and item[key] is not None:
                    item[key] = round(item[key] / 10000, 4)

        # 单位换算：万元 -> 亿元（统计数据）
        for key in ['avg_net_amount', 'total_net_amount', 'max_net_amount', 'min_net_amount',
                    'avg_buy_elg_amount', 'max_buy_elg_amount', 'avg_buy_lg_amount', 'max_buy_lg_amount']:
            if key in statistics and statistics[key] is not None:
                statistics[key] = round(statistics[key] / 10000, 4)

        return {
            "items": items,
            "statistics": statistics,
            "total": total_count,
            "page": page,
            "page_size": limit,
            "trade_date": resolved_date,
        }

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
