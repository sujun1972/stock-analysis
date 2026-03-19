"""
概念板块数据访问层

提供概念板块和股票关系的增删改查操作，支持分页查询、股票关联管理等。

数据表: concept, stock_concept
"""

from typing import Dict, List, Optional, Tuple
from loguru import logger
from psycopg2 import DatabaseError as PsycopgDatabaseError

from app.core.exceptions import DatabaseError, QueryError
from app.repositories.base_repository import BaseRepository


class ConceptRepository(BaseRepository):
    """
    概念板块数据访问层

    职责：
    - 概念板块的增删改查
    - 股票与概念的关联管理
    - 分页查询支持
    - 统计信息查询
    """

    TABLE_NAME = "concept"
    STOCK_CONCEPT_TABLE = "stock_concept"

    def __init__(self, db=None):
        """初始化Repository"""
        super().__init__(db)
        logger.debug("✓ ConceptRepository initialized")

    # ==================== 概念查询操作 ====================

    def list_concepts(
        self,
        page: int = 1,
        page_size: int = 50,
        search: Optional[str] = None
    ) -> Tuple[List[Dict], int]:
        """
        分页查询概念列表

        Args:
            page: 页码（从1开始）
            page_size: 每页数量
            search: 搜索关键词（概念名称）

        Returns:
            (概念列表, 总数)

        Examples:
            >>> repo = ConceptRepository()
            >>> concepts, total = repo.list_concepts(page=1, page_size=50)
            >>> concepts, total = repo.list_concepts(search='芯片')
        """
        try:
            # 计算偏移量
            offset = (page - 1) * page_size

            # 构建查询条件
            conditions = []
            params = []
            if search:
                conditions.append("name ILIKE %s")
                params.append(f'%{search}%')

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # 查询总数
            count_query = f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE {where_clause}"
            count_result = self.execute_query(count_query, tuple(params))
            total = count_result[0][0] if count_result else 0

            # 查询数据
            data_query = f"""
                SELECT id, code, name, source, stock_count, created_at, updated_at
                FROM {self.TABLE_NAME}
                WHERE {where_clause}
                ORDER BY stock_count DESC, name
                LIMIT %s OFFSET %s
            """
            params.extend([page_size, offset])
            results = self.execute_query(data_query, tuple(params))

            concepts = [
                {
                    "id": row[0],
                    "code": row[1],
                    "name": row[2],
                    "source": row[3],
                    "stock_count": row[4] or 0,
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None
                }
                for row in results
            ]

            return concepts, total

        except PsycopgDatabaseError as e:
            logger.error(f"查询概念列表失败: {e}")
            raise QueryError(
                "概念列表查询失败",
                error_code="CONCEPT_LIST_QUERY_FAILED",
                page=page,
                page_size=page_size,
                search=search,
                reason=str(e)
            )

    def get_by_id(self, concept_id: int) -> Optional[Dict]:
        """
        根据ID获取概念详情

        Args:
            concept_id: 概念ID

        Returns:
            概念详情，不存在则返回None

        Examples:
            >>> repo = ConceptRepository()
            >>> concept = repo.get_by_id(1)
        """
        try:
            query = """
                SELECT id, code, name, source, description, stock_count, created_at, updated_at
                FROM concept
                WHERE id = %s
            """
            results = self.execute_query(query, (concept_id,))

            if not results:
                return None

            row = results[0]
            return {
                "id": row[0],
                "code": row[1],
                "name": row[2],
                "source": row[3],
                "description": row[4],
                "stock_count": row[5] or 0,
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None
            }

        except PsycopgDatabaseError as e:
            logger.error(f"查询概念详情失败: {e}")
            raise QueryError(
                "概念详情查询失败",
                error_code="CONCEPT_DETAIL_QUERY_FAILED",
                concept_id=concept_id,
                reason=str(e)
            )

    def get_by_code(self, code: str) -> Optional[Dict]:
        """
        根据代码获取概念

        Args:
            code: 概念代码

        Returns:
            概念详情，不存在则返回None
        """
        try:
            query = """
                SELECT id, code, name, source, description, stock_count, created_at, updated_at
                FROM concept
                WHERE code = %s
            """
            results = self.execute_query(query, (code,))

            if not results:
                return None

            row = results[0]
            return {
                "id": row[0],
                "code": row[1],
                "name": row[2],
                "source": row[3],
                "description": row[4],
                "stock_count": row[5] or 0,
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None
            }

        except PsycopgDatabaseError as e:
            logger.error(f"查询概念失败: {e}")
            raise QueryError(
                "概念查询失败",
                error_code="CONCEPT_QUERY_FAILED",
                code=code,
                reason=str(e)
            )

    # ==================== 股票-概念关联查询 ====================

    def get_concept_stocks(
        self,
        concept_id: int,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        获取概念包含的股票列表

        Args:
            concept_id: 概念ID
            limit: 限制返回数量

        Returns:
            股票列表

        Examples:
            >>> repo = ConceptRepository()
            >>> stocks = repo.get_concept_stocks(1, limit=100)
        """
        try:
            query = """
                SELECT
                    sc.stock_code,
                    si.name,
                    si.market,
                    si.industry
                FROM stock_concept sc
                LEFT JOIN stock_info si ON sc.stock_code = si.code
                WHERE sc.concept_id = %s
                ORDER BY sc.stock_code
            """

            if limit:
                query += f" LIMIT {int(limit)}"

            results = self.execute_query(query, (concept_id,))

            return [
                {
                    "code": row[0],
                    "name": row[1],
                    "market": row[2],
                    "industry": row[3]
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询概念股票列表失败: {e}")
            raise QueryError(
                "概念股票列表查询失败",
                error_code="CONCEPT_STOCKS_QUERY_FAILED",
                concept_id=concept_id,
                reason=str(e)
            )

    def get_stock_concepts(self, stock_code: str) -> List[Dict]:
        """
        获取股票所属的所有概念

        Args:
            stock_code: 股票代码

        Returns:
            概念列表

        Examples:
            >>> repo = ConceptRepository()
            >>> concepts = repo.get_stock_concepts('000001.SZ')
        """
        try:
            query = """
                SELECT
                    c.id,
                    c.code,
                    c.name,
                    c.source,
                    c.stock_count
                FROM stock_concept sc
                INNER JOIN concept c ON sc.concept_id = c.id
                WHERE sc.stock_code = %s
                ORDER BY c.name
            """

            results = self.execute_query(query, (stock_code,))

            return [
                {
                    "id": row[0],
                    "code": row[1],
                    "name": row[2],
                    "source": row[3],
                    "stock_count": row[4] or 0
                }
                for row in results
            ]

        except PsycopgDatabaseError as e:
            logger.error(f"查询股票概念列表失败: {e}")
            raise QueryError(
                "股票概念列表查询失败",
                error_code="STOCK_CONCEPTS_QUERY_FAILED",
                stock_code=stock_code,
                reason=str(e)
            )

    def get_stocks_by_concept_codes(self, concept_codes: List[str]) -> List[str]:
        """
        根据概念代码列表获取股票代码列表

        Args:
            concept_codes: 概念代码列表

        Returns:
            股票代码列表（去重）

        Examples:
            >>> repo = ConceptRepository()
            >>> stocks = repo.get_stocks_by_concept_codes(['BK0001', 'BK0002'])
        """
        try:
            if not concept_codes:
                return []

            # 构建 IN 子句
            placeholders = ','.join(['%s'] * len(concept_codes))

            query = f"""
                SELECT DISTINCT sc.stock_code
                FROM stock_concept sc
                INNER JOIN concept c ON sc.concept_id = c.id
                WHERE c.code IN ({placeholders})
            """

            results = self.execute_query(query, tuple(concept_codes))

            return [row[0] for row in results]

        except PsycopgDatabaseError as e:
            logger.error(f"查询概念股票代码失败: {e}")
            raise QueryError(
                "概念股票代码查询失败",
                error_code="CONCEPT_STOCK_CODES_QUERY_FAILED",
                concept_codes=concept_codes,
                reason=str(e)
            )

    # ==================== 写入和更新操作 ====================

    def update_stock_concepts(
        self,
        stock_code: str,
        concept_ids: List[int]
    ) -> int:
        """
        更新股票的概念标签（事务操作）

        会先删除该股票的所有概念关系，然后添加新的关系，最后更新概念的股票数量。

        Args:
            stock_code: 股票代码
            concept_ids: 概念ID列表

        Returns:
            添加的概念数量

        Raises:
            DatabaseError: 数据库操作失败

        Examples:
            >>> repo = ConceptRepository()
            >>> count = repo.update_stock_concepts('000001.SZ', [1, 2, 3])
        """
        conn = None
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()

            # 1. 删除该股票的所有概念关系
            cursor.execute(
                f"DELETE FROM {self.STOCK_CONCEPT_TABLE} WHERE stock_code = %s",
                (stock_code,)
            )

            # 2. 添加新的概念关系
            added_count = 0
            for concept_id in concept_ids:
                # 获取概念信息
                cursor.execute(
                    "SELECT code, name FROM concept WHERE id = %s",
                    (concept_id,)
                )
                concept_row = cursor.fetchone()

                if concept_row:
                    concept_code, concept_name = concept_row
                    cursor.execute(
                        f"""
                        INSERT INTO {self.STOCK_CONCEPT_TABLE}
                            (stock_code, concept_id, concept_code, concept_name)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (stock_code, concept_id, concept_code, concept_name)
                    )
                    added_count += 1

            # 3. 更新概念的股票数量
            for concept_id in concept_ids:
                cursor.execute(
                    """
                    UPDATE concept
                    SET stock_count = (
                        SELECT COUNT(*) FROM stock_concept WHERE concept_id = %s
                    )
                    WHERE id = %s
                    """,
                    (concept_id, concept_id)
                )

            # 提交事务
            conn.commit()
            cursor.close()

            logger.info(f"✓ 更新股票概念: {stock_code}, 添加了 {added_count} 个概念")
            return added_count

        except PsycopgDatabaseError as e:
            if conn:
                conn.rollback()
            logger.error(f"更新股票概念失败: {e}")
            raise DatabaseError(
                "更新股票概念失败",
                error_code="UPDATE_STOCK_CONCEPTS_FAILED",
                stock_code=stock_code,
                concept_ids=concept_ids,
                reason=str(e)
            )
        finally:
            if conn:
                self.db.release_connection(conn)

    # ==================== 统计操作 ====================

    def get_statistics(self) -> Dict:
        """
        获取概念统计信息

        Returns:
            统计信息字典

        Examples:
            >>> stats = repo.get_statistics()
            >>> print(f"概念总数: {stats['total_concepts']}")
        """
        try:
            query = """
                SELECT
                    COUNT(*) as total_concepts,
                    COUNT(DISTINCT source) as source_count,
                    SUM(stock_count) as total_stock_relations,
                    MAX(stock_count) as max_stock_count
                FROM concept
            """

            result = self.execute_query(query)

            if result and result[0]:
                row = result[0]
                return {
                    "total_concepts": row[0] or 0,
                    "source_count": row[1] or 0,
                    "total_stock_relations": row[2] or 0,
                    "max_stock_count": row[3] or 0
                }

            return {
                "total_concepts": 0,
                "source_count": 0,
                "total_stock_relations": 0,
                "max_stock_count": 0
            }

        except PsycopgDatabaseError as e:
            logger.error(f"获取概念统计失败: {e}")
            raise QueryError(
                "概念统计查询失败",
                error_code="CONCEPT_STATS_FAILED",
                reason=str(e)
            )
