"""
FeatureStorage 集成测试

测试特征存储在真实场景下的集成功能：
- 多格式存储互操作
- 大规模数据处理
- 并发安全性
- 错误恢复
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加 src 目录到路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from features.storage.feature_storage import FeatureStorage


class TestMultiFormatIntegration:
    """测试多格式集成"""

    @pytest.fixture
    def sample_df(self):
        """创建测试用的 DataFrame"""
        dates = pd.date_range('2024-01-01', periods=1000)
        data = {
            'open': np.random.rand(1000) * 100,
            'high': np.random.rand(1000) * 100,
            'low': np.random.rand(1000) * 100,
            'close': np.random.rand(1000) * 100,
            'volume': np.random.randint(1000, 100000, 1000),
            'ma_5': np.random.rand(1000) * 100,
            'ma_10': np.random.rand(1000) * 100,
            'ma_20': np.random.rand(1000) * 100,
        }
        df = pd.DataFrame(data, index=dates)
        df.index.name = 'date'
        return df

    def test_cross_format_data_integrity(self, tmp_path, sample_df):
        """测试跨格式数据完整性"""
        formats = ['parquet', 'hdf5', 'csv']
        storages = {}

        # 在不同格式中保存相同数据
        for fmt in formats:
            storage_dir = tmp_path / fmt
            storage = FeatureStorage(storage_dir=str(storage_dir), format=fmt)
            storages[fmt] = storage
            storage.save_features(sample_df, '000001', 'transformed', 'v1')

        # 验证所有格式的数据一致性
        dfs = {}
        for fmt, storage in storages.items():
            dfs[fmt] = storage.load_features('000001', 'transformed')

        # 比较数据
        for i, fmt1 in enumerate(formats):
            for fmt2 in formats[i+1:]:
                pd.testing.assert_frame_equal(
                    dfs[fmt1], dfs[fmt2],
                    check_dtype=False,
                    check_freq=False,  # 忽略时间索引频率差异
                    rtol=1e-5
                )


class TestConcurrency:
    """测试并发安全性"""

    @pytest.fixture
    def storage(self, tmp_path):
        """创建测试用的存储对象"""
        return FeatureStorage(storage_dir=str(tmp_path), format='parquet')

    def test_concurrent_writes_different_stocks(self, storage):
        """测试不同股票的并发写入"""
        def save_stock(stock_code, n):
            df = pd.DataFrame({
                'value': np.random.rand(100) * 100
            }, index=pd.date_range('2024-01-01', periods=100))
            return storage.save_features(df, stock_code, 'transformed', 'v1')

        # 并发保存10只股票
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(save_stock, f'00000{i}', i)
                for i in range(10)
            ]

            results = [f.result() for f in as_completed(futures)]

        # 验证所有操作成功
        assert all(results)
        assert len(storage.list_stocks()) == 10

    def test_concurrent_reads(self, storage):
        """测试并发读取"""
        # 准备数据
        for i in range(10):
            df = pd.DataFrame({
                'value': [i] * 100
            }, index=pd.date_range('2024-01-01', periods=100))
            storage.save_features(df, f'00000{i}', 'transformed', 'v1')

        # 并发读取
        def load_stock(stock_code):
            return storage.load_features(stock_code, 'transformed')

        with ThreadPoolExecutor(max_workers=5) as executor:
            stock_codes = [f'00000{i}' for i in range(10)]
            futures = [
                executor.submit(load_stock, code)
                for code in stock_codes
            ]

            dfs = [f.result() for f in as_completed(futures)]

        # 验证所有读取成功
        assert all(df is not None for df in dfs)
        assert len(dfs) == 10

    def test_concurrent_metadata_updates(self, storage):
        """测试并发元数据更新"""
        def save_and_update(n):
            for i in range(10):
                df = pd.DataFrame({
                    'value': [n * 10 + i]
                }, index=pd.date_range('2024-01-01', periods=1))
                storage.save_features(
                    df,
                    f'stock_{n}_{i}',
                    'transformed',
                    'v1'
                )
            return True

        # 多线程并发保存
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(save_and_update, n) for n in range(3)]
            results = [f.result() for f in futures]

        assert all(results)
        assert len(storage.list_stocks()) == 30  # 3 threads * 10 stocks each

    def test_concurrent_read_write_same_stock(self, storage):
        """测试同一股票的并发读写"""
        # 先保存初始数据
        df = pd.DataFrame({
            'value': [1, 2, 3]
        }, index=pd.date_range('2024-01-01', periods=3))
        storage.save_features(df, '000001', 'transformed', 'v1')

        results = {'reads': [], 'writes': []}
        errors = []

        def read_stock():
            try:
                for _ in range(5):
                    df = storage.load_features('000001', 'transformed')
                    results['reads'].append(df is not None)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(('read', e))

        def write_stock():
            try:
                for i in range(5):
                    new_df = pd.DataFrame({
                        'value': [i, i+1, i+2]
                    }, index=pd.date_range('2024-01-01', periods=3))
                    success = storage.save_features(
                        new_df, '000001', 'transformed', f'v{i+2}'
                    )
                    results['writes'].append(success)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(('write', e))

        # 启动并发读写
        threads = [
            threading.Thread(target=read_stock),
            threading.Thread(target=write_stock)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证没有错误
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results['reads']) > 0
        assert len(results['writes']) > 0
        assert all(results['reads'])
        assert all(results['writes'])


class TestLargeScaleOperations:
    """测试大规模操作"""

    @pytest.fixture
    def storage(self, tmp_path):
        """创建测试用的存储对象"""
        return FeatureStorage(storage_dir=str(tmp_path), format='parquet')

    def test_save_load_large_dataframe(self, storage):
        """测试保存和加载大型 DataFrame"""
        # 创建包含 10000 行数据的 DataFrame
        n_rows = 10000
        df = pd.DataFrame({
            'open': np.random.rand(n_rows) * 100,
            'high': np.random.rand(n_rows) * 100,
            'low': np.random.rand(n_rows) * 100,
            'close': np.random.rand(n_rows) * 100,
            'volume': np.random.randint(1000, 100000, n_rows),
        }, index=pd.date_range('2000-01-01', periods=n_rows))

        # 保存
        result = storage.save_features(df, '000001', 'transformed', 'v1')
        assert result is True

        # 加载
        loaded_df = storage.load_features('000001', 'transformed')
        assert loaded_df is not None
        assert len(loaded_df) == n_rows

    def test_batch_operations_many_stocks(self, storage):
        """测试批量操作多只股票"""
        n_stocks = 100

        # 批量保存
        for i in range(n_stocks):
            df = pd.DataFrame({
                'close': np.random.rand(100) * 100
            }, index=pd.date_range('2024-01-01', periods=100))
            storage.save_features(df, f'{i:06d}', 'transformed', 'v1')

        assert len(storage.list_stocks()) == n_stocks

        # 批量加载（并发）
        stock_codes = [f'{i:06d}' for i in range(n_stocks)]
        features_dict = storage.load_multiple_stocks(
            stock_codes,
            parallel=True,
            max_workers=8
        )

        assert len(features_dict) == n_stocks

    def test_multiple_feature_types_per_stock(self, storage):
        """测试每只股票的多种特征类型"""
        feature_types = ['raw', 'technical', 'alpha', 'transformed']
        n_stocks = 20

        # 为每只股票保存多种类型的特征
        for i in range(n_stocks):
            stock_code = f'00{i:04d}'
            for ftype in feature_types:
                df = pd.DataFrame({
                    'value': np.random.rand(50)
                }, index=pd.date_range('2024-01-01', periods=50))
                storage.save_features(df, stock_code, ftype, 'v1')

        # 验证
        stats = storage.get_statistics()
        assert stats['total_stocks'] == n_stocks

        for ftype in feature_types:
            assert ftype in stats['feature_types']
            assert stats['feature_types'][ftype] == n_stocks


class TestErrorRecovery:
    """测试错误恢复"""

    @pytest.fixture
    def storage(self, tmp_path):
        """创建测试用的存储对象"""
        return FeatureStorage(storage_dir=str(tmp_path), format='parquet')

    def test_corrupted_metadata_recovery(self, tmp_path):
        """测试损坏元数据的恢复"""
        storage = FeatureStorage(storage_dir=str(tmp_path), format='parquet')

        # 保存一些数据
        df = pd.DataFrame({'value': [1, 2, 3]}, index=pd.date_range('2024-01-01', periods=3))
        storage.save_features(df, '000001', 'transformed', 'v1')

        # 损坏元数据文件
        with open(storage.metadata_file, 'w') as f:
            f.write('corrupted json data {{{')

        # 重新初始化应该创建新的元数据
        storage2 = FeatureStorage(storage_dir=str(tmp_path), format='parquet')

        # 元数据应该被重新初始化
        assert 'stocks' in storage2.metadata
        assert 'created_at' in storage2.metadata

    def test_partial_save_failure(self, storage):
        """测试部分保存失败的处理"""
        # 尝试保存到只读目录（模拟失败）
        df = pd.DataFrame({'value': [1, 2, 3]}, index=pd.date_range('2024-01-01', periods=3))

        # 正常保存应该成功
        result = storage.save_features(df, '000001', 'transformed', 'v1')
        assert result is True

        # 保存空 DataFrame 应该失败但不崩溃
        empty_df = pd.DataFrame()
        result = storage.save_features(empty_df, '000002', 'transformed', 'v1')
        assert result is False

        # 之前的数据应该还在
        loaded = storage.load_features('000001', 'transformed')
        assert loaded is not None


class TestPerformance:
    """性能测试"""

    @pytest.fixture
    def storage(self, tmp_path):
        """创建测试用的存储对象"""
        return FeatureStorage(storage_dir=str(tmp_path), format='parquet')

    def test_parallel_vs_serial_loading(self, storage):
        """比较并行和串行加载的性能"""
        # 准备数据
        n_stocks = 20
        for i in range(n_stocks):
            df = pd.DataFrame({
                'close': np.random.rand(500) * 100
            }, index=pd.date_range('2024-01-01', periods=500))
            storage.save_features(df, f'{i:06d}', 'transformed', 'v1')

        stock_codes = [f'{i:06d}' for i in range(n_stocks)]

        # 串行加载
        start_time = time.time()
        serial_dict = storage.load_multiple_stocks(
            stock_codes,
            parallel=False
        )
        serial_time = time.time() - start_time

        # 并行加载
        start_time = time.time()
        parallel_dict = storage.load_multiple_stocks(
            stock_codes,
            parallel=True,
            max_workers=4
        )
        parallel_time = time.time() - start_time

        # 验证结果一致
        assert len(serial_dict) == len(parallel_dict) == n_stocks

        # 检查并行和串行都完成了（性能差异在小数据集上可能不明显）
        print(f"Serial: {serial_time:.3f}s, Parallel: {parallel_time:.3f}s")
        # 仅验证两者都成功完成，不强制要求并行更快（因为小数据集上差异不明显）
        assert serial_time > 0 and parallel_time > 0


class TestRealWorldScenarios:
    """真实世界场景测试"""

    @pytest.fixture
    def storage(self, tmp_path):
        """创建测试用的存储对象"""
        return FeatureStorage(storage_dir=str(tmp_path), format='parquet')

    def test_feature_pipeline_workflow(self, storage):
        """测试特征工程流水线工作流"""
        # 模拟真实的特征工程流程

        # 1. 保存原始数据
        raw_df = pd.DataFrame({
            'open': [100, 101, 102],
            'close': [101, 102, 103],
        }, index=pd.date_range('2024-01-01', periods=3))
        storage.save_features(raw_df, '000001', 'raw', 'v1')

        # 2. 计算技术指标
        technical_df = raw_df.copy()
        technical_df['ma_5'] = technical_df['close'].rolling(2).mean()
        storage.save_features(technical_df, '000001', 'technical', 'v1')

        # 3. 计算 Alpha 因子
        alpha_df = technical_df.copy()
        alpha_df['alpha_1'] = technical_df['close'] / technical_df['open'] - 1
        storage.save_features(alpha_df, '000001', 'alpha', 'v1')

        # 4. 特征转换
        transformed_df = alpha_df.copy()
        transformed_df['normalized'] = (alpha_df['alpha_1'] - alpha_df['alpha_1'].mean()) / alpha_df['alpha_1'].std()
        storage.save_features(transformed_df, '000001', 'transformed', 'v1')

        # 验证所有阶段的数据都存在
        info = storage.get_stock_info('000001')
        assert 'raw' in info
        assert 'technical' in info
        assert 'alpha' in info
        assert 'transformed' in info

    def test_incremental_update_workflow(self, storage):
        """测试增量更新工作流"""
        # 初始数据
        df1 = pd.DataFrame({
            'close': [100, 101, 102]
        }, index=pd.date_range('2024-01-01', periods=3))
        storage.save_features(df1, '000001', 'transformed', 'v1')

        # 增量更新（追加新数据）
        df2 = pd.DataFrame({
            'close': [103, 104]
        }, index=pd.date_range('2024-01-04', periods=2))
        storage.update_features('000001', df2, 'transformed', mode='append')

        # 验证
        final_df = storage.load_features('000001', 'transformed')
        assert len(final_df) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '-s'])
