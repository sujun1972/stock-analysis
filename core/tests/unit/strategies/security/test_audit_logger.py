"""
AuditLogger 单元测试

测试审计日志记录器的功能
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from strategies.security.audit_logger import AuditLogger


class TestAuditLogger:
    """测试 AuditLogger 类"""

    @pytest.fixture
    def temp_log_dir(self):
        """创建临时日志目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # 清理
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def audit_logger(self, temp_log_dir):
        """创建 AuditLogger 实例"""
        return AuditLogger(log_dir=temp_log_dir)

    def test_initialization(self, audit_logger, temp_log_dir):
        """测试初始化"""
        assert audit_logger.log_dir == Path(temp_log_dir)
        assert audit_logger.log_dir.exists()
        # 审计文件在第一次写入时才创建
        assert audit_logger.audit_file is not None

    def test_log_strategy_load(self, audit_logger):
        """测试记录策略加载事件"""
        validation_result = {
            'safe': True,
            'risk_level': 'safe',
            'errors': [],
            'warnings': []
        }

        audit_logger.log_strategy_load(
            strategy_id=123,
            strategy_type='dynamic',
            strategy_class='CustomStrategy',
            code_hash='abc123',
            validation_result=validation_result,
            user='test_user'
        )

        # 验证日志文件存在且包含事件
        assert audit_logger.audit_file.exists()

        # 读取并验证日志内容
        with open(audit_logger.audit_file, 'r') as f:
            log_line = f.readline()
            event = json.loads(log_line)

            assert event['event_type'] == 'strategy_load'
            assert event['strategy_id'] == 123
            assert event['strategy_type'] == 'dynamic'
            assert event['strategy_class'] == 'CustomStrategy'
            assert event['code_hash'] == 'abc123'
            assert event['user'] == 'test_user'

    def test_log_strategy_execution(self, audit_logger):
        """测试记录策略执行事件"""
        execution_params = {'param1': 'value1'}
        execution_result = {'result': 'success'}

        audit_logger.log_strategy_execution(
            strategy_id=456,
            execution_type='backtest',
            execution_params=execution_params,
            execution_result=execution_result,
            duration_ms=1234.5,
            success=True
        )

        # 验证日志
        with open(audit_logger.audit_file, 'r') as f:
            log_line = f.readline()
            event = json.loads(log_line)

            assert event['event_type'] == 'strategy_execution'
            assert event['strategy_id'] == 456
            assert event['execution_type'] == 'backtest'
            assert event['duration_ms'] == 1234.5
            assert event['success'] is True

    def test_log_security_violation(self, audit_logger):
        """测试记录安全违规事件"""
        details = {
            'violation': 'forbidden_import',
            'module': 'os'
        }

        audit_logger.log_security_violation(
            strategy_id=789,
            violation_type='forbidden_import',
            details=details
        )

        # 验证日志
        with open(audit_logger.audit_file, 'r') as f:
            log_line = f.readline()
            event = json.loads(log_line)

            assert event['event_type'] == 'security_violation'
            assert event['strategy_id'] == 789
            assert event['violation_type'] == 'forbidden_import'
            assert event['severity'] == 'high'

    def test_log_cache_event(self, audit_logger):
        """测试记录缓存事件"""
        audit_logger.log_cache_event(
            event_type='hit',
            strategy_id=111,
            cache_key='strategy_111',
            hit=True
        )

        # 验证日志
        with open(audit_logger.audit_file, 'r') as f:
            log_line = f.readline()
            event = json.loads(log_line)

            assert event['event_type'] == 'cache_hit'
            assert event['strategy_id'] == 111
            assert event['hit'] is True

    def test_log_resource_usage(self, audit_logger):
        """测试记录资源使用事件"""
        usage = {
            'memory_mb': 256,
            'cpu_percent': 45.5
        }

        audit_logger.log_resource_usage(
            strategy_id=222,
            resource_type='memory',
            usage=usage
        )

        # 验证日志
        with open(audit_logger.audit_file, 'r') as f:
            log_line = f.readline()
            event = json.loads(log_line)

            assert event['event_type'] == 'resource_usage'
            assert event['strategy_id'] == 222
            assert event['resource_type'] == 'memory'

    def test_query_events_no_filter(self, audit_logger):
        """测试查询事件 - 无过滤"""
        # 添加多个事件
        for i in range(5):
            audit_logger.log_cache_event(
                event_type='hit',
                strategy_id=i,
                cache_key=f'key_{i}'
            )

        # 查询所有事件
        events = audit_logger.query_events()

        assert len(events) == 5

    def test_query_events_by_type(self, audit_logger):
        """测试查询事件 - 按类型过滤"""
        # 添加不同类型的事件
        audit_logger.log_cache_event('hit', 1, 'key1')
        audit_logger.log_cache_event('miss', 2, 'key2')
        audit_logger.log_security_violation(3, 'violation1', {})

        # 查询特定类型
        cache_events = audit_logger.query_events(event_type='cache_hit')
        security_events = audit_logger.query_events(event_type='security_violation')

        assert len(cache_events) == 1
        assert len(security_events) == 1

    def test_query_events_by_strategy_id(self, audit_logger):
        """测试查询事件 - 按策略ID过滤"""
        # 添加不同策略的事件
        audit_logger.log_cache_event('hit', 111, 'key1')
        audit_logger.log_cache_event('hit', 222, 'key2')
        audit_logger.log_cache_event('hit', 111, 'key3')

        # 查询特定策略的事件
        strategy_111_events = audit_logger.query_events(strategy_id=111)

        assert len(strategy_111_events) == 2
        assert all(e['strategy_id'] == 111 for e in strategy_111_events)

    def test_query_events_with_limit(self, audit_logger):
        """测试查询事件 - 限制数量"""
        # 添加多个事件
        for i in range(10):
            audit_logger.log_cache_event('hit', i, f'key_{i}')

        # 查询限制为5个
        events = audit_logger.query_events(limit=5)

        assert len(events) == 5

    def test_get_statistics(self, audit_logger):
        """测试获取统计信息"""
        # 添加各种事件
        audit_logger.log_strategy_load(1, 'dynamic', 'Class1', 'hash1', {})
        audit_logger.log_strategy_load(2, 'dynamic', 'Class2', 'hash2', {})

        audit_logger.log_strategy_execution(
            1, 'backtest', {}, {}, 100, True
        )
        audit_logger.log_strategy_execution(
            1, 'backtest', {}, {}, 200, False, 'error'
        )

        audit_logger.log_security_violation(1, 'violation', {})

        audit_logger.log_cache_event('hit', 1, 'key1', True)
        audit_logger.log_cache_event('miss', 1, 'key2', False)

        # 获取统计
        stats = audit_logger.get_statistics()

        assert stats['total_events'] == 7
        assert stats['strategy_loads'] == 2
        assert stats['strategy_executions'] == 2
        assert stats['security_violations'] == 1
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1
        assert stats['errors'] == 1

    def test_get_statistics_with_strategy_filter(self, audit_logger):
        """测试获取统计信息 - 按策略过滤"""
        # 添加不同策略的事件
        audit_logger.log_cache_event('hit', 111, 'key1')
        audit_logger.log_cache_event('hit', 222, 'key2')
        audit_logger.log_cache_event('hit', 111, 'key3')

        # 获取特定策略的统计
        stats = audit_logger.get_statistics(strategy_id=111)

        assert stats['total_events'] == 2

    def test_multiple_events_same_file(self, audit_logger):
        """测试同一文件中写入多个事件"""
        # 写入多个事件
        audit_logger.log_cache_event('hit', 1, 'key1')
        audit_logger.log_cache_event('miss', 2, 'key2')
        audit_logger.log_security_violation(3, 'violation', {})

        # 验证文件包含3行
        with open(audit_logger.audit_file, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3

    def test_timestamp_format(self, audit_logger):
        """测试时间戳格式"""
        audit_logger.log_cache_event('hit', 1, 'key1')

        # 读取事件
        with open(audit_logger.audit_file, 'r') as f:
            event = json.loads(f.readline())

        # 验证时间戳可以解析
        timestamp = datetime.fromisoformat(event['timestamp'])
        assert isinstance(timestamp, datetime)

    def test_log_dir_creation(self, temp_log_dir):
        """测试日志目录自动创建"""
        new_log_dir = Path(temp_log_dir) / 'subdir' / 'audit'
        logger = AuditLogger(log_dir=str(new_log_dir))

        assert new_log_dir.exists()
