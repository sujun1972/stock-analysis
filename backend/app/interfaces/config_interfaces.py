"""
配置管理服务接口定义
使用 Protocol 提供结构化类型约束
"""

from typing import Protocol, Dict, Optional


class IDataSourceManager(Protocol):
    """
    数据源管理器接口

    定义数据源配置管理的标准契约
    """

    async def get_data_source_config(self) -> Dict:
        """获取数据源配置"""
        ...

    async def get_data_source(self) -> str:
        """获取主数据源"""
        ...

    async def get_minute_data_source(self) -> str:
        """获取分时数据源"""
        ...

    async def get_realtime_data_source(self) -> str:
        """获取实时数据源"""
        ...

    async def get_tushare_token(self) -> str:
        """获取 Tushare Token"""
        ...

    def validate_data_source(self, source: str) -> bool:
        """验证数据源是否支持"""
        ...

    async def validate_tushare_config(
        self,
        data_source: str,
        token: Optional[str] = None
    ) -> bool:
        """验证 Tushare 配置"""
        ...

    async def update_data_source(
        self,
        data_source: str,
        minute_data_source: Optional[str] = None,
        realtime_data_source: Optional[str] = None,
        tushare_token: Optional[str] = None
    ) -> Dict:
        """更新数据源配置"""
        ...

    async def set_data_source(self, source: str) -> Dict:
        """设置主数据源"""
        ...

    async def set_tushare_token(self, token: str) -> Dict:
        """设置 Tushare Token"""
        ...

    async def is_using_tushare(self) -> bool:
        """检查是否正在使用 Tushare"""
        ...

    async def is_using_akshare(self) -> bool:
        """检查是否正在使用 AkShare"""
        ...

    async def switch_to_tushare(self, token: str) -> Dict:
        """切换到 Tushare"""
        ...

    async def switch_to_akshare(self) -> Dict:
        """切换到 AkShare"""
        ...


class ISyncStatusManager(Protocol):
    """
    同步状态管理器接口

    定义同步状态管理的标准契约
    """

    async def get_sync_status(self) -> Dict:
        """获取全局同步状态"""
        ...

    async def update_sync_status(
        self,
        status: Optional[str] = None,
        last_sync_date: Optional[str] = None,
        progress: Optional[int] = None,
        total: Optional[int] = None,
        completed: Optional[int] = None
    ) -> Dict:
        """更新全局同步状态"""
        ...

    async def reset_sync_status(self) -> Dict:
        """重置全局同步状态"""
        ...

    async def set_sync_abort_flag(self, abort: bool = True) -> None:
        """设置同步中止标志"""
        ...

    async def check_sync_abort_flag(self) -> bool:
        """检查是否有中止同步的请求"""
        ...

    async def clear_sync_abort_flag(self) -> None:
        """清除同步中止标志"""
        ...

    async def get_module_sync_status(self, module: str) -> Dict:
        """获取特定模块的同步状态"""
        ...

    async def create_sync_task(
        self,
        task_id: str,
        module: str,
        data_source: str
    ) -> None:
        """创建同步任务记录"""
        ...

    async def update_sync_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        total_count: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        progress: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """更新同步任务状态"""
        ...


class IConfigService(Protocol):
    """
    配置管理服务接口（Facade）

    定义配置管理服务的统一接口契约
    """

    # ==================== 通用配置接口 ====================

    async def get_config(self, key: str) -> Optional[str]:
        """获取单个配置值"""
        ...

    async def get_all_configs(self) -> Dict[str, str]:
        """获取所有配置"""
        ...

    async def set_config(self, key: str, value: str) -> bool:
        """设置单个配置值"""
        ...

    # ==================== 数据源配置接口 ====================

    async def get_data_source_config(self) -> Dict:
        """获取数据源配置"""
        ...

    async def update_data_source(
        self,
        data_source: str,
        minute_data_source: Optional[str] = None,
        realtime_data_source: Optional[str] = None,
        tushare_token: Optional[str] = None
    ) -> Dict:
        """更新数据源配置"""
        ...

    # ==================== 同步状态接口 ====================

    async def get_sync_status(self) -> Dict:
        """获取全局同步状态"""
        ...

    async def update_sync_status(
        self,
        status: Optional[str] = None,
        last_sync_date: Optional[str] = None,
        progress: Optional[int] = None,
        total: Optional[int] = None,
        completed: Optional[int] = None
    ) -> Dict:
        """更新全局同步状态"""
        ...

    async def reset_sync_status(self) -> Dict:
        """重置全局同步状态"""
        ...

    async def set_sync_abort_flag(self, abort: bool = True) -> None:
        """设置同步中止标志"""
        ...

    async def check_sync_abort_flag(self) -> bool:
        """检查是否有中止同步的请求"""
        ...

    async def clear_sync_abort_flag(self) -> None:
        """清除同步中止标志"""
        ...

    # ==================== 模块同步状态接口 ====================

    async def get_module_sync_status(self, module: str) -> Dict:
        """获取特定模块的同步状态"""
        ...

    async def create_sync_task(
        self,
        task_id: str,
        module: str,
        data_source: str
    ) -> None:
        """创建同步任务记录"""
        ...

    async def update_sync_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        total_count: Optional[int] = None,
        success_count: Optional[int] = None,
        failed_count: Optional[int] = None,
        progress: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        """更新同步任务状态"""
        ...
