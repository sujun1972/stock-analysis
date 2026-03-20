"""龙虎榜数据 Repository"""
from typing import Dict, List, Optional
from loguru import logger
from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError, DatabaseError

class DragonTigerListRepository(BaseRepository):
    TABLE_NAME = "dragon_tiger_list"
    
    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ DragonTigerListRepository initialized")
    
    def get_by_date(self, trade_date: str, limit: int = 100) -> List[Dict]:
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE trade_date = %s ORDER BY net_amount DESC LIMIT %s"
        try:
            result = self.execute_query(query, (trade_date, limit))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询龙虎榜数据失败: {e}")
            raise QueryError("查询龙虎榜数据失败", error_code="DRAGON_TIGER_QUERY_FAILED", reason=str(e))
    
    def get_by_stock(self, stock_code: str, start_date: str, end_date: str) -> List[Dict]:
        query = f"SELECT * FROM {self.TABLE_NAME} WHERE stock_code = %s AND trade_date >= %s AND trade_date <= %s ORDER BY trade_date DESC"
        try:
            result = self.execute_query(query, (stock_code, start_date, end_date))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询龙虎榜股票数据失败: {e}")
            raise QueryError("查询龙虎榜股票数据失败", error_code="DRAGON_TIGER_STOCK_QUERY_FAILED", reason=str(e))
    
    def _row_to_dict(self, row: tuple) -> Dict:
        return {"id": row[0], "trade_date": row[1], "stock_code": row[2], "stock_name": row[3],
                "reason": row[4], "reason_type": row[5], "close_price": float(row[6]) if row[6] else None,
                "price_change": float(row[7]) if row[7] else None, "turnover_rate": float(row[8]) if row[8] else None,
                "buy_amount": float(row[9]) if row[9] else None, "sell_amount": float(row[10]) if row[10] else None,
                "net_amount": float(row[11]) if row[11] else None, "top_buyers": row[12], "top_sellers": row[13],
                "has_institution": row[14], "institution_count": row[15], "dept_buy_count": row[16],
                "dept_sell_count": row[17], "created_at": row[18], "updated_at": row[19]}
