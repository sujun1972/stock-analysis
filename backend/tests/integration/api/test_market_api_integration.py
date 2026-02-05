"""
Market API 集成测试

测试 Market API 与 Core Adapters 的集成，使用真实的 Adapter 实例

作者: Backend Team
创建日期: 2026-02-02
"""

from datetime import datetime, time

import pytest
from httpx import AsyncClient

from app.main import app


@pytest.mark.asyncio
class TestMarketStatusIntegration:
    """市场状态 API 集成测试"""

    async def test_get_market_status_real(self):
        """测试获取真实市场状态"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/status")

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data["code"] == 200
            assert data["message"] == "获取市场状态成功"
            assert "data" in data

            # 检查必要字段
            assert "status" in data["data"]
            assert "description" in data["data"]
            assert "is_trading" in data["data"]
            assert "should_refresh" in data["data"]

            # 检查状态值是否合法
            valid_statuses = ["trading", "call_auction", "closed", "after_hours", "pre_market"]
            assert data["data"]["status"] in valid_statuses

            # 检查布尔值类型
            assert isinstance(data["data"]["is_trading"], bool)
            assert isinstance(data["data"]["should_refresh"], bool)

            # 检查交易时段信息
            assert "trading_hours" in data["data"]
            trading_hours = data["data"]["trading_hours"]
            assert "morning_open" in trading_hours
            assert "morning_close" in trading_hours
            assert "afternoon_open" in trading_hours
            assert "afternoon_close" in trading_hours

    async def test_get_market_status_response_format(self):
        """测试市场状态响应格式"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/status")

            # Assert
            data = response.json()

            # 验证时间格式
            if data["data"]["next_session_time"]:
                time_str = data["data"]["next_session_time"]
                # 应该能够解析为 datetime
                parsed_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                assert isinstance(parsed_time, datetime)


@pytest.mark.asyncio
class TestTradingInfoIntegration:
    """交易信息 API 集成测试"""

    async def test_get_trading_info_real(self):
        """测试获取真实交易信息"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/trading-info")

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data["code"] == 200
            assert data["message"] == "获取交易信息成功"

            # 检查必要字段
            assert "is_trading_day" in data["data"]
            assert "is_trading_time" in data["data"]
            assert "is_call_auction" in data["data"]
            assert "current_time" in data["data"]
            assert "market_status" in data["data"]
            assert "market_description" in data["data"]

            # 检查布尔值类型
            assert isinstance(data["data"]["is_trading_day"], bool)
            assert isinstance(data["data"]["is_trading_time"], bool)
            assert isinstance(data["data"]["is_call_auction"], bool)

    async def test_get_trading_info_sessions_format(self):
        """测试交易时段格式"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/trading-info")

            # Assert
            data = response.json()

            # 检查交易时段结构
            assert "trading_sessions" in data["data"]
            sessions = data["data"]["trading_sessions"]

            # 检查每个时段
            assert "call_auction" in sessions
            assert "morning" in sessions
            assert "afternoon" in sessions

            # 检查时段格式
            for session_name, session in sessions.items():
                assert "start" in session
                assert "end" in session

                # 验证时间格式 (HH:MM:SS)
                start_time = datetime.strptime(session["start"], "%H:%M:%S").time()
                end_time = datetime.strptime(session["end"], "%H:%M:%S").time()

                assert isinstance(start_time, time)
                assert isinstance(end_time, time)
                assert start_time < end_time

    async def test_trading_info_consistency(self):
        """测试交易信息一致性"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/trading-info")

            # Assert
            data = response.json()

            # 如果是交易时段，应该是交易日
            if data["data"]["is_trading_time"]:
                assert data["data"]["is_trading_day"] is True

            # 如果是集合竞价，应该是交易日
            if data["data"]["is_call_auction"]:
                assert data["data"]["is_trading_day"] is True


@pytest.mark.asyncio
class TestRefreshCheckIntegration:
    """数据刷新检查 API 集成测试"""

    async def test_check_refresh_needed_basic(self):
        """测试基本的刷新检查"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/refresh-check")

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data["code"] == 200
            assert data["message"] == "数据新鲜度检查完成"

            # 检查必要字段
            assert "should_refresh" in data["data"]
            assert "reason" in data["data"]
            assert "market_status" in data["data"]
            assert "market_description" in data["data"]

            assert isinstance(data["data"]["should_refresh"], bool)
            assert isinstance(data["data"]["reason"], str)

    async def test_check_refresh_with_force(self):
        """测试强制刷新"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/refresh-check?force=true")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # 强制刷新应该返回 true
            assert data["data"]["should_refresh"] is True
            assert data["data"]["force"] is True
            # 原因应该包含"强制"或"force"
            assert "强制" in data["data"]["reason"] or "force" in data["data"]["reason"].lower()

    async def test_check_refresh_with_codes(self):
        """测试指定股票代码的刷新检查"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get(
                "/api/market/refresh-check?codes=000001.SZ&codes=600000.SH&codes=600519.SH"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data["data"]["codes_count"] == 3

    async def test_check_refresh_without_force(self):
        """测试非强制刷新"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/refresh-check?force=false")

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data["data"]["force"] is False


@pytest.mark.asyncio
class TestNextSessionIntegration:
    """下一交易时段 API 集成测试"""

    async def test_get_next_session_basic(self):
        """测试获取下一交易时段"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/next-session")

            # Assert
            assert response.status_code == 200
            data = response.json()

            assert data["code"] == 200
            assert data["message"] == "获取下一交易时段成功"

            # 检查必要字段
            assert "next_session_desc" in data["data"]
            assert "current_time" in data["data"]
            assert "market_status" in data["data"]
            assert "market_description" in data["data"]

    async def test_next_session_time_format(self):
        """测试下一交易时段时间格式"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/next-session")

            # Assert
            data = response.json()

            # 验证时间格式
            if data["data"]["next_session_time"]:
                time_str = data["data"]["next_session_time"]
                parsed_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
                assert isinstance(parsed_time, datetime)

            # 验证当前时间格式
            current_str = data["data"]["current_time"]
            current_time = datetime.strptime(current_str, "%Y-%m-%d %H:%M:%S")
            assert isinstance(current_time, datetime)

    async def test_next_session_wait_minutes(self):
        """测试等待时间计算"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/next-session")

            # Assert
            data = response.json()

            # 如果有下一时段，应该有等待分钟数
            if data["data"]["next_session_time"]:
                wait_minutes = data["data"]["wait_minutes"]
                assert wait_minutes is not None
                assert isinstance(wait_minutes, int)

                # 等待时间应该是合理的（0分钟到7天）
                assert wait_minutes >= 0
                assert wait_minutes <= 7 * 24 * 60  # 最多7天

    async def test_next_session_description(self):
        """测试下一交易时段描述"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act
            response = await client.get("/api/market/next-session")

            # Assert
            data = response.json()

            desc = data["data"]["next_session_desc"]

            # 描述应该包含关键词
            valid_keywords = ["集合竞价", "早盘", "午盘", "开盘", "交易日"]
            assert any(keyword in desc for keyword in valid_keywords)


@pytest.mark.asyncio
class TestAPIConsistency:
    """测试 API 之间的一致性"""

    async def test_status_and_trading_info_consistency(self):
        """测试市场状态和交易信息的一致性"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Act - 同时调用两个 API
            status_response = await client.get("/api/market/status")
            info_response = await client.get("/api/market/trading-info")

            # Assert
            status_data = status_response.json()["data"]
            info_data = info_response.json()["data"]

            # 市场状态应该一致
            assert status_data["status"] == info_data["market_status"]
            assert status_data["description"] == info_data["market_description"]

    async def test_all_endpoints_accessible(self):
        """测试所有端点都可访问"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            endpoints = [
                "/api/market/status",
                "/api/market/trading-info",
                "/api/market/refresh-check",
                "/api/market/next-session",
            ]

            for endpoint in endpoints:
                response = await client.get(endpoint)
                assert response.status_code == 200
                data = response.json()
                assert data["code"] == 200
                assert "data" in data
                assert "message" in data
