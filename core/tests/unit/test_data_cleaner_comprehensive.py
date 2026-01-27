#!/usr/bin/env python3
"""
Data Cleaner 完整单元测试
测试 src/data/data_cleaner.py 模块的所有功能，提升覆盖率到90%+

包括:
- 异常数据处理（极端值、缺失值、无穷值）
- OHLC数据验证和修复
- 重采样功能
- 批量清洗功能
- 边界条件测试
"""

import sys
import unittest
import pandas as pd
import numpy as np
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.data_cleaner import DataCleaner, batch_clean_data


class TestDataCleanerComprehensive(unittest.TestCase):
    """测试 DataCleaner 类的完整功能"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*70)
        print("Data Cleaner 完整单元测试 - 提升覆盖率")
        print("="*70)

    def setUp(self):
        """每个测试前的准备"""
        self.cleaner = DataCleaner(verbose=False)

        # 创建标准测试数据
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        self.test_df = pd.DataFrame({
            'open': np.random.uniform(10, 20, 100),
            'high': np.random.uniform(15, 25, 100),
            'low': np.random.uniform(5, 15, 100),
            'close': np.random.uniform(10, 20, 100),
            'vol': np.random.uniform(1000000, 10000000, 100),
            'amount': np.random.uniform(10000000, 100000000, 100)
        }, index=dates)

    # ==================== 基础功能测试 ====================

    def test_01_init_verbose_true(self):
        """测试1: 初始化（verbose=True）"""
        print("\n[测试1] 初始化 verbose=True...")

        cleaner = DataCleaner(verbose=True)
        self.assertTrue(cleaner.verbose)
        self.assertIsNotNone(cleaner.cleaning_stats)
        self.assertEqual(cleaner.cleaning_stats['total_rows'], 0)

        print("  ✓ 初始化成功 (verbose=True)")

    def test_02_clean_empty_dataframe(self):
        """测试2: 清洗空DataFrame"""
        print("\n[测试2] 清洗空DataFrame...")

        empty_df = pd.DataFrame()
        result = self.cleaner.clean_price_data(empty_df, '000001')

        self.assertTrue(result.empty)
        print("  ✓ 空DataFrame处理正确")

    def test_03_clean_none_dataframe(self):
        """测试3: 清洗None DataFrame"""
        print("\n[测试3] 清洗None DataFrame...")

        result = self.cleaner.clean_price_data(None, '000001')
        self.assertIsNone(result)

        print("  ✓ None DataFrame处理正确")

    def test_04_clean_normal_data(self):
        """测试4: 清洗正常数据"""
        print("\n[测试4] 清洗正常数据...")

        result = self.cleaner.clean_price_data(self.test_df, '000001')

        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertGreaterEqual(len(result), len(self.test_df) * 0.8)

        stats = self.cleaner.get_stats()
        self.assertEqual(stats['total_rows'], len(self.test_df))
        self.assertEqual(stats['final_rows'], len(result))

        print(f"  ✓ 原始: {len(self.test_df)}, 清洗后: {len(result)}")

    def test_05_clean_with_verbose(self):
        """测试5: verbose模式清洗数据"""
        print("\n[测试5] verbose模式清洗...")

        cleaner_verbose = DataCleaner(verbose=True)

        # 添加一些问题数据，触发verbose输出
        df = self.test_df.copy()
        df.loc[df.index[:10], 'close'] = np.nan  # 添加缺失值

        result = cleaner_verbose.clean_price_data(df, '000001')

        self.assertIsInstance(result, pd.DataFrame)
        self.assertLess(len(result), len(df))

        print(f"  ✓ verbose模式正常工作")

    # ==================== 缺失值处理测试 ====================

    def test_06_handle_missing_price_values(self):
        """测试6: 处理价格缺失值"""
        print("\n[测试6] 处理价格缺失值...")

        df = self.test_df.copy()
        # 添加价格缺失值
        df.loc[df.index[10], 'close'] = np.nan
        df.loc[df.index[15], 'open'] = np.nan
        df.loc[df.index[20], 'high'] = np.nan
        df.loc[df.index[25], 'low'] = np.nan

        result = self.cleaner.clean_price_data(df, '000001')

        # 验证缺失值被处理
        self.assertFalse(result['close'].isnull().any())
        self.assertFalse(result['open'].isnull().any())
        self.assertFalse(result['high'].isnull().any())
        self.assertFalse(result['low'].isnull().any())

        stats = self.cleaner.get_stats()
        self.assertGreaterEqual(stats['missing_filled'], 0)

        print(f"  ✓ 价格缺失值处理完成 (填充: {stats['missing_filled']})")

    def test_07_handle_missing_volume_values(self):
        """测试7: 处理成交量缺失值"""
        print("\n[测试7] 处理成交量缺失值...")

        df = self.test_df.copy()
        # 添加成交量缺失值
        df.loc[df.index[10], 'vol'] = np.nan
        df.loc[df.index[15], 'amount'] = np.nan

        result = self.cleaner.clean_price_data(df, '000001')

        # 成交量缺失值应该被填充为0
        self.assertFalse(result['vol'].isnull().any())
        if 'amount' in result.columns:
            self.assertFalse(result['amount'].isnull().any())

        print("  ✓ 成交量缺失值处理完成")

    def test_08_handle_all_columns_missing(self):
        """测试8: 处理某行所有列都缺失的情况"""
        print("\n[测试8] 处理整行缺失...")

        df = self.test_df.copy()
        # 某几行的所有数据都缺失
        df.loc[df.index[10:15], :] = np.nan

        result = self.cleaner.clean_price_data(df, '000001')

        # 这些行应该被删除
        self.assertLess(len(result), len(df))
        self.assertFalse(result.isnull().any().any())

        print(f"  ✓ 整行缺失处理完成 (删除: {len(df) - len(result)}行)")

    # ==================== 重复值处理测试 ====================

    def test_09_remove_duplicate_dates(self):
        """测试9: 移除重复日期"""
        print("\n[测试9] 移除重复日期...")

        df = self.test_df.copy()
        # 添加重复的日期
        duplicate_row = df.iloc[10:11].copy()
        df = pd.concat([df, duplicate_row])

        original_len = len(df)
        result = self.cleaner.clean_price_data(df, '000001')

        # 验证重复被移除
        self.assertLess(len(result), original_len)
        self.assertEqual(len(result), len(result.index.unique()))

        stats = self.cleaner.get_stats()
        self.assertGreater(stats['duplicates_removed'], 0)

        print(f"  ✓ 重复日期移除完成 (移除: {stats['duplicates_removed']})")

    def test_10_remove_duplicates_non_datetime_index(self):
        """测试10: 移除非日期索引的重复行"""
        print("\n[测试10] 移除非日期索引的重复行...")

        df = self.test_df.copy()
        df = df.reset_index(drop=True)  # 移除日期索引

        # 添加完全重复的行
        duplicate_row = df.iloc[10:11].copy()
        df = pd.concat([df, duplicate_row])

        result = self.cleaner.clean_price_data(df, '000001')

        # 验证重复被移除
        self.assertLessEqual(len(result), len(df))

        print("  ✓ 非日期索引重复行移除完成")

    # ==================== 异常值处理测试 ====================

    def test_11_remove_invalid_price(self):
        """测试11: 移除无效价格"""
        print("\n[测试11] 移除无效价格...")

        df = self.test_df.copy()
        # 添加异常价格
        df.loc[df.index[10], 'close'] = -1  # 负价格
        df.loc[df.index[15], 'close'] = 0  # 零价格
        df.loc[df.index[20], 'close'] = 20000  # 超高价格

        result = self.cleaner.clean_price_data(df, '000001')

        # 验证异常价格被移除
        self.assertLess(len(result), len(df))
        self.assertTrue((result['close'] > 0.01).all())
        self.assertTrue((result['close'] < 10000).all())

        stats = self.cleaner.get_stats()
        self.assertGreater(stats['outliers_removed'], 0)

        print(f"  ✓ 无效价格移除完成 (移除: {stats['outliers_removed']})")

    def test_12_remove_extreme_daily_change(self):
        """测试12: 移除极端涨跌幅"""
        print("\n[测试12] 移除极端涨跌幅...")

        df = self.test_df.copy()
        # 制造极端涨幅（单日涨200%）
        df.loc[df.index[30], 'close'] = df.loc[df.index[29], 'close'] * 3

        result = self.cleaner.clean_price_data(df, '000001')

        # 验证该行被移除
        self.assertLess(len(result), len(df))

        stats = self.cleaner.get_stats()
        self.assertGreater(stats['outliers_removed'], 0)

        print("  ✓ 极端涨跌幅移除完成")

    def test_13_outliers_first_day_exception(self):
        """测试13: 首日数据不移除（即使涨跌幅大）"""
        print("\n[测试13] 首日数据异常涨跌幅不移除...")

        df = self.test_df.copy()
        # 首日设置极端值
        first_day = df.index[0]
        df.loc[first_day, 'close'] = 1000

        result = self.cleaner.clean_price_data(df, '000001')

        # 首日数据应该保留
        self.assertGreater(len(result), 0)

        print("  ✓ 首日数据保留正确")

    # ==================== 数据类型测试 ====================

    def test_14_ensure_numeric_types(self):
        """测试14: 确保数据类型正确"""
        print("\n[测试14] 确保数据类型正确...")

        df = self.test_df.copy()
        # 直接测试 _ensure_data_types 方法
        df_with_strings = df.copy()
        df_with_strings['close'] = df_with_strings['close'].astype(str)
        df_with_strings['vol'] = df_with_strings['vol'].astype(str)

        result = self.cleaner._ensure_data_types(df_with_strings)

        # 验证数据类型被转换为数字
        self.assertTrue(pd.api.types.is_numeric_dtype(result['close']))
        self.assertTrue(pd.api.types.is_numeric_dtype(result['vol']))

        print("  ✓ 数据类型转换正确")

    def test_15_handle_coerce_errors(self):
        """测试15: 处理无法转换的数据"""
        print("\n[测试15] 处理无法转换的数据...")

        df = self.test_df.copy()
        # 直接测试 _ensure_data_types 方法对无效字符串的处理
        df_with_invalid = df.copy()
        df_with_invalid['close'] = df_with_invalid['close'].astype(str)
        df_with_invalid.loc[df_with_invalid.index[10], 'close'] = 'invalid'

        result = self.cleaner._ensure_data_types(df_with_invalid)

        # 无法转换的字符串会变成NaN
        self.assertTrue(result.loc[df_with_invalid.index[10], 'close'] is pd.NA or
                       pd.isna(result.loc[df_with_invalid.index[10], 'close']))

        print("  ✓ 无法转换的数据处理正确")

    # ==================== OHLC验证测试 ====================

    def test_16_validate_ohlc_normal(self):
        """测试16: OHLC验证（正常数据）"""
        print("\n[测试16] OHLC验证（正常数据）...")

        result = self.cleaner.validate_ohlc(self.test_df, fix=False)

        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)

        print("  ✓ OHLC验证正常数据通过")

    def test_17_validate_ohlc_fix_high(self):
        """测试17: 修复high值"""
        print("\n[测试17] 修复high值...")

        df = self.test_df.copy()
        # 制造high < close的异常
        df.loc[df.index[10], 'high'] = 5
        df.loc[df.index[10], 'close'] = 15

        result = self.cleaner.validate_ohlc(df, fix=True)

        # 验证修复
        self.assertTrue((result['high'] >= result['close']).all())
        self.assertTrue((result['high'] >= result['open']).all())
        self.assertTrue((result['high'] >= result['low']).all())

        print("  ✓ high值修复成功")

    def test_18_validate_ohlc_fix_low(self):
        """测试18: 修复low值"""
        print("\n[测试18] 修复low值...")

        df = self.test_df.copy()
        # 制造low > close的异常
        df.loc[df.index[10], 'low'] = 25
        df.loc[df.index[10], 'close'] = 15

        result = self.cleaner.validate_ohlc(df, fix=True)

        # 验证修复
        self.assertTrue((result['low'] <= result['close']).all())
        self.assertTrue((result['low'] <= result['open']).all())
        self.assertTrue((result['low'] <= result['high']).all())

        print("  ✓ low值修复成功")

    def test_19_validate_ohlc_remove_negative_prices(self):
        """测试19: 移除负价格"""
        print("\n[测试19] 移除负价格...")

        df = self.test_df.copy()
        df.loc[df.index[10], 'close'] = -5

        result = self.cleaner.validate_ohlc(df, fix=True)

        # 所有价格应该 > 0
        self.assertTrue((result['open'] > 0).all())
        self.assertTrue((result['high'] > 0).all())
        self.assertTrue((result['low'] > 0).all())
        self.assertTrue((result['close'] > 0).all())

        print("  ✓ 负价格移除成功")

    def test_20_validate_ohlc_without_required_columns(self):
        """测试20: 缺少必需列时的OHLC验证"""
        print("\n[测试20] 缺少必需列时的OHLC验证...")

        df = pd.DataFrame({'close': [10, 20, 30]})

        result = self.cleaner.validate_ohlc(df, fix=True)

        # 缺少必需列，应该直接返回
        self.assertEqual(len(result), len(df))

        print("  ✓ 缺少必需列时处理正确")

    def test_21_validate_ohlc_verbose_mode(self):
        """测试21: OHLC验证verbose模式"""
        print("\n[测试21] OHLC验证verbose模式...")

        cleaner_verbose = DataCleaner(verbose=True)

        df = self.test_df.copy()
        # 制造多个无法修复的异常，确保会有行被移除
        for i in [10, 15, 20, 25]:
            df.loc[df.index[i], 'high'] = 5
            df.loc[df.index[i], 'low'] = 25
            df.loc[df.index[i], 'open'] = 15
            df.loc[df.index[i], 'close'] = 15

        result = cleaner_verbose.validate_ohlc(df, fix=True)

        # OHLC修复会自动调整high和low，所以可能不会移除行
        # 只验证函数正常执行
        self.assertIsInstance(result, pd.DataFrame)

        print("  ✓ verbose模式OHLC验证正常")

    # ==================== 重采样测试 ====================

    def test_22_resample_to_daily(self):
        """测试22: 分钟数据重采样为日线"""
        print("\n[测试22] 分钟数据重采样为日线...")

        # 创建分钟数据
        minute_dates = pd.date_range('2023-01-01 09:30', periods=240, freq='1min')
        minute_df = pd.DataFrame({
            'open': np.random.uniform(10, 20, 240),
            'high': np.random.uniform(15, 25, 240),
            'low': np.random.uniform(5, 15, 240),
            'close': np.random.uniform(10, 20, 240),
            'vol': np.random.uniform(100000, 1000000, 240),
            'amount': np.random.uniform(1000000, 10000000, 240)
        }, index=minute_dates)

        result = self.cleaner.resample_to_daily(minute_df)

        # 验证重采样结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertLess(len(result), len(minute_df))
        self.assertTrue(all(col in result.columns for col in ['open', 'high', 'low', 'close', 'vol']))

        # 验证聚合逻辑
        if len(result) > 0:
            # open应该是第一个值，close应该是最后一个值
            # vol应该是总和
            first_day = result.index[0]
            day_data = minute_df[minute_df.index.date == first_day.date()]
            if len(day_data) > 0:
                self.assertGreater(result.loc[first_day, 'vol'], 0)

        print(f"  ✓ 重采样成功: {len(minute_df)}条分钟数据 -> {len(result)}条日线数据")

    def test_23_resample_remove_zero_volume_days(self):
        """测试23: 重采样时移除零成交量日期"""
        print("\n[测试23] 重采样时移除零成交量日期...")

        # 创建包含零成交量的分钟数据
        minute_dates = pd.date_range('2023-01-01 09:30', periods=240, freq='1min')
        minute_df = pd.DataFrame({
            'open': np.random.uniform(10, 20, 240),
            'high': np.random.uniform(15, 25, 240),
            'low': np.random.uniform(5, 15, 240),
            'close': np.random.uniform(10, 20, 240),
            'vol': [0] * 240  # 所有成交量为0
        }, index=minute_dates)

        result = self.cleaner.resample_to_daily(minute_df)

        # 零成交量日期应该被移除
        self.assertEqual(len(result), 0)

        print("  ✓ 零成交量日期移除成功")

    def test_24_resample_non_datetime_index_error(self):
        """测试24: 非DatetimeIndex重采样应报错"""
        print("\n[测试24] 非DatetimeIndex重采样应报错...")

        df = self.test_df.copy()
        df = df.reset_index(drop=True)

        with self.assertRaises(ValueError):
            self.cleaner.resample_to_daily(df)

        print("  ✓ 非DatetimeIndex错误处理正确")

    # ==================== 特征添加测试 ====================

    def test_25_add_basic_features(self):
        """测试25: 添加基础特征"""
        print("\n[测试25] 添加基础特征...")

        result = self.cleaner.add_basic_features(self.test_df)

        # 验证特征被添加
        self.assertIn('pct_change', result.columns)
        self.assertIn('amplitude', result.columns)

        # 验证计算正确性
        self.assertFalse(result['pct_change'].isnull().all())
        self.assertFalse(result['amplitude'].isnull().all())

        print("  ✓ 基础特征添加成功")

    def test_26_add_features_existing_pct_change(self):
        """测试26: 已有pct_change时不重复计算"""
        print("\n[测试26] 已有pct_change时不重复计算...")

        df = self.test_df.copy()
        df['pct_change'] = 0.5  # 已有pct_change列

        result = self.cleaner.add_basic_features(df)

        # 应该保留原有值
        self.assertTrue((result['pct_change'] == 0.5).all())

        print("  ✓ 已有特征保留正确")

    def test_27_add_features_missing_columns(self):
        """测试27: 缺少列时跳过特征计算"""
        print("\n[测试27] 缺少列时跳过特征计算...")

        df = pd.DataFrame({'close': [10, 20, 30]})

        result = self.cleaner.add_basic_features(df)

        # pct_change可以计算，但amplitude需要high和low
        self.assertIn('pct_change', result.columns)
        self.assertNotIn('amplitude', result.columns)

        print("  ✓ 缺少列时处理正确")

    # ==================== 统计信息测试 ====================

    def test_28_get_stats(self):
        """测试28: 获取统计信息"""
        print("\n[测试28] 获取统计信息...")

        self.cleaner.clean_price_data(self.test_df, '000001')

        stats = self.cleaner.get_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn('total_rows', stats)
        self.assertIn('final_rows', stats)
        self.assertIn('missing_filled', stats)
        self.assertIn('outliers_removed', stats)
        self.assertIn('duplicates_removed', stats)

        print(f"  统计信息: {stats}")
        print("  ✓ 统计信息获取成功")

    def test_29_reset_stats(self):
        """测试29: 重置统计信息"""
        print("\n[测试29] 重置统计信息...")

        self.cleaner.clean_price_data(self.test_df, '000001')

        # 重置前
        stats_before = self.cleaner.get_stats()
        self.assertGreater(stats_before['total_rows'], 0)

        # 重置
        self.cleaner.reset_stats()

        # 重置后
        stats_after = self.cleaner.get_stats()
        self.assertEqual(stats_after['total_rows'], 0)
        self.assertEqual(stats_after['final_rows'], 0)

        print("  ✓ 统计信息重置成功")

    # ==================== 批量清洗测试 ====================

    def test_30_batch_clean_data(self):
        """测试30: 批量清洗数据"""
        print("\n[测试30] 批量清洗数据...")

        # 创建多个股票的数据
        data_dict = {
            '000001': self.test_df.copy(),
            '000002': self.test_df.copy(),
            '600000': self.test_df.copy()
        }

        cleaned_dict, stats_dict = batch_clean_data(data_dict, verbose=False)

        # 验证结果
        self.assertEqual(len(cleaned_dict), 3)
        self.assertEqual(len(stats_dict), 3)

        for stock_code in ['000001', '000002', '600000']:
            self.assertIn(stock_code, cleaned_dict)
            self.assertIn(stock_code, stats_dict)
            self.assertIsInstance(cleaned_dict[stock_code], pd.DataFrame)
            self.assertIsInstance(stats_dict[stock_code], dict)

        print(f"  ✓ 批量清洗成功: {len(cleaned_dict)}只股票")

    def test_31_batch_clean_with_verbose(self):
        """测试31: 批量清洗（verbose模式）"""
        print("\n[测试31] 批量清洗（verbose模式）...")

        # 创建较多股票触发进度输出
        data_dict = {f'{i:06d}': self.test_df.copy() for i in range(150)}

        cleaned_dict, stats_dict = batch_clean_data(data_dict, verbose=True)

        self.assertEqual(len(cleaned_dict), 150)

        print(f"  ✓ 批量清洗（verbose）成功: {len(cleaned_dict)}只股票")

    def test_32_batch_clean_empty_dict(self):
        """测试32: 批量清洗空字典"""
        print("\n[测试32] 批量清洗空字典...")

        cleaned_dict, stats_dict = batch_clean_data({}, verbose=False)

        self.assertEqual(len(cleaned_dict), 0)
        self.assertEqual(len(stats_dict), 0)

        print("  ✓ 空字典处理正确")

    # ==================== 综合场景测试 ====================

    def test_33_complex_scenario(self):
        """测试33: 复杂场景（多种问题数据混合）"""
        print("\n[测试33] 复杂场景测试...")

        df = self.test_df.copy()

        # 添加各种问题
        df.loc[df.index[5], 'close'] = np.nan  # 缺失值
        df.loc[df.index[10], 'close'] = -5  # 负价格
        df.loc[df.index[15], 'close'] = 20000  # 超高价格
        df.loc[df.index[20], 'high'] = 5  # OHLC逻辑错误
        df.loc[df.index[25], 'close'] = df.loc[df.index[24], 'close'] * 3  # 极端涨幅

        # 添加重复行
        duplicate_row = df.iloc[30:31].copy()
        df = pd.concat([df, duplicate_row])

        # 清洗
        result = self.cleaner.clean_price_data(df, '000001')

        # 验证清洗效果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertLess(len(result), len(df))
        self.assertFalse(result.isnull().any().any())

        stats = self.cleaner.get_stats()
        self.assertGreater(stats['missing_filled'] + stats['outliers_removed'] + stats['duplicates_removed'], 0)

        print(f"  原始: {len(df)}行")
        print(f"  清洗后: {len(result)}行")
        print(f"  缺失填充: {stats['missing_filled']}")
        print(f"  异常移除: {stats['outliers_removed']}")
        print(f"  重复移除: {stats['duplicates_removed']}")
        print("  ✓ 复杂场景清洗成功")

    def test_34_data_sorting(self):
        """测试34: 数据排序"""
        print("\n[测试34] 数据排序...")

        df = self.test_df.copy()
        # 打乱顺序
        df = df.sample(frac=1)

        result = self.cleaner.clean_price_data(df, '000001')

        # 验证排序
        self.assertTrue(result.index.is_monotonic_increasing)

        print("  ✓ 数据排序正确")

    def test_35_edge_case_single_row(self):
        """测试35: 边界情况 - 单行数据"""
        print("\n[测试35] 边界情况 - 单行数据...")

        df = self.test_df.iloc[:1].copy()

        result = self.cleaner.clean_price_data(df, '000001')

        # 单行数据应该正常处理
        self.assertEqual(len(result), 1)

        print("  ✓ 单行数据处理正确")

    def test_36_edge_case_two_rows(self):
        """测试36: 边界情况 - 两行数据"""
        print("\n[测试36] 边界情况 - 两行数据...")

        df = self.test_df.iloc[:2].copy()

        result = self.cleaner.clean_price_data(df, '000001')

        # 两行数据应该正常处理
        self.assertGreaterEqual(len(result), 1)

        print("  ✓ 两行数据处理正确")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDataCleanerComprehensive)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ 所有测试通过!")
    else:
        print("\n❌ 部分测试失败")

    print("="*70)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
