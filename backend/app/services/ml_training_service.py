"""
机器学习训练服务（重构版）
使用 TrainingTaskManager 和 ModelPredictor 提供统一接口
"""

from typing import Dict, Any, Optional
from pathlib import Path

from app.services.training_task_manager import TrainingTaskManager
from app.services.model_predictor import ModelPredictor


class MLTrainingService:
    """
    机器学习训练服务（Facade模式）

    将训练任务管理和模型预测功能委托给专门的服务类，
    提供统一的接口供API层调用。
    """

    def __init__(self, models_dir: Optional[Path] = None):
        """
        初始化服务

        Args:
            models_dir: 模型存储目录
        """
        # 委托给专门的服务
        self.task_manager = TrainingTaskManager(models_dir)
        self.predictor = ModelPredictor()

    # ==================== 任务管理接口 ====================

    async def create_task(self, config: Dict[str, Any]) -> str:
        """
        创建训练任务

        Args:
            config: 训练配置

        Returns:
            task_id: 任务ID
        """
        return await self.task_manager.create_task(config)

    async def run_training(self, task_id: str):
        """
        执行训练任务

        Args:
            task_id: 任务ID
        """
        await self.task_manager.run_training(task_id)

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            任务信息
        """
        return self.task_manager.get_task(task_id)

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
            任务列表和总数
        """
        return self.task_manager.list_tasks(status, limit, offset)

    def cancel_task(self, task_id: str):
        """
        取消任务

        Args:
            task_id: 任务ID
        """
        self.task_manager.cancel_task(task_id)

    def delete_task(self, task_id: str):
        """
        删除任务

        Args:
            task_id: 任务ID
        """
        self.task_manager.delete_task(task_id)

    # ==================== 预测接口 ====================

    async def predict(
        self,
        model_id: str,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        使用训练好的模型进行预测

        Args:
            model_id: 模型ID（即task_id）
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            预测结果
        """
        # 获取任务信息
        task = self.get_task(model_id)
        if not task or task['status'] != 'completed':
            raise ValueError(f"模型不存在或未完成训练: {model_id}")

        # 使用预测服务
        return await self.predictor.predict_from_task(
            task_info=task,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

    async def predict_from_experiment(
        self,
        experiment_id: int,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        使用实验表中的模型进行预测

        Args:
            experiment_id: 实验ID
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            预测结果
        """
        return await self.predictor.predict_from_experiment(
            experiment_id=experiment_id,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

    async def batch_predict(
        self,
        experiment_id: int,
        symbols: list[str],
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        批量预测多只股票

        Args:
            experiment_id: 实验ID
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            批量预测结果
        """
        return await self.predictor.batch_predict(
            experiment_id=experiment_id,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )
