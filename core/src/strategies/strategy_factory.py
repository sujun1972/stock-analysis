"""
策略工厂模块（数据库驱动版本）

完全数据库驱动的策略系统
所有策略从数据库动态加载，不依赖本地文件

版本: 2.0.0 (Database-Driven)
更新日期: 2026-03-07
"""

from typing import Dict, Any, Optional
from loguru import logger

from .base_strategy import BaseStrategy


class StrategyFactory:
    """
    策略工厂 - 完全数据库驱动

    ⚠️ 重要变更 (v2.0.0):
    - 所有策略从数据库动态加载
    - 移除了对本地策略文件的硬编码依赖
    - 不再支持直接创建预定义策略

    使用方式:
        # 旧方式（已废弃）
        # factory = StrategyFactory()
        # strategy = factory.create('momentum', config={})

        # 新方式（通过 Backend API）
        from app.services.strategy_loader import StrategyDynamicLoader
        from app.repositories.strategy_repository import StrategyRepository

        repo = StrategyRepository()
        strategy_record = repo.get_by_name('momentum_entry')
        strategy = StrategyDynamicLoader.load_strategy(strategy_record)
    """

    def __init__(self):
        """初始化策略工厂"""
        logger.warning(
            "StrategyFactory 已废弃本地策略创建功能，请使用 Backend 的 StrategyDynamicLoader"
        )

    @classmethod
    def create(
        cls,
        strategy_type: str,
        config: Dict[str, Any],
        name: Optional[str] = None
    ) -> BaseStrategy:
        """
        创建策略（已废弃）

        ⚠️ 此方法已废弃，请使用数据库驱动的加载方式

        Args:
            strategy_type: 策略类型
            config: 策略配置
            name: 策略名称

        Raises:
            NotImplementedError: 始终抛出，提示使用新方式
        """
        raise NotImplementedError(
            "StrategyFactory.create() 已废弃。\n"
            "请使用数据库驱动的方式:\n\n"
            "from app.services.strategy_loader import StrategyDynamicLoader\n"
            "from app.repositories.strategy_repository import StrategyRepository\n\n"
            "repo = StrategyRepository()\n"
            "strategy_record = repo.get_by_name('momentum_entry')  # 或其他策略\n"
            "strategy = StrategyDynamicLoader.load_strategy(strategy_record, custom_config=config)\n"
        )

    def create_from_config(self, config_id: int, **kwargs) -> BaseStrategy:
        """
        从配置创建策略（已废弃）

        ⚠️ 此方法已废弃，请使用数据库驱动的加载方式

        Raises:
            NotImplementedError: 始终抛出
        """
        raise NotImplementedError(
            "create_from_config() 已废弃，请使用 StrategyDynamicLoader.load_strategy()"
        )

    def create_from_code(self, strategy_id: int, **kwargs) -> BaseStrategy:
        """
        从AI代码创建策略（已废弃）

        ⚠️ 此方法已废弃，请使用数据库驱动的加载方式

        Raises:
            NotImplementedError: 始终抛出
        """
        raise NotImplementedError(
            "create_from_code() 已废弃，请使用 StrategyDynamicLoader.load_strategy()"
        )

    @classmethod
    def list_strategies(cls) -> list:
        """
        列出所有可用的策略（数据库版本）

        ⚠️ 此方法已更改为查询数据库

        Returns:
            提示信息，建议使用 StrategyRepository
        """
        logger.warning(
            "list_strategies() 应通过数据库查询:\n"
            "repo = StrategyRepository()\n"
            "strategies = repo.get_all(strategy_type='entry')"
        )
        return []

    @classmethod
    def register_strategy(cls, strategy_type: str, strategy_class: type):
        """
        注册策略（已废弃）

        ⚠️ 此方法已废弃，策略应通过数据库插入

        Raises:
            NotImplementedError: 始终抛出
        """
        raise NotImplementedError(
            "register_strategy() 已废弃。\n"
            "请通过数据库插入策略:\n"
            "INSERT INTO strategies (name, code, ...) VALUES (...);"
        )


# ==================== 向后兼容性说明 ====================

"""
# 旧代码迁移指南

## 1. 创建预定义策略

旧方式:
    factory = StrategyFactory()
    strategy = factory.create('momentum', config={'lookback_period': 20})

新方式:
    from app.services.strategy_loader import StrategyDynamicLoader
    from app.repositories.strategy_repository import StrategyRepository

    repo = StrategyRepository()
    strategy_record = repo.get_by_name('momentum_entry')
    strategy = StrategyDynamicLoader.load_strategy(
        strategy_record,
        custom_config={'lookback_period': 20}
    )

## 2. 列出可用策略

旧方式:
    strategies = StrategyFactory.list_strategies()

新方式:
    repo = StrategyRepository()
    strategies = repo.get_all(strategy_type='entry', is_enabled=True)

## 3. 回测中使用策略

旧方式:
    strategy = StrategyFactory.create('momentum', config={})
    engine.backtest(strategy, prices)

新方式:
    # 通过 Backend API 自动加载
    # 参见 backend/app/api/endpoints/backtest.py
    # execute_backtest_core() 函数
"""


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("StrategyFactory v2.0.0 (Database-Driven)")
    logger.info("=" * 60)
    logger.info("")
    logger.info("此模块已迁移至完全数据库驱动")
    logger.info("所有策略现在从 strategies 表动态加载")
    logger.info("")
    logger.info("请使用:")
    logger.info("  - StrategyRepository (数据库查询)")
    logger.info("  - StrategyDynamicLoader (动态加载)")
    logger.info("")
    logger.info("=" * 60)
