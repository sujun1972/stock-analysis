"""
宏观经济指标数据仓储（macro_indicators）

数据源：AkShare 免费宏观接口（见 core `_mixins/macro_indicators.py`）。
主键 (indicator_code, period_date)；JSONB `raw` 字段兜底保留原始中文字段。
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


class MacroIndicatorsRepository(BaseRepository):
    """宏观经济指标仓储。"""

    TABLE_NAME = "macro_indicators"

    SORTABLE_COLUMNS = {'indicator_code', 'period_date', 'publish_date', 'created_at'}

    # -------------------------------------------------
    # 写入
    # -------------------------------------------------

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """批量 UPSERT 宏观指标（ON CONFLICT(indicator_code, period_date) 更新数值与 raw）。

        Args:
            df: 列至少 indicator_code / period_date / value（其余可空）

        Returns:
            实际 UPSERT 行数
        """
        if df is None or df.empty:
            return 0

        from psycopg2.extras import Json

        required = ['indicator_code', 'period_date']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"[macro_indicators] bulk_upsert 缺少必填列: {missing}")

        rows: List[tuple] = []
        for _, row in df.iterrows():
            raw_val = _to_py(row.get('raw'))
            # JSONB 列必须用 Json 包装 dict；None 直接存 NULL
            raw_param = Json(raw_val) if isinstance(raw_val, dict) else None

            rows.append((
                _to_py(row.get('indicator_code')),
                _to_py(row.get('period_date')),
                _to_py(row.get('value')),
                _to_py(row.get('yoy')),
                _to_py(row.get('mom')),
                _to_py(row.get('publish_date')),
                _to_py(row.get('source')) or 'akshare',
                raw_param,
            ))

        query = f"""
            INSERT INTO {self.TABLE_NAME}
                (indicator_code, period_date, value, yoy, mom, publish_date, source, raw)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (indicator_code, period_date) DO UPDATE SET
                value        = COALESCE(EXCLUDED.value,        {self.TABLE_NAME}.value),
                yoy          = COALESCE(EXCLUDED.yoy,          {self.TABLE_NAME}.yoy),
                mom          = COALESCE(EXCLUDED.mom,          {self.TABLE_NAME}.mom),
                publish_date = COALESCE(EXCLUDED.publish_date, {self.TABLE_NAME}.publish_date),
                source       = EXCLUDED.source,
                raw          = COALESCE(EXCLUDED.raw,          {self.TABLE_NAME}.raw),
                updated_at   = CURRENT_TIMESTAMP
        """
        count = self.execute_batch(query, rows)
        logger.info(f"[macro_indicators] upsert {count} 条")
        return count

    # -------------------------------------------------
    # 查询
    # -------------------------------------------------

    def query_series(
        self,
        indicator_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 60,
    ) -> List[Dict]:
        """按 indicator_code 查询时间序列（period_date 倒序）。

        参数：
          - start_date / end_date: YYYY-MM-DD 或 YYYYMMDD；区间闭合
          - limit: 返回条数上限（默认 60，覆盖月度近 5 年）
        """
        self._enforce_limit(limit)
        where = ["indicator_code = %s"]
        params: List[Any] = [indicator_code]
        if start_date:
            where.append("period_date >= %s")
            params.append(self._ensure_dash_date(start_date))
        if end_date:
            where.append("period_date <= %s")
            params.append(self._ensure_dash_date(end_date))

        query = f"""
            SELECT indicator_code, period_date, value, yoy, mom, publish_date, source, raw, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE {' AND '.join(where)}
            ORDER BY period_date DESC
            LIMIT %s
        """
        params.append(int(limit))
        rows = self.execute_query(query, tuple(params))
        return [self._row_to_dict(r) for r in rows]

    def query_by_filters(
        self,
        indicator_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
    ) -> List[Dict]:
        """列表页分页查询（跨指标）。"""
        conditions, params = self._build_conditions(indicator_code, start_date, end_date)
        where = " AND ".join(conditions) if conditions else "TRUE"

        order = 'DESC' if sort_order.lower() != 'asc' else 'ASC'
        sort_col = sort_by if sort_by in self.SORTABLE_COLUMNS else 'period_date'
        order_clause = f"ORDER BY {sort_col} {order}, indicator_code ASC"

        offset = max(0, (int(page) - 1) * int(page_size))
        query = f"""
            SELECT indicator_code, period_date, value, yoy, mom, publish_date, source, raw, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE {where}
            {order_clause}
            LIMIT %s OFFSET %s
        """
        rows = self.execute_query(query, tuple(params + [int(page_size), offset]))
        return [self._row_to_dict(r) for r in rows]

    def count_by_filters(
        self,
        indicator_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        conditions, params = self._build_conditions(indicator_code, start_date, end_date)
        where = " AND ".join(conditions) if conditions else "TRUE"
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where}"
        rows = self.execute_query(query, tuple(params))
        return int(rows[0][0]) if rows else 0

    def get_indicator_summary(self) -> List[Dict]:
        """各 indicator_code 的覆盖范围与条数（前端统计用）。"""
        query = f"""
            SELECT
                indicator_code,
                COUNT(*)           AS n,
                MIN(period_date)   AS earliest,
                MAX(period_date)   AS latest,
                MAX(updated_at)    AS last_updated
            FROM {self.TABLE_NAME}
            GROUP BY indicator_code
            ORDER BY indicator_code
        """
        rows = self.execute_query(query)
        return [
            {
                'indicator_code': r[0],
                'count': int(r[1]),
                'earliest': r[2].strftime('%Y-%m-%d') if r[2] else None,
                'latest': r[3].strftime('%Y-%m-%d') if r[3] else None,
                'last_updated': r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]

    def get_latest_snapshot(self, indicator_codes: List[str]) -> Dict[str, Dict]:
        """为一组 indicator_code 拉最新一条（供 CIO / 宏观专家一次性取"当前值"）。"""
        if not indicator_codes:
            return {}
        placeholders = ','.join(['%s'] * len(indicator_codes))
        query = f"""
            SELECT DISTINCT ON (indicator_code)
                indicator_code, period_date, value, yoy, mom, publish_date, raw, updated_at
            FROM {self.TABLE_NAME}
            WHERE indicator_code IN ({placeholders})
              AND value IS NOT NULL
            ORDER BY indicator_code, period_date DESC
        """
        rows = self.execute_query(query, tuple(indicator_codes))
        out: Dict[str, Dict] = {}
        for r in rows:
            out[r[0]] = {
                'indicator_code': r[0],
                'period_date': r[1].strftime('%Y-%m-%d') if r[1] else None,
                'value': float(r[2]) if r[2] is not None else None,
                'yoy': float(r[3]) if r[3] is not None else None,
                'mom': float(r[4]) if r[4] is not None else None,
                'publish_date': r[5].strftime('%Y-%m-%d') if r[5] else None,
                'raw': dict(r[6]) if r[6] else None,
                'updated_at': r[7].isoformat() if r[7] else None,
            }
        return out

    def exists_by_date(self, period_date: str) -> bool:
        """用于 sync_configs 探针（"某日是否已有数据"）。
        宏观无"交易日"概念，这里返回：是否存在 period_date >= 给定日的记录。"""
        date_fmt = self._ensure_dash_date(period_date)
        query = f"""
            SELECT 1 FROM {self.TABLE_NAME}
            WHERE period_date >= %s
            LIMIT 1
        """
        rows = self.execute_query(query, (date_fmt,))
        return bool(rows)

    def get_latest_period_date(self) -> Optional[str]:
        """全表最新 period_date（YYYYMMDD 字符串）。"""
        query = f"SELECT MAX(period_date) FROM {self.TABLE_NAME}"
        rows = self.execute_query(query)
        if not rows or not rows[0][0]:
            return None
        d = rows[0][0]
        return d.strftime('%Y%m%d') if hasattr(d, 'strftime') else str(d).replace('-', '')

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
        indicator_code: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
    ):
        conditions: List[str] = []
        params: List[Any] = []
        if indicator_code:
            conditions.append("indicator_code = %s")
            params.append(indicator_code)
        if start_date:
            conditions.append("period_date >= %s")
            params.append(MacroIndicatorsRepository._ensure_dash_date(start_date))
        if end_date:
            conditions.append("period_date <= %s")
            params.append(MacroIndicatorsRepository._ensure_dash_date(end_date))
        return conditions, params

    @staticmethod
    def _row_to_dict(row: tuple) -> Dict[str, Any]:
        return {
            'indicator_code': row[0],
            'period_date': row[1].strftime('%Y-%m-%d') if row[1] else None,
            'value': float(row[2]) if row[2] is not None else None,
            'yoy': float(row[3]) if row[3] is not None else None,
            'mom': float(row[4]) if row[4] is not None else None,
            'publish_date': row[5].strftime('%Y-%m-%d') if row[5] else None,
            'source': row[6],
            'raw': dict(row[7]) if row[7] else None,
            'created_at': row[8].isoformat() if row[8] else None,
            'updated_at': row[9].isoformat() if row[9] else None,
        }
