"""
实验管理服务接口定义
使用 Protocol 提供结构化类型约束
"""

from typing import Protocol, Dict, List, Any, Optional


class IBatchManager(Protocol):
    """
    批次管理器接口

    定义实验批次管理的标准契约
    """

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
            int: 批次ID
        """
        ...

    async def get_batch_info(self, batch_id: int) -> Optional[Dict]:
        """获取批次详细信息"""
        ...

    async def list_batches(
        self,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict]:
        """列出批次"""
        ...


class IExperimentRunner(Protocol):
    """
    实验运行器接口

    定义实验执行逻辑的标准契约
    """

    async def run_batch(
        self,
        batch_id: int,
        max_workers: Optional[int] = None,
        auto_backtest: bool = True
    ) -> None:
        """
        运行批次实验

        Args:
            batch_id: 批次ID
            max_workers: 最大并行Worker数
            auto_backtest: 是否自动回测
        """
        ...


class IExperimentService(Protocol):
    """
    实验管理服务接口（Facade）

    定义实验管理服务的统一接口契约
    """

    # ==================== 批次管理接口 ====================

    async def create_batch(
        self,
        batch_name: str,
        param_space: Dict[str, Any],
        strategy: str = 'grid',
        max_experiments: Optional[int] = None,
        description: Optional[str] = None
    ) -> int:
        """创建实验批次"""
        ...

    async def run_batch(
        self,
        batch_id: int,
        max_workers: Optional[int] = None,
        auto_backtest: bool = True
    ) -> None:
        """运行批次实验"""
        ...

    async def get_batch_info(self, batch_id: int) -> Optional[Dict]:
        """获取批次详细信息"""
        ...

    async def list_batches(
        self,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict]:
        """列出批次"""
        ...

    # ==================== 实验查询接口 ====================

    async def get_batch_experiments(
        self,
        batch_id: int,
        status: Optional[str] = None,
        limit: int = 500
    ) -> List[Dict]:
        """获取批次下的实验列表"""
        ...

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
        """获取Top模型"""
        ...
