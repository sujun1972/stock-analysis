"""
DataAdapter 单元测试

测试数据访问适配器的所有功能。

作者: Backend Team
创建日期: 2026-02-01
"""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.core_adapters.data_adapter import DataAdapter


@pytest.fixture
def mock_pool_manager():
    """模拟连接池管理器"""
    mock = Mock()
    mock.get_connection = Mock(return_value=Mock())
    mock.close_all = Mock()
    return mock


@pytest.fixture
def mock_query_manager():
    """模拟查询管理器"""
    mock = Mock()
    # Core 的 get_stock_list 返回 DataFrame，不是列表
    mock.get_stock_list = Mock(
        return_value=pd.DataFrame([
            {"code": "000001", "name": "平安银行", "market": "主板"},
            {"code": "000002", "name": "万科A", "market": "主板"},
        ])
    )
    mock.load_daily_data = Mock(
        return_value=pd.DataFrame(
            {
                "open": [10.0, 10.5],
                "high": [10.5, 11.0],
                "low": [9.8, 10.2],
                "close": [10.2, 10.8],
                "volume": [1000000, 1100000],
            }
        )
    )
    mock.load_minute_data = Mock(
        return_value=pd.DataFrame(
            {
                "time": ["09:30", "09:31"],
                "open": [10.0, 10.1],
                "close": [10.1, 10.2],
                "volume": [10000, 11000],
            }
        )
    )
    mock.check_daily_data_completeness = Mock(
        return_value={"total_days": 100, "missing_days": 5, "completeness": 0.95}
    )
    mock.is_trading_day = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_insert_manager():
    """模拟插入管理器"""
    mock = Mock()
    mock.insert_stock_list = Mock(return_value=True)
    mock.insert_daily_data = Mock(return_value=True)
    mock.insert_minute_data = Mock(return_value=True)
    return mock


@pytest.fixture
def data_adapter(mock_pool_manager, mock_query_manager, mock_insert_manager):
    """创建数据适配器实例"""
    with (
        patch(
            "app.core_adapters.data_adapter.ConnectionPoolManager", return_value=mock_pool_manager
        ),
        patch("app.core_adapters.data_adapter.DataQueryManager", return_value=mock_query_manager),
        patch("app.core_adapters.data_adapter.DataInsertManager", return_value=mock_insert_manager),
    ):
        adapter = DataAdapter()
        return adapter


class TestDataAdapter:
    """DataAdapter 单元测试类"""

    @pytest.mark.asyncio
    async def test_get_stock_list_all_markets(self, data_adapter, mock_query_manager):
        """测试获取所有市场的股票列表"""
        # Act
        result = await data_adapter.get_stock_list()

        # Assert
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["code"] == "000001"
        assert result[1]["code"] == "000002"
        mock_query_manager.get_stock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stock_list_specific_market(self, data_adapter, mock_query_manager):
        """测试获取特定市场的股票列表"""
        # Act
        result = await data_adapter.get_stock_list(market="主板")

        # Assert
        assert isinstance(result, list)
        mock_query_manager.get_stock_list.assert_called_with(market="主板", status="正常")

    @pytest.mark.asyncio
    async def test_get_daily_data(self, data_adapter, mock_query_manager):
        """测试获取日线数据"""
        # Arrange
        code = "000001"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)

        # Act
        result = await data_adapter.get_daily_data(code, start_date, end_date)

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert "close" in result.columns
        assert "volume" in result.columns
        mock_query_manager.load_daily_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_daily_data_no_dates(self, data_adapter, mock_query_manager):
        """测试获取日线数据（不指定日期）"""
        # Act
        result = await data_adapter.get_daily_data("000001")

        # Assert
        assert isinstance(result, pd.DataFrame)
        mock_query_manager.load_daily_data.assert_called_with(
            stock_code="000001", start_date=None, end_date=None
        )

    @pytest.mark.asyncio
    async def test_get_minute_data(self, data_adapter, mock_query_manager):
        """测试获取分钟数据"""
        # Arrange
        code = "000001"
        trade_date = date(2023, 6, 1)

        # Act
        result = await data_adapter.get_minute_data(code, period="5min", trade_date=trade_date)

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        mock_query_manager.load_minute_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_stock_list(self, data_adapter, mock_insert_manager):
        """测试插入股票列表"""
        # Arrange
        df = pd.DataFrame(
            {
                "code": ["000001", "000002"],
                "name": ["平安银行", "万科A"],
                "market": ["主板", "主板"],
            }
        )

        # Act
        result = await data_adapter.insert_stock_list(df)

        # Assert
        assert result is True
        mock_insert_manager.insert_stock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_daily_data(self, data_adapter, mock_insert_manager):
        """测试插入日线数据"""
        # Arrange
        df = pd.DataFrame(
            {
                "date": ["2023-01-01", "2023-01-02"],
                "open": [10.0, 10.5],
                "close": [10.2, 10.8],
                "volume": [1000000, 1100000],
            }
        )
        code = "000001"

        # Act
        result = await data_adapter.insert_daily_data(df, code)

        # Assert
        assert result is True
        mock_insert_manager.insert_daily_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_minute_data(self, data_adapter, mock_insert_manager):
        """测试插入分钟数据"""
        # Arrange
        df = pd.DataFrame({"time": ["09:30", "09:31"], "open": [10.0, 10.1], "close": [10.1, 10.2]})
        code = "000001"

        # Act
        result = await data_adapter.insert_minute_data(df, code, period="1min")

        # Assert
        assert result is True
        mock_insert_manager.insert_minute_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_data_completeness(self, data_adapter, mock_query_manager):
        """测试检查数据完整性"""
        # Arrange
        code = "000001"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)

        # Act
        result = await data_adapter.check_data_completeness(code, start_date, end_date)

        # Assert
        assert isinstance(result, dict)
        assert "total_days" in result
        assert "missing_days" in result
        assert "completeness" in result
        assert result["completeness"] == 0.95
        mock_query_manager.check_daily_data_completeness.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_trading_day(self, data_adapter, mock_query_manager):
        """测试判断是否为交易日"""
        # Arrange
        trade_date = date(2023, 6, 1)

        # Act
        result = await data_adapter.is_trading_day(trade_date)

        # Assert
        assert result is True
        mock_query_manager.is_trading_day.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stock_info_exists(self, data_adapter):
        """测试获取存在的股票信息"""
        # Act
        result = await data_adapter.get_stock_info("000001")

        # Assert
        assert result is not None
        assert result["code"] == "000001"
        assert result["name"] == "平安银行"

    @pytest.mark.asyncio
    async def test_get_stock_info_not_exists(self, data_adapter):
        """测试获取不存在的股票信息"""
        # Act
        result = await data_adapter.get_stock_info("999999")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, data_adapter, mock_query_manager):
        """测试并发请求"""
        import asyncio

        # Arrange
        tasks = [
            data_adapter.get_stock_list(),
            data_adapter.get_stock_list(market="主板"),
            data_adapter.get_stock_info("000001"),
        ]

        # Act
        results = await asyncio.gather(*tasks)

        # Assert
        assert len(results) == 3
        assert all(r is not None for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
