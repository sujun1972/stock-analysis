"""股票价值度量 Repository

管理 stock_value_metrics 表（维度型，每股票一行最新值）。
计算逻辑由 ValueMetricsService 完成，本 Repository 只负责数据库读写。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from app.repositories.base_repository import BaseRepository


class ValueMetricsRepository(BaseRepository):
    """stock_value_metrics 表 Repository"""

    TABLE_NAME = "stock_value_metrics"

    COLUMNS = (
        "ts_code",
        "roc", "earnings_yield",
        "intrinsic_value", "intrinsic_margin", "g_rate", "g_source",
        "ebit", "basic_eps", "total_mv", "ev",
        "working_capital", "net_fixed_assets", "latest_price",
        "income_end_date", "balance_end_date", "quote_trade_date",
    )

    def upsert_one(self, row: Dict[str, Any]) -> int:
        """UPSERT 单条 value_metrics 记录，主键 ts_code。"""
        cols = list(self.COLUMNS)
        placeholders = ",".join(["%s"] * len(cols))
        update_set = ",".join([f"{c} = EXCLUDED.{c}" for c in cols if c != "ts_code"])
        query = f"""
            INSERT INTO {self.TABLE_NAME} ({",".join(cols)}, computed_at, updated_at)
            VALUES ({placeholders}, NOW(), NOW())
            ON CONFLICT (ts_code) DO UPDATE SET
                {update_set},
                computed_at = NOW(),
                updated_at = NOW()
        """
        values = tuple(row.get(c) for c in cols)
        try:
            return self.execute_update(query, values)
        except Exception as e:
            logger.error(f"[value_metrics] upsert 失败 ts_code={row.get('ts_code')}: {e}")
            raise

    def get_by_ts_codes(self, ts_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """按 ts_code 批量取最新一行，返回 {ts_code: row_dict}。"""
        if not ts_codes:
            return {}
        placeholders = ",".join(["%s"] * len(ts_codes))
        cols = ",".join(self.COLUMNS)
        query = f"SELECT {cols} FROM {self.TABLE_NAME} WHERE ts_code IN ({placeholders})"
        rows = self.execute_query(query, tuple(ts_codes))
        col_names = self.COLUMNS
        return {
            row[0]: {col: row[idx] for idx, col in enumerate(col_names)}
            for row in rows
        }

    def delete_by_ts_code(self, ts_code: str) -> int:
        """删除单只股票的快照（用于重算前清理或退市清理）。"""
        return self.execute_update(
            f"DELETE FROM {self.TABLE_NAME} WHERE ts_code = %s", (ts_code,)
        )

    def count(self) -> int:
        rows = self.execute_query(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")
        return int(rows[0][0]) if rows else 0
