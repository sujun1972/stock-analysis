"""
Stocks API 单元测试

测试 stocks.py 中的所有端点：
- GET /api/stocks/list
- GET /api/stocks/{code}
- GET /api/stocks/{code}/daily
- POST /api/stocks/update
- GET /api/stocks/{code}/minute

作者: Backend Team
创建日期: 2026-02-01
版本: 1.0.0
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date
import pandas as pd

from app.api.endpoints.stocks import (
    get_stock_list,
    get_stock_info,
    get_stock_daily_data,
    update_stock_list,
    get_minute_data
)


class TestGetStockList:
    """测试 GET /api/stocks/list 端点"""

    @pytest.mark.asyncio
    async def test_get_stock_list_success(self):
        """测试成功获取股票列表"""
        # Arrange: 准备测试数据
        mock_stocks = [
            {"code": "000001", "name": "平安银行", "market": "主板"},
            {"code": "000002", "name": "万科A", "market": "主板"},
            {"code": "300001", "name": "特锐德", "market": "创业板"},
        ]

        # 模拟 data_adapter.get_stock_list
        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_stock_list = AsyncMock(return_value=mock_stocks)

            # Act: 执行测试
            response = await get_stock_list(
                market=None,
                status_filter="正常",
                search=None,
                page=1,
                page_size=20
            )

            # Assert: 验证结果
            assert response["code"] == 200
            assert response["message"] == "获取股票列表成功"
            assert response["data"]["total"] == 3
            assert len(response["data"]["items"]) == 3
            assert response["data"]["page"] == 1
            assert response["data"]["page_size"] == 20
            assert response["data"]["total_pages"] == 1

    @pytest.mark.asyncio
    async def test_get_stock_list_with_market_filter(self):
        """测试按市场过滤股票列表"""
        # Arrange
        mock_stocks = [
            {"code": "300001", "name": "特锐德", "market": "创业板"},
            {"code": "300002", "name": "神州泰岳", "market": "创业板"},
        ]

        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_stock_list = AsyncMock(return_value=mock_stocks)

            # Act
            response = await get_stock_list(
                market="创业板",
                status_filter="正常",
                search=None,
                page=1,
                page_size=20
            )

            # Assert
            assert response["code"] == 200
            assert response["data"]["total"] == 2
            mock_adapter.get_stock_list.assert_called_once_with(
                market="创业板",
                status="正常"
            )

    @pytest.mark.asyncio
    async def test_get_stock_list_with_search(self):
        """测试搜索功能"""
        # Arrange
        mock_stocks = [
            {"code": "000001", "name": "平安银行", "market": "主板"},
            {"code": "000002", "name": "万科A", "market": "主板"},
            {"code": "600000", "name": "浦发银行", "market": "主板"},
        ]

        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_stock_list = AsyncMock(return_value=mock_stocks)

            # Act: 搜索 "银行"
            response = await get_stock_list(
                market=None,
                status_filter="正常",
                search="银行",
                page=1,
                page_size=20
            )

            # Assert: 应该只返回包含"银行"的股票
            assert response["code"] == 200
            assert response["data"]["total"] == 2
            assert all("银行" in item["name"] for item in response["data"]["items"])

    @pytest.mark.asyncio
    async def test_get_stock_list_pagination(self):
        """测试分页功能"""
        # Arrange: 准备 50 条数据
        mock_stocks = [
            {"code": f"{i:06d}", "name": f"股票{i}", "market": "主板"}
            for i in range(50)
        ]

        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_stock_list = AsyncMock(return_value=mock_stocks)

            # Act: 请求第 2 页，每页 20 条
            response = await get_stock_list(
                market=None,
                status_filter="正常",
                search=None,
                page=2,
                page_size=20
            )

            # Assert
            assert response["code"] == 200
            assert response["data"]["total"] == 50
            assert len(response["data"]["items"]) == 20
            assert response["data"]["page"] == 2
            assert response["data"]["total_pages"] == 3
            # 验证是第 2 页的数据（索引 20-39）
            assert response["data"]["items"][0]["code"] == "000020"

    @pytest.mark.asyncio
    async def test_get_stock_list_empty_result(self):
        """测试空结果"""
        # Arrange
        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_stock_list = AsyncMock(return_value=[])

            # Act
            response = await get_stock_list(
                market="不存在的市场",
                status_filter="正常",
                search=None,
                page=1,
                page_size=20
            )

            # Assert
            assert response["code"] == 200
            assert response["data"]["total"] == 0
            assert response["data"]["items"] == []

    @pytest.mark.asyncio
    async def test_get_stock_list_error_handling(self):
        """测试错误处理"""
        # Arrange
        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_stock_list = AsyncMock(
                side_effect=Exception("数据库连接失败")
            )

            # Act
            response = await get_stock_list(
                market=None,
                status_filter="正常",
                search=None,
                page=1,
                page_size=20
            )

            # Assert
            assert response["code"] == 500
            assert "失败" in response["message"]


class TestGetStockInfo:
    """测试 GET /api/stocks/{code} 端点"""

    @pytest.mark.asyncio
    async def test_get_stock_info_success(self):
        """测试成功获取股票信息"""
        # Arrange
        mock_stock = {
            "code": "000001",
            "name": "平安银行",
            "market": "主板",
            "industry": "银行",
            "area": "深圳"
        }

        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_stock_info = AsyncMock(return_value=mock_stock)

            # Act
            response = await get_stock_info(code="000001")

            # Assert
            assert response["code"] == 200
            assert response["message"] == "获取股票信息成功"
            assert response["data"]["code"] == "000001"
            assert response["data"]["name"] == "平安银行"
            mock_adapter.get_stock_info.assert_called_once_with("000001")

    @pytest.mark.asyncio
    async def test_get_stock_info_not_found(self):
        """测试股票不存在"""
        # Arrange
        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_stock_info = AsyncMock(return_value=None)

            # Act
            response = await get_stock_info(code="999999")

            # Assert
            assert response["code"] == 404
            assert "不存在" in response["message"]

    @pytest.mark.asyncio
    async def test_get_stock_info_error(self):
        """测试错误处理"""
        # Arrange
        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_stock_info = AsyncMock(
                side_effect=Exception("数据库错误")
            )

            # Act
            response = await get_stock_info(code="000001")

            # Assert
            assert response["code"] == 500
            assert "失败" in response["message"]


class TestGetStockDailyData:
    """测试 GET /api/stocks/{code}/daily 端点"""

    @pytest.mark.asyncio
    async def test_get_stock_daily_data_success(self):
        """测试成功获取日线数据"""
        # Arrange
        mock_df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "open": [10.0, 10.5, 11.0],
            "high": [10.5, 11.0, 11.5],
            "low": [9.5, 10.0, 10.5],
            "close": [10.2, 10.8, 11.2],
            "volume": [1000000, 1100000, 1200000]
        })

        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_daily_data = AsyncMock(return_value=mock_df)

            # Act
            response = await get_stock_daily_data(
                code="000001",
                start_date="2024-01-01",
                end_date="2024-01-03",
                limit=100
            )

            # Assert
            assert response["code"] == 200
            assert response["message"] == "获取日线数据成功"
            assert response["data"]["code"] == "000001"
            assert response["data"]["record_count"] == 3
            assert len(response["data"]["records"]) == 3

    @pytest.mark.asyncio
    async def test_get_stock_daily_data_limit(self):
        """测试记录数限制"""
        # Arrange: 准备 200 条数据
        mock_df = pd.DataFrame({
            "date": [f"2024-{i//30+1:02d}-{i%30+1:02d}" for i in range(200)],
            "close": [10.0] * 200
        })

        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_daily_data = AsyncMock(return_value=mock_df)

            # Act: 限制 50 条
            response = await get_stock_daily_data(
                code="000001",
                start_date=None,
                end_date=None,
                limit=50
            )

            # Assert: 应该只返回最后 50 条
            assert response["code"] == 200
            assert response["data"]["record_count"] == 50

    @pytest.mark.asyncio
    async def test_get_stock_daily_data_empty(self):
        """测试无数据"""
        # Arrange
        mock_df = pd.DataFrame()

        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.get_daily_data = AsyncMock(return_value=mock_df)

            # Act
            response = await get_stock_daily_data(
                code="000001",
                start_date="2024-01-01",
                end_date="2024-01-03",
                limit=100
            )

            # Assert
            assert response["code"] == 404
            assert "无日线数据" in response["message"]

    @pytest.mark.asyncio
    async def test_get_stock_daily_data_invalid_date(self):
        """测试无效日期格式"""
        # Arrange
        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            # Act
            response = await get_stock_daily_data(
                code="000001",
                start_date="invalid-date",
                end_date="2024-01-03",
                limit=100
            )

            # Assert
            assert response["code"] == 400
            assert "日期格式错误" in response["message"]


class TestUpdateStockList:
    """测试 POST /api/stocks/update 端点"""

    @pytest.mark.asyncio
    async def test_update_stock_list_not_implemented(self):
        """测试未实现的更新功能"""
        # Act
        response = await update_stock_list()

        # Assert
        assert response["code"] == 501
        assert "暂未实现" in response["message"]


class TestGetMinuteData:
    """测试 GET /api/stocks/{code}/minute 端点"""

    @pytest.mark.asyncio
    async def test_get_minute_data_success(self):
        """测试成功获取分时数据"""
        # Arrange
        mock_df = pd.DataFrame({
            "time": ["09:31", "09:32", "09:33"],
            "price": [10.0, 10.1, 10.2],
            "volume": [1000, 1100, 1200]
        })

        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.is_trading_day = AsyncMock(return_value=True)
            mock_adapter.get_minute_data = AsyncMock(return_value=mock_df)

            # Act
            response = await get_minute_data(
                code="000001",
                trade_date="2024-01-15",
                period="1min"
            )

            # Assert
            assert response["code"] == 200
            assert response["message"] == "获取分时数据成功"
            assert response["data"]["code"] == "000001"
            assert response["data"]["date"] == "2024-01-15"
            assert response["data"]["period"] == "1min"
            assert response["data"]["record_count"] == 3

    @pytest.mark.asyncio
    async def test_get_minute_data_non_trading_day(self):
        """测试非交易日"""
        # Arrange
        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.is_trading_day = AsyncMock(return_value=False)

            # Act
            response = await get_minute_data(
                code="000001",
                trade_date="2024-01-01",  # 假设是节假日
                period="1min"
            )

            # Assert
            assert response["code"] == 200
            assert response["message"] == "非交易日"
            assert response["data"]["is_trading_day"] is False
            assert response["data"]["records"] == []

    @pytest.mark.asyncio
    async def test_get_minute_data_empty(self):
        """测试无分时数据"""
        # Arrange
        mock_df = pd.DataFrame()

        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.is_trading_day = AsyncMock(return_value=True)
            mock_adapter.get_minute_data = AsyncMock(return_value=mock_df)

            # Act
            response = await get_minute_data(
                code="000001",
                trade_date="2024-01-15",
                period="1min"
            )

            # Assert
            assert response["code"] == 404
            assert "无分时数据" in response["message"]

    @pytest.mark.asyncio
    async def test_get_minute_data_default_date(self):
        """测试默认日期（今天）"""
        # Arrange
        mock_df = pd.DataFrame({
            "time": ["09:31"],
            "price": [10.0]
        })

        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            mock_adapter.is_trading_day = AsyncMock(return_value=True)
            mock_adapter.get_minute_data = AsyncMock(return_value=mock_df)

            # Act: 不传 trade_date
            response = await get_minute_data(
                code="000001",
                trade_date=None,
                period="1min"
            )

            # Assert
            assert response["code"] == 200
            # 验证使用了今天的日期
            today = datetime.now().date().strftime("%Y-%m-%d")
            assert response["data"]["date"] == today

    @pytest.mark.asyncio
    async def test_get_minute_data_invalid_date(self):
        """测试无效日期格式"""
        # Arrange
        with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
            # Act
            response = await get_minute_data(
                code="000001",
                trade_date="invalid-date",
                period="1min"
            )

            # Assert
            assert response["code"] == 400
            assert "日期格式错误" in response["message"]


# ==================== 测试夹具 ====================

@pytest.fixture
def sample_stock_list():
    """样例股票列表"""
    return [
        {"code": "000001", "name": "平安银行", "market": "主板"},
        {"code": "000002", "name": "万科A", "market": "主板"},
        {"code": "300001", "name": "特锐德", "market": "创业板"},
        {"code": "600000", "name": "浦发银行", "market": "主板"},
    ]


@pytest.fixture
def sample_daily_df():
    """样例日线数据"""
    return pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        "open": [10.0, 10.5, 11.0],
        "high": [10.5, 11.0, 11.5],
        "low": [9.5, 10.0, 10.5],
        "close": [10.2, 10.8, 11.2],
        "volume": [1000000, 1100000, 1200000]
    })


@pytest.fixture
def sample_minute_df():
    """样例分时数据"""
    return pd.DataFrame({
        "time": ["09:31", "09:32", "09:33", "09:34", "09:35"],
        "price": [10.0, 10.1, 10.2, 10.15, 10.25],
        "volume": [1000, 1100, 1200, 1150, 1300]
    })
