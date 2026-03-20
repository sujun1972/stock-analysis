"""AI情绪分析 Repository"""
from typing import Dict, List, Optional
from loguru import logger
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError

class SentimentAiAnalysisRepository(BaseRepository):
    TABLE_NAME = "market_sentiment_ai_analysis"
    
    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ SentimentAiAnalysisRepository initialized")
    
    def get_by_date(self, trade_date: str) -> Optional[Dict]:
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE trade_date = %s"
        try:
            result = self.execute_query(query, (trade_date,))
            return self._row_to_dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"查询AI分析数据失败: {e}")
            raise QueryError("查询AI分析数据失败", error_code="AI_ANALYSIS_QUERY_FAILED", reason=str(e))
    
    def get_latest(self, limit: int = 10) -> List[Dict]:
        query = f"SELECT * FROM {self.TABLE_NAME} ORDER BY trade_date DESC LIMIT %s"
        try:
            result = self.execute_query(query, (limit,))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询最新AI分析数据失败: {e}")
            raise QueryError("查询最新AI分析数据失败", error_code="LATEST_AI_ANALYSIS_QUERY_FAILED", reason=str(e))
    
    def _row_to_dict(self, row: tuple) -> Dict:
        return {"id": row[0], "trade_date": row[1], "analysis_content": row[2], "key_points": row[3],
                "sentiment_label": row[4], "confidence_score": float(row[5]) if row[5] else None,
                "created_at": row[6], "updated_at": row[7]}
