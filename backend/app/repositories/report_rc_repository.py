"""
卖方盈利预测数据 Repository

管理 report_rc 表的数据访问
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository
from app.core.exceptions import QueryError


class ReportRcRepository(BaseRepository):
    """卖方盈利预测数据仓库"""

    TABLE_NAME = "report_rc"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ ReportRcRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        org_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询卖方盈利预测数据

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）
            org_name: 机构名称（可选）
            limit: 返回记录数限制（可选）

        Returns:
            数据列表

        Examples:
            >>> repo = ReportRcRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131')
            >>> data = repo.get_by_date_range('20240101', '20240131', ts_code='000001.SZ')
        """
        try:
            # 构建查询条件
            conditions = []
            params = []

            if start_date:
                conditions.append("report_date >= %s")
                params.append(start_date)
            else:
                conditions.append("report_date >= %s")
                params.append('19900101')

            if end_date:
                conditions.append("report_date <= %s")
                params.append(end_date)
            else:
                conditions.append("report_date <= %s")
                params.append('29991231')

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            if org_name:
                conditions.append("org_name = %s")
                params.append(org_name)

            where_clause = " AND ".join(conditions)

            # 构建查询
            query = f"""
                SELECT
                    ts_code, name, report_date, report_title, report_type,
                    classify, org_name, author_name, quarter,
                    op_rt, op_pr, tp, np, eps, pe, rd, roe, ev_ebitda,
                    rating, max_price, min_price, imp_dg,
                    create_time, created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY report_date DESC, ts_code
            """

            if limit:
                query += " LIMIT %s"
                params.append(limit)

            result = self.execute_query(query, tuple(params))

            # 转换为字典列表
            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'name': row[1],
                    'report_date': row[2],
                    'report_title': row[3],
                    'report_type': row[4],
                    'classify': row[5],
                    'org_name': row[6],
                    'author_name': row[7],
                    'quarter': row[8],
                    'op_rt': float(row[9]) if row[9] is not None else None,
                    'op_pr': float(row[10]) if row[10] is not None else None,
                    'tp': float(row[11]) if row[11] is not None else None,
                    'np': float(row[12]) if row[12] is not None else None,
                    'eps': float(row[13]) if row[13] is not None else None,
                    'pe': float(row[14]) if row[14] is not None else None,
                    'rd': float(row[15]) if row[15] is not None else None,
                    'roe': float(row[16]) if row[16] is not None else None,
                    'ev_ebitda': float(row[17]) if row[17] is not None else None,
                    'rating': row[18],
                    'max_price': float(row[19]) if row[19] is not None else None,
                    'min_price': float(row[20]) if row[20] is not None else None,
                    'imp_dg': row[21],
                    'create_time': row[22].isoformat() + 'Z' if row[22] else None,
                    'created_at': row[23].isoformat() + 'Z' if row[23] else None,
                    'updated_at': row[24].isoformat() + 'Z' if row[24] else None
                })

            logger.debug(f"查询到 {len(data)} 条卖方盈利预测数据")
            return data

        except Exception as e:
            logger.error(f"查询卖方盈利预测数据失败: {e}")
            raise QueryError(
                "数据查询失败",
                error_code="REPORT_RC_QUERY_FAILED",
                reason=str(e)
            )

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None
    ) -> Dict:
        """
        获取卖方盈利预测数据统计信息

        Args:
            start_date: 开始日期，格式：YYYYMMDD
            end_date: 结束日期，格式：YYYYMMDD
            ts_code: 股票代码（可选）

        Returns:
            统计信息字典

        Examples:
            >>> repo = ReportRcRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("report_date >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("report_date <= %s")
                params.append(end_date)

            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(*) as total_count,
                    COUNT(DISTINCT ts_code) as stock_count,
                    COUNT(DISTINCT org_name) as org_count,
                    AVG(eps) as avg_eps,
                    AVG(pe) as avg_pe,
                    AVG(roe) as avg_roe
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            row = result[0] if result else None

            if row:
                return {
                    'total_count': int(row[0]) if row[0] else 0,
                    'stock_count': int(row[1]) if row[1] else 0,
                    'org_count': int(row[2]) if row[2] else 0,
                    'avg_eps': float(row[3]) if row[3] is not None else 0,
                    'avg_pe': float(row[4]) if row[4] is not None else 0,
                    'avg_roe': float(row[5]) if row[5] is not None else 0
                }
            else:
                return {
                    'total_count': 0,
                    'stock_count': 0,
                    'org_count': 0,
                    'avg_eps': 0,
                    'avg_pe': 0,
                    'avg_roe': 0
                }

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise QueryError(
                "统计信息查询失败",
                error_code="REPORT_RC_STATS_FAILED",
                reason=str(e)
            )

    def get_latest_report_date(self) -> Optional[str]:
        """
        获取最新的研报日期

        Returns:
            最新研报日期（YYYYMMDD），如果没有数据返回 None

        Examples:
            >>> repo = ReportRcRepository()
            >>> latest_date = repo.get_latest_report_date()
        """
        try:
            query = f"""
                SELECT MAX(report_date)
                FROM {self.TABLE_NAME}
            """

            result = self.execute_query(query, ())
            latest_date = result[0][0] if result and result[0][0] else None

            logger.debug(f"最新研报日期: {latest_date}")
            return latest_date

        except Exception as e:
            logger.error(f"获取最新研报日期失败: {e}")
            return None

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新卖方盈利预测数据（UPSERT）

        Args:
            df: 包含卖方盈利预测数据的 DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = ReportRcRepository()
            >>> import pandas as pd
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过插入")
            return 0

        try:
            # 辅助函数：将 pandas/numpy 类型转换为 Python 原生类型
            def to_python_type(value):
                """
                将 pandas/numpy 类型转换为 Python 原生类型

                关键问题：psycopg2 无法直接处理 numpy 类型
                必须转换为 Python 原生类型（int, float, None）
                """
                if pd.isna(value):
                    return None
                # 转换 numpy 整数类型为 Python int
                if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
                    try:
                        return int(value)
                    except (ValueError, TypeError):
                        return None
                # 转换 numpy 浮点类型为 Python float
                if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
                    return float(value)
                return value

            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('name')),
                    to_python_type(row.get('report_date')),
                    to_python_type(row.get('report_title')),
                    to_python_type(row.get('report_type')),
                    to_python_type(row.get('classify')),
                    to_python_type(row.get('org_name')),
                    to_python_type(row.get('author_name')),
                    to_python_type(row.get('quarter')),
                    to_python_type(row.get('op_rt')),
                    to_python_type(row.get('op_pr')),
                    to_python_type(row.get('tp')),
                    to_python_type(row.get('np')),
                    to_python_type(row.get('eps')),
                    to_python_type(row.get('pe')),
                    to_python_type(row.get('rd')),
                    to_python_type(row.get('roe')),
                    to_python_type(row.get('ev_ebitda')),
                    to_python_type(row.get('rating')),
                    to_python_type(row.get('max_price')),
                    to_python_type(row.get('min_price')),
                    to_python_type(row.get('imp_dg')),
                    to_python_type(row.get('create_time'))
                ))

            # UPSERT 查询
            query = f"""
                INSERT INTO {self.TABLE_NAME} (
                    ts_code, name, report_date, report_title, report_type,
                    classify, org_name, author_name, quarter,
                    op_rt, op_pr, tp, np, eps, pe, rd, roe, ev_ebitda,
                    rating, max_price, min_price, imp_dg,
                    create_time, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, NOW(), NOW()
                )
                ON CONFLICT (ts_code, report_date, org_name, quarter)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    report_title = EXCLUDED.report_title,
                    report_type = EXCLUDED.report_type,
                    classify = EXCLUDED.classify,
                    author_name = EXCLUDED.author_name,
                    op_rt = EXCLUDED.op_rt,
                    op_pr = EXCLUDED.op_pr,
                    tp = EXCLUDED.tp,
                    np = EXCLUDED.np,
                    eps = EXCLUDED.eps,
                    pe = EXCLUDED.pe,
                    rd = EXCLUDED.rd,
                    roe = EXCLUDED.roe,
                    ev_ebitda = EXCLUDED.ev_ebitda,
                    rating = EXCLUDED.rating,
                    max_price = EXCLUDED.max_price,
                    min_price = EXCLUDED.min_price,
                    imp_dg = EXCLUDED.imp_dg,
                    create_time = EXCLUDED.create_time,
                    updated_at = NOW()
            """

            # 执行批量插入
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条卖方盈利预测数据")
            return count

        except Exception as e:
            logger.error(f"批量插入卖方盈利预测数据失败: {e}")
            raise QueryError(
                "批量插入数据失败",
                error_code="REPORT_RC_UPSERT_FAILED",
                reason=str(e)
            )

    def get_by_stock(
        self,
        ts_code: str,
        limit: Optional[int] = 30
    ) -> List[Dict]:
        """
        获取指定股票的卖方盈利预测数据

        Args:
            ts_code: 股票代码
            limit: 返回记录数限制

        Returns:
            数据列表

        Examples:
            >>> repo = ReportRcRepository()
            >>> data = repo.get_by_stock('000001.SZ', limit=50)
        """
        return self.get_by_date_range(
            ts_code=ts_code,
            limit=limit
        )

    def get_top_rated_stocks(
        self,
        report_date: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取指定日期的高评级股票

        Args:
            report_date: 研报日期，格式：YYYYMMDD
            limit: 返回记录数限制

        Returns:
            数据列表（按机构数量排序）

        Examples:
            >>> repo = ReportRcRepository()
            >>> data = repo.get_top_rated_stocks('20240115', limit=20)
        """
        try:
            query = f"""
                SELECT
                    ts_code,
                    name,
                    COUNT(DISTINCT org_name) as org_count,
                    AVG(eps) as avg_eps,
                    AVG(pe) as avg_pe,
                    AVG(max_price) as avg_target_price
                FROM {self.TABLE_NAME}
                WHERE report_date = %s
                    AND rating IN ('买入', '增持', '强烈推荐')
                GROUP BY ts_code, name
                ORDER BY org_count DESC, avg_target_price DESC
                LIMIT %s
            """

            result = self.execute_query(query, (report_date, limit))

            data = []
            for row in result:
                data.append({
                    'ts_code': row[0],
                    'name': row[1],
                    'org_count': int(row[2]) if row[2] else 0,
                    'avg_eps': float(row[3]) if row[3] is not None else None,
                    'avg_pe': float(row[4]) if row[4] is not None else None,
                    'avg_target_price': float(row[5]) if row[5] is not None else None
                })

            logger.debug(f"查询到 {len(data)} 个高评级股票")
            return data

        except Exception as e:
            logger.error(f"查询高评级股票失败: {e}")
            raise QueryError(
                "查询高评级股票失败",
                error_code="REPORT_RC_TOP_RATED_FAILED",
                reason=str(e)
            )
