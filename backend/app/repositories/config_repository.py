"""
Config Repository
管理系统配置的数据访问
"""

from typing import Dict, List, Optional

from loguru import logger

from .base_repository import BaseRepository


class ConfigRepository(BaseRepository):
    """配置数据访问层"""

    def get_config_value(self, key: str) -> Optional[str]:
        """
        获取单个配置值

        Args:
            key: 配置键名

        Returns:
            配置值，不存在则返回 None
        """
        query = """
            SELECT config_value
            FROM system_config
            WHERE config_key = %s
        """

        result = self.execute_query(query, (key,))

        if result and len(result) > 0:
            return result[0][0]

        return None

    def get_all_configs(self) -> Dict[str, Dict[str, str]]:
        """
        获取所有配置

        Returns:
            配置字典 {key: {value, description}}
        """
        query = """
            SELECT config_key, config_value, description
            FROM system_config
            ORDER BY config_key
        """

        result = self.execute_query(query)

        configs = {}
        for row in result:
            configs[row[0]] = {"value": row[1], "description": row[2]}

        return configs

    def set_config_value(self, key: str, value: str, description: str = "") -> int:
        """
        设置单个配置值（使用 UPSERT，如果不存在则插入，存在则更新）

        Args:
            key: 配置键名
            value: 配置值
            description: 配置描述（仅在插入时使用）

        Returns:
            受影响的行数
        """
        query = """
            INSERT INTO system_config (config_key, config_value, description, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (config_key)
            DO UPDATE SET
                config_value = EXCLUDED.config_value,
                updated_at = CURRENT_TIMESTAMP
        """

        rows = self.execute_update(query, (key, value, description))

        if rows > 0:
            logger.info(f"✓ 更新配置: {key} = {value}")

        return rows

    def get_configs_by_keys(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """
        批量获取配置值

        Args:
            keys: 配置键名列表

        Returns:
            配置字典 {key: value}
        """
        if not keys:
            return {}

        placeholders = ", ".join(["%s"] * len(keys))
        query = f"""
            SELECT config_key, config_value
            FROM system_config
            WHERE config_key IN ({placeholders})
        """

        result = self.execute_query(query, tuple(keys))

        # 初始化所有键为 None
        configs = {key: None for key in keys}

        # 填充查询结果
        for row in result:
            configs[row[0]] = row[1]

        return configs

    def set_configs_batch(self, configs: Dict[str, str]) -> int:
        """
        批量设置配置值

        Args:
            configs: 配置字典 {key: value}

        Returns:
            受影响的行数总计
        """
        if not configs:
            return 0

        total_rows = 0
        for key, value in configs.items():
            total_rows += self.set_config_value(key, value)

        return total_rows

    def config_exists(self, key: str) -> bool:
        """
        检查配置是否存在

        Args:
            key: 配置键名

        Returns:
            是否存在
        """
        return self.exists(table="system_config", where="config_key = %s", params=(key,))
