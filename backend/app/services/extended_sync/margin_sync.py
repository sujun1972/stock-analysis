"""
扩展数据同步 - 两融数据同步服务

分类: 两融及转融通
包含数据:
- margin_detail: 融资融券交易明细
"""

from typing import Optional, Dict, Any
import asyncio
import pandas as pd
from loguru import logger

from app.repositories import MarginDetailRepository
from .base_sync_service import BaseSyncService
from .common import DataType


class MarginSyncService(BaseSyncService):
    """两融数据同步服务"""

    def __init__(self):
        super().__init__()
        # 初始化 Repository
        self.margin_detail_repo = MarginDetailRepository()

    # ========== 公共同步方法 ==========

    async def sync_margin_detail(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步融资融券交易明细数据

        分类: 两融及转融通
        优先级: P2
        调用频率: 每日18:30
        积分消耗: 300
        """
        if not trade_date and not start_date:
            trade_date = self._calculate_trade_date("margin_detail", trade_date, start_date)

        return await self._sync_data_template(
            data_type=DataType.MARGIN_DETAIL,
            fetch_method=lambda p, **kw: p.get_margin_detail(**kw),
            insert_method=self._insert_margin_detail,
            validator_method=self.validator.validate_margin_detail,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    # ========== 私有数据插入方法 ==========

    async def _insert_margin_detail(self, df: pd.DataFrame):
        """插入融资融券交易明细数据"""
        await asyncio.to_thread(self.margin_detail_repo.bulk_upsert, df)


# 创建全局单例
margin_sync_service = MarginSyncService()
