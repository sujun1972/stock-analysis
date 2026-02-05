"""
数据同步服务接口定义
使用 Protocol 提供结构化类型约束
"""

from typing import Dict, List, Optional, Protocol


class IStockListSyncService(Protocol):
    """
    股票列表同步服务接口

    定义股票列表、新股、退市股票同步的标准契约
    """

    async def sync_stock_list(self) -> Dict:
        """
        同步股票列表

        Returns:
            Dict: {"total": int} - 同步的股票总数
        """
        ...

    async def sync_new_stocks(self, days: int = 30) -> Dict:
        """
        同步新股列表

        Args:
            days: 最近天数

        Returns:
            Dict: {"total": int} - 同步的新股总数
        """
        ...

    async def sync_delisted_stocks(self) -> Dict:
        """
        同步退市股票列表

        Returns:
            Dict: {"total": int} - 同步的退市股票总数
        """
        ...


class IDailySyncService(Protocol):
    """
    日线数据同步服务接口

    定义单只和批量股票日线数据同步的标准契约
    """

    async def sync_single_stock(self, code: str, years: int = 5) -> Dict:
        """
        同步单只股票日线数据

        Args:
            code: 股票代码
            years: 历史年数

        Returns:
            Dict: {"code": str, "records": int}
        """
        ...

    async def sync_batch(
        self,
        codes: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        years: Optional[int] = None,
    ) -> Dict:
        """
        批量同步日线数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            years: 历史年数

        Returns:
            Dict: {"success": int, "failed": int, "skipped": int, "total": int, "aborted": bool}
        """
        ...


class IRealtimeSyncService(Protocol):
    """
    实时行情同步服务接口

    定义实时行情和分时数据同步的标准契约
    """

    async def sync_minute_data(self, code: str, period: str = "5", days: int = 5) -> Dict:
        """
        同步分时数据

        Args:
            code: 股票代码
            period: 分时周期
            days: 同步天数

        Returns:
            Dict: {"code": str, "period": str, "records": int}
        """
        ...

    async def sync_realtime_quotes(
        self,
        codes: Optional[List[str]] = None,
        batch_size: Optional[int] = 100,
        update_oldest: bool = False,
    ) -> Dict:
        """
        同步实时行情

        Args:
            codes: 股票代码列表
            batch_size: 每批次更新的股票数量
            update_oldest: 是否优先更新最旧的数据

        Returns:
            Dict: {"total": int, "batch_size": ..., "update_mode": str, ...}
        """
        ...


class ISyncService(Protocol):
    """
    通用同步服务接口

    定义同步状态管理和控制的标准契约
    """

    async def get_sync_status(self) -> Dict:
        """获取全局同步状态"""
        ...

    async def get_module_sync_status(self, module: str) -> Dict:
        """获取模块同步状态"""
        ...

    async def abort_sync(self) -> Dict:
        """中止当前同步任务"""
        ...
