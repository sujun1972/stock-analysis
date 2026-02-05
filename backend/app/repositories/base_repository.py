"""
Base Repository
提供数据访问层的基础功能
"""

from typing import Any, List, Optional, Tuple

from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError
from psycopg2 import InterfaceError, OperationalError
from src.database.db_manager import DatabaseManager

from app.core.exceptions import DatabaseError, QueryError


class BaseRepository:
    """
    数据访问层基类

    封装 DatabaseManager，提供统一的数据库操作接口
    所有具体的 Repository 应继承此类
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化 Repository

        Args:
            db: DatabaseManager 实例，如果不提供则创建新实例
        """
        self.db = db or DatabaseManager()

    def execute_query(self, query: str, params: Optional[Tuple] = None) -> List[Tuple]:
        """
        执行查询并返回结果

        Args:
            query: SQL 查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        try:
            return self.db._execute_query(query, params or ())
        except (OperationalError, InterfaceError, PsycopgDatabaseError) as e:
            logger.error(f"数据库查询失败: {query[:100]}... - {e}")
            raise QueryError(
                "数据库查询执行失败",
                error_code="DB_QUERY_FAILED",
                query_preview=query[:100],
                reason=str(e),
            )

    def execute_update(self, query: str, params: Optional[Tuple] = None) -> int:
        """
        执行更新操作（INSERT, UPDATE, DELETE）

        Args:
            query: SQL 语句
            params: 参数

        Returns:
            受影响的行数
        """
        try:
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                affected_rows = cursor.rowcount
                conn.commit()
                cursor.close()
                return affected_rows
            finally:
                self.db.release_connection(conn)
        except (OperationalError, InterfaceError, PsycopgDatabaseError) as e:
            logger.error(f"数据库更新失败: {query[:100]}... - {e}")
            raise DatabaseError(
                "数据库更新操作失败",
                error_code="DB_UPDATE_FAILED",
                operation="update",
                query_preview=query[:100],
                reason=str(e),
            )

    def execute_insert(self, query: str, params: Optional[Tuple] = None) -> int:
        """
        执行插入操作并返回新插入行的 ID

        Args:
            query: INSERT 语句
            params: 参数

        Returns:
            新插入行的 ID
        """
        try:
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                last_id = cursor.lastrowid
                conn.commit()
                cursor.close()
                return last_id
            finally:
                self.db.release_connection(conn)
        except (OperationalError, InterfaceError, PsycopgDatabaseError) as e:
            logger.error(f"数据库插入失败: {query[:100]}... - {e}")
            raise DatabaseError(
                "数据库插入操作失败",
                error_code="DB_INSERT_FAILED",
                operation="insert",
                query_preview=query[:100],
                reason=str(e),
            )

    def find_by_id(self, table: str, id_value: Any, id_column: str = "id") -> Optional[Tuple]:
        """
        根据 ID 查找单条记录

        Args:
            table: 表名
            id_value: ID 值
            id_column: ID 列名（默认 'id'）

        Returns:
            记录元组，不存在则返回 None
        """
        query = f"SELECT * FROM {table} WHERE {id_column} = %s"
        results = self.execute_query(query, (id_value,))
        return results[0] if results else None

    def find_all(
        self,
        table: str,
        where: Optional[str] = None,
        params: Optional[Tuple] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Tuple]:
        """
        查找多条记录

        Args:
            table: 表名
            where: WHERE 子句（不含 WHERE 关键字）
            params: 参数
            order_by: 排序子句（如 "created_at DESC"）
            limit: 限制数量
            offset: 偏移量

        Returns:
            记录列表
        """
        query = f"SELECT * FROM {table}"

        if where:
            query += f" WHERE {where}"

        if order_by:
            query += f" ORDER BY {order_by}"

        if limit is not None:
            query += f" LIMIT {limit}"

        if offset is not None:
            query += f" OFFSET {offset}"

        return self.execute_query(query, params)

    def count(self, table: str, where: Optional[str] = None, params: Optional[Tuple] = None) -> int:
        """
        统计记录数

        Args:
            table: 表名
            where: WHERE 子句（不含 WHERE 关键字）
            params: 参数

        Returns:
            记录数
        """
        query = f"SELECT COUNT(*) FROM {table}"

        if where:
            query += f" WHERE {where}"

        result = self.execute_query(query, params)
        return result[0][0] if result else 0

    def exists(self, table: str, where: str, params: Optional[Tuple] = None) -> bool:
        """
        检查记录是否存在

        Args:
            table: 表名
            where: WHERE 子句（不含 WHERE 关键字）
            params: 参数

        Returns:
            是否存在
        """
        return self.count(table, where, params) > 0

    def delete_by_id(self, table: str, id_value: Any, id_column: str = "id") -> int:
        """
        根据 ID 删除记录

        Args:
            table: 表名
            id_value: ID 值
            id_column: ID 列名（默认 'id'）

        Returns:
            删除的行数
        """
        query = f"DELETE FROM {table} WHERE {id_column} = %s"
        return self.execute_update(query, (id_value,))
