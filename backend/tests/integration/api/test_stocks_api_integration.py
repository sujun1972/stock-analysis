"""
Stocks API 集成测试

测试 Stocks API 与 Core Adapters 的集成：
- 真实调用 Core 的数据访问模块
- 验证端到端的数据流
- 测试 API 响应格式

注意：需要数据库连接和测试数据

作者: Backend Team
创建日期: 2026-02-01
版本: 1.0.0
"""

import pytest
from datetime import datetime, date
import asyncio



# ==================== 测试配置 ====================

# 测试基础 URL
API_PREFIX = "/api/stocks"


@pytest.fixture
def test_stock_code():
    """测试用股票代码（假设数据库中存在）"""
    return "000001"


@pytest.fixture
def test_date_range():
    """测试日期范围"""
    return {
        "start": "2024-01-01",
        "end": "2024-01-31"
    }


# ==================== 集成测试 ====================

class TestStocksAPIIntegration:
    """Stocks API 集成测试套件"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_stock_list_integration(self, client):
        """
        集成测试：获取股票列表

        验证：
        1. API 返回正确的状态码
        2. 响应格式符合规范
        3. Core Adapter 正常工作
        """
        # Act
        response = await client.get(
            f"{API_PREFIX}/list",
            params={
                "page": 1,
                "page_size": 10
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # 验证响应结构
        assert "code" in data
        assert "message" in data
        assert "data" in data

        # 验证分页结构
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "page_size" in data["data"]
        assert "total_pages" in data["data"]

        # 验证数据类型
        assert isinstance(data["data"]["items"], list)
        assert isinstance(data["data"]["total"], int)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_stock_list_with_filters(self, client):
        """
        集成测试：带过滤条件的股票列表
        """
        # Act: 测试市场过滤
        response = await client.get(
            f"{API_PREFIX}/list",
            params={
                "market": "主板",
                "status": "正常",
                "page": 1,
                "page_size": 20
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

        # 如果有数据，验证市场过滤是否生效
        if data["data"]["total"] > 0:
            for item in data["data"]["items"]:
                # 注意：这取决于 Core 是否正确过滤
                assert "code" in item
                assert "name" in item

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_stock_list_search(self, client):
        """
        集成测试：股票搜索功能
        """
        # Act: 搜索股票代码
        response = await client.get(
            f"{API_PREFIX}/list",
            params={
                "search": "000001",
                "page": 1,
                "page_size": 20
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

        # 验证搜索结果
        if data["data"]["total"] > 0:
            assert any(
                "000001" in item.get("code", "") or
                "000001" in item.get("name", "")
                for item in data["data"]["items"]
            )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_stock_list_pagination(self, client):
        """
        集成测试：分页功能
        """
        # Act: 获取第 1 页
        response1 = await client.get(
            f"{API_PREFIX}/list",
            params={"page": 1, "page_size": 5}
        )

        # Act: 获取第 2 页
        response2 = await client.get(
            f"{API_PREFIX}/list",
            params={"page": 2, "page_size": 5}
        )

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # 如果有足够数据，验证分页
        if data1["data"]["total"] > 5:
            items1 = data1["data"]["items"]
            items2 = data2["data"]["items"]

            # 验证两页数据不同
            if len(items1) > 0 and len(items2) > 0:
                assert items1[0]["code"] != items2[0]["code"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_stock_info_integration(self, client, test_stock_code):
        """
        集成测试：获取单只股票信息
        """
        # Act
        response = await client.get(f"{API_PREFIX}/{test_stock_code}")

        # Assert
        # 注意：如果数据库中没有数据，可能返回 404
        assert response.status_code in [200, 404]

        data = response.json()
        assert "code" in data
        assert "message" in data

        if response.status_code == 200:
            assert "data" in data
            assert data["data"]["code"] == test_stock_code
            assert "name" in data["data"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_stock_info_not_found(self, client):
        """
        集成测试：获取不存在的股票
        """
        # Act
        response = await client.get(f"{API_PREFIX}/999999")

        # Assert
        data = response.json()
        assert data["code"] == 404
        assert "不存在" in data["message"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_stock_daily_data_integration(self, client, test_stock_code, test_date_range):
        """
        集成测试：获取日线数据
        """
        # Act
        response = await client.get(
            f"{API_PREFIX}/{test_stock_code}/daily",
            params={
                "start_date": test_date_range["start"],
                "end_date": test_date_range["end"],
                "limit": 100
            }
        )

        # Assert
        assert response.status_code in [200, 404]

        data = response.json()
        assert "code" in data

        if response.status_code == 200:
            assert data["data"]["code"] == test_stock_code
            assert "records" in data["data"]
            assert "record_count" in data["data"]
            assert isinstance(data["data"]["records"], list)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_stock_daily_data_limit(self, client, test_stock_code):
        """
        集成测试：日线数据限制
        """
        # Act: 限制 10 条
        response = await client.get(
            f"{API_PREFIX}/{test_stock_code}/daily",
            params={"limit": 10}
        )

        # Assert
        if response.status_code == 200:
            data = response.json()
            # 验证返回记录数不超过限制
            assert data["data"]["record_count"] <= 10

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_minute_data_integration(self, client, test_stock_code):
        """
        集成测试：获取分时数据
        """
        # Act
        response = await client.get(
            f"{API_PREFIX}/{test_stock_code}/minute",
            params={
                "trade_date": "2024-01-15",
                "period": "1min"
            }
        )

        # Assert
        # 可能是交易日（200）或非交易日（200 但无数据）或无数据（404）
        assert response.status_code == 200

        data = response.json()
        assert "code" in data
        assert "data" in data

        # 验证响应结构
        assert "code" in data["data"]
        assert "date" in data["data"]
        assert "records" in data["data"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_update_stock_list_not_implemented(self, client):
        """
        集成测试：更新股票列表（未实现）
        """
        # Act
        response = await client.post(f"{API_PREFIX}/update")

        # Assert
        data = response.json()
        assert data["code"] == 501
        assert "暂未实现" in data["message"]


# ==================== 性能测试 ====================

class TestStocksAPIPerformance:
    """Stocks API 性能测试"""

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.skip(reason="性能测试，手动运行")
    async def test_concurrent_requests(self, client):
        """
        性能测试：并发请求

        验证 API 能否处理并发请求
        """
        # 创建 10 个并发请求
        tasks = [
            client.get(f"{API_PREFIX}/list", params={"page": i, "page_size": 10})
            for i in range(1, 11)
        ]

        # 并发执行
        start_time = datetime.now()
        responses = await asyncio.gather(*tasks)
        end_time = datetime.now()

        # 验证所有请求都成功
        for response in responses:
            assert response.status_code == 200

        # 计算耗时
        elapsed = (end_time - start_time).total_seconds()
        print(f"\n10 个并发请求耗时: {elapsed:.2f} 秒")

        # 性能断言（可根据实际情况调整）
        assert elapsed < 5.0, "并发请求耗时过长"

    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.skip(reason="性能测试，手动运行")
    async def test_response_time(self, client):
        """
        性能测试：响应时间

        验证单个请求的响应时间
        """
        start_time = datetime.now()
        response = await client.get(
            f"{API_PREFIX}/list",
            params={"page": 1, "page_size": 20}
        )
        end_time = datetime.now()

        elapsed = (end_time - start_time).total_seconds()
        print(f"\n单个请求响应时间: {elapsed*1000:.0f} ms")

        # 响应时间断言
        assert response.status_code == 200
        assert elapsed < 1.0, "响应时间过长"


# ==================== 边界测试 ====================

class TestStocksAPIBoundary:
    """Stocks API 边界测试"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_large_page_size(self, client):
        """边界测试：超大页面大小"""
        # Act: 请求最大允许的页面大小
        response = await client.get(
            f"{API_PREFIX}/list",
            params={"page": 1, "page_size": 100}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        # 验证返回记录数不超过 100
        assert len(data["data"]["items"]) <= 100

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_page_number(self, client):
        """边界测试：无效页码"""
        # Act: 页码为 0（无效）
        response = await client.get(
            f"{API_PREFIX}/list",
            params={"page": 0, "page_size": 20}
        )

        # Assert: 应该被 FastAPI 验证拦截
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_oversized_page_size(self, client):
        """边界测试：超过限制的页面大小"""
        # Act: 页面大小为 200（超过限制 100）
        response = await client.get(
            f"{API_PREFIX}/list",
            params={"page": 1, "page_size": 200}
        )

        # Assert: 应该被 FastAPI 验证拦截
        assert response.status_code == 422

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_invalid_date_format(self, client):
        """边界测试：无效日期格式"""
        # Act
        response = await client.get(
            f"{API_PREFIX}/000001/daily",
            params={
                "start_date": "invalid-date",
                "end_date": "2024-01-31"
            }
        )

        # Assert
        data = response.json()
        assert data["code"] == 400
        assert "日期格式错误" in data["message"]


# ==================== 测试辅助函数 ====================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
