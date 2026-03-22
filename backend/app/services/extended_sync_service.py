"""
扩展数据同步服务（已废弃）

⚠️ DEPRECATED: 此文件已废弃，请使用模块化的新架构

新架构位置：app.services.extended_sync
- BasicDataSyncService: 基础数据同步 (daily_basic, stk_limit, adj_factor, suspend)
- MoneyflowSyncService: 资金流向同步 (moneyflow系列)
- MarginSyncService: 两融数据同步 (margin_detail)
- ReferenceDataSyncService: 参考数据同步 (block_trade)

迁移示例：
    # 旧代码
    from app.services.extended_sync_service import ExtendedDataSyncService, extended_sync_service

    # 新代码（推荐）
    from app.services.extended_sync import basic_data_sync_service
    result = await basic_data_sync_service.sync_daily_basic()

    # 新代码（向后兼容）
    from app.services.extended_sync import extended_sync_service
    result = await extended_sync_service.sync_daily_basic()

重构时间：2026-03-22
计划移除时间：2026年9月

---

原有文档（已过时）：

用于同步Tushare扩展数据(资金流向、每日指标、北向资金等)。
采用模板方法模式统一同步流程,减少代码重复,提高可维护性。
"""

import warnings

# 显示废弃警告
warnings.warn(
    "extended_sync_service.py 已废弃，请使用 app.services.extended_sync 模块。"
    "详见文件顶部的迁移指南。",
    DeprecationWarning,
    stacklevel=2
)

# 导入新架构的类和实例（向后兼容）
from app.services.extended_sync import (
    ExtendedDataSyncService,
    extended_sync_service,
    DataType,
    SyncResult
)

# 确保向后兼容
__all__ = [
    'ExtendedDataSyncService',
    'extended_sync_service',
    'DataType',
    'SyncResult'
]
