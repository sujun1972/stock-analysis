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


def _normalize_ts_codes(codes: Optional[List[str]]) -> Optional[List[str]]:
    """写入兜底：把 6 位纯数字补全为带交易所后缀的 ts_code。

    历史数据或早期实现可能写入纯数字；此处统一通过 StockCodeExtractor 白名单映射
    补全，白名单查不到则原样保留（避免误丢已退市代码等）。去重且保序。
    """
    if not codes:
        return codes
    from app.services.news_anns.stock_code_extractor import _cache as _extractor_cache
    pure_map = _extractor_cache.pure_to_ts()
    seen = set()
    out: List[str] = []
    for c in codes:
        if c is None:
            continue
        s = str(c).strip().upper()
        if not s:
            continue
        if '.' not in s and s.isdigit() and len(s) == 6:
            s = pure_map.get(s, s)
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


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
            related = _normalize_ts_codes(related)
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
            SELECT id, publish_time, source, title, summary, url, tags, related_ts_codes, created_at,
                   sentiment_score, sentiment_impact, sentiment_tags, scoring_reason, score_model, scored_at
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
            SELECT id, publish_time, source, title, summary, url, tags, related_ts_codes, created_at,
                   sentiment_score, sentiment_impact, sentiment_tags, scoring_reason, score_model, scored_at
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

    def get_unscored_batch(self, limit: int = 30) -> List[Dict]:
        """取未打分且 related_ts_codes 非空的快讯批次（Phase 5 舆情打分）。

        使用 `idx_news_flash_unscored` 部分索引，按 publish_time 降序"先打新"。
        返回字段供 LLM prompt：id/title/summary/related_ts_codes。
        """
        self._enforce_limit(limit)
        query = f"""
            SELECT id, publish_time, title, summary, related_ts_codes
            FROM {self.TABLE_NAME}
            WHERE scored_at IS NULL
              AND related_ts_codes IS NOT NULL
              AND array_length(related_ts_codes, 1) > 0
              AND title IS NOT NULL AND title <> ''
            ORDER BY publish_time DESC
            LIMIT %s
        """
        rows = self.execute_query(query, (int(limit),))
        return [
            {
                'id': int(r[0]),
                'publish_time': r[1].isoformat() if r[1] else None,
                'title': r[2],
                'summary': r[3] or '',
                'related_ts_codes': list(r[4]) if r[4] else [],
            }
            for r in rows
        ]

    def bulk_update_scores(self, scores: List[Dict[str, Any]]) -> int:
        """批量回写舆情打分。每个 dict：id / publish_time / sentiment_score /
        sentiment_impact / sentiment_tags / scoring_reason / score_model。

        `publish_time` 必传 —— news_flash 是 TimescaleDB hypertable，主键是
        (id, publish_time)，跨分区 UPDATE 必须同时锁定时间戳，否则 UPDATE 效率退化
        为全 chunk 扫描。
        """
        if not scores:
            return 0
        updates: List[tuple] = []
        for s in scores:
            sid = s.get('id')
            pt = s.get('publish_time')
            if sid is None or pt is None:
                continue
            try:
                flash_id = int(sid)
            except (TypeError, ValueError):
                continue
            sentiment_tags = s.get('sentiment_tags') or None
            if sentiment_tags is not None and not isinstance(sentiment_tags, list):
                sentiment_tags = list(sentiment_tags)
            updates.append((
                _to_py(s.get('sentiment_score')),
                _to_py(s.get('sentiment_impact')),
                sentiment_tags,
                _to_py(s.get('scoring_reason')),
                _to_py(s.get('score_model')),
                flash_id,
                _to_py(pt),
            ))
        if not updates:
            return 0
        query = f"""
            UPDATE {self.TABLE_NAME}
            SET sentiment_score  = %s,
                sentiment_impact = %s,
                sentiment_tags   = %s,
                scoring_reason   = %s,
                score_model      = %s,
                scored_at        = CURRENT_TIMESTAMP
            WHERE id = %s AND publish_time = %s
        """
        return self.execute_batch(query, updates)

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
        d = {
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
        # 舆情打分列（部分旧查询 SQL 不 SELECT 这些列，用 len(row) 判断兼容）
        if len(row) > 9:
            sentiment_score = row[9]
            d['sentiment_score'] = float(sentiment_score) if sentiment_score is not None else None
            d['sentiment_impact'] = row[10]
            d['sentiment_tags'] = list(row[11]) if row[11] else []
            d['scoring_reason'] = row[12]
            d['score_model'] = row[13]
            d['scored_at'] = row[14].isoformat() if row[14] else None
        return d
