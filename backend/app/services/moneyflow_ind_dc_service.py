"""板块资金流向业务逻辑层（东财概念及行业板块资金流向 DC）"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from app.repositories.moneyflow_ind_dc_repository import MoneyflowIndDcRepository


class MoneyflowIndDcService:
    """板块资金流向业务逻辑层"""

    def __init__(self):
        self.repo = MoneyflowIndDcRepository()
        logger.debug("✓ MoneyflowIndDcService initialized")

    # 原始数据单位为元，统一换算为亿元
    _AMOUNT_KEYS = ('net_amount', 'buy_elg_amount', 'buy_lg_amount', 'buy_md_amount', 'buy_sm_amount')
    _STATS_AMOUNT_KEYS = (
        'avg_net_amount', 'max_net_amount', 'min_net_amount', 'total_net_amount',
        'avg_buy_elg_amount', 'max_buy_elg_amount', 'avg_buy_lg_amount', 'max_buy_lg_amount',
    )

    def _convert_items_to_yi(self, items: List[Dict]) -> None:
        """将 items 中的金额字段从元原地换算为亿元（就地修改）"""
        for item in items:
            for key in self._AMOUNT_KEYS:
                if item.get(key) is not None:
                    item[key] = round(item[key] / 100_000_000, 2)

    def _convert_stats_to_yi(self, statistics: Dict) -> None:
        """将统计字典中的金额字段从元原地换算为亿元（就地修改）"""
        for key in self._STATS_AMOUNT_KEYS:
            if statistics.get(key) is not None:
                statistics[key] = round(statistics[key] / 100_000_000, 2)

    async def resolve_default_trade_date(self, content_type: Optional[str] = None) -> Optional[str]:
        """返回最近有数据的交易日（YYYY-MM-DD），供前端回填日期选择器"""
        today = datetime.now().strftime('%Y%m%d')
        has_today = await asyncio.to_thread(self.repo.exists_by_date, today)
        if has_today:
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = await asyncio.to_thread(self.repo.get_latest_trade_date, content_type)
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    def get_moneyflow_data(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        content_type: Optional[str] = None,
        ts_code: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
        # 保留旧参数兼容性
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Dict:
        """获取板块资金流向数据

        Note: trade_date 优先于 start_date/end_date；ts_code 参数保留用于 API 兼容性，目前未使用
        """
        # trade_date 优先
        if trade_date:
            trade_date_fmt = trade_date.replace('-', '')
            start_date_fmt = trade_date_fmt
            end_date_fmt = trade_date_fmt
        else:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None

        # 分页：兼容旧 limit/offset，新接口用 page/page_size
        if limit is not None:
            actual_limit = limit
            actual_offset = offset
        else:
            actual_limit = page_size
            actual_offset = (page - 1) * page_size

        items = self.repo.get_by_date_range(
            start_date=start_date_fmt or '19900101',
            end_date=end_date_fmt or '29991231',
            content_type=content_type,
            limit=actual_limit,
            offset=actual_offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_count = self.repo.get_record_count(
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            content_type=content_type
        )

        statistics = self.repo.get_statistics(
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            content_type=content_type
        )

        self._convert_items_to_yi(items)
        self._convert_stats_to_yi(statistics)

        # 解析实际查询日期，供前端回填（trade_date 单日模式时直接返回）
        resolved_trade_date = None
        if trade_date:
            resolved_trade_date = trade_date if '-' in trade_date else \
                f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}"
        elif items:
            raw = items[0].get('trade_date', '')
            if raw and len(raw) == 8:
                resolved_trade_date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"

        return {
            "items": items,
            "statistics": statistics,
            "total": total_count,
            "limit": actual_limit,
            "offset": actual_offset,
            "trade_date": resolved_trade_date,
        }

    def get_latest_moneyflow(self, content_type: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """获取最新交易日的板块资金流向数据"""
        items = self.repo.get_latest(content_type=content_type, limit=limit)
        self._convert_items_to_yi(items)
        return items
