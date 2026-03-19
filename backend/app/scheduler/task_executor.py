"""
任务执行器
用于手动触发定时任务执行

职责：
- 执行任务（提交到Celery队列）
- 查询任务状态
- 取消任务执行
"""

from typing import Dict, Any, Optional
from loguru import logger

from app.celery_app import celery_app
from .task_metadata_service import TaskMetadataService


class TaskExecutor:
    """定时任务执行器，统一处理各种任务的手动执行"""

    def __init__(self):
        """初始化执行器"""
        self.metadata_service = TaskMetadataService()

    @property
    def TASK_MAPPING(self) -> Dict[str, Dict[str, Any]]:
        """
        向后兼容：提供TASK_MAPPING属性访问

        注意：此属性已废弃，建议直接使用 metadata_service
        """
        return self.metadata_service.task_mapping

    async def execute_task(
        self,
        task_name: str,
        module: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        执行定时任务

        Args:
            task_name: 任务名称（用于日志）
            module: 模块名称（用于查找对应的Celery任务）
            params: 任务参数

        Returns:
            Celery任务ID

        Raises:
            ValueError: 如果模块没有对应的Celery任务
        """
        # 查找对应的Celery任务
        task_config = self.metadata_service.get_task_config(module)

        if not task_config:
            # 尝试根据任务名称模糊查找（兼容旧格式）
            task_config = self.metadata_service.find_task_by_name(task_name)

        if not task_config:
            raise ValueError(f"未找到模块 '{module}' 对应的Celery任务")

        celery_task_name = task_config['task']
        friendly_name = task_config.get('name', task_name)

        # 合并默认参数和用户参数，并过滤元数据字段
        final_params = self.metadata_service.merge_task_params(module, params)

        # 日志输出
        logger.info(f"🚀 手动执行任务: {friendly_name}")
        logger.info(f"   Celery任务: {celery_task_name}")
        logger.info(f"   参数: {final_params}")

        if params:
            filtered_fields = self.metadata_service.get_filtered_metadata_fields(params)
            if filtered_fields:
                logger.info(f"   原始参数: {params}")
                logger.info(f"   已过滤元数据: {filtered_fields}")

        try:
            # 获取Celery任务
            task = celery_app.send_task(
                celery_task_name,
                kwargs=final_params,
                queue='default'
            )

            logger.info(f"✅ 任务已提交: {friendly_name} (ID: {task.id})")
            return task.id

        except Exception as e:
            logger.error(f"❌ 执行任务失败 {friendly_name}: {e}")
            raise

    def get_task_status(self, celery_task_id: str) -> Dict[str, Any]:
        """
        获取Celery任务状态

        Args:
            celery_task_id: Celery任务ID

        Returns:
            任务状态信息
        """
        from celery.result import AsyncResult

        result = AsyncResult(celery_task_id, app=celery_app)

        status_info = {
            'task_id': celery_task_id,
            'state': result.state,
            'current': 0,
            'total': 100,
            'status': 'PENDING'
        }

        if result.state == 'PENDING':
            status_info['status'] = '等待执行'
        elif result.state == 'STARTED':
            status_info['status'] = '正在执行'
        elif result.state == 'SUCCESS':
            status_info['status'] = '执行成功'
            status_info['result'] = result.result
        elif result.state == 'FAILURE':
            status_info['status'] = '执行失败'
            status_info['error'] = str(result.info)
        else:
            # 处理其他状态
            status_info['status'] = result.state
            if hasattr(result.info, 'get'):
                status_info['current'] = result.info.get('current', 0)
                status_info['total'] = result.info.get('total', 100)

        return status_info

    async def cancel_task(self, celery_task_id: str) -> bool:
        """
        取消Celery任务

        Args:
            celery_task_id: Celery任务ID

        Returns:
            是否成功取消
        """
        try:
            celery_app.control.revoke(celery_task_id, terminate=True)
            logger.info(f"✅ 已取消任务: {celery_task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 取消任务失败 {celery_task_id}: {e}")
            return False
