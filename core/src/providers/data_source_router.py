"""
数据源路由器

根据健康状态智能路由数据请求：
- 自动选择健康的数据源
- 主备切换
- 故障恢复
"""

from typing import Optional, List, Dict, Any, Callable
from src.providers.base_provider import BaseDataProvider
from src.providers.health_checker import DataSourceHealthChecker
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DataSourceRouter:
    """
    数据源路由器

    功能：
    - 根据健康状态选择最佳数据源
    - 自动故障转移
    - 负载均衡（按健康分数）
    """

    def __init__(
        self,
        providers: Dict[str, BaseDataProvider],
        health_checker: Optional[DataSourceHealthChecker] = None,
        fallback_enabled: bool = True
    ):
        """
        初始化数据源路由器

        Args:
            providers: 数据提供者字典 {name: provider_instance}
            health_checker: 健康检查器
            fallback_enabled: 是否启用故障转移
        """
        self.providers = providers
        self.health_checker = health_checker or DataSourceHealthChecker()
        self.fallback_enabled = fallback_enabled

        # 配置优先级
        self.priority_config: Dict[str, List[str]] = {}

        logger.info(f"数据源路由器初始化，可用数据源: {list(providers.keys())}")

    def set_priority(self, data_type: str, primary: str, secondaries: Optional[List[str]] = None):
        """
        设置数据源优先级

        Args:
            data_type: 数据类型（如 'daily_data', 'realtime_data'）
            primary: 主数据源名称
            secondaries: 备用数据源名称列表
        """
        self.priority_config[data_type] = [primary] + (secondaries or [])
        logger.info(f"数据源优先级配置: {data_type} -> {self.priority_config[data_type]}")

    def get_provider(
        self,
        data_type: str = 'daily_data',
        required_method: Optional[str] = None
    ) -> Optional[BaseDataProvider]:
        """
        获取可用的数据提供者

        Args:
            data_type: 数据类型
            required_method: 要求的方法名（用于检查提供者是否支持）

        Returns:
            可用的数据提供者，找不到返回None
        """
        # 获取优先级列表
        priority_list = self.priority_config.get(data_type, list(self.providers.keys()))

        # 尝试按优先级获取健康的提供者
        for provider_name in priority_list:
            if provider_name not in self.providers:
                logger.warning(f"数据源不存在: {provider_name}")
                continue

            # 检查健康状态
            if not self.health_checker.check_health(provider_name):
                logger.warning(f"数据源不健康: {provider_name}, 尝试下一个")
                continue

            # 检查是否支持所需方法
            provider = self.providers[provider_name]
            if required_method and not hasattr(provider, required_method):
                logger.warning(f"数据源 {provider_name} 不支持方法: {required_method}")
                continue

            logger.debug(f"选择数据源: {provider_name} (类型: {data_type})")
            return provider

        # 如果所有提供者都不可用
        logger.error(f"没有可用的数据源 (类型: {data_type})")
        return None

    def call_with_fallback(
        self,
        method_name: str,
        *args,
        data_type: str = 'daily_data',
        **kwargs
    ) -> Any:
        """
        调用数据提供者方法，失败时自动尝试备用数据源

        Args:
            method_name: 方法名
            *args: 位置参数
            data_type: 数据类型
            **kwargs: 关键字参数

        Returns:
            方法返回值

        Raises:
            RuntimeError: 所有数据源都失败时抛出
        """
        # 获取优先级列表
        priority_list = self.priority_config.get(data_type, list(self.providers.keys()))

        last_exception = None

        for provider_name in priority_list:
            if provider_name not in self.providers:
                continue

            # 检查健康状态
            if not self.health_checker.check_health(provider_name):
                continue

            provider = self.providers[provider_name]

            # 检查是否支持该方法
            if not hasattr(provider, method_name):
                logger.warning(f"数据源 {provider_name} 不支持方法: {method_name}")
                continue

            try:
                logger.debug(f"调用数据源: {provider_name}.{method_name}")

                # 调用方法
                method = getattr(provider, method_name)
                result = method(*args, **kwargs)

                # 记录成功
                self.health_checker.record_success(provider_name)

                logger.debug(f"数据源 {provider_name} 调用成功")
                return result

            except Exception as e:
                last_exception = e
                logger.warning(f"数据源 {provider_name} 调用失败: {e}")

                # 记录失败
                self.health_checker.record_failure(provider_name, str(e))

                # 如果不启用故障转移，直接抛出异常
                if not self.fallback_enabled:
                    raise

                # 继续尝试下一个数据源
                continue

        # 所有数据源都失败
        error_msg = f"所有数据源都失败 (方法: {method_name}, 类型: {data_type})"
        logger.error(error_msg)

        if last_exception:
            raise RuntimeError(error_msg) from last_exception
        else:
            raise RuntimeError(error_msg)

    def get_best_provider(self, data_type: str = 'daily_data') -> Optional[BaseDataProvider]:
        """
        获取健康分数最高的数据提供者

        Args:
            data_type: 数据类型

        Returns:
            最佳数据提供者
        """
        best_provider = None
        best_score = -1.0

        # 获取候选列表
        candidates = self.priority_config.get(data_type, list(self.providers.keys()))

        for provider_name in candidates:
            if provider_name not in self.providers:
                continue

            # 检查是否可用
            if not self.health_checker.check_health(provider_name):
                continue

            # 获取健康分数
            score = self.health_checker.get_health_score(provider_name)

            if score > best_score:
                best_score = score
                best_provider = self.providers[provider_name]

        if best_provider:
            logger.debug(f"最佳数据源健康分数: {best_score:.1f}")

        return best_provider

    def get_router_stats(self) -> Dict[str, Any]:
        """
        获取路由器统计信息

        Returns:
            统计信息字典
        """
        stats = {
            'total_providers': len(self.providers),
            'available_providers': 0,
            'providers': {},
            'priority_config': self.priority_config
        }

        for provider_name in self.providers.keys():
            is_healthy = self.health_checker.check_health(provider_name)
            health_score = self.health_checker.get_health_score(provider_name)

            if is_healthy:
                stats['available_providers'] += 1

            stats['providers'][provider_name] = {
                'is_healthy': is_healthy,
                'health_score': health_score
            }

        return stats

    def reset_provider_health(self, provider_name: str) -> bool:
        """
        重置指定数据源的健康状态

        Args:
            provider_name: 数据源名称

        Returns:
            是否重置成功
        """
        if provider_name not in self.providers:
            logger.warning(f"数据源不存在: {provider_name}")
            return False

        return self.health_checker.reset_provider(provider_name)

    def reset_all_health(self):
        """重置所有数据源的健康状态"""
        for provider_name in self.providers.keys():
            self.health_checker.reset_provider(provider_name)

        logger.info("所有数据源健康状态已重置")


# 全局路由器实例（单例模式）
_global_router: Optional[DataSourceRouter] = None


def init_global_router(
    providers: Dict[str, BaseDataProvider],
    health_checker: Optional[DataSourceHealthChecker] = None
) -> DataSourceRouter:
    """
    初始化全局路由器

    Args:
        providers: 数据提供者字典
        health_checker: 健康检查器

    Returns:
        路由器实例
    """
    global _global_router
    _global_router = DataSourceRouter(providers, health_checker)
    return _global_router


def get_global_router() -> Optional[DataSourceRouter]:
    """获取全局路由器实例"""
    return _global_router
