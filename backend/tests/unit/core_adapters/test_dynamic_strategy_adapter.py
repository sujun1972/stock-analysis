"""
DynamicStrategyAdapter 单元测试

测试动态代码策略适配器的核心功能。

作者: Backend Team
创建日期: 2026-02-09
版本: 1.0.0
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core_adapters.dynamic_strategy_adapter import DynamicStrategyAdapter
from app.core.exceptions import AdapterError, SecurityError


@pytest.fixture
def adapter():
    """创建适配器实例"""
    return DynamicStrategyAdapter()


@pytest.fixture
def mock_strategy_data():
    """模拟策略数据"""
    return {
        'id': 1,
        'strategy_name': 'my_custom_strategy',
        'display_name': '自定义策略',
        'description': '测试策略',
        'class_name': 'MyCustomStrategy',
        'generated_code': 'class MyCustomStrategy(BaseStrategy):\n    pass',
        'code_hash': 'abc123',
        'validation_status': 'passed',
        'validation_errors': None,
        'validation_warnings': None,
        'test_status': 'passed',
        'test_results': None,
        'is_enabled': True,
        'status': 'active',
        'last_backtest_metrics': None,
        'last_backtest_date': None,
        'ai_model': 'deepseek-coder',
        'user_prompt': '创建一个动量策略',
        'created_by': 'user1',
        'created_at': '2026-02-09T10:00:00',
        'updated_at': '2026-02-09T10:00:00',
    }


class TestDynamicStrategyAdapter:
    """DynamicStrategyAdapter 测试类"""

    @pytest.mark.asyncio
    async def test_create_strategy_from_code_success(self, adapter, mock_strategy_data):
        """测试成功创建策略"""
        with patch.object(adapter.repo, 'get_by_id', return_value=mock_strategy_data):
            with patch.object(adapter.factory, 'create_from_code') as mock_create:
                mock_strategy = MagicMock()
                mock_create.return_value = mock_strategy

                strategy = await adapter.create_strategy_from_code(strategy_id=1)

                assert strategy == mock_strategy
                mock_create.assert_called_once_with(
                    strategy_id=1,
                    strict_mode=True
                )

    @pytest.mark.asyncio
    async def test_create_strategy_not_found(self, adapter):
        """测试策略不存在"""
        with patch.object(adapter.repo, 'get_by_id', return_value=None):
            with pytest.raises(AdapterError) as exc_info:
                await adapter.create_strategy_from_code(strategy_id=999)

            assert exc_info.value.error_code == 'STRATEGY_NOT_FOUND'
            assert '策略不存在' in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_strategy_disabled(self, adapter, mock_strategy_data):
        """测试策略已禁用"""
        mock_strategy_data['is_enabled'] = False

        with patch.object(adapter.repo, 'get_by_id', return_value=mock_strategy_data):
            with pytest.raises(AdapterError) as exc_info:
                await adapter.create_strategy_from_code(strategy_id=1)

            assert exc_info.value.error_code == 'STRATEGY_DISABLED'
            assert '策略已禁用' in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_strategy_validation_failed(self, adapter, mock_strategy_data):
        """测试验证失败的策略"""
        mock_strategy_data['validation_status'] = 'failed'
        mock_strategy_data['validation_errors'] = {'error': 'Dangerous operation detected'}

        with patch.object(adapter.repo, 'get_by_id', return_value=mock_strategy_data):
            with pytest.raises(SecurityError) as exc_info:
                await adapter.create_strategy_from_code(strategy_id=1)

            assert exc_info.value.error_code == 'VALIDATION_FAILED'
            assert '策略验证失败' in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_strategy_with_non_strict_mode(self, adapter, mock_strategy_data):
        """测试非严格模式创建策略"""
        with patch.object(adapter.repo, 'get_by_id', return_value=mock_strategy_data):
            with patch.object(adapter.factory, 'create_from_code') as mock_create:
                mock_strategy = MagicMock()
                mock_create.return_value = mock_strategy

                strategy = await adapter.create_strategy_from_code(
                    strategy_id=1,
                    strict_mode=False
                )

                assert strategy == mock_strategy
                mock_create.assert_called_once_with(
                    strategy_id=1,
                    strict_mode=False
                )

    @pytest.mark.asyncio
    async def test_get_strategy_metadata_success(self, adapter, mock_strategy_data):
        """测试获取策略元信息成功"""
        with patch.object(adapter.repo, 'get_by_id', return_value=mock_strategy_data):
            metadata = await adapter.get_strategy_metadata(strategy_id=1)

            assert metadata['strategy_id'] == 1
            assert metadata['strategy_name'] == 'my_custom_strategy'
            assert metadata['class_name'] == 'MyCustomStrategy'
            assert metadata['validation_status'] == 'passed'
            assert metadata['is_enabled'] is True

    @pytest.mark.asyncio
    async def test_get_strategy_metadata_not_found(self, adapter):
        """测试获取不存在的策略元信息"""
        with patch.object(adapter.repo, 'get_by_id', return_value=None):
            with pytest.raises(AdapterError) as exc_info:
                await adapter.get_strategy_metadata(strategy_id=999)

            assert exc_info.value.error_code == 'STRATEGY_NOT_FOUND'

    @pytest.mark.asyncio
    async def test_get_strategy_code_success(self, adapter, mock_strategy_data):
        """测试获取策略代码成功"""
        with patch.object(adapter.repo, 'get_by_id', return_value=mock_strategy_data):
            code_info = await adapter.get_strategy_code(strategy_id=1)

            assert code_info['strategy_id'] == 1
            assert code_info['generated_code'] == mock_strategy_data['generated_code']
            assert code_info['code_hash'] == 'abc123'
            assert code_info['user_prompt'] == '创建一个动量策略'

    @pytest.mark.asyncio
    async def test_list_strategies(self, adapter):
        """测试获取策略列表"""
        mock_result = {
            'items': [
                {'id': 1, 'strategy_name': 'strategy1', 'validation_status': 'passed'},
                {'id': 2, 'strategy_name': 'strategy2', 'validation_status': 'pending'},
            ],
            'meta': {
                'total': 2,
                'page': 1,
                'page_size': 20,
                'total_pages': 1
            }
        }

        with patch.object(adapter.repo, 'list', return_value=mock_result):
            result = await adapter.list_strategies()

            assert len(result['items']) == 2
            assert result['meta']['total'] == 2

    @pytest.mark.asyncio
    async def test_list_strategies_with_filters(self, adapter):
        """测试带过滤条件的策略列表"""
        mock_result = {
            'items': [
                {'id': 1, 'strategy_name': 'strategy1', 'validation_status': 'passed'},
            ],
            'meta': {
                'total': 1,
                'page': 1,
                'page_size': 20,
                'total_pages': 1
            }
        }

        with patch.object(adapter.repo, 'list', return_value=mock_result) as mock_list:
            result = await adapter.list_strategies(
                validation_status='passed',
                is_enabled=True
            )

            mock_list.assert_called_once_with(
                validation_status='passed',
                is_enabled=True,
                status=None,
                page=1,
                page_size=20
            )
            assert len(result['items']) == 1

    @pytest.mark.asyncio
    async def test_validate_strategy_code_valid(self, adapter):
        """测试验证有效的策略代码"""
        valid_code = '''
class MyStrategy(BaseStrategy):
    def generate_signals(self, data):
        return data
'''

        # 模拟 Core 的 CodeValidator 不可用，使用简单验证
        result = await adapter.validate_strategy_code(valid_code)

        assert result['is_valid'] is True
        assert result['status'] in ['passed', 'pending']

    @pytest.mark.asyncio
    async def test_validate_strategy_code_invalid_syntax(self, adapter):
        """测试验证无效的策略代码（语法错误）"""
        invalid_code = '''
class MyStrategy(BaseStrategy)
    def generate_signals(self, data):  # 缺少冒号
        return data
'''

        result = await adapter.validate_strategy_code(invalid_code)

        assert result['is_valid'] is False
        assert len(result['errors']) > 0

    @pytest.mark.asyncio
    async def test_update_validation_status(self, adapter):
        """测试更新验证状态"""
        with patch.object(adapter.repo, 'update_validation_status', return_value=1) as mock_update:
            affected_rows = await adapter.update_validation_status(
                strategy_id=1,
                validation_status='passed',
                validation_errors=None,
                validation_warnings={'warning': 'Minor issue'}
            )

            assert affected_rows == 1
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_strategy_name_exists_true(self, adapter):
        """测试检查策略名称存在"""
        with patch.object(adapter.repo, 'check_name_exists', return_value=True):
            exists = await adapter.check_strategy_name_exists('existing_strategy')

            assert exists is True

    @pytest.mark.asyncio
    async def test_check_strategy_name_exists_false(self, adapter):
        """测试检查策略名称不存在"""
        with patch.object(adapter.repo, 'check_name_exists', return_value=False):
            exists = await adapter.check_strategy_name_exists('new_strategy')

            assert exists is False

    @pytest.mark.asyncio
    async def test_check_strategy_name_exists_with_exclude(self, adapter):
        """测试检查策略名称（排除特定ID）"""
        with patch.object(adapter.repo, 'check_name_exists', return_value=False) as mock_check:
            exists = await adapter.check_strategy_name_exists(
                'strategy_name',
                exclude_id=5
            )

            assert exists is False
            mock_check.assert_called_once_with('strategy_name', 5)

    @pytest.mark.asyncio
    async def test_get_strategy_statistics(self, adapter):
        """测试获取策略统计信息"""
        mock_result = {
            'items': [
                {
                    'id': 1,
                    'is_enabled': True,
                    'validation_status': 'passed',
                    'status': 'active'
                },
                {
                    'id': 2,
                    'is_enabled': False,
                    'validation_status': 'failed',
                    'status': 'draft'
                },
                {
                    'id': 3,
                    'is_enabled': True,
                    'validation_status': 'passed',
                    'status': 'active'
                },
            ],
            'meta': {'total': 3}
        }

        with patch.object(adapter.repo, 'list', return_value=mock_result):
            stats = await adapter.get_strategy_statistics()

            assert stats['total_count'] == 3
            assert stats['enabled_count'] == 2
            assert stats['disabled_count'] == 1
            assert stats['validation_passed'] == 2
            assert stats['validation_failed'] == 1
            assert stats['by_status']['active'] == 2
            assert stats['by_status']['draft'] == 1
