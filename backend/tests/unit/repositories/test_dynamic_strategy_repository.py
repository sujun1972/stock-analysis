"""
DynamicStrategyRepository 单元测试

测试动态策略数据访问层的所有功能。

作者: Backend Team
创建日期: 2026-02-09
版本: 1.0.0
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.repositories.dynamic_strategy_repository import DynamicStrategyRepository


@pytest.fixture
def mock_db():
    """创建模拟数据库连接"""
    db = Mock()
    conn = Mock()
    cursor = Mock()

    db.get_connection.return_value = conn
    conn.cursor.return_value = cursor

    return db, conn, cursor


@pytest.fixture
def repository(mock_db):
    """创建Repository实例"""
    db, conn, cursor = mock_db
    repo = DynamicStrategyRepository()
    repo.db = db
    return repo, db, conn, cursor


@pytest.fixture
def sample_strategy_code():
    """示例策略代码"""
    return """
class MomentumStrategy(BaseStrategy):
    def generate_signals(self, data):
        return data['close'].pct_change(20) > 0.1
"""


@pytest.fixture
def sample_strategy_data(sample_strategy_code):
    """示例策略数据"""
    return {
        'strategy_name': 'momentum_v1',
        'class_name': 'MomentumStrategy',
        'generated_code': sample_strategy_code,
        'display_name': '动量策略V1',
        'description': 'AI生成的动量策略',
        'user_prompt': '创建一个基于20日动量的策略',
        'ai_model': 'claude-3-5-sonnet',
        'ai_prompt': '生成动量策略代码',
        'generation_tokens': 500,
        'generation_cost': 0.025,
        'validation_status': 'passed',
        'tags': ['momentum', 'ai_generated'],
        'category': 'trend',
        'created_by': 'user123'
    }


class TestDynamicStrategyRepositoryComputeHash:
    """测试代码哈希计算"""

    def test_compute_code_hash(self):
        """测试计算代码哈希"""
        code = "print('hello world')"
        hash1 = DynamicStrategyRepository.compute_code_hash(code)

        # 验证哈希值特性
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hash length

        # 相同代码应该产生相同哈希
        hash2 = DynamicStrategyRepository.compute_code_hash(code)
        assert hash1 == hash2

    def test_compute_code_hash_different(self):
        """测试不同代码产生不同哈希"""
        code1 = "print('hello')"
        code2 = "print('world')"

        hash1 = DynamicStrategyRepository.compute_code_hash(code1)
        hash2 = DynamicStrategyRepository.compute_code_hash(code2)

        assert hash1 != hash2


class TestDynamicStrategyRepositoryCreate:
    """测试创建动态策略"""

    def test_create_success(self, repository, sample_strategy_data):
        """测试成功创建策略"""
        repo, db, conn, cursor = repository

        cursor.fetchone.return_value = (123,)

        strategy_id = repo.create(sample_strategy_data)

        assert strategy_id == 123
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()
        cursor.close.assert_called_once()
        db.release_connection.assert_called_with(conn)

    def test_create_minimal_data(self, repository, sample_strategy_code):
        """测试使用最小数据创建策略"""
        repo, db, conn, cursor = repository
        cursor.fetchone.return_value = (456,)

        minimal_data = {
            'strategy_name': 'simple_strategy',
            'class_name': 'SimpleStrategy',
            'generated_code': sample_strategy_code
        }

        strategy_id = repo.create(minimal_data)

        assert strategy_id == 456

    def test_create_computes_hash(self, repository, sample_strategy_data):
        """测试创建时自动计算代码哈希"""
        repo, db, conn, cursor = repository
        cursor.fetchone.return_value = (789,)

        strategy_id = repo.create(sample_strategy_data)

        # 验证execute被调用，且参数中包含哈希
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args[0]
        assert len(call_args) == 2  # query and params
        params = call_args[1]
        # code_hash 是第6个参数（索引5）
        assert len(params[5]) == 64  # SHA256 hash


class TestDynamicStrategyRepositoryGetById:
    """测试根据ID获取策略"""

    def test_get_by_id_success(self, repository, sample_strategy_code):
        """测试成功获取策略"""
        repo, db, conn, cursor = repository

        row = (
            1, 'momentum_v1', '动量策略V1', '描述', 'MomentumStrategy',
            sample_strategy_code, 'abc123...', 'user prompt', 'claude', 'ai prompt',
            500, 0.025, 'passed', '{}', '{}', 'success', '{}',
            '{}', None, True, 'active', 1, None,
            ['momentum'], 'trend', 'user123', None, None, None
        )

        with patch.object(repo, 'execute_query', return_value=[row]):
            result = repo.get_by_id(1)

        assert result is not None
        assert result['id'] == 1
        assert result['strategy_name'] == 'momentum_v1'
        assert result['class_name'] == 'MomentumStrategy'
        assert result['validation_status'] == 'passed'

    def test_get_by_id_not_found(self, repository):
        """测试策略不存在"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[]):
            result = repo.get_by_id(999)

        assert result is None

    def test_get_by_id_null_cost(self, repository, sample_strategy_code):
        """测试成本为NULL的处理"""
        repo, db, conn, cursor = repository

        row = (
            1, 'test_strategy', 'Test', 'Desc', 'TestClass',
            sample_strategy_code, 'hash', None, None, None,
            None, None, 'pending', None, None, None, None,
            None, None, True, 'active', 1, None,
            None, None, None, None, None, None
        )

        with patch.object(repo, 'execute_query', return_value=[row]):
            result = repo.get_by_id(1)

        assert result['generation_cost'] is None


class TestDynamicStrategyRepositoryGetByName:
    """测试根据名称获取策略"""

    def test_get_by_name_success(self, repository, sample_strategy_code):
        """测试成功根据名称获取策略"""
        repo, db, conn, cursor = repository

        row = (
            1, 'momentum_v1', '动量策略V1', '描述', 'MomentumStrategy',
            sample_strategy_code, 'hash', 'passed',
            True, 'active', None
        )

        with patch.object(repo, 'execute_query', return_value=[row]):
            result = repo.get_by_name('momentum_v1')

        assert result is not None
        assert result['strategy_name'] == 'momentum_v1'

    def test_get_by_name_not_found(self, repository):
        """测试策略名称不存在"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[]):
            result = repo.get_by_name('non_existent')

        assert result is None


class TestDynamicStrategyRepositoryList:
    """测试获取策略列表"""

    def test_list_all(self, repository):
        """测试获取所有策略"""
        repo, db, conn, cursor = repository

        count_result = [(5,)]
        list_result = [
            (1, 'strategy1', 'Display1', 'Desc1', 'Class1', 'passed', 'success', True, 'active',
             {}, None, 'claude', ['tag1'], 'cat1', None, None),
            (2, 'strategy2', 'Display2', 'Desc2', 'Class2', 'failed', 'pending', False, 'archived',
             {}, None, 'gpt4', ['tag2'], 'cat2', None, None),
        ]

        with patch.object(repo, 'execute_query', side_effect=[count_result, list_result]):
            result = repo.list()

        assert result['meta']['total'] == 5
        assert len(result['items']) == 2

    def test_list_with_validation_status_filter(self, repository):
        """测试按验证状态过滤"""
        repo, db, conn, cursor = repository

        count_result = [(3,)]
        list_result = [
            (1, 'strategy1', 'Display1', 'Desc1', 'Class1', 'passed', 'success', True, 'active',
             {}, None, 'claude', [], 'cat1', None, None),
        ]

        with patch.object(repo, 'execute_query', side_effect=[count_result, list_result]):
            result = repo.list(validation_status='passed')

        assert result['meta']['total'] == 3

    def test_list_with_pagination(self, repository):
        """测试分页"""
        repo, db, conn, cursor = repository

        count_result = [(100,)]
        list_result = []

        with patch.object(repo, 'execute_query', side_effect=[count_result, list_result]):
            result = repo.list(page=3, page_size=10)

        assert result['meta']['page'] == 3
        assert result['meta']['page_size'] == 10
        assert result['meta']['total_pages'] == 10

    def test_list_with_multiple_filters(self, repository):
        """测试多个过滤条件"""
        repo, db, conn, cursor = repository

        count_result = [(1,)]
        list_result = [
            (1, 'strategy1', 'Display1', 'Desc1', 'Class1', 'passed', 'success', True, 'active',
             {}, None, 'claude', [], 'cat1', None, None),
        ]

        with patch.object(repo, 'execute_query', side_effect=[count_result, list_result]):
            result = repo.list(
                validation_status='passed',
                is_enabled=True,
                status='active'
            )

        assert result['meta']['total'] == 1


class TestDynamicStrategyRepositoryUpdate:
    """测试更新策略"""

    def test_update_success(self, repository):
        """测试成功更新策略"""
        repo, db, conn, cursor = repository

        update_data = {
            'display_name': '新显示名称',
            'description': '新描述',
            'is_enabled': False
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update(1, update_data)

        assert rows_affected == 1

    def test_update_code_updates_hash(self, repository):
        """测试更新代码时自动更新哈希"""
        repo, db, conn, cursor = repository

        update_data = {
            'generated_code': 'print("new code")'
        }

        with patch.object(repo, 'execute_update', return_value=1) as mock_update:
            rows_affected = repo.update(1, update_data)

        assert rows_affected == 1
        # 验证同时更新了code_hash
        call_args = mock_update.call_args[0]
        assert 'code_hash = %s' in call_args[0]

    def test_update_validation_status(self, repository):
        """测试更新验证状态"""
        repo, db, conn, cursor = repository

        update_data = {
            'validation_status': 'failed',
            'validation_errors': {'error': 'syntax error'},
            'validation_warnings': {'warning': 'deprecated API'}
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update(1, update_data)

        assert rows_affected == 1

    def test_update_empty_data(self, repository):
        """测试空更新数据"""
        repo, db, conn, cursor = repository

        rows_affected = repo.update(1, {})

        assert rows_affected == 0

    def test_update_test_results(self, repository):
        """测试更新测试结果"""
        repo, db, conn, cursor = repository

        update_data = {
            'test_status': 'completed',
            'test_results': {
                'passed': 10,
                'failed': 2,
                'errors': ['test error']
            }
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update(1, update_data)

        assert rows_affected == 1


class TestDynamicStrategyRepositoryDelete:
    """测试删除策略"""

    def test_delete_success(self, repository):
        """测试成功删除策略"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_deleted = repo.delete(1)

        assert rows_deleted == 1

    def test_delete_not_found(self, repository):
        """测试删除不存在的策略"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=0):
            rows_deleted = repo.delete(999)

        assert rows_deleted == 0


class TestDynamicStrategyRepositoryBacktestMetrics:
    """测试回测指标更新"""

    def test_update_backtest_metrics_success(self, repository):
        """测试成功更新回测指标"""
        repo, db, conn, cursor = repository

        metrics = {
            'total_return': 0.35,
            'sharpe_ratio': 1.8,
            'max_drawdown': -0.12
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_backtest_metrics(1, metrics)

        assert rows_affected == 1


class TestDynamicStrategyRepositoryUpdateValidationStatus:
    """测试更新验证状态"""

    def test_update_validation_status_success(self, repository):
        """测试成功更新验证状态"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_validation_status(
                strategy_id=1,
                validation_status='passed',
                validation_errors=None,
                validation_warnings={'warning': 'minor issue'}
            )

        assert rows_affected == 1

    def test_update_validation_status_with_errors(self, repository):
        """测试更新验证状态（包含错误）"""
        repo, db, conn, cursor = repository

        errors = {
            'syntax_errors': ['line 10: unexpected token'],
            'security_issues': ['dangerous import']
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_validation_status(
                strategy_id=1,
                validation_status='failed',
                validation_errors=errors
            )

        assert rows_affected == 1

    def test_update_validation_status_clear_errors(self, repository):
        """测试清除验证错误"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_validation_status(
                strategy_id=1,
                validation_status='passed',
                validation_errors=None,
                validation_warnings=None
            )

        assert rows_affected == 1


class TestDynamicStrategyRepositoryCheckNameExists:
    """测试检查策略名称是否存在"""

    def test_check_name_exists_true(self, repository):
        """测试名称已存在"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[(1,)]):
            exists = repo.check_name_exists('existing_strategy')

        assert exists is True

    def test_check_name_exists_false(self, repository):
        """测试名称不存在"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[(0,)]):
            exists = repo.check_name_exists('new_strategy')

        assert exists is False

    def test_check_name_exists_with_exclude(self, repository):
        """测试检查名称时排除特定ID"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[(0,)]) as mock_query:
            exists = repo.check_name_exists('strategy_name', exclude_id=5)

        assert exists is False

        # 验证调用参数包含exclude_id
        mock_query.assert_called_once()
        call_args = mock_query.call_args[0]
        assert len(call_args) == 2  # query and params
        assert 5 in call_args[1]  # exclude_id should be in params

    def test_check_name_exists_duplicate_update(self, repository):
        """测试更新时的重复名称检查"""
        repo, db, conn, cursor = repository

        # 模拟：名称已存在但是同一个策略（排除自己）
        with patch.object(repo, 'execute_query', return_value=[(0,)]):
            exists = repo.check_name_exists('my_strategy', exclude_id=10)

        assert exists is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
