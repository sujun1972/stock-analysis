"""
数据源配置服务
管理数据源配置（从 DataSourceManager 重构）

职责：
1. 数据源配置的读写操作
2. 数据源切换逻辑
3. Token 管理和验证
4. 数据源配置查询

重构说明：
- 从 DataSourceManager 重命名和重构
- 更符合 Service 层命名规范
- 保持与 DataSourceManager 的接口兼容性
"""

import asyncio
from typing import Dict, Optional

from loguru import logger
from src.database.db_manager import DatabaseManager

from app.core.exceptions import ConfigError, DatabaseError
from app.repositories.config_repository import ConfigRepository


class DataSourceConfigService:
    """
    数据源配置服务（重构自 DataSourceManager）

    职责：
    - 数据源配置验证
    - 数据源切换逻辑
    - Token 管理
    - 数据源配置查询
    """

    # 支持的数据源列表
    SUPPORTED_SOURCES = ["akshare", "tushare"]

    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化数据源配置服务

        Args:
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.config_repo = ConfigRepository(db)
        logger.debug("✓ DataSourceConfigService initialized")

    # ==================== 数据源配置查询 ====================

    @staticmethod
    def _mask_token(token: str) -> str:
        """
        脱敏 Token（仅用于返回给前端显示）

        安全策略：
        - 短Token（<=8字符）：全部替换为星号
        - 长Token（>8字符）：仅保留前4位和后4位，中间用星号替换
        - 例如：d038...f3ad (48字符) -> d038****************f3ad

        Args:
            token: 原始 Token

        Returns:
            脱敏后的 Token
        """
        if not token:
            return ""
        if len(token) <= 8:
            return "*" * len(token)
        return f"{token[:4]}{'*' * (len(token) - 8)}{token[-4:]}"

    async def get_data_source_config(self, mask_token: bool = True) -> Dict:
        """
        获取数据源配置

        Args:
            mask_token: 是否对 Token 进行脱敏处理（默认 True）

        Returns:
            Dict: 包含所有数据源配置
        """
        try:
            keys = [
                "data_source",
                "minute_data_source",
                "realtime_data_source",
                "limit_up_data_source",
                "top_list_data_source",
                "premarket_data_source",
                "concept_data_source",
                "sentiment_data_source",
                "tushare_token"
            ]

            configs = await asyncio.to_thread(self.config_repo.get_configs_by_keys, keys)

            # 获取原始 Token
            raw_token = configs.get("tushare_token") or ""

            return {
                "data_source": configs.get("data_source") or "akshare",
                "minute_data_source": configs.get("minute_data_source") or "akshare",
                "realtime_data_source": configs.get("realtime_data_source") or "akshare",
                "limit_up_data_source": configs.get("limit_up_data_source") or "tushare",  # 默认tushare（用户有5000积分）
                "top_list_data_source": configs.get("top_list_data_source") or "tushare",  # 默认tushare
                "premarket_data_source": configs.get("premarket_data_source") or "akshare",  # 默认akshare（外盘数据）
                "concept_data_source": configs.get("concept_data_source") or "akshare",  # 默认akshare（免费且数据丰富）
                "sentiment_data_source": configs.get("sentiment_data_source") or "akshare",  # 默认akshare（免费，推荐切换为tushare避免反爬）
                "tushare_token": self._mask_token(raw_token) if mask_token else raw_token,
            }

        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"获取数据源配置失败: {e}")
            raise ConfigError(
                "数据源配置获取失败", error_code="DATA_SOURCE_CONFIG_FETCH_FAILED", reason=str(e)
            )

    async def get_data_source(self) -> str:
        """
        获取主数据源

        Returns:
            数据源名称
        """
        config = await self.get_data_source_config()
        return config["data_source"]

    async def get_minute_data_source(self) -> str:
        """
        获取分时数据源

        Returns:
            数据源名称
        """
        config = await self.get_data_source_config()
        return config["minute_data_source"]

    async def get_realtime_data_source(self) -> str:
        """
        获取实时数据源

        Returns:
            数据源名称
        """
        config = await self.get_data_source_config()
        return config["realtime_data_source"]

    async def get_concept_data_source(self) -> str:
        """
        获取概念数据源

        Returns:
            数据源名称
        """
        config = await self.get_data_source_config()
        return config["concept_data_source"]

    async def get_tushare_token(self) -> str:
        """
        获取 Tushare Token（内部使用，不脱敏）

        Returns:
            Token 字符串
        """
        config = await self.get_data_source_config(mask_token=False)
        return config["tushare_token"]

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
            raise ValueError(
                f"不支持的数据源: {source}，支持的数据源: {', '.join(self.SUPPORTED_SOURCES)}"
            )
        return True

    async def validate_tushare_config(self, data_source: str, token: Optional[str] = None) -> bool:
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
        if data_source == "tushare":
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
        limit_up_data_source: Optional[str] = None,
        top_list_data_source: Optional[str] = None,
        premarket_data_source: Optional[str] = None,
        concept_data_source: Optional[str] = None,
        sentiment_data_source: Optional[str] = None,
        tushare_token: Optional[str] = None,
    ) -> Dict:
        """
        更新数据源配置

        支持8种数据源的独立配置：
        1. 主数据源：日线数据、股票列表等
        2. 分时数据源：分钟级K线数据
        3. 实时数据源：实时行情数据
        4. 涨停板池数据源：涨停板池数据
        5. 龙虎榜数据源：龙虎榜数据
        6. 盘前数据源：盘前外盘数据
        7. 概念数据源：概念板块数据
        8. 市场情绪数据源：大盘指数数据

        安全特性：
        - Token留空不修改：如果tushare_token为None，则保持原有Token不变
        - Token掩码：返回给前端的Token自动掩码处理

        Args:
            data_source: 主数据源 ('akshare' 或 'tushare')
            minute_data_source: 分时数据源（可选）
            realtime_data_source: 实时数据源（可选）
            limit_up_data_source: 涨停板池数据源（可选）
            top_list_data_source: 龙虎榜数据源（可选）
            premarket_data_source: 盘前数据源（可选）
            concept_data_source: 概念数据源（可选）
            sentiment_data_source: 市场情绪数据源（可选）
            tushare_token: Tushare Token（可选，留空不修改原有Token）

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

            # 验证涨停板池数据源
            if limit_up_data_source:
                self.validate_data_source(limit_up_data_source)

            # 验证龙虎榜数据源
            if top_list_data_source:
                self.validate_data_source(top_list_data_source)

            # 验证盘前数据源
            if premarket_data_source:
                self.validate_data_source(premarket_data_source)

            # 验证概念数据源
            if concept_data_source:
                self.validate_data_source(concept_data_source)

            # 验证市场情绪数据源
            if sentiment_data_source:
                self.validate_data_source(sentiment_data_source)

            # 验证 Tushare 配置
            await self.validate_tushare_config(data_source, tushare_token)

            # 准备更新
            updates = {"data_source": data_source}

            if minute_data_source:
                updates["minute_data_source"] = minute_data_source

            if realtime_data_source:
                updates["realtime_data_source"] = realtime_data_source

            if limit_up_data_source:
                updates["limit_up_data_source"] = limit_up_data_source

            if top_list_data_source:
                updates["top_list_data_source"] = top_list_data_source

            if premarket_data_source:
                updates["premarket_data_source"] = premarket_data_source

            if concept_data_source:
                updates["concept_data_source"] = concept_data_source

            if sentiment_data_source:
                updates["sentiment_data_source"] = sentiment_data_source

            if tushare_token:
                updates["tushare_token"] = tushare_token

            # 批量更新
            await asyncio.to_thread(self.config_repo.set_configs_batch, updates)

            logger.info(
                f"✓ 数据源已更新: "
                f"主数据源={data_source}, "
                f"分时={minute_data_source or '未更改'}, "
                f"实时={realtime_data_source or '未更改'}, "
                f"涨停板={limit_up_data_source or '未更改'}, "
                f"龙虎榜={top_list_data_source or '未更改'}, "
                f"盘前={premarket_data_source or '未更改'}, "
                f"概念={concept_data_source or '未更改'}"
            )

            return await self.get_data_source_config()

        except ValueError as e:
            # 验证错误（不支持的数据源、Token缺失等）
            raise ConfigError(
                str(e), error_code="DATA_SOURCE_VALIDATION_FAILED", data_source=data_source
            )
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"更新数据源配置失败: {e}")
            raise ConfigError(
                "数据源配置更新失败",
                error_code="DATA_SOURCE_UPDATE_FAILED",
                data_source=data_source,
                reason=str(e),
            )

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
            await asyncio.to_thread(self.config_repo.set_config_value, "tushare_token", token)

            logger.info("✓ Tushare Token 已更新")

            return await self.get_data_source_config()

        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            logger.error(f"设置 Tushare Token 失败: {e}")
            raise ConfigError(
                "Tushare Token 设置失败", error_code="TUSHARE_TOKEN_UPDATE_FAILED", reason=str(e)
            )

    # ==================== 便捷方法 ====================

    async def is_using_tushare(self) -> bool:
        """
        检查是否正在使用 Tushare

        Returns:
            是否使用 Tushare
        """
        source = await self.get_data_source()
        return source == "tushare"

    async def is_using_akshare(self) -> bool:
        """
        检查是否正在使用 AkShare

        Returns:
            是否使用 AkShare
        """
        source = await self.get_data_source()
        return source == "akshare"

    async def switch_to_tushare(self, token: str) -> Dict:
        """
        切换到 Tushare

        Args:
            token: Tushare Token

        Returns:
            更新后的配置
        """
        return await self.update_data_source(data_source="tushare", tushare_token=token)

    async def switch_to_akshare(self) -> Dict:
        """
        切换到 AkShare

        Returns:
            更新后的配置
        """
        return await self.update_data_source(data_source="akshare")
