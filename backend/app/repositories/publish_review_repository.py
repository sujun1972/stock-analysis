"""
策略发布审核历史 Repository
管理策略发布审核记录的数据访问

作者: Backend Team
创建日期: 2026-03-02
版本: 1.0.0
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_repository import BaseRepository


class PublishReviewRepository(BaseRepository):
    """策略发布审核历史数据访问层"""

    def create(self, data: Dict[str, Any]) -> int:
        """
        创建审核记录

        Args:
            data: 审核记录数据字典
                - strategy_id (int): 策略ID
                - reviewer_id (int): 审核人用户ID
                - action (str): 操作类型 (approve/reject/withdraw)
                - previous_status (str): 审核前状态
                - new_status (str): 审核后状态
                - comment (str, optional): 审核意见或拒绝原因
                - metadata (dict, optional): 额外元数据

        Returns:
            新创建记录的 ID
        """
        query = """
            INSERT INTO strategy_publish_reviews (
                strategy_id, reviewer_id, action, previous_status, new_status,
                comment, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        params = (
            data['strategy_id'],
            data['reviewer_id'],
            data['action'],
            data['previous_status'],
            data['new_status'],
            data.get('comment'),
            json.dumps(data.get('metadata')) if data.get('metadata') else None,
        )

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            review_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return review_id
        finally:
            self.db.release_connection(conn)

    def get_by_strategy_id(self, strategy_id: int) -> List[Dict[str, Any]]:
        """
        获取策略的所有审核历史记录

        Args:
            strategy_id: 策略ID

        Returns:
            审核历史记录列表（按时间倒序）
        """
        query = """
            SELECT
                r.id, r.strategy_id, r.reviewer_id, r.action,
                r.previous_status, r.new_status, r.comment,
                r.created_at, r.metadata,
                u.username as reviewer_username
            FROM strategy_publish_reviews r
            LEFT JOIN users u ON r.reviewer_id = u.id
            WHERE r.strategy_id = %s
            ORDER BY r.created_at DESC
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (strategy_id,))
            rows = cursor.fetchall()
            cursor.close()

            return [self._row_to_dict(cursor, row) for row in rows]
        finally:
            self.db.release_connection(conn)

    def get_latest_by_strategy_id(self, strategy_id: int) -> Optional[Dict[str, Any]]:
        """
        获取策略的最新审核记录

        Args:
            strategy_id: 策略ID

        Returns:
            最新审核记录，不存在则返回 None
        """
        query = """
            SELECT
                r.id, r.strategy_id, r.reviewer_id, r.action,
                r.previous_status, r.new_status, r.comment,
                r.created_at, r.metadata,
                u.username as reviewer_username
            FROM strategy_publish_reviews r
            LEFT JOIN users u ON r.reviewer_id = u.id
            WHERE r.strategy_id = %s
            ORDER BY r.created_at DESC
            LIMIT 1
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (strategy_id,))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return None

            return self._row_to_dict(cursor, row)
        finally:
            self.db.release_connection(conn)

    def list_all(
        self,
        reviewer_id: Optional[int] = None,
        action: Optional[str] = None,
        strategy_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取审核记录列表（支持筛选和分页）

        Args:
            reviewer_id: 审核人ID过滤
            action: 操作类型过滤 (approve/reject/withdraw)
            strategy_id: 策略ID过滤
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            {
                'items': [...],
                'meta': {
                    'total': 100,
                    'page': 1,
                    'page_size': 20,
                    'total_pages': 5
                }
            }
        """
        where_clauses = []
        params = []

        if reviewer_id is not None:
            where_clauses.append("r.reviewer_id = %s")
            params.append(reviewer_id)

        if action:
            where_clauses.append("r.action = %s")
            params.append(action)

        if strategy_id is not None:
            where_clauses.append("r.strategy_id = %s")
            params.append(strategy_id)

        where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"

        # 计算总数
        count_query = f"SELECT COUNT(*) FROM strategy_publish_reviews r WHERE {where_sql}"

        # 查询数据
        effective_page_size = self._enforce_limit(page_size)
        offset = (page - 1) * effective_page_size
        data_query = f"""
            SELECT
                r.id, r.strategy_id, r.reviewer_id, r.action,
                r.previous_status, r.new_status, r.comment,
                r.created_at, r.metadata,
                u.username as reviewer_username
            FROM strategy_publish_reviews r
            LEFT JOIN users u ON r.reviewer_id = u.id
            WHERE {where_sql}
            ORDER BY r.created_at DESC
            LIMIT %s OFFSET %s
        """

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()

            # 获取总数
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # 获取数据
            cursor.execute(data_query, params + [effective_page_size, offset])
            rows = cursor.fetchall()
            cursor.close()

            items = [self._row_to_dict(cursor, row) for row in rows]

            total_pages = (total + page_size - 1) // page_size

            return {
                'items': items,
                'meta': {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': total_pages
                }
            }
        finally:
            self.db.release_connection(conn)

    def _row_to_dict(self, cursor, row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        if not row:
            return {}

        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))

        # 解析 JSON 字段
        if 'metadata' in result and result['metadata']:
            result['metadata'] = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']

        return result
