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

from typing import Optional, Dict, Any, List
import asyncio
import pandas as pd
from loguru import logger

from app.repositories import (
    MoneyflowRepository,
    MoneyflowHsgtRepository,
    MoneyflowMktDcRepository,
    MoneyflowIndDcRepository,
    MoneyflowStockDcRepository
)
from app.services.trading_calendar_service import trading_calendar_service
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
            trade_date = trading_calendar_service.get_latest_data_date_sync()
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
            trade_date = trading_calendar_service.get_latest_data_date_sync()
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
            trade_date = trading_calendar_service.get_latest_data_date_sync()
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
            trade_date = trading_calendar_service.get_latest_data_date_sync()
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
            trade_date = trading_calendar_service.get_latest_data_date_sync()
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
