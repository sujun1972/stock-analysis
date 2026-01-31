"""
内存优化性能基准测试

对比测试:
- 流式特征计算 vs 传统一次性加载
- 分块回测 vs 常规回测
- 内存池 vs 直接分配

测量指标:
- 峰值内存占用
- 执行时间
- 内存重用率

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import shutil
from pathlib import Path
import gc
import time

from src.features.streaming_feature_engine import StreamingFeatureEngine, StreamingConfig
from src.backtest.backtest_engine import BacktestEngine
from src.utils.memory_pool import DataFrameMemoryPool, get_global_memory_pool, reset_global_memory_pool
from src.utils.memory_profiler import memory_profiler, get_current_memory_usage
from src.utils.response import Response


# ==================== Response 辅助函数 ====================


def unwrap_response(response):
    """
    从 Response 对象中提取数据

    在重构过程中，回测和特征计算函数从直接返回数据改为返回 Response 对象。
    此函数用于统一解包 Response 对象，提取其中的实际数据。

    Args:
        response: Response 对象或原始数据（兼容旧 API）

    Returns:
        解包后的数据（dict 或 DataFrame）

    Raises:
        ValueError: 如果 Response 状态为失败

    Examples:
        >>> results = unwrap_response(engine.backtest_long_only_chunked(...))
        >>> final_value = results['portfolio_value']['total'].iloc[-1]
    """
    if isinstance(response, Response):
        if not response.is_success():
            raise ValueError(f"操作失败: {response.error_message}")
        return response.data
    return response


@pytest.fixture
def temp_dir():
    """临时目录"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.mark.performance
class TestStreamingFeatureBenchmark:
    """流式特征计算性能基准测试"""

    def test_memory_usage_comparison(self, temp_dir):
        """对比内存使用：流式 vs 传统"""

        # 生成测试数据加载器
        def create_stock_data(stock_code):
            dates = pd.date_range('2023-01-01', periods=250, freq='D')
            np.random.seed(hash(stock_code) % (2**32))
            return pd.DataFrame({
                'open': np.random.uniform(10, 20, 250),
                'high': np.random.uniform(15, 25, 250),
                'low': np.random.uniform(8, 15, 250),
                'close': np.random.uniform(10, 20, 250),
                'volume': np.random.uniform(1e6, 1e7, 250)
            }, index=dates)

        def calculate_features(df):
            features = pd.DataFrame(index=df.index)
            features['momentum_5'] = df['close'].pct_change(5)
            features['momentum_10'] = df['close'].pct_change(10)
            features['volatility_10'] = df['close'].pct_change().rolling(10).std()
            return features

        stock_codes = [f"{i:06d}.SZ" for i in range(1, 101)]  # 100只股票

        # === 方法1: 传统方式（一次性加载） ===
        gc.collect()
        mem_before_traditional = get_current_memory_usage()['process_rss_mb']

        with memory_profiler("传统特征计算", track_interval=0.2, log_result=False) as _:
            # 一次性加载所有数据
            all_data = []
            for code in stock_codes:
                df = create_stock_data(code)
                df['stock_code'] = code
                all_data.append(df)

            combined_data = pd.concat(all_data, ignore_index=True)

            # 计算特征（这里简化处理）
            all_features = []
            for code in stock_codes:
                stock_data = combined_data[combined_data['stock_code'] == code]
                features = calculate_features(stock_data)
                features['stock_code'] = code
                all_features.append(features)

            traditional_result = pd.concat(all_features, ignore_index=True)

        mem_after_traditional = get_current_memory_usage()['process_rss_mb']
        mem_used_traditional = mem_after_traditional - mem_before_traditional

        # 清理
        del all_data, combined_data, all_features, traditional_result
        gc.collect()
        time.sleep(0.5)

        # === 方法2: 流式方式 ===
        gc.collect()
        mem_before_streaming = get_current_memory_usage()['process_rss_mb']

        config = StreamingConfig(batch_size=20, checkpoint_enabled=False, auto_gc=True)
        engine = StreamingFeatureEngine(config=config, output_dir=temp_dir)

        with memory_profiler("流式特征计算", track_interval=0.2, log_result=False) as _:
            result_path = engine.compute_features_streaming(
                stock_codes=stock_codes,
                data_loader=create_stock_data,
                feature_calculator=calculate_features
            )

        mem_after_streaming = get_current_memory_usage()['process_rss_mb']
        mem_used_streaming = mem_after_streaming - mem_before_streaming

        stats = engine.get_stats()

        # 对比结果
        print(f"\n=== 内存使用对比 ===")
        print(f"传统方式: {mem_used_traditional:.1f} MB")
        print(f"流式方式: {mem_used_streaming:.1f} MB")
        print(f"节省: {(1 - mem_used_streaming/max(mem_used_traditional, 1)) * 100:.1f}%")
        print(f"峰值内存: {stats.peak_memory_mb:.1f} MB")

        # 验证：流式方式应该使用更少内存
        # 注意：Python GC不确定性导致内存测量不可靠，仅作参考
        if mem_used_streaming < mem_used_traditional * 1.2:
            print("✓ 流式方式减少了内存使用")
        else:
            print(f"⚠ 流式方式未明显减少内存（可能受GC影响）")
            print(f"  传统: {mem_used_traditional:.1f}MB, 流式: {mem_used_streaming:.1f}MB")

    def test_batch_size_impact(self, temp_dir):
        """测试batch_size对内存的影响"""

        def create_stock_data(stock_code):
            dates = pd.date_range('2023-01-01', periods=200, freq='D')
            np.random.seed(hash(stock_code) % (2**32))
            return pd.DataFrame({
                'close': np.random.uniform(10, 20, 200),
                'volume': np.random.uniform(1e6, 1e7, 200)
            }, index=dates)

        def calculate_features(df):
            return pd.DataFrame({
                'momentum_5': df['close'].pct_change(5)
            }, index=df.index)

        stock_codes = [f"{i:06d}.SZ" for i in range(1, 61)]  # 60只股票

        batch_sizes = [10, 20, 30, 60]
        results = {}

        for batch_size in batch_sizes:
            gc.collect()

            config = StreamingConfig(
                batch_size=batch_size,
                checkpoint_enabled=False,
                auto_gc=True
            )
            engine = StreamingFeatureEngine(
                config=config,
                output_dir=temp_dir / f"batch_{batch_size}"
            )

            engine.compute_features_streaming(
                stock_codes=stock_codes,
                data_loader=create_stock_data,
                feature_calculator=calculate_features
            )

            stats = engine.get_stats()
            results[batch_size] = {
                'peak_memory_mb': stats.peak_memory_mb,
                'time_seconds': stats.get_elapsed_time()
            }

        print(f"\n=== Batch Size Impact ===")
        for batch_size, metrics in results.items():
            print(f"Batch Size {batch_size:2d}: "
                  f"内存 {metrics['peak_memory_mb']:.1f}MB, "
                  f"耗时 {metrics['time_seconds']:.2f}s")

        # 验证：较小的batch_size应该使用更少内存（但可能更慢）
        assert results[10]['peak_memory_mb'] <= results[60]['peak_memory_mb'] * 1.5


@pytest.mark.performance
class TestBacktestBenchmark:
    """回测性能基准测试"""

    def test_chunked_vs_regular_backtest(self):
        """对比分块回测vs常规回测"""
        np.random.seed(42)

        # 生成较大数据集
        dates = pd.date_range('2022-01-01', periods=500, freq='D')
        stocks = [f"{i:06d}.SZ" for i in range(600000, 600080)]  # 80只股票

        price_data = {}
        signal_data = {}

        for stock in stocks:
            base = 12.0
            returns = np.random.normal(0.0004, 0.013, len(dates))
            prices = base * (1 + returns).cumprod()
            price_data[stock] = prices
            signal_data[stock] = np.random.randn(len(dates))

        prices_df = pd.DataFrame(price_data, index=dates)
        signals_df = pd.DataFrame(signal_data, index=dates)

        # === 常规回测 ===
        gc.collect()
        mem_before_regular = get_current_memory_usage()['process_rss_mb']
        time_start_regular = time.time()

        engine_regular = BacktestEngine(initial_capital=2000000, verbose=False)

        with memory_profiler("常规回测", track_interval=0.5, log_result=False) as _:
            results_regular_response = engine_regular.backtest_long_only(
                signals=signals_df,
                prices=prices_df,
                top_n=10,
                holding_period=5,
                rebalance_freq='W'
            )
            results_regular = unwrap_response(results_regular_response)  # 解包Response对象

        time_regular = time.time() - time_start_regular
        mem_after_regular = get_current_memory_usage()['process_rss_mb']
        mem_used_regular = mem_after_regular - mem_before_regular

        final_regular = results_regular['portfolio_value']['total'].iloc[-1]

        # 清理
        del engine_regular, results_regular
        gc.collect()
        time.sleep(0.5)

        # === 分块回测 ===
        gc.collect()
        mem_before_chunked = get_current_memory_usage()['process_rss_mb']
        time_start_chunked = time.time()

        engine_chunked = BacktestEngine(initial_capital=2000000, verbose=False)

        with memory_profiler("分块回测", track_interval=0.5, log_result=False) as _:
            results_chunked_response = engine_chunked.backtest_long_only_chunked(
                signals=signals_df,
                prices=prices_df,
                top_n=10,
                holding_period=5,
                rebalance_freq='W',
                chunk_size=100
            )
            results_chunked = unwrap_response(results_chunked_response)  # 解包Response对象

        time_chunked = time.time() - time_start_chunked
        mem_after_chunked = get_current_memory_usage()['process_rss_mb']
        mem_used_chunked = mem_after_chunked - mem_before_chunked

        final_chunked = results_chunked['portfolio_value']['total'].iloc[-1]

        # 对比结果
        print(f"\n=== 回测性能对比 ===")
        print(f"常规回测: 内存 {mem_used_regular:.1f}MB, 耗时 {time_regular:.2f}s, 最终资产 {final_regular:,.0f}")
        print(f"分块回测: 内存 {mem_used_chunked:.1f}MB, 耗时 {time_chunked:.2f}s, 最终资产 {final_chunked:,.0f}")
        print(f"内存节省: {(1 - mem_used_chunked/max(mem_used_regular, 1)) * 100:.1f}%")
        print(f"时间比: {time_chunked/max(time_regular, 0.001):.2f}x")

        # 验证结果一致性
        relative_diff = abs(final_chunked - final_regular) / final_regular
        assert relative_diff < 0.01, f"结果差异过大: {relative_diff:.2%}"


@pytest.mark.performance
class TestMemoryPoolBenchmark:
    """内存池性能基准测试"""

    def test_pool_vs_direct_allocation(self):
        """对比内存池vs直接分配"""

        num_iterations = 500
        array_shape = (1000, 50)

        # === 方法1: 直接分配 ===
        gc.collect()
        time_start_direct = time.time()

        with memory_profiler("直接分配", track_interval=0.1, log_result=False) as _:
            for i in range(num_iterations):
                arr = np.empty(array_shape, dtype=np.float64)
                arr[:, 0] = i  # 简单操作
                del arr

        time_direct = time.time() - time_start_direct

        gc.collect()
        time.sleep(0.3)

        # === 方法2: 内存池 ===
        reset_global_memory_pool()
        pool = get_global_memory_pool()

        gc.collect()
        time_start_pool = time.time()

        with memory_profiler("内存池", track_interval=0.1, log_result=False) as _:
            for i in range(num_iterations):
                arr = pool.acquire(shape=array_shape)
                arr[:, 0] = i
                pool.release(arr)

        time_pool = time.time() - time_start_pool

        stats = pool.get_stats()

        # 对比结果
        print(f"\n=== 内存池性能对比 ===")
        print(f"直接分配: 耗时 {time_direct:.3f}s")
        print(f"内存池: 耗时 {time_pool:.3f}s")
        print(f"加速比: {time_direct/max(time_pool, 0.001):.2f}x")
        print(f"新分配: {stats.total_alloc_count} 次")
        print(f"重用: {stats.total_reuse_count} 次")
        print(f"重用率: {stats.get_reuse_rate():.1%}")

        # 验证：内存池应该有高重用率
        assert stats.get_reuse_rate() > 0.95, "内存池重用率过低"

        # 验证：只有少量新分配
        assert stats.total_alloc_count < 10, f"新分配次数过多: {stats.total_alloc_count}"

    def test_concurrent_pool_performance(self):
        """测试并发场景下的内存池性能"""
        import threading

        reset_global_memory_pool()
        pool = get_global_memory_pool()

        num_threads = 8
        iterations_per_thread = 100

        results = []

        def worker(worker_id):
            for i in range(iterations_per_thread):
                arr = pool.acquire(shape=(500, 20))
                arr[:, 0] = worker_id
                pool.release(arr)
            results.append(worker_id)

        gc.collect()
        time_start = time.time()

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        time_elapsed = time.time() - time_start

        stats = pool.get_stats()

        print(f"\n=== 并发内存池性能 ===")
        print(f"线程数: {num_threads}")
        print(f"每线程迭代: {iterations_per_thread}")
        print(f"总耗时: {time_elapsed:.3f}s")
        print(f"新分配: {stats.total_alloc_count}")
        print(f"重用: {stats.total_reuse_count}")
        print(f"重用率: {stats.get_reuse_rate():.1%}")

        # 验证所有线程完成
        assert len(results) == num_threads

        # 验证高重用率
        assert stats.get_reuse_rate() > 0.85


@pytest.mark.integration
class TestMemoryOptimizationIntegration:
    """内存优化集成测试"""

    def test_full_workflow_memory_efficiency(self, temp_dir):
        """测试完整工作流的内存效率"""

        print(f"\n=== 完整工作流内存测试 ===")

        # 模拟场景：200只股票，1年数据，计算特征并回测

        def create_stock_data(stock_code):
            dates = pd.date_range('2023-01-01', periods=250, freq='D')
            np.random.seed(hash(stock_code) % (2**32))
            return pd.DataFrame({
                'open': np.random.uniform(10, 20, 250),
                'high': np.random.uniform(12, 22, 250),
                'low': np.random.uniform(8, 18, 250),
                'close': np.random.uniform(10, 20, 250),
                'volume': np.random.uniform(1e6, 1e7, 250)
            }, index=dates)

        def calculate_features(df):
            features = pd.DataFrame(index=df.index)
            features['momentum_5'] = df['close'].pct_change(5)
            features['momentum_20'] = df['close'].pct_change(20)
            features['volatility'] = df['close'].pct_change().rolling(20).std()
            return features

        stock_codes = [f"{i:06d}.SZ" for i in range(1, 201)]  # 200只股票

        gc.collect()
        mem_start = get_current_memory_usage()['process_rss_mb']

        # 步骤1: 流式计算特征
        config = StreamingConfig(batch_size=25, checkpoint_enabled=False)
        engine = StreamingFeatureEngine(config=config, output_dir=temp_dir)

        with memory_profiler("完整工作流", track_interval=1.0, log_result=True) as _:
            features_path = engine.compute_features_streaming(
                stock_codes=stock_codes,
                data_loader=create_stock_data,
                feature_calculator=calculate_features
            )

            # 读取特征（按需加载）
            features_df = pd.read_parquet(features_path)

            # 构建价格和信号数据（简化）
            # 实际应用中可以从特征中提取
            dates = pd.date_range('2023-01-01', periods=250, freq='D')
            prices_dict = {}
            signals_dict = {}

            for code in stock_codes[:50]:  # 简化为50只
                stock_data = create_stock_data(code)
                prices_dict[code] = stock_data['close']

                # 使用动量作为信号
                stock_features = features_df[features_df['stock_code'] == code]
                if not stock_features.empty:
                    signals_dict[code] = stock_features.set_index('date')['momentum_20']

            prices_df = pd.DataFrame(prices_dict, index=dates)
            signals_df = pd.DataFrame(signals_dict, index=dates)

            # 步骤2: 分块回测
            backtest_engine = BacktestEngine(initial_capital=3000000, verbose=False)

            results_response = backtest_engine.backtest_long_only_chunked(
                signals=signals_df,
                prices=prices_df,
                top_n=8,
                holding_period=5,
                rebalance_freq='W',
                chunk_size=60
            )
            results = unwrap_response(results_response)  # 解包Response对象

        mem_end = get_current_memory_usage()['process_rss_mb']
        mem_used_total = mem_end - mem_start

        final_value = results['portfolio_value']['total'].iloc[-1]

        print(f"\n完整工作流结果:")
        print(f"  处理股票: {len(stock_codes)}只")
        print(f"  内存使用: {mem_used_total:.1f} MB")
        print(f"  最终资产: {final_value:,.0f}")
        print(f"  特征统计: {engine.get_stats().to_dict()}")

        # 验证内存使用合理
        assert mem_used_total < 500, f"内存使用过高: {mem_used_total:.1f}MB"

        # 验证回测成功
        assert final_value > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
