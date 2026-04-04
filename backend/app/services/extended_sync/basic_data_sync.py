"""
扩展数据同步 - 基础数据同步服务

分类: 基础数据
包含数据:
- daily_basic: 每日指标 (市盈率、换手率等)
- adj_factor: 复权因子
- suspend: 停复牌信息
"""

from typing import Optional, Dict, Any
import asyncio
import pandas as pd
from datetime import datetime
from loguru import logger

from app.services.trading_calendar_service import trading_calendar_service
from .base_sync_service import BaseSyncService
from .common import DataType


class BasicDataSyncService(BaseSyncService):
    """基础数据同步服务"""

    def __init__(self):
        super().__init__()

    # ========== 公共同步方法 ==========

    async def sync_daily_basic(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步每日指标数据

        分类: 基础数据
        优先级: P0
        调用频率: 每日17:00
        积分消耗: 120
        """
        # 计算交易日期
        if not trade_date and not start_date:
            trade_date = self._calculate_trade_date("daily_basic", trade_date, start_date)

        return await self._sync_data_template(
            data_type=DataType.DAILY_BASIC,
            fetch_method=lambda p, **kw: p.get_daily_basic(**kw),
            insert_method=self._insert_daily_basic,
            validator_method=self.validator.validate_daily_basic,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_adj_factor(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步复权因子数据

        分类: 基础数据
        优先级: P2
        调用频率: 每周一
        积分消耗: 120
        """
        return await self._sync_data_template(
            data_type=DataType.ADJ_FACTOR,
            fetch_method=lambda p, **kw: p.get_adj_factor(**kw),
            insert_method=self._insert_adj_factor,
            validator_method=None,  # 复权因子不需要验证
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_suspend(
        self,
        ts_code: Optional[str] = None,
        suspend_date: Optional[str] = None,
        resume_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步停复牌信息

        分类: 基础数据
        优先级: P3
        调用频率: 每日
        积分消耗: 120
        """
        return await self._sync_data_template(
            data_type=DataType.SUSPEND,
            fetch_method=lambda p, **kw: p.get_suspend(**kw),
            insert_method=self._insert_suspend,
            validator_method=None,
            ts_code=ts_code,
            suspend_date=suspend_date,
            resume_date=resume_date
        )

    # ========== 私有数据插入方法 ==========

    async def _insert_daily_basic(self, df: pd.DataFrame):
        """
        插入每日指标数据

        TODO: 创建 DailyBasicRepository 并使用 bulk_upsert 方法
        """
        from app.core.database import get_async_db
        from sqlalchemy import text

        async with get_async_db() as db:
            records = df.to_dict('records')
            for record in records:
                # 转换日期字段
                if 'trade_date' in record and isinstance(record['trade_date'], str):
                    record['trade_date'] = datetime.strptime(record['trade_date'], '%Y%m%d').date()

                columns = list(record.keys())
                placeholders = [f":{col}" for col in columns]

                query = text(f"""
                    INSERT INTO daily_basic ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        close = EXCLUDED.close,
                        turnover_rate = EXCLUDED.turnover_rate,
                        turnover_rate_f = EXCLUDED.turnover_rate_f,
                        volume_ratio = EXCLUDED.volume_ratio,
                        pe = EXCLUDED.pe,
                        pe_ttm = EXCLUDED.pe_ttm,
                        pb = EXCLUDED.pb,
                        ps = EXCLUDED.ps,
                        ps_ttm = EXCLUDED.ps_ttm,
                        dv_ratio = EXCLUDED.dv_ratio,
                        dv_ttm = EXCLUDED.dv_ttm,
                        total_share = EXCLUDED.total_share,
                        float_share = EXCLUDED.float_share,
                        free_share = EXCLUDED.free_share,
                        total_mv = EXCLUDED.total_mv,
                        circ_mv = EXCLUDED.circ_mv,
                        updated_at = CURRENT_TIMESTAMP
                """)
                await db.execute(query, record)
            await db.commit()

    async def _insert_adj_factor(self, df: pd.DataFrame):
        """
        插入复权因子数据

        TODO: 创建 AdjFactorRepository 并使用 bulk_upsert 方法
        """
        from app.core.database import get_async_db
        from sqlalchemy import text

        async with get_async_db() as db:
            records = df.to_dict('records')
            for record in records:
                if 'trade_date' in record and isinstance(record['trade_date'], str):
                    record['trade_date'] = datetime.strptime(record['trade_date'], '%Y%m%d').date()

                columns = list(record.keys())
                placeholders = [f":{col}" for col in columns]

                query = text(f"""
                    INSERT INTO adj_factor ({', '.join(columns)})
                    VALUES ({', '.join(placeholders)})
                    ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                        adj_factor = EXCLUDED.adj_factor,
                        updated_at = CURRENT_TIMESTAMP
                """)
                await db.execute(query, record)
            await db.commit()

    async def _insert_suspend(self, df: pd.DataFrame):
        """
        插入停复牌信息

        TODO: 创建 SuspendRepository 并使用 bulk_insert 方法
        """
        from app.core.database import get_async_db
        from sqlalchemy import text

        async with get_async_db() as db:
            records = df.to_dict('records')

            for record in records:
                # 转换所有日期字符串为日期对象
                date_fields = ['suspend_date', 'resume_date', 'ann_date']
                for field in date_fields:
                    if field in record and isinstance(record[field], str) and record[field]:
                        record[field] = datetime.strptime(record[field], '%Y%m%d').date()

                # 停复牌信息不使用UPSERT,直接插入
                query = text("""
                    INSERT INTO suspend_info (
                        ts_code, suspend_date, resume_date, ann_date, suspend_reason, reason_type
                    ) VALUES (
                        :ts_code, :suspend_date, :resume_date, :ann_date, :suspend_reason, :reason_type
                    )
                """)

                await db.execute(query, record)

            await db.commit()


# 创建全局单例
basic_data_sync_service = BasicDataSyncService()
