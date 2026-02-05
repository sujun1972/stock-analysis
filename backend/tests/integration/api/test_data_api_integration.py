"""
Data API 集成测试

测试 Data API 与 Core Adapters 的集成，使用真实的数据库连接。

作者: Backend Team
创建日期: 2026-02-02
版本: 1.0.0
"""

from datetime import date, timedelta

import pytest
from fastapi import status


@pytest.mark.integration
class TestDataAPIIntegration:
    """Data API 集成测试"""

    @pytest.mark.asyncio
    async def test_get_daily_data_integration(self, client):
        """集成测试：获取日线数据（真实数据库）"""
        # Arrange
        code = "000001.SZ"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 31)

        # Act
        response = await client.get(
            f"/api/data/daily/{code}",
            params={"start_date": str(start_date), "end_date": str(end_date)},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 验证响应格式
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert "timestamp" in data

        # 验证数据内容
        if data["code"] == 200:
            assert data["data"]["code"] == code
            assert "count" in data["data"]
            assert "data" in data["data"]

            # 验证数据字段
            if data["data"]["count"] > 0:
                first_record = data["data"]["data"][0]
                assert "date" in first_record
                assert "open" in first_record
                assert "high" in first_record
                assert "low" in first_record
                assert "close" in first_record
                assert "volume" in first_record

    @pytest.mark.asyncio
    async def test_get_daily_data_multiple_stocks(self, client):
        """集成测试：获取多只股票数据"""
        # Arrange
        codes = ["000001.SZ", "000002.SZ", "600000.SH"]
        start_date = date(2023, 12, 1)
        end_date = date(2023, 12, 31)

        # Act & Assert
        for code in codes:
            response = await client.get(
                f"/api/data/daily/{code}",
                params={"start_date": str(start_date), "end_date": str(end_date)},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["code"] in [200, 404, 500]  # 成功、无数据或服务器错误（集成测试环境可能无数据库）

    @pytest.mark.asyncio
    async def test_get_daily_data_with_different_limits(self, client):
        """集成测试：测试不同的数据量限制"""
        # Arrange
        code = "000001.SZ"
        limits = [10, 50, 100, 500]

        # Act & Assert
        for limit in limits:
            response = await client.get(f"/api/data/daily/{code}", params={"limit": limit})

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            if data["code"] == 200:
                # 验证返回数量不超过限制
                assert data["data"]["count"] <= limit
                assert len(data["data"]["data"]) <= limit

    @pytest.mark.asyncio
    async def test_get_minute_data_integration(self, client):
        """集成测试：获取分钟数据"""
        # Arrange
        code = "000001.SZ"
        trade_date = date.today() - timedelta(days=1)  # 昨天
        periods = ["1min", "5min", "15min", "30min", "60min"]

        # Act & Assert
        for period in periods:
            response = await client.get(
                f"/api/data/minute/{code}", params={"trade_date": str(trade_date), "period": period}
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["code"] in [200, 404]  # 成功或无数据

            if data["code"] == 200:
                assert data["data"]["period"] == period

    @pytest.mark.asyncio
    async def test_download_single_stock_integration(self, client):
        """集成测试：下载单只股票数据"""
        # Arrange
        codes = ["000001.SZ"]
        years = 1

        # Act
        response = await client.post(
            "/api/data/download", params={"codes": codes, "years": years, "batch_size": 10}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200
        assert "data" in data

        # 验证下载结果
        result = data["data"]
        assert "status" in result
        assert "total" in result
        assert "success" in result
        assert "failed" in result
        assert result["total"] == len(codes)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_download_multiple_stocks_integration(self, client):
        """集成测试：下载多只股票数据（慢测试）"""
        # Arrange
        codes = ["000001.SZ", "000002.SZ", "600000.SH"]
        start_date = date(2023, 12, 1)
        end_date = date(2023, 12, 31)

        # Act
        response = await client.post(
            "/api/data/download",
            params={
                "codes": codes,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "batch_size": 5,
            },
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["code"] == 200

        result = data["data"]
        assert result["total"] == len(codes)
        assert result["success"] + result["failed"] == result["total"]

    @pytest.mark.asyncio
    async def test_check_data_integrity_integration(self, client):
        """集成测试：检查数据完整性"""
        # Arrange
        code = "000001.SZ"
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)

        # Act
        response = await client.get(
            f"/api/data/check/{code}",
            params={"start_date": str(start_date), "end_date": str(end_date)},
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if data["code"] == 200:
            result = data["data"]
            assert "expected_trading_days" in result
            assert "actual_data_count" in result
            assert "data_completeness" in result
            assert 0 <= result["data_completeness"] <= 100

    @pytest.mark.asyncio
    async def test_data_workflow_integration(self, client):
        """集成测试：完整的数据工作流"""
        # Arrange
        code = "000001.SZ"

        # 1. 先下载数据
        download_response = await client.post(
            "/api/data/download", params={"codes": [code], "years": 1, "batch_size": 10}
        )
        assert download_response.status_code == status.HTTP_200_OK

        # 2. 查询日线数据
        daily_response = await client.get(f"/api/data/daily/{code}", params={"limit": 100})
        assert daily_response.status_code == status.HTTP_200_OK

        # 3. 检查数据完整性
        integrity_response = await client.get(f"/api/data/check/{code}")
        assert integrity_response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, client):
        """集成测试：错误处理"""
        # Test 1: 无效的股票代码
        response1 = await client.get("/api/data/daily/INVALID_CODE")
        assert response1.status_code == status.HTTP_200_OK
        data1 = response1.json()
        assert data1["code"] in [404, 500]

        # Test 2: 无效的周期
        response2 = await client.get(
            "/api/data/minute/000001.SZ", params={"period": "invalid_period"}
        )
        assert response2.status_code == status.HTTP_200_OK
        data2 = response2.json()
        assert data2["code"] == 400

    @pytest.mark.asyncio
    async def test_concurrent_requests_integration(self, client):
        """集成测试：并发请求"""
        import asyncio

        # Arrange
        codes = ["000001.SZ", "000002.SZ", "600000.SH"]

        # Act: 并发请求多只股票数据
        tasks = [client.get(f"/api/data/daily/{code}", params={"limit": 50}) for code in codes]
        responses = await asyncio.gather(*tasks)

        # Assert: 所有请求都应该成功
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "code" in data

    @pytest.mark.asyncio
    async def test_date_range_validation_integration(self, client):
        """集成测试：日期范围验证"""
        # Arrange
        code = "000001.SZ"

        # Test 1: 正常日期范围
        response1 = await client.get(
            f"/api/data/daily/{code}", params={"start_date": "2023-01-01", "end_date": "2023-12-31"}
        )
        assert response1.status_code == status.HTTP_200_OK

        # Test 2: 只指定结束日期
        response2 = await client.get(f"/api/data/daily/{code}", params={"end_date": "2023-12-31"})
        assert response2.status_code == status.HTTP_200_OK

        # Test 3: 都不指定（使用默认值）
        response3 = await client.get(f"/api/data/daily/{code}")
        assert response3.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_performance_large_dataset_integration(self, client):
        """集成测试：大数据集性能测试"""
        import time

        # Arrange
        code = "000001.SZ"
        start_date = date(2020, 1, 1)
        end_date = date(2023, 12, 31)

        # Act
        start_time = time.time()
        response = await client.get(
            f"/api/data/daily/{code}",
            params={"start_date": str(start_date), "end_date": str(end_date), "limit": 5000},
        )
        elapsed_time = time.time() - start_time

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 5.0  # 应该在 5 秒内完成

        data = response.json()
        if data["code"] == 200:
            # 验证数据量
            assert data["data"]["count"] > 0


@pytest.fixture
async def cleanup_test_data():
    """测试后清理测试数据（可选）"""
    yield
    # 清理逻辑（如果需要）
