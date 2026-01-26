"""
Batch Repository
管理实验批次的数据访问
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from .base_repository import BaseRepository
from loguru import logger


class BatchRepository(BaseRepository):
    """实验批次数据访问层"""

    def find_batches_with_stats(
        self,
        status: Optional[str] = None,
        strategy: Optional[str] = None,
        order_by: str = "created_at DESC",
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        查询批次列表（包含统计信息）

        Args:
            status: 批次状态过滤
            strategy: 策略过滤
            order_by: 排序规则
            limit: 限制数量
            offset: 偏移量

        Returns:
            批次列表（包含统计信息）
        """
        # 构建查询条件
        conditions = []
        params = []

        if status:
            conditions.append("eb.status = %s")
            params.append(status)

        if strategy:
            conditions.append("eb.strategy = %s")
            params.append(strategy)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # 主查询（注意：experiment_batches 表的主键是 id，不是 batch_id）
        query = f"""
            SELECT
                eb.id as batch_id,
                eb.batch_name,
                eb.strategy,
                eb.status,
                eb.total_experiments,
                eb.completed_experiments,
                eb.failed_experiments,
                eb.running_experiments,
                ROUND((eb.completed_experiments::DECIMAL / NULLIF(eb.total_experiments, 0)) * 100, 2) as success_rate_pct,
                eb.created_at,
                eb.started_at,
                eb.completed_at,
                EXTRACT(EPOCH FROM (COALESCE(eb.completed_at, NOW()) - eb.started_at)) / 3600 as duration_hours,
                AVG(e.rank_score) as avg_rank_score,
                MAX(e.rank_score) as max_rank_score,
                (
                    SELECT e2.id
                    FROM experiments e2
                    WHERE e2.batch_id = eb.id
                      AND e2.status = 'completed'
                      AND e2.rank_score IS NOT NULL
                    ORDER BY e2.rank_score DESC
                    LIMIT 1
                ) as top_model_id
            FROM experiment_batches eb
            LEFT JOIN experiments e ON eb.id = e.batch_id
            {where_clause}
            GROUP BY eb.id, eb.batch_name, eb.strategy, eb.status,
                     eb.total_experiments, eb.completed_experiments,
                     eb.failed_experiments, eb.running_experiments,
                     eb.created_at, eb.started_at, eb.completed_at
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
        """

        params.extend([limit, offset])
        results = self.execute_query(query, tuple(params))

        # 转换为字典列表
        batches = []
        for row in results:
            batches.append({
                'batch_id': row[0],
                'batch_name': row[1],
                'strategy': row[2],
                'status': row[3],
                'total_experiments': row[4],
                'completed_experiments': row[5],
                'failed_experiments': row[6],
                'running_experiments': row[7],
                'success_rate_pct': float(row[8]) if row[8] else 0,
                'created_at': row[9].isoformat() if row[9] else None,
                'started_at': row[10].isoformat() if row[10] else None,
                'completed_at': row[11].isoformat() if row[11] else None,
                'duration_hours': float(row[12]) if row[12] else None,
                'avg_rank_score': float(row[13]) if row[13] else None,
                'max_rank_score': float(row[14]) if row[14] else None,
                'top_model_id': row[15]
            })

        return batches

    def count_batches(
        self,
        status: Optional[str] = None,
        strategy: Optional[str] = None
    ) -> int:
        """
        统计批次数量

        Args:
            status: 状态过滤
            strategy: 策略过滤

        Returns:
            批次数量
        """
        conditions = []
        params = []

        if status:
            conditions.append("status = %s")
            params.append(status)

        if strategy:
            conditions.append("strategy = %s")
            params.append(strategy)

        where_clause = " AND ".join(conditions) if conditions else None
        return self.count("experiment_batches", where_clause, tuple(params) if params else None)

    def delete_batch_cascade(self, batch_id: int) -> Dict[str, int]:
        """
        级联删除批次及其所有实验

        Args:
            batch_id: 批次 ID（对应 experiment_batches.id）

        Returns:
            删除统计信息
        """
        try:
            # 先删除实验
            delete_experiments_query = "DELETE FROM experiments WHERE batch_id = %s"
            experiments_deleted = self.execute_update(delete_experiments_query, (batch_id,))

            # 再删除批次（experiment_batches 表的主键是 id）
            delete_batch_query = "DELETE FROM experiment_batches WHERE id = %s"
            batches_deleted = self.execute_update(delete_batch_query, (batch_id,))

            logger.info(f"✓ 删除批次 {batch_id}: 批次 {batches_deleted} 个, 实验 {experiments_deleted} 个")

            return {
                'batches_deleted': batches_deleted,
                'experiments_deleted': experiments_deleted
            }
        except Exception as e:
            logger.error(f"删除批次失败 {batch_id}: {e}")
            raise

    def update_batch_status(self, batch_id: int, status: str, **kwargs) -> int:
        """
        更新批次状态

        Args:
            batch_id: 批次 ID（对应 experiment_batches.id）
            status: 新状态
            **kwargs: 其他要更新的字段（如 started_at, completed_at）

        Returns:
            受影响的行数
        """
        set_clauses = ["status = %s"]
        params = [status]

        for field, value in kwargs.items():
            set_clauses.append(f"{field} = %s")
            params.append(value)

        params.append(batch_id)

        query = f"""
            UPDATE experiment_batches
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """

        return self.execute_update(query, tuple(params))

    def get_batch_by_id(self, batch_id: int) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取批次信息（包含计算字段和统计信息）

        Args:
            batch_id: 批次 ID（对应 experiment_batches.id）

        Returns:
            批次信息字典
        """
        # 使用与 find_batches_with_stats 类似的查询，确保包含所有计算字段
        query = """
            SELECT
                eb.id as batch_id,
                eb.batch_name,
                eb.description,
                eb.strategy,
                eb.param_space,
                eb.status,
                eb.total_experiments,
                eb.completed_experiments,
                eb.failed_experiments,
                eb.running_experiments,
                ROUND((eb.completed_experiments::DECIMAL / NULLIF(eb.total_experiments, 0)) * 100, 2) as success_rate_pct,
                eb.config,
                eb.created_at,
                eb.started_at,
                eb.completed_at,
                eb.created_by,
                eb.tags,
                EXTRACT(EPOCH FROM (COALESCE(eb.completed_at, NOW()) - eb.started_at)) / 3600 as duration_hours,
                AVG(e.rank_score) as avg_rank_score,
                MAX(e.rank_score) as max_rank_score,
                (
                    SELECT e2.id
                    FROM experiments e2
                    WHERE e2.batch_id = eb.id
                      AND e2.status = 'completed'
                      AND e2.rank_score IS NOT NULL
                    ORDER BY e2.rank_score DESC
                    LIMIT 1
                ) as top_model_id
            FROM experiment_batches eb
            LEFT JOIN experiments e ON eb.id = e.batch_id
            WHERE eb.id = %s
            GROUP BY eb.id, eb.batch_name, eb.description, eb.strategy, eb.param_space,
                     eb.status, eb.total_experiments, eb.completed_experiments,
                     eb.failed_experiments, eb.running_experiments, eb.config,
                     eb.created_at, eb.started_at, eb.completed_at, eb.created_by, eb.tags
        """

        results = self.execute_query(query, (batch_id,))
        if not results:
            return None

        row = results[0]
        return {
            'batch_id': row[0],
            'batch_name': row[1],
            'description': row[2],
            'strategy': row[3],
            'param_space': row[4],  # JSONB
            'status': row[5],
            'total_experiments': row[6],
            'completed_experiments': row[7],
            'failed_experiments': row[8],
            'running_experiments': row[9],
            'success_rate_pct': float(row[10]) if row[10] else 0.0,
            'config': row[11],  # JSONB
            'created_at': row[12].isoformat() if row[12] else None,
            'started_at': row[13].isoformat() if row[13] else None,
            'completed_at': row[14].isoformat() if row[14] else None,
            'created_by': row[15],
            'tags': row[16] if row[16] else [],
            'duration_hours': float(row[17]) if row[17] else None,
            'avg_rank_score': float(row[18]) if row[18] else None,
            'max_rank_score': float(row[19]) if row[19] else None,
            'top_model_id': row[20]
        }
