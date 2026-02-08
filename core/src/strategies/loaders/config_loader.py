"""
配置加载器模块

从数据库加载策略配置，实例化为预定义的策略类（方案1 - 参数配置）
"""

from typing import Dict, Any, Optional
from loguru import logger

from .base_loader import BaseLoader

try:
    from ...database.db_manager import DatabaseManager
except ImportError:
    # 用于测试时的兼容
    DatabaseManager = None


class ConfigLoader(BaseLoader):
    """
    配置加载器 - 支持方案1 (参数配置)

    从数据库加载策略配置，实例化为预定义的策略类

    数据流:
    1. 从 strategy_configs 表读取配置
    2. 验证配置状态（is_active）
    3. 根据 strategy_type 创建对应的策略实例
    4. 附加元信息（config_id, version等）
    5. 缓存策略实例
    """

    def __init__(self):
        """初始化配置加载器"""
        super().__init__()

        # 延迟初始化数据库连接
        self._db = None

        # 策略工厂（延迟导入避免循环依赖）
        self._factory = None

        logger.info("ConfigLoader 初始化完成")

    @property
    def db(self):
        """懒加载数据库管理器"""
        if self._db is None:
            if DatabaseManager is None:
                raise ImportError("DatabaseManager 未正确导入，请检查依赖")
            self._db = DatabaseManager()
        return self._db

    @property
    def factory(self):
        """懒加载策略工厂"""
        if self._factory is None:
            # 延迟导入避免循环依赖
            from ..strategy_factory import StrategyFactory
            self._factory = StrategyFactory()
        return self._factory

    def load_strategy(
        self,
        strategy_id: int,
        use_cache: bool = True,
        **kwargs
    ):
        """
        从配置ID加载策略

        Args:
            strategy_id: strategy_configs表的ID
            use_cache: 是否使用缓存
            **kwargs: 额外参数

        Returns:
            策略实例

        Raises:
            ValueError: 配置不存在或无效
            DatabaseError: 数据库错误
        """
        # 检查缓存
        if use_cache and strategy_id in self._cache:
            logger.debug(f"从缓存加载策略配置: ID={strategy_id}")
            return self._cache[strategy_id]

        logger.info(f"开始加载策略配置: ID={strategy_id}")

        # 从数据库加载配置
        config_data = self._load_config_from_db(strategy_id)

        # 验证配置状态
        if not config_data.get('is_active', False):
            raise ValueError(f"策略配置已禁用: ID={strategy_id}")

        # 创建策略实例
        strategy_type = config_data['strategy_type']
        config = config_data['config']
        name = config_data.get('name', f"strategy_{strategy_id}")

        logger.debug(f"创建策略: type={strategy_type}, name={name}")

        strategy = self.factory.create(
            strategy_type=strategy_type,
            config=config,
            name=name
        )

        # 附加元信息
        strategy._config_id = strategy_id
        strategy._strategy_type = 'configured'
        strategy._config_version = config_data.get('version', 1)
        strategy._config_hash = config_data.get('config_hash', '')

        # 缓存
        if use_cache:
            self._cache[strategy_id] = strategy

        logger.success(
            f"策略配置加载成功: {name} "
            f"(ID={strategy_id}, Version={strategy._config_version})"
        )

        return strategy

    def _load_config_from_db(self, config_id: int) -> Dict[str, Any]:
        """
        从数据库加载配置

        Args:
            config_id: 配置ID

        Returns:
            配置数据字典

        Raises:
            ValueError: 配置不存在
        """
        query = """
            SELECT
                id, name, display_name, strategy_type,
                config, config_hash, version,
                is_active, created_at, updated_at
            FROM strategy_configs
            WHERE id = %s
        """

        try:
            result = self.db.execute_query(query, (config_id,))

            if not result:
                raise ValueError(f"策略配置不存在: ID={config_id}")

            # 将查询结果转换为字典
            row = result[0]

            return {
                'id': row[0],
                'name': row[1],
                'display_name': row[2],
                'strategy_type': row[3],
                'config': row[4],  # JSONB字段会自动解析为dict
                'config_hash': row[5],
                'version': row[6],
                'is_active': row[7],
                'created_at': row[8],
                'updated_at': row[9],
            }

        except Exception as e:
            logger.error(f"加载策略配置失败: ID={config_id}, 错误: {e}")
            raise

    def reload_strategy(self, strategy_id: int):
        """
        重新加载策略（清除缓存后加载）

        Args:
            strategy_id: 策略ID

        Returns:
            新的策略实例
        """
        self.clear_cache(strategy_id)
        return self.load_strategy(strategy_id, use_cache=True)

    def batch_load_strategies(
        self,
        strategy_ids: list[int],
        use_cache: bool = True
    ) -> Dict[int, Any]:
        """
        批量加载策略

        Args:
            strategy_ids: 策略ID列表
            use_cache: 是否使用缓存

        Returns:
            {strategy_id: strategy_instance} 字典
        """
        strategies = {}

        for strategy_id in strategy_ids:
            try:
                strategy = self.load_strategy(strategy_id, use_cache=use_cache)
                strategies[strategy_id] = strategy
            except Exception as e:
                logger.error(f"加载策略失败: ID={strategy_id}, 错误: {e}")
                # 继续加载其他策略
                continue

        logger.info(f"批量加载完成: 成功 {len(strategies)}/{len(strategy_ids)}")

        return strategies

    def list_available_configs(
        self,
        active_only: bool = True,
        strategy_type: Optional[str] = None
    ) -> list[Dict[str, Any]]:
        """
        列出可用的策略配置

        Args:
            active_only: 只返回激活的配置
            strategy_type: 过滤策略类型

        Returns:
            配置列表
        """
        query = """
            SELECT
                id, name, display_name, strategy_type,
                version, is_active, created_at, updated_at
            FROM strategy_configs
            WHERE 1=1
        """

        params = []

        if active_only:
            query += " AND is_active = %s"
            params.append(True)

        if strategy_type:
            query += " AND strategy_type = %s"
            params.append(strategy_type)

        query += " ORDER BY updated_at DESC"

        try:
            results = self.db.execute_query(query, tuple(params))

            configs = []
            for row in results:
                configs.append({
                    'id': row[0],
                    'name': row[1],
                    'display_name': row[2],
                    'strategy_type': row[3],
                    'version': row[4],
                    'is_active': row[5],
                    'created_at': row[6],
                    'updated_at': row[7],
                })

            logger.info(f"查询到 {len(configs)} 个策略配置")
            return configs

        except Exception as e:
            logger.error(f"查询策略配置失败: {e}")
            return []

    def __repr__(self) -> str:
        return f"ConfigLoader(cached={len(self._cache)})"


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例：加载策略配置
    loader = ConfigLoader()

    try:
        # 加载单个策略
        strategy = loader.load_strategy(config_id=1)
        print(f"策略加载成功: {strategy}")

        # 批量加载
        strategies = loader.batch_load_strategies([1, 2, 3])
        print(f"批量加载: {len(strategies)} 个策略")

        # 列出可用配置
        configs = loader.list_available_configs(active_only=True)
        print(f"可用配置: {len(configs)} 个")

    except Exception as e:
        logger.error(f"示例执行失败: {e}")
