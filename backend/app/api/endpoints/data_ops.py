"""
数据操作 API（批量清空、全量同步辅助）

提供通用的数据表清空端点，供各数据页面的"清空数据"按钮调用。
使用白名单机制防止误操作或注入攻击。
"""

from typing import Optional

import asyncio
from fastapi import APIRouter, Depends, Query
from loguru import logger

from app.api.error_handler import handle_api_errors
from app.models.api_response import ApiResponse
from app.core.dependencies import require_admin
from app.models.user import User
from app.repositories.base_repository import BaseRepository

router = APIRouter()

# ========== 允许清空的表名白名单 ==========
# 键：前端传入的 table_key（URL友好）
# 值：实际数据库表名
CLEARABLE_TABLES: dict[str, str] = {
    # 基础数据
    "trade_cal":        "trade_cal",
    "stock_st":         "stock_st",
    # 行情数据
    "stock_daily":      "stock_daily",
    "adj_factor":       "adj_factor",
    "daily_basic":      "daily_basic",
    "stk_limit_d":      "stk_limit_d",
    "suspend":          "suspend",
    "hsgt_top10":       "hsgt_top10",
    "ggt_top10":        "ggt_top10",
    "ggt_daily":        "ggt_daily",
    "ggt_monthly":      "ggt_monthly",
    # 财务数据
    "income":           "income",
    "balancesheet":     "balancesheet",
    "cashflow":         "cashflow",
    "forecast":         "forecast",
    "express":          "express",
    "dividend":         "dividend",
    "fina_indicator":   "fina_indicator",
    "fina_audit":       "fina_audit",
    "fina_mainbz":      "fina_mainbz",
    "disclosure_date":  "disclosure_date",
    # 参考数据
    "stk_shock":        "stk_shock",
    "stk_high_shock":   "stk_high_shock",
    "stk_alert":        "stk_alert",
    "pledge_stat":      "pledge_stat",
    "repurchase":       "repurchase",
    "share_float":      "share_float",
    "stk_holdernumber": "stk_holdernumber",
    "block_trade":      "block_trade",
    "stk_holdertrade":  "stk_holdertrade",
    # 特色数据
    "report_rc":        "report_rc",
    "cyq_perf":         "cyq_perf",
    "cyq_chips":        "cyq_chips",
    "ccass_hold":       "ccass_hold",
    "ccass_hold_detail":"ccass_hold_detail",
    "hk_hold":          "hk_hold",
    "stk_auction_o":    "stk_auction_o",
    "stk_auction_c":    "stk_auction_c",
    "stk_nineturn":     "stk_nineturn",
    "stk_ah_comparison":"stk_ah_comparison",
    "stk_surv":         "stk_surv",
    "broker_recommend": "broker_recommend",
    # 两融数据
    "margin":           "margin",
    "margin_detail":    "margin_detail",
    "margin_secs":      "margin_secs",
    "slb_len":          "slb_len",
    # 资金流向
    "moneyflow":        "moneyflow",
    "moneyflow_hsgt":   "moneyflow_hsgt",
    "moneyflow_mkt_dc": "moneyflow_mkt_dc",
    "moneyflow_ind_dc": "moneyflow_ind_dc",
    "moneyflow_stock_dc":"moneyflow_stock_dc",
    # 打板专题
    "top_list":         "top_list",
    "top_inst":         "top_inst",
    "limit_list":       "limit_list_d",
    "limit_step":       "limit_step",
    "limit_cpt":        "limit_cpt_list",
    "dc_index":         "dc_index",
    "dc_member":        "dc_member",
    "dc_daily":         "dc_daily",
}


class _ClearRepo(BaseRepository):
    """临时 Repository，仅用于执行 TRUNCATE。"""

    TABLE_NAME = ""  # 动态设置

    def truncate_table(self, table_name: str) -> int:
        """TRUNCATE 指定表，返回 0（TRUNCATE 不返回行数）。"""
        # 表名已经过白名单验证，此处可安全拼接
        query = f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"
        self.execute_update(query, ())
        return 0

    def delete_by_date_range(self, table_name: str, start_date: Optional[str], end_date: Optional[str]) -> int:
        """按日期范围删除，返回删除行数。"""
        params = []
        conditions = []
        # 尝试常见日期列名
        date_col = "trade_date"
        if start_date:
            conditions.append(f"{date_col} >= %s")
            params.append(start_date)
        if end_date:
            conditions.append(f"{date_col} <= %s")
            params.append(end_date)
        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"DELETE FROM {table_name} WHERE {where}"
        return self.execute_update(query, tuple(params))


@router.post("/clear/{table_key}")
@handle_api_errors
async def clear_table(
    table_key: str,
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD，留空则清空全表"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD，留空则清空全表"),
    current_user: User = Depends(require_admin),
):
    """
    清空指定数据表（或按日期范围删除）。

    - **table_key**: 数据表标识（白名单控制）
    - **start_date / end_date**: 可选，按 trade_date 范围删除；留空则 TRUNCATE 全表
    """
    table_name = CLEARABLE_TABLES.get(table_key)
    if not table_name:
        return ApiResponse.error(
            message=f"不允许清空的表: {table_key}",
            code=400,
        )

    repo = _ClearRepo()

    if start_date or end_date:
        deleted = await asyncio.to_thread(repo.delete_by_date_range, table_name, start_date, end_date)
        logger.info(f"已删除 {table_name} 中 {deleted} 条记录（{start_date} ~ {end_date}）")
        return ApiResponse.success(
            data={"table": table_key, "deleted": deleted, "mode": "range"},
            message=f"已删除 {deleted} 条记录",
        )
    else:
        await asyncio.to_thread(repo.truncate_table, table_name)
        logger.info(f"已清空表 {table_name}")
        return ApiResponse.success(
            data={"table": table_key, "deleted": -1, "mode": "truncate"},
            message=f"已清空表 {table_key}",
        )
