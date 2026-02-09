"""
StrategyConfigRepository 单元测试

测试策略配置数据访问层的所有功能。

作者: Backend Team
创建日期: 2026-02-09
版本: 1.0.0
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

import pytest

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.repositories.strategy_config_repository import StrategyConfigRepository


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
    repo = StrategyConfigRepository()
    repo.db = db
    return repo, db, conn, cursor


@pytest.fixture
def sample_config_data():
    """示例配置数据"""
    return {
        'strategy_type': 'momentum',
        'config': {'lookback_period': 20, 'top_n': 10},
        'name': '动量策略配置',
        'description': '基于动量因子的选股策略',
        'category': 'factor',
        'tags': ['momentum', 'factor'],
        'created_by': 'admin'
    }


@pytest.fixture
def sample_config_row():
    """示例配置数据库行"""
    return (
        1,  # id
        'momentum',  # strategy_type
        {'lookback_period': 20, 'top_n': 10},  # config
        '动量策略配置',  # name
        '基于动量因子的选股策略',  # description
        'factor',  # category
        ['momentum', 'factor'],  # tags
        True,  # is_enabled
        'active',  # status
        1,  # version
        None,  # parent_id
        {'sharpe_ratio': 1.5},  # last_backtest_metrics
        None,  # last_backtest_date
        'admin',  # created_by
        None,  # created_at
        None,  # updated_by
        None  # updated_at
    )


class TestStrategyConfigRepositoryCreate:
    """测试创建策略配置"""

    def test_create_success(self, repository, sample_config_data):
        """测试成功创建配置"""
        repo, db, conn, cursor = repository

        # 模拟数据库返回新ID
        cursor.fetchone.return_value = (123,)

        # 执行创建
        config_id = repo.create(sample_config_data)

        # 验证
        assert config_id == 123
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()
        cursor.close.assert_called_once()
        db.release_connection.assert_called_with(conn)

    def test_create_minimal_data(self, repository):
        """测试使用最小数据创建配置"""
        repo, db, conn, cursor = repository
        cursor.fetchone.return_value = (456,)

        minimal_data = {
            'strategy_type': 'value',
            'config': {'pb_threshold': 1.5}
        }

        config_id = repo.create(minimal_data)

        assert config_id == 456
        cursor.execute.assert_called_once()

    def test_create_with_tags(self, repository):
        """测试创建包含标签的配置"""
        repo, db, conn, cursor = repository
        cursor.fetchone.return_value = (789,)

        data = {
            'strategy_type': 'multi_factor',
            'config': {},
            'tags': ['alpha', 'quality', 'momentum']
        }

        config_id = repo.create(data)

        assert config_id == 789


class TestStrategyConfigRepositoryGetById:
    """测试根据ID获取配置"""

    def test_get_by_id_success(self, repository, sample_config_row):
        """测试成功获取配置"""
        repo, db, conn, cursor = repository

        # 模拟数据库返回
        with patch.object(repo, 'execute_query', return_value=[sample_config_row]):
            result = repo.get_by_id(1)

        # 验证
        assert result is not None
        assert result['id'] == 1
        assert result['strategy_type'] == 'momentum'
        assert result['name'] == '动量策略配置'
        assert result['config'] == {'lookback_period': 20, 'top_n': 10}
        assert result['tags'] == ['momentum', 'factor']

    def test_get_by_id_not_found(self, repository):
        """测试配置不存在"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[]):
            result = repo.get_by_id(999)

        assert result is None

    def test_get_by_id_empty_tags(self, repository):
        """测试空标签处理"""
        repo, db, conn, cursor = repository

        row = (
            1, 'momentum', {}, 'Config', 'Desc', 'factor',
            None,  # tags为None
            True, 'active', 1, None, {}, None,
            'admin', None, None, None
        )

        with patch.object(repo, 'execute_query', return_value=[row]):
            result = repo.get_by_id(1)

        assert result['tags'] == []


class TestStrategyConfigRepositoryList:
    """测试获取配置列表"""

    def test_list_all(self, repository):
        """测试获取所有配置"""
        repo, db, conn, cursor = repository

        # 模拟总数查询
        count_result = [(10,)]
        # 模拟列表查询
        list_result = [
            (1, 'momentum', {}, 'Config 1', 'Desc 1', 'factor', ['tag1'], True, 'active', {}, None, None, None),
            (2, 'value', {}, 'Config 2', 'Desc 2', 'factor', ['tag2'], True, 'active', {}, None, None, None),
        ]

        with patch.object(repo, 'execute_query', side_effect=[count_result, list_result]):
            result = repo.list()

        assert result['meta']['total'] == 10
        assert len(result['items']) == 2
        assert result['items'][0]['id'] == 1
        assert result['items'][1]['id'] == 2

    def test_list_with_strategy_type_filter(self, repository):
        """测试按策略类型过滤"""
        repo, db, conn, cursor = repository

        count_result = [(5,)]
        list_result = [
            (1, 'momentum', {}, 'Config 1', 'Desc 1', 'factor', [], True, 'active', {}, None, None, None),
        ]

        with patch.object(repo, 'execute_query', side_effect=[count_result, list_result]):
            result = repo.list(strategy_type='momentum')

        assert result['meta']['total'] == 5

    def test_list_with_enabled_filter(self, repository):
        """测试按启用状态过滤"""
        repo, db, conn, cursor = repository

        count_result = [(3,)]
        list_result = [
            (1, 'momentum', {}, 'Config 1', 'Desc 1', 'factor', [], True, 'active', {}, None, None, None),
        ]

        with patch.object(repo, 'execute_query', side_effect=[count_result, list_result]):
            result = repo.list(is_enabled=True)

        assert result['meta']['total'] == 3

    def test_list_with_status_filter(self, repository):
        """测试按状态过滤"""
        repo, db, conn, cursor = repository

        count_result = [(2,)]
        list_result = []

        with patch.object(repo, 'execute_query', side_effect=[count_result, list_result]):
            result = repo.list(status='archived')

        assert result['meta']['total'] == 2

    def test_list_with_pagination(self, repository):
        """测试分页"""
        repo, db, conn, cursor = repository

        count_result = [(100,)]
        list_result = []

        with patch.object(repo, 'execute_query', side_effect=[count_result, list_result]):
            result = repo.list(page=2, page_size=20)

        assert result['meta']['page'] == 2
        assert result['meta']['page_size'] == 20
        assert result['meta']['total_pages'] == 5

    def test_list_with_multiple_filters(self, repository):
        """测试多个过滤条件"""
        repo, db, conn, cursor = repository

        count_result = [(1,)]
        list_result = [
            (1, 'momentum', {}, 'Config 1', 'Desc 1', 'factor', [], True, 'active', {}, None, None, None),
        ]

        with patch.object(repo, 'execute_query', side_effect=[count_result, list_result]):
            result = repo.list(
                strategy_type='momentum',
                is_enabled=True,
                status='active',
                page=1,
                page_size=10
            )

        assert result['meta']['total'] == 1


class TestStrategyConfigRepositoryUpdate:
    """测试更新配置"""

    def test_update_success(self, repository):
        """测试成功更新配置"""
        repo, db, conn, cursor = repository

        update_data = {
            'name': '新名称',
            'description': '新描述',
            'is_enabled': False
        }

        with patch.object(repo, 'execute_update', return_value=1) as mock_update:
            rows_affected = repo.update(1, update_data)

        assert rows_affected == 1
        mock_update.assert_called_once()

    def test_update_config_json(self, repository):
        """测试更新配置JSON"""
        repo, db, conn, cursor = repository

        update_data = {
            'config': {'lookback_period': 30, 'top_n': 20}
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update(1, update_data)

        assert rows_affected == 1

    def test_update_empty_data(self, repository):
        """测试空更新数据"""
        repo, db, conn, cursor = repository

        rows_affected = repo.update(1, {})

        assert rows_affected == 0

    def test_update_tags(self, repository):
        """测试更新标签"""
        repo, db, conn, cursor = repository

        update_data = {
            'tags': ['new_tag1', 'new_tag2', 'new_tag3']
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update(1, update_data)

        assert rows_affected == 1

    def test_update_with_updated_by(self, repository):
        """测试更新时记录更新人"""
        repo, db, conn, cursor = repository

        update_data = {
            'name': '修改后的名称',
            'updated_by': 'admin'
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update(1, update_data)

        assert rows_affected == 1

    def test_update_invalid_field(self, repository):
        """测试更新不允许的字段（应被忽略）"""
        repo, db, conn, cursor = repository

        update_data = {
            'name': '新名称',
            'invalid_field': 'should be ignored'
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update(1, update_data)

        assert rows_affected == 1


class TestStrategyConfigRepositoryDelete:
    """测试删除配置"""

    def test_delete_success(self, repository):
        """测试成功删除配置"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_deleted = repo.delete(1)

        assert rows_deleted == 1

    def test_delete_not_found(self, repository):
        """测试删除不存在的配置"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=0):
            rows_deleted = repo.delete(999)

        assert rows_deleted == 0


class TestStrategyConfigRepositoryBacktestMetrics:
    """测试回测指标更新"""

    def test_update_backtest_metrics_success(self, repository):
        """测试成功更新回测指标"""
        repo, db, conn, cursor = repository

        metrics = {
            'total_return': 0.25,
            'sharpe_ratio': 1.5,
            'max_drawdown': -0.15
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_backtest_metrics(1, metrics)

        assert rows_affected == 1

    def test_update_backtest_metrics_empty(self, repository):
        """测试更新空指标"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_backtest_metrics(1, {})

        assert rows_affected == 1


class TestStrategyConfigRepositoryGetByStrategyType:
    """测试按策略类型获取配置"""

    def test_get_by_strategy_type_success(self, repository):
        """测试成功获取指定类型的配置"""
        repo, db, conn, cursor = repository

        result_rows = [
            (1, 'momentum', {}, 'Config 1', 'Desc 1', 'factor', ['tag1'], {}, None),
            (2, 'momentum', {}, 'Config 2', 'Desc 2', 'factor', ['tag2'], {}, None),
        ]

        with patch.object(repo, 'execute_query', return_value=result_rows):
            result = repo.get_by_strategy_type('momentum', limit=10)

        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[1]['id'] == 2

    def test_get_by_strategy_type_with_limit(self, repository):
        """测试限制返回数量"""
        repo, db, conn, cursor = repository

        result_rows = [
            (1, 'value', {}, 'Config 1', 'Desc 1', 'factor', [], {}, None),
        ]

        with patch.object(repo, 'execute_query', return_value=result_rows):
            result = repo.get_by_strategy_type('value', limit=5)

        assert len(result) == 1

    def test_get_by_strategy_type_empty(self, repository):
        """测试没有匹配的配置"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[]):
            result = repo.get_by_strategy_type('non_existent', limit=10)

        assert len(result) == 0

    def test_get_by_strategy_type_null_tags(self, repository):
        """测试空标签处理"""
        repo, db, conn, cursor = repository

        result_rows = [
            (1, 'momentum', {}, 'Config 1', 'Desc 1', 'factor', None, {}, None),
        ]

        with patch.object(repo, 'execute_query', return_value=result_rows):
            result = repo.get_by_strategy_type('momentum')

        assert result[0]['tags'] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
