"""
动态策略API单元测试

测试 /api/dynamic-strategies 端点的所有功能

作者: Backend Team
创建日期: 2026-02-09
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.main import app

client = TestClient(app)


class TestDynamicStrategiesAPI:
    """动态策略API测试类"""

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_get_statistics(self, mock_adapter):
        """测试获取统计信息"""
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_strategy_statistics = AsyncMock(return_value={
            'total_count': 10,
            'enabled_count': 8,
            'disabled_count': 2,
            'validation_passed': 7,
            'validation_failed': 1,
            'validation_pending': 2,
            'by_status': {'draft': 3, 'active': 5, 'archived': 2}
        })

        response = client.get("/api/dynamic-strategies/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['total_count'] == 10
        assert data['data']['enabled_count'] == 8

    def test_validate_code_success(self):
        """测试验证代码 - 成功"""
        payload = {
            "code": "class MyStrategy(BaseStrategy):\n    def select_stocks(self, data):\n        return []"
        }

        with patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter') as mock_adapter:
            mock_adapter_instance = mock_adapter.return_value
            mock_adapter_instance.validate_strategy_code = AsyncMock(return_value={
                'is_valid': True,
                'status': 'passed',
                'errors': [],
                'warnings': [],
                'security_issues': []
            })

            response = client.post("/api/dynamic-strategies/validate", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['is_valid'] is True
            assert data['data']['status'] == 'passed'

    def test_validate_code_with_errors(self):
        """测试验证代码 - 有错误"""
        payload = {
            "code": "class MyStrategy:\n    def invalid syntax"
        }

        with patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter') as mock_adapter:
            mock_adapter_instance = mock_adapter.return_value
            mock_adapter_instance.validate_strategy_code = AsyncMock(return_value={
                'is_valid': False,
                'status': 'failed',
                'errors': [{'type': 'SyntaxError', 'message': 'invalid syntax'}],
                'warnings': [],
                'security_issues': []
            })

            response = client.post("/api/dynamic-strategies/validate", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['data']['is_valid'] is False
            assert len(data['data']['errors']) > 0

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyRepository')
    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_create_dynamic_strategy_success(self, mock_adapter, mock_repo):
        """测试创建动态策略 - 成功"""
        # Mock 名称检查
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.check_strategy_name_exists = AsyncMock(return_value=False)
        mock_adapter_instance.validate_strategy_code = AsyncMock(return_value={
            'is_valid': True,
            'status': 'passed',
            'errors': [],
            'warnings': []
        })

        # Mock 创建结果
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.create = Mock(return_value=1)

        payload = {
            "strategy_name": "my_test_strategy",
            "display_name": "测试策略",
            "description": "这是一个测试策略",
            "class_name": "MyTestStrategy",
            "generated_code": "class MyTestStrategy(BaseStrategy):\n    pass"
        }

        response = client.post("/api/dynamic-strategies", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert data['data']['strategy_id'] == 1
        assert data['data']['validation']['status'] == 'passed'

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_create_dynamic_strategy_name_exists(self, mock_adapter):
        """测试创建动态策略 - 名称已存在"""
        # Mock 名称检查返回已存在
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.check_strategy_name_exists = AsyncMock(return_value=True)

        payload = {
            "strategy_name": "existing_strategy",
            "class_name": "ExistingStrategy",
            "generated_code": "class ExistingStrategy(BaseStrategy):\n    pass"
        }

        response = client.post("/api/dynamic-strategies", json=payload)

        assert response.status_code == 409  # Conflict

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_list_dynamic_strategies(self, mock_adapter):
        """测试获取动态策略列表"""
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.list_strategies = AsyncMock(return_value={
            'items': [
                {
                    'id': 1,
                    'strategy_name': 'strategy_1',
                    'validation_status': 'passed',
                    'is_enabled': True
                },
                {
                    'id': 2,
                    'strategy_name': 'strategy_2',
                    'validation_status': 'failed',
                    'is_enabled': False
                }
            ],
            'meta': {
                'total': 2,
                'page': 1,
                'page_size': 20,
                'total_pages': 1
            }
        })

        response = client.get("/api/dynamic-strategies?page=1&page_size=20")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['meta']['total'] == 2

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_get_dynamic_strategy_by_id(self, mock_adapter):
        """测试获取动态策略详情"""
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_strategy_metadata = AsyncMock(return_value={
            'strategy_id': 1,
            'strategy_name': 'my_strategy',
            'class_name': 'MyStrategy',
            'validation_status': 'passed',
            'is_enabled': True
        })

        response = client.get("/api/dynamic-strategies/1")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['strategy_id'] == 1

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_get_strategy_code(self, mock_adapter):
        """测试获取策略代码"""
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_strategy_code = AsyncMock(return_value={
            'strategy_id': 1,
            'strategy_name': 'my_strategy',
            'class_name': 'MyStrategy',
            'generated_code': 'class MyStrategy(BaseStrategy):\n    pass',
            'code_hash': 'abc123',
            'validation_status': 'passed'
        })

        response = client.get("/api/dynamic-strategies/1/code")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'generated_code' in data['data']
        assert data['data']['strategy_id'] == 1

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyRepository')
    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_update_dynamic_strategy_success(self, mock_adapter, mock_repo):
        """测试更新动态策略 - 成功"""
        # Mock 现有策略
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_strategy_metadata = AsyncMock(return_value={
            'strategy_id': 1,
            'strategy_name': 'my_strategy'
        })

        # Mock 更新操作
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.update = Mock(return_value=1)

        payload = {
            "display_name": "更新后的名称",
            "is_enabled": False
        }

        response = client.put("/api/dynamic-strategies/1", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyRepository')
    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_update_dynamic_strategy_with_code(self, mock_adapter, mock_repo):
        """测试更新动态策略 - 更新代码"""
        # Mock 现有策略
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_strategy_metadata = AsyncMock(return_value={
            'strategy_id': 1,
            'strategy_name': 'my_strategy'
        })
        mock_adapter_instance.validate_strategy_code = AsyncMock(return_value={
            'is_valid': True,
            'status': 'passed',
            'errors': [],
            'warnings': []
        })

        # Mock 更新操作
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.update = Mock(return_value=1)

        payload = {
            "generated_code": "class MyStrategy(BaseStrategy):\n    def new_method(self):\n        pass"
        }

        response = client.put("/api/dynamic-strategies/1", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'validation' in data  # 应该包含验证结果

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyRepository')
    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_delete_dynamic_strategy_success(self, mock_adapter, mock_repo):
        """测试删除动态策略 - 成功"""
        # Mock 现有策略
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_strategy_metadata = AsyncMock(return_value={
            'strategy_id': 1,
            'strategy_name': 'my_strategy'
        })

        # Mock 删除操作
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.delete = Mock(return_value=1)

        response = client.delete("/api/dynamic-strategies/1")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert '删除成功' in data['message']

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_test_dynamic_strategy_success(self, mock_adapter):
        """测试动态策略测试端点 - 成功"""
        # Mock 策略创建
        mock_strategy = Mock()
        mock_strategy.__class__.__name__ = 'MyTestStrategy'

        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_strategy_metadata = AsyncMock(return_value={
            'strategy_name': 'my_test_strategy',
            'validation_status': 'passed'
        })
        mock_adapter_instance.create_strategy_from_code = AsyncMock(
            return_value=mock_strategy
        )

        response = client.post("/api/dynamic-strategies/1/test?strict_mode=true")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['test_passed'] is True

    @patch('app.api.endpoints.dynamic_strategies.DynamicStrategyAdapter')
    def test_test_dynamic_strategy_failed(self, mock_adapter):
        """测试动态策略测试端点 - 失败"""
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_strategy_metadata = AsyncMock(return_value={
            'strategy_name': 'my_test_strategy',
            'validation_status': 'failed'
        })
        mock_adapter_instance.create_strategy_from_code = AsyncMock(
            side_effect=Exception("策略创建失败")
        )

        response = client.post("/api/dynamic-strategies/1/test")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is False
        assert data['data']['test_passed'] is False
        assert 'error' in data['data']
