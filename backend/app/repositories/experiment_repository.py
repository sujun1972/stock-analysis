"""
Experiment Repository
管理实验的数据访问
"""

from typing import List, Dict, Optional, Any
from .base_repository import BaseRepository
from loguru import logger


class ExperimentRepository(BaseRepository):
    """实验数据访问层"""

    def find_experiments_by_batch(
        self,
        batch_id: int,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询批次下的实验列表

        Args:
            batch_id: 批次 ID
            status: 实验状态过滤
            limit: 限制数量

        Returns:
            实验列表
        """
        conditions = ["batch_id = %s"]
        params = [batch_id]

        if status:
            conditions.append("status = %s")
            params.append(status)

        query = f"""
            SELECT id, experiment_name, model_id, config, train_metrics, backtest_metrics,
                   rank_score, rank_position, status, error_message
            FROM experiments
            WHERE {' AND '.join(conditions)}
            ORDER BY rank_score DESC NULLS LAST
            LIMIT %s
        """
        params.append(limit)

        results = self.execute_query(query, tuple(params))

        experiments = []
        for row in results:
            experiments.append({
                'id': row[0],
                'experiment_name': row[1],
                'model_id': row[2],
                'config': row[3],
                'train_metrics': row[4],
                'backtest_metrics': row[5],
                'rank_score': float(row[6]) if row[6] else None,
                'rank_position': row[7],
                'status': row[8],
                'error_message': row[9]
            })

        return experiments

    def get_experiment_detail(self, experiment_id: int) -> Optional[Dict[str, Any]]:
        """
        获取实验详情

        Args:
            experiment_id: 实验 ID

        Returns:
            实验详情字典
        """
        query = """
            SELECT
                id, batch_id, experiment_name, model_id, model_path,
                config, train_metrics, backtest_metrics,
                rank_score, rank_position, status, error_message,
                created_at, started_at, completed_at
            FROM experiments
            WHERE id = %s
        """

        results = self.execute_query(query, (experiment_id,))
        if not results:
            return None

        row = results[0]
        return {
            'id': row[0],
            'batch_id': row[1],
            'experiment_name': row[2],
            'model_id': row[3],
            'model_path': row[4],
            'config': row[5],
            'train_metrics': row[6],
            'backtest_metrics': row[7],
            'rank_score': float(row[8]) if row[8] else None,
            'rank_position': row[9],
            'status': row[10],
            'error_message': row[11],
            'created_at': row[12].isoformat() if row[12] else None,
            'started_at': row[13].isoformat() if row[13] else None,
            'completed_at': row[14].isoformat() if row[14] else None
        }

    def delete_experiment(self, experiment_id: int) -> int:
        """
        删除实验

        Args:
            experiment_id: 实验 ID

        Returns:
            删除的行数
        """
        query = "DELETE FROM experiments WHERE id = %s"
        return self.execute_update(query, (experiment_id,))

    def update_experiment_status(
        self,
        experiment_id: int,
        status: str,
        error_message: Optional[str] = None,
        **kwargs
    ) -> int:
        """
        更新实验状态

        Args:
            experiment_id: 实验 ID
            status: 新状态
            error_message: 错误消息
            **kwargs: 其他要更新的字段

        Returns:
            受影响的行数
        """
        set_clauses = ["status = %s"]
        params = [status]

        if error_message is not None:
            set_clauses.append("error_message = %s")
            params.append(error_message)

        for field, value in kwargs.items():
            set_clauses.append(f"{field} = %s")
            params.append(value)

        params.append(experiment_id)

        query = f"""
            UPDATE experiments
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """

        return self.execute_update(query, tuple(params))

    def count_experiments_by_status(self, batch_id: int) -> Dict[str, int]:
        """
        统计批次下各状态的实验数量

        Args:
            batch_id: 批次 ID

        Returns:
            状态统计字典
        """
        query = """
            SELECT status, COUNT(*) as count
            FROM experiments
            WHERE batch_id = %s
            GROUP BY status
        """

        results = self.execute_query(query, (batch_id,))

        stats = {
            'pending': 0,
            'running': 0,
            'completed': 0,
            'failed': 0
        }

        for row in results:
            status = row[0]
            count = row[1]
            if status in stats:
                stats[status] = count

        return stats

    def get_top_experiments(
        self,
        batch_id: int,
        top_n: int = 10,
        min_rank_score: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        获取排名靠前的实验

        Args:
            batch_id: 批次 ID
            top_n: 返回数量
            min_rank_score: 最小排名分数

        Returns:
            实验列表
        """
        conditions = ["batch_id = %s", "status = 'completed'"]
        params = [batch_id]

        if min_rank_score is not None:
            conditions.append("rank_score >= %s")
            params.append(min_rank_score)

        query = f"""
            SELECT
                id, experiment_name, model_id, config,
                train_metrics, backtest_metrics,
                rank_score, rank_position
            FROM experiments
            WHERE {' AND '.join(conditions)}
            ORDER BY rank_score DESC
            LIMIT %s
        """
        params.append(top_n)

        results = self.execute_query(query, tuple(params))

        experiments = []
        for row in results:
            experiments.append({
                'id': row[0],
                'experiment_name': row[1],
                'model_id': row[2],
                'config': row[3],
                'train_metrics': row[4],
                'backtest_metrics': row[5],
                'rank_score': float(row[6]) if row[6] else None,
                'rank_position': row[7]
            })

        return experiments
