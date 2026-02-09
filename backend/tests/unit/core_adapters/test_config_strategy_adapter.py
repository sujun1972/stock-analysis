"""
ConfigStrategyAdapter 单元测试

测试配置驱动策略适配器的核心功能。

作者: Backend Team
创建日期: 2026-02-09
版本: 1.0.0
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core_adapters.config_strategy_adapter import ConfigStrategyAdapter
from app.core.exceptions import AdapterError


@pytest.fixture
def adapter():
    """创建适配器实例"""
    return ConfigStrategyAdapter()


@pytest.fixture
def mock_config_data():
    """模拟配置数据"""
    return {
        'id': 1,
        'strategy_type': 'momentum',
        'config': {
            'lookback_period': 20,
            'threshold': 0.10,
            'top_n': 20
        },
        'name': '动量策略配置1',
        'description': '测试配置',
        'is_enabled': True,
        'status': 'active',
        'created_at': '2026-02-09T10:00:00'
    }


class TestConfigStrategyAdapter:
    """ConfigStrategyAdapter 测试类"""

    @pytest.mark.asyncio
    async def test_get_available_strategy_types(self, adapter):
        """测试获取可用策略类型"""
        types = await adapter.get_available_strategy_types()

        assert isinstance(types, list)
        assert len(types) == 3

        # 检查第一个策略类型
        momentum_type = types[0]
        assert momentum_type['type'] == 'momentum'
        assert momentum_type['name'] == '动量策略'
        assert 'default_params' in momentum_type
        assert 'param_schema' in momentum_type

    @pytest.mark.asyncio
    async def test_create_strategy_from_config_success(self, adapter, mock_config_data):
        """测试成功创建策略"""
        with patch.object(adapter.repo, 'get_by_id', return_value=mock_config_data):
            with patch.object(adapter.factory, 'create') as mock_create:
                mock_strategy = MagicMock()
                mock_create.return_value = mock_strategy

                strategy = await adapter.create_strategy_from_config(config_id=1)

                assert strategy == mock_strategy
                mock_create.assert_called_once_with(
                    'momentum',
                    {
                        'lookback_period': 20,
                        'threshold': 0.10,
                        'top_n': 20
                    }
                )

    @pytest.mark.asyncio
    async def test_create_strategy_config_not_found(self, adapter):
        """测试配置不存在"""
        with patch.object(adapter.repo, 'get_by_id', return_value=None):
            with pytest.raises(AdapterError) as exc_info:
                await adapter.create_strategy_from_config(config_id=999)

            assert exc_info.value.error_code == 'CONFIG_NOT_FOUND'
            assert '配置不存在' in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_strategy_config_disabled(self, adapter, mock_config_data):
        """测试配置已禁用"""
        mock_config_data['is_enabled'] = False

        with patch.object(adapter.repo, 'get_by_id', return_value=mock_config_data):
            with pytest.raises(AdapterError) as exc_info:
                await adapter.create_strategy_from_config(config_id=1)

            assert exc_info.value.error_code == 'CONFIG_DISABLED'
            assert '配置已禁用' in exc_info.value.message

    @pytest.mark.asyncio
    async def test_validate_config_success(self, adapter):
        """测试验证配置成功"""
        config = {
            'lookback_period': 20,
            'top_n': 30
        }

        result = await adapter.validate_config('momentum', config)

        assert result['is_valid'] is True
        assert len(result['errors']) == 0

    @pytest.mark.asyncio
    async def test_validate_config_invalid_strategy_type(self, adapter):
        """测试不支持的策略类型"""
        config = {'lookback_period': 20}

        result = await adapter.validate_config('invalid_type', config)

        assert result['is_valid'] is False
        assert len(result['errors']) > 0
        assert 'strategy_type' in result['errors'][0]['field']

    @pytest.mark.asyncio
    async def test_validate_config_missing_required_param(self, adapter):
        """测试缺少必需参数"""
        config = {
            'lookback_period': 20
            # 缺少 top_n
        }

        result = await adapter.validate_config('momentum', config)

        assert result['is_valid'] is False
        assert any('top_n' in err['field'] for err in result['errors'])

    @pytest.mark.asyncio
    async def test_validate_config_invalid_param_type(self, adapter):
        """测试参数类型错误"""
        config = {
            'lookback_period': 'invalid',  # 应该是整数
            'top_n': 20
        }

        result = await adapter.validate_config('momentum', config)

        assert result['is_valid'] is False
        assert any('lookback_period' in err['field'] for err in result['errors'])

    @pytest.mark.asyncio
    async def test_validate_config_param_out_of_range(self, adapter):
        """测试参数超出建议范围（警告）"""
        config = {
            'lookback_period': 100,  # 超出建议范围 [5, 60]
            'top_n': 20
        }

        result = await adapter.validate_config('momentum', config)

        # 应该有警告但仍然有效
        assert len(result['warnings']) > 0
        assert any('lookback_period' in warn['field'] for warn in result['warnings'])

    @pytest.mark.asyncio
    async def test_validate_multi_factor_weights(self, adapter):
        """测试多因子策略权重验证"""
        # 权重总和不为1.0
        config = {
            'factors': ['momentum', 'value', 'quality'],
            'weights': [0.5, 0.3, 0.3],  # 总和为1.1
            'top_n': 30
        }

        result = await adapter.validate_config('multi_factor', config)

        assert len(result['warnings']) > 0
        assert any('weights' in warn['field'] for warn in result['warnings'])

    @pytest.mark.asyncio
    async def test_validate_multi_factor_length_mismatch(self, adapter):
        """测试多因子策略因子和权重长度不匹配"""
        config = {
            'factors': ['momentum', 'value'],
            'weights': [0.5, 0.3, 0.2],  # 长度不匹配
            'top_n': 30
        }

        result = await adapter.validate_config('multi_factor', config)

        assert result['is_valid'] is False
        assert any('weights' in err['field'] for err in result['errors'])

    @pytest.mark.asyncio
    async def test_list_configs(self, adapter):
        """测试获取配置列表"""
        mock_result = {
            'items': [
                {'id': 1, 'strategy_type': 'momentum', 'name': '配置1'},
                {'id': 2, 'strategy_type': 'mean_reversion', 'name': '配置2'},
            ],
            'meta': {
                'total': 2,
                'page': 1,
                'page_size': 20,
                'total_pages': 1
            }
        }

        with patch.object(adapter.repo, 'list', return_value=mock_result):
            result = await adapter.list_configs()

            assert len(result['items']) == 2
            assert result['meta']['total'] == 2

    @pytest.mark.asyncio
    async def test_list_configs_with_filters(self, adapter):
        """测试带过滤条件的配置列表"""
        mock_result = {
            'items': [
                {'id': 1, 'strategy_type': 'momentum', 'name': '配置1'},
            ],
            'meta': {
                'total': 1,
                'page': 1,
                'page_size': 20,
                'total_pages': 1
            }
        }

        with patch.object(adapter.repo, 'list', return_value=mock_result) as mock_list:
            result = await adapter.list_configs(
                strategy_type='momentum',
                is_enabled=True
            )

            mock_list.assert_called_once_with(
                strategy_type='momentum',
                is_enabled=True,
                page=1,
                page_size=20
            )
            assert len(result['items']) == 1

    @pytest.mark.asyncio
    async def test_get_config_by_id_success(self, adapter, mock_config_data):
        """测试根据ID获取配置成功"""
        with patch.object(adapter.repo, 'get_by_id', return_value=mock_config_data):
            config = await adapter.get_config_by_id(config_id=1)

            assert config is not None
            assert config['id'] == 1
            assert config['strategy_type'] == 'momentum'

    @pytest.mark.asyncio
    async def test_get_config_by_id_not_found(self, adapter):
        """测试根据ID获取配置不存在"""
        with patch.object(adapter.repo, 'get_by_id', return_value=None):
            config = await adapter.get_config_by_id(config_id=999)

            assert config is None
