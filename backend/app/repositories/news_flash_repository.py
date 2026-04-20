"""
财经快讯数据仓储（news_flash）

数据源：AkShare `stock_news_main_cx`（财新） + `stock_news_em`（东财个股）。
表结构见 db_init/migrations/121_create_news_flash.sql。

主键是 (id, publish_time)（TimescaleDB 要求分区列参与主键），但实际业务"唯一"
是 (source, title, publish_time)—— bulk_upsert 先查已存在的三元组再 INSERT 剩余。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


def _to_py(value: Any) -> Any:
    """将 pandas / numpy 类型转为 psycopg2 可识别的 Python 原生类型。"""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, 'item'):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass
    return value


class NewsFlashRepository(BaseRepository):
    """财经快讯仓储"""

    TABLE_NAME = "news_flash"

    SORTABLE_COLUMNS = {'publish_time', 'source', 'created_at'}

    # -------------------------------------------------
    # 写入
    # -------------------------------------------------

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """批量写入快讯（按 (source, title, publish_time) 去重后 INSERT）。

        TimescaleDB hypertable 无法跨分区建 UNIQUE 约束，此处采用"先查已存在 → 只插新"
        的策略，避免重复写入导致 GIN 索引膨胀。

        Args:
            df: 列至少 publish_time / source / title / summary / url / tags / related_ts_codes

        Returns:
            实际插入行数
        """
        if df is None or df.empty:
            return 0

        required = ['publish_time', 'source', 'title']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"[news_flash] bulk_upsert 缺少必填列: {missing}")

        # 1) 查已存在（按 source + title + publish_time 三元组）
        keys: List[tuple] = []
        for _, row in df.iterrows():
            keys.append((
                _to_py(row.get('source')),
                _to_py(row.get('title')),
                _to_py(row.get('publish_time')),
            ))

        if not keys:
            return 0

        # 按 source 分组查，减小参数膨胀
        by_source: Dict[str, List[tuple]] = {}
        for src, title, pt in keys:
            by_source.setdefault(src or 'unknown', []).append((title, pt))

        existing: set = set()
        for src, pairs in by_source.items():
            placeholders = ','.join(['(%s, %s)'] * len(pairs))
            flat_params: List[Any] = [src]
            for title, pt in pairs:
                flat_params.extend([title, pt])
            query = f"""
                SELECT title, publish_time
                FROM {self.TABLE_NAME}
                WHERE source = %s AND (title, publish_time) IN ({placeholders})
            """
            rows = self.execute_query(query, tuple(flat_params))
            for r in rows:
                existing.add((src, r[0], r[1]))

        # 2) 过滤新行
        inserts: List[tuple] = []
        for idx, row in df.iterrows():
            src = _to_py(row.get('source'))
            title = _to_py(row.get('title'))
            pt = _to_py(row.get('publish_time'))
            if (src, title, pt) in existing:
                continue
            tags = _to_py(row.get('tags'))
            related = _to_py(row.get('related_ts_codes'))
            # pandas 的 tuple/array → list
            if tags is not None and not isinstance(tags, list):
                tags = list(tags)
            if related is not None and not isinstance(related, list):
                related = list(related)
            inserts.append((
                pt,
                src,
                title,
                _to_py(row.get('summary')),
                _to_py(row.get('url')),
                tags,
                related,
            ))

        if not inserts:
            logger.debug(f"[news_flash] 全部 {len(df)} 条已存在，跳过 INSERT")
            return 0

        query = f"""
            INSERT INTO {self.TABLE_NAME}
                (publish_time, source, title, summary, url, tags, related_ts_codes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        count = self.execute_batch(query, inserts)
        logger.info(f"[news_flash] 新增 {count} 条（输入 {len(df)}，已存在 {len(df) - len(inserts)}）")
        return count

    # -------------------------------------------------
    # 查询
    # -------------------------------------------------

    def query_by_stock(self, ts_code: str, days: int = 7, limit: int = 50) -> List[Dict]:
        """查询关联到指定股票的最近 N 天快讯（GIN 数组索引）。"""
        self._enforce_limit(limit)
        query = f"""
            SELECT id, publish_time, source, title, summary, url, tags, related_ts_codes, created_at
            FROM {self.TABLE_NAME}
            WHERE %s = ANY(related_ts_codes)
              AND publish_time >= NOW() - (%s::INT * INTERVAL '1 day')
            ORDER BY publish_time DESC
            LIMIT %s
        """
        rows = self.execute_query(query, (ts_code, int(days), int(limit)))
        return [self._row_to_dict(r) for r in rows]

    def query_by_filters(
        self,
        source: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        ts_code: Optional[str] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
    ) -> List[Dict]:
        """前端列表页分页查询。"""
        conditions, params = self._build_conditions(source, start_time, end_time, ts_code, keyword, tag)
        where = " AND ".join(conditions) if conditions else "TRUE"

        order = 'DESC' if sort_order.lower() != 'asc' else 'ASC'
        sort_col = sort_by if sort_by in self.SORTABLE_COLUMNS else 'publish_time'
        order_clause = f"ORDER BY {sort_col} {order}, id DESC"

        offset = max(0, (int(page) - 1) * int(page_size))
        query = f"""
            SELECT id, publish_time, source, title, summary, url, tags, related_ts_codes, created_at
            FROM {self.TABLE_NAME}
            WHERE {where}
            {order_clause}
            LIMIT %s OFFSET %s
        """
        rows = self.execute_query(query, tuple(params + [int(page_size), offset]))
        return [self._row_to_dict(r) for r in rows]

    def count_by_filters(
        self,
        source: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        ts_code: Optional[str] = None,
        keyword: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> int:
        conditions, params = self._build_conditions(source, start_time, end_time, ts_code, keyword, tag)
        where = " AND ".join(conditions) if conditions else "TRUE"
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where}"
        rows = self.execute_query(query, tuple(params))
        return int(rows[0][0]) if rows else 0

    def get_distinct_sources(self) -> List[Dict]:
        """返回已入库的 source 列表及计数（前端下拉框）。"""
        query = f"""
            SELECT source, COUNT(*) AS n, MAX(publish_time) AS last_at
            FROM {self.TABLE_NAME}
            GROUP BY source
            ORDER BY n DESC
        """
        rows = self.execute_query(query)
        return [
            {
                'source': r[0],
                'count': int(r[1]),
                'last_publish_time': r[2].isoformat() if r[2] else None,
            }
            for r in rows
        ]

    def get_latest_publish_time(self, source: Optional[str] = None) -> Optional[str]:
        """返回最新 publish_time 的 ISO 字符串（sync_history 续继用）。"""
        if source:
            query = f"SELECT MAX(publish_time) FROM {self.TABLE_NAME} WHERE source = %s"
            rows = self.execute_query(query, (source,))
        else:
            query = f"SELECT MAX(publish_time) FROM {self.TABLE_NAME}"
            rows = self.execute_query(query)
        if not rows or not rows[0][0]:
            return None
        return rows[0][0].strftime('%Y%m%d')

    def exists_by_date(self, publish_date: str) -> bool:
        """判断某天是否已入库（sync_configs 探针）。"""
        date_fmt = self._ensure_dash_date(publish_date)
        query = f"""
            SELECT 1 FROM {self.TABLE_NAME}
            WHERE publish_time >= %s AND publish_time < %s::DATE + INTERVAL '1 day'
            LIMIT 1
        """
        rows = self.execute_query(query, (date_fmt, date_fmt))
        return bool(rows)

    # -------------------------------------------------
    # 内部工具
    # -------------------------------------------------

    @staticmethod
    def _ensure_dash_date(date_str: str) -> str:
        s = str(date_str).strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return s

    @staticmethod
    def _build_conditions(
        source: Optional[str],
        start_time: Optional[str],
        end_time: Optional[str],
        ts_code: Optional[str],
        keyword: Optional[str],
        tag: Optional[str],
    ):
        conditions: List[str] = []
        params: List[Any] = []
        if source:
            conditions.append("source = %s")
            params.append(source)
        if start_time:
            conditions.append("publish_time >= %s")
            params.append(NewsFlashRepository._ensure_dash_date(start_time))
        if end_time:
            conditions.append("publish_time <= %s::DATE + INTERVAL '1 day'")
            params.append(NewsFlashRepository._ensure_dash_date(end_time))
        if ts_code:
            conditions.append("%s = ANY(related_ts_codes)")
            params.append(ts_code)
        if keyword:
            conditions.append("(title ILIKE %s OR summary ILIKE %s)")
            params.append(f"%{keyword}%")
            params.append(f"%{keyword}%")
        if tag:
            conditions.append("%s = ANY(tags)")
            params.append(tag)
        return conditions, params

    @staticmethod
    def _row_to_dict(row: tuple) -> Dict[str, Any]:
        return {
            'id': int(row[0]) if row[0] is not None else None,
            'publish_time': row[1].isoformat() if row[1] else None,
            'source': row[2],
            'title': row[3],
            'summary': row[4],
            'url': row[5],
            'tags': list(row[6]) if row[6] else [],
            'related_ts_codes': list(row[7]) if row[7] else [],
            'created_at': row[8].isoformat() if row[8] else None,
        }
