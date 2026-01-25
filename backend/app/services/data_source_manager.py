"""
数据源管理器
负责数据源配置的验证和管理
"""

import asyncio
from typing import Dict, Optional
from loguru import logger
from src.database.db_manager import DatabaseManager

from app.repositories.config_repository import ConfigRepository


class DataSourceManager:
    """
    数据源管理器

    职责：
    - 数据源配置验证
    - 数据源切换逻辑
    - Token 管理
    - 数据源配置查询
    """

    # 支持的数据源列表
    SUPPORTED_SOURCES = ['akshare', 'tushare']

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化数据源管理器

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.config_repo = ConfigRepository(db)

    # ==================== 数据源配置查询 ====================

    async def get_data_source_config(self) -> Dict:
        """
        获取数据源配置

        Returns:
            Dict: 包含 data_source、minute_data_source、realtime_data_source 和 tushare_token
        """
        try:
            keys = [
                'data_source',
                'minute_data_source',
                'realtime_data_source',
                'tushare_token'
            ]

            configs = await asyncio.to_thread(
                self.config_repo.get_configs_by_keys,
                keys
            )

            return {
                'data_source': configs.get('data_source') or 'akshare',
                'minute_data_source': configs.get('minute_data_source') or 'akshare',
                'realtime_data_source': configs.get('realtime_data_source') or 'akshare',
                'tushare_token': configs.get('tushare_token') or ''
            }

        except Exception as e:
            logger.error(f"获取数据源配置失败: {e}")
            raise

    async def get_data_source(self) -> str:
        """
        获取主数据源

        Returns:
            数据源名称
        """
        config = await self.get_data_source_config()
        return config['data_source']

    async def get_minute_data_source(self) -> str:
        """
        获取分时数据源

        Returns:
            数据源名称
        """
        config = await self.get_data_source_config()
        return config['minute_data_source']

    async def get_realtime_data_source(self) -> str:
        """
        获取实时数据源

        Returns:
            数据源名称
        """
        config = await self.get_data_source_config()
        return config['realtime_data_source']

    async def get_tushare_token(self) -> str:
        """
        获取 Tushare Token

        Returns:
            Token 字符串
        """
        config = await self.get_data_source_config()
        return config['tushare_token']

    # ==================== 数据源验证 ====================

    def validate_data_source(self, source: str) -> bool:
        """
        验证数据源是否支持

        Args:
            source: 数据源名称

        Returns:
            是否支持

        Raises:
            ValueError: 不支持的数据源
        """
        if source not in self.SUPPORTED_SOURCES:
            raise ValueError(f"不支持的数据源: {source}，支持的数据源: {', '.join(self.SUPPORTED_SOURCES)}")
        return True

    async def validate_tushare_config(
        self,
        data_source: str,
        token: Optional[str] = None
    ) -> bool:
        """
        验证 Tushare 配置

        Args:
            data_source: 数据源名称
            token: Tushare Token

        Returns:
            是否有效

        Raises:
            ValueError: Tushare 配置无效
        """
        if data_source == 'tushare':
            if not token:
                # 检查是否已有 Token
                current_token = await self.get_tushare_token()
                if not current_token:
                    raise ValueError("切换到 Tushare 需要提供 Token")
        return True

    # ==================== 数据源更新 ====================

    async def update_data_source(
        self,
        data_source: str,
        minute_data_source: Optional[str] = None,
        realtime_data_source: Optional[str] = None,
        tushare_token: Optional[str] = None
    ) -> Dict:
        """
        更新数据源配置

        Args:
            data_source: 主数据源 ('akshare' 或 'tushare')，用于历史数据、股票列表等
            minute_data_source: 分时数据源 ('akshare' 或 'tushare')，用于分时K线
            realtime_data_source: 实时数据源 ('akshare' 或 'tushare')，用于实时行情
            tushare_token: Tushare Token (可选)

        Returns:
            Dict: 更新后的配置

        Raises:
            ValueError: 配置验证失败
        """
        try:
            # 验证主数据源
            self.validate_data_source(data_source)

            # 验证分时数据源
            if minute_data_source:
                self.validate_data_source(minute_data_source)

            # 验证实时数据源
            if realtime_data_source:
                self.validate_data_source(realtime_data_source)

            # 验证 Tushare 配置
            await self.validate_tushare_config(data_source, tushare_token)

            # 准备更新
            updates = {'data_source': data_source}

            if minute_data_source:
                updates['minute_data_source'] = minute_data_source

            if realtime_data_source:
                updates['realtime_data_source'] = realtime_data_source

            if tushare_token:
                updates['tushare_token'] = tushare_token

            # 批量更新
            await asyncio.to_thread(
                self.config_repo.set_configs_batch,
                updates
            )

            logger.info(
                f"✓ 数据源已更新: "
                f"主数据源={data_source}, "
                f"分时数据源={minute_data_source or '未更改'}, "
                f"实时数据源={realtime_data_source or '未更改'}"
            )

            return await self.get_data_source_config()

        except Exception as e:
            logger.error(f"更新数据源配置失败: {e}")
            raise

    async def set_data_source(self, source: str) -> Dict:
        """
        设置主数据源

        Args:
            source: 数据源名称

        Returns:
            更新后的配置
        """
        return await self.update_data_source(data_source=source)

    async def set_tushare_token(self, token: str) -> Dict:
        """
        设置 Tushare Token

        Args:
            token: Token 字符串

        Returns:
            更新后的配置
        """
        try:
            await asyncio.to_thread(
                self.config_repo.set_config_value,
                'tushare_token',
                token
            )

            logger.info("✓ Tushare Token 已更新")

            return await self.get_data_source_config()

        except Exception as e:
            logger.error(f"设置 Tushare Token 失败: {e}")
            raise

    # ==================== 便捷方法 ====================

    async def is_using_tushare(self) -> bool:
        """
        检查是否正在使用 Tushare

        Returns:
            是否使用 Tushare
        """
        source = await self.get_data_source()
        return source == 'tushare'

    async def is_using_akshare(self) -> bool:
        """
        检查是否正在使用 AkShare

        Returns:
            是否使用 AkShare
        """
        source = await self.get_data_source()
        return source == 'akshare'

    async def switch_to_tushare(self, token: str) -> Dict:
        """
        切换到 Tushare

        Args:
            token: Tushare Token

        Returns:
            更新后的配置
        """
        return await self.update_data_source(
            data_source='tushare',
            tushare_token=token
        )

    async def switch_to_akshare(self) -> Dict:
        """
        切换到 AkShare

        Returns:
            更新后的配置
        """
        return await self.update_data_source(data_source='akshare')
