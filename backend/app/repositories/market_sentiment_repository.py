"""
大盘情绪数据 Repository

负责 market_sentiment_daily 表的数据访问操作。
"""

from typing import Dict, List, Optional
from datetime import date
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError, DatabaseError


class MarketSentimentRepository(BaseRepository):
    """
    大盘情绪数据访问层
    
    职责:
    - 每日大盘基础数据的查询和管理
    - 上证、深证、创业板指数数据
    - 市场成交汇总统计
    """
    
    TABLE_NAME = "market_sentiment_daily"
    
    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ MarketSentimentRepository initialized")
    
    # ==================== 查询操作 ====================
    
    def get_by_date(self, trade_date: str) -> Optional[Dict]:
        """获取指定日期的大盘数据"""
        query = f"""
            SELECT id, trade_date, sh_index_code, sh_index_close, sh_index_change,
                   sh_index_amplitude, sh_index_volume, sh_index_amount,
                   sz_index_code, sz_index_close, sz_index_change,
                   sz_index_amplitude, sz_index_volume, sz_index_amount,
                   cyb_index_code, cyb_index_close, cyb_index_change,
                   cyb_index_amplitude, cyb_index_volume, cyb_index_amount,
                   total_volume, total_amount, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE trade_date = %s
        """
        try:
            result = self.execute_query(query, (trade_date,))
            return self._row_to_dict(result[0]) if result else None
        except Exception as e:
            logger.error(f"查询大盘数据失败 (date={trade_date}): {e}")
            raise QueryError("查询大盘数据失败", error_code="MARKET_SENTIMENT_QUERY_FAILED", reason=str(e))
    
    def get_by_date_range(self, start_date: str, end_date: str, limit: int = 100) -> List[Dict]:
        """获取日期范围内的大盘数据"""
        query = f"""
            SELECT id, trade_date, sh_index_code, sh_index_close, sh_index_change,
                   sh_index_amplitude, sh_index_volume, sh_index_amount,
                   sz_index_code, sz_index_close, sz_index_change,
                   sz_index_amplitude, sz_index_volume, sz_index_amount,
                   cyb_index_code, cyb_index_close, cyb_index_change,
                   cyb_index_amplitude, cyb_index_volume, cyb_index_amount,
                   total_volume, total_amount, created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
            ORDER BY trade_date DESC
            LIMIT %s
        """
        try:
            result = self.execute_query(query, (start_date, end_date, limit))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询大盘数据范围失败: {e}")
            raise QueryError("查询大盘数据范围失败", error_code="MARKET_SENTIMENT_RANGE_QUERY_FAILED", reason=str(e))
    
    def get_latest(self, limit: int = 30) -> List[Dict]:
        """获取最新的大盘数据"""
        query = f"""
            SELECT id, trade_date, sh_index_code, sh_index_close, sh_index_change,
                   sh_index_amplitude, sh_index_volume, sh_index_amount,
                   sz_index_code, sz_index_close, sz_index_change,
                   sz_index_amplitude, sz_index_volume, sz_index_amount,
                   cyb_index_code, cyb_index_close, cyb_index_change,
                   cyb_index_amplitude, cyb_index_volume, cyb_index_amount,
                   total_volume, total_amount, created_at, updated_at
            FROM {self.TABLE_NAME}
            ORDER BY trade_date DESC
            LIMIT %s
        """
        try:
            result = self.execute_query(query, (limit,))
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询最新大盘数据失败: {e}")
            raise QueryError("查询最新大盘数据失败", error_code="LATEST_MARKET_SENTIMENT_QUERY_FAILED", reason=str(e))
    
    def get_statistics(self, start_date: str, end_date: str) -> Dict:
        """获取大盘统计信息"""
        query = f"""
            SELECT
                COUNT(*) as total_days,
                AVG(sh_index_change) as avg_sh_change,
                AVG(sz_index_change) as avg_sz_change,
                AVG(cyb_index_change) as avg_cyb_change,
                AVG(total_amount) as avg_total_amount,
                MAX(total_amount) as max_total_amount,
                MIN(total_amount) as min_total_amount
            FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        try:
            result = self.execute_query(query, (start_date, end_date))
            if not result:
                return self._empty_statistics()
            row = result[0]
            return {
                "total_days": row[0] or 0,
                "avg_sh_change": float(row[1]) if row[1] else 0.0,
                "avg_sz_change": float(row[2]) if row[2] else 0.0,
                "avg_cyb_change": float(row[3]) if row[3] else 0.0,
                "avg_total_amount": float(row[4]) if row[4] else 0.0,
                "max_total_amount": float(row[5]) if row[5] else 0.0,
                "min_total_amount": float(row[6]) if row[6] else 0.0
            }
        except Exception as e:
            logger.error(f"获取大盘统计失败: {e}")
            raise QueryError("获取大盘统计失败", error_code="MARKET_SENTIMENT_STATS_FAILED", reason=str(e))
    
    # ==================== 写入操作 ====================
    
    def upsert(self, data: Dict) -> int:
        """插入或更新单条大盘数据"""
        query = f"""
            INSERT INTO {self.TABLE_NAME} (
                trade_date, sh_index_code, sh_index_close, sh_index_change,
                sh_index_amplitude, sh_index_volume, sh_index_amount,
                sz_index_code, sz_index_close, sz_index_change,
                sz_index_amplitude, sz_index_volume, sz_index_amount,
                cyb_index_code, cyb_index_close, cyb_index_change,
                cyb_index_amplitude, cyb_index_volume, cyb_index_amount,
                total_volume, total_amount
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (trade_date)
            DO UPDATE SET
                sh_index_close = EXCLUDED.sh_index_close,
                sh_index_change = EXCLUDED.sh_index_change,
                sh_index_amplitude = EXCLUDED.sh_index_amplitude,
                sh_index_volume = EXCLUDED.sh_index_volume,
                sh_index_amount = EXCLUDED.sh_index_amount,
                sz_index_close = EXCLUDED.sz_index_close,
                sz_index_change = EXCLUDED.sz_index_change,
                sz_index_amplitude = EXCLUDED.sz_index_amplitude,
                sz_index_volume = EXCLUDED.sz_index_volume,
                sz_index_amount = EXCLUDED.sz_index_amount,
                cyb_index_close = EXCLUDED.cyb_index_close,
                cyb_index_change = EXCLUDED.cyb_index_change,
                cyb_index_amplitude = EXCLUDED.cyb_index_amplitude,
                cyb_index_volume = EXCLUDED.cyb_index_volume,
                cyb_index_amount = EXCLUDED.cyb_index_amount,
                total_volume = EXCLUDED.total_volume,
                total_amount = EXCLUDED.total_amount,
                updated_at = NOW()
        """
        try:
            params = (
                data['trade_date'], data.get('sh_index_code', '000001'),
                data.get('sh_index_close'), data.get('sh_index_change'),
                data.get('sh_index_amplitude'), data.get('sh_index_volume'), data.get('sh_index_amount'),
                data.get('sz_index_code', '399001'), data.get('sz_index_close'), data.get('sz_index_change'),
                data.get('sz_index_amplitude'), data.get('sz_index_volume'), data.get('sz_index_amount'),
                data.get('cyb_index_code', '399006'), data.get('cyb_index_close'), data.get('cyb_index_change'),
                data.get('cyb_index_amplitude'), data.get('cyb_index_volume'), data.get('cyb_index_amount'),
                data.get('total_volume'), data.get('total_amount')
            )
            rows = self.execute_update(query, params)
            logger.info(f"插入/更新大盘数据: {data['trade_date']}")
            return rows
        except Exception as e:
            logger.error(f"插入/更新大盘数据失败: {e}")
            raise DatabaseError("插入/更新大盘数据失败", error_code="MARKET_SENTIMENT_UPSERT_FAILED", reason=str(e))
    
    def _row_to_dict(self, row: tuple) -> Dict:
        """将数据库行转换为字典"""
        return {
            "id": row[0], "trade_date": row[1],
            "sh_index_code": row[2], "sh_index_close": float(row[3]) if row[3] else None,
            "sh_index_change": float(row[4]) if row[4] else None,
            "sh_index_amplitude": float(row[5]) if row[5] else None,
            "sh_index_volume": row[6], "sh_index_amount": float(row[7]) if row[7] else None,
            "sz_index_code": row[8], "sz_index_close": float(row[9]) if row[9] else None,
            "sz_index_change": float(row[10]) if row[10] else None,
            "sz_index_amplitude": float(row[11]) if row[11] else None,
            "sz_index_volume": row[12], "sz_index_amount": float(row[13]) if row[13] else None,
            "cyb_index_code": row[14], "cyb_index_close": float(row[15]) if row[15] else None,
            "cyb_index_change": float(row[16]) if row[16] else None,
            "cyb_index_amplitude": float(row[17]) if row[17] else None,
            "cyb_index_volume": row[18], "cyb_index_amount": float(row[19]) if row[19] else None,
            "total_volume": row[20], "total_amount": float(row[21]) if row[21] else None,
            "created_at": row[22], "updated_at": row[23]
        }
    
    def _empty_statistics(self) -> Dict:
        """返回空统计"""
        return {"total_days": 0, "avg_sh_change": 0.0, "avg_sz_change": 0.0,
                "avg_cyb_change": 0.0, "avg_total_amount": 0.0,
                "max_total_amount": 0.0, "min_total_amount": 0.0}
