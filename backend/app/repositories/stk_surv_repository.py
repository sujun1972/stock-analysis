"""
机构调研表 Repository

负责 stk_surv 表的数据访问操作
"""

from typing import List, Dict, Optional
from loguru import logger
import pandas as pd

from app.repositories.base_repository import BaseRepository


class StkSurvRepository(BaseRepository):
    """机构调研表 Repository"""

    TABLE_NAME = "stk_surv"

    def __init__(self, db=None):
        super().__init__(db)
        logger.debug("✓ StkSurvRepository initialized")

    def get_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        org_type: Optional[str] = None,
        rece_mode: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        按日期范围查询机构调研数据

        Args:
            start_date: 开始日期,格式:YYYYMMDD
            end_date: 结束日期,格式:YYYYMMDD
            ts_code: 股票代码(可选)
            org_type: 接待公司类型(可选)
            rece_mode: 接待方式(可选)
            limit: 限制返回数量(可选)

        Returns:
            机构调研数据列表

        Examples:
            >>> repo = StkSurvRepository()
            >>> data = repo.get_by_date_range('20240101', '20240131', ts_code='000001.SZ')
            >>> print(len(data))
        """
        try:
            # 构建WHERE条件
            conditions = []
            params = []

            if start_date:
                conditions.append("surv_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("surv_date <= %s")
                params.append(end_date)
            if ts_code:
                conditions.append("ts_code = %s")
                params.append(ts_code)
            if org_type:
                conditions.append("org_type = %s")
                params.append(org_type)
            if rece_mode:
                conditions.append("rece_mode = %s")
                params.append(rece_mode)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    id, ts_code, name, surv_date, fund_visitors,
                    rece_place, rece_mode, rece_org, org_type,
                    comp_rece, content, created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY surv_date DESC, ts_code
            """

            if limit:
                query += f" LIMIT {limit}"

            result = self.execute_query(query, tuple(params))
            return [self._row_to_dict(row) for row in result]

        except Exception as e:
            logger.error(f"查询机构调研数据失败: {e}")
            raise

    def get_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict:
        """
        获取机构调研统计信息

        Args:
            start_date: 开始日期,格式:YYYYMMDD
            end_date: 结束日期,格式:YYYYMMDD

        Returns:
            统计信息字典

        Examples:
            >>> repo = StkSurvRepository()
            >>> stats = repo.get_statistics('20240101', '20240131')
            >>> print(stats['total_records'])
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("surv_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("surv_date <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT ts_code) as unique_stocks,
                    COUNT(DISTINCT surv_date) as unique_dates,
                    COUNT(DISTINCT org_type) as unique_org_types
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            if result:
                row = result[0]
                return {
                    'total_records': int(row[0]) if row[0] else 0,
                    'unique_stocks': int(row[1]) if row[1] else 0,
                    'unique_dates': int(row[2]) if row[2] else 0,
                    'unique_org_types': int(row[3]) if row[3] else 0
                }
            return {
                'total_records': 0,
                'unique_stocks': 0,
                'unique_dates': 0,
                'unique_org_types': 0
            }

        except Exception as e:
            logger.error(f"获取机构调研统计信息失败: {e}")
            raise

    def get_latest_date(self) -> Optional[str]:
        """
        获取最新调研日期

        Returns:
            最新调研日期,格式:YYYYMMDD

        Examples:
            >>> repo = StkSurvRepository()
            >>> latest = repo.get_latest_date()
            >>> print(latest)  # '20240315'
        """
        try:
            query = f"""
                SELECT MAX(surv_date) as latest_date
                FROM {self.TABLE_NAME}
            """
            result = self.execute_query(query)
            if result and result[0][0]:
                return result[0][0]
            return None

        except Exception as e:
            logger.error(f"获取最新调研日期失败: {e}")
            raise

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """
        批量插入/更新机构调研数据

        Args:
            df: 包含机构调研数据的DataFrame

        Returns:
            插入/更新的记录数

        Examples:
            >>> repo = StkSurvRepository()
            >>> df = pd.DataFrame({...})
            >>> count = repo.bulk_upsert(df)
            >>> print(f"插入/更新了 {count} 条记录")
        """
        if df is None or df.empty:
            logger.warning("DataFrame为空,跳过插入")
            return 0

        try:
            # 辅助函数:将pandas/numpy类型转换为Python原生类型
            def to_python_type(value):
                """
                将pandas/numpy类型转换为Python原生类型

                ⚠️ 关键问题:psycopg2无法直接处理numpy类型
                """
                if pd.isna(value):
                    return None
                if isinstance(value, (int, float)):
                    return value
                return str(value) if value else None

            # 准备插入数据
            values = []
            for _, row in df.iterrows():
                values.append((
                    to_python_type(row.get('ts_code')),
                    to_python_type(row.get('name')),
                    to_python_type(row.get('surv_date')),
                    to_python_type(row.get('fund_visitors')),
                    to_python_type(row.get('rece_place')),
                    to_python_type(row.get('rece_mode')),
                    to_python_type(row.get('rece_org')),
                    to_python_type(row.get('org_type')),
                    to_python_type(row.get('comp_rece')),
                    to_python_type(row.get('content'))
                ))

            # UPSERT查询
            query = f"""
                INSERT INTO {self.TABLE_NAME}
                (ts_code, name, surv_date, fund_visitors, rece_place,
                 rece_mode, rece_org, org_type, comp_rece, content)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ts_code, surv_date, MD5(fund_visitors))
                DO UPDATE SET
                    name = EXCLUDED.name,
                    rece_place = EXCLUDED.rece_place,
                    rece_mode = EXCLUDED.rece_mode,
                    rece_org = EXCLUDED.rece_org,
                    org_type = EXCLUDED.org_type,
                    comp_rece = EXCLUDED.comp_rece,
                    content = EXCLUDED.content,
                    updated_at = NOW()
            """

            # 执行批量插入
            count = self.execute_batch(query, values)
            logger.info(f"成功插入/更新 {count} 条机构调研记录")
            return count

        except Exception as e:
            logger.error(f"批量插入机构调研数据失败: {e}")
            raise

    def delete_by_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> int:
        """
        删除指定日期范围的数据

        Args:
            start_date: 开始日期,格式:YYYYMMDD
            end_date: 结束日期,格式:YYYYMMDD

        Returns:
            删除的记录数

        Examples:
            >>> repo = StkSurvRepository()
            >>> count = repo.delete_by_date_range('20240101', '20240131')
            >>> print(f"删除了 {count} 条记录")
        """
        try:
            query = f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE surv_date >= %s AND surv_date <= %s
            """
            count = self.execute_update(query, (start_date, end_date))
            logger.info(f"删除了 {count} 条机构调研记录")
            return count

        except Exception as e:
            logger.error(f"删除机构调研数据失败: {e}")
            raise

    def exists_by_date(self, surv_date: str) -> bool:
        """
        检查指定日期的数据是否存在

        Args:
            surv_date: 调研日期,格式:YYYYMMDD

        Returns:
            是否存在数据

        Examples:
            >>> repo = StkSurvRepository()
            >>> exists = repo.exists_by_date('20240315')
            >>> print(exists)  # True or False
        """
        try:
            query = f"""
                SELECT EXISTS(
                    SELECT 1 FROM {self.TABLE_NAME}
                    WHERE surv_date = %s
                )
            """
            result = self.execute_query(query, (surv_date,))
            return result[0][0] if result else False

        except Exception as e:
            logger.error(f"检查日期数据存在性失败: {e}")
            raise

    def get_record_count(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
        """
        获取指定日期范围的记录数

        Args:
            start_date: 开始日期,格式:YYYYMMDD
            end_date: 结束日期,格式:YYYYMMDD

        Returns:
            记录数

        Examples:
            >>> repo = StkSurvRepository()
            >>> count = repo.get_record_count('20240101', '20240131')
            >>> print(count)
        """
        try:
            conditions = []
            params = []

            if start_date:
                conditions.append("surv_date >= %s")
                params.append(start_date)
            if end_date:
                conditions.append("surv_date <= %s")
                params.append(end_date)

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT COUNT(*) FROM {self.TABLE_NAME}
                WHERE {where_clause}
            """

            result = self.execute_query(query, tuple(params))
            return int(result[0][0]) if result and result[0][0] else 0

        except Exception as e:
            logger.error(f"获取记录数失败: {e}")
            raise

    def _row_to_dict(self, row: tuple) -> Dict:
        """
        将查询结果行转换为字典

        Args:
            row: 查询结果行

        Returns:
            字典格式的数据
        """
        return {
            'id': row[0],
            'ts_code': row[1],
            'name': row[2],
            'surv_date': row[3],
            'fund_visitors': row[4],
            'rece_place': row[5],
            'rece_mode': row[6],
            'rece_org': row[7],
            'org_type': row[8],
            'comp_rece': row[9],
            'content': row[10],
            'created_at': row[11].isoformat() if row[11] else None,
            'updated_at': row[12].isoformat() if row[12] else None
        }
