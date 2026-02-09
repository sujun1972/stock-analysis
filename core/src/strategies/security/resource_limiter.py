"""
资源限制器

限制策略执行时的资源使用
"""

import signal
import sys
from typing import Dict, Any, Callable, Optional
from contextlib import contextmanager
from loguru import logger


class ResourceLimiter:
    """
    资源限制器

    限制策略执行时的资源使用

    注意: 由于 macOS 对 RLIMIT_AS 的限制，这个版本主要使用时间限制和信号处理
    """

    def __init__(
        self,
        max_memory_mb: int = 512,      # 最大内存 (MB) - 仅用于参考，macOS无法强制限制
        max_cpu_time: int = 300,       # 最大CPU时间 (秒) - 提高默认值避免测试时累积超限
        max_wall_time: int = 60        # 最大实际时间 (秒)
    ):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time = max_cpu_time
        self.max_wall_time = max_wall_time
        self._old_handlers = {}

    @contextmanager
    def limit_resources(self):
        """
        上下文管理器: 限制资源使用

        Usage:
            with limiter.limit_resources():
                # 执行策略代码
                strategy.generate_signals(prices)
        """
        try:
            # 尝试导入 resource 模块 (仅在 Unix 系统上可用)
            if sys.platform != 'win32':
                try:
                    import resource
                    self._set_resource_limits(resource)
                except ImportError:
                    logger.warning("resource 模块不可用，跳过资源限制设置")

            # 设置实际时间限制 (使用signal - 所有平台都支持)
            self._set_timeout_alarm()

            logger.debug(
                f"已设置资源限制: 内存={self.max_memory_mb}MB (参考), "
                f"CPU={self.max_cpu_time}s, 墙钟时间={self.max_wall_time}s"
            )

            yield

        except MemoryError:
            logger.error(f"内存超限: > {self.max_memory_mb}MB")
            raise ResourceLimitError(f"内存超限: > {self.max_memory_mb}MB")

        except TimeoutError as e:
            logger.error(f"执行超时: {e}")
            raise ResourceLimitError(str(e))

        finally:
            # 恢复原始限制
            self._restore_limits()

            logger.debug("已恢复资源限制")

    def _set_resource_limits(self, resource):
        """设置资源限制 (仅Unix系统)"""
        try:
            # 保存原始限制
            self._old_handlers['cpu'] = resource.getrlimit(resource.RLIMIT_CPU)

            # 设置CPU时间限制
            resource.setrlimit(
                resource.RLIMIT_CPU,
                (self.max_cpu_time, self.max_cpu_time)
            )

            # 注意: macOS 不支持 RLIMIT_AS，所以我们跳过内存限制
            # 在生产环境中，建议使用容器(Docker)来进行内存限制
            if sys.platform != 'darwin':
                try:
                    self._old_handlers['memory'] = resource.getrlimit(resource.RLIMIT_AS)
                    memory_limit = self.max_memory_mb * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
                except (ValueError, OSError) as e:
                    logger.warning(f"无法设置内存限制: {e}")

        except Exception as e:
            logger.warning(f"设置资源限制失败: {e}")

    def _set_timeout_alarm(self):
        """设置超时告警"""
        def timeout_handler(signum, frame):
            raise TimeoutError(f"执行超时 ({self.max_wall_time}秒)")

        # 保存旧的信号处理器
        try:
            self._old_handlers['alarm'] = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.max_wall_time)
        except (ValueError, OSError) as e:
            # Windows 不支持 SIGALRM
            logger.warning(f"无法设置超时告警: {e}")

    def _restore_limits(self):
        """恢复原始限制"""
        # 取消alarm
        try:
            signal.alarm(0)
            if 'alarm' in self._old_handlers:
                signal.signal(signal.SIGALRM, self._old_handlers['alarm'])
        except (ValueError, OSError):
            pass

        # 恢复资源限制
        if sys.platform != 'win32':
            try:
                import resource

                if 'cpu' in self._old_handlers:
                    resource.setrlimit(resource.RLIMIT_CPU, self._old_handlers['cpu'])

                if 'memory' in self._old_handlers:
                    resource.setrlimit(resource.RLIMIT_AS, self._old_handlers['memory'])

            except (ImportError, ValueError, OSError):
                pass

        # 清空保存的处理器
        self._old_handlers.clear()

    def check_memory_usage(self) -> Dict[str, Any]:
        """
        检查当前内存使用情况

        Returns:
            {
                'current_mb': float,
                'limit_mb': int,
                'usage_percent': float
            }
        """
        try:
            import psutil
            import os

            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            current_mb = memory_info.rss / 1024 / 1024
            usage_percent = (current_mb / self.max_memory_mb) * 100

            return {
                'current_mb': round(current_mb, 2),
                'limit_mb': self.max_memory_mb,
                'usage_percent': round(usage_percent, 2)
            }
        except ImportError:
            logger.warning("psutil 未安装，无法检查内存使用")
            return {
                'current_mb': 0,
                'limit_mb': self.max_memory_mb,
                'usage_percent': 0
            }


class ResourceLimitError(Exception):
    """资源限制错误"""
    pass
