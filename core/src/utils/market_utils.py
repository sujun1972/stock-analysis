#!/usr/bin/env python3
"""
市场工具模块
提供交易时段判断、交易日历等功能
"""

from datetime import datetime, time, timedelta
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class MarketUtils:
    """市场工具类"""

    # A股交易时段
    MORNING_OPEN = time(9, 30)      # 早盘开盘
    MORNING_CLOSE = time(11, 30)    # 早盘收盘
    AFTERNOON_OPEN = time(13, 0)    # 午盘开盘
    AFTERNOON_CLOSE = time(15, 0)   # 午盘收盘

    # 集合竞价时段
    CALL_AUCTION_START = time(9, 15)   # 集合竞价开始
    CALL_AUCTION_END = time(9, 25)     # 集合竞价结束

    @staticmethod
    def is_trading_day(dt: datetime = None) -> bool:
        """
        判断是否为交易日（简化版本，仅判断工作日）

        Args:
            dt: 日期时间，默认为当前时间

        Returns:
            bool: 是否为交易日

        Note:
            完整版本应该查询交易日历数据库，这里简化为排除周末
        """
        dt = dt or datetime.now()
        # 周一到周五（0-4）
        return dt.weekday() < 5

    @staticmethod
    def is_trading_time(dt: datetime = None) -> bool:
        """
        判断是否在交易时段内

        Args:
            dt: 日期时间，默认为当前时间

        Returns:
            bool: 是否在交易时段
        """
        dt = dt or datetime.now()

        # 首先判断是否为交易日
        if not MarketUtils.is_trading_day(dt):
            return False

        current_time = dt.time()

        # 判断是否在早盘或午盘时段
        in_morning = MarketUtils.MORNING_OPEN <= current_time <= MarketUtils.MORNING_CLOSE
        in_afternoon = MarketUtils.AFTERNOON_OPEN <= current_time <= MarketUtils.AFTERNOON_CLOSE

        return in_morning or in_afternoon

    @staticmethod
    def is_call_auction_time(dt: datetime = None) -> bool:
        """
        判断是否在集合竞价时段

        Args:
            dt: 日期时间，默认为当前时间

        Returns:
            bool: 是否在集合竞价时段
        """
        dt = dt or datetime.now()

        if not MarketUtils.is_trading_day(dt):
            return False

        current_time = dt.time()
        return MarketUtils.CALL_AUCTION_START <= current_time <= MarketUtils.CALL_AUCTION_END

    @staticmethod
    def get_market_status() -> Tuple[str, str]:
        """
        获取当前市场状态

        Returns:
            Tuple[str, str]: (状态码, 状态描述)
                - trading: 交易中
                - call_auction: 集合竞价
                - closed: 休市
                - after_hours: 盘后
                - pre_market: 盘前
        """
        now = datetime.now()
        current_time = now.time()

        # 非交易日
        if not MarketUtils.is_trading_day(now):
            return 'closed', '休市（周末或节假日）'

        # 集合竞价时段
        if MarketUtils.is_call_auction_time(now):
            return 'call_auction', '集合竞价'

        # 早盘交易时段
        if MarketUtils.MORNING_OPEN <= current_time <= MarketUtils.MORNING_CLOSE:
            return 'trading', '交易中（早盘）'

        # 午间休市
        if MarketUtils.MORNING_CLOSE < current_time < MarketUtils.AFTERNOON_OPEN:
            return 'closed', '午间休市'

        # 午盘交易时段
        if MarketUtils.AFTERNOON_OPEN <= current_time <= MarketUtils.AFTERNOON_CLOSE:
            return 'trading', '交易中（午盘）'

        # 盘后（15:00之后到23:59）
        if current_time > MarketUtils.AFTERNOON_CLOSE:
            return 'after_hours', '盘后'

        # 盘前（00:00到09:15之前）
        if current_time < MarketUtils.CALL_AUCTION_START:
            return 'pre_market', '盘前'

        return 'closed', '休市'

    @staticmethod
    def should_refresh_realtime_data(last_update: datetime = None, force: bool = False) -> Tuple[bool, str]:
        """
        判断是否应该刷新实时数据

        Args:
            last_update: 上次更新时间
            force: 是否强制刷新

        Returns:
            Tuple[bool, str]: (是否应该刷新, 原因说明)
        """
        if force:
            return True, '用户强制刷新'

        now = datetime.now()
        market_status, status_desc = MarketUtils.get_market_status()

        # 没有上次更新记录，需要刷新
        if last_update is None:
            return True, '首次加载'

        # 检查数据是否是今天的
        # 如果是盘后时间，但数据不是今天的，说明还没有获取今日收盘数据
        if market_status == 'after_hours':
            data_date = last_update.date()
            today = now.date()

            if data_date < today:
                return True, f'数据日期过旧（{data_date}），需要更新今日数据'

            # 如果数据是今天的，检查是否是收盘后的数据
            # 收盘时间是15:00，如果数据更新时间早于14:50，可能没有收盘价
            if last_update.time() < time(14, 50):
                return True, '盘后数据不完整，需要获取收盘价'

            # 数据是今天的且是收盘后更新的，不需要刷新
            return False, f'{status_desc}，今日数据已是最新'

        # 盘前时间：如果数据不是昨天或更早的，不需要刷新
        if market_status == 'pre_market':
            # 盘前时间应该显示昨日收盘数据，检查数据是否足够新
            days_old = (now.date() - last_update.date()).days

            if days_old > 3:
                return True, f'数据已过期{days_old}天，需要更新'

            return False, f'{status_desc}，显示昨日收盘数据'

        # 周末或节假日
        if market_status == 'closed':
            # 非交易日，检查数据是否过于陈旧（超过7天）
            days_old = (now.date() - last_update.date()).days

            if days_old > 7:
                return True, f'数据已过期{days_old}天'

            return False, f'{status_desc}，无需刷新'

        # 交易时段或集合竞价，需要刷新

        # 计算距离上次更新的时间
        time_diff = (now - last_update).total_seconds()

        # 集合竞价时段：每30秒刷新一次
        if market_status == 'call_auction':
            if time_diff >= 30:
                return True, '集合竞价数据更新'
            else:
                return False, f'数据仍然新鲜（{int(time_diff)}秒前更新）'

        # 交易时段：每3秒刷新一次（避免过于频繁）
        if market_status == 'trading':
            if time_diff >= 3:
                return True, '实时行情更新'
            else:
                return False, f'数据仍然新鲜（{int(time_diff)}秒前更新）'

        return False, '无需刷新'

    @staticmethod
    def get_next_trading_session() -> Tuple[datetime, str]:
        """
        获取下一个交易时段的开始时间

        Returns:
            Tuple[datetime, str]: (下次交易时间, 描述)
        """
        now = datetime.now()
        current_time = now.time()

        # 如果是交易日
        if MarketUtils.is_trading_day(now):
            # 盘前，等待集合竞价
            if current_time < MarketUtils.CALL_AUCTION_START:
                next_time = datetime.combine(now.date(), MarketUtils.CALL_AUCTION_START)
                return next_time, '今日集合竞价开始'

            # 集合竞价到早盘开盘之间
            if MarketUtils.CALL_AUCTION_START <= current_time < MarketUtils.MORNING_OPEN:
                next_time = datetime.combine(now.date(), MarketUtils.MORNING_OPEN)
                return next_time, '今日早盘开盘'

            # 早盘时段
            if MarketUtils.MORNING_OPEN <= current_time <= MarketUtils.MORNING_CLOSE:
                next_time = datetime.combine(now.date(), MarketUtils.AFTERNOON_OPEN)
                return next_time, '今日午盘开盘'

            # 午间休市
            if MarketUtils.MORNING_CLOSE < current_time < MarketUtils.AFTERNOON_OPEN:
                next_time = datetime.combine(now.date(), MarketUtils.AFTERNOON_OPEN)
                return next_time, '今日午盘开盘'

            # 午盘时段或盘后
            if current_time >= MarketUtils.AFTERNOON_OPEN:
                # 找到下一个交易日
                next_day = now + timedelta(days=1)
                while not MarketUtils.is_trading_day(next_day):
                    next_day += timedelta(days=1)
                next_time = datetime.combine(next_day.date(), MarketUtils.CALL_AUCTION_START)
                return next_time, '下一交易日集合竞价'

        # 如果不是交易日，找到下一个交易日
        next_day = now + timedelta(days=1)
        while not MarketUtils.is_trading_day(next_day):
            next_day += timedelta(days=1)
        next_time = datetime.combine(next_day.date(), MarketUtils.CALL_AUCTION_START)
        return next_time, '下一交易日集合竞价'
