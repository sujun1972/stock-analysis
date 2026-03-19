"""
任务元数据管理服务
提供任务元数据查询、过滤、合并等功能

职责：
- 封装任务元数据访问逻辑
- 提供任务查找和过滤方法
- 处理任务参数合并
"""

from typing import Dict, Any, Optional, List
from loguru import logger

from .task_metadata import TASK_MAPPING, TASK_CATEGORIES, METADATA_FIELDS


class TaskMetadataService:
    """任务元数据管理服务"""

    def __init__(self):
        """初始化服务"""
        self.task_mapping = TASK_MAPPING
        self.categories = TASK_CATEGORIES
        self.metadata_fields = METADATA_FIELDS

    def get_task_config(self, module: str) -> Optional[Dict[str, Any]]:
        """
        获取任务配置

        Args:
            module: 模块名称

        Returns:
            任务配置字典，未找到返回None
        """
        return self.task_mapping.get(module)

    def find_task_by_name(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        根据任务名称模糊查找任务配置

        Args:
            task_name: 任务名称

        Returns:
            任务配置字典，未找到返回None
        """
        for key, config in self.task_mapping.items():
            if task_name in key or key in task_name:
                return config
        return None

    def get_celery_task_name(self, module: str) -> Optional[str]:
        """
        获取Celery任务名称

        Args:
            module: 模块名称

        Returns:
            Celery任务名称，未找到返回None
        """
        config = self.get_task_config(module)
        return config['task'] if config else None

    def get_friendly_name(self, module: str, default: str = '') -> str:
        """
        获取任务友好名称

        Args:
            module: 模块名称
            default: 默认名称

        Returns:
            任务友好名称
        """
        config = self.get_task_config(module)
        return config.get('name', default) if config else default

    def merge_task_params(
        self,
        module: str,
        user_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        合并任务参数（默认参数 + 用户参数），并过滤元数据字段

        Args:
            module: 模块名称
            user_params: 用户提供的参数

        Returns:
            合并并过滤后的参数字典
        """
        config = self.get_task_config(module)
        if not config:
            return user_params or {}

        # 从默认参数开始
        final_params = {}
        if 'default_params' in config:
            final_params.update(config['default_params'])

        # 合并用户参数，但排除元数据字段
        if user_params:
            filtered_params = {
                k: v for k, v in user_params.items()
                if k not in self.metadata_fields
            }
            final_params.update(filtered_params)

        return final_params

    def filter_metadata_fields(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        过滤元数据字段

        Args:
            params: 原始参数

        Returns:
            过滤后的参数
        """
        return {
            k: v for k, v in params.items()
            if k not in self.metadata_fields
        }

    def get_filtered_metadata_fields(self, params: Dict[str, Any]) -> List[str]:
        """
        获取被过滤的元数据字段列表

        Args:
            params: 原始参数

        Returns:
            被过滤的元数据字段列表
        """
        return [k for k in params.keys() if k in self.metadata_fields]

    def get_tasks_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """
        按分类获取任务

        Args:
            category: 任务分类

        Returns:
            任务配置字典
        """
        return {
            module: config
            for module, config in self.task_mapping.items()
            if config.get('category') == category
        }

    def get_all_categories(self) -> List[Dict[str, Any]]:
        """
        获取所有任务分类

        Returns:
            分类列表
        """
        return self.categories

    def validate_task_exists(self, module: str) -> bool:
        """
        验证任务是否存在

        Args:
            module: 模块名称

        Returns:
            是否存在
        """
        return module in self.task_mapping

    def get_task_count(self) -> int:
        """
        获取任务总数

        Returns:
            任务总数
        """
        return len(self.task_mapping)

    def get_task_count_by_category(self) -> Dict[str, int]:
        """
        按分类统计任务数量

        Returns:
            分类任务数量字典
        """
        result = {}
        for config in self.task_mapping.values():
            category = config.get('category', 'Unknown')
            result[category] = result.get(category, 0) + 1
        return result
