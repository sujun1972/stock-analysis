"""
策略加载器基类模块

定义所有策略加载器必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger


class BaseLoader(ABC):
    """
    策略加载器抽象基类

    所有加载器必须实现 load_strategy 方法
    """

    def __init__(self):
        """初始化加载器"""
        self._cache: Dict[int, Any] = {}
        logger.debug(f"初始化加载器: {self.__class__.__name__}")

    @abstractmethod
    def load_strategy(
        self,
        strategy_id: int,
        use_cache: bool = True,
        **kwargs
    ):
        """
        加载策略（必须实现）

        Args:
            strategy_id: 策略ID
            use_cache: 是否使用缓存
            **kwargs: 其他参数

        Returns:
            策略实例
        """
        pass

    def clear_cache(self, strategy_id: Optional[int] = None):
        """
        清除缓存

        Args:
            strategy_id: 策略ID（None表示清除全部）
        """
        if strategy_id is not None:
            if strategy_id in self._cache:
                del self._cache[strategy_id]
                logger.debug(f"清除缓存: strategy_id={strategy_id}")
        else:
            self._cache.clear()
            logger.debug("清除所有缓存")

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息

        Returns:
            缓存统计信息
        """
        return {
            'loader_type': self.__class__.__name__,
            'cached_count': len(self._cache),
            'cached_ids': list(self._cache.keys())
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(cached={len(self._cache)})"
