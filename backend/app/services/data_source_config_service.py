"""
数据源配置服务

职责：
- Tushare Token 的读写与脱敏
- 全量同步最早日期的读写
"""

import asyncio
from typing import Dict, Optional

from loguru import logger
from src.database.db_manager import DatabaseManager

from app.core.exceptions import ConfigError, DatabaseError
from app.repositories.config_repository import ConfigRepository


class DataSourceConfigService:
    """Tushare Token 及全量同步起始日期的配置管理。"""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.config_repo = ConfigRepository(db)

    @staticmethod
    def _mask_token(token: str) -> str:
        """脱敏 Token，仅保留首尾各 4 位，中间替换为星号。"""
        if not token:
            return ""
        if len(token) <= 8:
            return "*" * len(token)
        return f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}"

    async def get_data_source_config(self, mask_token: bool = True) -> Dict:
        """
        获取数据源配置。

        Returns:
            Dict: 包含 tushare_token（脱敏）和 earliest_history_date
        """
        try:
            configs = await asyncio.to_thread(
                self.config_repo.get_configs_by_keys,
                ["tushare_token", "earliest_history_date"],
            )
            raw_token = configs.get("tushare_token") or ""
            return {
                "tushare_token": self._mask_token(raw_token) if mask_token else raw_token,
                "earliest_history_date": configs.get("earliest_history_date") or "2021-01-04",
            }
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"获取数据源配置失败: {e}")
            raise ConfigError(
                "数据源配置获取失败", error_code="DATA_SOURCE_CONFIG_FETCH_FAILED", reason=str(e)
            )

    async def get_tushare_token(self) -> str:
        """获取未脱敏的 Tushare Token（供内部服务使用）。"""
        config = await self.get_data_source_config(mask_token=False)
        return config["tushare_token"]

    async def update_data_source(
        self,
        tushare_token: Optional[str] = None,
        earliest_history_date: Optional[str] = None,
    ) -> Dict:
        """
        更新数据源配置。Token 为 None 时保持原值不变。

        Returns:
            Dict: 更新后的配置（Token 已脱敏）
        """
        try:
            updates = {}
            if tushare_token:
                updates["tushare_token"] = tushare_token
            if earliest_history_date:
                updates["earliest_history_date"] = earliest_history_date

            if updates:
                await asyncio.to_thread(self.config_repo.set_configs_batch, updates)
                logger.info(f"✓ 数据源配置已更新: {list(updates.keys())}")

            return await self.get_data_source_config()

        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"更新数据源配置失败: {e}")
            raise ConfigError(
                "数据源配置更新失败",
                error_code="DATA_SOURCE_UPDATE_FAILED",
                reason=str(e),
            )
