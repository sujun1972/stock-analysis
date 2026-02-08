"""
加载器工厂模块

根据策略来源选择合适的加载器
"""

from typing import Dict, Any, Optional
from loguru import logger

from .base_loader import BaseLoader
from .config_loader import ConfigLoader
from .dynamic_loader import DynamicCodeLoader


class LoaderFactory:
    """
    加载器工厂

    根据策略来源选择合适的加载器：
    - 'config': 使用 ConfigLoader（参数配置方案）
    - 'dynamic': 使用 DynamicCodeLoader（AI代码生成方案）

    采用单例模式，确保全局只有一套加载器实例
    """

    _instance = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(LoaderFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化加载器工厂"""
        if self._initialized:
            return

        self.config_loader = ConfigLoader()
        self.dynamic_loader = DynamicCodeLoader()

        self._initialized = True

        logger.info("LoaderFactory 初始化完成")

    def load_strategy(
        self,
        strategy_source: str,
        strategy_id: int,
        **kwargs
    ):
        """
        加载策略

        Args:
            strategy_source: 策略来源
                - 'config': 参数配置方案
                - 'dynamic': AI代码生成方案
            strategy_id: 策略ID
            **kwargs: 传递给加载器的参数

        Returns:
            策略实例

        Raises:
            ValueError: 未知的策略来源
        """
        if strategy_source == 'config':
            logger.info(f"使用ConfigLoader加载策略: ID={strategy_id}")
            return self.config_loader.load_strategy(strategy_id, **kwargs)

        elif strategy_source == 'dynamic':
            logger.info(f"使用DynamicCodeLoader加载策略: ID={strategy_id}")
            return self.dynamic_loader.load_strategy(strategy_id, **kwargs)

        else:
            raise ValueError(
                f"未知的策略来源: {strategy_source}. "
                f"支持的来源: ['config', 'dynamic']"
            )

    def reload_strategy(
        self,
        strategy_source: str,
        strategy_id: int,
        **kwargs
    ):
        """
        重新加载策略（清除缓存后加载）

        Args:
            strategy_source: 策略来源
            strategy_id: 策略ID
            **kwargs: 传递给加载器的参数

        Returns:
            新的策略实例
        """
        if strategy_source == 'config':
            return self.config_loader.reload_strategy(strategy_id)

        elif strategy_source == 'dynamic':
            strict_mode = kwargs.get('strict_mode', True)
            return self.dynamic_loader.reload_strategy(strategy_id, strict_mode=strict_mode)

        else:
            raise ValueError(f"未知的策略来源: {strategy_source}")

    def batch_load_strategies(
        self,
        strategy_configs: list[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Dict[int, Any]]:
        """
        批量加载策略

        Args:
            strategy_configs: 策略配置列表
                [
                    {'source': 'config', 'id': 1},
                    {'source': 'dynamic', 'id': 2},
                    ...
                ]
            **kwargs: 传递给加载器的参数

        Returns:
            {
                'config': {1: strategy1, ...},
                'dynamic': {2: strategy2, ...}
            }
        """
        results = {
            'config': {},
            'dynamic': {}
        }

        for config in strategy_configs:
            source = config.get('source')
            strategy_id = config.get('id')

            if not source or not strategy_id:
                logger.warning(f"跳过无效的配置: {config}")
                continue

            try:
                strategy = self.load_strategy(source, strategy_id, **kwargs)
                results[source][strategy_id] = strategy
            except Exception as e:
                logger.error(f"加载策略失败: source={source}, id={strategy_id}, 错误: {e}")
                continue

        total = len(results['config']) + len(results['dynamic'])
        logger.info(f"批量加载完成: 成功 {total}/{len(strategy_configs)}")

        return results

    def clear_cache(self, strategy_source: Optional[str] = None):
        """
        清除缓存

        Args:
            strategy_source: 策略来源（None表示清除全部）
        """
        if strategy_source is None or strategy_source == 'config':
            self.config_loader.clear_cache()
            logger.debug("ConfigLoader 缓存已清除")

        if strategy_source is None or strategy_source == 'dynamic':
            self.dynamic_loader.clear_cache()
            logger.debug("DynamicCodeLoader 缓存已清除")

        if strategy_source is None:
            logger.info("所有加载器缓存已清除")

    def get_cache_info(self) -> Dict[str, Any]:
        """
        获取缓存信息

        Returns:
            缓存统计信息
        """
        return {
            'config_loader': self.config_loader.get_cache_info(),
            'dynamic_loader': self.dynamic_loader.get_cache_info(),
        }

    def list_available_strategies(
        self,
        strategy_source: Optional[str] = None
    ) -> Dict[str, list]:
        """
        列出可用的策略

        Args:
            strategy_source: 策略来源（None表示全部）

        Returns:
            {
                'config': [...],
                'dynamic': [...]
            }
        """
        results = {}

        if strategy_source is None or strategy_source == 'config':
            try:
                results['config'] = self.config_loader.list_available_configs()
            except Exception as e:
                logger.error(f"列出配置策略失败: {e}")
                results['config'] = []

        if strategy_source is None or strategy_source == 'dynamic':
            try:
                results['dynamic'] = self.dynamic_loader.list_available_strategies()
            except Exception as e:
                logger.error(f"列出动态策略失败: {e}")
                results['dynamic'] = []

        return results

    def get_loader(self, strategy_source: str) -> BaseLoader:
        """
        获取指定的加载器实例

        Args:
            strategy_source: 策略来源

        Returns:
            加载器实例

        Raises:
            ValueError: 未知的策略来源
        """
        if strategy_source == 'config':
            return self.config_loader
        elif strategy_source == 'dynamic':
            return self.dynamic_loader
        else:
            raise ValueError(f"未知的策略来源: {strategy_source}")

    def __repr__(self) -> str:
        config_cached = len(self.config_loader._cache)
        dynamic_cached = len(self.dynamic_loader._cache)
        return f"LoaderFactory(config={config_cached}, dynamic={dynamic_cached})"


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例：使用加载器工厂
    factory = LoaderFactory()

    try:
        # 1. 加载参数配置策略
        config_strategy = factory.load_strategy(
            strategy_source='config',
            strategy_id=1
        )
        print(f"配置策略: {config_strategy}")

        # 2. 加载AI代码策略
        dynamic_strategy = factory.load_strategy(
            strategy_source='dynamic',
            strategy_id=1,
            strict_mode=True
        )
        print(f"动态策略: {dynamic_strategy}")

        # 3. 批量加载
        strategies = factory.batch_load_strategies([
            {'source': 'config', 'id': 1},
            {'source': 'config', 'id': 2},
            {'source': 'dynamic', 'id': 1},
        ])
        print(f"批量加载: {strategies}")

        # 4. 查看缓存信息
        cache_info = factory.get_cache_info()
        print(f"缓存信息: {cache_info}")

        # 5. 列出可用策略
        available = factory.list_available_strategies()
        print(f"可用策略: {available}")

        # 6. 清除缓存
        factory.clear_cache()
        print("缓存已清除")

    except Exception as e:
        logger.error(f"示例执行失败: {e}")
