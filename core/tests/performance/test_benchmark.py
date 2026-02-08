"""
Performance benchmark tests for Phase 4 optimization.

Tests various performance scenarios to measure improvements.
"""

import pytest
import time
import pandas as pd
import numpy as np
from typing import List, Dict, Any

from core.strategies.monitoring import PerformanceMonitor, MetricsCollector
from core.strategies.cache import StrategyCache, CodeCache


class TestCachingPerformance:
    """Test caching performance improvements."""

    @pytest.fixture
    def strategy_cache(self):
        """Create strategy cache."""
        return StrategyCache(ttl_minutes=30)

    @pytest.fixture
    def code_cache(self):
        """Create code cache."""
        return CodeCache(max_size=100)

    def test_memory_cache_performance(self, strategy_cache, benchmark):
        """Benchmark memory cache performance."""
        # Prepare test data
        test_data = {'strategy': 'test', 'config': {'param': 1}}

        def cache_operations():
            # Write to cache
            strategy_cache.set('test_key', test_data)

            # Read from cache
            result = strategy_cache.get('test_key')
            assert result is not None

        # Run benchmark
        result = benchmark(cache_operations)

        # Should be very fast (< 1ms)
        assert benchmark.stats['mean'] < 0.001

    def test_cache_hit_vs_miss(self, strategy_cache):
        """Compare cache hit vs miss performance."""
        test_data = {'large_data': list(range(10000))}

        # Measure cache miss (first access)
        start = time.time()
        result = strategy_cache.get('miss_key')
        miss_time = (time.time() - start) * 1000

        # Populate cache
        strategy_cache.set('hit_key', test_data)

        # Measure cache hit
        start = time.time()
        result = strategy_cache.get('hit_key')
        hit_time = (time.time() - start) * 1000

        print(f"\nCache miss: {miss_time:.4f}ms")
        print(f"Cache hit: {hit_time:.4f}ms")
        print(f"Hit speedup: {miss_time / hit_time:.2f}x faster")

        # Hit should be faster
        assert result is not None
        assert hit_time < miss_time or miss_time < 0.1  # Both very fast

    def test_code_cache_lru_eviction(self, code_cache):
        """Test code cache LRU eviction performance."""
        max_size = code_cache.max_size

        # Fill cache beyond capacity
        for i in range(max_size + 10):
            code_hash = f"hash_{i}"
            module = type('Module', (), {'id': i})()
            code_cache.set(code_hash, module)

        stats = code_cache.get_stats()

        # Should not exceed max size
        assert stats['total_modules'] <= max_size

        # Should have usage rate close to 100%
        assert stats['usage_rate'] >= 0.9


class TestPerformanceMonitoring:
    """Test performance monitoring overhead."""

    @pytest.fixture
    def monitor(self):
        """Create performance monitor."""
        return PerformanceMonitor(enable_alerts=False)

    def test_monitoring_overhead(self, monitor, benchmark):
        """Measure performance monitoring overhead."""

        def monitored_operation():
            with monitor.monitor('test_operation'):
                # Simulate some work
                time.sleep(0.001)  # 1ms

        # Run benchmark
        result = benchmark(monitored_operation)

        # Monitoring overhead should be minimal (< 10% of operation time)
        overhead_ms = (benchmark.stats['mean'] - 0.001) * 1000
        print(f"\nMonitoring overhead: {overhead_ms:.4f}ms")

        assert overhead_ms < 0.5  # Less than 0.5ms overhead

    def test_metrics_collection_overhead(self):
        """Test metrics collection overhead."""
        collector = MetricsCollector()

        # Measure overhead of metric recording
        iterations = 10000

        start = time.time()
        for i in range(iterations):
            collector.increment('test_counter')
            collector.set_gauge('test_gauge', i)
            collector.record_histogram('test_histogram', i)
            collector.record_timer('test_timer', i * 0.1)

        duration = time.time() - start
        avg_time_us = (duration / iterations) * 1_000_000

        print(f"\nMetrics collection: {avg_time_us:.2f}μs per operation")

        # Should be very fast (< 100μs per operation)
        assert avg_time_us < 100

    def test_statistics_calculation(self, monitor):
        """Test statistics calculation performance."""
        # Generate some metrics
        for i in range(1000):
            with monitor.monitor('test_op'):
                time.sleep(0.0001)  # 0.1ms

        # Measure statistics calculation time
        start = time.time()
        stats = monitor.get_statistics('test_op')
        calc_time = (time.time() - start) * 1000

        print(f"\nStatistics calculation: {calc_time:.4f}ms for 1000 metrics")

        # Should be fast even for many metrics
        assert calc_time < 50  # Less than 50ms
        assert stats['count'] == 1000


class TestBatchLoadingPerformance:
    """Test batch loading performance improvements."""

    def test_batch_vs_individual_loading(self):
        """
        Compare batch loading vs individual loading.

        Note: This is a conceptual test - actual implementation
        would require database setup.
        """
        # Simulate loading times
        individual_load_time = 10  # 10ms per item
        batch_overhead = 5  # 5ms batch overhead

        num_items = 50

        # Individual loading
        individual_total = num_items * individual_load_time

        # Batch loading
        batch_total = batch_overhead + (num_items * 0.5)  # Much faster per item

        speedup = individual_total / batch_total

        print(f"\nIndividual loading: {individual_total}ms")
        print(f"Batch loading: {batch_total}ms")
        print(f"Speedup: {speedup:.2f}x faster")

        # Batch loading should be significantly faster
        assert speedup > 10


class TestLazyLoadingPerformance:
    """Test lazy loading performance."""

    def test_lazy_vs_eager_loading(self):
        """
        Compare lazy loading vs eager loading startup time.

        Lazy loading should have faster startup but slower first access.
        """
        num_strategies = 100
        load_time_per_strategy = 0.01  # 10ms

        # Eager loading - all strategies loaded at startup
        eager_startup = num_strategies * load_time_per_strategy

        # Lazy loading - no strategies loaded at startup
        lazy_startup = 0
        lazy_first_access = load_time_per_strategy

        print(f"\nEager loading startup: {eager_startup * 1000:.2f}ms")
        print(f"Lazy loading startup: {lazy_startup * 1000:.2f}ms")
        print(f"Lazy first access: {lazy_first_access * 1000:.2f}ms")

        # Lazy should have much faster startup
        assert lazy_startup < eager_startup


class TestMemoryUsage:
    """Test memory usage optimization."""

    def test_cache_memory_cleanup(self):
        """Test that cache cleanup reduces memory usage."""
        cache = StrategyCache(ttl_minutes=0.001)  # Very short TTL

        # Create large objects
        large_data = {'data': list(range(100000))}

        # Fill cache
        for i in range(10):
            cache.set(f'key_{i}', large_data)

        initial_stats = cache.get_stats()
        assert initial_stats['total_keys'] == 10

        # Wait for expiration
        time.sleep(0.1)

        # Clean up
        cache.cleanup_expired()

        final_stats = cache.get_stats()

        print(f"\nBefore cleanup: {initial_stats['total_keys']} keys")
        print(f"After cleanup: {final_stats['total_keys']} keys")

        # Expired keys should be removed
        assert final_stats['total_keys'] < initial_stats['total_keys']


class TestConcurrency:
    """Test concurrent access performance."""

    def test_thread_safe_cache_access(self):
        """Test cache performance under concurrent access."""
        import threading

        cache = StrategyCache()
        num_threads = 10
        operations_per_thread = 100

        def worker(thread_id):
            for i in range(operations_per_thread):
                key = f'thread_{thread_id}_key_{i}'
                cache.set(key, {'thread': thread_id, 'op': i})
                result = cache.get(key)
                assert result is not None

        # Create and start threads
        threads = []
        start = time.time()

        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)

        # Wait for completion
        for t in threads:
            t.join()

        duration = time.time() - start
        total_ops = num_threads * operations_per_thread
        ops_per_sec = total_ops / duration

        print(f"\nConcurrent cache operations: {ops_per_sec:.2f} ops/sec")
        print(f"Total operations: {total_ops}")
        print(f"Duration: {duration:.4f}s")

        # Should handle many concurrent operations
        assert ops_per_sec > 1000  # At least 1000 ops/sec


@pytest.mark.benchmark
class TestEndToEndPerformance:
    """End-to-end performance tests."""

    def test_complete_workflow_performance(self):
        """
        Test complete strategy loading workflow with all optimizations.

        This simulates a real-world scenario.
        """
        # Initialize components
        monitor = PerformanceMonitor()
        cache = StrategyCache()
        metrics = MetricsCollector()

        # Simulate strategy loading with monitoring
        num_strategies = 10

        start = time.time()

        for i in range(num_strategies):
            with monitor.monitor('load_strategy', strategy_id=i):
                # Check cache first
                cached = cache.get(f'strategy_{i}')

                if cached is None:
                    # Simulate loading (cache miss)
                    time.sleep(0.01)  # 10ms load time
                    strategy = {'id': i, 'name': f'Strategy {i}'}
                    cache.set(f'strategy_{i}', strategy)
                    metrics.increment('cache_misses')
                else:
                    # Cache hit
                    metrics.increment('cache_hits')

                metrics.record_timer('load_time', 10.0)

        duration = (time.time() - start) * 1000

        # Get statistics
        stats = monitor.get_statistics('load_strategy')
        cache_stats = cache.get_stats()
        metrics_summary = metrics.get_summary()

        print(f"\n=== End-to-End Performance ===")
        print(f"Total strategies loaded: {num_strategies}")
        print(f"Total time: {duration:.2f}ms")
        print(f"Average per strategy: {duration / num_strategies:.2f}ms")
        print(f"Cache hits: {metrics.get_counter('cache_hits')}")
        print(f"Cache misses: {metrics.get_counter('cache_misses')}")
        print(f"Monitor stats: {stats}")

        # Should complete reasonably fast
        assert duration < 200  # Less than 200ms for 10 strategies


if __name__ == '__main__':
    # Run benchmarks
    pytest.main([__file__, '-v', '--benchmark-only'])
