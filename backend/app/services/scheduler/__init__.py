"""
定时任务调度服务模块

包含以下子服务：
- CronService: Cron 表达式工具
- TaskConfigService: 任务配置管理（CRUD）
- TaskHistoryService: 任务执行历史查询
- TaskExecutionService: 任务执行和状态查询
- ScheduledTaskService: 聚合门面（委托给上述 4 个子服务）
"""

from .cron_service import CronService
from .task_config_service import TaskConfigService
from .task_history_service import TaskHistoryService
from .task_execution_service import TaskExecutionService


class ScheduledTaskService:
    """
    定时任务管理聚合门面

    将 4 个子服务的功能聚合在一起，供端点层统一调用。
    端点内需要单一职责时，也可以直接使用专门的服务类：
    - CronService: Cron 表达式工具
    - TaskConfigService: 任务配置管理
    - TaskHistoryService: 执行历史查询
    - TaskExecutionService: 任务执行
    """

    def __init__(self):
        # 初始化各个子服务
        self.cron_service = CronService()
        self.config_service = TaskConfigService()
        self.history_service = TaskHistoryService()
        self.execution_service = TaskExecutionService()

    # ==================== Cron 工具方法（委托给 CronService） ====================

    def validate_cron_expression(self, cron_expr: str) -> bool:
        """验证 Cron 表达式"""
        return self.cron_service.validate_cron_expression(cron_expr)

    def calculate_next_run_time(self, cron_expr: str):
        """计算下次执行时间"""
        return self.cron_service.calculate_next_run_time(cron_expr)

    async def validate_and_get_next_run(self, cron_expression: str) -> dict:
        """验证 Cron 表达式并返回下次执行时间"""
        return self.cron_service.validate_and_get_next_run(cron_expression)

    # ==================== 任务配置管理（委托给 TaskConfigService） ====================

    async def get_all_tasks(self):
        """获取所有定时任务列表"""
        return await self.config_service.get_all_tasks()

    async def get_task_by_id(self, task_id: int):
        """根据任务 ID 获取任务详情"""
        return await self.config_service.get_task_by_id(task_id)

    async def create_task(self, task_name: str, module: str, **kwargs):
        """创建定时任务"""
        return await self.config_service.create_task(task_name, module, **kwargs)

    async def update_task(self, task_id: int, **kwargs):
        """更新定时任务配置"""
        return await self.config_service.update_task(task_id, **kwargs)

    async def toggle_task(self, task_id: int):
        """切换任务启用状态"""
        return await self.config_service.toggle_task(task_id)

    async def delete_task(self, task_id: int):
        """删除定时任务"""
        return await self.config_service.delete_task(task_id)

    # ==================== 任务执行历史（委托给 TaskHistoryService） ====================

    async def get_task_execution_history(self, task_id: int, limit: int = 20):
        """获取任务执行历史"""
        return await self.history_service.get_task_execution_history(task_id, limit)

    async def get_recent_execution_history(self, limit: int = 50):
        """获取最近的任务执行历史（所有任务）"""
        return await self.history_service.get_recent_execution_history(limit)

    # ==================== 任务执行（委托给 TaskExecutionService） ====================

    async def execute_task_async(self, task_id: int, user_id: int):
        """手动执行定时任务（异步提交到 Celery）"""
        return await self.execution_service.execute_task_async(task_id, user_id)

    async def get_task_execution_status(self, task_id: int, celery_task_id=None):
        """获取任务执行状态"""
        return await self.execution_service.get_task_execution_status(task_id, celery_task_id)


# 导出所有服务
__all__ = [
    'CronService',
    'TaskConfigService',
    'TaskHistoryService',
    'TaskExecutionService',
    'ScheduledTaskService',
]
