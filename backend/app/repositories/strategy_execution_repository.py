"""
Strategy Execution Repository
管理策略执行记录的数据访问
"""

import json
from typing import Any, Dict, List, Optional

from .base_repository import BaseRepository


class StrategyExecutionRepository(BaseRepository):
    """策略执行记录数据访问层"""

    def create(self, data: Dict[str, Any]) -> int:
        """
        创建策略执行记录

        Args:
            data: 执行记录数据字典
                - execution_type (str): 执行类型
                - execution_params (dict): 执行参数
                - predefined_strategy_type (str, optional): 预定义策略类型
                - config_strategy_id (int, optional): 配置策略ID
                - dynamic_strategy_id (int, optional): 动态策略ID
                - executed_by (str, optional): 执行人

        Returns:
            新创建记录的 ID
        """
        query = """
            INSERT INTO strategy_executions (
                predefined_strategy_type, config_strategy_id, dynamic_strategy_id,
                execution_type, execution_params, status, executed_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        params = (
            data.get('predefined_strategy_type'),
            data.get('config_strategy_id'),
            data.get('dynamic_strategy_id'),
            data['execution_type'],
            json.dumps(data['execution_params']),
            'pending',
            data.get('executed_by'),
        )

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            execution_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            return execution_id
        finally:
            self.db.release_connection(conn)

    def get_by_id(self, execution_id: int) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取执行记录

        Args:
            execution_id: 执行记录 ID

        Returns:
            执行记录字典，不存在则返回 None
        """
        query = """
            SELECT
                id, predefined_strategy_type, config_strategy_id, dynamic_strategy_id,
                execution_type, execution_params, status, result, metrics,
                error_message, execution_duration_ms,
                executed_by, started_at, completed_at, created_at
            FROM strategy_executions
            WHERE id = %s
        """

        results = self.execute_query(query, (execution_id,))
        if not results:
            return None

        row = results[0]
        return {
            'id': row[0],
            'predefined_strategy_type': row[1],
            'config_strategy_id': row[2],
            'dynamic_strategy_id': row[3],
            'execution_type': row[4],
            'execution_params': row[5],
            'status': row[6],
            'result': row[7],
            'metrics': row[8],
            'error_message': row[9],
            'execution_duration_ms': row[10],
            'executed_by': row[11],
            'started_at': row[12].isoformat() if row[12] else None,
            'completed_at': row[13].isoformat() if row[13] else None,
            'created_at': row[14].isoformat() if row[14] else None,
        }

    def list_by_config_strategy(
        self,
        config_strategy_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取配置策略的执行记录列表

        Args:
            config_strategy_id: 配置策略 ID
            limit: 限制数量

        Returns:
            执行记录列表
        """
        query = """
            SELECT
                id, execution_type, status, metrics,
                execution_duration_ms, started_at, completed_at, created_at
            FROM strategy_executions
            WHERE config_strategy_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """

        results = self.execute_query(query, (config_strategy_id, limit))

        items = []
        for row in results:
            items.append({
                'id': row[0],
                'execution_type': row[1],
                'status': row[2],
                'metrics': row[3],
                'execution_duration_ms': row[4],
                'started_at': row[5].isoformat() if row[5] else None,
                'completed_at': row[6].isoformat() if row[6] else None,
                'created_at': row[7].isoformat() if row[7] else None,
            })

        return items

    def list_by_dynamic_strategy(
        self,
        dynamic_strategy_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取动态策略的执行记录列表

        Args:
            dynamic_strategy_id: 动态策略 ID
            limit: 限制数量

        Returns:
            执行记录列表
        """
        query = """
            SELECT
                id, execution_type, status, metrics,
                execution_duration_ms, started_at, completed_at, created_at
            FROM strategy_executions
            WHERE dynamic_strategy_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """

        results = self.execute_query(query, (dynamic_strategy_id, limit))

        items = []
        for row in results:
            items.append({
                'id': row[0],
                'execution_type': row[1],
                'status': row[2],
                'metrics': row[3],
                'execution_duration_ms': row[4],
                'started_at': row[5].isoformat() if row[5] else None,
                'completed_at': row[6].isoformat() if row[6] else None,
                'created_at': row[7].isoformat() if row[7] else None,
            })

        return items

    def update_status(
        self,
        execution_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> int:
        """
        更新执行状态

        Args:
            execution_id: 执行记录 ID
            status: 新状态
            error_message: 错误消息（可选）

        Returns:
            受影响的行数
        """
        if status == 'running':
            query = """
                UPDATE strategy_executions
                SET status = %s, started_at = NOW()
                WHERE id = %s
            """
            params = (status, execution_id)
        elif status in ['completed', 'failed', 'cancelled']:
            query = """
                UPDATE strategy_executions
                SET status = %s,
                    completed_at = NOW(),
                    error_message = %s,
                    execution_duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
                WHERE id = %s
            """
            params = (status, error_message, execution_id)
        else:
            query = "UPDATE strategy_executions SET status = %s WHERE id = %s"
            params = (status, execution_id)

        return self.execute_update(query, params)

    def update_result(
        self,
        execution_id: int,
        result: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> int:
        """
        更新执行结果

        Args:
            execution_id: 执行记录 ID
            result: 完整结果数据
            metrics: 关键指标

        Returns:
            受影响的行数
        """
        query = """
            UPDATE strategy_executions
            SET result = %s, metrics = %s
            WHERE id = %s
        """
        return self.execute_update(
            query,
            (json.dumps(result), json.dumps(metrics), execution_id)
        )

    def get_statistics(
        self,
        config_strategy_id: Optional[int] = None,
        dynamic_strategy_id: Optional[int] = None,
        execution_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取执行统计信息

        Args:
            config_strategy_id: 配置策略 ID（可选）
            dynamic_strategy_id: 动态策略 ID（可选）
            execution_type: 执行类型（可选）

        Returns:
            统计信息字典
        """
        conditions = []
        params = []

        if config_strategy_id:
            conditions.append("config_strategy_id = %s")
            params.append(config_strategy_id)

        if dynamic_strategy_id:
            conditions.append("dynamic_strategy_id = %s")
            params.append(dynamic_strategy_id)

        if execution_type:
            conditions.append("execution_type = %s")
            params.append(execution_type)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'running') as running,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                AVG(execution_duration_ms) FILTER (WHERE status = 'completed') as avg_duration_ms
            FROM strategy_executions
            {where_clause}
        """

        result = self.execute_query(query, tuple(params))
        if not result:
            return {}

        row = result[0]
        return {
            'total': row[0],
            'completed': row[1],
            'failed': row[2],
            'running': row[3],
            'pending': row[4],
            'avg_duration_ms': float(row[5]) if row[5] else None,
        }
