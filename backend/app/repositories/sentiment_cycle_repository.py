"""情绪周期 Repository"""
from typing import Dict, List, Optional
from loguru import logger
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError

class SentimentCycleRepository(BaseRepository):
    TABLE_NAME = "market_sentiment_cycle"
    
    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ SentimentCycleRepository initialized")
    
    def get_by_date(self, trade_date: str) -> Optional[Dict]:
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE trade_date = %s"
        try:
            result = self.execute_query(query, (trade_date,))
            return self._row_to_dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"查询情绪周期数据失败: {e}")
            raise QueryError("查询情绪周期数据失败", error_code="SENTIMENT_CYCLE_QUERY_FAILED", reason=str(e))
    
    def get_latest(self, limit: int = 30) -> List[Dict]:
        query = f"SELECT * FROM {self.TABLE_NAME} ORDER BY trade_date DESC LIMIT %s"
        try:
            result = self.execute_query(query, (limit,))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询最新情绪周期数据失败: {e}")
            raise QueryError("查询最新情绪周期数据失败", error_code="LATEST_SENTIMENT_CYCLE_QUERY_FAILED", reason=str(e))
    
    def _row_to_dict(self, row: tuple) -> Dict:
        return {"id": row[0], "trade_date": row[1], "cycle_phase": row[2], "heat_index": float(row[3]) if row[3] else None,
                "sentiment_score": float(row[4]) if row[4] else None, "created_at": row[5], "updated_at": row[6]}
