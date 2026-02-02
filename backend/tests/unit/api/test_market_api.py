"""
Market API 单元测试

测试 Market API 的各个端点，使用 Mock 模拟 Adapter 行为

作者: Backend Team
创建日期: 2026-02-02
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, time
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestMarketStatusAPI:
    """测试市场状态 API"""

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_market_status_trading(self, mock_adapter):
        """测试获取市场状态 - 交易时段"""
        # Arrange
        mock_adapter.get_market_status = AsyncMock(
            return_value=('trading', '交易中（早盘）')
        )
        mock_adapter.get_next_trading_session = AsyncMock(
            return_value=(
                datetime(2023, 12, 29, 13, 0, 0),
                '今日午盘开盘'
            )
        )
        mock_adapter.MORNING_OPEN = time(9, 30)
        mock_adapter.MORNING_CLOSE = time(11, 30)
        mock_adapter.AFTERNOON_OPEN = time(13, 0)
        mock_adapter.AFTERNOON_CLOSE = time(15, 0)

        # Act
        response = client.get("/api/market/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert data['message'] == "获取市场状态成功"
        assert data['data']['status'] == 'trading'
        assert data['data']['description'] == '交易中（早盘）'
        assert data['data']['is_trading'] is True
        assert data['data']['should_refresh'] is True
        assert data['data']['next_session_time'] == '2023-12-29 13:00:00'
        assert 'trading_hours' in data['data']

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_market_status_closed(self, mock_adapter):
        """测试获取市场状态 - 休市"""
        # Arrange
        mock_adapter.get_market_status = AsyncMock(
            return_value=('closed', '休市（周末或节假日）')
        )
        mock_adapter.get_next_trading_session = AsyncMock(
            return_value=(
                datetime(2023, 12, 31, 9, 15, 0),
                '下一交易日集合竞价'
            )
        )
        mock_adapter.MORNING_OPEN = time(9, 30)
        mock_adapter.MORNING_CLOSE = time(11, 30)
        mock_adapter.AFTERNOON_OPEN = time(13, 0)
        mock_adapter.AFTERNOON_CLOSE = time(15, 0)

        # Act
        response = client.get("/api/market/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['data']['status'] == 'closed'
        assert data['data']['is_trading'] is False
        assert data['data']['should_refresh'] is False

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_market_status_call_auction(self, mock_adapter):
        """测试获取市场状态 - 集合竞价"""
        # Arrange
        mock_adapter.get_market_status = AsyncMock(
            return_value=('call_auction', '集合竞价')
        )
        mock_adapter.get_next_trading_session = AsyncMock(
            return_value=(
                datetime(2023, 12, 29, 9, 30, 0),
                '今日早盘开盘'
            )
        )
        mock_adapter.MORNING_OPEN = time(9, 30)
        mock_adapter.MORNING_CLOSE = time(11, 30)
        mock_adapter.AFTERNOON_OPEN = time(13, 0)
        mock_adapter.AFTERNOON_CLOSE = time(15, 0)

        # Act
        response = client.get("/api/market/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['data']['status'] == 'call_auction'
        assert data['data']['is_trading'] is True
        assert data['data']['should_refresh'] is True


class TestTradingInfoAPI:
    """测试交易信息 API"""

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_trading_info_trading_day(self, mock_adapter):
        """测试获取交易信息 - 交易日"""
        # Arrange
        mock_adapter.is_trading_day = AsyncMock(return_value=True)
        mock_adapter.is_trading_time = AsyncMock(return_value=True)
        mock_adapter.is_call_auction_time = AsyncMock(return_value=False)
        mock_adapter.get_market_status = AsyncMock(
            return_value=('trading', '交易中（早盘）')
        )
        mock_adapter.CALL_AUCTION_START = time(9, 15)
        mock_adapter.CALL_AUCTION_END = time(9, 25)
        mock_adapter.MORNING_OPEN = time(9, 30)
        mock_adapter.MORNING_CLOSE = time(11, 30)
        mock_adapter.AFTERNOON_OPEN = time(13, 0)
        mock_adapter.AFTERNOON_CLOSE = time(15, 0)

        # Act
        response = client.get("/api/market/trading-info")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert data['data']['is_trading_day'] is True
        assert data['data']['is_trading_time'] is True
        assert data['data']['is_call_auction'] is False
        assert data['data']['market_status'] == 'trading'
        assert 'trading_sessions' in data['data']
        assert 'call_auction' in data['data']['trading_sessions']
        assert 'morning' in data['data']['trading_sessions']
        assert 'afternoon' in data['data']['trading_sessions']

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_trading_info_weekend(self, mock_adapter):
        """测试获取交易信息 - 周末"""
        # Arrange
        mock_adapter.is_trading_day = AsyncMock(return_value=False)
        mock_adapter.is_trading_time = AsyncMock(return_value=False)
        mock_adapter.is_call_auction_time = AsyncMock(return_value=False)
        mock_adapter.get_market_status = AsyncMock(
            return_value=('closed', '休市（周末或节假日）')
        )
        mock_adapter.CALL_AUCTION_START = time(9, 15)
        mock_adapter.CALL_AUCTION_END = time(9, 25)
        mock_adapter.MORNING_OPEN = time(9, 30)
        mock_adapter.MORNING_CLOSE = time(11, 30)
        mock_adapter.AFTERNOON_OPEN = time(13, 0)
        mock_adapter.AFTERNOON_CLOSE = time(15, 0)

        # Act
        response = client.get("/api/market/trading-info")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['data']['is_trading_day'] is False
        assert data['data']['is_trading_time'] is False
        assert data['data']['market_status'] == 'closed'


class TestRefreshCheckAPI:
    """测试数据刷新检查 API"""

    @patch('app.api.endpoints.market.market_adapter')
    def test_check_refresh_needed_should_refresh(self, mock_adapter):
        """测试检查刷新 - 需要刷新"""
        # Arrange
        mock_adapter.get_market_status = AsyncMock(
            return_value=('trading', '交易中（早盘）')
        )
        mock_adapter.should_refresh_realtime_data = AsyncMock(
            return_value=(True, '实时行情更新')
        )

        # Act
        response = client.get("/api/market/refresh-check")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert data['data']['should_refresh'] is True
        assert data['data']['reason'] == '实时行情更新'
        assert data['data']['market_status'] == 'trading'

    @patch('app.api.endpoints.market.market_adapter')
    def test_check_refresh_needed_force(self, mock_adapter):
        """测试检查刷新 - 强制刷新"""
        # Arrange
        mock_adapter.get_market_status = AsyncMock(
            return_value=('closed', '休市（周末或节假日）')
        )
        mock_adapter.should_refresh_realtime_data = AsyncMock(
            return_value=(True, '用户强制刷新')
        )

        # Act
        response = client.get("/api/market/refresh-check?force=true")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['data']['should_refresh'] is True
        assert data['data']['reason'] == '用户强制刷新'
        assert data['data']['force'] is True

    @patch('app.api.endpoints.market.market_adapter')
    def test_check_refresh_needed_with_codes(self, mock_adapter):
        """测试检查刷新 - 指定股票代码"""
        # Arrange
        mock_adapter.get_market_status = AsyncMock(
            return_value=('trading', '交易中（午盘）')
        )
        mock_adapter.should_refresh_realtime_data = AsyncMock(
            return_value=(True, '实时行情更新')
        )

        # Act
        response = client.get(
            "/api/market/refresh-check?codes=000001.SZ&codes=600000.SH"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['data']['codes_count'] == 2

    @patch('app.api.endpoints.market.market_adapter')
    def test_check_refresh_needed_no_refresh(self, mock_adapter):
        """测试检查刷新 - 不需要刷新"""
        # Arrange
        mock_adapter.get_market_status = AsyncMock(
            return_value=('after_hours', '盘后')
        )
        mock_adapter.should_refresh_realtime_data = AsyncMock(
            return_value=(False, '盘后，今日数据已是最新')
        )

        # Act
        response = client.get("/api/market/refresh-check")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['data']['should_refresh'] is False


class TestNextSessionAPI:
    """测试下一交易时段 API"""

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_next_session_lunch_break(self, mock_adapter):
        """测试获取下一交易时段 - 午间休市"""
        # Arrange
        next_time = datetime(2023, 12, 29, 13, 0, 0)
        mock_adapter.get_next_trading_session = AsyncMock(
            return_value=(next_time, '今日午盘开盘')
        )
        mock_adapter.get_market_status = AsyncMock(
            return_value=('closed', '午间休市')
        )

        # Act
        response = client.get("/api/market/next-session")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert data['data']['next_session_desc'] == '今日午盘开盘'
        assert data['data']['market_status'] == 'closed'
        assert data['data']['wait_minutes'] is not None

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_next_session_after_hours(self, mock_adapter):
        """测试获取下一交易时段 - 盘后"""
        # Arrange
        next_time = datetime(2023, 12, 30, 9, 15, 0)
        mock_adapter.get_next_trading_session = AsyncMock(
            return_value=(next_time, '下一交易日集合竞价')
        )
        mock_adapter.get_market_status = AsyncMock(
            return_value=('after_hours', '盘后')
        )

        # Act
        response = client.get("/api/market/next-session")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['data']['next_session_desc'] == '下一交易日集合竞价'
        assert data['data']['market_status'] == 'after_hours'

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_next_session_weekend(self, mock_adapter):
        """测试获取下一交易时段 - 周末"""
        # Arrange
        next_time = datetime(2024, 1, 2, 9, 15, 0)
        mock_adapter.get_next_trading_session = AsyncMock(
            return_value=(next_time, '下一交易日集合竞价')
        )
        mock_adapter.get_market_status = AsyncMock(
            return_value=('closed', '休市（周末或节假日）')
        )

        # Act
        response = client.get("/api/market/next-session")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['data']['next_session_desc'] == '下一交易日集合竞价'


class TestErrorHandling:
    """测试错误处理"""

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_market_status_error(self, mock_adapter):
        """测试获取市场状态异常"""
        # Arrange
        mock_adapter.get_market_status = AsyncMock(
            side_effect=Exception("数据库连接失败")
        )

        # Act
        response = client.get("/api/market/status")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 500
        assert "数据库连接失败" in data['message']

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_trading_info_error(self, mock_adapter):
        """测试获取交易信息异常"""
        # Arrange
        mock_adapter.is_trading_day = AsyncMock(
            side_effect=Exception("服务不可用")
        )

        # Act
        response = client.get("/api/market/trading-info")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 500

    @patch('app.api.endpoints.market.market_adapter')
    def test_check_refresh_needed_error(self, mock_adapter):
        """测试检查刷新异常"""
        # Arrange
        mock_adapter.get_market_status = AsyncMock(
            side_effect=Exception("网络错误")
        )

        # Act
        response = client.get("/api/market/refresh-check")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 500

    @patch('app.api.endpoints.market.market_adapter')
    def test_get_next_session_error(self, mock_adapter):
        """测试获取下一交易时段异常"""
        # Arrange
        mock_adapter.get_next_trading_session = AsyncMock(
            side_effect=Exception("计算错误")
        )

        # Act
        response = client.get("/api/market/next-session")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 500
