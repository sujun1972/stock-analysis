#!/usr/bin/env python3
"""
FeatureCache 单元测试

测试特征缓存管理器的功能
"""

import sys
import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from src.data_pipeline.feature_cache import FeatureCache


class TestFeatureCache(unittest.TestCase):
    """测试 FeatureCache 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("FeatureCache 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        # 创建临时缓存目录
        self.temp_dir = tempfile.mkdtemp()
        self.cache = FeatureCache(cache_dir=self.temp_dir, feature_version='v2.1')

        # 创建测试数据
        np.random.seed(42)
        self.X = pd.DataFrame({
            'feature1': np.random.randn(100),
            'feature2': np.random.randn(100),
            'feature3': np.random.randn(100)
        })
        self.y = pd.Series(np.random.randn(100), name='target')

    def tearDown(self):
        """每个测试后的清理"""
        # 删除临时目录
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_01_init(self):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        cache = FeatureCache(cache_dir=self.temp_dir, feature_version='v2.1')
        self.assertIsNotNone(cache)
        self.assertEqual(cache.feature_version, 'v2.1')
        self.assertTrue(cache.cache_dir.exists())

        print("  ✓ 初始化成功")

    def test_02_get_cache_path(self):
        """测试2: 生成缓存路径"""
        print("\n[测试2] 生成缓存路径...")

        config = {
            'scaler_type': 'robust',
            'target_period': 5,
            'feature_config_hash': 'abc123'
        }

        path1 = self.cache.get_cache_path('000001', '20230101', '20231231', config)
        path2 = self.cache.get_cache_path('000001', '20230101', '20231231', config)

        # 相同配置应该生成相同路径
        self.assertEqual(path1, path2)

        # 不同配置应该生成不同路径
        config_diff = config.copy()
        config_diff['target_period'] = 10
        path3 = self.cache.get_cache_path('000001', '20230101', '20231231', config_diff)
        self.assertNotEqual(path1, path3)

        print(f"  ✓ 缓存路径生成成功")
        print(f"  路径: {path1.name}")

    def test_03_save_and_load(self):
        """测试3: 保存和加载"""
        print("\n[测试3] 保存和加载...")

        config = {
            'scaler_type': 'robust',
            'target_period': 5,
            'feature_config_hash': 'test123'
        }

        cache_file = self.cache.get_cache_path('000001', '20230101', '20231231', config)

        # 保存
        self.cache.save(self.X, self.y, cache_file, config, 'target')

        # 验证文件存在
        self.assertTrue(cache_file.exists())

        # 加载
        result = self.cache.load(cache_file, 'target', config)

        self.assertIsNotNone(result)
        X_loaded, y_loaded = result

        # 验证数据一致
        pd.testing.assert_frame_equal(self.X, X_loaded)
        pd.testing.assert_series_equal(self.y, y_loaded)

        print(f"  ✓ 保存和加载成功")

    def test_04_cache_validation(self):
        """测试4: 缓存验证"""
        print("\n[测试4] 缓存验证...")

        config = {
            'scaler_type': 'robust',
            'target_period': 5,
            'feature_config_hash': 'test123'
        }

        cache_file = self.cache.get_cache_path('000001', '20230101', '20231231', config)

        # 保存
        self.cache.save(self.X, self.y, cache_file, config, 'target')

        # 使用相同配置加载 - 应该成功
        result1 = self.cache.load(cache_file, 'target', config)
        self.assertIsNotNone(result1)

        # 使用不同配置加载 - 应该失败（验证不通过）
        config_diff = config.copy()
        config_diff['scaler_type'] = 'standard'
        result2 = self.cache.load(cache_file, 'target', config_diff)
        self.assertIsNone(result2)

        print(f"  ✓ 缓存验证成功")

    def test_05_version_mismatch(self):
        """测试5: 版本不匹配"""
        print("\n[测试5] 版本不匹配...")

        config = {
            'scaler_type': 'robust',
            'target_period': 5,
            'feature_config_hash': 'test123'
        }

        cache_file = self.cache.get_cache_path('000001', '20230101', '20231231', config)

        # 使用v2.1保存
        self.cache.save(self.X, self.y, cache_file, config, 'target')

        # 使用v2.0加载
        cache_v2 = FeatureCache(cache_dir=self.temp_dir, feature_version='v2.0')
        result = cache_v2.load(cache_file, 'target', config)

        # 版本不匹配，应该返回 None
        self.assertIsNone(result)

        print(f"  ✓ 版本不匹配处理正确")

    def test_06_clear_cache(self):
        """测试6: 清除缓存"""
        print("\n[测试6] 清除缓存...")

        config = {
            'scaler_type': 'robust',
            'target_period': 5,
            'feature_config_hash': 'test123'
        }

        # 保存多个股票的缓存
        cache_file1 = self.cache.get_cache_path('000001', '20230101', '20231231', config)
        cache_file2 = self.cache.get_cache_path('000002', '20230101', '20231231', config)

        self.cache.save(self.X, self.y, cache_file1, config, 'target')
        self.cache.save(self.X, self.y, cache_file2, config, 'target')

        self.assertTrue(cache_file1.exists())
        self.assertTrue(cache_file2.exists())

        # 清除特定股票
        self.cache.clear(symbol='000001')

        # 000001 应该被删除，000002 应该保留
        self.assertFalse(cache_file1.exists())
        self.assertTrue(cache_file2.exists())

        # 清除所有
        self.cache.clear()
        self.assertFalse(cache_file2.exists())

        print(f"  ✓ 清除缓存成功")

    def test_07_compute_feature_config_hash(self):
        """测试7: 计算特征配置哈希"""
        print("\n[测试7] 计算特征配置哈希...")

        config1 = {
            'version': 'v2.1',
            'scaler_type': 'robust',
            'target_period': 5
        }

        config2 = {
            'version': 'v2.1',
            'scaler_type': 'robust',
            'target_period': 5
        }

        config3 = {
            'version': 'v2.1',
            'scaler_type': 'robust',
            'target_period': 10  # 不同
        }

        hash1 = self.cache.compute_feature_config_hash(config1)
        hash2 = self.cache.compute_feature_config_hash(config2)
        hash3 = self.cache.compute_feature_config_hash(config3)

        # 相同配置生成相同哈希
        self.assertEqual(hash1, hash2)

        # 不同配置生成不同哈希
        self.assertNotEqual(hash1, hash3)

        # 哈希长度应该是8
        self.assertEqual(len(hash1), 8)

        print(f"  ✓ 哈希计算成功")
        print(f"  Hash: {hash1}")

    def test_08_corrupted_cache(self):
        """测试8: 损坏的缓存"""
        print("\n[测试8] 损坏的缓存...")

        config = {
            'scaler_type': 'robust',
            'target_period': 5,
            'feature_config_hash': 'test123'
        }

        cache_file = self.cache.get_cache_path('000001', '20230101', '20231231', config)

        # 创建损坏的缓存文件
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text("corrupted data")

        # 尝试加载应该返回 None
        result = self.cache.load(cache_file, 'target', config)
        self.assertIsNone(result)

        print(f"  ✓ 损坏缓存处理正确")

    def test_09_missing_metadata(self):
        """测试9: 缺少元数据"""
        print("\n[测试9] 缺少元数据...")

        config = {
            'scaler_type': 'robust',
            'target_period': 5,
            'feature_config_hash': 'test123'
        }

        cache_file = self.cache.get_cache_path('000001', '20230101', '20231231', config)

        # 保存数据但删除元数据
        self.cache.save(self.X, self.y, cache_file, config, 'target')

        metadata_file = cache_file.with_suffix('.meta.json')
        if metadata_file.exists():
            metadata_file.unlink()

        # 尝试加载应该返回 None
        result = self.cache.load(cache_file, 'target', config)
        self.assertIsNone(result)

        print(f"  ✓ 缺少元数据处理正确")

    def test_10_cache_metadata_content(self):
        """测试10: 缓存元数据内容"""
        print("\n[测试10] 缓存元数据内容...")

        import json

        config = {
            'scaler_type': 'robust',
            'target_period': 5,
            'feature_config_hash': 'test123'
        }

        cache_file = self.cache.get_cache_path('000001', '20230101', '20231231', config)
        self.cache.save(self.X, self.y, cache_file, config, 'target')

        # 读取元数据
        metadata_file = cache_file.with_suffix('.meta.json')
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        # 验证元数据内容
        self.assertEqual(metadata['version'], 'v2.1')
        self.assertEqual(metadata['feature_count'], 3)
        self.assertEqual(metadata['sample_count'], 100)
        self.assertEqual(metadata['target_name'], 'target')
        self.assertIn('created_at', metadata)
        self.assertEqual(set(metadata['feature_names']), {'feature1', 'feature2', 'feature3'})

        print(f"  ✓ 元数据内容正确")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestFeatureCache)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"运行: {result.testsRun}, 成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}, 错误: {len(result.errors)}")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
