#!/usr/bin/env python3
"""
DataFrame iterrows() 性能优化验证测试

测试向量化操作相比 iterrows() 的性能提升
"""

import sys
import time
import unittest
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


class TestIterrowsPerformance(unittest.TestCase):
    """测试 iterrows 性能优化"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*80)
        print("DataFrame iterrows() 性能优化验证")
        print("="*80)

    def setUp(self):
        """每个测试前的准备"""
        # 创建测试数据（模拟真实场景）
        np.random.seed(42)
        self.df_small = self._create_test_dataframe(100)      # 100 行
        self.df_medium = self._create_test_dataframe(1000)    # 1000 行
        self.df_large = self._create_test_dataframe(10000)    # 10000 行

    def _create_test_dataframe(self, n_rows):
        """创建测试数据框"""
        dates = pd.date_range('2023-01-01', periods=n_rows, freq='D')
        return pd.DataFrame({
            'code': ['000001'] * n_rows,
            'name': ['平安银行'] * n_rows,
            'open': np.random.uniform(10, 20, n_rows),
            'high': np.random.uniform(15, 25, n_rows),
            'low': np.random.uniform(5, 15, n_rows),
            'close': np.random.uniform(10, 20, n_rows),
            'volume': np.random.randint(1000000, 10000000, n_rows),
            'amount': np.random.uniform(10000000, 100000000, n_rows),
            'pct_change': np.random.uniform(-5, 5, n_rows),
            'turnover': np.random.uniform(0, 10, n_rows),
        }, index=dates)

    def test_01_stock_list_performance(self):
        """测试1: 股票列表数据准备性能"""
        print("\n[测试1] 股票列表数据准备性能对比")

        df = self.df_medium

        # 方法1：iterrows（旧方法）
        start = time.time()
        records_old = []
        for _, row in df.iterrows():
            records_old.append((
                row.get('code'),
                row.get('name'),
                '',  # market
                '',  # industry
                '',  # area
                None,  # list_date
                None,  # delist_date
                '正常',  # status
                'akshare'  # data_source
            ))
        time_old = time.time() - start

        # 方法2：向量化（新方法）
        start = time.time()
        records_new = list(zip(
            df['code'].values,
            df['name'].values,
            [''] * len(df),
            [''] * len(df),
            [''] * len(df),
            [None] * len(df),
            [None] * len(df),
            ['正常'] * len(df),
            ['akshare'] * len(df)
        ))
        time_new = time.time() - start

        # 验证结果一致性
        self.assertEqual(len(records_old), len(records_new))
        self.assertEqual(records_old[0][:2], records_new[0][:2])

        # 性能对比
        speedup = time_old / time_new
        print(f"  iterrows 耗时: {time_old*1000:.2f}ms")
        print(f"  向量化耗时: {time_new*1000:.2f}ms")
        print(f"  性能提升: {speedup:.1f}x")

        # 验证：至少5倍提升
        self.assertGreater(speedup, 5, f"Expected >5x speedup, got {speedup:.1f}x")

    def test_02_daily_data_performance(self):
        """测试2: 日线数据准备性能"""
        print("\n[测试2] 日线数据准备性能对比")

        df = self.df_large  # 使用大数据集

        # 方法1：iterrows（旧方法）
        start = time.time()
        records_old = []
        for idx, row in df.iterrows():
            records_old.append((
                '000001',
                idx.date() if isinstance(idx, pd.Timestamp) else idx,
                float(row.get('open', 0)),
                float(row.get('high', 0)),
                float(row.get('low', 0)),
                float(row.get('close', 0)),
                int(row.get('volume', 0)),
                float(row.get('amount', 0)),
                0.0,  # amplitude
                float(row.get('pct_change', 0)),
                0.0,  # change
                float(row.get('turnover', 0))
            ))
        time_old = time.time() - start

        # 方法2：向量化（新方法）
        start = time.time()
        dates = pd.to_datetime(df.index).date
        records_new = list(zip(
            ['000001'] * len(df),
            dates,
            df['open'].astype(float).values,
            df['high'].astype(float).values,
            df['low'].astype(float).values,
            df['close'].astype(float).values,
            df['volume'].astype(int).values,
            df['amount'].astype(float).values,
            [0.0] * len(df),
            df['pct_change'].astype(float).values,
            [0.0] * len(df),
            df['turnover'].astype(float).values
        ))
        time_new = time.time() - start

        # 验证结果一致性
        self.assertEqual(len(records_old), len(records_new))

        # 性能对比
        speedup = time_old / time_new
        print(f"  数据规模: {len(df)} 行")
        print(f"  iterrows 耗时: {time_old*1000:.2f}ms")
        print(f"  向量化耗时: {time_new*1000:.2f}ms")
        print(f"  性能提升: {speedup:.1f}x")

        # 验证：至少10倍提升（大数据集）
        self.assertGreater(speedup, 10, f"Expected >10x speedup, got {speedup:.1f}x")

    def test_03_realtime_quotes_performance(self):
        """测试3: 实时行情数据准备性能"""
        print("\n[测试3] 实时行情数据准备性能对比")

        df = self.df_medium

        def safe_float(val, default=0.0):
            if pd.isna(val) or val is None:
                return default
            return float(val)

        def safe_int(val, default=0):
            if pd.isna(val) or val is None:
                return default
            return int(val)

        # 方法1：iterrows（旧方法）
        start = time.time()
        records_old = []
        for _, row in df.iterrows():
            records_old.append((
                row.get('code'),
                row.get('name'),
                safe_float(row.get('close')),
                safe_float(row.get('open')),
                safe_float(row.get('high')),
                safe_float(row.get('low')),
                0.0,  # pre_close
                safe_int(row.get('volume')),
                safe_float(row.get('amount')),
                safe_float(row.get('pct_change')),
                0.0,  # change_amount
                safe_float(row.get('turnover')),
                0.0,  # amplitude
                'akshare'
            ))
        time_old = time.time() - start

        # 方法2：向量化（新方法）
        def safe_float_series(series):
            return series.fillna(0.0).astype(float).values

        def safe_int_series(series):
            return series.fillna(0).astype(int).values

        start = time.time()
        records_new = list(zip(
            df['code'].values,
            df['name'].values,
            safe_float_series(df['close']),
            safe_float_series(df['open']),
            safe_float_series(df['high']),
            safe_float_series(df['low']),
            [0.0] * len(df),
            safe_int_series(df['volume']),
            safe_float_series(df['amount']),
            safe_float_series(df['pct_change']),
            [0.0] * len(df),
            safe_float_series(df['turnover']),
            [0.0] * len(df),
            ['akshare'] * len(df)
        ))
        time_new = time.time() - start

        # 验证结果一致性
        self.assertEqual(len(records_old), len(records_new))

        # 性能对比
        speedup = time_old / time_new
        print(f"  iterrows 耗时: {time_old*1000:.2f}ms")
        print(f"  向量化耗时: {time_new*1000:.2f}ms")
        print(f"  性能提升: {speedup:.1f}x")

        # 验证：至少8倍提升
        self.assertGreater(speedup, 8, f"Expected >8x speedup, got {speedup:.1f}x")

    def test_04_scalability(self):
        """测试4: 可扩展性验证"""
        print("\n[测试4] 不同数据规模的性能对比")

        test_sizes = [100, 1000, 10000]
        results = []

        for size in test_sizes:
            df = self._create_test_dataframe(size)

            # iterrows
            start = time.time()
            _ = [row for _, row in df.iterrows()]
            time_old = time.time() - start

            # 向量化
            start = time.time()
            _ = list(zip(df['code'].values, df['close'].values))
            time_new = time.time() - start

            speedup = time_old / time_new
            results.append((size, time_old * 1000, time_new * 1000, speedup))

            print(f"  {size:>6} 行: iterrows={time_old*1000:>8.2f}ms, "
                  f"向量化={time_new*1000:>6.2f}ms, 提升={speedup:>5.1f}x")

        # 验证：数据规模越大，提升越明显
        self.assertLess(results[0][3], results[-1][3],
                       "Speedup should increase with data size")

    def test_05_memory_usage(self):
        """测试5: 内存使用对比"""
        print("\n[测试5] 内存使用对比")
        import tracemalloc

        df = self.df_large

        # iterrows 内存
        tracemalloc.start()
        records_old = []
        for _, row in df.iterrows():
            records_old.append((row['code'], row['close']))
        _, peak_old = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 向量化内存
        tracemalloc.start()
        records_new = list(zip(df['code'].values, df['close'].values))
        _, peak_new = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print(f"  iterrows 峰值内存: {peak_old / 1024 / 1024:.2f} MB")
        print(f"  向量化峰值内存: {peak_new / 1024 / 1024:.2f} MB")
        print(f"  内存节省: {(peak_old - peak_new) / peak_old * 100:.1f}%")

        # 验证：向量化应该使用更少内存
        self.assertLess(peak_new, peak_old, "Vectorized should use less memory")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestIterrowsPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    print(f"运行: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}, 错误: {len(result.errors)}")
    print("="*80)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
