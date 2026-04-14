"""
同步历史记录 Repository

管理 sync_history 表，记录每次增量/全量同步的执行情况。
"""

from datetime import datetime
from typing import Optional, Dict, List
from loguru import logger

from app.repositories.base_repository import BaseRepository


class SyncHistoryRepository(BaseRepository):
    TABLE_NAME = "sync_history"

    def __init__(self, db=None):
        super().__init__(db)

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def create(
        self,
        table_key: str,
        sync_type: str,
        sync_strategy: Optional[str],
        data_start_date: Optional[str] = None,
    ) -> int:
        """
        创建一条同步历史记录（状态为 running），返回 id。

        Args:
            table_key: sync_configs.table_key
            sync_type: 'incremental' | 'full'
            sync_strategy: 'by_date'|'by_month'|'by_ts_code'|'snapshot' 等，无时间段时为 None
            data_start_date: 请求的时间范围起始 YYYYMMDD

        Returns:
            新记录的 id
        """
        rows = self.execute_query_returning(
            """
            INSERT INTO sync_history (table_key, sync_type, sync_strategy, data_start_date, started_at, status)
            VALUES (%s, %s, %s, %s, NOW(), 'running')
            RETURNING id
            """,
            (table_key, sync_type, sync_strategy, data_start_date),
        )
        record_id = rows[0][0] if rows else None
        logger.debug(f"[sync_history] 创建记录 id={record_id} table={table_key} type={sync_type}")
        return record_id

    def complete(
        self,
        record_id: int,
        status: str,
        records: int = 0,
        data_end_date: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        完成同步历史记录（写入结束时间、结果、实际数据最大日期）。

        Args:
            record_id: create() 返回的 id
            status: 'success' | 'failure'
            records: 入库条数
            data_end_date: 实际入库数据中最大日期 YYYYMMDD
            error: 失败时的错误信息
        """
        self.execute_update(
            """
            UPDATE sync_history
            SET completed_at  = NOW(),
                status        = %s,
                records       = %s,
                data_end_date = %s,
                error         = %s
            WHERE id = %s
            """,
            (status, records, data_end_date, error, record_id),
        )
        logger.debug(f"[sync_history] 完成记录 id={record_id} status={status} records={records} end={data_end_date}")

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_last_success(
        self,
        table_key: str,
        sync_type: str = 'incremental',
    ) -> Optional[Dict]:
        """
        获取某表最近一次成功同步记录。

        Returns:
            dict with keys: id, sync_strategy, data_start_date, data_end_date, completed_at
            or None if not found
        """
        rows = self.execute_query(
            """
            SELECT id, sync_strategy, data_start_date, data_end_date, completed_at
            FROM sync_history
            WHERE table_key = %s AND sync_type = %s AND status = 'success'
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (table_key, sync_type),
        )
        if not rows:
            return None
        r = rows[0]
        return {
            'id': r[0],
            'sync_strategy': r[1],
            'data_start_date': r[2],
            'data_end_date': r[3],
            'completed_at': r[4].isoformat() + 'Z' if r[4] else None,
        }

    def get_last_end_date(
        self,
        table_key: str,
        sync_type: str = 'incremental',
    ) -> Optional[str]:
        """
        获取最近一次成功的按时间段同步的 data_end_date（YYYYMMDD）。
        by_ts_code / snapshot 等无时间段策略的记录不计入。

        Returns:
            YYYYMMDD string or None
        """
        rows = self.execute_query(
            """
            SELECT data_end_date
            FROM sync_history
            WHERE table_key = %s
              AND sync_type  = %s
              AND status     = 'success'
              AND data_end_date IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (table_key, sync_type),
        )
        if not rows or not rows[0][0]:
            return None
        return rows[0][0]

    def get_max_completed_at(
        self,
        table_keys: List[str],
    ) -> Optional[str]:
        """
        获取指定表集合中最近一次成功同步的 completed_at 时间戳（ISO 格式）。

        用于分析缓存失效判断：如果依赖的数据表在缓存生成后有过新的成功同步，
        说明底层数据已变更，缓存需要重新生成。

        Args:
            table_keys: 数据表标识列表（sync_configs.table_key）

        Returns:
            最大 completed_at 的 ISO 字符串（如 '2026-04-14T15:30:00Z'），
            或 None（如果这些表从未成功同步过）
        """
        if not table_keys:
            return None
        placeholders = ", ".join(["%s"] * len(table_keys))
        rows = self.execute_query(
            f"""
            SELECT MAX(completed_at)
            FROM sync_history
            WHERE table_key IN ({placeholders})
              AND status = 'success'
            """,
            tuple(table_keys),
        )
        if not rows or not rows[0][0]:
            return None
        return rows[0][0].isoformat() + 'Z'

    def get_recent(
        self,
        table_key: str,
        limit: int = 20,
    ) -> List[Dict]:
        """获取某表最近 N 条同步历史记录。"""
        rows = self.execute_query(
            """
            SELECT id, sync_type, sync_strategy,
                   started_at, completed_at,
                   data_start_date, data_end_date,
                   records, status, error
            FROM sync_history
            WHERE table_key = %s
            ORDER BY started_at DESC
            LIMIT %s
            """,
            (table_key, limit),
        )
        result = []
        for r in rows:
            result.append({
                'id': r[0],
                'sync_type': r[1],
                'sync_strategy': r[2],
                'started_at': r[3].isoformat() + 'Z' if r[3] else None,
                'completed_at': r[4].isoformat() + 'Z' if r[4] else None,
                'data_start_date': r[5],
                'data_end_date': r[6],
                'records': r[7],
                'status': r[8],
                'error': r[9],
            })
        return result
