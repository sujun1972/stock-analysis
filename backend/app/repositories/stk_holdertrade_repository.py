"""
股东增减持数据Repository

负责stk_holdertrade表的数据访问操作
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class StkHoldertradeRepository(BaseRepository):
    """股东增减持Repository"""

    TABLE_NAME = "stk_holdertrade"

    def __init__(self, db=None):
        super().__init__(db)

    def get_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        holder_type: Optional[str] = None,
        trade_type: Optional[str] = None
    ) -> int:
        """
        获取符合条件的记录总数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            holder_type: 股东类型（可选）
            trade_type: 交易类型（可选）

        Returns:
            记录总数
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE 1=1"
            params = []
            if start_date:
                query += " AND ann_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND ann_date <= %s"
                params.append(end_date)
            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)
            if holder_type:
                query += " AND holder_type = %s"
                params.append(holder_type)
            if trade_type:
                query += " AND in_de = %s"
                params.append(trade_type)
            result = self.execute_query(query, tuple(params) if params else None)
            return int(result[0][0]) if result else 0
        except Exception as e:
            logger.error(f"获取记录总数失败: {e}")
            return 0

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        holder_type: Optional[str] = None,
        trade_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict]:
        """
        按日期范围查询股东增减持数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            holder_type: 股东类型（可选）G=高管 P=个人 C=公司
            trade_type: 交易类型（可选）IN=增持 DE=减持
            limit: 限制返回数量

        Returns:
            股东增减持数据列表

        Examples:
            >>> repo = StkHoldertradeRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range(ts_code='000001.SZ', trade_type='IN')
        """
        try:
            query = f"""
                SELECT
                    ts_code,
                    ann_date,
                    holder_name,
                    holder_type,
                    in_de,
                    change_vol,
                    change_ratio,
                    after_share,
                    after_ratio,
                    avg_price,
                    total_share,
                    begin_date,
                    close_date,
                    created_at,
                    updated_at
                FROM {self.TABLE_NAME}
                WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND ann_date >= %s"
                params.append(start_date)

            if end_date:
                query += " AND ann_date <= %s"
                params.append(end_date)

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            if holder_type:
                query += " AND holder_type = %s"
                params.append(holder_type)

            if trade_type:
                query += " AND in_de = %s"
                params.append(trade_type)

            query += " ORDER BY ann_date DESC, ts_code"

            query += " LIMIT %s"
            params.append(self._enforce_limit(limit))

            if offset:
                query += " OFFSET %s"
                params.append(offset)

            result = self.execute_query(query, tuple(params) if params else None)

            return [
                {
                    "ts_code": row[0],
                    "ann_date": row[1],
                    "holder_name": row[2],
                    "holder_type": row[3],
                    "in_de": row[4],
                    "change_vol": float(row[5]) if row[5] is not None else None,
                    "change_ratio": float(row[6]) if row[6] is not None else None,
                    "after_share": float(row[7]) if row[7] is not None else None,
                    "after_ratio": float(row[8]) if row[8] is not None else None,
                    "avg_price": float(row[9]) if row[9] is not None else None,
                    "total_share": float(row[10]) if row[10] is not None else None,
                    "begin_date": row[11],
                    "close_date": row[12],
                    "created_at": row[13],
                    "updated_at": row[14]
                }
                for row in result
            ]

        except Exception as e:
            logger.error(f"查询股东增减持数据失败: {e}")
            raise

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取股东增减持统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = StkHoldertradeRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
        """
        try:
            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    COUNT(CASE WHEN in_de = 'IN' THEN 1 END) as increase_count,
                    COUNT(CASE WHEN in_de = 'DE' THEN 1 END) as decrease_count,
                    SUM(CASE WHEN in_de = 'IN' THEN change_vol ELSE 0 END) as total_increase_vol,
                    SUM(CASE WHEN in_de = 'DE' THEN change_vol ELSE 0 END) as total_decrease_vol,
                    AVG(CASE WHEN in_de = 'IN' THEN change_ratio END) as avg_increase_ratio,
                    AVG(CASE WHEN in_de = 'DE' THEN change_ratio END) as avg_decrease_ratio
                FROM {self.TABLE_NAME}
                WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND ann_date >= %s"
                params.append(start_date)

            if end_date:
                query += " AND ann_date <= %s"
                params.append(end_date)

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            result = self.execute_query(query, tuple(params) if params else None)

            if result and len(result) > 0:
                row = result[0]
                return {
                    "total_count": int(row[0]) if row[0] else 0,
                    "stock_count": int(row[1]) if row[1] else 0,
                    "increase_count": int(row[2]) if row[2] else 0,
                    "decrease_count": int(row[3]) if row[3] else 0,
                    "total_increase_vol": float(row[4]) if row[4] else 0.0,
                    "total_decrease_vol": float(row[5]) if row[5] else 0.0,
                    "avg_increase_ratio": float(row[6]) if row[6] else 0.0,
                    "avg_decrease_ratio": float(row[7]) if row[7] else 0.0
                }

            return {
                "total_count": 0,
                "stock_count": 0,
                "increase_count": 0,
                "decrease_count": 0,
                "total_increase_vol": 0.0,
                "total_decrease_vol": 0.0,
                "avg_increase_ratio": 0.0,
                "avg_decrease_ratio": 0.0
            }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise

    def get_latest_ann_date(self) -> Optional[str]:
        """
        获取最新公告日期

        Returns:
            最新公告日期（YYYYMMDD格式），如果没有数据则返回None
        """
        try:
            query = f"SELECT MAX(ann_date) FROM {self.TABLE_NAME}"
            result = self.execute_query(query)

            if result and result[0][0]:
                return str(result[0][0])

            return None

        except Exception as e:
            logger.error(f"获取最新公告日期失败: {e}")
            raise

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新股东增减持数据

        使用PostgreSQL的ON CONFLICT DO UPDATE实现UPSERT语义

        Args:
            df: 包含股东增减持数据的DataFrame

        Returns:
            成功插入/更新的记录数

        Examples:
            >>> repo = StkHoldertradeRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        try:
            # 辅助函数：将pandas/numpy类型转换为Python原生类型
            def to_python_type(value):
                """
                将pandas/numpy类型转换为Python原生类型
                psycopg2无法直接处理numpy类型，必须转换
                """
                if pd.isna(value):
                    return None
                if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                    return float(value)
                return value

            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('ann_date')),
                    to_python_type(row.get('holder_name')),
                    to_python_type(row.get('holder_type')),
                    to_python_type(row.get('in_de')),
                    to_python_type(row.get('change_vol')),
                    to_python_type(row.get('change_ratio')),
                    to_python_type(row.get('after_share')),
                    to_python_type(row.get('after_ratio')),
                    to_python_type(row.get('avg_price')),
                    to_python_type(row.get('total_share')),
                    to_python_type(row.get('begin_date')),
                    to_python_type(row.get('close_date'))
                ))

            # UPSERT SQL
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, ann_date, holder_name, holder_type, in_de, change_vol,
                 change_ratio, after_share, after_ratio, avg_price, total_share,
                 begin_date, close_date, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (ts_code, ann_date, holder_name, in_de)
                DO UPDATE SET
                    holder_type = EXCLUDED.holder_type,
                    change_vol = EXCLUDED.change_vol,
                    change_ratio = EXCLUDED.change_ratio,
                    after_share = EXCLUDED.after_share,
                    after_ratio = EXCLUDED.after_ratio,
                    avg_price = EXCLUDED.avg_price,
                    total_share = EXCLUDED.total_share,
                    begin_date = EXCLUDED.begin_date,
                    close_date = EXCLUDED.close_date,
                    updated_at = NOW()
            """

            count = self.execute_batch(query, values)
            logger.info(f"批量插入/更新 {count} 条股东增减持记录")
            return count

        except Exception as e:
            logger.error(f"批量插入失败: {e}")
            raise

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> int:
        """
        按日期范围删除数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            删除的记录数
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE ann_date >= %s AND ann_date <= %s
            """
            count = self.execute_update(query, (start_date, end_date))
            logger.info(f"删除 {count} 条记录 (日期范围: {start_date} - {end_date})")
            return count

        except Exception as e:
            logger.error(f"删除数据失败: {e}")
            raise

    def exists_by_date(self, ann_date: str) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            ann_date: 公告日期，格式：YYYYMMDD

        Returns:
            True表示存在，False表示不存在
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE ann_date = %s"
            result = self.execute_query(query, (ann_date,))
            return result[0][0] > 0 if result else False

        except Exception as e:
            logger.error(f"检查数据是否存在失败: {e}")
            raise

    def get_record_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        获取记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            记录数
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE 1=1"
            params = []

            if start_date:
                query += " AND ann_date >= %s"
                params.append(start_date)

            if end_date:
                query += " AND ann_date <= %s"
                params.append(end_date)

            result = self.execute_query(query, tuple(params) if params else None)
            return int(result[0][0]) if result else 0

        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            raise
