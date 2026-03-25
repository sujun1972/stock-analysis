"""
涨跌停列表数据仓储层

负责 limit_list_d 表的数据访问操作
"""

from typing import List, Dict, Optional
import pandas as pd
from loguru import logger

from app.repositories.base_repository import BaseRepository


class LimitListRepository(BaseRepository):
    """涨跌停列表数据仓储类"""

    TABLE_NAME = "limit_list_d"

    def __init__(self, db=None):
        """
        初始化涨跌停列表仓储

        Args:
            db: 数据库连接（可选）
        """
        super().__init__(db)
        logger.debug("✓ LimitListRepository initialized")

    def get_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None,
        limit_type: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        按日期范围查询涨跌停列表数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            limit_type: 涨跌停类型（U涨停D跌停Z炸板）（可选）
            limit: 返回记录数限制

        Returns:
            涨跌停列表数据列表

        Examples:
            >>> repo = LimitListRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240101', '20240131', limit_type='U')
        """
        query = f"""
            SELECT
                trade_date, ts_code, industry, name,
                close, pct_chg, amount, limit_amount,
                float_mv, total_mv, turnover_ratio,
                fd_amount, first_time, last_time, open_times,
                up_stat, limit_times, limit_type,
                created_at, updated_at
            FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        params = [start_date, end_date]

        if ts_code:
            query += " AND ts_code = %s"
            params.append(ts_code)

        if limit_type:
            query += " AND limit_type = %s"
            params.append(limit_type)

        query += " ORDER BY trade_date DESC, pct_chg DESC LIMIT %s"
        params.append(limit)

        try:
            result = self.execute_query(query, tuple(params))
            logger.debug(f"查询到 {len(result)} 条涨跌停列表数据")
            return [self._row_to_dict(row) for row in result]
        except Exception as e:
            logger.error(f"查询涨跌停列表数据失败: {e}")
            raise

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'trade_date': row[0],
            'ts_code': row[1],
            'industry': row[2],
            'name': row[3],
            'close': float(row[4]) if row[4] is not None else None,
            'pct_chg': float(row[5]) if row[5] is not None else None,
            'amount': float(row[6]) if row[6] is not None else None,
            'limit_amount': float(row[7]) if row[7] is not None else None,
            'float_mv': float(row[8]) if row[8] is not None else None,
            'total_mv': float(row[9]) if row[9] is not None else None,
            'turnover_ratio': float(row[10]) if row[10] is not None else None,
            'fd_amount': float(row[11]) if row[11] is not None else None,
            'first_time': row[12],
            'last_time': row[13],
            'open_times': int(row[14]) if row[14] is not None else None,
            'up_stat': row[15],
            'limit_times': int(row[16]) if row[16] is not None else None,
            'limit_type': row[17],
            'created_at': str(row[18]) if row[18] is not None else None,
            'updated_at': str(row[19]) if row[19] is not None else None,
        }

    def get_statistics(
        self,
        start_date: str,
        end_date: str,
        limit_type: Optional[str] = None
    ) -> Dict:
        """
        获取涨跌停列表统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            limit_type: 涨跌停类型（U涨停D跌停Z炸板）（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = LimitListRepository()
            >>> stats = repo.get_statistics('20240101', '20240131', 'U')
        """
        query = f"""
            SELECT
                COUNT(*) as total_count,
                COUNT(DISTINCT trade_date) as trade_days,
                COUNT(DISTINCT ts_code) as stock_count,
                AVG(pct_chg) as avg_pct_chg,
                MAX(pct_chg) as max_pct_chg,
                AVG(limit_times) as avg_limit_times,
                MAX(limit_times) as max_limit_times
            FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        params = [start_date, end_date]

        if limit_type:
            query += " AND limit_type = %s"
            params.append(limit_type)

        try:
            result = self.execute_query(query, tuple(params))
            if result and len(result) > 0:
                row = result[0]
                return {
                    'total_count': row[0] or 0,
                    'trade_days': row[1] or 0,
                    'stock_count': row[2] or 0,
                    'avg_pct_chg': float(row[3]) if row[3] else 0.0,
                    'max_pct_chg': float(row[4]) if row[4] else 0.0,
                    'avg_limit_times': float(row[5]) if row[5] else 0.0,
                    'max_limit_times': int(row[6]) if row[6] else 0
                }
            return {
                'total_count': 0,
                'trade_days': 0,
                'stock_count': 0,
                'avg_pct_chg': 0.0,
                'max_pct_chg': 0.0,
                'avg_limit_times': 0.0,
                'max_limit_times': 0
            }
        except Exception as e:
            logger.error(f"获取涨跌停列表统计信息失败: {e}")
            raise

    def get_latest_trade_date(self) -> Optional[str]:
        """
        获取最新交易日期

        Returns:
            最新交易日期（YYYYMMDD格式），如果没有数据则返回None

        Examples:
            >>> repo = LimitListRepository()
            >>> latest_date = repo.get_latest_trade_date()
        """
        query = f"SELECT MAX(trade_date) FROM {self.TABLE_NAME}"
        try:
            result = self.execute_query(query)
            if result and result[0][0]:
                return result[0][0]
            return None
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise

    def bulk_upsert(self, df) -> int:
        """
        批量插入或更新涨跌停列表数据

        Args:
            df: pandas DataFrame，包含涨跌停列表数据

        Returns:
            影响的记录数

        Examples:
            >>> repo = LimitListRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空，跳过插入")
            return 0

        # 辅助函数：将pandas/numpy类型转换为Python原生类型
        def to_python_type(value):
            """
            将pandas/numpy类型转换为Python原生类型

            psycopg2无法直接处理numpy类型（numpy.int64, numpy.float64等）
            需要转换为Python原生类型（int, float, None）
            """
            if pd.isna(value):
                return None
            # 转换numpy整数类型为Python int
            if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return None
            # 转换numpy浮点类型为Python float
            if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                return float(value)
            # 字符串类型保持不变
            return value

        # 准备插入数据
        values = []
        for _, row in df.iterrows():
            values.append((
                to_python_type(row.get('trade_date')),
                to_python_type(row.get('ts_code')),
                to_python_type(row.get('industry')),
                to_python_type(row.get('name')),
                to_python_type(row.get('close')),
                to_python_type(row.get('pct_chg')),
                to_python_type(row.get('amount')),
                to_python_type(row.get('limit_amount')),
                to_python_type(row.get('float_mv')),
                to_python_type(row.get('total_mv')),
                to_python_type(row.get('turnover_ratio')),
                to_python_type(row.get('fd_amount')),
                to_python_type(row.get('first_time')),
                to_python_type(row.get('last_time')),
                to_python_type(row.get('open_times')),
                to_python_type(row.get('up_stat')),
                to_python_type(row.get('limit_times')),
                to_python_type(row.get('limit'))  # 从limit字段读取，数据库字段名为limit_type
            ))

        query = f"""
            INSERT INTO {self.TABLE_NAME}
            (trade_date, ts_code, industry, name, close, pct_chg, amount, limit_amount,
             float_mv, total_mv, turnover_ratio, fd_amount, first_time, last_time,
             open_times, up_stat, limit_times, limit_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (trade_date, ts_code)
            DO UPDATE SET
                industry = EXCLUDED.industry,
                name = EXCLUDED.name,
                close = EXCLUDED.close,
                pct_chg = EXCLUDED.pct_chg,
                amount = EXCLUDED.amount,
                limit_amount = EXCLUDED.limit_amount,
                float_mv = EXCLUDED.float_mv,
                total_mv = EXCLUDED.total_mv,
                turnover_ratio = EXCLUDED.turnover_ratio,
                fd_amount = EXCLUDED.fd_amount,
                first_time = EXCLUDED.first_time,
                last_time = EXCLUDED.last_time,
                open_times = EXCLUDED.open_times,
                up_stat = EXCLUDED.up_stat,
                limit_times = EXCLUDED.limit_times,
                limit_type = EXCLUDED.limit_type,
                updated_at = CURRENT_TIMESTAMP
        """

        try:
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条涨跌停列表数据")
            return count
        except Exception as e:
            logger.error(f"批量插入涨跌停列表数据失败: {e}")
            raise

    def delete_by_date_range(self, start_date: str, end_date: str) -> int:
        """
        删除指定日期范围的数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            删除的记录数

        Examples:
            >>> repo = LimitListRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
        """
        query = f"""
            DELETE FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        try:
            count = self.execute_update(query, (start_date, end_date))
            logger.info(f"删除了 {count} 条涨跌停列表数据")
            return count
        except Exception as e:
            logger.error(f"删除涨跌停列表数据失败: {e}")
            raise

    def exists_by_date(self, trade_date: str) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            trade_date: 交易日期，格式：YYYYMMDD

        Returns:
            如果存在返回True，否则返回False

        Examples:
            >>> repo = LimitListRepository()
            >>> exists = repo.exists_by_date('20240115')
        """
        query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE trade_date = %s"
        try:
            result = self.execute_query(query, (trade_date,))
            return result[0][0] > 0 if result else False
        except Exception as e:
            logger.error(f"检查数据是否存在失败: {e}")
            raise

    def get_record_count(self, start_date: str, end_date: str) -> int:
        """
        获取指定日期范围内的记录数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD

        Returns:
            记录数

        Examples:
            >>> repo = LimitListRepository()
            >>> count = repo.get_record_count('20240101', '20240131')
        """
        query = f"""
            SELECT COUNT(*) FROM {self.TABLE_NAME}
            WHERE trade_date >= %s AND trade_date <= %s
        """
        try:
            result = self.execute_query(query, (start_date, end_date))
            return result[0][0] if result else 0
        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            raise

    def get_top_limit_up_stocks(
        self,
        trade_date: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取指定日期的涨停股票排行（按连板数、涨幅排序）

        Args:
            trade_date: 交易日期，格式：YYYYMMDD
            limit: 返回记录数限制

        Returns:
            涨停股票列表

        Examples:
            >>> repo = LimitListRepository()
            >>> top_stocks = repo.get_top_limit_up_stocks('20240115', 20)
        """
        query = f"""
            SELECT
                trade_date, ts_code, industry, name,
                close, pct_chg, amount, fd_amount,
                first_time, last_time, open_times,
                up_stat, limit_times, limit_type
            FROM {self.TABLE_NAME}
            WHERE trade_date = %s AND limit_type = 'U'
            ORDER BY limit_times DESC, pct_chg DESC
            LIMIT %s
        """
        try:
            result = self.execute_query(query, (trade_date, limit))
            logger.debug(f"查询到 {len(result)} 条涨停股票数据")
            return result
        except Exception as e:
            logger.error(f"查询涨停股票排行失败: {e}")
            raise
