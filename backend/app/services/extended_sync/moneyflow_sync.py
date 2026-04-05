"""
扩展数据同步 - 资金流向同步服务

分类: 资金流向
包含数据:
- moneyflow: 个股资金流向 (Tushare标准接口)
- moneyflow_hsgt: 沪深港通资金流向 (北向+南向)
- moneyflow_mkt_dc: 大盘资金流向 (东方财富DC)
- moneyflow_ind_dc: 板块资金流向 (东方财富DC)
- moneyflow_stock_dc: 个股资金流向 (东方财富DC)
"""

from typing import Optional, Dict, Any, List, Callable
import asyncio
from datetime import datetime
import pandas as pd
from loguru import logger

from app.repositories import (
    MoneyflowRepository,
    MoneyflowHsgtRepository,
    MoneyflowMktDcRepository,
    MoneyflowIndDcRepository,
    MoneyflowStockDcRepository
)
from app.repositories.trading_calendar_repository import TradingCalendarRepository
from app.repositories.stock_basic_repository import StockBasicRepository
from .base_sync_service import BaseSyncService
from .common import DataType


class MoneyflowSyncService(BaseSyncService):
    """资金流向同步服务"""

    def __init__(self):
        super().__init__()
        # 初始化 Repositories
        self.moneyflow_repo = MoneyflowRepository()
        self.moneyflow_hsgt_repo = MoneyflowHsgtRepository()
        self.moneyflow_mkt_dc_repo = MoneyflowMktDcRepository()
        self.moneyflow_ind_dc_repo = MoneyflowIndDcRepository()
        self.moneyflow_stock_dc_repo = MoneyflowStockDcRepository()
        self.calendar_repo = TradingCalendarRepository()

    # ========== 公共同步方法 ==========

    async def sync_moneyflow(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        stock_list: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        同步资金流向数据(Tushare标准接口)

        分类: 资金流向
        数据源: pro.moneyflow() - 基于主动买卖单统计的资金流向
        优先级: P0
        调用频率: 每日17:30
        积分消耗: 2000(高消耗,需要控制调用频率)

        Note:
            - 不指定股票代码时,直接使用日期参数查询,Tushare会返回该日期所有有数据的股票
            - 单次最大提取6000行记录
            - 股票和时间参数至少输入一个
        """
        # 资金流向支持当前日期
        if not trade_date and not start_date:
            trade_date = self.calendar_repo.get_latest_trading_day()
            logger.info(f"资金流向: 使用日期 {trade_date}")

        return await self._sync_data_template(
            data_type=DataType.MONEYFLOW,
            fetch_method=lambda p, **kw: p.get_moneyflow(**kw),
            insert_method=self._insert_moneyflow,
            validator_method=self.validator.validate_moneyflow,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_moneyflow_hsgt(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步沪深港通资金流向数据

        分类: 资金流向
        包含北向资金(沪股通+深股通)和南向资金(港股通上海+港股通深圳)的每日资金流向。
        数据从Tushare获取,支持2026年及以后的最新数据。

        优先级: P0
        调用频率: 每日收盘后
        积分消耗: 2000
        """
        if not trade_date and not start_date:
            trade_date = self.calendar_repo.get_latest_trading_day()
            logger.info(f"沪深港通资金流向: 使用日期 {trade_date}")

        return await self._sync_data_template(
            data_type=DataType.MONEYFLOW_HSGT,
            fetch_method=lambda p, **kw: p.get_moneyflow_hsgt(**kw),
            insert_method=self._insert_moneyflow_hsgt,
            validator_method=None,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_moneyflow_mkt_dc(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步大盘资金流向数据(东方财富DC)

        分类: 资金流向
        包含大盘主力资金流向、超大单、大单、中单、小单的流入流出情况。
        数据从Tushare获取,每日盘后更新。

        优先级: P1
        调用频率: 每日盘后
        积分消耗: 120(试用) / 6000(正式)
        """
        if not trade_date and not start_date:
            trade_date = self.calendar_repo.get_latest_trading_day()
            logger.info(f"大盘资金流向: 使用日期 {trade_date}")

        return await self._sync_data_template(
            data_type=DataType.MONEYFLOW_MKT_DC,
            fetch_method=lambda p, **kw: p.get_moneyflow_mkt_dc(**kw),
            insert_method=self._insert_moneyflow_mkt_dc,
            validator_method=None,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_moneyflow_ind_dc(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步板块资金流向数据(东财概念及行业板块资金流向 DC)

        分类: 资金流向
        包含行业、概念、地域板块的资金流向数据,包括主力资金、超大单、大单、中单、小单的流入流出情况。
        数据从Tushare获取,每天盘后更新。

        优先级: P2
        调用频率: 每日盘后
        积分消耗: 6000
        单次最大: 5000条数据
        """
        if not trade_date and not start_date:
            trade_date = self.calendar_repo.get_latest_trading_day()
            logger.info(f"板块资金流向: 使用日期 {trade_date}")

        return await self._sync_data_template(
            data_type=DataType.MONEYFLOW_IND_DC,
            fetch_method=lambda p, **kw: p.get_moneyflow_ind_dc(**kw),
            insert_method=self._insert_moneyflow_ind_dc,
            validator_method=None,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date,
            content_type=content_type
        )

    async def sync_moneyflow_stock_dc(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步个股资金流向数据(东方财富DC)

        分类: 资金流向
        包含个股主力资金、超大单、大单、中单、小单的流入流出情况。
        数据从Tushare获取,每日盘后更新。数据开始于20230911。

        优先级: P2
        调用频率: 每日盘后
        积分消耗: 5000
        单次最大: 6000条数据
        """
        if not trade_date and not start_date:
            trade_date = self.calendar_repo.get_latest_trading_day()
            logger.info(f"个股资金流向: 使用日期 {trade_date}")

        return await self._sync_data_template(
            data_type=DataType.MONEYFLOW_STOCK_DC,
            fetch_method=lambda p, **kw: p.get_moneyflow_stock_dc(**kw),
            insert_method=self._insert_moneyflow_stock_dc,
            validator_method=None,
            ts_code=ts_code,
            trade_date=trade_date,
            start_date=start_date,
            end_date=end_date
        )

    async def sync_moneyflow_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        concurrency: int = 5,
        update_state_fn: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        按股票代码逐只同步个股资金流向全量历史数据

        策略：仅支持 ts_code 维度的逐只请求（Tushare moneyflow 接口按日期全市场拉取
        单次上限 6000 条，历史年份数据极易截断，因此改为逐只请求保证完整性）。

        支持中断续继：Redis Set 记录已完成的 ts_code，重新触发时自动跳过。

        Redis Key: sync:moneyflow:full_history:progress

        Args:
            redis_client: Redis 连接实例
            start_date: 开始日期 YYYYMMDD，默认 20100101
            concurrency: 并发数，来自 sync_configs.full_sync_concurrency，默认 5
            update_state_fn: Celery update_state 回调，用于上报进度

        Returns:
            {"status": "success", "total": int, "success": int, "skipped": int, "errors": int}
        """
        PROGRESS_KEY = "sync:moneyflow:full_history:progress"
        CONCURRENCY = max(1, concurrency)
        BATCH_SIZE = 50
        effective_start = start_date or "20100101"
        today = datetime.now().strftime("%Y%m%d")

        stock_repo = StockBasicRepository()
        all_ts_codes = await asyncio.to_thread(stock_repo.get_listed_ts_codes, status='L')
        total = len(all_ts_codes)
        logger.info(f"[全量资金流向] 共 {total} 只上市股票")

        completed_set = {
            v.decode() if isinstance(v, bytes) else v
            for v in redis_client.smembers(PROGRESS_KEY)
        }
        pending_codes = [c for c in all_ts_codes if c not in completed_set]
        skip_count = len(completed_set)
        logger.info(f"[全量资金流向] 已完成 {skip_count} 只，剩余 {len(pending_codes)} 只")

        success_count = 0
        error_count = 0
        sem = asyncio.Semaphore(CONCURRENCY)

        def sync_one_sync(ts_code: str):
            """同步版本，在线程池中执行，避免 Tushare 同步 I/O 阻塞事件循环"""
            import asyncio as _asyncio
            loop = _asyncio.new_event_loop()
            try:
                return loop.run_until_complete(
                    self._sync_data_template(
                        data_type=DataType.MONEYFLOW,
                        fetch_method=lambda p, **kw: p.get_moneyflow(**kw),
                        insert_method=self._insert_moneyflow,
                        validator_method=None,
                        ts_code=ts_code,
                        start_date=effective_start,
                        end_date=today
                    )
                )
            finally:
                loop.close()

        async def sync_one(ts_code: str):
            async with sem:
                try:
                    result = await asyncio.to_thread(sync_one_sync, ts_code)
                    if result.get("status") == "error":
                        return ts_code, False, result.get("error", "未知错误")
                    return ts_code, True, None
                except Exception as e:
                    return ts_code, False, str(e)

        for batch_start in range(0, len(pending_codes), BATCH_SIZE):
            batch = pending_codes[batch_start:batch_start + BATCH_SIZE]
            results = await asyncio.gather(*[sync_one(c) for c in batch])

            for ts_code, ok, err in results:
                if ok:
                    redis_client.sadd(PROGRESS_KEY, ts_code)
                    success_count += 1
                else:
                    error_count += 1
                    logger.error(f"[全量资金流向] 同步 {ts_code} 失败（下次续继）: {err}")

            done = skip_count + success_count
            if update_state_fn:
                pct = round(done / total * 100, 1) if total else 0
                update_state_fn(
                    state='PROGRESS',
                    meta={
                        'progress': pct,   # 前端 & 后端统一读此字段
                        'current': done,
                        'total': total,
                        'success': success_count,
                        'errors': error_count
                    }
                )
            logger.info(
                f"[全量资金流向] 进度: {done}/{total} ({round(done/total*100,1)}%) "
                f"| 本次成功={success_count} 失败={error_count}"
            )

        final_done = len(redis_client.smembers(PROGRESS_KEY))
        if final_done >= total:
            redis_client.delete(PROGRESS_KEY)
            logger.info("[全量资金流向] ✅ 全部完成，进度已清除")

        return {
            "status": "success",
            "total": total,
            "success": success_count,
            "skipped": skip_count,
            "errors": error_count,
            "completed": final_done
        }

    # ========== 私有数据插入方法 ==========

    async def _insert_moneyflow(self, df: pd.DataFrame):
        """插入资金流向数据(Tushare标准接口)"""
        await asyncio.to_thread(self.moneyflow_repo.bulk_upsert, df)

    async def _insert_moneyflow_hsgt(self, df: pd.DataFrame):
        """插入沪深港通资金流向数据"""
        await asyncio.to_thread(self.moneyflow_hsgt_repo.bulk_upsert, df)

    async def _insert_moneyflow_mkt_dc(self, df: pd.DataFrame):
        """插入大盘资金流向数据"""
        await asyncio.to_thread(self.moneyflow_mkt_dc_repo.bulk_upsert, df)

    async def _insert_moneyflow_ind_dc(self, df: pd.DataFrame):
        """插入板块资金流向数据"""
        await asyncio.to_thread(self.moneyflow_ind_dc_repo.bulk_upsert, df)

    async def _insert_moneyflow_stock_dc(self, df: pd.DataFrame):
        """插入个股资金流向数据"""
        await asyncio.to_thread(self.moneyflow_stock_dc_repo.bulk_upsert, df)


# 创建全局单例
moneyflow_sync_service = MoneyflowSyncService()
