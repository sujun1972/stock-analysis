"""
业绩预告数据Repository

管理forecast表的数据访问
"""

import pandas as pd
from typing import List, Dict, Optional
from loguru import logger

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class ForecastRepository(BaseRepository):
    """业绩预告数据Repository"""

    TABLE_NAME = "forecast"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ ForecastRepository initialized")

    def get_by_date_range(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        type_: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询业绩预告数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            period: 报告期（可选，如：20171231表示年报）
            type_: 预告类型（可选，如：预增/预减/扭亏/首亏）
            limit: 限制返回记录数

        Returns:
            业绩预告数据列表

        Examples:
            >>> repo = ForecastRepository()
            >>> data = repo.get_by_date_range('20240101', '20241231')
            >>> data = repo.get_by_date_range(ts_code='600000.SH', type_='预增')
        """
        try:
            query = f"""
                SELECT ts_code, ann_date, end_date, type,
                       p_change_min, p_change_max,
                       net_profit_min, net_profit_max, last_parent_net,
                       first_ann_date, summary, change_reason,
                       created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE ann_date >= %s AND ann_date <= %s
            """
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            if period:
                query += " AND end_date = %s"
                params.append(period)

            if type_:
                query += " AND type = %s"
                params.append(type_)

            query += " ORDER BY ann_date DESC, ts_code"

            query += " LIMIT %s"
            params.append(self._enforce_limit(limit))

            if offset:
                query += " OFFSET %s"
                params.append(offset)

            result = self.execute_query(query, tuple(params))

            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询业绩预告数据失败: {e}")
            raise QueryError(
                "业绩预告数据查询失败",
                error_code="FORECAST_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None,
        type_: Optional[str] = None
    ) -> Dict:
        """
        获取业绩预告统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            type_: 预告类型（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = ForecastRepository()
            >>> stats = repo.get_statistics('20240101', '20241231')
        """
        try:
            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    AVG(p_change_min) as avg_p_change_min,
                    AVG(p_change_max) as avg_p_change_max,
                    AVG(net_profit_min) as avg_net_profit_min,
                    AVG(net_profit_max) as avg_net_profit_max,
                    SUM(CASE WHEN type IN ('预增', '略增', '续盈', '扭亏') THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN type IN ('预减', '略减', '续亏', '首亏') THEN 1 ELSE 0 END) as negative_count
                FROM {self.TABLE_NAME}
                WHERE ann_date >= %s AND ann_date <= %s
            """
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            if type_:
                query += " AND type = %s"
                params.append(type_)

            result = self.execute_query(query, tuple(params))

            if result:
                row = result[0]
                total = row[0] or 0
                positive = row[6] or 0
                negative = row[7] or 0

                return {
                    'total_count': total,
                    'stock_count': row[1] or 0,
                    'avg_p_change_min': float(row[2]) if row[2] else 0.0,
                    'avg_p_change_max': float(row[3]) if row[3] else 0.0,
                    'avg_net_profit_min': float(row[4]) if row[4] else 0.0,
                    'avg_net_profit_max': float(row[5]) if row[5] else 0.0,
                    'positive_count': positive,
                    'negative_count': negative,
                    'positive_ratio': (positive / total * 100) if total > 0 else 0.0,
                    'negative_ratio': (negative / total * 100) if total > 0 else 0.0
                }

            return {
                'total_count': 0,
                'stock_count': 0,
                'avg_p_change_min': 0.0,
                'avg_p_change_max': 0.0,
                'avg_net_profit_min': 0.0,
                'avg_net_profit_max': 0.0,
                'positive_count': 0,
                'negative_count': 0,
                'positive_ratio': 0.0,
                'negative_ratio': 0.0
            }

        except Exception as e:
            logger.error(f"获取业绩预告统计信息失败: {e}")
            raise QueryError(
                "业绩预告统计查询失败",
                error_code="FORECAST_STATISTICS_FAILED",
                reason=str(e)
            )

    def get_latest_ann_date(self, ts_code: Optional[str] = None) -> Optional[str]:
        """
        获取最新公告日期

        Args:
            ts_code: 股票代码（可选）

        Returns:
            最新公告日期（YYYYMMDD格式），如果没有数据返回None

        Examples:
            >>> repo = ForecastRepository()
            >>> latest_date = repo.get_latest_ann_date()
            >>> latest_date = repo.get_latest_ann_date(ts_code='600000.SH')
        """
        try:
            query = f"SELECT MAX(ann_date) FROM {self.TABLE_NAME}"
            params = []

            if ts_code:
                query += " WHERE ts_code = %s"
                params.append(ts_code)

            result = self.execute_query(query, tuple(params) if params else None)

            if result and result[0][0]:
                return result[0][0]

            return None

        except Exception as e:
            logger.error(f"获取最新公告日期失败: {e}")
            raise QueryError(
                "获取最新公告日期失败",
                error_code="FORECAST_LATEST_DATE_FAILED",
                reason=str(e)
            )

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新业绩预告数据

        Args:
            df: 包含业绩预告数据的DataFrame

        Returns:
            受影响的记录数

        Examples:
            >>> repo = ForecastRepository()
            >>> import pandas as pd
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

                ⚠️ 关键问题：psycopg2无法直接处理numpy类型
                必须转换为Python原生类型（int, float, None）
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
                return value

            # 准备UPSERT查询
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, ann_date, end_date, type,
                 p_change_min, p_change_max,
                 net_profit_min, net_profit_max, last_parent_net,
                 first_ann_date, summary, change_reason,
                 updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (ts_code, ann_date, end_date)
                DO UPDATE SET
                    type = EXCLUDED.type,
                    p_change_min = EXCLUDED.p_change_min,
                    p_change_max = EXCLUDED.p_change_max,
                    net_profit_min = EXCLUDED.net_profit_min,
                    net_profit_max = EXCLUDED.net_profit_max,
                    last_parent_net = EXCLUDED.last_parent_net,
                    first_ann_date = EXCLUDED.first_ann_date,
                    summary = EXCLUDED.summary,
                    change_reason = EXCLUDED.change_reason,
                    updated_at = NOW()
            """

            # 准备插入数据（对每个字段应用类型转换）
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('ann_date')),
                    to_python_type(row.get('end_date')),
                    to_python_type(row.get('type')),
                    to_python_type(row.get('p_change_min')),
                    to_python_type(row.get('p_change_max')),
                    to_python_type(row.get('net_profit_min')),
                    to_python_type(row.get('net_profit_max')),
                    to_python_type(row.get('last_parent_net')),
                    to_python_type(row.get('first_ann_date')),
                    to_python_type(row.get('summary')),
                    to_python_type(row.get('change_reason'))
                ))

            # 执行批量插入
            count = self.execute_batch(query, values)

            logger.info(f"成功插入/更新 {count} 条业绩预告记录")
            return count

        except Exception as e:
            logger.error(f"批量插入业绩预告数据失败: {e}")
            raise QueryError(
                "批量插入业绩预告数据失败",
                error_code="FORECAST_BULK_UPSERT_FAILED",
                reason=str(e)
            )

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str,
        ts_code: Optional[str] = None
    ) -> int:
        """
        按日期范围删除数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            删除的记录数

        Examples:
            >>> repo = ForecastRepository()
            >>> count = repo.delete_by_date_range('20240101', '20241231')
        """
        try:
            query = f"DELETE FROM {self.TABLE_NAME} WHERE ann_date >= %s AND ann_date <= %s"
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            count = self.execute_update(query, tuple(params))

            logger.info(f"删除了 {count} 条业绩预告记录")
            return count

        except Exception as e:
            logger.error(f"删除业绩预告数据失败: {e}")
            raise QueryError(
                "删除业绩预告数据失败",
                error_code="FORECAST_DELETE_FAILED",
                reason=str(e)
            )

    def exists_by_date(self, ann_date: str, ts_code: Optional[str] = None) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            ann_date: 公告日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            True 如果存在，否则 False

        Examples:
            >>> repo = ForecastRepository()
            >>> exists = repo.exists_by_date('20240115')
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE ann_date = %s"
            params = [ann_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            result = self.execute_query(query, tuple(params))

            return result[0][0] > 0 if result else False

        except Exception as e:
            logger.error(f"检查业绩预告数据是否存在失败: {e}")
            return False

    def get_record_count(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None
    ) -> int:
        """
        获取记录总数

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            记录总数

        Examples:
            >>> repo = ForecastRepository()
            >>> count = repo.get_record_count('20240101', '20241231')
        """
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE ann_date >= %s AND ann_date <= %s"
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            result = self.execute_query(query, tuple(params))

            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"获取业绩预告记录数失败: {e}")
            raise QueryError(
                "获取业绩预告记录数失败",
                error_code="FORECAST_COUNT_FAILED",
                reason=str(e)
            )

    def get_total_count(
        self,
        start_date: str = '19900101',
        end_date: str = '29991231',
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        type_: Optional[str] = None
    ) -> int:
        """获取符合条件的记录总数"""
        try:
            query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE ann_date >= %s AND ann_date <= %s"
            params = [start_date, end_date]

            if ts_code:
                query += " AND ts_code = %s"
                params.append(ts_code)

            if period:
                query += " AND end_date = %s"
                params.append(period)

            if type_:
                query += " AND type = %s"
                params.append(type_)

            result = self.execute_query(query, tuple(params))
            return int(result[0][0]) if result else 0

        except Exception as e:
            logger.error(f"获取业绩预告记录总数失败: {e}")
            raise QueryError(
                "获取业绩预告记录总数失败",
                error_code="FORECAST_TOTAL_COUNT_FAILED",
                reason=str(e)
            )

    def get_by_type(
        self,
        type_: str,
        start_date: str = '19900101',
        end_date: str = '29991231',
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按预告类型查询数据

        Args:
            type_: 预告类型（如：预增、预减、扭亏、首亏）
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            limit: 限制返回记录数

        Returns:
            业绩预告数据列表

        Examples:
            >>> repo = ForecastRepository()
            >>> data = repo.get_by_type('预增', limit=50)
        """
        return self.get_by_date_range(
            start_date=start_date,
            end_date=end_date,
            type_=type_,
            limit=limit
        )

    def get_by_period(
        self,
        period: str,
        start_date: str = '19900101',
        end_date: str = '29991231',
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按报告期查询数据

        Args:
            period: 报告期（如：20171231表示年报，20170630半年报）
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            limit: 限制返回记录数

        Returns:
            业绩预告数据列表

        Examples:
            >>> repo = ForecastRepository()
            >>> data = repo.get_by_period('20181231', limit=100)
        """
        return self.get_by_date_range(
            start_date=start_date,
            end_date=end_date,
            period=period,
            limit=limit
        )

    def _row_to_dict(self, row: tuple) -> Dict:
        """将查询结果行转换为字典"""
        return {
            'ts_code': row[0],
            'ann_date': row[1],
            'end_date': row[2],
            'type': row[3],
            'p_change_min': float(row[4]) if row[4] is not None else None,
            'p_change_max': float(row[5]) if row[5] is not None else None,
            'net_profit_min': float(row[6]) if row[6] is not None else None,
            'net_profit_max': float(row[7]) if row[7] is not None else None,
            'last_parent_net': float(row[8]) if row[8] is not None else None,
            'first_ann_date': row[9],
            'summary': row[10],
            'change_reason': row[11],
            'created_at': row[12].isoformat() if row[12] else None,
            'updated_at': row[13].isoformat() if row[13] else None
        }
