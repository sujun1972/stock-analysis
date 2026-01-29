"""
市场工具模块测试
测试 market_utils.py 中的所有功能
"""
import pytest
from datetime import datetime, time, timedelta
from unittest.mock import patch

from src.utils.market_utils import MarketUtils


class TestIsTradingDay:
    """测试交易日判断"""

    def test_monday_is_trading_day(self):
        """测试周一是交易日"""
        # 2024-01-01 是星期一
        monday = datetime(2024, 1, 1)
        assert MarketUtils.is_trading_day(monday) is True

    def test_tuesday_is_trading_day(self):
        """测试周二是交易日"""
        tuesday = datetime(2024, 1, 2)
        assert MarketUtils.is_trading_day(tuesday) is True

    def test_wednesday_is_trading_day(self):
        """测试周三是交易日"""
        wednesday = datetime(2024, 1, 3)
        assert MarketUtils.is_trading_day(wednesday) is True

    def test_thursday_is_trading_day(self):
        """测试周四是交易日"""
        thursday = datetime(2024, 1, 4)
        assert MarketUtils.is_trading_day(thursday) is True

    def test_friday_is_trading_day(self):
        """测试周五是交易日"""
        friday = datetime(2024, 1, 5)
        assert MarketUtils.is_trading_day(friday) is True

    def test_saturday_not_trading_day(self):
        """测试周六不是交易日"""
        # 2024-01-06 是星期六
        saturday = datetime(2024, 1, 6)
        assert MarketUtils.is_trading_day(saturday) is False

    def test_sunday_not_trading_day(self):
        """测试周日不是交易日"""
        # 2024-01-07 是星期日
        sunday = datetime(2024, 1, 7)
        assert MarketUtils.is_trading_day(sunday) is False

    def test_default_parameter_uses_current_time(self):
        """测试默认参数使用当前时间"""
        with patch('src.utils.market_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1)  # Monday
            result = MarketUtils.is_trading_day()
            assert result is True


class TestIsTradingTime:
    """测试交易时段判断"""

    def test_morning_session_start(self):
        """测试早盘开盘时间"""
        dt = datetime(2024, 1, 1, 9, 30)  # Monday 9:30
        assert MarketUtils.is_trading_time(dt) is True

    def test_morning_session_mid(self):
        """测试早盘中间时段"""
        dt = datetime(2024, 1, 1, 10, 30)  # Monday 10:30
        assert MarketUtils.is_trading_time(dt) is True

    def test_morning_session_end(self):
        """测试早盘结束时间"""
        dt = datetime(2024, 1, 1, 11, 30)  # Monday 11:30
        assert MarketUtils.is_trading_time(dt) is True

    def test_lunch_break(self):
        """测试午间休市"""
        dt = datetime(2024, 1, 1, 12, 0)  # Monday 12:00
        assert MarketUtils.is_trading_time(dt) is False

    def test_afternoon_session_start(self):
        """测试午盘开盘时间"""
        dt = datetime(2024, 1, 1, 13, 0)  # Monday 13:00
        assert MarketUtils.is_trading_time(dt) is True

    def test_afternoon_session_mid(self):
        """测试午盘中间时段"""
        dt = datetime(2024, 1, 1, 14, 0)  # Monday 14:00
        assert MarketUtils.is_trading_time(dt) is True

    def test_afternoon_session_end(self):
        """测试午盘结束时间"""
        dt = datetime(2024, 1, 1, 15, 0)  # Monday 15:00
        assert MarketUtils.is_trading_time(dt) is True

    def test_after_market_close(self):
        """测试盘后时间"""
        dt = datetime(2024, 1, 1, 16, 0)  # Monday 16:00
        assert MarketUtils.is_trading_time(dt) is False

    def test_before_market_open(self):
        """测试盘前时间"""
        dt = datetime(2024, 1, 1, 8, 0)  # Monday 8:00
        assert MarketUtils.is_trading_time(dt) is False

    def test_weekend_morning(self):
        """测试周末早上"""
        dt = datetime(2024, 1, 6, 10, 0)  # Saturday 10:00
        assert MarketUtils.is_trading_time(dt) is False

    def test_weekend_afternoon(self):
        """测试周末下午"""
        dt = datetime(2024, 1, 7, 14, 0)  # Sunday 14:00
        assert MarketUtils.is_trading_time(dt) is False

    def test_default_parameter(self):
        """测试默认参数"""
        with patch('src.utils.market_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0)  # Monday 10:00
            result = MarketUtils.is_trading_time()
            assert result is True


class TestIsCallAuctionTime:
    """测试集合竞价时段判断"""

    def test_call_auction_start(self):
        """测试集合竞价开始时间"""
        dt = datetime(2024, 1, 1, 9, 15)  # Monday 9:15
        assert MarketUtils.is_call_auction_time(dt) is True

    def test_call_auction_mid(self):
        """测试集合竞价中间时段"""
        dt = datetime(2024, 1, 1, 9, 20)  # Monday 9:20
        assert MarketUtils.is_call_auction_time(dt) is True

    def test_call_auction_end(self):
        """测试集合竞价结束时间"""
        dt = datetime(2024, 1, 1, 9, 25)  # Monday 9:25
        assert MarketUtils.is_call_auction_time(dt) is True

    def test_before_call_auction(self):
        """测试集合竞价前"""
        dt = datetime(2024, 1, 1, 9, 10)  # Monday 9:10
        assert MarketUtils.is_call_auction_time(dt) is False

    def test_after_call_auction(self):
        """测试集合竞价后（开盘前）"""
        dt = datetime(2024, 1, 1, 9, 26)  # Monday 9:26
        assert MarketUtils.is_call_auction_time(dt) is False

    def test_weekend_call_auction_time(self):
        """测试周末的集合竞价时间"""
        dt = datetime(2024, 1, 6, 9, 20)  # Saturday 9:20
        assert MarketUtils.is_call_auction_time(dt) is False

    def test_default_parameter(self):
        """测试默认参数"""
        with patch('src.utils.market_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 9, 20)  # Monday 9:20
            result = MarketUtils.is_call_auction_time()
            assert result is True


class TestGetMarketStatus:
    """测试市场状态获取"""

    def test_status_pre_market(self):
        """测试盘前状态"""
        with patch('src.utils.market_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 8, 0)  # Monday 8:00
            status, desc = MarketUtils.get_market_status()
            assert status == 'pre_market'
            assert '盘前' in desc

    def test_status_call_auction(self):
        """测试集合竞价状态"""
        with patch('src.utils.market_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 9, 20)  # Monday 9:20
            status, desc = MarketUtils.get_market_status()
            assert status == 'call_auction'
            assert '集合竞价' in desc

    def test_status_morning_trading(self):
        """测试早盘交易状态"""
        with patch('src.utils.market_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0)  # Monday 10:00
            status, desc = MarketUtils.get_market_status()
            assert status == 'trading'
            assert '交易中' in desc
            assert '早盘' in desc

    def test_status_lunch_break(self):
        """测试午间休市状态"""
        with patch('src.utils.market_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0)  # Monday 12:00
            status, desc = MarketUtils.get_market_status()
            assert status == 'closed'
            assert '午间休市' in desc

    def test_status_afternoon_trading(self):
        """测试午盘交易状态"""
        with patch('src.utils.market_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 14, 0)  # Monday 14:00
            status, desc = MarketUtils.get_market_status()
            assert status == 'trading'
            assert '交易中' in desc
            assert '午盘' in desc

    def test_status_after_hours(self):
        """测试盘后状态"""
        with patch('src.utils.market_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 16, 0)  # Monday 16:00
            status, desc = MarketUtils.get_market_status()
            assert status == 'after_hours'
            assert '盘后' in desc

    def test_status_weekend(self):
        """测试周末休市状态"""
        with patch('src.utils.market_utils.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 6, 10, 0)  # Saturday 10:00
            status, desc = MarketUtils.get_market_status()
            assert status == 'closed'
            assert '休市' in desc


class TestShouldRefreshRealtimeData:
    """测试实时数据刷新判断"""

    def test_force_refresh(self):
        """测试强制刷新"""
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(
            last_update=datetime.now(),
            force=True
        )
        assert should_refresh is True
        assert '强制刷新' in reason

    def test_first_load_no_last_update(self):
        """测试首次加载（无上次更新记录）"""
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(
            last_update=None,
            force=False
        )
        assert should_refresh is True
        assert '首次加载' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_after_hours_old_data(self, mock_status, mock_datetime):
        """测试盘后时间但数据过旧"""
        mock_datetime.now.return_value = datetime(2024, 1, 2, 16, 0)  # Tuesday 16:00
        mock_status.return_value = ('after_hours', '盘后')

        last_update = datetime(2024, 1, 1, 15, 0)  # Monday 15:00 (昨天的数据)
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is True
        assert '数据日期过旧' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_after_hours_incomplete_data(self, mock_status, mock_datetime):
        """测试盘后时间但数据不完整"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 16, 0)  # Monday 16:00
        mock_status.return_value = ('after_hours', '盘后')

        last_update = datetime(2024, 1, 1, 14, 0)  # Monday 14:00 (收盘前的数据)
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is True
        assert '不完整' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_after_hours_fresh_data(self, mock_status, mock_datetime):
        """测试盘后时间且数据是今日收盘后的"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 16, 0)  # Monday 16:00
        mock_status.return_value = ('after_hours', '盘后')

        last_update = datetime(2024, 1, 1, 15, 10)  # Monday 15:10 (收盘后的数据)
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is False
        assert '最新' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_pre_market_recent_data(self, mock_status, mock_datetime):
        """测试盘前时间且数据较新"""
        mock_datetime.now.return_value = datetime(2024, 1, 2, 8, 0)  # Tuesday 8:00
        mock_status.return_value = ('pre_market', '盘前')

        last_update = datetime(2024, 1, 1, 15, 0)  # Monday 15:00 (昨天收盘数据)
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is False
        assert '盘前' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_pre_market_old_data(self, mock_status, mock_datetime):
        """测试盘前时间但数据过旧（超过3天）"""
        mock_datetime.now.return_value = datetime(2024, 1, 5, 8, 0)  # Friday 8:00
        mock_status.return_value = ('pre_market', '盘前')

        last_update = datetime(2024, 1, 1, 15, 0)  # Monday 15:00 (4天前)
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is True
        assert '过期' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_weekend_recent_data(self, mock_status, mock_datetime):
        """测试周末且数据较新"""
        mock_datetime.now.return_value = datetime(2024, 1, 6, 10, 0)  # Saturday 10:00
        mock_status.return_value = ('closed', '休市（周末或节假日）')

        last_update = datetime(2024, 1, 5, 15, 0)  # Friday 15:00 (1天前)
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is False
        assert '休市' in reason or '无需刷新' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_weekend_old_data(self, mock_status, mock_datetime):
        """测试周末但数据过旧（超过7天）"""
        mock_datetime.now.return_value = datetime(2024, 1, 13, 10, 0)  # Saturday 10:00
        mock_status.return_value = ('closed', '休市（周末或节假日）')

        last_update = datetime(2024, 1, 1, 15, 0)  # 12天前
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is True
        assert '过期' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_call_auction_need_refresh(self, mock_status, mock_datetime):
        """测试集合竞价时段需要刷新（距上次更新超过30秒）"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 9, 20, 35)  # Monday 9:20:35
        mock_status.return_value = ('call_auction', '集合竞价')

        last_update = datetime(2024, 1, 1, 9, 20, 0)  # 35秒前
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is True
        assert '集合竞价' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_call_auction_no_refresh(self, mock_status, mock_datetime):
        """测试集合竞价时段不需要刷新（距上次更新不到30秒）"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 9, 20, 20)  # Monday 9:20:20
        mock_status.return_value = ('call_auction', '集合竞价')

        last_update = datetime(2024, 1, 1, 9, 20, 0)  # 20秒前
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is False
        assert '新鲜' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_trading_need_refresh(self, mock_status, mock_datetime):
        """测试交易时段需要刷新（距上次更新超过3秒）"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0, 5)  # Monday 10:00:05
        mock_status.return_value = ('trading', '交易中（早盘）')

        last_update = datetime(2024, 1, 1, 10, 0, 0)  # 5秒前
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is True
        assert '实时行情' in reason

    @patch('src.utils.market_utils.datetime')
    @patch.object(MarketUtils, 'get_market_status')
    def test_trading_no_refresh(self, mock_status, mock_datetime):
        """测试交易时段不需要刷新（距上次更新不到3秒）"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0, 2)  # Monday 10:00:02
        mock_status.return_value = ('trading', '交易中（早盘）')

        last_update = datetime(2024, 1, 1, 10, 0, 0)  # 2秒前
        should_refresh, reason = MarketUtils.should_refresh_realtime_data(last_update)

        assert should_refresh is False
        assert '新鲜' in reason


class TestGetNextTradingSession:
    """测试下一个交易时段获取"""

    @patch('src.utils.market_utils.datetime')
    def test_before_call_auction(self, mock_datetime):
        """测试集合竞价前"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 8, 0)  # Monday 8:00
        mock_datetime.combine = datetime.combine  # Use real datetime.combine
        next_time, desc = MarketUtils.get_next_trading_session()

        assert next_time == datetime(2024, 1, 1, 9, 15)
        assert '集合竞价开始' in desc

    @patch('src.utils.market_utils.datetime')
    def test_during_call_auction(self, mock_datetime):
        """测试集合竞价时段"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 9, 20)  # Monday 9:20
        mock_datetime.combine = datetime.combine  # Use real datetime.combine
        next_time, desc = MarketUtils.get_next_trading_session()

        assert next_time == datetime(2024, 1, 1, 9, 30)
        assert '早盘开盘' in desc

    @patch('src.utils.market_utils.datetime')
    def test_morning_session(self, mock_datetime):
        """测试早盘时段"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 10, 0)  # Monday 10:00
        mock_datetime.combine = datetime.combine  # Use real datetime.combine
        next_time, desc = MarketUtils.get_next_trading_session()

        assert next_time == datetime(2024, 1, 1, 13, 0)
        assert '午盘开盘' in desc

    @patch('src.utils.market_utils.datetime')
    def test_lunch_break(self, mock_datetime):
        """测试午间休市"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 12, 0)  # Monday 12:00
        mock_datetime.combine = datetime.combine  # Use real datetime.combine
        next_time, desc = MarketUtils.get_next_trading_session()

        assert next_time == datetime(2024, 1, 1, 13, 0)
        assert '午盘开盘' in desc

    @patch('src.utils.market_utils.datetime')
    def test_afternoon_session(self, mock_datetime):
        """测试午盘时段"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 14, 0)  # Monday 14:00
        mock_datetime.combine = datetime.combine  # Use real datetime.combine
        next_time, desc = MarketUtils.get_next_trading_session()

        # 应该返回下一交易日
        assert next_time.date() == datetime(2024, 1, 2).date()  # Tuesday
        assert next_time.time() == time(9, 15)
        assert '下一交易日' in desc

    @patch('src.utils.market_utils.datetime')
    def test_after_hours(self, mock_datetime):
        """测试盘后时间"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 16, 0)  # Monday 16:00
        mock_datetime.combine = datetime.combine  # Use real datetime.combine
        next_time, desc = MarketUtils.get_next_trading_session()

        assert next_time.date() == datetime(2024, 1, 2).date()  # Tuesday
        assert next_time.time() == time(9, 15)
        assert '下一交易日' in desc

    @patch('src.utils.market_utils.datetime')
    def test_saturday_to_monday(self, mock_datetime):
        """测试周六到下周一"""
        mock_datetime.now.return_value = datetime(2024, 1, 6, 10, 0)  # Saturday 10:00
        mock_datetime.combine = datetime.combine  # Use real datetime.combine
        next_time, desc = MarketUtils.get_next_trading_session()

        assert next_time.date() == datetime(2024, 1, 8).date()  # Monday
        assert next_time.time() == time(9, 15)
        assert '下一交易日' in desc

    @patch('src.utils.market_utils.datetime')
    def test_sunday_to_monday(self, mock_datetime):
        """测试周日到下周一"""
        mock_datetime.now.return_value = datetime(2024, 1, 7, 10, 0)  # Sunday 10:00
        mock_datetime.combine = datetime.combine  # Use real datetime.combine
        next_time, desc = MarketUtils.get_next_trading_session()

        assert next_time.date() == datetime(2024, 1, 8).date()  # Monday
        assert next_time.time() == time(9, 15)
        assert '下一交易日' in desc

    @patch('src.utils.market_utils.datetime')
    def test_friday_afternoon_to_monday(self, mock_datetime):
        """测试周五下午到下周一"""
        mock_datetime.now.return_value = datetime(2024, 1, 5, 16, 0)  # Friday 16:00
        mock_datetime.combine = datetime.combine  # Use real datetime.combine
        next_time, desc = MarketUtils.get_next_trading_session()

        assert next_time.date() == datetime(2024, 1, 8).date()  # Monday
        assert next_time.time() == time(9, 15)
        assert '下一交易日' in desc


class TestMarketUtilsConstants:
    """测试市场工具类常量"""

    def test_morning_open_time(self):
        """测试早盘开盘时间常量"""
        assert MarketUtils.MORNING_OPEN == time(9, 30)

    def test_morning_close_time(self):
        """测试早盘收盘时间常量"""
        assert MarketUtils.MORNING_CLOSE == time(11, 30)

    def test_afternoon_open_time(self):
        """测试午盘开盘时间常量"""
        assert MarketUtils.AFTERNOON_OPEN == time(13, 0)

    def test_afternoon_close_time(self):
        """测试午盘收盘时间常量"""
        assert MarketUtils.AFTERNOON_CLOSE == time(15, 0)

    def test_call_auction_start_time(self):
        """测试集合竞价开始时间常量"""
        assert MarketUtils.CALL_AUCTION_START == time(9, 15)

    def test_call_auction_end_time(self):
        """测试集合竞价结束时间常量"""
        assert MarketUtils.CALL_AUCTION_END == time(9, 25)


class TestEdgeCases:
    """测试边缘情况"""

    @patch('src.utils.market_utils.datetime')
    def test_exactly_at_morning_open(self, mock_datetime):
        """测试刚好在早盘开盘时间"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 9, 30, 0)  # Monday 9:30:00
        assert MarketUtils.is_trading_time() is True

    @patch('src.utils.market_utils.datetime')
    def test_exactly_at_afternoon_close(self, mock_datetime):
        """测试刚好在午盘收盘时间"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 15, 0, 0)  # Monday 15:00:00
        assert MarketUtils.is_trading_time() is True

    @patch('src.utils.market_utils.datetime')
    def test_one_second_after_close(self, mock_datetime):
        """测试收盘后1秒"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 15, 0, 1)  # Monday 15:00:01
        assert MarketUtils.is_trading_time() is False

    @patch('src.utils.market_utils.datetime')
    def test_one_second_before_open(self, mock_datetime):
        """测试开盘前1秒"""
        mock_datetime.now.return_value = datetime(2024, 1, 1, 9, 29, 59)  # Monday 9:29:59
        assert MarketUtils.is_trading_time() is False


class TestIntegration:
    """集成测试"""

    @patch('src.utils.market_utils.datetime')
    def test_full_trading_day_cycle(self, mock_datetime):
        """测试完整交易日周期"""
        test_times = [
            (datetime(2024, 1, 1, 8, 0), False, 'pre_market'),
            (datetime(2024, 1, 1, 9, 20), True, 'call_auction'),
            (datetime(2024, 1, 1, 10, 0), True, 'trading'),
            (datetime(2024, 1, 1, 12, 0), False, 'closed'),
            (datetime(2024, 1, 1, 14, 0), True, 'trading'),
            (datetime(2024, 1, 1, 16, 0), False, 'after_hours'),
        ]

        for test_time, expected_trading, expected_status in test_times:
            mock_datetime.now.return_value = test_time
            is_trading = MarketUtils.is_trading_time()
            status, _ = MarketUtils.get_market_status()

            assert is_trading == expected_trading, f"Failed at {test_time}"
            assert status == expected_status, f"Failed at {test_time}"
