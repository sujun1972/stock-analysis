"""
StrategyExecutionRepository 单元测试

测试策略执行记录数据访问层的所有功能。

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

from app.repositories.strategy_execution_repository import StrategyExecutionRepository


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
    repo = StrategyExecutionRepository()
    repo.db = db
    return repo, db, conn, cursor


@pytest.fixture
def sample_execution_data():
    """示例执行记录数据"""
    return {
        'execution_type': 'backtest',
        'execution_params': {
            'stock_pool': ['000001', '600000'],
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'initial_capital': 1000000
        },
        'config_strategy_id': 1,
        'executed_by': 'user123'
    }


class TestStrategyExecutionRepositoryCreate:
    """测试创建执行记录"""

    def test_create_success(self, repository, sample_execution_data):
        """测试成功创建执行记录"""
        repo, db, conn, cursor = repository

        cursor.fetchone.return_value = (123,)

        execution_id = repo.create(sample_execution_data)

        assert execution_id == 123
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()
        cursor.close.assert_called_once()
        db.release_connection.assert_called_with(conn)

    def test_create_predefined_strategy(self, repository):
        """测试创建预定义策略执行记录"""
        repo, db, conn, cursor = repository
        cursor.fetchone.return_value = (456,)

        data = {
            'execution_type': 'backtest',
            'execution_params': {'param1': 'value1'},
            'predefined_strategy_type': 'momentum'
        }

        execution_id = repo.create(data)

        assert execution_id == 456

    def test_create_dynamic_strategy(self, repository):
        """测试创建动态策略执行记录"""
        repo, db, conn, cursor = repository
        cursor.fetchone.return_value = (789,)

        data = {
            'execution_type': 'test',
            'execution_params': {},
            'dynamic_strategy_id': 10
        }

        execution_id = repo.create(data)

        assert execution_id == 789

    def test_create_minimal_data(self, repository):
        """测试使用最小数据创建"""
        repo, db, conn, cursor = repository
        cursor.fetchone.return_value = (999,)

        minimal_data = {
            'execution_type': 'backtest',
            'execution_params': {}
        }

        execution_id = repo.create(minimal_data)

        assert execution_id == 999


class TestStrategyExecutionRepositoryGetById:
    """测试根据ID获取执行记录"""

    def test_get_by_id_success(self, repository):
        """测试成功获取执行记录"""
        repo, db, conn, cursor = repository

        row = (
            1, 'momentum', 2, None, 'backtest', '{}', 'completed',
            '{}', '{}', None, 1500, 'user123', None, None, None
        )

        with patch.object(repo, 'execute_query', return_value=[row]):
            result = repo.get_by_id(1)

        assert result is not None
        assert result['id'] == 1
        assert result['predefined_strategy_type'] == 'momentum'
        assert result['config_strategy_id'] == 2
        assert result['execution_type'] == 'backtest'
        assert result['status'] == 'completed'

    def test_get_by_id_not_found(self, repository):
        """测试执行记录不存在"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[]):
            result = repo.get_by_id(999)

        assert result is None

    def test_get_by_id_with_dates(self, repository):
        """测试包含日期的执行记录"""
        repo, db, conn, cursor = repository

        from datetime import datetime

        started_at = datetime(2023, 1, 1, 10, 0, 0)
        completed_at = datetime(2023, 1, 1, 10, 5, 0)
        created_at = datetime(2023, 1, 1, 10, 0, 0)

        row = (
            1, None, None, 5, 'backtest', '{}', 'completed',
            '{}', '{}', None, 300000, 'user123',
            started_at, completed_at, created_at
        )

        with patch.object(repo, 'execute_query', return_value=[row]):
            result = repo.get_by_id(1)

        assert result['started_at'] is not None
        assert result['completed_at'] is not None
        assert result['execution_duration_ms'] == 300000


class TestStrategyExecutionRepositoryListByConfigStrategy:
    """测试获取配置策略的执行记录列表"""

    def test_list_by_config_strategy_success(self, repository):
        """测试成功获取配置策略执行记录"""
        repo, db, conn, cursor = repository

        from datetime import datetime

        dt = datetime(2023, 1, 1)

        result_rows = [
            (1, 'backtest', 'completed', '{}', 1500, dt, dt, dt),
            (2, 'test', 'failed', '{}', 500, dt, dt, dt),
        ]

        with patch.object(repo, 'execute_query', return_value=result_rows):
            result = repo.list_by_config_strategy(config_strategy_id=1, limit=20)

        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[0]['execution_type'] == 'backtest'
        assert result[1]['status'] == 'failed'

    def test_list_by_config_strategy_with_limit(self, repository):
        """测试限制返回数量"""
        repo, db, conn, cursor = repository

        result_rows = []

        with patch.object(repo, 'execute_query', return_value=result_rows):
            result = repo.list_by_config_strategy(config_strategy_id=1, limit=5)

        assert len(result) == 0

    def test_list_by_config_strategy_empty(self, repository):
        """测试没有执行记录"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[]):
            result = repo.list_by_config_strategy(config_strategy_id=999)

        assert len(result) == 0


class TestStrategyExecutionRepositoryListByDynamicStrategy:
    """测试获取动态策略的执行记录列表"""

    def test_list_by_dynamic_strategy_success(self, repository):
        """测试成功获取动态策略执行记录"""
        repo, db, conn, cursor = repository

        from datetime import datetime

        dt = datetime(2023, 1, 1)

        result_rows = [
            (1, 'backtest', 'completed', '{}', 2000, dt, dt, dt),
        ]

        with patch.object(repo, 'execute_query', return_value=result_rows):
            result = repo.list_by_dynamic_strategy(dynamic_strategy_id=5, limit=20)

        assert len(result) == 1
        assert result[0]['execution_type'] == 'backtest'

    def test_list_by_dynamic_strategy_empty(self, repository):
        """测试没有执行记录"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[]):
            result = repo.list_by_dynamic_strategy(dynamic_strategy_id=999)

        assert len(result) == 0


class TestStrategyExecutionRepositoryUpdateStatus:
    """测试更新执行状态"""

    def test_update_status_running(self, repository):
        """测试更新状态为running"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_status(execution_id=1, status='running')

        assert rows_affected == 1

    def test_update_status_completed(self, repository):
        """测试更新状态为completed"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_status(
                execution_id=1,
                status='completed',
                error_message=None
            )

        assert rows_affected == 1

    def test_update_status_failed_with_error(self, repository):
        """测试更新状态为failed并记录错误"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_status(
                execution_id=1,
                status='failed',
                error_message='数据加载失败'
            )

        assert rows_affected == 1

    def test_update_status_cancelled(self, repository):
        """测试更新状态为cancelled"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_status(
                execution_id=1,
                status='cancelled'
            )

        assert rows_affected == 1

    def test_update_status_pending(self, repository):
        """测试更新状态为pending"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_status(
                execution_id=1,
                status='pending'
            )

        assert rows_affected == 1


class TestStrategyExecutionRepositoryUpdateResult:
    """测试更新执行结果"""

    def test_update_result_success(self, repository):
        """测试成功更新执行结果"""
        repo, db, conn, cursor = repository

        result_data = {
            'equity_curve': [{'date': '2023-01-01', 'value': 1000000}],
            'trades': [],
            'positions': []
        }

        metrics = {
            'total_return': 0.25,
            'sharpe_ratio': 1.5,
            'max_drawdown': -0.15
        }

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_result(
                execution_id=1,
                result=result_data,
                metrics=metrics
            )

        assert rows_affected == 1

    def test_update_result_empty_metrics(self, repository):
        """测试更新空指标"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_update', return_value=1):
            rows_affected = repo.update_result(
                execution_id=1,
                result={},
                metrics={}
            )

        assert rows_affected == 1


class TestStrategyExecutionRepositoryGetStatistics:
    """测试获取执行统计"""

    def test_get_statistics_all(self, repository):
        """测试获取所有执行的统计信息"""
        repo, db, conn, cursor = repository

        stat_row = [(100, 80, 15, 3, 2, 1500.5)]

        with patch.object(repo, 'execute_query', return_value=stat_row):
            result = repo.get_statistics()

        assert result['total'] == 100
        assert result['completed'] == 80
        assert result['failed'] == 15
        assert result['running'] == 3
        assert result['pending'] == 2
        assert result['avg_duration_ms'] == 1500.5

    def test_get_statistics_by_config_strategy(self, repository):
        """测试获取特定配置策略的统计信息"""
        repo, db, conn, cursor = repository

        stat_row = [(50, 45, 5, 0, 0, 1200.0)]

        with patch.object(repo, 'execute_query', return_value=stat_row):
            result = repo.get_statistics(config_strategy_id=1)

        assert result['total'] == 50
        assert result['completed'] == 45

    def test_get_statistics_by_dynamic_strategy(self, repository):
        """测试获取特定动态策略的统计信息"""
        repo, db, conn, cursor = repository

        stat_row = [(30, 25, 3, 1, 1, 1800.0)]

        with patch.object(repo, 'execute_query', return_value=stat_row):
            result = repo.get_statistics(dynamic_strategy_id=5)

        assert result['total'] == 30

    def test_get_statistics_by_execution_type(self, repository):
        """测试按执行类型获取统计信息"""
        repo, db, conn, cursor = repository

        stat_row = [(20, 18, 2, 0, 0, 2000.0)]

        with patch.object(repo, 'execute_query', return_value=stat_row):
            result = repo.get_statistics(execution_type='backtest')

        assert result['total'] == 20

    def test_get_statistics_multiple_filters(self, repository):
        """测试使用多个过滤条件"""
        repo, db, conn, cursor = repository

        stat_row = [(10, 9, 1, 0, 0, 1500.0)]

        with patch.object(repo, 'execute_query', return_value=stat_row):
            result = repo.get_statistics(
                config_strategy_id=1,
                execution_type='test'
            )

        assert result['total'] == 10

    def test_get_statistics_empty_result(self, repository):
        """测试没有数据的统计"""
        repo, db, conn, cursor = repository

        with patch.object(repo, 'execute_query', return_value=[]):
            result = repo.get_statistics()

        assert result == {}

    def test_get_statistics_null_avg_duration(self, repository):
        """测试平均时长为NULL的情况"""
        repo, db, conn, cursor = repository

        stat_row = [(5, 0, 0, 5, 0, None)]

        with patch.object(repo, 'execute_query', return_value=stat_row):
            result = repo.get_statistics()

        assert result['avg_duration_ms'] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
