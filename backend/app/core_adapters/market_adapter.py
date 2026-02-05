"""
市场状态适配器 (Market Adapter)

将 Core 的市场工具模块包装为异步方法，供 FastAPI 使用。

核心功能:
- 判断市场状态
- 交易时段判断
- 下一交易时段查询
- 实时数据新鲜度判断

作者: Backend Team
创建日期: 2026-02-02
版本: 1.0.0
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


# 添加 core 项目到 Python 路径
core_path = Path(__file__).parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

# 导入 Core 模块
from src.utils.market_utils import MarketUtils

from app.core.cache import cache
from app.core.config import settings


class MarketAdapter:
    """
    Core 市场工具模块的异步适配器

    包装 Core 的 MarketUtils，将同步方法转换为异步方法。

    示例:
        >>> adapter = MarketAdapter()
        >>> status, desc = await adapter.get_market_status()
        >>> is_trading = await adapter.is_trading_time()
    """

    def __init__(self):
        """初始化市场适配器"""
        # MarketUtils 是静态工具类，不需要实例化

    async def is_trading_day(self, dt: Optional[datetime] = None) -> bool:
        """
        异步判断是否为交易日

        Args:
            dt: 日期时间，默认为当前时间

        Returns:
            是否为交易日
        """
        return await asyncio.to_thread(MarketUtils.is_trading_day, dt)

    async def is_trading_time(self, dt: Optional[datetime] = None) -> bool:
        """
        异步判断是否在交易时段内

        Args:
            dt: 日期时间，默认为当前时间

        Returns:
            是否在交易时段
        """
        return await asyncio.to_thread(MarketUtils.is_trading_time, dt)

    async def is_call_auction_time(self, dt: Optional[datetime] = None) -> bool:
        """
        异步判断是否在集合竞价时段

        Args:
            dt: 日期时间，默认为当前时间

        Returns:
            是否在集合竞价时段
        """
        return await asyncio.to_thread(MarketUtils.is_call_auction_time, dt)

    @cache.cached(ttl=settings.CACHE_MARKET_STATUS_TTL, key_prefix="market_status")
    async def get_market_status(self) -> Tuple[str, str]:
        """
        异步获取当前市场状态（带缓存）

        Returns:
            Tuple[str, str]: (状态码, 状态描述)
                - trading: 交易中
                - call_auction: 集合竞价
                - closed: 休市
                - after_hours: 盘后
                - pre_market: 盘前

        示例:
            >>> status, description = await adapter.get_market_status()
            >>> print(f"{status}: {description}")
            trading: 交易中（早盘）

        Note:
            缓存TTL: 1分钟（市场状态实时性要求高）
        """
        return await asyncio.to_thread(MarketUtils.get_market_status)

    async def should_refresh_realtime_data(
        self, last_update: Optional[datetime] = None, force: bool = False
    ) -> Tuple[bool, str]:
        """
        异步判断是否应该刷新实时数据

        Args:
            last_update: 上次更新时间
            force: 是否强制刷新

        Returns:
            Tuple[bool, str]: (是否应该刷新, 原因说明)

        示例:
            >>> should_refresh, reason = await adapter.should_refresh_realtime_data(
            ...     last_update=datetime(2023, 12, 29, 10, 30)
            ... )
            >>> print(f"需要刷新: {should_refresh}, 原因: {reason}")
            需要刷新: True, 原因: 实时行情更新
        """
        return await asyncio.to_thread(MarketUtils.should_refresh_realtime_data, last_update, force)

    async def get_next_trading_session(self) -> Tuple[Optional[datetime], str]:
        """
        异步获取下一个交易时段的开始时间

        Returns:
            Tuple[datetime, str]: (下次交易时间, 描述)

        示例:
            >>> next_time, desc = await adapter.get_next_trading_session()
            >>> print(f"{desc}: {next_time}")
            今日午盘开盘: 2023-12-29 13:00:00
        """
        return await asyncio.to_thread(MarketUtils.get_next_trading_session)

    # 交易时段常量（方便访问）
    @property
    def MORNING_OPEN(self):
        """早盘开盘时间"""
        return MarketUtils.MORNING_OPEN

    @property
    def MORNING_CLOSE(self):
        """早盘收盘时间"""
        return MarketUtils.MORNING_CLOSE

    @property
    def AFTERNOON_OPEN(self):
        """午盘开盘时间"""
        return MarketUtils.AFTERNOON_OPEN

    @property
    def AFTERNOON_CLOSE(self):
        """午盘收盘时间"""
        return MarketUtils.AFTERNOON_CLOSE

    @property
    def CALL_AUCTION_START(self):
        """集合竞价开始时间"""
        return MarketUtils.CALL_AUCTION_START

    @property
    def CALL_AUCTION_END(self):
        """集合竞价结束时间"""
        return MarketUtils.CALL_AUCTION_END
