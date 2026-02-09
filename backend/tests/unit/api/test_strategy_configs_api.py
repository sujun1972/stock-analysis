"""
策略配置API单元测试

测试 /api/strategy-configs 端点的所有功能

作者: Backend Team
创建日期: 2026-02-09
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.main import app

client = TestClient(app)


class TestStrategyConfigsAPI:
    """策略配置API测试类"""

    def test_get_strategy_types(self):
        """测试获取策略类型列表"""
        response = client.get("/api/strategy-configs/types")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'data' in data
        assert len(data['data']) == 3  # momentum, mean_reversion, multi_factor

        # 验证返回的策略类型结构
        for strategy_type in data['data']:
            assert 'type' in strategy_type
            assert 'name' in strategy_type
            assert 'description' in strategy_type
            assert 'default_params' in strategy_type
            assert 'param_schema' in strategy_type

    def test_validate_config_success(self):
        """测试验证配置 - 成功"""
        payload = {
            "strategy_type": "momentum",
            "config": {
                "lookback_period": 20,
                "threshold": 0.10,
                "top_n": 20
            }
        }

        response = client.post("/api/strategy-configs/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['is_valid'] is True
        assert len(data['data']['errors']) == 0

    def test_validate_config_missing_params(self):
        """测试验证配置 - 缺少必需参数"""
        payload = {
            "strategy_type": "momentum",
            "config": {
                "lookback_period": 20
                # 缺少 top_n
            }
        }

        response = client.post("/api/strategy-configs/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['is_valid'] is False
        assert len(data['data']['errors']) > 0

    def test_validate_config_invalid_type(self):
        """测试验证配置 - 不支持的策略类型"""
        payload = {
            "strategy_type": "invalid_type",
            "config": {}
        }

        response = client.post("/api/strategy-configs/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['is_valid'] is False
        assert any('不支持的策略类型' in str(err) for err in data['data']['errors'])

    @patch('app.api.endpoints.strategy_configs.StrategyConfigRepository')
    @patch('app.api.endpoints.strategy_configs.ConfigStrategyAdapter')
    def test_create_config_success(self, mock_adapter, mock_repo):
        """测试创建配置 - 成功"""
        # Mock 验证结果
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.validate_config = AsyncMock(return_value={
            'is_valid': True,
            'errors': [],
            'warnings': []
        })

        # Mock 创建结果
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.create = Mock(return_value=1)

        payload = {
            "strategy_type": "momentum",
            "config": {
                "lookback_period": 20,
                "threshold": 0.10,
                "top_n": 20
            },
            "name": "测试动量策略",
            "description": "测试用配置"
        }

        response = client.post("/api/strategy-configs", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data['success'] is True
        assert data['data']['config_id'] == 1
        assert '创建成功' in data['message']

    @patch('app.api.endpoints.strategy_configs.StrategyConfigRepository')
    @patch('app.api.endpoints.strategy_configs.ConfigStrategyAdapter')
    def test_create_config_validation_failed(self, mock_adapter, mock_repo):
        """测试创建配置 - 验证失败"""
        # Mock 验证结果为失败
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.validate_config = AsyncMock(return_value={
            'is_valid': False,
            'errors': [{'field': 'top_n', 'message': '缺少必需参数'}],
            'warnings': []
        })

        payload = {
            "strategy_type": "momentum",
            "config": {
                "lookback_period": 20
            }
        }

        response = client.post("/api/strategy-configs", json=payload)

        assert response.status_code == 400
        # 验证失败应该返回错误详情

    @patch('app.api.endpoints.strategy_configs.ConfigStrategyAdapter')
    def test_list_configs(self, mock_adapter):
        """测试获取配置列表"""
        # Mock 列表结果
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.list_configs = AsyncMock(return_value={
            'items': [
                {
                    'id': 1,
                    'strategy_type': 'momentum',
                    'name': '动量策略1',
                    'is_enabled': True
                },
                {
                    'id': 2,
                    'strategy_type': 'mean_reversion',
                    'name': '均值回归策略',
                    'is_enabled': True
                }
            ],
            'meta': {
                'total': 2,
                'page': 1,
                'page_size': 20,
                'total_pages': 1
            }
        })

        response = client.get("/api/strategy-configs?page=1&page_size=20")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['data']) == 2
        assert data['meta']['total'] == 2

    @patch('app.api.endpoints.strategy_configs.ConfigStrategyAdapter')
    def test_get_config_by_id_success(self, mock_adapter):
        """测试获取配置详情 - 成功"""
        # Mock 配置详情
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_config_by_id = AsyncMock(return_value={
            'id': 1,
            'strategy_type': 'momentum',
            'config': {'lookback_period': 20, 'top_n': 20},
            'name': '测试配置',
            'is_enabled': True
        })

        response = client.get("/api/strategy-configs/1")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['id'] == 1
        assert data['data']['strategy_type'] == 'momentum'

    @patch('app.api.endpoints.strategy_configs.ConfigStrategyAdapter')
    def test_get_config_by_id_not_found(self, mock_adapter):
        """测试获取配置详情 - 不存在"""
        # Mock 配置不存在
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_config_by_id = AsyncMock(return_value=None)

        response = client.get("/api/strategy-configs/999")

        assert response.status_code == 404

    @patch('app.api.endpoints.strategy_configs.StrategyConfigRepository')
    @patch('app.api.endpoints.strategy_configs.ConfigStrategyAdapter')
    def test_update_config_success(self, mock_adapter, mock_repo):
        """测试更新配置 - 成功"""
        # Mock 现有配置
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_config_by_id = AsyncMock(return_value={
            'id': 1,
            'strategy_type': 'momentum',
            'config': {'lookback_period': 20, 'top_n': 20},
            'is_enabled': True
        })
        mock_adapter_instance.validate_config = AsyncMock(return_value={
            'is_valid': True,
            'errors': [],
            'warnings': []
        })

        # Mock 更新操作
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.update = Mock(return_value=1)

        payload = {
            "name": "更新后的名称",
            "is_enabled": False
        }

        response = client.put("/api/strategy-configs/1", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert '更新成功' in data['message']

    @patch('app.api.endpoints.strategy_configs.StrategyConfigRepository')
    @patch('app.api.endpoints.strategy_configs.ConfigStrategyAdapter')
    def test_delete_config_success(self, mock_adapter, mock_repo):
        """测试删除配置 - 成功"""
        # Mock 现有配置
        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.get_config_by_id = AsyncMock(return_value={
            'id': 1,
            'strategy_type': 'momentum'
        })

        # Mock 删除操作
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.delete = Mock(return_value=1)

        response = client.delete("/api/strategy-configs/1")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert '删除成功' in data['message']

    @patch('app.api.endpoints.strategy_configs.ConfigStrategyAdapter')
    def test_test_config_success(self, mock_adapter):
        """测试配置测试端点 - 成功"""
        # Mock 策略创建
        mock_strategy = Mock()
        mock_strategy.__class__.__name__ = 'MomentumStrategy'

        mock_adapter_instance = mock_adapter.return_value
        mock_adapter_instance.create_strategy_from_config = AsyncMock(
            return_value=mock_strategy
        )
        mock_adapter_instance.get_config_by_id = AsyncMock(return_value={
            'strategy_type': 'momentum',
            'config': {}
        })

        response = client.post("/api/strategy-configs/1/test")

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['data']['test_passed'] is True
