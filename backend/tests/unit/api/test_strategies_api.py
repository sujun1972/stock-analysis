"""
统一策略 API 测试 (Phase 2)

测试新的统一策略系统 API 端点

作者: Backend Team
创建日期: 2026-02-09
版本: 1.0.0
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestStrategiesAPI:
    """统一策略 API 测试"""

    @pytest.fixture
    def mock_strategy_repo(self):
        """Mock StrategyRepository"""
        with patch("app.api.endpoints.strategies.StrategyRepository") as mock:
            yield mock

    @pytest.fixture
    def mock_code_sanitizer(self):
        """Mock CodeSanitizer"""
        with patch("app.api.endpoints.strategies.CodeSanitizer") as mock:
            yield mock

    @pytest.fixture
    def sample_strategy(self):
        """示例策略数据"""
        return {
            "id": 1,
            "name": "momentum_20d",
            "display_name": "动量策略 20日",
            "code": "class MomentumStrategy(BaseStrategy):\n    pass",
            "code_hash": "abc123",
            "class_name": "MomentumStrategy",
            "source_type": "builtin",
            "description": "基于20日动量选股",
            "category": "momentum",
            "tags": ["动量", "趋势"],
            "default_params": {"lookback_period": 20},
            "validation_status": "passed",
            "validation_errors": None,
            "validation_warnings": None,
            "risk_level": "low",
            "is_enabled": True,
            "usage_count": 10,
            "backtest_count": 5,
            "avg_sharpe_ratio": 1.5,
            "avg_annual_return": 0.25,
            "version": 1,
            "parent_strategy_id": None,
            "created_by": "system",
            "created_at": "2026-02-09T10:00:00",
            "updated_at": "2026-02-09T10:00:00",
            "last_used_at": "2026-02-09T12:00:00"
        }

    def test_get_statistics(self, mock_strategy_repo):
        """测试获取策略统计信息"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_statistics.return_value = {
            "total_count": 10,
            "enabled_count": 8,
            "disabled_count": 2,
            "by_source": {"builtin": 3, "ai": 4, "custom": 3},
            "by_category": {"momentum": 5, "reversal": 5},
            "by_validation": {"passed": 9, "failed": 1},
            "by_risk": {"low": 6, "medium": 4}
        }
        mock_strategy_repo.return_value = mock_repo_instance

        response = client.get("/api/strategies/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_count"] == 10
        assert data["data"]["enabled_count"] == 8

    def test_validate_code_success(self, mock_code_sanitizer):
        """测试验证策略代码 - 成功"""
        mock_sanitizer_instance = MagicMock()
        mock_sanitizer_instance.sanitize.return_value = {
            "safe": True,
            "risk_level": "low",
            "errors": [],
            "warnings": [],
            "security_issues": []
        }
        mock_code_sanitizer.return_value = mock_sanitizer_instance

        response = client.post(
            "/api/strategies/validate",
            json={
                "code": "class MyStrategy(BaseStrategy):\n    pass",
                "strict_mode": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_valid"] is True
        assert data["data"]["status"] == "passed"
        assert data["data"]["risk_level"] == "low"

    def test_validate_code_failed(self, mock_code_sanitizer):
        """测试验证策略代码 - 失败"""
        mock_sanitizer_instance = MagicMock()
        mock_sanitizer_instance.sanitize.return_value = {
            "safe": False,
            "risk_level": "high",
            "errors": ["使用了禁止的函数 eval()"],
            "warnings": [],
            "security_issues": ["代码注入风险"]
        }
        mock_code_sanitizer.return_value = mock_sanitizer_instance

        response = client.post(
            "/api/strategies/validate",
            json={
                "code": "eval('malicious code')",
                "strict_mode": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_valid"] is False
        assert data["data"]["status"] == "failed"
        assert len(data["data"]["errors"]) > 0

    def test_list_strategies(self, mock_strategy_repo, sample_strategy):
        """测试获取策略列表"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.list_all.return_value = {
            "items": [sample_strategy],
            "meta": {
                "total": 1,
                "page": 1,
                "page_size": 20,
                "total_pages": 1
            }
        }
        mock_strategy_repo.return_value = mock_repo_instance

        response = client.get("/api/strategies?source_type=builtin&page=1&page_size=20")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "momentum_20d"
        assert data["meta"]["total"] == 1

    def test_get_strategy_detail(self, mock_strategy_repo, sample_strategy):
        """测试获取策略详情"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_id.return_value = sample_strategy
        mock_repo_instance.increment_usage_count = MagicMock()
        mock_strategy_repo.return_value = mock_repo_instance

        response = client.get("/api/strategies/1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "momentum_20d"
        assert data["data"]["code"] is not None  # 应该包含完整代码
        mock_repo_instance.increment_usage_count.assert_called_once_with(1)

    def test_get_strategy_not_found(self, mock_strategy_repo):
        """测试获取不存在的策略"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_id.return_value = None
        mock_strategy_repo.return_value = mock_repo_instance

        response = client.get("/api/strategies/999")

        assert response.status_code == 404
        data = response.json()
        assert "策略不存在" in data["detail"]

    def test_create_strategy_success(self, mock_strategy_repo, mock_code_sanitizer):
        """测试创建策略 - 成功"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.check_name_exists.return_value = False
        mock_repo_instance.create.return_value = 1
        mock_strategy_repo.return_value = mock_repo_instance

        mock_sanitizer_instance = MagicMock()
        mock_sanitizer_instance.sanitize.return_value = {
            "safe": True,
            "risk_level": "low",
            "errors": [],
            "warnings": [],
            "security_issues": []
        }
        mock_code_sanitizer.return_value = mock_sanitizer_instance

        response = client.post(
            "/api/strategies",
            json={
                "name": "custom_momentum",
                "display_name": "自定义动量策略",
                "code": "class CustomMomentumStrategy(BaseStrategy):\n    pass",
                "class_name": "CustomMomentumStrategy",
                "source_type": "custom",
                "category": "momentum",
                "tags": ["动量", "自定义"]
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["strategy_id"] == 1
        assert data["data"]["validation"]["is_valid"] is True

    def test_create_strategy_duplicate_name(self, mock_strategy_repo):
        """测试创建策略 - 名称已存在"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.check_name_exists.return_value = True
        mock_strategy_repo.return_value = mock_repo_instance

        response = client.post(
            "/api/strategies",
            json={
                "name": "existing_strategy",
                "display_name": "已存在的策略",
                "code": "class ExistingStrategy(BaseStrategy):\n    pass",
                "class_name": "ExistingStrategy",
                "source_type": "custom"
            }
        )

        assert response.status_code == 409
        data = response.json()
        assert "策略名称已存在" in data["detail"]

    def test_update_strategy_success(self, mock_strategy_repo, sample_strategy):
        """测试更新策略 - 成功"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_id.return_value = sample_strategy
        mock_repo_instance.update = MagicMock()
        mock_strategy_repo.return_value = mock_repo_instance

        response = client.put(
            "/api/strategies/1",
            json={
                "display_name": "动量策略 20日 v2",
                "description": "优化后的版本",
                "is_enabled": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "更新成功" in data["message"]

    def test_update_builtin_strategy_code_forbidden(self, mock_strategy_repo, sample_strategy):
        """测试更新内置策略代码 - 禁止"""
        sample_strategy["source_type"] = "builtin"
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_id.return_value = sample_strategy
        mock_strategy_repo.return_value = mock_repo_instance

        response = client.put(
            "/api/strategies/1",
            json={
                "code": "class ModifiedStrategy(BaseStrategy):\n    pass"
            }
        )

        assert response.status_code == 403
        data = response.json()
        assert "内置策略不允许修改代码" in data["detail"]

    def test_delete_strategy_success(self, mock_strategy_repo, sample_strategy):
        """测试删除策略 - 成功"""
        sample_strategy["source_type"] = "custom"
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_id.return_value = sample_strategy
        mock_repo_instance.delete = MagicMock()
        mock_strategy_repo.return_value = mock_repo_instance

        response = client.delete("/api/strategies/1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "删除成功" in data["message"]

    def test_delete_builtin_strategy_forbidden(self, mock_strategy_repo, sample_strategy):
        """测试删除内置策略 - 禁止"""
        sample_strategy["source_type"] = "builtin"
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_id.return_value = sample_strategy
        mock_strategy_repo.return_value = mock_repo_instance

        response = client.delete("/api/strategies/1")

        assert response.status_code == 403
        data = response.json()
        assert "内置策略不允许删除" in data["detail"]

    def test_get_strategy_code(self, mock_strategy_repo, sample_strategy):
        """测试获取策略代码"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_id.return_value = sample_strategy
        mock_strategy_repo.return_value = mock_repo_instance

        response = client.get("/api/strategies/1/code")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["code"] == sample_strategy["code"]
        assert data["data"]["code_hash"] == sample_strategy["code_hash"]
        assert data["data"]["class_name"] == sample_strategy["class_name"]

    def test_test_strategy(self, mock_strategy_repo, mock_code_sanitizer, sample_strategy):
        """测试策略测试端点"""
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_by_id.return_value = sample_strategy
        mock_strategy_repo.return_value = mock_repo_instance

        mock_sanitizer_instance = MagicMock()
        mock_sanitizer_instance.sanitize.return_value = {
            "safe": True,
            "risk_level": "low",
            "errors": []
        }
        mock_code_sanitizer.return_value = mock_sanitizer_instance

        response = client.post("/api/strategies/1/test?strict_mode=true")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["test_passed"] is True
        assert data["data"]["strategy_name"] == "momentum_20d"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
