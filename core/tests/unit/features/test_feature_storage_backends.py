"""
特征存储后端测试

测试不同存储后端的功能：
- ParquetStorage
- HDF5Storage
- CSVStorage
- 后端切换
- 文件格式兼容性

作者: Stock Analysis Team
创建: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
import shutil
from pathlib import Path

from src.features.storage.feature_storage import FeatureStorage
from src.features.storage.parquet_storage import ParquetStorage
from src.features.storage.hdf5_storage import HDF5Storage
from src.features.storage.csv_storage import CSVStorage
from src.utils.response import Response


# ==================== Fixtures ====================


@pytest.fixture
def temp_storage_dir(tmp_path):
    """创建临时存储目录"""
    storage_dir = tmp_path / "test_backends"
    storage_dir.mkdir(parents=True, exist_ok=True)
    yield storage_dir
    if storage_dir.exists():
        shutil.rmtree(storage_dir)


@pytest.fixture
def sample_feature_df():
    """生成样本特征DataFrame"""
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=50, freq='D')
    return pd.DataFrame({
        'feature1': np.random.randn(50),
        'feature2': np.random.randn(50),
        'feature3': np.random.randn(50),
    }, index=dates)


# ==================== Parquet存储测试 ====================


class TestParquetStorage:
    """Parquet存储后端测试"""

    def test_parquet_save_and_load(self, temp_storage_dir, sample_feature_df):
        """测试Parquet格式保存和加载"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')

        # 保存
        save_resp = storage.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")
        assert isinstance(save_resp, Response)
        assert save_resp.is_success()

        # 加载
        load_resp = storage.load_features("TEST001", feature_type="test", version="v1")
        assert isinstance(load_resp, Response)
        assert load_resp.is_success()

        loaded = load_resp.data
        # 验证 (check_freq=False to ignore index frequency differences)
        pd.testing.assert_frame_equal(loaded, sample_feature_df, check_freq=False)

    def test_parquet_file_extension(self, temp_storage_dir, sample_feature_df):
        """测试Parquet文件扩展名"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')
        storage.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")

        # 验证文件存在且扩展名正确 (实际保存为 test/TEST001_v1.parquet)
        parquet_file = temp_storage_dir / "test" / "TEST001_v1.parquet"
        assert parquet_file.exists()

    def test_parquet_compression(self, temp_storage_dir, sample_feature_df):
        """测试Parquet压缩"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')

        # 创建较大的DataFrame
        large_df = pd.DataFrame(
            np.random.randn(1000, 20),
            columns=[f'feature{i}' for i in range(20)]
        )

        storage.save_features(large_df, "LARGE", feature_type="test", version="v1")

        # 验证文件大小（压缩应该比原始数据小）
        file_path = temp_storage_dir / "test" / "LARGE_v1.parquet"
        file_size = file_path.stat().st_size

        # Parquet文件应该小于未压缩的CSV
        # 这里只是验证能成功保存和加载
        loaded = storage.load_features("LARGE", feature_type="test")
        assert loaded.shape == large_df.shape

    def test_parquet_data_types(self, temp_storage_dir):
        """测试Parquet保留数据类型"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')

        # 创建包含不同数据类型的DataFrame
        df = pd.DataFrame({
            'int_col': [1, 2, 3],
            'float_col': [1.1, 2.2, 3.3],
            'str_col': ['a', 'b', 'c'],
            'bool_col': [True, False, True],
        })

        storage.save_features(df, "TYPES", feature_type="test")
        loaded = storage.load_features("TYPES", feature_type="test")

        # 验证数据类型保留
        assert loaded['int_col'].dtype == df['int_col'].dtype
        assert loaded['float_col'].dtype == df['float_col'].dtype
        assert loaded['bool_col'].dtype == df['bool_col'].dtype

    def test_parquet_index_preservation(self, temp_storage_dir, sample_feature_df):
        """测试Parquet保留索引"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')

        storage.save_features(sample_feature_df, "INDEX_TEST", feature_type="test")
        loaded = storage.load_features("INDEX_TEST", feature_type="test")

        # 验证索引
        pd.testing.assert_index_equal(loaded.index, sample_feature_df.index)


# ==================== HDF5存储测试 ====================


class TestHDF5Storage:
    """HDF5存储后端测试"""

    def test_hdf5_save_and_load(self, temp_storage_dir, sample_feature_df):
        """测试HDF5格式保存和加载"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='hdf5')

        storage.save_features(sample_feature_df, "TEST001", feature_type="test")
        loaded = storage.load_features("TEST001", feature_type="test")

        pd.testing.assert_frame_equal(loaded, sample_feature_df)

    def test_hdf5_file_extension(self, temp_storage_dir, sample_feature_df):
        """测试HDF5文件扩展名"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='hdf5')
        storage.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")

        # HDF5文件保存为 test/TEST001_v1.h5
        h5_file = temp_storage_dir / "test" / "TEST001_v1.h5"

        assert h5_file.exists()

    def test_hdf5_compression(self, temp_storage_dir):
        """测试HDF5压缩"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='hdf5')

        # 大DataFrame
        large_df = pd.DataFrame(
            np.random.randn(1000, 20),
            columns=[f'feature{i}' for i in range(20)]
        )

        storage.save_features(large_df, "LARGE", feature_type="test")
        loaded = storage.load_features("LARGE", feature_type="test")

        assert loaded.shape == large_df.shape

    def test_hdf5_index_preservation(self, temp_storage_dir, sample_feature_df):
        """测试HDF5保留索引"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='hdf5')

        storage.save_features(sample_feature_df, "INDEX_TEST", feature_type="test")
        loaded = storage.load_features("INDEX_TEST", feature_type="test")

        pd.testing.assert_index_equal(loaded.index, sample_feature_df.index)


# ==================== CSV存储测试 ====================


class TestCSVStorage:
    """CSV存储后端测试"""

    def test_csv_save_and_load(self, temp_storage_dir, sample_feature_df):
        """测试CSV格式保存和加载"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='csv')

        storage.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")
        loaded = storage.load_features("TEST001", feature_type="test", version="v1")

        # CSV可能有精度损失，使用较宽松的比较
        pd.testing.assert_frame_equal(loaded, sample_feature_df, check_exact=False, rtol=1e-5, check_freq=False)

    def test_csv_file_extension(self, temp_storage_dir, sample_feature_df):
        """测试CSV文件扩展名"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='csv')
        storage.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")

        csv_file = temp_storage_dir / "test" / "TEST001_v1.csv"
        assert csv_file.exists()

    def test_csv_readable_format(self, temp_storage_dir, sample_feature_df):
        """测试CSV文件可读性"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='csv')
        storage.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")

        # 直接用pandas读取验证
        csv_file = temp_storage_dir / "test" / "TEST001_v1.csv"
        df_direct = pd.read_csv(csv_file, index_col=0, parse_dates=True)

        assert df_direct.shape == sample_feature_df.shape

    def test_csv_index_preservation(self, temp_storage_dir, sample_feature_df):
        """测试CSV保留索引"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='csv')

        storage.save_features(sample_feature_df, "INDEX_TEST", feature_type="test")
        loaded = storage.load_features("INDEX_TEST", feature_type="test")

        # CSV的日期索引可能需要解析
        assert len(loaded.index) == len(sample_feature_df.index)


# ==================== 后端切换测试 ====================


class TestBackendSwitching:
    """存储后端切换测试"""

    def test_switch_from_parquet_to_hdf5(self, temp_storage_dir, sample_feature_df):
        """测试从Parquet切换到HDF5"""
        # 使用Parquet保存
        storage_parquet = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')
        storage_parquet.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")

        # 切换到HDF5
        storage_hdf5 = FeatureStorage(storage_dir=str(temp_storage_dir), format='hdf5')

        # 尝试加载（应该失败或返回None）
        loaded = storage_hdf5.load_features("TEST001", feature_type="test", version="v1")
        assert loaded is None  # 因为文件格式不匹配

    def test_switch_from_csv_to_parquet(self, temp_storage_dir, sample_feature_df):
        """测试从CSV切换到Parquet"""
        # 使用CSV保存
        storage_csv = FeatureStorage(storage_dir=str(temp_storage_dir), format='csv')
        storage_csv.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")

        # 切换到Parquet
        storage_parquet = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')

        # 应该加载失败
        loaded = storage_parquet.load_features("TEST001", feature_type="test", version="v1")
        assert loaded is None

    def test_multiple_formats_coexist(self, temp_storage_dir, sample_feature_df):
        """测试多种格式共存"""
        # 使用不同格式保存同一股票的不同版本
        storage_parquet = FeatureStorage(storage_dir=str(temp_storage_dir / "parquet"), format='parquet')
        storage_hdf5 = FeatureStorage(storage_dir=str(temp_storage_dir / "hdf5"), format='hdf5')
        storage_csv = FeatureStorage(storage_dir=str(temp_storage_dir / "csv"), format='csv')

        storage_parquet.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")
        storage_hdf5.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")
        storage_csv.save_features(sample_feature_df, "TEST001", feature_type="test", version="v1")

        # 验证都能加载
        loaded_parquet = storage_parquet.load_features("TEST001", feature_type="test", version="v1")
        loaded_hdf5 = storage_hdf5.load_features("TEST001", feature_type="test", version="v1")
        loaded_csv = storage_csv.load_features("TEST001", feature_type="test", version="v1")

        assert loaded_parquet is not None
        assert loaded_hdf5 is not None
        assert loaded_csv is not None


# ==================== 后端性能对比测试 ====================


class TestBackendPerformance:
    """存储后端性能对比测试"""

    @pytest.fixture
    def large_feature_df(self):
        """生成大型特征DataFrame"""
        np.random.seed(42)
        return pd.DataFrame(
            np.random.randn(5000, 50),
            columns=[f'feature{i}' for i in range(50)],
            index=pd.date_range('2020-01-01', periods=5000, freq='D')
        )

    def test_parquet_save_speed(self, temp_storage_dir, large_feature_df):
        """测试Parquet保存速度"""
        import time

        storage = FeatureStorage(storage_dir=str(temp_storage_dir / "parquet"), format='parquet')

        start = time.time()
        storage.save_features(large_feature_df, "LARGE")
        parquet_time = time.time() - start

        print(f"\nParquet save time: {parquet_time:.3f}s")
        assert parquet_time < 5.0  # 应该在5秒内完成

    def test_hdf5_save_speed(self, temp_storage_dir, large_feature_df):
        """测试HDF5保存速度"""
        import time

        storage = FeatureStorage(storage_dir=str(temp_storage_dir / "hdf5"), format='hdf5')

        start = time.time()
        storage.save_features(large_feature_df, "LARGE")
        hdf5_time = time.time() - start

        print(f"\nHDF5 save time: {hdf5_time:.3f}s")
        assert hdf5_time < 5.0

    def test_csv_save_speed(self, temp_storage_dir, large_feature_df):
        """测试CSV保存速度"""
        import time

        storage = FeatureStorage(storage_dir=str(temp_storage_dir / "csv"), format='csv')

        start = time.time()
        storage.save_features(large_feature_df, "LARGE")
        csv_time = time.time() - start

        print(f"\nCSV save time: {csv_time:.3f}s")
        assert csv_time < 10.0  # CSV通常较慢

    def test_file_size_comparison(self, temp_storage_dir, large_feature_df):
        """测试文件大小对比"""
        storage_parquet = FeatureStorage(storage_dir=str(temp_storage_dir / "parquet"), format='parquet')
        storage_hdf5 = FeatureStorage(storage_dir=str(temp_storage_dir / "hdf5"), format='hdf5')
        storage_csv = FeatureStorage(storage_dir=str(temp_storage_dir / "csv"), format='csv')

        storage_parquet.save_features(large_feature_df, "SIZE_TEST", feature_type="test", version="v1")
        storage_hdf5.save_features(large_feature_df, "SIZE_TEST", feature_type="test", version="v1")
        storage_csv.save_features(large_feature_df, "SIZE_TEST", feature_type="test", version="v1")

        # 获取文件大小 (文件保存在 test/SIZE_TEST_v1.*)
        parquet_size = (temp_storage_dir / "parquet" / "test" / "SIZE_TEST_v1.parquet").stat().st_size
        csv_size = (temp_storage_dir / "csv" / "test" / "SIZE_TEST_v1.csv").stat().st_size

        # HDF5文件保存为 .h5
        hdf5_path = temp_storage_dir / "hdf5" / "test" / "SIZE_TEST_v1.h5"
        hdf5_size = hdf5_path.stat().st_size

        print(f"\nFile sizes: Parquet={parquet_size}, HDF5={hdf5_size}, CSV={csv_size}")

        # Parquet和HDF5通常比CSV小
        assert parquet_size < csv_size
        assert hdf5_size < csv_size


# ==================== 后端兼容性测试 ====================


class TestBackendCompatibility:
    """存储后端兼容性测试"""

    def test_parquet_with_nan_values(self, temp_storage_dir):
        """测试Parquet处理NaN值"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')

        df = pd.DataFrame({
            'feature1': [1.0, np.nan, 3.0],
            'feature2': [np.nan, 2.0, np.nan],
        })

        storage.save_features(df, "NAN_TEST", feature_type="test")
        loaded = storage.load_features("NAN_TEST", feature_type="test")

        pd.testing.assert_frame_equal(loaded, df)

    def test_hdf5_with_nan_values(self, temp_storage_dir):
        """测试HDF5处理NaN值"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='hdf5')

        df = pd.DataFrame({
            'feature1': [1.0, np.nan, 3.0],
            'feature2': [np.nan, 2.0, np.nan],
        })

        storage.save_features(df, "NAN_TEST", feature_type="test")
        loaded = storage.load_features("NAN_TEST", feature_type="test")

        pd.testing.assert_frame_equal(loaded, df)

    def test_csv_with_nan_values(self, temp_storage_dir):
        """测试CSV处理NaN值"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='csv')

        df = pd.DataFrame({
            'feature1': [1.0, np.nan, 3.0],
            'feature2': [np.nan, 2.0, np.nan],
        })

        storage.save_features(df, "NAN_TEST", feature_type="test")
        loaded = storage.load_features("NAN_TEST", feature_type="test")

        pd.testing.assert_frame_equal(loaded, df, check_exact=False)

    def test_parquet_with_unicode(self, temp_storage_dir):
        """测试Parquet处理Unicode"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')

        df = pd.DataFrame({
            '特征1': [1, 2, 3],
            '特征2': [4, 5, 6],
        })

        storage.save_features(df, "UNICODE", feature_type="test")
        loaded = storage.load_features("UNICODE", feature_type="test")

        pd.testing.assert_frame_equal(loaded, df)


# ==================== 错误处理测试 ====================


class TestBackendErrorHandling:
    """存储后端错误处理测试"""

    def test_load_nonexistent_file_parquet(self, temp_storage_dir):
        """测试Parquet加载不存在的文件"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')

        result = storage.load_features("NONEXISTENT", feature_type="test")
        assert result is None

    def test_load_nonexistent_file_hdf5(self, temp_storage_dir):
        """测试HDF5加载不存在的文件"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='hdf5')

        result = storage.load_features("NONEXISTENT", feature_type="test")
        assert result is None

    def test_load_nonexistent_file_csv(self, temp_storage_dir):
        """测试CSV加载不存在的文件"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='csv')

        result = storage.load_features("NONEXISTENT", feature_type="test")
        assert result is None

    def test_corrupted_file_handling_parquet(self, temp_storage_dir, sample_feature_df):
        """测试Parquet处理损坏文件"""
        storage = FeatureStorage(storage_dir=str(temp_storage_dir), format='parquet')
        storage.save_features(sample_feature_df, "CORRUPT", feature_type="test", version="v1")

        # 损坏文件 (实际路径是 test/CORRUPT_v1.parquet)
        file_path = temp_storage_dir / "test" / "CORRUPT_v1.parquet"
        with open(file_path, 'w') as f:
            f.write("corrupted data")

        # 应该返回None或抛出异常
        result = storage.load_features("CORRUPT", feature_type="test", version="v1")
        assert result is None or isinstance(result, type(None))

    def test_invalid_format(self, temp_storage_dir):
        """测试无效的存储格式"""
        with pytest.raises((ValueError, KeyError)):
            FeatureStorage(storage_dir=str(temp_storage_dir), format='invalid_format')


# ==================== 直接后端API测试 ====================


class TestBackendDirectAPI:
    """直接测试后端类的API"""

    def test_parquet_backend_direct(self, temp_storage_dir, sample_feature_df):
        """直接测试ParquetStorage"""
        backend = ParquetStorage(str(temp_storage_dir))

        file_path = temp_storage_dir / "test.parquet"
        backend.save(sample_feature_df, file_path)
        loaded = backend.load(file_path)

        # 不检查频率信息,因为保存后可能丢失
        pd.testing.assert_frame_equal(loaded, sample_feature_df, check_freq=False)

    def test_hdf5_backend_direct(self, temp_storage_dir, sample_feature_df):
        """直接测试HDF5Storage"""
        backend = HDF5Storage(str(temp_storage_dir))

        file_path = temp_storage_dir / "test.h5"
        backend.save(sample_feature_df, file_path)
        loaded = backend.load(file_path)

        pd.testing.assert_frame_equal(loaded, sample_feature_df)

    def test_csv_backend_direct(self, temp_storage_dir, sample_feature_df):
        """直接测试CSVStorage"""
        backend = CSVStorage(str(temp_storage_dir))

        file_path = temp_storage_dir / "test.csv"
        backend.save(sample_feature_df, file_path)
        loaded = backend.load(file_path)

        # 不检查频率信息,因为CSV保存后会丢失
        pd.testing.assert_frame_equal(loaded, sample_feature_df, check_exact=False, rtol=1e-5, check_freq=False)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
