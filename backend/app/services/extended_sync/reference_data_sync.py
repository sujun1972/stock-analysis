"""
扩展数据同步 - 参考数据同步服务

分类: 参考数据
包含数据:
- block_trade: 大宗交易数据
"""

from typing import Optional, Dict, Any
import pandas as pd
from datetime import datetime
from loguru import logger

from .base_sync_service import BaseSyncService
from .common import DataType


class ReferenceDataSyncService(BaseSyncService):
    """参考数据同步服务"""

    def __init__(self):
        super().__init__()

    # ========== 公共同步方法 ==========

    async def sync_block_trade(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步大宗交易数据

        分类: 参考数据
        优先级: P3
        调用频率: 每日19:00
        积分消耗: 300
        """
        if not trade_date and not start_date:
            trade_date = self._calculate_trade_date("block_trade", trade_date, start_date)

        return await self._sync_data_template(
            data_type=DataType.BLOCK_TRADE,
            fetch_method=lambda p, **kw: p.get_block_trade(**kw),
            insert_method=self._insert_block_trade,
            validator_method=None,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    # ========== 私有数据插入方法 ==========

    async def _insert_block_trade(self, df: pd.DataFrame):
        """
        插入大宗交易数据

        TODO: 创建 BlockTradeRepository 并使用 bulk_insert 方法
        """
        from app.core.database import get_async_db
        from sqlalchemy import text

        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # 转换日期字符串为日期对象
                if 'trade_date' in record and isinstance(record['trade_date'], str):
                    record['trade_date'] = datetime.strptime(record['trade_date'], '%Y%m%d').date()

                # 大宗交易数据不使用UPSERT,直接插入
                query = text("""
                    INSERT INTO block_trade (
                        ts_code, trade_date, price, vol, amount, buyer, seller
                    ) VALUES (
                        :ts_code, :trade_date, :price, :vol, :amount, :buyer, :seller
                    )
                """)

                await db.execute(query, record)

            await db.commit()


# 创建全局单例
reference_data_sync_service = ReferenceDataSyncService()
