"""
策略工厂模块

提供统一的策略创建接口，支持三种创建方式：
1. 预定义策略 (直接创建)
2. 配置驱动策略 (从数据库加载配置)
3. 动态代码策略 (从数据库加载AI生成的代码)
"""

from typing import Dict, Any, Optional, Type
from loguru import logger

from .base_strategy import BaseStrategy
from .predefined.momentum_strategy import MomentumStrategy
from .predefined.mean_reversion_strategy import MeanReversionStrategy
from .predefined.multi_factor_strategy import MultiFactorStrategy


class StrategyFactory:
    """
    策略工厂 - 统一的策略创建接口

    支持三种创建方式:
    1. 预定义策略 (直接创建)
    2. 配置驱动策略 (从数据库加载配置)
    3. 动态代码策略 (从数据库加载AI生成的代码)
    """

    # 预定义策略类型映射
    PREDEFINED_STRATEGIES = {
        'momentum': MomentumStrategy,
        'mean_reversion': MeanReversionStrategy,
        'multi_factor': MultiFactorStrategy,
    }

    def __init__(self):
        """初始化策略工厂"""
        # 延迟导入加载器工厂，避免循环依赖
        self._loader_factory = None

    @property
    def loader_factory(self):
        """懒加载 LoaderFactory"""
        if self._loader_factory is None:
            from .loaders.loader_factory import LoaderFactory
            self._loader_factory = LoaderFactory()
        return self._loader_factory

    @classmethod
    def create(
        cls,
        strategy_type: str,
        config: Dict[str, Any],
        name: Optional[str] = None
    ) -> BaseStrategy:
        """
        创建预定义策略 (方式1)

        Args:
            strategy_type: 策略类型 ('momentum', 'mean_reversion', 'multi_factor')
            config: 策略配置字典
            name: 策略名称 (可选)

        Returns:
            策略实例

        Raises:
            ValueError: 如果策略类型不支持

        Examples:
            >>> factory = StrategyFactory()
            >>> strategy = factory.create(
            ...     strategy_type='momentum',
            ...     config={'lookback_period': 20, 'top_n': 50},
            ...     name='MOM20'
            ... )
        """
        if strategy_type not in cls.PREDEFINED_STRATEGIES:
            raise ValueError(
                f"不支持的策略类型: {strategy_type}. "
                f"支持的类型: {list(cls.PREDEFINED_STRATEGIES.keys())}"
            )

        strategy_class = cls.PREDEFINED_STRATEGIES[strategy_type]
        strategy_name = name or f"{strategy_type}_strategy"

        logger.debug(f"创建预定义策略: {strategy_name} ({strategy_type})")

        strategy = strategy_class(strategy_name, config)
        strategy._strategy_type = 'predefined'

        return strategy

    def create_from_config(
        self,
        config_id: int,
        **kwargs
    ) -> BaseStrategy:
        """
        从配置创建策略 (方式2 - 参数配置方案)

        从 strategy_configs 表加载配置并创建策略实例

        Args:
            config_id: strategy_configs表的ID
            **kwargs: 传递给加载器的参数 (如 use_cache)

        Returns:
            策略实例

        Raises:
            ValueError: 如果配置不存在或已禁用
            Exception: 数据库连接失败等

        Examples:
            >>> factory = StrategyFactory()
            >>> strategy = factory.create_from_config(config_id=123)
        """
        logger.info(f"从配置创建策略: config_id={config_id}")

        strategy = self.loader_factory.load_strategy(
            strategy_source='config',
            strategy_id=config_id,
            **kwargs
        )

        strategy._strategy_type = 'configured'

        return strategy

    def create_from_code(
        self,
        strategy_id: int,
        **kwargs
    ) -> BaseStrategy:
        """
        从AI代码创建策略 (方式3 - AI代码生成方案)

        从 ai_strategies 表加载AI生成的代码并动态创建策略实例

        Args:
            strategy_id: ai_strategies表的ID
            **kwargs: 传递给加载器的参数 (如 strict_mode, use_cache)

        Returns:
            策略实例

        Raises:
            ValueError: 如果策略不存在或已禁用
            SecurityError: 如果代码安全验证失败
            Exception: 编译或执行失败等

        Examples:
            >>> factory = StrategyFactory()
            >>> strategy = factory.create_from_code(
            ...     strategy_id=456,
            ...     strict_mode=True
            ... )
        """
        logger.info(f"从AI代码创建策略: strategy_id={strategy_id}")

        strategy = self.loader_factory.load_strategy(
            strategy_source='dynamic',
            strategy_id=strategy_id,
            **kwargs
        )

        strategy._strategy_type = 'dynamic'

        return strategy

    @classmethod
    def register_strategy(
        cls,
        strategy_type: str,
        strategy_class: Type[BaseStrategy]
    ):
        """
        注册自定义策略类型

        允许用户注册自己的策略类，之后可通过 create() 方法创建

        Args:
            strategy_type: 策略类型标识 (如 'custom_momentum')
            strategy_class: 策略类 (必须继承自 BaseStrategy)

        Raises:
            ValueError: 如果策略类不继承自 BaseStrategy

        Examples:
            >>> class MyCustomStrategy(BaseStrategy):
            ...     pass
            >>> StrategyFactory.register_strategy('my_custom', MyCustomStrategy)
            >>> strategy = StrategyFactory.create('my_custom', config={})
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"{strategy_class} 必须继承自 BaseStrategy")

        cls.PREDEFINED_STRATEGIES[strategy_type] = strategy_class
        logger.info(f"已注册策略类型: {strategy_type} -> {strategy_class.__name__}")

    @classmethod
    def list_strategies(cls) -> list:
        """
        列出所有可用的预定义策略类型

        Returns:
            策略类型列表

        Examples:
            >>> StrategyFactory.list_strategies()
            ['momentum', 'mean_reversion', 'multi_factor']
        """
        return list(cls.PREDEFINED_STRATEGIES.keys())

    @classmethod
    def get_strategy_class(cls, strategy_type: str) -> Type[BaseStrategy]:
        """
        获取策略类

        Args:
            strategy_type: 策略类型

        Returns:
            策略类

        Raises:
            ValueError: 如果策略类型不存在
        """
        if strategy_type not in cls.PREDEFINED_STRATEGIES:
            raise ValueError(f"策略类型不存在: {strategy_type}")

        return cls.PREDEFINED_STRATEGIES[strategy_type]


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例1: 创建预定义策略
    factory = StrategyFactory()

    momentum_strategy = factory.create(
        strategy_type='momentum',
        config={'lookback_period': 20, 'top_n': 50},
        name='MOM20'
    )
    logger.info(f"创建策略: {momentum_strategy}")
    logger.info(f"元数据: {momentum_strategy.get_metadata()}")

    # 示例2: 列出所有策略
    logger.info(f"可用策略: {StrategyFactory.list_strategies()}")

    # 示例3: 注册自定义策略
    # class MyStrategy(BaseStrategy):
    #     def generate_signals(self, prices, features=None, **kwargs):
    #         pass
    #     def calculate_scores(self, prices, features=None, date=None):
    #         pass
    #
    # StrategyFactory.register_strategy('my_strategy', MyStrategy)
    # custom = factory.create('my_strategy', config={})

    logger.success("策略工厂模块测试完成")
