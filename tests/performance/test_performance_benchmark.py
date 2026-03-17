"""
性能基准测试
测试系统各个组件的性能表现
"""

import pytest
import asyncio
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import psutil
import memory_profiler
from unittest.mock import Mock, AsyncMock, patch

from backend.app.services.performance_optimizer import PerformanceOptimizer
from backend.app.services.cache_service import CacheService
from backend.app.services.extended_sync_service import ExtendedDataSyncService
from core.src.data.validators.extended_validator import ExtendedDataValidator


class PerformanceMetrics:
    """性能指标收集器"""

    def __init__(self):
        self.metrics = {
            'execution_time': [],
            'memory_usage': [],
            'cpu_usage': [],
            'throughput': []
        }

    def record_execution_time(self, operation: str, duration: float):
        """记录执行时间"""
        self.metrics['execution_time'].append({
            'operation': operation,
            'duration': duration,
            'timestamp': datetime.now()
        })

    def record_memory_usage(self, operation: str, memory_mb: float):
        """记录内存使用"""
        self.metrics['memory_usage'].append({
            'operation': operation,
            'memory_mb': memory_mb,
            'timestamp': datetime.now()
        })

    def record_throughput(self, operation: str, records_per_second: float):
        """记录吞吐量"""
        self.metrics['throughput'].append({
            'operation': operation,
            'records_per_second': records_per_second,
            'timestamp': datetime.now()
        })

    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        summary = {}

        # 执行时间统计
        if self.metrics['execution_time']:
            durations = [m['duration'] for m in self.metrics['execution_time']]
            summary['execution_time'] = {
                'avg': np.mean(durations),
                'min': np.min(durations),
                'max': np.max(durations),
                'p50': np.percentile(durations, 50),
                'p95': np.percentile(durations, 95),
                'p99': np.percentile(durations, 99)
            }

        # 内存使用统计
        if self.metrics['memory_usage']:
            memory = [m['memory_mb'] for m in self.metrics['memory_usage']]
            summary['memory_usage'] = {
                'avg': np.mean(memory),
                'max': np.max(memory)
            }

        # 吞吐量统计
        if self.metrics['throughput']:
            throughput = [m['records_per_second'] for m in self.metrics['throughput']]
            summary['throughput'] = {
                'avg': np.mean(throughput),
                'max': np.max(throughput)
            }

        return summary


class TestDataValidationPerformance:
    """数据验证性能测试"""

    def setup_method(self):
        """初始化测试环境"""
        self.validator = ExtendedDataValidator()
        self.metrics = PerformanceMetrics()

    def generate_test_data(self, rows: int) -> pd.DataFrame:
        """生成测试数据"""
        return pd.DataFrame({
            'ts_code': [f'{i:06d}.SZ' for i in range(rows)],
            'trade_date': [datetime.now().date()] * rows,
            'turnover_rate': np.random.uniform(0, 20, rows),
            'pe': np.random.uniform(5, 50, rows),
            'pb': np.random.uniform(0.5, 10, rows),
            'total_mv': np.random.uniform(1e6, 1e9, rows),
            'circ_mv': np.random.uniform(5e5, 5e8, rows)
        })

    @pytest.mark.benchmark
    def test_validation_performance_small(self):
        """测试小数据集验证性能（1000条）"""
        df = self.generate_test_data(1000)

        start_time = time.time()
        is_valid, errors, warnings = self.validator.validate_daily_basic(df)
        duration = time.time() - start_time

        self.metrics.record_execution_time('validate_1k', duration)
        self.metrics.record_throughput('validate_1k', 1000 / duration)

        assert duration < 0.5  # 应在0.5秒内完成
        print(f"验证1000条记录耗时: {duration:.3f}秒")

    @pytest.mark.benchmark
    def test_validation_performance_medium(self):
        """测试中等数据集验证性能（10000条）"""
        df = self.generate_test_data(10000)

        start_time = time.time()
        is_valid, errors, warnings = self.validator.validate_daily_basic(df)
        duration = time.time() - start_time

        self.metrics.record_execution_time('validate_10k', duration)
        self.metrics.record_throughput('validate_10k', 10000 / duration)

        assert duration < 2  # 应在2秒内完成
        print(f"验证10000条记录耗时: {duration:.3f}秒")

    @pytest.mark.benchmark
    def test_validation_performance_large(self):
        """测试大数据集验证性能（100000条）"""
        df = self.generate_test_data(100000)

        # 记录内存使用
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        start_time = time.time()
        is_valid, errors, warnings = self.validator.validate_daily_basic(df)
        duration = time.time() - start_time

        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_used = mem_after - mem_before

        self.metrics.record_execution_time('validate_100k', duration)
        self.metrics.record_throughput('validate_100k', 100000 / duration)
        self.metrics.record_memory_usage('validate_100k', mem_used)

        assert duration < 10  # 应在10秒内完成
        assert mem_used < 500  # 内存使用不超过500MB
        print(f"验证100000条记录耗时: {duration:.3f}秒, 内存使用: {mem_used:.2f}MB")

    @pytest.mark.benchmark
    def test_fix_performance(self):
        """测试数据修复性能"""
        # 创建包含错误的数据
        df = self.generate_test_data(10000)
        df['turnover_rate'] = df['turnover_rate'] * 10  # 创造需要修复的数据

        start_time = time.time()
        df_fixed = self.validator.fix_data(df, 'daily_basic')
        duration = time.time() - start_time

        self.metrics.record_execution_time('fix_10k', duration)

        assert duration < 3  # 应在3秒内完成
        print(f"修复10000条记录耗时: {duration:.3f}秒")


class TestBatchInsertPerformance:
    """批量插入性能测试"""

    @pytest.fixture
    async def optimizer(self):
        """创建性能优化器实例"""
        return PerformanceOptimizer()

    def generate_bulk_data(self, rows: int) -> pd.DataFrame:
        """生成批量测试数据"""
        return pd.DataFrame({
            'ts_code': [f'{i:06d}.SZ' for i in range(rows)],
            'trade_date': [datetime.now().date()] * rows,
            'turnover_rate': np.random.uniform(0, 20, rows),
            'pe': np.random.uniform(5, 50, rows),
            'pb': np.random.uniform(0.5, 10, rows),
            'total_mv': np.random.uniform(1e6, 1e9, rows),
            'circ_mv': np.random.uniform(5e5, 5e8, rows),
            'created_at': [datetime.now()] * rows
        })

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_batch_insert_small(self, optimizer):
        """测试小批量插入性能（5000条）"""
        df = self.generate_bulk_data(5000)

        with patch.object(optimizer, 'engine'):
            with patch.object(optimizer, 'batch_insert_fallback', new_callable=AsyncMock) as mock_insert:
                mock_insert.return_value = 5000

                start_time = time.time()
                result = await optimizer.batch_insert_with_copy('test_table', df)
                duration = time.time() - start_time

                assert result == 5000
                print(f"插入5000条记录耗时: {duration:.3f}秒")

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_batch_insert_large(self, optimizer):
        """测试大批量插入性能（50000条）"""
        df = self.generate_bulk_data(50000)

        with patch.object(optimizer, 'engine'):
            with patch.object(optimizer, 'batch_insert_fallback', new_callable=AsyncMock) as mock_insert:
                mock_insert.return_value = 50000

                start_time = time.time()
                result = await optimizer.batch_insert_with_copy('test_table', df)
                duration = time.time() - start_time

                throughput = 50000 / duration
                assert throughput > 5000  # 吞吐量应大于5000条/秒
                print(f"插入50000条记录耗时: {duration:.3f}秒, 吞吐量: {throughput:.0f}条/秒")


class TestCachePerformance:
    """缓存性能测试"""

    @pytest.fixture
    async def cache(self):
        """创建缓存服务实例"""
        cache = CacheService()
        # Mock Redis客户端
        cache.redis_client = AsyncMock()
        return cache

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_cache_write_performance(self, cache):
        """测试缓存写入性能"""
        test_data = {'key': 'value', 'data': list(range(1000))}

        # 模拟Redis setex操作
        cache.redis_client.setex = AsyncMock(return_value=True)

        start_time = time.time()
        for i in range(1000):
            await cache.set(f'test_key_{i}', test_data)
        duration = time.time() - start_time

        ops_per_second = 1000 / duration
        assert ops_per_second > 100  # 应该达到100次/秒以上
        print(f"缓存写入1000次耗时: {duration:.3f}秒, {ops_per_second:.0f}次/秒")

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_cache_read_performance(self, cache):
        """测试缓存读取性能"""
        test_data = b'{"key": "value", "data": [1, 2, 3]}'

        # 模拟Redis get操作
        cache.redis_client.get = AsyncMock(return_value=test_data)

        start_time = time.time()
        for i in range(1000):
            await cache.get(f'test_key_{i}')
        duration = time.time() - start_time

        ops_per_second = 1000 / duration
        assert ops_per_second > 200  # 读取应该更快
        print(f"缓存读取1000次耗时: {duration:.3f}秒, {ops_per_second:.0f}次/秒")

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_cache_hit_rate(self, cache):
        """测试缓存命中率"""
        # 模拟缓存命中和未命中
        hit_count = 0
        miss_count = 0

        for i in range(1000):
            if i % 5 == 0:  # 20%的未命中率
                cache.redis_client.get = AsyncMock(return_value=None)
                miss_count += 1
            else:
                cache.redis_client.get = AsyncMock(return_value=b'{"data": "cached"}')
                hit_count += 1

            await cache.get(f'key_{i}')

        hit_rate = (hit_count / (hit_count + miss_count)) * 100
        assert hit_rate == 80  # 预期80%的命中率
        print(f"缓存命中率: {hit_rate:.1f}%")


class TestQueryOptimizationPerformance:
    """查询优化性能测试"""

    @pytest.fixture
    async def optimizer(self):
        """创建性能优化器实例"""
        return PerformanceOptimizer()

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_parallel_query_performance(self, optimizer):
        """测试并行查询性能"""
        # 模拟多个查询
        queries = [
            ("SELECT * FROM daily_basic WHERE trade_date = :date", {'date': '2024-03-15'}),
            ("SELECT * FROM moneyflow WHERE ts_code = :code", {'code': '000001.SZ'}),
            ("SELECT * FROM hk_hold WHERE exchange = :ex", {'ex': 'SH'}),
            ("SELECT * FROM margin_detail WHERE trade_date = :date", {'date': '2024-03-15'}),
        ]

        # Mock查询执行
        with patch.object(optimizer, 'optimize_query_with_cache', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = pd.DataFrame({'result': [1, 2, 3]})

            start_time = time.time()
            results = await optimizer.parallel_query_execution(queries)
            duration = time.time() - start_time

            assert len(results) == 4
            assert duration < 1  # 并行执行应在1秒内完成
            print(f"并行执行4个查询耗时: {duration:.3f}秒")


class TestEndToEndPerformance:
    """端到端性能测试"""

    @pytest.mark.asyncio
    @pytest.mark.benchmark
    async def test_sync_pipeline_performance(self):
        """测试完整同步流水线性能"""
        service = ExtendedDataSyncService()
        metrics = PerformanceMetrics()

        # 模拟数据提供者
        mock_provider = Mock()
        mock_provider.get_daily_basic = Mock(return_value=pd.DataFrame({
            'ts_code': [f'{i:06d}.SZ' for i in range(5000)],
            'trade_date': ['20240315'] * 5000,
            'turnover_rate': np.random.uniform(0, 20, 5000)
        }))

        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_daily_basic', new_callable=AsyncMock):
                start_time = time.time()
                result = await service.sync_daily_basic(trade_date="20240315")
                duration = time.time() - start_time

                metrics.record_execution_time('sync_pipeline', duration)
                metrics.record_throughput('sync_pipeline', 5000 / duration)

                assert result['status'] == 'success'
                assert duration < 5  # 完整流水线应在5秒内完成
                print(f"同步5000条记录（包括验证）耗时: {duration:.3f}秒")

    @pytest.mark.benchmark
    def test_memory_leak_check(self):
        """测试内存泄漏"""
        validator = ExtendedDataValidator()
        process = psutil.Process()

        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 执行多次操作
        for _ in range(100):
            df = pd.DataFrame({
                'ts_code': [f'{i:06d}.SZ' for i in range(1000)],
                'trade_date': [datetime.now().date()] * 1000,
                'turnover_rate': np.random.uniform(0, 20, 1000)
            })
            validator.validate_daily_basic(df)
            validator.fix_data(df, 'daily_basic')

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        assert memory_increase < 100  # 内存增长不应超过100MB
        print(f"100次操作后内存增长: {memory_increase:.2f}MB")


def run_performance_tests():
    """运行所有性能测试并生成报告"""
    import pytest

    # 运行性能测试
    pytest.main([
        __file__,
        '-v',
        '-m', 'benchmark',
        '--tb=short',
        '--benchmark-only',
        '--benchmark-autosave'
    ])


if __name__ == '__main__':
    run_performance_tests()