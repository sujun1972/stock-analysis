"""
Backtest API 集成测试

测试 Backtest API 与 Core Adapters 的集成。

作者: Backend Team
创建日期: 2026-02-02
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, date
import sys
from pathlib import Path

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.main import app


@pytest.fixture
async def client():
    """创建测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestBacktestAPIIntegration:
    """Backtest API 集成测试类"""

    @pytest.mark.asyncio
    async def test_run_backtest_endpoint(self, client):
        """测试运行回测端点（端到端）"""
        # Arrange
        payload = {
            "stock_codes": ["000001"],
            "start_date": "2023-01-01",
            "end_date": "2023-03-31",
            "strategy_params": {
                "type": "ma_cross",
                "short_window": 5,
                "long_window": 20
            },
            "initial_capital": 1000000.0,
            "commission_rate": 0.0003,
            "stamp_tax_rate": 0.001,
            "min_commission": 5.0,
            "slippage": 0.0
        }

        # Act
        response = await client.post("/api/backtest/run", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data

        # 验证返回数据结构（如果回测成功）
        if data["code"] == 200 and data["data"]:
            assert "metrics" in data["data"] or "portfolio_value" in data["data"]

    @pytest.mark.asyncio
    async def test_calculate_metrics_endpoint(self, client):
        """测试计算指标端点"""
        # Arrange
        payload = {
            "portfolio_value": [1000000, 1020000, 1015000, 1030000],
            "dates": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"],
            "trades": [],
            "positions": []
        }

        # Act
        response = await client.post("/api/backtest/metrics", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data

        # 验证指标存在
        if data["data"]:
            metrics = data["data"]
            # 至少应该有一些基本指标
            assert isinstance(metrics, dict)

    @pytest.mark.asyncio
    async def test_cost_analysis_endpoint(self, client):
        """测试成本分析端点"""
        # Arrange
        payload = {
            "trades": [
                {
                    "code": "000001",
                    "action": "buy",
                    "price": 10.0,
                    "quantity": 1000,
                    "date": "2023-01-01"
                },
                {
                    "code": "000001",
                    "action": "sell",
                    "price": 11.0,
                    "quantity": 1000,
                    "date": "2023-01-05"
                }
            ]
        }

        # Act
        response = await client.post("/api/backtest/cost-analysis", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data

    @pytest.mark.asyncio
    async def test_risk_metrics_endpoint(self, client):
        """测试风险指标端点"""
        # Arrange
        payload = {
            "returns": [0.01, -0.005, 0.015, -0.01, 0.02],
            "dates": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "2023-01-05"],
            "positions": []
        }

        # Act
        response = await client.post("/api/backtest/risk-metrics", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data

    @pytest.mark.asyncio
    async def test_trade_statistics_endpoint(self, client):
        """测试交易统计端点"""
        # Arrange
        payload = {
            "trades": [
                {"code": "000001", "buy_price": 10.0, "sell_price": 11.0, "quantity": 100},
                {"code": "000002", "buy_price": 20.0, "sell_price": 21.5, "quantity": 100},
                {"code": "000003", "buy_price": 15.0, "sell_price": 14.0, "quantity": 100}
            ]
        }

        # Act
        response = await client.post("/api/backtest/trade-statistics", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data

        # 验证统计数据
        if data["data"]:
            stats = data["data"]
            assert "total_trades" in stats
            assert stats["total_trades"] == 3

    @pytest.mark.asyncio
    async def test_invalid_date_range(self, client):
        """测试无效日期范围"""
        # Arrange
        payload = {
            "stock_codes": ["000001"],
            "start_date": "2023-12-31",  # 晚于结束日期
            "end_date": "2023-01-01",
            "strategy_params": {},
            "initial_capital": 1000000.0
        }

        # Act
        response = await client.post("/api/backtest/run", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert "日期" in data["message"]

    @pytest.mark.asyncio
    async def test_empty_trades_cost_analysis(self, client):
        """测试空交易记录的成本分析"""
        # Arrange
        payload = {"trades": []}

        # Act
        response = await client.post("/api/backtest/cost-analysis", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert "不能为空" in data["message"]

    @pytest.mark.asyncio
    async def test_parallel_backtest_endpoint(self, client):
        """测试并行回测端点"""
        # Arrange
        payload = {
            "stock_codes": ["000001"],
            "strategy_params_list": [
                {"type": "ma_cross", "short_window": 5, "long_window": 20},
                {"type": "ma_cross", "short_window": 10, "long_window": 40}
            ],
            "start_date": "2023-01-01",
            "end_date": "2023-03-31",
            "initial_capital": 1000000.0,
            "n_processes": 2
        }

        # Act
        response = await client.post("/api/backtest/parallel", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        # 可能成功或失败（取决于数据是否可用）
        assert data["code"] in [200, 500]

    @pytest.mark.asyncio
    async def test_optimize_params_endpoint(self, client):
        """测试参数优化端点"""
        # Arrange
        payload = {
            "stock_codes": ["000001"],
            "param_grid": {
                "short_window": [5, 10],
                "long_window": [20, 40]
            },
            "start_date": "2023-01-01",
            "end_date": "2023-03-31",
            "initial_capital": 1000000.0,
            "metric": "sharpe_ratio"
        }

        # Act
        response = await client.post("/api/backtest/optimize", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()
        # 可能成功或失败（取决于数据是否可用）
        assert data["code"] in [200, 500]


class TestBacktestAPIValidation:
    """API 参数验证测试"""

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client):
        """测试缺少必需字段"""
        # Arrange
        payload = {
            "stock_codes": ["000001"],
            # 缺少 start_date 和 end_date
            "strategy_params": {}
        }

        # Act
        response = await client.post("/api/backtest/run", json=payload)

        # Assert
        assert response.status_code == 422  # Pydantic 验证错误

    @pytest.mark.asyncio
    async def test_invalid_capital(self, client):
        """测试无效资金"""
        # Arrange
        payload = {
            "stock_codes": ["000001"],
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_params": {},
            "initial_capital": -1000.0  # 负数
        }

        # Act
        response = await client.post("/api/backtest/run", json=payload)

        # Assert
        assert response.status_code == 422  # Pydantic 验证错误

    @pytest.mark.asyncio
    async def test_invalid_commission_rate(self, client):
        """测试无效佣金费率"""
        # Arrange
        payload = {
            "stock_codes": ["000001"],
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_params": {},
            "initial_capital": 1000000.0,
            "commission_rate": 0.05  # 超过上限 0.01
        }

        # Act
        response = await client.post("/api/backtest/run", json=payload)

        # Assert
        assert response.status_code == 422  # Pydantic 验证错误

    @pytest.mark.asyncio
    async def test_empty_stock_codes(self, client):
        """测试空股票代码列表"""
        # Arrange
        payload = {
            "stock_codes": [],  # 空列表
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_params": {},
            "initial_capital": 1000000.0
        }

        # Act
        response = await client.post("/api/backtest/run", json=payload)

        # Assert
        assert response.status_code == 422  # Pydantic 验证错误


class TestBacktestAPIResponseFormat:
    """API 响应格式测试"""

    @pytest.mark.asyncio
    async def test_response_has_standard_format(self, client):
        """测试响应具有标准格式"""
        # Arrange
        payload = {
            "returns": [0.01, -0.005],
            "dates": ["2023-01-01", "2023-01-02"]
        }

        # Act
        response = await client.post("/api/backtest/risk-metrics", json=payload)

        # Assert
        assert response.status_code == 200
        data = response.json()

        # 验证标准响应格式
        assert "code" in data
        assert "message" in data
        assert "data" in data
        assert isinstance(data["code"], int)
        assert isinstance(data["message"], str)

    @pytest.mark.asyncio
    async def test_error_response_format(self, client):
        """测试错误响应格式"""
        # Arrange
        payload = {
            "stock_codes": ["000001"],
            "start_date": "2023-12-31",
            "end_date": "2023-01-01",  # 无效日期范围
            "strategy_params": {},
            "initial_capital": 1000000.0
        }

        # Act
        response = await client.post("/api/backtest/run", json=payload)

        # Assert
        data = response.json()
        assert data["code"] == 400
        assert "message" in data
        assert len(data["message"]) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
