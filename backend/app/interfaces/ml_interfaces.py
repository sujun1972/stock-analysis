"""
机器学习训练服务接口定义
使用 Protocol 提供结构化类型约束
"""

from typing import Protocol, Dict, List, Any, Optional


class ITrainingTaskManager(Protocol):
    """
    训练任务管理器接口

    定义训练任务的生命周期管理契约
    """

    async def create_task(self, config: Dict[str, Any]) -> str:
        """
        创建训练任务

        Args:
            config: 训练配置

        Returns:
            str: 任务ID
        """
        ...

    async def run_training(self, task_id: str) -> None:
        """
        执行训练任务

        Args:
            task_id: 任务ID
        """
        ...

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            Optional[Dict]: 任务信息
        """
        ...

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        列出任务

        Args:
            status: 状态过滤
            limit: 限制数量
            offset: 偏移量

        Returns:
            Dict: 任务列表和总数
        """
        ...

    def cancel_task(self, task_id: str) -> None:
        """取消任务"""
        ...

    def delete_task(self, task_id: str) -> None:
        """删除任务"""
        ...


class IModelPredictor(Protocol):
    """
    模型预测服务接口

    定义模型预测功能的标准契约
    """

    async def predict(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        model_source: Optional[Any] = None,
        task_id: Optional[str] = None,
        experiment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        统一的预测接口

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            model_source: 模型来源
            task_id: 任务ID
            experiment_id: 实验ID

        Returns:
            Dict: 预测结果
        """
        ...

    async def batch_predict(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        model_source: Optional[Any] = None,
        task_id: Optional[str] = None,
        experiment_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        批量预测

        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            model_source: 模型来源
            task_id: 任务ID
            experiment_id: 实验ID

        Returns:
            Dict: 批量预测结果
        """
        ...


class IMLTrainingService(Protocol):
    """
    机器学习训练服务接口（Facade）

    定义ML训练服务的统一接口契约
    """

    # ==================== 任务管理接口 ====================

    async def create_task(self, config: Dict[str, Any]) -> str:
        """创建训练任务"""
        ...

    async def run_training(self, task_id: str) -> None:
        """执行训练任务"""
        ...

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        ...

    def list_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """列出任务"""
        ...

    def cancel_task(self, task_id: str) -> None:
        """取消任务"""
        ...

    def delete_task(self, task_id: str) -> None:
        """删除任务"""
        ...

    # ==================== 预测接口 ====================

    async def predict(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        model_id: Optional[str] = None,
        experiment_id: Optional[int] = None,
        model_source: Optional[Any] = None
    ) -> Dict[str, Any]:
        """统一的预测接口"""
        ...

    async def batch_predict(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        experiment_id: Optional[int] = None,
        model_id: Optional[str] = None,
        model_source: Optional[Any] = None
    ) -> Dict[str, Any]:
        """批量预测"""
        ...
