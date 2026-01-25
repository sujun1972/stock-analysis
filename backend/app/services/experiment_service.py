"""
实验管理服务（重构版）
使用 BatchManager 和 ExperimentRunner 提供统一接口
"""

from typing import List, Dict, Any, Optional
from loguru import logger

from src.database.db_manager import DatabaseManager
from app.services.batch_manager import BatchManager
from app.services.experiment_runner import ExperimentRunner
from app.services.model_ranker import ModelRanker
from app.repositories.experiment_repository import ExperimentRepository


class ExperimentService:
    """
    实验管理服务（Facade模式）

    将批次管理和实验执行功能委托给专门的服务类，
    提供统一的接口供API层调用。
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
                """
        初始化服务

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        # 委托给专门的服务
        self.batch_manager = BatchManager(db)
        self.experiment_runner = ExperimentRunner(db)
        self.experiment_repo = ExperimentRepository(db)

    # ==================== 批次管理接口 ====================

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
            strategy: 参数生成策略
            max_experiments: 最大实验数
            description: 批次描述

        Returns:
            batch_id: 批次ID
        """
        return await self.batch_manager.create_batch(
            batch_name=batch_name,
            param_space=param_space,
            strategy=strategy,
            max_experiments=max_experiments,
            description=description
        )

    async def run_batch(
        self,
        batch_id: int,
        max_workers: Optional[int] = None,
        auto_backtest: bool = True
    ):
        """
        运行批次实验

        Args:
            batch_id: 批次ID
            max_workers: 最大并行Worker数
            auto_backtest: 是否自动回测
        """
        await self.experiment_runner.run_batch(
            batch_id=batch_id,
            max_workers=max_workers,
            auto_backtest=auto_backtest
        )

    async def get_batch_info(self, batch_id: int) -> Optional[Dict]:
        """
        获取批次详细信息

        Args:
            batch_id: 批次ID

        Returns:
            批次信息字典
        """
        return await self.batch_manager.get_batch_info(batch_id)

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
        return await self.batch_manager.list_batches(
            limit=limit,
            status=status
        )

    # ==================== 实验查询接口 ====================

    async def get_batch_experiments(
        self,
        batch_id: int,
        status: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict]:
        """
        获取批次下的实验列表

        Args:
            batch_id: 批次ID
            status: 状态过滤
            limit: 限制数量

        Returns:
            实验列表
        """
        import asyncio
        return await asyncio.to_thread(
            self.experiment_repo.find_experiments_by_batch,
            batch_id=batch_id,
            status=status,
            limit=limit
        )

    async def get_top_models(
        self,
        batch_id: int,
        top_n: int = 10,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        min_annual_return: Optional[float] = None,
        min_win_rate: Optional[float] = None,
        min_ic: Optional[float] = None
    ) -> List[Dict]:
        """
        获取Top模型

        Args:
            batch_id: 批次ID
            top_n: 返回数量
            min_sharpe: 最小夏普比率
            max_drawdown: 最大回撤
            min_annual_return: 最小年化收益
            min_win_rate: 最小胜率
            min_ic: 最小IC

        Returns:
            Top模型列表
        """
        ranker = ModelRanker()
        return ranker.filter_models(
            batch_id=batch_id,
            min_sharpe=min_sharpe,
            max_drawdown=max_drawdown,
            min_annual_return=min_annual_return,
            min_win_rate=min_win_rate,
            min_ic=min_ic,
            top_n=top_n
        )
