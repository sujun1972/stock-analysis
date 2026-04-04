"""
新股列表 Repository（new_stocks 表）
对应 Tushare new_share 接口数据
"""

from typing import Optional, List, Dict
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class NewStocksRepository(BaseRepository):
    TABLE_NAME = "new_stocks"

    def __init__(self, db=None):
        super().__init__(db)

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """
        按上网发行日期范围查询新股列表

        Args:
            start_date: 开始日期 YYYYMMDD
            end_date:   结束日期 YYYYMMDD
            limit:      返回条数
            offset:     偏移量

        Returns:
            新股列表
        """
        conditions = []
        params: list = []

        if start_date:
            conditions.append("ipo_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("ipo_date <= %s")
            params.append(end_date)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        query = f"""
            SELECT ts_code, sub_code, name, ipo_date, issue_date,
                   amount, market_amount, price, pe, limit_amount, funds, ballot
            FROM {self.TABLE_NAME}
            {where}
            ORDER BY ipo_date DESC NULLS LAST, ts_code
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        rows = self.execute_query(query, tuple(params))
        return [self._row_to_dict(r) for r in rows]

    def count_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> int:
        conditions = []
        params: list = []
        if start_date:
            conditions.append("ipo_date >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("ipo_date <= %s")
            params.append(end_date)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} {where}"
        rows = self.execute_query(query, tuple(params))
        return rows[0][0] if rows else 0

    def get_statistics(self) -> Dict:
        """统计卡片数据：总数、最近7/30/90天"""
        query = """
            SELECT
                COUNT(*)                                                      AS total_count,
                COUNT(*) FILTER (WHERE ipo_date >= TO_CHAR(CURRENT_DATE - 7,  'YYYYMMDD')) AS recent_7_days,
                COUNT(*) FILTER (WHERE ipo_date >= TO_CHAR(CURRENT_DATE - 30, 'YYYYMMDD')) AS recent_30_days,
                COUNT(*) FILTER (WHERE ipo_date >= TO_CHAR(CURRENT_DATE - 90, 'YYYYMMDD')) AS recent_90_days
            FROM new_stocks
        """
        rows = self.execute_query(query, ())
        if not rows:
            return {"total_count": 0, "recent_7_days": 0, "recent_30_days": 0, "recent_90_days": 0}
        r = rows[0]
        return {
            "total_count":   int(r[0] or 0),
            "recent_7_days": int(r[1] or 0),
            "recent_30_days":int(r[2] or 0),
            "recent_90_days":int(r[3] or 0),
        }

    def get_latest_ipo_date(self) -> Optional[str]:
        """返回表中最新的 ipo_date（YYYYMMDD），无数据返回 None"""
        query = f"SELECT MAX(ipo_date) FROM {self.TABLE_NAME}"
        rows = self.execute_query(query, ())
        return rows[0][0] if rows and rows[0][0] else None

    def exists_by_date(self, date_str: str) -> bool:
        query = f"SELECT 1 FROM {self.TABLE_NAME} WHERE ipo_date = %s LIMIT 1"
        rows = self.execute_query(query, (date_str,))
        return bool(rows)

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新（ON CONFLICT DO UPDATE）

        Returns:
            upsert 条数
        """
        if df is None or df.empty:
            return 0

        def _val(v):
            if pd.isna(v):
                return None
            if hasattr(v, 'item'):
                try:
                    return float(v) if 'float' in str(type(v)) else int(v)
                except Exception:
                    return None
            return v

        records = []
        for _, row in df.iterrows():
            records.append((
                str(row.get('ts_code', '') or ''),
                str(row.get('sub_code', '') or '') or None,
                str(row.get('name', '') or ''),
                str(row.get('ipo_date', '') or '') or None,
                str(row.get('issue_date', '') or '') or None,
                _val(row.get('amount')),
                _val(row.get('market_amount')),
                _val(row.get('price')),
                _val(row.get('pe')),
                _val(row.get('limit_amount')),
                _val(row.get('funds')),
                _val(row.get('ballot')),
            ))

        query = """
            INSERT INTO new_stocks
                (ts_code, sub_code, name, ipo_date, issue_date,
                 amount, market_amount, price, pe, limit_amount, funds, ballot)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ts_code) DO UPDATE SET
                sub_code      = EXCLUDED.sub_code,
                name          = EXCLUDED.name,
                ipo_date      = EXCLUDED.ipo_date,
                issue_date    = EXCLUDED.issue_date,
                amount        = EXCLUDED.amount,
                market_amount = EXCLUDED.market_amount,
                price         = EXCLUDED.price,
                pe            = EXCLUDED.pe,
                limit_amount  = EXCLUDED.limit_amount,
                funds         = EXCLUDED.funds,
                ballot        = EXCLUDED.ballot,
                updated_at    = NOW()
        """
        count = self.execute_batch(query, records)
        logger.info(f"new_stocks bulk_upsert: {count} 条")
        return count

    # ── 内部辅助 ──────────────────────────────────────────────

    @staticmethod
    def _row_to_dict(row: tuple) -> Dict:
        keys = [
            'ts_code', 'sub_code', 'name', 'ipo_date', 'issue_date',
            'amount', 'market_amount', 'price', 'pe', 'limit_amount', 'funds', 'ballot',
        ]
        return {k: (float(v) if isinstance(v, (int, float)) and k not in ('ts_code', 'sub_code', 'name', 'ipo_date', 'issue_date') else v)
                for k, v in zip(keys, row)}
