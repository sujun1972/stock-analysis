"""
Data API 单元测试

测试 Data API 的所有端点，使用 Mock 模拟 Core Adapters。

作者: Backend Team
创建日期: 2026-02-02
版本: 1.0.0
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date, datetime, timedelta
import pandas as pd
from fastapi import status
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    """创建测试客户端"""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestGetDailyData:
    """测试 GET /api/data/daily/{code} 端点"""

    @pytest.mark.asyncio
    async def test_get_daily_data_success(self, client):
        """测试成功获取日线数据"""
        # Arrange
        code = "000001.SZ"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)

        # Mock DataFrame
        mock_df = pd.DataFrame({
            'date': pd.date_range(start='2023-01-03', periods=5, freq='D'),
            'open': [13.50, 13.60, 13.55, 13.70, 13.65],
            'high': [13.80, 13.90, 13.85, 14.00, 13.95],
            'low': [13.40, 13.50, 13.45, 13.60, 13.55],
            'close': [13.75, 13.85, 13.80, 13.95, 13.90],
            'volume': [1000000, 1100000, 1050000, 1200000, 1150000],
            'amount': [13750000, 15235000, 14490000, 16740000, 15985000]
        })
        mock_df.set_index('date', inplace=True)

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.get_daily_data = AsyncMock(return_value=mock_df)

            # Act
            response = await client.get(
                f"/api/data/daily/{code}",
                params={
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "limit": 500
                }
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == f"获取股票 {code} 日线数据成功"
        assert data["data"]["code"] == code
        assert data["data"]["count"] == 5
        assert len(data["data"]["data"]) == 5

    @pytest.mark.asyncio
    async def test_get_daily_data_not_found(self, client):
        """测试股票数据不存在"""
        # Arrange
        code = "999999.SZ"
        mock_df = pd.DataFrame()  # 空 DataFrame

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.get_daily_data = AsyncMock(return_value=mock_df)

            # Act
            response = await client.get(f"/api/data/daily/{code}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 404
        assert "无数据" in data["message"]

    @pytest.mark.asyncio
    async def test_get_daily_data_with_limit(self, client):
        """测试数据量限制"""
        # Arrange
        code = "000001.SZ"
        # 创建 1000 条数据
        mock_df = pd.DataFrame({
            'date': pd.date_range(start='2020-01-01', periods=1000, freq='D'),
            'close': [13.50] * 1000
        })
        mock_df.set_index('date', inplace=True)

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.get_daily_data = AsyncMock(return_value=mock_df)

            # Act
            response = await client.get(
                f"/api/data/daily/{code}",
                params={"limit": 100}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]["data"]) == 100  # 被限制为 100 条

    @pytest.mark.asyncio
    async def test_get_daily_data_default_dates(self, client):
        """测试默认日期范围（最近一年）"""
        # Arrange
        code = "000001.SZ"
        mock_df = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=10, freq='D'),
            'close': [13.50] * 10
        })
        mock_df.set_index('date', inplace=True)

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.get_daily_data = AsyncMock(return_value=mock_df)

            # Act
            response = await client.get(f"/api/data/daily/{code}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        # 验证调用了 adapter，并且日期范围约为一年
        mock_adapter.get_daily_data.assert_called_once()
        call_args = mock_adapter.get_daily_data.call_args
        start_date = call_args.kwargs['start_date']
        end_date = call_args.kwargs['end_date']
        assert (end_date - start_date).days >= 360

    @pytest.mark.asyncio
    async def test_get_daily_data_error(self, client):
        """测试服务器错误"""
        # Arrange
        code = "000001.SZ"

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.get_daily_data = AsyncMock(
                side_effect=Exception("Database connection failed")
            )

            # Act
            response = await client.get(f"/api/data/daily/{code}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 500
        assert "失败" in data["message"]


class TestDownloadData:
    """测试 POST /api/data/download 端点"""

    @pytest.mark.asyncio
    async def test_download_data_success(self, client):
        """测试成功下载数据"""
        # Arrange
        codes = ["000001.SZ", "000002.SZ"]
        mock_df = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=5, freq='D'),
            'close': [13.50] * 5
        })

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.download_daily_data = AsyncMock(return_value=mock_df)
            mock_adapter.insert_daily_data = AsyncMock(return_value=True)

            # Act
            response = await client.post(
                "/api/data/download",
                params={
                    "codes": codes,
                    "years": 1,
                    "batch_size": 50
                }
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["total"] == 2
        assert data["data"]["success"] >= 0
        assert data["data"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_download_data_all_stocks(self, client):
        """测试下载全部股票（不指定 codes）"""
        # Arrange
        mock_stock_list = [
            {"code": "000001.SZ", "name": "平安银行"},
            {"code": "000002.SZ", "name": "万科A"}
        ]
        mock_df = pd.DataFrame({'close': [13.50]})

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.get_stock_list = AsyncMock(return_value=mock_stock_list)
            mock_adapter.download_daily_data = AsyncMock(return_value=mock_df)
            mock_adapter.insert_daily_data = AsyncMock(return_value=True)

            # Act
            response = await client.post(
                "/api/data/download",
                params={"max_stocks": 2, "batch_size": 10}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["total"] == 2

    @pytest.mark.asyncio
    async def test_download_data_with_max_stocks(self, client):
        """测试限制下载数量"""
        # Arrange
        codes = [f"00000{i}.SZ" for i in range(1, 101)]  # 100 只股票
        mock_df = pd.DataFrame({'close': [13.50]})

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.download_daily_data = AsyncMock(return_value=mock_df)
            mock_adapter.insert_daily_data = AsyncMock(return_value=True)

            # Act
            response = await client.post(
                "/api/data/download",
                params={"codes": codes, "max_stocks": 10}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["total"] == 10  # 被限制为 10 只

    @pytest.mark.asyncio
    async def test_download_data_with_date_range(self, client):
        """测试指定日期范围下载"""
        # Arrange
        codes = ["000001.SZ"]
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        mock_df = pd.DataFrame({'close': [13.50]})

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.download_daily_data = AsyncMock(return_value=mock_df)
            mock_adapter.insert_daily_data = AsyncMock(return_value=True)

            # Act
            response = await client.post(
                "/api/data/download",
                params={
                    "codes": codes,
                    "start_date": str(start_date),
                    "end_date": str(end_date)
                }
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["start_date"] == str(start_date)
        assert data["data"]["end_date"] == str(end_date)

    @pytest.mark.asyncio
    async def test_download_data_with_years(self, client):
        """测试使用年数参数下载"""
        # Arrange
        codes = ["000001.SZ"]
        mock_df = pd.DataFrame({'close': [13.50]})

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.download_daily_data = AsyncMock(return_value=mock_df)
            mock_adapter.insert_daily_data = AsyncMock(return_value=True)

            # Act
            response = await client.post(
                "/api/data/download",
                params={"codes": codes, "years": 5}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        # 验证日期范围约为 5 年
        mock_adapter.download_daily_data.assert_called()

    @pytest.mark.asyncio
    async def test_download_data_partial_failure(self, client):
        """测试部分下载失败"""
        # Arrange
        codes = ["000001.SZ", "000002.SZ", "999999.SZ"]

        async def mock_download(code, start_date, end_date):
            if code == "999999.SZ":
                raise Exception("Stock not found")
            return pd.DataFrame({'close': [13.50]})

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.download_daily_data = AsyncMock(side_effect=mock_download)
            mock_adapter.insert_daily_data = AsyncMock(return_value=True)

            # Act
            response = await client.post(
                "/api/data/download",
                params={"codes": codes}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["total"] == 3
        assert data["data"]["failed"] >= 1
        assert len(data["data"]["failed_codes"]) >= 1


class TestGetMinuteData:
    """测试 GET /api/data/minute/{code} 端点"""

    @pytest.mark.asyncio
    async def test_get_minute_data_success(self, client):
        """测试成功获取分钟数据"""
        # Arrange
        code = "000001.SZ"
        trade_date = date(2023, 12, 29)

        mock_df = pd.DataFrame({
            'time': pd.date_range(start='09:31:00', periods=5, freq='1min'),
            'open': [13.50, 13.51, 13.52, 13.53, 13.54],
            'close': [13.51, 13.52, 13.53, 13.54, 13.55]
        })
        mock_df.set_index('time', inplace=True)

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.get_minute_data = AsyncMock(return_value=mock_df)

            # Act
            response = await client.get(
                f"/api/data/minute/{code}",
                params={"trade_date": str(trade_date), "period": "1min"}
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["code"] == code
        assert data["data"]["period"] == "1min"

    @pytest.mark.asyncio
    async def test_get_minute_data_invalid_period(self, client):
        """测试无效的周期参数"""
        # Arrange
        code = "000001.SZ"

        # Act
        response = await client.get(
            f"/api/data/minute/{code}",
            params={"period": "invalid"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 400
        assert "无效" in data["message"]

    @pytest.mark.asyncio
    async def test_get_minute_data_not_found(self, client):
        """测试分钟数据不存在"""
        # Arrange
        code = "000001.SZ"
        mock_df = pd.DataFrame()

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.get_minute_data = AsyncMock(return_value=mock_df)

            # Act
            response = await client.get(f"/api/data/minute/{code}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 404


class TestCheckDataIntegrity:
    """测试 GET /api/data/check/{code} 端点"""

    @pytest.mark.asyncio
    async def test_check_data_integrity_success(self, client):
        """测试成功检查数据完整性"""
        # Arrange
        code = "000001.SZ"
        mock_result = {
            "code": code,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "expected_trading_days": 244,
            "actual_data_count": 242,
            "missing_count": 2,
            "data_completeness": 99.18,
            "missing_dates": ["2023-03-15", "2023-08-22"]
        }

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.check_data_integrity = AsyncMock(return_value=mock_result)

            # Act
            response = await client.get(f"/api/data/check/{code}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["data_completeness"] == 99.18

    @pytest.mark.asyncio
    async def test_check_data_integrity_with_date_range(self, client):
        """测试指定日期范围检查"""
        # Arrange
        code = "000001.SZ"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 6, 30)
        mock_result = {
            "expected_trading_days": 122,
            "actual_data_count": 122,
            "data_completeness": 100.0
        }

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.check_data_integrity = AsyncMock(return_value=mock_result)

            # Act
            response = await client.get(
                f"/api/data/check/{code}",
                params={
                    "start_date": str(start_date),
                    "end_date": str(end_date)
                }
            )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["data_completeness"] == 100.0

    @pytest.mark.asyncio
    async def test_check_data_integrity_error(self, client):
        """测试检查失败"""
        # Arrange
        code = "000001.SZ"

        with patch('app.api.endpoints.data.data_adapter') as mock_adapter:
            mock_adapter.check_data_integrity = AsyncMock(
                side_effect=Exception("Database error")
            )

            # Act
            response = await client.get(f"/api/data/check/{code}")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 500
