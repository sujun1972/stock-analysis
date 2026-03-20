"""
批次管理器
负责实验批次的创建、查询和状态管理
"""

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

from app.core.exceptions import DatabaseError
from app.repositories.batch_repository import BatchRepository
from app.repositories.experiment_repository import ExperimentRepository
from app.services.parameter_grid import ParameterGrid


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
        """
        初始化批次管理器
        """
        self.batch_repo = BatchRepository()
        self.experiment_repo = ExperimentRepository()

    async def create_batch(
        self,
        batch_name: str,
        param_space: Dict[str, Any],
        strategy: str = "grid",
        max_experiments: Optional[int] = None,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
    ) -> int:
        """
        创建实验批次

        Args:
            batch_name: 批次名称
            param_space: 参数空间定义
            strategy: 参数生成策略 ('grid', 'random', 'bayesian')
            max_experiments: 最大实验数
            description: 批次描述
            config: 批次配置（如 max_workers, auto_backtest 等）
            tags: 标签列表

        Returns:
            batch_id: 批次ID
        """
        logger.info(f"创建批次: {batch_name}, 策略: {strategy}")

        # 生成参数组合
        grid = ParameterGrid(param_space)
        configs = grid.generate(strategy=strategy, max_experiments=max_experiments)

        total_experiments = len(configs)
        logger.info(f"生成了 {total_experiments} 个实验配置")

        # 创建批次记录
        batch_id = await self._create_batch_record(
            batch_name=batch_name,
            strategy=strategy,
            param_space=param_space,
            total_experiments=total_experiments,
            description=description,
            config=config,
            tags=tags,
        )

        # 创建实验记录
        await self._create_experiments(batch_id, configs)

        logger.info(f"✓ 批次创建完成: batch_id={batch_id}, experiments={total_experiments}")

        return batch_id

    async def _create_batch_record(
        self,
        batch_name: str,
        strategy: str,
        param_space: Dict[str, Any],
        total_experiments: int,
        description: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
    ) -> int:
        """
        创建批次记录（使用 Repository）

        Args:
            batch_name: 批次名称
            strategy: 策略
            param_space: 参数空间定义
            total_experiments: 总实验数
            description: 描述
            config: 批次配置
            tags: 标签列表

        Returns:
            batch_id: 批次ID（对应 experiment_batches.id）
        """
        # 使用 BatchRepository 创建批次
        batch_id = await asyncio.to_thread(
            self.batch_repo.create_batch,
            batch_name=batch_name,
            strategy=strategy,
            param_space=param_space,
            total_experiments=total_experiments,
            description=description,
            config=config,
            tags=tags,
        )

        return batch_id

    async def _create_experiments(self, batch_id: int, configs: List[Dict]):
        """
        创建实验记录（使用 Repository）

        Args:
            batch_id: 批次ID
            configs: 实验配置列表
        """
        logger.info(f"创建 {len(configs)} 个实验记录...")

        # 准备实验数据
        experiments = []
        for config in configs:
            experiment_name = self._generate_experiment_name(config)
            experiment_hash = config.get("experiment_hash", "")

            experiments.append({
                'name': experiment_name,
                'hash': experiment_hash,
                'config': config,
            })

        # 使用 ExperimentRepository 批量创建实验
        count = await asyncio.to_thread(
            self.experiment_repo.bulk_create_experiments,
            batch_id,
            experiments
        )

        logger.info(f"✓ 创建了 {count} 个实验记录")

    def _generate_experiment_name(self, config: Dict) -> str:
        """生成实验名称"""
        symbol = config.get("symbol", "UNKNOWN")
        model_type = config.get("model_type", "UNKNOWN")
        target_period = config.get("target_period", 0)
        return f"{symbol}_{model_type}_T{target_period}"

    async def update_batch_status(self, batch_id: int, status: str, **kwargs):
        """
        更新批次状态

        Args:
            batch_id: 批次ID
            status: 新状态
            **kwargs: 其他要更新的字段
        """
        await asyncio.to_thread(self.batch_repo.update_batch_status, batch_id, status, **kwargs)

    async def increment_batch_counter(self, batch_id: int, counter_type: str):
        """
        增加批次计数器（使用 Repository）

        Args:
            batch_id: 批次ID
            counter_type: 计数器类型 ('completed', 'failed', 'running')
        """
        # 使用 BatchRepository 增加计数器
        await asyncio.to_thread(
            self.batch_repo.increment_batch_counter,
            batch_id,
            counter_type
        )

    async def get_batch_info(self, batch_id: int) -> Optional[Dict]:
        """
        获取批次详细信息

        Args:
            batch_id: 批次ID

        Returns:
            批次信息字典
        """
        return await asyncio.to_thread(self.batch_repo.get_batch_by_id, batch_id)

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

        return {"strategy": result[0][0]}

    async def list_batches(self, limit: int = 100, status: Optional[str] = None) -> List[Dict]:
        """
        列出批次

        Args:
            limit: 限制数量
            status: 状态过滤

        Returns:
            批次列表
        """
        return await asyncio.to_thread(
            self.batch_repo.find_batches_with_stats, status=status, limit=limit, offset=0
        )

    async def calculate_rankings(self, batch_id: int):
        """
        计算实验排名（使用 Repository）

        Args:
            batch_id: 批次ID
        """
        logger.info(f"计算批次 {batch_id} 的排名...")

        # 使用 ExperimentRepository 获取已完成的实验
        experiments = await asyncio.to_thread(
            self.experiment_repo.get_completed_experiments_for_ranking,
            batch_id
        )

        if not experiments:
            logger.warning(f"批次 {batch_id} 没有完成的实验")
            return

        # 计算综合排名分数
        scored_experiments = []
        for exp in experiments:
            exp_id = exp['id']
            metrics = exp['backtest_metrics']

            # 计算排名分数（根据你的评分逻辑）
            rank_score = self._calculate_rank_score(metrics)
            scored_experiments.append((exp_id, rank_score))

        # 按分数排序
        scored_experiments.sort(key=lambda x: x[1], reverse=True)

        # 使用 ExperimentRepository 批量更新排名
        for position, (exp_id, score) in enumerate(scored_experiments, 1):
            await asyncio.to_thread(
                self.experiment_repo.update_rank,
                exp_id,
                score,
                position
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
        sharpe_ratio = metrics.get("sharpe_ratio", 0)
        annual_return = metrics.get("annual_return", 0)
        max_drawdown = metrics.get("max_drawdown", 0)
        win_rate = metrics.get("win_rate", 0)

        # 综合评分（可以根据需要调整权重）
        score = (
            sharpe_ratio * 0.4
            + annual_return * 0.3
            + (1 - abs(max_drawdown)) * 0.2
            + win_rate * 0.1
        )

        return score
