"""涨停板情绪池 Repository"""
from typing import Dict, List, Optional
from loguru import logger
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError, DatabaseError

class LimitUpPoolRepository(BaseRepository):
    TABLE_NAME = "limit_up_pool"
    
    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ LimitUpPoolRepository initialized")
    
    def get_by_date(self, trade_date: str) -> Optional[Dict]:
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE trade_date = %s"
        try:
            result = self.execute_query(query, (trade_date,))
            return dict(zip([
                "id", "trade_date", "limit_up_count", "limit_down_count",
                "blast_count", "blast_rate", "max_continuous_days", "max_continuous_count",
                "continuous_ladder", "limit_up_stocks", "blast_stocks",
                "total_stocks", "rise_count", "fall_count", "rise_fall_ratio",
                "created_at", "updated_at"
            ], result[0])) if result else None
        except Exception as e:
            logger.error(f"查询涨停板数据失败: {e}")
            raise QueryError("查询涨停板数据失败", error_code="LIMIT_UP_QUERY_FAILED", reason=str(e))
    
    def get_by_date_range(self, start_date: str, end_date: str, limit: int = 100) -> List[Dict]:
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE trade_date >= %s AND trade_date <= %s ORDER BY trade_date DESC LIMIT %s"
        try:
            result = self.execute_query(query, (start_date, end_date, limit))
            return [dict(zip([
                "id", "trade_date", "limit_up_count", "limit_down_count",
                "blast_count", "blast_rate", "max_continuous_days", "max_continuous_count",
                "continuous_ladder", "limit_up_stocks", "blast_stocks",
                "total_stocks", "rise_count", "fall_count", "rise_fall_ratio",
                "created_at", "updated_at"
            ], row)) for row in result]
        except Exception as e:
            logger.error(f"查询涨停板数据范围失败: {e}")
            raise QueryError("查询涨停板数据范围失败", error_code="LIMIT_UP_RANGE_QUERY_FAILED", reason=str(e))
    
    def upsert(self, data: Dict) -> int:
        query = f"""
            INSERT INTO {self.TABLE_NAME} (
                trade_date, limit_up_count, limit_down_count, blast_count, blast_rate,
                max_continuous_days, max_continuous_count, continuous_ladder,
                limit_up_stocks, blast_stocks, total_stocks, rise_count, fall_count, rise_fall_ratio
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trade_date) DO UPDATE SET
                limit_up_count = EXCLUDED.limit_up_count,
                limit_down_count = EXCLUDED.limit_down_count,
                blast_count = EXCLUDED.blast_count,
                blast_rate = EXCLUDED.blast_rate,
                max_continuous_days = EXCLUDED.max_continuous_days,
                max_continuous_count = EXCLUDED.max_continuous_count,
                continuous_ladder = EXCLUDED.continuous_ladder,
                limit_up_stocks = EXCLUDED.limit_up_stocks,
                blast_stocks = EXCLUDED.blast_stocks,
                total_stocks = EXCLUDED.total_stocks,
                rise_count = EXCLUDED.rise_count,
                fall_count = EXCLUDED.fall_count,
                rise_fall_ratio = EXCLUDED.rise_fall_ratio,
                updated_at = NOW()
        """
        try:
            import json
            params = (
                data['trade_date'], data.get('limit_up_count', 0), data.get('limit_down_count', 0),
                data.get('blast_count', 0), data.get('blast_rate'), data.get('max_continuous_days', 0),
                data.get('max_continuous_count', 0), json.dumps(data.get('continuous_ladder')) if data.get('continuous_ladder') else None,
                json.dumps(data.get('limit_up_stocks')) if data.get('limit_up_stocks') else None,
                json.dumps(data.get('blast_stocks')) if data.get('blast_stocks') else None,
                data.get('total_stocks', 0), data.get('rise_count', 0), data.get('fall_count', 0), data.get('rise_fall_ratio')
            )
            return self.execute_update(query, params)
        except Exception as e:
            logger.error(f"插入/更新涨停板数据失败: {e}")
            raise DatabaseError("插入/更新涨停板数据失败", error_code="LIMIT_UP_UPSERT_FAILED", reason=str(e))
