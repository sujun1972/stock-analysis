"""
新闻联播数据仓储（cctv_news）

数据源：AkShare `ak.news_cctv`。主键 (news_date, seq_no)。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


def _to_py(value: Any) -> Any:
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


class CctvNewsRepository(BaseRepository):
    """新闻联播仓储"""

    TABLE_NAME = "cctv_news"

    SORTABLE_COLUMNS = {'news_date', 'seq_no', 'created_at'}

    # -------------------------------------------------
    # 写入
    # -------------------------------------------------

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """批量写入新闻联播（ON CONFLICT (news_date, seq_no) 更新标题/内容）。"""
        if df is None or df.empty:
            return 0

        required = ['news_date', 'seq_no', 'title']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"[cctv_news] bulk_upsert 缺少必填列: {missing}")

        rows: List[tuple] = []
        for _, row in df.iterrows():
            rows.append((
                _to_py(row.get('news_date')),
                _to_py(row.get('seq_no')),
                _to_py(row.get('title')),
                _to_py(row.get('content')),
            ))

        query = f"""
            INSERT INTO {self.TABLE_NAME}
                (news_date, seq_no, title, content)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (news_date, seq_no) DO UPDATE SET
                title      = EXCLUDED.title,
                content    = COALESCE(EXCLUDED.content, {self.TABLE_NAME}.content),
                updated_at = CURRENT_TIMESTAMP
        """
        count = self.execute_batch(query, rows)
        logger.info(f"[cctv_news] upsert {count} 条")
        return count

    # -------------------------------------------------
    # 查询
    # -------------------------------------------------

    def query_by_date(self, news_date: str, limit: int = 50) -> List[Dict]:
        """查询某日的新闻联播（按 seq_no 升序）。"""
        self._enforce_limit(limit)
        date_fmt = self._ensure_dash_date(news_date)
        query = f"""
            SELECT news_date, seq_no, title, content, created_at
            FROM {self.TABLE_NAME}
            WHERE news_date = %s
            ORDER BY seq_no
            LIMIT %s
        """
        rows = self.execute_query(query, (date_fmt, int(limit)))
        return [self._row_to_dict(r) for r in rows]

    def query_by_filters(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
    ) -> List[Dict]:
        conditions, params = self._build_conditions(start_date, end_date, keyword)
        where = " AND ".join(conditions) if conditions else "TRUE"

        order = 'DESC' if sort_order.lower() != 'asc' else 'ASC'
        sort_col = sort_by if sort_by in self.SORTABLE_COLUMNS else 'news_date'
        # 同日内按 seq_no 升序，不跟随用户 order
        order_clause = f"ORDER BY {sort_col} {order}, seq_no ASC"

        offset = max(0, (int(page) - 1) * int(page_size))
        query = f"""
            SELECT news_date, seq_no, title, content, created_at
            FROM {self.TABLE_NAME}
            WHERE {where}
            {order_clause}
            LIMIT %s OFFSET %s
        """
        rows = self.execute_query(query, tuple(params + [int(page_size), offset]))
        return [self._row_to_dict(r) for r in rows]

    def count_by_filters(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> int:
        conditions, params = self._build_conditions(start_date, end_date, keyword)
        where = " AND ".join(conditions) if conditions else "TRUE"
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where}"
        rows = self.execute_query(query, tuple(params))
        return int(rows[0][0]) if rows else 0

    def get_latest_news_date(self) -> Optional[str]:
        """返回最新 news_date 的 YYYYMMDD 字符串。"""
        query = f"SELECT MAX(news_date) FROM {self.TABLE_NAME}"
        rows = self.execute_query(query)
        if not rows or not rows[0][0]:
            return None
        d = rows[0][0]
        return d.strftime('%Y%m%d') if hasattr(d, 'strftime') else str(d).replace('-', '')

    def exists_by_date(self, news_date: str) -> bool:
        date_fmt = self._ensure_dash_date(news_date)
        query = f"SELECT 1 FROM {self.TABLE_NAME} WHERE news_date = %s LIMIT 1"
        rows = self.execute_query(query, (date_fmt,))
        return bool(rows)

    def get_distinct_dates(self, limit: int = 60) -> List[str]:
        """返回已入库的日期列表（最近 N 天，前端日期筛选用）。"""
        self._enforce_limit(limit)
        query = f"""
            SELECT news_date, COUNT(*) AS n
            FROM {self.TABLE_NAME}
            GROUP BY news_date
            ORDER BY news_date DESC
            LIMIT %s
        """
        rows = self.execute_query(query, (int(limit),))
        return [
            {
                'news_date': r[0].strftime('%Y-%m-%d') if hasattr(r[0], 'strftime') else str(r[0]),
                'count': int(r[1]),
            }
            for r in rows
        ]

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
        start_date: Optional[str],
        end_date: Optional[str],
        keyword: Optional[str],
    ):
        conditions: List[str] = []
        params: List[Any] = []
        if start_date:
            conditions.append("news_date >= %s")
            params.append(CctvNewsRepository._ensure_dash_date(start_date))
        if end_date:
            conditions.append("news_date <= %s")
            params.append(CctvNewsRepository._ensure_dash_date(end_date))
        if keyword:
            conditions.append("(title ILIKE %s OR content ILIKE %s)")
            params.append(f"%{keyword}%")
            params.append(f"%{keyword}%")
        return conditions, params

    @staticmethod
    def _row_to_dict(row: tuple) -> Dict[str, Any]:
        return {
            'news_date': row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0]),
            'seq_no': int(row[1]) if row[1] is not None else None,
            'title': row[2],
            'content': row[3],
            'created_at': row[4].isoformat() if row[4] else None,
        }
