#!/usr/bin/env python3
"""
类型转换工具模块单元测试

测试 type_utils 中所有类型转换函数
"""

import sys
import unittest
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from utils.type_utils import (
    safe_float,
    safe_int,
    safe_str,
    safe_float_series,
    safe_int_series,
    safe_float_or_none,
    safe_float_or_zero,
    safe_int_or_zero,
    is_numeric,
    is_valid_string
)


class TestScalarConversion(unittest.TestCase):
    """测试标量转换函数"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("类型转换工具 - 标量转换测试")
        print("="*60)

    def test_01_safe_float_normal(self):
        """测试1: safe_float - 正常值"""
        print("\n[测试1] safe_float 正常值...")

        self.assertEqual(safe_float(3.14), 3.14)
        self.assertEqual(safe_float(42), 42.0)
        self.assertEqual(safe_float("3.14"), 3.14)
        self.assertEqual(safe_float(0), 0.0)
        self.assertEqual(safe_float(-3.14), -3.14)

        print("  ✓ 正常值转换正确")

    def test_02_safe_float_special(self):
        """测试2: safe_float - 特殊值"""
        print("\n[测试2] safe_float 特殊值...")

        self.assertEqual(safe_float(None), 0.0)
        self.assertEqual(safe_float(np.nan), 0.0)
        self.assertEqual(safe_float(pd.NA), 0.0)
        self.assertEqual(safe_float(np.inf), 0.0)
        self.assertEqual(safe_float(-np.inf), 0.0)
        self.assertEqual(safe_float("invalid"), 0.0)

        # 测试自定义默认值
        self.assertEqual(safe_float(None, default=-1.0), -1.0)
        self.assertEqual(safe_float(np.nan, default=999.0), 999.0)

        print("  ✓ 特殊值处理正确")

    def test_03_safe_int_normal(self):
        """测试3: safe_int - 正常值"""
        print("\n[测试3] safe_int 正常值...")

        self.assertEqual(safe_int(42), 42)
        self.assertEqual(safe_int(3.14), 3)
        self.assertEqual(safe_int(3.9), 3)
        self.assertEqual(safe_int("42"), 42)
        self.assertEqual(safe_int(0), 0)
        self.assertEqual(safe_int(-42), -42)

        print("  ✓ 正常值转换正确")

    def test_04_safe_int_special(self):
        """测试4: safe_int - 特殊值"""
        print("\n[测试4] safe_int 特殊值...")

        self.assertEqual(safe_int(None), 0)
        self.assertEqual(safe_int(np.nan), 0)
        self.assertEqual(safe_int(pd.NA), 0)
        self.assertEqual(safe_int(np.inf), 0)
        self.assertEqual(safe_int(-np.inf), 0)
        self.assertEqual(safe_int("invalid"), 0)

        # 测试自定义默认值
        self.assertEqual(safe_int(None, default=-1), -1)
        self.assertEqual(safe_int(np.nan, default=999), 999)

        print("  ✓ 特殊值处理正确")

    def test_05_safe_str_normal(self):
        """测试5: safe_str - 正常值"""
        print("\n[测试5] safe_str 正常值...")

        self.assertEqual(safe_str("hello"), "hello")
        self.assertEqual(safe_str("  hello  "), "hello")
        self.assertEqual(safe_str(42), "42")
        self.assertEqual(safe_str(3.14), "3.14")

        print("  ✓ 正常值转换正确")

    def test_06_safe_str_special(self):
        """测试6: safe_str - 特殊值"""
        print("\n[测试6] safe_str 特殊值...")

        self.assertEqual(safe_str(None), "")
        self.assertEqual(safe_str(np.nan), "")
        self.assertEqual(safe_str(pd.NA), "")

        # 测试自定义默认值
        self.assertEqual(safe_str(None, default="N/A"), "N/A")

        print("  ✓ 特殊值处理正确")


class TestSeriesConversion(unittest.TestCase):
    """测试 Series 向量化转换函数"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("类型转换工具 - Series 转换测试")
        print("="*60)

    def test_01_safe_float_series(self):
        """测试1: safe_float_series"""
        print("\n[测试1] safe_float_series...")

        s = pd.Series([1.0, np.nan, 3.0, None, np.inf, -np.inf])
        result = safe_float_series(s)

        expected = np.array([1.0, 0.0, 3.0, 0.0, 0.0, 0.0])
        np.testing.assert_array_equal(result, expected)

        print("  ✓ Series 转换正确")

    def test_02_safe_int_series(self):
        """测试2: safe_int_series"""
        print("\n[测试2] safe_int_series...")

        s = pd.Series([1.5, np.nan, 3.9, None, np.inf])
        result = safe_int_series(s)

        expected = np.array([1, 0, 3, 0, 0])
        np.testing.assert_array_equal(result, expected)

        print("  ✓ Series 转换正确")

    def test_03_safe_float_or_none(self):
        """测试3: safe_float_or_none"""
        print("\n[测试3] safe_float_or_none...")

        s = pd.Series([1.0, np.nan, 3.0, None])
        result = safe_float_or_none(s)

        self.assertEqual(result[0], 1.0)
        self.assertIsNone(result[1])
        self.assertEqual(result[2], 3.0)
        self.assertIsNone(result[3])

        print("  ✓ Series 转换正确（保留 None）")

    def test_04_safe_float_or_zero(self):
        """测试4: safe_float_or_zero"""
        print("\n[测试4] safe_float_or_zero...")

        s = pd.Series([1.0, np.nan, 3.0])
        result = safe_float_or_zero(s)

        expected = np.array([1.0, 0.0, 3.0])
        np.testing.assert_array_equal(result, expected)

        print("  ✓ Series 转换正确（NaN -> 0.0）")

    def test_05_safe_int_or_zero(self):
        """测试5: safe_int_or_zero"""
        print("\n[测试5] safe_int_or_zero...")

        s = pd.Series([1, np.nan, 3])
        result = safe_int_or_zero(s)

        expected = np.array([1, 0, 3])
        np.testing.assert_array_equal(result, expected)

        print("  ✓ Series 转换正确（NaN -> 0）")


class TestTypeChecking(unittest.TestCase):
    """测试类型检查函数"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("类型转换工具 - 类型检查测试")
        print("="*60)

    def test_01_is_numeric(self):
        """测试1: is_numeric"""
        print("\n[测试1] is_numeric...")

        # 有效数字
        self.assertTrue(is_numeric(42))
        self.assertTrue(is_numeric(3.14))
        self.assertTrue(is_numeric(-3.14))
        self.assertTrue(is_numeric(0))

        # 无效值
        self.assertFalse(is_numeric(None))
        self.assertFalse(is_numeric(np.nan))
        self.assertFalse(is_numeric(pd.NA))
        self.assertFalse(is_numeric(np.inf))
        self.assertFalse(is_numeric(-np.inf))
        self.assertFalse(is_numeric("42"))
        self.assertFalse(is_numeric("hello"))

        print("  ✓ 数字检查正确")

    def test_02_is_valid_string(self):
        """测试2: is_valid_string"""
        print("\n[测试2] is_valid_string...")

        # 有效字符串
        self.assertTrue(is_valid_string("hello"))
        self.assertTrue(is_valid_string("  hello  "))
        self.assertTrue(is_valid_string("123"))

        # 无效值
        self.assertFalse(is_valid_string(""))
        self.assertFalse(is_valid_string("   "))
        self.assertFalse(is_valid_string(None))
        self.assertFalse(is_valid_string(np.nan))
        self.assertFalse(is_valid_string(pd.NA))
        self.assertFalse(is_valid_string(42))

        print("  ✓ 字符串检查正确")


class TestPerformance(unittest.TestCase):
    """测试性能"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("类型转换工具 - 性能测试")
        print("="*60)

    def test_01_series_performance(self):
        """测试1: Series 转换性能"""
        print("\n[测试1] Series 转换性能...")

        import time

        # 创建大数据集
        s = pd.Series(np.random.randn(10000))
        s.iloc[::100] = np.nan  # 添加一些 NaN

        # 测试向量化转换
        start = time.time()
        result = safe_float_series(s)
        elapsed = time.time() - start

        print(f"  数据规模: {len(s)} 行")
        print(f"  转换耗时: {elapsed*1000:.2f}ms")
        self.assertEqual(len(result), len(s))
        self.assertLess(elapsed, 0.1, "Should complete in less than 100ms")

        print("  ✓ 性能符合预期")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestScalarConversion))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSeriesConversion))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTypeChecking))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestPerformance))

    # 运行测试
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
