"""
扩展数据同步 - 公共组件

包含所有同步服务共享的枚举、数据类和工具函数。
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class DataType(str, Enum):
    """数据类型枚举"""
    # 基础数据
    DAILY_BASIC = "daily_basic"
    ADJ_FACTOR = "adj_factor"
    SUSPEND = "suspend"

    # 资金流向
    MONEYFLOW = "moneyflow"
    MONEYFLOW_HSGT = "moneyflow_hsgt"
    MONEYFLOW_MKT_DC = "moneyflow_mkt_dc"
    MONEYFLOW_IND_DC = "moneyflow_ind_dc"
    MONEYFLOW_STOCK_DC = "moneyflow_stock_dc"

    # 两融数据
    MARGIN_DETAIL = "margin_detail"

    # 参考数据
    BLOCK_TRADE = "block_trade"


@dataclass
class SyncResult:
    """
    同步结果数据类

    Attributes:
        task_id: 任务唯一标识
        status: 任务状态('success' 或 'error')
        records: 同步的记录数
        validation_errors: 数据验证错误数
        validation_warnings: 数据验证警告数
        message: 结果描述信息
        error: 错误信息(仅在status='error'时有值)
    """
    task_id: str
    status: str
    records: int
    validation_errors: int = 0
    validation_warnings: int = 0
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典,过滤掉默认值"""
        result = {
            "task_id": self.task_id,
            "status": self.status,
            "records": self.records,
            "message": self.message
        }
        if self.validation_errors > 0:
            result["validation_errors"] = self.validation_errors
        if self.validation_warnings > 0:
            result["validation_warnings"] = self.validation_warnings
        if self.error:
            result["error"] = self.error
        return result


def generate_task_id(task_type: str) -> str:
    """生成任务ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{task_type}_{timestamp}"
