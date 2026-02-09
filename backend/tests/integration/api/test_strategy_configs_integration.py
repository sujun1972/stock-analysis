"""
策略配置API集成测试

端到端测试策略配置的完整流程

作者: Backend Team
创建日期: 2026-02-09
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.integration
class TestStrategyConfigsIntegration:
    """策略配置API集成测试"""

    def test_full_lifecycle(self):
        """测试策略配置的完整生命周期"""

        # 1. 获取可用策略类型
        response = client.get("/api/strategy-configs/types")
        assert response.status_code == 200
        types_data = response.json()
        assert len(types_data['data']) > 0

        # 2. 验证配置
        validate_payload = {
            "strategy_type": "momentum",
            "config": {
                "lookback_period": 20,
                "threshold": 0.10,
                "top_n": 20
            }
        }
        response = client.post("/api/strategy-configs/validate", json=validate_payload)
        assert response.status_code == 200
        validation = response.json()
        assert validation['data']['is_valid'] is True

        # 3. 创建配置
        create_payload = {
            "strategy_type": "momentum",
            "config": {
                "lookback_period": 20,
                "threshold": 0.10,
                "top_n": 20
            },
            "name": "集成测试动量策略",
            "description": "用于集成测试的策略配置"
        }
        response = client.post("/api/strategy-configs", json=create_payload)
        assert response.status_code == 201
        create_data = response.json()
        assert create_data['success'] is True
        config_id = create_data['data']['config_id']

        # 4. 获取配置详情
        response = client.get(f"/api/strategy-configs/{config_id}")
        assert response.status_code == 200
        config = response.json()
        assert config['data']['name'] == "集成测试动量策略"

        # 5. 测试配置
        response = client.post(f"/api/strategy-configs/{config_id}/test")
        assert response.status_code == 200
        test_result = response.json()
        # 注意：测试可能失败如果 Core 不可用，这里只验证接口正常响应

        # 6. 更新配置
        update_payload = {
            "name": "更新后的策略名称",
            "is_enabled": False
        }
        response = client.put(f"/api/strategy-configs/{config_id}", json=update_payload)
        assert response.status_code == 200

        # 7. 验证更新
        response = client.get(f"/api/strategy-configs/{config_id}")
        assert response.status_code == 200
        updated_config = response.json()
        assert updated_config['data']['name'] == "更新后的策略名称"
        assert updated_config['data']['is_enabled'] is False

        # 8. 获取列表（应该包含新创建的配置）
        response = client.get("/api/strategy-configs")
        assert response.status_code == 200
        list_data = response.json()
        assert list_data['success'] is True
        assert any(item['id'] == config_id for item in list_data['data'])

        # 9. 删除配置
        response = client.delete(f"/api/strategy-configs/{config_id}")
        assert response.status_code == 200

        # 10. 验证删除
        response = client.get(f"/api/strategy-configs/{config_id}")
        assert response.status_code == 404

    def test_list_with_filters(self):
        """测试带过滤条件的列表查询"""

        # 按策略类型过滤
        response = client.get("/api/strategy-configs?strategy_type=momentum")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        # 按启用状态过滤
        response = client.get("/api/strategy-configs?is_enabled=true")
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

        # 分页
        response = client.get("/api/strategy-configs?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert 'meta' in data
        assert data['meta']['page'] == 1
        assert data['meta']['page_size'] == 10

    def test_validation_edge_cases(self):
        """测试验证的边界情况"""

        # 参数超出范围
        payload = {
            "strategy_type": "momentum",
            "config": {
                "lookback_period": 200,  # 超出建议范围
                "threshold": 0.10,
                "top_n": 20
            }
        }
        response = client.post("/api/strategy-configs/validate", json=payload)
        assert response.status_code == 200
        data = response.json()
        # 应该有警告但可能仍然有效
        assert 'warnings' in data['data']

        # 缺少必需参数
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
        assert data['data']['is_valid'] is False
        assert len(data['data']['errors']) > 0
