"""
公司公告数据仓储（stock_anns）

数据源：AkShare 东方财富聚合（通过 AkShareProvider.get_market_anns / get_stock_anns）。
表结构见 db_init/migrations/118_create_stock_anns.sql。
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
    # numpy scalar
    if hasattr(value, 'item'):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass
    return value


class StockAnnsRepository(BaseRepository):
    """公司公告仓储"""

    TABLE_NAME = "stock_anns"

    SORTABLE_COLUMNS = {'ann_date', 'ts_code', 'anno_type', 'created_at'}

    # -------------------------------------------------
    # 写入
    # -------------------------------------------------

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """批量写入公告（ON CONFLICT 保留已有 content 字段）。

        Args:
            df: 包含至少 ts_code / ann_date / title / anno_type / stock_name / url / source 列
                的 DataFrame（由 AkShareProvider 已标准化）

        Returns:
            影响行数（psycopg2 execute_batch 的累计 rowcount）

        冲突处理：
          主键 (ts_code, ann_date, title) 冲突时，**只更新元数据**（anno_type / url / stock_name /
          source / updated_at），保留已抓取的 content 和 content_fetched_at，避免重复抓取。
        """
        if df is None or df.empty:
            logger.debug("[stock_anns] bulk_upsert: empty DataFrame, skip")
            return 0

        required = ['ts_code', 'ann_date', 'title']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"[stock_anns] bulk_upsert 缺少必填列: {missing}")

        rows: List[tuple] = []
        for _, row in df.iterrows():
            rows.append((
                _to_py(row.get('ts_code')),
                _to_py(row.get('ann_date')),
                _to_py(row.get('title')),
                _to_py(row.get('anno_type')),
                _to_py(row.get('stock_name')),
                _to_py(row.get('url')),
                _to_py(row.get('source')) or 'eastmoney',
            ))

        query = f"""
            INSERT INTO {self.TABLE_NAME}
                (ts_code, ann_date, title, anno_type, stock_name, url, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ts_code, ann_date, title) DO UPDATE SET
                anno_type  = COALESCE(EXCLUDED.anno_type,  {self.TABLE_NAME}.anno_type),
                stock_name = COALESCE(EXCLUDED.stock_name, {self.TABLE_NAME}.stock_name),
                url        = COALESCE(EXCLUDED.url,        {self.TABLE_NAME}.url),
                source     = EXCLUDED.source,
                updated_at = CURRENT_TIMESTAMP
        """

        count = self.execute_batch(query, rows)
        logger.info(f"[stock_anns] upsert {count} 条")
        return count

    def update_content(self, ts_code: str, ann_date: str, title: str, content: str) -> int:
        """回填单条公告的正文（Phase 1.5 anns_content_fetcher 使用）。

        Args:
            ts_code: 股票代码
            ann_date: 公告日期 YYYY-MM-DD 或 YYYYMMDD
            title: 公告标题
            content: 正文纯文本

        Returns:
            影响行数（0 或 1）
        """
        date_fmt = self._ensure_dash_date(ann_date)
        query = f"""
            UPDATE {self.TABLE_NAME}
            SET content = %s,
                content_fetched_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE ts_code = %s AND ann_date = %s AND title = %s
        """
        return self.execute_update(query, (content, ts_code, date_fmt, title))

    # -------------------------------------------------
    # 查询（Service / API 使用）
    # -------------------------------------------------

    def query_by_stock(
        self,
        ts_code: str,
        days: int = 30,
        limit: int = 50,
    ) -> List[Dict]:
        """查询某只股票最近 N 天的公告，按 ann_date 降序。"""
        self._enforce_limit(limit)
        query = f"""
            SELECT ts_code, ann_date, title, anno_type, stock_name, url, source,
                   (content IS NOT NULL) AS has_content, content_fetched_at,
                   event_tags, sentiment_score, sentiment_impact, scoring_reason, score_model, scored_at
            FROM {self.TABLE_NAME}
            WHERE ts_code = %s
              AND ann_date >= CURRENT_DATE - (%s::INT * INTERVAL '1 day')
            ORDER BY ann_date DESC, title
            LIMIT %s
        """
        rows = self.execute_query(query, (ts_code, int(days), int(limit)))
        return [self._row_to_dict(r) for r in rows]

    def query_by_date(self, ann_date: str, limit: int = 1000) -> List[Dict]:
        """查询某一天全市场公告。"""
        self._enforce_limit(limit)
        date_fmt = self._ensure_dash_date(ann_date)
        query = f"""
            SELECT ts_code, ann_date, title, anno_type, stock_name, url, source,
                   (content IS NOT NULL) AS has_content, content_fetched_at,
                   event_tags, sentiment_score, sentiment_impact, scoring_reason, score_model, scored_at
            FROM {self.TABLE_NAME}
            WHERE ann_date = %s
            ORDER BY ts_code, title
            LIMIT %s
        """
        rows = self.execute_query(query, (date_fmt, int(limit)))
        return [self._row_to_dict(r) for r in rows]

    def query_by_filters(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        anno_type: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
    ) -> List[Dict]:
        """通用分页查询（admin 前端列表页用）。"""
        conditions, params = self._build_conditions(ts_code, start_date, end_date, anno_type, keyword)
        where = " AND ".join(conditions) if conditions else "TRUE"

        order = 'DESC' if sort_order.lower() != 'asc' else 'ASC'
        sort_col = sort_by if sort_by in self.SORTABLE_COLUMNS else 'ann_date'
        order_clause = f"ORDER BY {sort_col} {order}, ts_code, title"

        offset = max(0, (int(page) - 1) * int(page_size))
        query = f"""
            SELECT ts_code, ann_date, title, anno_type, stock_name, url, source,
                   (content IS NOT NULL) AS has_content, content_fetched_at,
                   event_tags, sentiment_score, sentiment_impact, scoring_reason, score_model, scored_at,
                   created_at
            FROM {self.TABLE_NAME}
            WHERE {where}
            {order_clause}
            LIMIT %s OFFSET %s
        """
        rows = self.execute_query(query, tuple(params + [int(page_size), offset]))
        return [self._row_to_dict(r, include_created=True) for r in rows]

    def count_by_filters(
        self,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        anno_type: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> int:
        conditions, params = self._build_conditions(ts_code, start_date, end_date, anno_type, keyword)
        where = " AND ".join(conditions) if conditions else "TRUE"
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where}"
        rows = self.execute_query(query, tuple(params))
        return int(rows[0][0]) if rows else 0

    def get_latest_ann_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """返回表中最新的 ann_date（YYYYMMDD 字符串，与 sync_history 约定一致）。"""
        if ts_code:
            query = f"SELECT MAX(ann_date) FROM {self.TABLE_NAME} WHERE ts_code = %s"
            rows = self.execute_query(query, (ts_code,))
        else:
            query = f"SELECT MAX(ann_date) FROM {self.TABLE_NAME}"
            rows = self.execute_query(query)
        if not rows or not rows[0][0]:
            return None
        d = rows[0][0]
        return d.strftime('%Y%m%d') if hasattr(d, 'strftime') else str(d).replace('-', '')

    def exists_by_date(self, ann_date: str) -> bool:
        """判断某天是否已入库（sync_configs 的公共探针）。"""
        date_fmt = self._ensure_dash_date(ann_date)
        query = f"SELECT 1 FROM {self.TABLE_NAME} WHERE ann_date = %s LIMIT 1"
        rows = self.execute_query(query, (date_fmt,))
        return bool(rows)

    def get_distinct_anno_types(self, days: int = 90, limit: int = 200) -> List[Dict]:
        """返回近 N 天出现过的公告类型及计数，供前端筛选下拉框。"""
        self._enforce_limit(limit)
        query = f"""
            SELECT anno_type, COUNT(*) AS n
            FROM {self.TABLE_NAME}
            WHERE ann_date >= CURRENT_DATE - (%s::INT * INTERVAL '1 day')
              AND anno_type IS NOT NULL AND anno_type <> ''
            GROUP BY anno_type
            ORDER BY n DESC, anno_type
            LIMIT %s
        """
        rows = self.execute_query(query, (int(days), int(limit)))
        return [{'anno_type': r[0], 'count': int(r[1])} for r in rows]

    def get_unscored_batch(self, limit: int = 30) -> List[Dict]:
        """取未打分的公告批次（Phase 5 舆情打分）。

        条件：`scored_at IS NULL`（走 idx_stock_anns_unscored 部分索引）；
        只取 `ts_code` 非空且 `title` 非空的记录；按 ann_date 降序"先打新"。
        返回字段供 LLM prompt 使用：id/title/anno_type/stock_name。
        `id` 是合成主键 `ts_code|ann_date|title`（回写时解包）。
        """
        self._enforce_limit(limit)
        query = f"""
            SELECT ts_code, ann_date, title, anno_type, stock_name
            FROM {self.TABLE_NAME}
            WHERE scored_at IS NULL
              AND ts_code IS NOT NULL AND ts_code <> ''
              AND title IS NOT NULL AND title <> ''
            ORDER BY ann_date DESC, ts_code, title
            LIMIT %s
        """
        rows = self.execute_query(query, (int(limit),))
        return [
            {
                'id': f"{r[0]}|{r[1].strftime('%Y-%m-%d') if hasattr(r[1], 'strftime') else r[1]}|{r[2]}",
                'ts_code': r[0],
                'ann_date': r[1].strftime('%Y-%m-%d') if hasattr(r[1], 'strftime') else str(r[1]),
                'title': r[2],
                'anno_type': r[3],
                'stock_name': r[4],
            }
            for r in rows
        ]

    def bulk_update_scores(self, scores: List[Dict[str, Any]]) -> int:
        """批量回写舆情打分结果。

        每个 dict 至少含：id（ts_code|ann_date|title）、event_tags、sentiment_score、
        sentiment_impact、scoring_reason、score_model。
        `scored_at` 由数据库 CURRENT_TIMESTAMP 写入。
        """
        if not scores:
            return 0
        updates: List[tuple] = []
        for s in scores:
            parts = str(s.get('id') or '').split('|', 2)
            if len(parts) != 3:
                continue
            ts_code, ann_date, title = parts
            event_tags = s.get('event_tags') or None
            if event_tags is not None and not isinstance(event_tags, list):
                event_tags = list(event_tags)
            updates.append((
                event_tags,
                _to_py(s.get('sentiment_score')),
                _to_py(s.get('sentiment_impact')),
                _to_py(s.get('scoring_reason')),
                _to_py(s.get('score_model')),
                ts_code,
                self._ensure_dash_date(ann_date),
                title,
            ))
        if not updates:
            return 0
        query = f"""
            UPDATE {self.TABLE_NAME}
            SET event_tags       = %s,
                sentiment_score  = %s,
                sentiment_impact = %s,
                scoring_reason   = %s,
                score_model      = %s,
                scored_at        = CURRENT_TIMESTAMP,
                updated_at       = CURRENT_TIMESTAMP
            WHERE ts_code = %s AND ann_date = %s AND title = %s
        """
        return self.execute_batch(query, updates)

    def get_missing_content_urls(self, limit: int = 5) -> List[Dict]:
        """返回尚未抓取正文的 URL（content_fetched_at IS NULL 且 url IS NOT NULL）。

        Phase 1.5 anns_content_fetcher 使用；默认按 ann_date 降序，先抓新的。
        """
        self._enforce_limit(limit)
        query = f"""
            SELECT ts_code, ann_date, title, url
            FROM {self.TABLE_NAME}
            WHERE content_fetched_at IS NULL AND url IS NOT NULL AND url <> ''
            ORDER BY ann_date DESC, ts_code, title
            LIMIT %s
        """
        rows = self.execute_query(query, (int(limit),))
        return [
            {
                'ts_code': r[0],
                'ann_date': r[1].strftime('%Y-%m-%d') if hasattr(r[1], 'strftime') else str(r[1]),
                'title': r[2],
                'url': r[3],
            }
            for r in rows
        ]

    def get_content(self, ts_code: str, ann_date: str, title: str) -> Optional[Dict]:
        """读取已抓取的公告正文（Phase 1.5 / CIO Agent 使用）。"""
        date_fmt = self._ensure_dash_date(ann_date)
        query = f"""
            SELECT ts_code, ann_date, title, content, content_fetched_at, url, anno_type
            FROM {self.TABLE_NAME}
            WHERE ts_code = %s AND ann_date = %s AND title = %s
        """
        rows = self.execute_query(query, (ts_code, date_fmt, title))
        if not rows:
            return None
        r = rows[0]
        return {
            'ts_code': r[0],
            'ann_date': r[1].strftime('%Y-%m-%d') if hasattr(r[1], 'strftime') else str(r[1]),
            'title': r[2],
            'content': r[3],
            'content_fetched_at': r[4].isoformat() if r[4] else None,
            'url': r[5],
            'anno_type': r[6],
        }

    # -------------------------------------------------
    # 内部工具
    # -------------------------------------------------

    @staticmethod
    def _ensure_dash_date(date_str: str) -> str:
        """YYYYMMDD → YYYY-MM-DD（PostgreSQL DATE 列比较需要）；已带横线时原样返回。"""
        s = str(date_str).strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return s

    @staticmethod
    def _build_conditions(
        ts_code: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        anno_type: Optional[str],
        keyword: Optional[str],
    ):
        conditions: List[str] = []
        params: List[Any] = []
        if ts_code:
            conditions.append("ts_code = %s")
            params.append(ts_code)
        if start_date:
            conditions.append("ann_date >= %s")
            params.append(StockAnnsRepository._ensure_dash_date(start_date))
        if end_date:
            conditions.append("ann_date <= %s")
            params.append(StockAnnsRepository._ensure_dash_date(end_date))
        if anno_type:
            conditions.append("anno_type = %s")
            params.append(anno_type)
        if keyword:
            conditions.append("title ILIKE %s")
            params.append(f"%{keyword}%")
        return conditions, params

    @staticmethod
    def _row_to_dict(row: tuple, include_created: bool = False) -> Dict[str, Any]:
        d = {
            'ts_code': row[0],
            'ann_date': row[1].strftime('%Y-%m-%d') if hasattr(row[1], 'strftime') else str(row[1]),
            'title': row[2],
            'anno_type': row[3],
            'stock_name': row[4],
            'url': row[5],
            'source': row[6],
            'has_content': bool(row[7]),
            'content_fetched_at': row[8].isoformat() if row[8] else None,
        }
        # 舆情打分列（6 列：event_tags / sentiment_score / sentiment_impact /
        # scoring_reason / score_model / scored_at），查询 SQL 均已固定带上
        if len(row) > 14:
            d['event_tags'] = list(row[9]) if row[9] else []
            score = row[10]
            d['sentiment_score'] = float(score) if score is not None else None
            d['sentiment_impact'] = row[11]
            d['scoring_reason'] = row[12]
            d['score_model'] = row[13]
            d['scored_at'] = row[14].isoformat() if row[14] else None
        # include_created 的版本在最后一列带 created_at
        if include_created and len(row) > 15:
            d['created_at'] = row[15].isoformat() if row[15] else None
        return d
