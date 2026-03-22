"""
扩展数据同步服务 - 模块化架构

模块按照数据分类划分:
- basic_data_sync: 基础数据 (daily_basic, stk_limit, adj_factor, suspend)
- moneyflow_sync: 资金流向 (moneyflow, moneyflow_hsgt, moneyflow_mkt_dc, moneyflow_ind_dc, moneyflow_stock_dc)
- margin_sync: 两融数据 (margin_detail)
- reference_data_sync: 参考数据 (block_trade)

重构完成时间: 2026-03-22
"""

from .common import DataType, SyncResult, generate_task_id
from .base_sync_service import BaseSyncService
from .basic_data_sync import BasicDataSyncService, basic_data_sync_service
from .moneyflow_sync import MoneyflowSyncService, moneyflow_sync_service
from .margin_sync import MarginSyncService, margin_sync_service
from .reference_data_sync import ReferenceDataSyncService, reference_data_sync_service

# 统一导出
__all__ = [
    # 公共组件
    'DataType',
    'SyncResult',
    'generate_task_id',

    # 基础类
    'BaseSyncService',

    # 服务类
    'BasicDataSyncService',
    'MoneyflowSyncService',
    'MarginSyncService',
    'ReferenceDataSyncService',

    # 服务实例
    'basic_data_sync_service',
    'moneyflow_sync_service',
    'margin_sync_service',
    'reference_data_sync_service',

    # 聚合服务（向后兼容）
    'ExtendedDataSyncService',
    'extended_sync_service',
]


class ExtendedDataSyncService:
    """
    扩展数据同步服务 - 统一聚合服务（向后兼容）

    这个类聚合所有模块化的同步服务，提供统一的接口。
    原有代码可以继续使用 ExtendedDataSyncService，无需修改。

    推荐使用方式:
        # 方式1: 使用专门的服务类（推荐）
        from app.services.extended_sync import basic_data_sync_service
        result = await basic_data_sync_service.sync_daily_basic()

        # 方式2: 使用统一服务（向后兼容）
        from app.services.extended_sync import extended_sync_service
        result = await extended_sync_service.sync_daily_basic()
    """

    def __init__(self):
        # 注入专门的服务实例
        self._basic_data = basic_data_sync_service
        self._moneyflow = moneyflow_sync_service
        self._margin = margin_sync_service
        self._reference_data = reference_data_sync_service

        # 保留共享组件（为了向后兼容）
        self.provider_factory = self._basic_data.provider_factory
        self.validator = self._basic_data.validator

    # ========== 基础数据同步方法 ==========

    async def sync_daily_basic(self, **kwargs):
        """同步每日指标数据"""
        return await self._basic_data.sync_daily_basic(**kwargs)

    async def sync_stk_limit(self, **kwargs):
        """同步涨跌停价格数据"""
        return await self._basic_data.sync_stk_limit(**kwargs)

    async def sync_adj_factor(self, **kwargs):
        """同步复权因子数据"""
        return await self._basic_data.sync_adj_factor(**kwargs)

    async def sync_suspend(self, **kwargs):
        """同步停复牌信息"""
        return await self._basic_data.sync_suspend(**kwargs)

    # ========== 资金流向同步方法 ==========

    async def sync_moneyflow(self, **kwargs):
        """同步资金流向数据(Tushare标准)"""
        return await self._moneyflow.sync_moneyflow(**kwargs)

    async def sync_moneyflow_hsgt(self, **kwargs):
        """同步沪深港通资金流向"""
        return await self._moneyflow.sync_moneyflow_hsgt(**kwargs)

    async def sync_moneyflow_mkt_dc(self, **kwargs):
        """同步大盘资金流向(DC)"""
        return await self._moneyflow.sync_moneyflow_mkt_dc(**kwargs)

    async def sync_moneyflow_ind_dc(self, **kwargs):
        """同步板块资金流向(DC)"""
        return await self._moneyflow.sync_moneyflow_ind_dc(**kwargs)

    async def sync_moneyflow_stock_dc(self, **kwargs):
        """同步个股资金流向(DC)"""
        return await self._moneyflow.sync_moneyflow_stock_dc(**kwargs)

    # ========== 两融数据同步方法 ==========

    async def sync_margin_detail(self, **kwargs):
        """同步融资融券交易明细"""
        return await self._margin.sync_margin_detail(**kwargs)

    # ========== 参考数据同步方法 ==========

    async def sync_block_trade(self, **kwargs):
        """同步大宗交易数据"""
        return await self._reference_data.sync_block_trade(**kwargs)

    # ========== 向后兼容的内部方法 ==========

    def _get_provider(self):
        """获取Tushare数据提供者（向后兼容）"""
        return self._basic_data._get_provider()


# 创建全局单例（向后兼容）
extended_sync_service = ExtendedDataSyncService()
