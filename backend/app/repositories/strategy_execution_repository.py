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
                - task_id (str, optional): Celery 任务ID

        Returns:
            新创建记录的 ID
        """
        from loguru import logger

        query = """
            INSERT INTO strategy_executions (
                predefined_strategy_type, config_strategy_id, dynamic_strategy_id,
                strategy_id, execution_type, execution_params, status, executed_by, task_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        # 序列化execution_params
        try:
            execution_params_json = json.dumps(data['execution_params'])
            logger.debug("Serialized execution_params length: %d", len(execution_params_json))
        except Exception as e:
            error_msg = str(e)
            logger.error("Failed to serialize execution_params: %s", error_msg)
            raise ValueError("Failed to serialize execution_params: " + error_msg)

        params = (
            data.get('predefined_strategy_type'),
            data.get('config_strategy_id'),
            data.get('dynamic_strategy_id'),
            data.get('strategy_id'),
            data['execution_type'],
            execution_params_json,
            'pending',
            data.get('executed_by'),
            data.get('task_id'),
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
                executed_by, started_at, completed_at, created_at, task_id
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
            'task_id': row[15],
        }

    def get_by_task_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        根据 Celery task_id 获取执行记录

        Args:
            task_id: Celery 任务 ID

        Returns:
            执行记录字典，不存在则返回 None
        """
        query = """
            SELECT
                id, predefined_strategy_type, config_strategy_id, dynamic_strategy_id,
                execution_type, execution_params, status, result, metrics,
                error_message, execution_duration_ms,
                executed_by, started_at, completed_at, created_at, task_id
            FROM strategy_executions
            WHERE task_id = %s
        """

        results = self.execute_query(query, (task_id,))
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
            'task_id': row[15],
        }

    def update_task_id(self, execution_id: int, task_id: str) -> int:
        """
        更新执行记录的 task_id

        Args:
            execution_id: 执行记录 ID
            task_id: Celery 任务 ID

        Returns:
            受影响的行数
        """
        query = """
            UPDATE strategy_executions
            SET task_id = %s
            WHERE id = %s
        """
        return self.execute_update(query, (task_id, execution_id))

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

    def list_by_user_with_pagination(
        self,
        username: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        strategy_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        分页查询用户的回测历史记录（带策略关联）

        Args:
            username: 用户名
            page: 页码（从1开始）
            page_size: 每页数量
            status_filter: 状态筛选（可选）
            strategy_id: 策略ID筛选（可选）

        Returns:
            包含 total, items 的字典

        Examples:
            >>> repo = StrategyExecutionRepository()
            >>> result = repo.list_by_user_with_pagination('admin', page=1, page_size=20)
            >>> print(f"总数: {result['total']}, 记录数: {len(result['items'])}")
        """
        # 构建查询条件
        conditions = ["se.executed_by = %s"]
        params = [username]

        if status_filter:
            conditions.append("se.status = %s")
            params.append(status_filter)

        if strategy_id:
            conditions.append("CAST(se.execution_params->>'strategy_id' AS INT) = %s")
            params.append(strategy_id)

        where_clause = " AND ".join(conditions)

        # 查询总数
        count_query = f"""
            SELECT COUNT(*)
            FROM strategy_executions se
            WHERE {where_clause}
        """
        count_result = self.execute_query(count_query, tuple(params))
        total = count_result[0][0] if count_result else 0

        # 查询数据（带策略关联）
        offset = (page - 1) * page_size
        data_params = params + [page_size, offset]

        query = f"""
            SELECT
                se.id,
                se.execution_type,
                se.status,
                se.metrics,
                se.execution_params,
                se.error_message,
                se.execution_duration_ms,
                se.started_at,
                se.completed_at,
                se.created_at,
                s.id as strategy_id,
                s.name as strategy_name,
                s.display_name as strategy_display_name,
                s.source_type as strategy_source_type
            FROM strategy_executions se
            LEFT JOIN strategies s ON (
                s.id = CAST(se.execution_params->>'strategy_id' AS INT)
            )
            WHERE {where_clause}
            ORDER BY se.created_at DESC
            LIMIT %s OFFSET %s
        """

        results = self.execute_query(query, tuple(data_params))

        items = []
        for row in results:
            items.append({
                'id': row[0],
                'execution_type': row[1],
                'status': row[2],
                'metrics': row[3],
                'execution_params': row[4],
                'error_message': row[5],
                'execution_duration_ms': row[6],
                'started_at': row[7].isoformat() if row[7] else None,
                'completed_at': row[8].isoformat() if row[8] else None,
                'created_at': row[9].isoformat() if row[9] else None,
                'strategy': {
                    'id': row[10],
                    'name': row[11],
                    'display_name': row[12],
                    'source_type': row[13],
                } if row[10] else None,
            })

        return {
            'total': total,
            'items': items
        }

    def get_by_id_with_strategy(self, execution_id: int) -> Optional[Dict[str, Any]]:
        """
        根据 ID 获取执行记录（带策略详情）

        Args:
            execution_id: 执行记录 ID

        Returns:
            执行记录字典（包含策略信息），不存在则返回 None

        Examples:
            >>> repo = StrategyExecutionRepository()
            >>> detail = repo.get_by_id_with_strategy(123)
            >>> if detail:
            >>>     print(f"策略: {detail['strategy']['display_name']}")
        """
        query = """
            SELECT
                se.id,
                se.execution_type,
                se.status,
                se.metrics,
                se.execution_params,
                se.result,
                se.error_message,
                se.execution_duration_ms,
                se.started_at,
                se.completed_at,
                se.created_at,
                se.executed_by,
                s.id as strategy_id,
                s.name as strategy_name,
                s.display_name as strategy_display_name,
                s.source_type as strategy_source_type,
                s.code as strategy_code
            FROM strategy_executions se
            LEFT JOIN strategies s ON (
                s.id = CAST(se.execution_params->>'strategy_id' AS INT)
            )
            WHERE se.id = %s
        """

        results = self.execute_query(query, (execution_id,))
        if not results:
            return None

        row = results[0]
        return {
            'id': row[0],
            'execution_type': row[1],
            'status': row[2],
            'metrics': row[3],
            'execution_params': row[4],
            'result': row[5],
            'error_message': row[6],
            'execution_duration_ms': row[7],
            'started_at': row[8].isoformat() if row[8] else None,
            'completed_at': row[9].isoformat() if row[9] else None,
            'created_at': row[10].isoformat() if row[10] else None,
            'executed_by': row[11],
            'strategy': {
                'id': row[12],
                'name': row[13],
                'display_name': row[14],
                'source_type': row[15],
                'code': row[16],
            } if row[12] else None,
        }

    def delete_by_id(self, execution_id: int) -> int:
        """
        根据 ID 删除执行记录

        Args:
            execution_id: 执行记录 ID

        Returns:
            受影响的行数

        Examples:
            >>> repo = StrategyExecutionRepository()
            >>> deleted = repo.delete_by_id(123)
            >>> print(f"已删除 {deleted} 条记录")
        """
        query = "DELETE FROM strategy_executions WHERE id = %s"
        return self.execute_update(query, (execution_id,))
