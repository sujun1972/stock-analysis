"""
三层架构 API 单元测试

测试覆盖：
- GET /api/three-layer/selectors
- GET /api/three-layer/entries
- GET /api/three-layer/exits
- POST /api/three-layer/validate
- POST /api/three-layer/backtest

作者: Backend Team
创建日期: 2026-02-06
版本: 1.0.0
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestThreeLayerAPI:
    """三层架构 API 单元测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from app.main import app

        return TestClient(app)

    @pytest.fixture
    def mock_adapter(self):
        """Mock ThreeLayerAdapter"""
        with patch("app.api.endpoints.three_layer.three_layer_adapter") as mock:
            yield mock

    # ==================== GET /selectors 测试 ====================

    def test_get_selectors_success(self, client, mock_adapter):
        """测试成功获取选股器列表"""
        # 模拟适配器返回
        mock_selectors = [
            {
                "id": "momentum",
                "name": "动量选股器",
                "description": "动量选股器选股策略",
                "version": "1.0.0",
                "parameters": [
                    {
                        "name": "lookback_period",
                        "label": "回溯周期",
                        "type": "integer",
                        "default": 20,
                        "description": "计算动量的回溯天数",
                        "min_value": 5,
                        "max_value": 200,
                    }
                ],
            },
            {
                "id": "value",
                "name": "价值选股器",
                "description": "价值选股器选股策略",
                "version": "1.0.0",
                "parameters": [],
            },
        ]

        # 配置 mock
        mock_adapter.get_selectors = AsyncMock(return_value=mock_selectors)

        # 发送请求
        response = client.get("/api/three-layer/selectors")

        # 验证
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "获取选股器列表成功"
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "momentum"
        assert data["data"][1]["id"] == "value"

    def test_get_selectors_empty(self, client, mock_adapter):
        """测试获取空的选股器列表"""
        mock_adapter.get_selectors = AsyncMock(return_value=[])

        response = client.get("/api/three-layer/selectors")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]) == 0

    def test_get_selectors_error(self, client, mock_adapter):
        """测试获取选股器时发生错误"""
        mock_adapter.get_selectors = AsyncMock(side_effect=Exception("数据库连接失败"))

        response = client.get("/api/three-layer/selectors")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 500
        assert "获取选股器列表失败" in data["message"]

    # ==================== GET /entries 测试 ====================

    def test_get_entries_success(self, client, mock_adapter):
        """测试成功获取入场策略列表"""
        mock_entries = [
            {
                "id": "immediate",
                "name": "立即入场",
                "description": "立即入场策略",
                "version": "1.0.0",
                "parameters": [],
            },
            {
                "id": "ma_breakout",
                "name": "均线突破入场",
                "description": "均线突破入场策略",
                "version": "1.0.0",
                "parameters": [
                    {
                        "name": "ma_period",
                        "label": "均线周期",
                        "type": "integer",
                        "default": 20,
                        "description": "移动平均线周期",
                    }
                ],
            },
        ]

        mock_adapter.get_entries = AsyncMock(return_value=mock_entries)

        response = client.get("/api/three-layer/entries")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]) == 2
        assert data["data"][0]["id"] == "immediate"

    def test_get_entries_error(self, client, mock_adapter):
        """测试获取入场策略时发生错误"""
        mock_adapter.get_entries = AsyncMock(side_effect=RuntimeError("服务异常"))

        response = client.get("/api/three-layer/entries")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 500
        assert "获取入场策略列表失败" in data["message"]

    # ==================== GET /exits 测试 ====================

    def test_get_exits_success(self, client, mock_adapter):
        """测试成功获取退出策略列表"""
        mock_exits = [
            {
                "id": "fixed_stop_loss",
                "name": "固定止损",
                "description": "固定止损策略",
                "version": "1.0.0",
                "parameters": [
                    {
                        "name": "stop_loss_pct",
                        "label": "止损百分比",
                        "type": "float",
                        "default": -5.0,
                        "description": "触发止损的跌幅",
                        "min_value": -50.0,
                        "max_value": 0.0,
                    }
                ],
            }
        ]

        mock_adapter.get_exits = AsyncMock(return_value=mock_exits)

        response = client.get("/api/three-layer/exits")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "fixed_stop_loss"

    def test_get_exits_error(self, client, mock_adapter):
        """测试获取退出策略时发生错误"""
        mock_adapter.get_exits = AsyncMock(side_effect=ValueError("无效参数"))

        response = client.get("/api/three-layer/exits")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 500

    # ==================== POST /validate 测试 ====================

    def test_validate_strategy_success(self, client, mock_adapter):
        """测试验证有效的策略组合"""
        # 模拟验证成功
        mock_adapter.validate_strategy_combo = AsyncMock(return_value={"valid": True})

        payload = {
            "selector": {"id": "momentum", "params": {"lookback_period": 20, "top_n": 50}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {"stop_loss_pct": -5.0}},
            "rebalance_freq": "W",
        }

        response = client.post("/api/three-layer/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "策略组合有效"
        assert data["data"]["valid"] is True

        # 验证调用参数
        mock_adapter.validate_strategy_combo.assert_called_once()
        call_kwargs = mock_adapter.validate_strategy_combo.call_args[1]
        assert call_kwargs["selector_id"] == "momentum"
        assert call_kwargs["entry_id"] == "immediate"
        assert call_kwargs["exit_id"] == "fixed_stop_loss"
        assert call_kwargs["rebalance_freq"] == "W"

    def test_validate_strategy_invalid_selector(self, client, mock_adapter):
        """测试验证无效的选股器"""
        mock_adapter.validate_strategy_combo = AsyncMock(
            return_value={"valid": False, "errors": ["未知的选股器: unknown_selector"]}
        )

        payload = {
            "selector": {"id": "unknown_selector", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {}},
            "rebalance_freq": "W",
        }

        response = client.post("/api/three-layer/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert "策略验证失败" in data["message"]
        assert "未知的选股器" in data["data"]["errors"][0]

    def test_validate_strategy_invalid_freq(self, client, mock_adapter):
        """测试验证无效的调仓频率"""
        mock_adapter.validate_strategy_combo = AsyncMock(
            return_value={"valid": False, "errors": ["无效的调仓频率: X，必须是 D/W/M 之一"]}
        )

        payload = {
            "selector": {"id": "momentum", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {}},
            "rebalance_freq": "X",
        }

        response = client.post("/api/three-layer/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert len(data["data"]["errors"]) > 0

    def test_validate_strategy_missing_params(self, client, mock_adapter):
        """测试验证缺少参数的策略"""
        mock_adapter.validate_strategy_combo = AsyncMock(
            return_value={"valid": False, "errors": ["参数验证失败: 缺少必需参数 stop_loss_pct"]}
        )

        payload = {
            "selector": {"id": "momentum", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {}},  # 缺少 stop_loss_pct
            "rebalance_freq": "W",
        }

        response = client.post("/api/three-layer/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400

    def test_validate_strategy_exception(self, client, mock_adapter):
        """测试验证过程抛出异常"""
        mock_adapter.validate_strategy_combo = AsyncMock(side_effect=Exception("内部错误"))

        payload = {
            "selector": {"id": "momentum", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {}},
            "rebalance_freq": "W",
        }

        response = client.post("/api/three-layer/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 500
        assert "策略验证过程出错" in data["message"]

    # ==================== POST /backtest 测试 ====================

    def test_run_backtest_success(self, client, mock_adapter):
        """测试成功执行回测"""
        mock_result = {
            "success": True,
            "data": {
                "metrics": {
                    "total_return": 0.32,
                    "annual_return": 0.32,
                    "sharpe_ratio": 1.85,
                    "max_drawdown": -0.12,
                    "win_rate": 0.62,
                    "total_trades": 150,
                },
                "trades": [],
                "daily_portfolio": [],
            },
        }

        mock_adapter.run_backtest = AsyncMock(return_value=mock_result)

        payload = {
            "selector": {"id": "momentum", "params": {"lookback_period": 20, "top_n": 50}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {"stop_loss_pct": -5.0}},
            "rebalance_freq": "W",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 1000000.0,
        }

        response = client.post("/api/three-layer/backtest", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["message"] == "回测完成"
        assert data["data"]["success"] is True
        assert data["data"]["data"]["metrics"]["total_return"] == 0.32

        # 验证调用参数
        mock_adapter.run_backtest.assert_called_once()
        call_kwargs = mock_adapter.run_backtest.call_args[1]
        assert call_kwargs["selector_id"] == "momentum"
        assert call_kwargs["start_date"] == "2023-01-01"
        assert call_kwargs["end_date"] == "2023-12-31"
        assert call_kwargs["initial_capital"] == 1000000.0

    def test_run_backtest_with_stock_codes(self, client, mock_adapter):
        """测试指定股票池的回测"""
        mock_result = {"success": True, "data": {"metrics": {}, "trades": []}}
        mock_adapter.run_backtest = AsyncMock(return_value=mock_result)

        payload = {
            "selector": {"id": "momentum", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {"stop_loss_pct": -5.0}},
            "rebalance_freq": "W",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 1000000.0,
            "stock_codes": ["000001", "000002", "600000"],
        }

        response = client.post("/api/three-layer/backtest", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

        # 验证股票池参数
        call_kwargs = mock_adapter.run_backtest.call_args[1]
        assert call_kwargs["stock_codes"] == ["000001", "000002", "600000"]

    def test_run_backtest_data_error(self, client, mock_adapter):
        """测试回测时数据获取失败"""
        mock_result = {"success": False, "error": "数据获取失败: 数据库连接超时"}

        mock_adapter.run_backtest = AsyncMock(return_value=mock_result)

        payload = {
            "selector": {"id": "momentum", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {"stop_loss_pct": -5.0}},
            "rebalance_freq": "W",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
        }

        response = client.post("/api/three-layer/backtest", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 500
        assert "回测执行失败" in data["message"]
        assert "数据获取失败" in data["data"]["error"]

    def test_run_backtest_strategy_error(self, client, mock_adapter):
        """测试回测时策略创建失败"""
        mock_result = {"success": False, "error": "���知的策略ID: 'unknown'"}

        mock_adapter.run_backtest = AsyncMock(return_value=mock_result)

        payload = {
            "selector": {"id": "unknown", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {}},
            "rebalance_freq": "W",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
        }

        response = client.post("/api/three-layer/backtest", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 500

    def test_run_backtest_invalid_params(self, client, mock_adapter):
        """测试回测时参数验证失败"""
        mock_adapter.run_backtest = AsyncMock(side_effect=ValueError("日期格式错误"))

        payload = {
            "selector": {"id": "momentum", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {}},
            "rebalance_freq": "W",
            "start_date": "invalid-date",
            "end_date": "2023-12-31",
        }

        response = client.post("/api/three-layer/backtest", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 400
        assert "回测参数错误" in data["message"]

    def test_run_backtest_exception(self, client, mock_adapter):
        """测试回测时抛出异常"""
        mock_adapter.run_backtest = AsyncMock(side_effect=Exception("意外错误"))

        payload = {
            "selector": {"id": "momentum", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {}},
            "rebalance_freq": "W",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
        }

        response = client.post("/api/three-layer/backtest", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 500
        assert "回测执行失败" in data["message"]

    def test_run_backtest_empty_data(self, client, mock_adapter):
        """测试回测时数据为空"""
        mock_result = {"success": False, "error": "未找到符合条件的价格数据"}

        mock_adapter.run_backtest = AsyncMock(return_value=mock_result)

        payload = {
            "selector": {"id": "momentum", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {}},
            "rebalance_freq": "W",
            "start_date": "2023-01-01",
            "end_date": "2023-01-02",  # 极短期间
        }

        response = client.post("/api/three-layer/backtest", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 500

    # ==================== 请求格式验证测试 ====================

    def test_backtest_missing_required_fields(self, client):
        """测试缺少必需字段"""
        payload = {
            "selector": {"id": "momentum", "params": {}},
            # 缺少 entry, exit, start_date, end_date
        }

        response = client.post("/api/three-layer/backtest", json=payload)

        assert response.status_code == 422  # Pydantic 验证错误

    def test_backtest_invalid_field_types(self, client):
        """测试字段类型错误"""
        payload = {
            "selector": {"id": "momentum", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {}},
            "rebalance_freq": "W",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": "not_a_number",  # 应该是 float
        }

        response = client.post("/api/three-layer/backtest", json=payload)

        assert response.status_code == 422

    def test_validate_missing_required_fields(self, client):
        """测试验证请求缺少必需字段"""
        payload = {
            "selector": {"id": "momentum", "params": {}},
            # 缺少 entry, exit, rebalance_freq
        }

        response = client.post("/api/three-layer/validate", json=payload)

        assert response.status_code == 422

    # ==================== 边界测试 ====================

    def test_backtest_with_default_capital(self, client, mock_adapter):
        """测试使用默认初始资金"""
        mock_result = {"success": True, "data": {"metrics": {}}}
        mock_adapter.run_backtest = AsyncMock(return_value=mock_result)

        payload = {
            "selector": {"id": "momentum", "params": {}},
            "entry": {"id": "immediate", "params": {}},
            "exit": {"id": "fixed_stop_loss", "params": {}},
            "rebalance_freq": "W",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            # 不指定 initial_capital，应使用默认值 1000000.0
        }

        response = client.post("/api/three-layer/backtest", json=payload)

        assert response.status_code == 200

        # 验证使用了默认值
        call_kwargs = mock_adapter.run_backtest.call_args[1]
        assert call_kwargs["initial_capital"] == 1000000.0

    def test_backtest_with_different_rebalance_freq(self, client, mock_adapter):
        """测试不同的调仓频率"""
        mock_result = {"success": True, "data": {"metrics": {}}}
        mock_adapter.run_backtest = AsyncMock(return_value=mock_result)

        for freq in ["D", "W", "M"]:
            payload = {
                "selector": {"id": "momentum", "params": {}},
                "entry": {"id": "immediate", "params": {}},
                "exit": {"id": "fixed_stop_loss", "params": {}},
                "rebalance_freq": freq,
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
            }

            response = client.post("/api/three-layer/backtest", json=payload)

            assert response.status_code == 200

            # 验证调仓频率参数
            call_kwargs = mock_adapter.run_backtest.call_args[1]
            assert call_kwargs["rebalance_freq"] == freq
