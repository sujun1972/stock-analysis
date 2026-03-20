"""
Experiment Repository
管理实验的数据访问
"""

from typing import Any, Dict, List, Optional


from .base_repository import BaseRepository


class ExperimentRepository(BaseRepository):
    """实验数据访问层"""

    def find_experiments_by_batch(
        self, batch_id: int, status: Optional[str] = None, limit: int = 100
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
            experiments.append(
                {
                    "id": row[0],
                    "experiment_name": row[1],
                    "model_id": row[2],
                    "config": row[3],
                    "train_metrics": row[4],
                    "backtest_metrics": row[5],
                    "rank_score": float(row[6]) if row[6] else None,
                    "rank_position": row[7],
                    "status": row[8],
                    "error_message": row[9],
                }
            )

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
                created_at, train_started_at, train_completed_at,
                backtest_started_at, backtest_completed_at
            FROM experiments
            WHERE id = %s
        """

        results = self.execute_query(query, (experiment_id,))
        if not results:
            return None

        row = results[0]
        return {
            "id": row[0],
            "batch_id": row[1],
            "experiment_name": row[2],
            "model_id": row[3],
            "model_path": row[4],
            "config": row[5],
            "train_metrics": row[6],
            "backtest_metrics": row[7],
            "rank_score": float(row[8]) if row[8] else None,
            "rank_position": row[9],
            "status": row[10],
            "error_message": row[11],
            "created_at": row[12].isoformat() if row[12] else None,
            "train_started_at": row[13].isoformat() if row[13] else None,
            "train_completed_at": row[14].isoformat() if row[14] else None,
            "backtest_started_at": row[15].isoformat() if row[15] else None,
            "backtest_completed_at": row[16].isoformat() if row[16] else None,
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
        self, experiment_id: int, status: str, error_message: Optional[str] = None, **kwargs
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

        stats = {"pending": 0, "running": 0, "completed": 0, "failed": 0}

        for row in results:
            status = row[0]
            count = row[1]
            if status in stats:
                stats[status] = count

        return stats

    def get_top_experiments(
        self, batch_id: int, top_n: int = 10, min_rank_score: Optional[float] = None
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
            experiments.append(
                {
                    "id": row[0],
                    "experiment_name": row[1],
                    "model_id": row[2],
                    "config": row[3],
                    "train_metrics": row[4],
                    "backtest_metrics": row[5],
                    "rank_score": float(row[6]) if row[6] else None,
                    "rank_position": row[7],
                }
            )

        return experiments

    def update_train_result(
        self,
        experiment_id: int,
        model_id: str,
        train_metrics: Dict[str, Any],
        feature_importance: Dict[str, Any],
        model_path: str,
        train_completed_at,
        train_duration_seconds: int,
    ) -> int:
        """
        更新实验的训练结果

        Args:
            experiment_id: 实验 ID
            model_id: 模型 ID
            train_metrics: 训练指标（字典）
            feature_importance: 特征重要性（字典）
            model_path: 模型文件路径
            train_completed_at: 训练完成时间
            train_duration_seconds: 训练耗时（秒）

        Returns:
            受影响的行数

        Examples:
            >>> repo = ExperimentRepository()
            >>> repo.update_train_result(
            ...     123, 'model_001', {'accuracy': 0.85}, {'f1': 0.9},
            ...     '/path/to/model', datetime.now(), 3600
            ... )
        """
        import json

        query = """
            UPDATE experiments
            SET model_id = %s,
                train_metrics = %s,
                feature_importance = %s,
                model_path = %s,
                train_completed_at = %s,
                train_duration_seconds = %s
            WHERE id = %s
        """
        params = (
            model_id,
            json.dumps(train_metrics) if train_metrics else None,
            json.dumps(feature_importance) if feature_importance else None,
            str(model_path),
            train_completed_at,
            train_duration_seconds,
            experiment_id,
        )

        return self.execute_update(query, params)

    def update_backtest_result(
        self,
        experiment_id: int,
        backtest_metrics: Dict[str, Any],
        backtest_completed_at,
        backtest_duration_seconds: int,
    ) -> int:
        """
        更新实验的回测结果

        Args:
            experiment_id: 实验 ID
            backtest_metrics: 回测指标（字典）
            backtest_completed_at: 回测完成时间
            backtest_duration_seconds: 回测耗时（秒）

        Returns:
            受影响的行数

        Examples:
            >>> repo = ExperimentRepository()
            >>> repo.update_backtest_result(
            ...     123, {'sharpe': 1.5, 'returns': 0.25},
            ...     datetime.now(), 600
            ... )
        """
        import json

        query = """
            UPDATE experiments
            SET backtest_status = 'completed',
                backtest_metrics = %s,
                backtest_completed_at = %s,
                backtest_duration_seconds = %s
            WHERE id = %s
        """
        params = (
            json.dumps(backtest_metrics) if backtest_metrics else None,
            backtest_completed_at,
            backtest_duration_seconds,
            experiment_id,
        )

        return self.execute_update(query, params)

    def filter_experiments_by_metrics(
        self,
        batch_id: int,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        min_annual_return: Optional[float] = None,
        min_win_rate: Optional[float] = None,
        min_ic: Optional[float] = None,
        top_n: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据指标筛选实验

        Args:
            batch_id: 批次 ID
            min_sharpe: 最低夏普比率
            max_drawdown: 最大回撤阈值
            min_annual_return: 最低年化收益率
            min_win_rate: 最低胜率
            min_ic: 最低IC值
            top_n: 返回前N个

        Returns:
            符合条件的实验列表

        Examples:
            >>> repo = ExperimentRepository()
            >>> models = repo.filter_experiments_by_metrics(
            ...     batch_id=1, min_sharpe=1.5, top_n=10
            ... )
        """
        conditions = ["batch_id = %s", "status = 'completed'", "backtest_status = 'completed'"]
        params = [batch_id]

        if min_sharpe is not None:
            conditions.append("(backtest_metrics->>'sharpe_ratio')::FLOAT >= %s")
            params.append(min_sharpe)

        if max_drawdown is not None:
            conditions.append("(backtest_metrics->>'max_drawdown')::FLOAT >= %s")
            params.append(max_drawdown)

        if min_annual_return is not None:
            conditions.append("(backtest_metrics->>'annual_return')::FLOAT >= %s")
            params.append(min_annual_return)

        if min_win_rate is not None:
            conditions.append("(backtest_metrics->>'win_rate')::FLOAT >= %s")
            params.append(min_win_rate)

        if min_ic is not None:
            conditions.append("(train_metrics->>'ic')::FLOAT >= %s")
            params.append(min_ic)

        query = f"""
            SELECT
                id, experiment_name, model_id, config,
                train_metrics, backtest_metrics, rank_score, rank_position
            FROM experiments
            WHERE {' AND '.join(conditions)}
            ORDER BY rank_score DESC NULLS LAST
        """

        if top_n:
            query += f" LIMIT {top_n}"

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
            })

        return experiments

    def get_experiments_with_rank_scores(self, batch_id: int) -> List[Dict[str, Any]]:
        """
        获取批次下有评分的实验

        Args:
            batch_id: 批次 ID

        Returns:
            实验列表（包含 config 和 rank_score）

        Examples:
            >>> repo = ExperimentRepository()
            >>> exps = repo.get_experiments_with_rank_scores(1)
        """
        query = """
            SELECT config, rank_score
            FROM experiments
            WHERE batch_id = %s AND status = 'completed' AND rank_score IS NOT NULL
        """

        results = self.execute_query(query, (batch_id,))

        experiments = []
        for row in results:
            experiments.append({'config': row[0], 'rank_score': float(row[1])})

        return experiments

    def get_performance_statistics(self, batch_id: int) -> Dict[str, Any]:
        """
        获取批次的性能统计

        Args:
            batch_id: 批次 ID

        Returns:
            性能统计字典

        Examples:
            >>> repo = ExperimentRepository()
            >>> stats = repo.get_performance_statistics(1)
            >>> print(f"平均年化收益: {stats['avg_annual_return']}")
        """
        query = """
            SELECT
                COUNT(*) as total,
                AVG((backtest_metrics->>'annual_return')::FLOAT) as avg_return,
                STDDEV((backtest_metrics->>'annual_return')::FLOAT) as std_return,
                AVG((backtest_metrics->>'sharpe_ratio')::FLOAT) as avg_sharpe,
                AVG((backtest_metrics->>'max_drawdown')::FLOAT) as avg_drawdown,
                AVG((train_metrics->>'ic')::FLOAT) as avg_ic
            FROM experiments
            WHERE batch_id = %s AND status = 'completed' AND backtest_status = 'completed'
        """

        result = self.execute_query(query, (batch_id,))

        if result and result[0][0]:
            row = result[0]
            return {
                'total_models': row[0],
                'avg_annual_return': round(float(row[1]), 2) if row[1] else None,
                'std_annual_return': round(float(row[2]), 2) if row[2] else None,
                'avg_sharpe_ratio': round(float(row[3]), 2) if row[3] else None,
                'avg_max_drawdown': round(float(row[4]), 2) if row[4] else None,
                'avg_ic': round(float(row[5]), 4) if row[5] else None,
            }

        return {}

    def get_best_configurations_by_model_type(self, batch_id: int) -> List[Dict[str, Any]]:
        """
        按模型类型分组获取最佳配置

        Args:
            batch_id: 批次 ID

        Returns:
            最佳模型类型列表

        Examples:
            >>> repo = ExperimentRepository()
            >>> best = repo.get_best_configurations_by_model_type(1)
        """
        query = """
            SELECT
                config->>'model_type' as model_type,
                AVG(rank_score) as avg_score,
                COUNT(*) as count
            FROM experiments
            WHERE batch_id = %s AND status = 'completed'
            GROUP BY config->>'model_type'
            ORDER BY avg_score DESC
        """

        results = self.execute_query(query, (batch_id,))

        configurations = []
        for row in results:
            configurations.append({
                'model_type': row[0],
                'avg_score': float(row[1]) if row[1] else None,
                'count': row[2],
            })

        return configurations

    def get_best_configurations_by_target_period(
        self, batch_id: int
    ) -> List[Dict[str, Any]]:
        """
        按预测周期分组获取最佳配置

        Args:
            batch_id: 批次 ID

        Returns:
            最佳预测周期列表

        Examples:
            >>> repo = ExperimentRepository()
            >>> best = repo.get_best_configurations_by_target_period(1)
        """
        query = """
            SELECT
                config->>'target_period' as target_period,
                AVG(rank_score) as avg_score,
                COUNT(*) as count
            FROM experiments
            WHERE batch_id = %s AND status = 'completed'
            GROUP BY config->>'target_period'
            ORDER BY avg_score DESC
        """

        results = self.execute_query(query, (batch_id,))

        configurations = []
        for row in results:
            configurations.append({
                'target_period': int(row[0]) if row[0] else None,
                'avg_score': float(row[1]) if row[1] else None,
                'count': row[2],
            })

        return configurations
