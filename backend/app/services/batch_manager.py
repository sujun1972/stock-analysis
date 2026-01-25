"""
批次管理器
负责实验批次的创建、查询和状态管理
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger

from database.db_manager import DatabaseManager
from app.services.parameter_grid import ParameterGrid
from app.repositories.batch_repository import BatchRepository


class BatchManager:
    """
    批次管理器

    职责：
    - 创建和管理实验批次
    - 生成实验参数组合
    - 批次状态查询和更新
    - 批次统计信息
    """

    def __init__(self):
        """初始化批次管理器"""
        self.db = DatabaseManager()
        self.batch_repo = BatchRepository()

    async def create_batch(
        self,
        batch_name: str,
        param_space: Dict[str, Any],
        strategy: str = 'grid',
        max_experiments: Optional[int] = None,
        description: Optional[str] = None
    ) -> int:
        """
        创建实验批次

        Args:
            batch_name: 批次名称
            param_space: 参数空间定义
            strategy: 参数生成策略 ('grid', 'random', 'bayesian')
            max_experiments: 最大实验数
            description: 批次描述

        Returns:
            batch_id: 批次ID
        """
        logger.info(f"创建批次: {batch_name}, 策略: {strategy}")

        # 生成参数组合
        grid = ParameterGrid(param_space)
        configs = grid.generate(
            strategy=strategy,
            max_experiments=max_experiments
        )

        total_experiments = len(configs)
        logger.info(f"生成了 {total_experiments} 个实验配置")

        # 创建批次记录
        batch_id = await self._create_batch_record(
            batch_name=batch_name,
            strategy=strategy,
            total_experiments=total_experiments,
            description=description
        )

        # 创建实验记录
        await self._create_experiments(batch_id, configs)

        logger.info(f"✓ 批次创建完成: batch_id={batch_id}, experiments={total_experiments}")

        return batch_id

    async def _create_batch_record(
        self,
        batch_name: str,
        strategy: str,
        total_experiments: int,
        description: Optional[str] = None
    ) -> int:
        """
        创建批次记录

        Args:
            batch_name: 批次名称
            strategy: 策略
            total_experiments: 总实验数
            description: 描述

        Returns:
            batch_id: 批次ID
        """
        query = """
            INSERT INTO experiment_batches (
                batch_name, strategy, status, total_experiments,
                completed_experiments, failed_experiments, running_experiments,
                created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING batch_id
        """

        params = (
            batch_name,
            strategy,
            'pending',
            total_experiments,
            0,  # completed_experiments
            0,  # failed_experiments
            0,  # running_experiments
            datetime.now()
        )

        result = await asyncio.to_thread(
            self.db._execute_query,
            query,
            params
        )

        return result[0][0]

    async def _create_experiments(self, batch_id: int, configs: List[Dict]):
        """
        创建实验记录

        Args:
            batch_id: 批次ID
            configs: 实验配置列表
        """
        logger.info(f"创建 {len(configs)} 个实验记录...")

        insert_query = """
            INSERT INTO experiments (
                batch_id, experiment_name, experiment_hash, config,
                status, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """

        # 批量插入
        experiments = []
        for config in configs:
            experiment_name = self._generate_experiment_name(config)
            experiment_hash = config.get('experiment_hash', '')

            experiments.append((
                batch_id,
                experiment_name,
                experiment_hash,
                config,
                'pending',
                datetime.now()
            ))

        # 执行批量插入
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.executemany(insert_query, experiments)
            conn.commit()
            cursor.close()
            logger.info(f"✓ 创建了 {len(experiments)} 个实验记录")
        finally:
            self.db.release_connection(conn)

    def _generate_experiment_name(self, config: Dict) -> str:
        """生成实验名称"""
        symbol = config.get('symbol', 'UNKNOWN')
        model_type = config.get('model_type', 'UNKNOWN')
        target_period = config.get('target_period', 0)
        return f"{symbol}_{model_type}_T{target_period}"

    async def update_batch_status(
        self,
        batch_id: int,
        status: str,
        **kwargs
    ):
        """
        更新批次状态

        Args:
            batch_id: 批次ID
            status: 新状态
            **kwargs: 其他要更新的字段
        """
        await asyncio.to_thread(
            self.batch_repo.update_batch_status,
            batch_id,
            status,
            **kwargs
        )

    async def increment_batch_counter(
        self,
        batch_id: int,
        counter_type: str
    ):
        """
        增加批次计数器

        Args:
            batch_id: 批次ID
            counter_type: 计数器类型 ('completed', 'failed', 'running')
        """
        field_map = {
            'completed': 'completed_experiments',
            'failed': 'failed_experiments',
            'running': 'running_experiments'
        }

        field = field_map.get(counter_type)
        if not field:
            raise ValueError(f"未知的计数器类型: {counter_type}")

        query = f"""
            UPDATE experiment_batches
            SET {field} = {field} + 1
            WHERE batch_id = %s
        """

        await asyncio.to_thread(self.db._execute_update, query, (batch_id,))

    async def get_batch_info(self, batch_id: int) -> Optional[Dict]:
        """
        获取批次详细信息

        Args:
            batch_id: 批次ID

        Returns:
            批次信息字典
        """
        return await asyncio.to_thread(
            self.batch_repo.get_batch_by_id,
            batch_id
        )

    async def get_batch_config(self, batch_id: int) -> Dict:
        """
        获取批次配置

        Args:
            batch_id: 批次ID

        Returns:
            批次配置
        """
        query = "SELECT strategy FROM experiment_batches WHERE batch_id = %s"
        result = await asyncio.to_thread(self.db._execute_query, query, (batch_id,))

        if not result:
            raise ValueError(f"批次不存在: {batch_id}")

        return {'strategy': result[0][0]}

    async def list_batches(
        self,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        列出批次

        Args:
            limit: 限制数量
            status: 状态过滤

        Returns:
            批次列表
        """
        return await asyncio.to_thread(
            self.batch_repo.find_batches_with_stats,
            status=status,
            limit=limit,
            offset=0
        )

    async def calculate_rankings(self, batch_id: int):
        """
        计算实验排名

        Args:
            batch_id: 批次ID
        """
        logger.info(f"计算批次 {batch_id} 的排名...")

        # 查询所有完成的实验
        query = """
            SELECT id, backtest_metrics
            FROM experiments
            WHERE batch_id = %s
              AND status = 'completed'
              AND backtest_status = 'completed'
              AND backtest_metrics IS NOT NULL
        """

        results = await asyncio.to_thread(self.db._execute_query, query, (batch_id,))

        if not results:
            logger.warning(f"批次 {batch_id} 没有完成的实验")
            return

        # 计算综合排名分数
        scored_experiments = []
        for row in results:
            exp_id, metrics = row[0], row[1]

            # 计算排名分数（根据你的评分逻辑）
            rank_score = self._calculate_rank_score(metrics)
            scored_experiments.append((exp_id, rank_score))

        # 按分数排序
        scored_experiments.sort(key=lambda x: x[1], reverse=True)

        # 更新排名
        for position, (exp_id, score) in enumerate(scored_experiments, 1):
            update_query = """
                UPDATE experiments
                SET rank_score = %s, rank_position = %s
                WHERE id = %s
            """
            await asyncio.to_thread(
                self.db._execute_update,
                update_query,
                (score, position, exp_id)
            )

        logger.info(f"✓ 完成排名计算: {len(scored_experiments)} 个实验")

    def _calculate_rank_score(self, metrics: Dict) -> float:
        """
        计算排名分数

        Args:
            metrics: 回测指标

        Returns:
            排名分数
        """
        if not metrics:
            return 0.0

        # 提取关键指标
        sharpe_ratio = metrics.get('sharpe_ratio', 0)
        annual_return = metrics.get('annual_return', 0)
        max_drawdown = metrics.get('max_drawdown', 0)
        win_rate = metrics.get('win_rate', 0)

        # 综合评分（可以根据需要调整权重）
        score = (
            sharpe_ratio * 0.4 +
            annual_return * 0.3 +
            (1 - abs(max_drawdown)) * 0.2 +
            win_rate * 0.1
        )

        return score
