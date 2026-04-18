"""
Base Repository
提供数据访问层的基础功能
"""

import re
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

    # 无界查询的硬上限：防止误用 find_all/get_by_date_range 拉取整张表
    DEFAULT_MAX_LIMIT: int = 10000

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化 Repository

        Args:
            db: DatabaseManager 实例，如果不提供则创建新实例
        """
        self.db = db or DatabaseManager()

    @staticmethod
    def _validate_identifier(identifier: str, name: str = "identifier") -> str:
        """
        验证并清理 SQL 标识符（表名、列名等）以防止 SQL 注入

        Args:
            identifier: 标识符字符串
            name: 标识符名称（用于错误消息）

        Returns:
            验证后的标识符

        Raises:
            QueryError: 如果标识符无效
        """
        # 只允许字母、数字、下划线
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
            raise QueryError(
                f"无效的 {name}：只允许字母、数字和下划线",
                error_code="INVALID_IDENTIFIER",
                identifier=identifier,
            )
        return identifier

    @classmethod
    def _enforce_limit(cls, limit: Optional[int]) -> int:
        """
        统一的 LIMIT 兜底 / 上限校验

        - limit 为 None：返回 DEFAULT_MAX_LIMIT（无界查询的兜底值）
        - limit 为正整数且 ≤ DEFAULT_MAX_LIMIT：原样返回
        - limit > DEFAULT_MAX_LIMIT 或 ≤ 0：抛 ValueError（由 API 层转 400）

        Args:
            limit: 调用方传入的 limit（允许 None）

        Returns:
            最终生效的 limit 整数

        Raises:
            ValueError: limit 超过 DEFAULT_MAX_LIMIT 或非正数
        """
        if limit is None:
            return cls.DEFAULT_MAX_LIMIT
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError(f"limit 必须为正整数，收到: {limit!r}")
        if limit > cls.DEFAULT_MAX_LIMIT:
            raise ValueError(
                f"limit 不能超过 {cls.DEFAULT_MAX_LIMIT}（收到 {limit}），"
                f"如需导出更大数据集请使用分页或专用批量接口"
            )
        return limit

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

    def find_by_id(
        self,
        table: str,
        id_value: Any,
        id_column: str = "id",
        columns: Optional[List[str]] = None,
    ) -> Optional[Tuple]:
        """
        根据 ID 查找单条记录

        Args:
            table: 表名
            id_value: ID 值
            id_column: ID 列名（默认 'id'）
            columns: 需要返回的列名白名单；默认 None 返回所有列（SELECT *）

        Returns:
            记录元组，不存在则返回 None
        """
        # 验证标识符防止 SQL 注入
        table = self._validate_identifier(table, "table")
        id_column = self._validate_identifier(id_column, "id_column")

        if columns:
            col_clause = ", ".join(
                self._validate_identifier(c, "column") for c in columns
            )
        else:
            col_clause = "*"

        query = f"SELECT {col_clause} FROM {table} WHERE {id_column} = %s"
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
        columns: Optional[List[str]] = None,
    ) -> List[Tuple]:
        """
        查找多条记录（强制 LIMIT 保护，防止误拉整表）

        Args:
            table: 表名
            where: WHERE 子句（不含 WHERE 关键字，使用参数化查询）
            params: 参数
            order_by: 排序子句（如 "created_at DESC"，仅限受信任的输入）
            limit: 限制数量。None 时使用 DEFAULT_MAX_LIMIT（10000）兜底；
                   超过 DEFAULT_MAX_LIMIT 抛 ValueError
            offset: 偏移量
            columns: 需要返回的列名白名单；默认 None 返回所有列（SELECT *）

        Returns:
            记录列表

        Raises:
            ValueError: limit 超过 DEFAULT_MAX_LIMIT 或非正数

        注意：
            - where 子句应使用 %s 占位符，不应直接拼接用户输入
            - order_by 应仅使用受信任的输入（如硬编码的列名）
        """
        # 验证表名防止 SQL 注入
        table = self._validate_identifier(table, "table")

        if columns:
            col_clause = ", ".join(
                self._validate_identifier(c, "column") for c in columns
            )
        else:
            col_clause = "*"

        query = f"SELECT {col_clause} FROM {table}"

        if where:
            query += f" WHERE {where}"

        if order_by:
            # 验证 order_by 中的列名（支持 "column ASC/DESC" 格式）
            order_parts = order_by.split()
            if order_parts:
                self._validate_identifier(order_parts[0], "order_by column")
            query += f" ORDER BY {order_by}"

        # 强制 LIMIT：None 兜底为 DEFAULT_MAX_LIMIT，超限抛 ValueError
        effective_limit = self._enforce_limit(limit)
        query += f" LIMIT {effective_limit}"

        if offset is not None:
            query += f" OFFSET {int(offset)}"

        return self.execute_query(query, params)

    def count(self, table: str, where: Optional[str] = None, params: Optional[Tuple] = None) -> int:
        """
        统计记录数

        Args:
            table: 表名
            where: WHERE 子句（不含 WHERE 关键字，使用参数化查询）
            params: 参数

        Returns:
            记录数
        """
        # 验证表名防止 SQL 注入
        table = self._validate_identifier(table, "table")

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
        # 验证标识符防止 SQL 注入
        table = self._validate_identifier(table, "table")
        id_column = self._validate_identifier(id_column, "id_column")

        query = f"DELETE FROM {table} WHERE {id_column} = %s"
        return self.execute_update(query, (id_value,))

    def execute_query_returning(
        self, query: str, params: Optional[Tuple] = None
    ) -> List[Tuple]:
        """
        执行带 RETURNING 子句的查询（用于 INSERT/UPDATE）

        Args:
            query: SQL 语句（包含 RETURNING 子句）
            params: 参数

        Returns:
            RETURNING 返回的结果列表

        Examples:
            >>> repo = BaseRepository()
            >>> result = repo.execute_query_returning(
            ...     "INSERT INTO table (col1) VALUES (%s) RETURNING id", (value,)
            ... )
            >>> new_id = result[0][0]
        """
        try:
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(query, params or ())
                result = cursor.fetchall()
                conn.commit()
                cursor.close()
                return result
            finally:
                self.db.release_connection(conn)
        except (OperationalError, InterfaceError, PsycopgDatabaseError) as e:
            logger.error(f"数据库 RETURNING 查询失败: {query[:100]}... - {e}")
            raise DatabaseError(
                "数据库 RETURNING 查询失败",
                error_code="DB_RETURNING_QUERY_FAILED",
                operation="insert_or_update",
                query_preview=query[:100],
                reason=str(e),
            )

    def execute_batch(self, query: str, values: List[Tuple]) -> int:
        """
        批量执行语句（如批量插入）

        Args:
            query: SQL 语句
            values: 参数列表

        Returns:
            受影响的总行数

        Examples:
            >>> repo = BaseRepository()
            >>> values = [(1, 'a'), (2, 'b'), (3, 'c')]
            >>> count = repo.execute_batch(
            ...     "INSERT INTO table (id, name) VALUES (%s, %s)", values
            ... )
        """
        try:
            conn = self.db.get_connection()
            try:
                cursor = conn.cursor()
                cursor.executemany(query, values)
                affected_rows = cursor.rowcount
                conn.commit()
                cursor.close()
                logger.info(f"✓ 批量操作成功: {affected_rows} 行")
                return affected_rows
            finally:
                self.db.release_connection(conn)
        except (OperationalError, InterfaceError, PsycopgDatabaseError) as e:
            logger.error(f"批量操作失败: {query[:100]}... - {e}")
            raise DatabaseError(
                "批量操作失败",
                error_code="DB_BATCH_FAILED",
                operation="batch_insert",
                query_preview=query[:100],
                reason=str(e),
            )
