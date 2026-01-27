#!/usr/bin/env python3
"""
Stock Filter 完整单元测试
测试 src/data/stock_filter.py 模块的所有功能，提升覆盖率到90%+

包括:
- ST股票过滤
- 退市股票过滤
- 价格数据验证
- 停牌检测
- 筛选器组合逻辑
- 批量过滤
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

from src.data.stock_filter import StockFilter, filter_stocks_by_market


class TestStockFilterComprehensive(unittest.TestCase):
    """测试 StockFilter 类的完整功能"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*70)
        print("Stock Filter 完整单元测试 - 提升覆盖率")
        print("="*70)

    def setUp(self):
        """每个测试前的准备"""
        self.filter = StockFilter(verbose=False)

        # 创建测试股票列表
        self.test_stocks = pd.DataFrame({
            'symbol': ['000001', '000002', '000003', '600000', '600001', '300001', '300002'],
            'name': ['平安银行', '*ST万科', 'ST国华', '浦发银行', '邯郸钢铁', '特锐德', '神州泰岳'],
            'market': ['主板', '主板', '主板', '主板', '主板', '创业板', '创业板']
        })

        # 创建测试价格数据
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=300, freq='D')
        self.test_price_df = pd.DataFrame({
            'close': np.random.uniform(10, 20, 300),
            'vol': np.random.uniform(1000000, 10000000, 300)
        }, index=dates)

    # ==================== 初始化测试 ====================

    def test_01_init_verbose_false(self):
        """测试1: 初始化（verbose=False）"""
        print("\n[测试1] 初始化 verbose=False...")

        filter_obj = StockFilter(verbose=False)
        self.assertFalse(filter_obj.verbose)
        self.assertIsNotNone(filter_obj.filter_stats)
        self.assertEqual(filter_obj.filter_stats['total'], 0)

        print("  ✓ 初始化成功 (verbose=False)")

    def test_02_init_verbose_true(self):
        """测试2: 初始化（verbose=True）"""
        print("\n[测试2] 初始化 verbose=True...")

        filter_obj = StockFilter(verbose=True)
        self.assertTrue(filter_obj.verbose)

        print("  ✓ 初始化成功 (verbose=True)")

    # ==================== 股票列表过滤测试 ====================

    def test_03_filter_stock_list_st(self):
        """测试3: 过滤ST股票"""
        print("\n[测试3] 过滤ST股票...")

        result = self.filter.filter_stock_list(self.test_stocks)

        # 验证ST股票被过滤
        self.assertNotIn('*ST万科', result['name'].values)
        self.assertNotIn('ST国华', result['name'].values)

        # 验证统计信息
        stats = self.filter.get_stats()
        self.assertGreaterEqual(stats['st_filtered'], 2)

        print(f"  ✓ ST股票过滤成功 (过滤: {stats['st_filtered']})")

    def test_04_filter_stock_list_delisting(self):
        """测试4: 过滤退市股票"""
        print("\n[测试4] 过滤退市股票...")

        stocks = self.test_stocks.copy()
        stocks.loc[0, 'name'] = '退市大智'
        stocks.loc[1, 'name'] = '*退保千'

        result = self.filter.filter_stock_list(stocks)

        # 验证退市股票被过滤
        self.assertNotIn('退市大智', result['name'].values)
        self.assertNotIn('*退保千', result['name'].values)

        stats = self.filter.get_stats()
        self.assertGreaterEqual(stats['delisting_filtered'], 2)

        print(f"  ✓ 退市股票过滤成功 (过滤: {stats['delisting_filtered']})")

    def test_05_filter_stock_list_normal(self):
        """测试5: 正常股票通过过滤"""
        print("\n[测试5] 正常股票通过过滤...")

        result = self.filter.filter_stock_list(self.test_stocks)

        # 验证正常股票保留
        self.assertIn('平安银行', result['name'].values)
        self.assertIn('浦发银行', result['name'].values)

        print(f"  ✓ 正常股票保留成功 (通过: {len(result)})")

    def test_06_filter_stock_list_missing_name_column(self):
        """测试6: 缺少name列时抛出异常"""
        print("\n[测试6] 缺少name列时抛出异常...")

        stocks = pd.DataFrame({'symbol': ['000001']})

        with self.assertRaises(ValueError):
            self.filter.filter_stock_list(stocks)

        print("  ✓ 缺少name列错误处理正确")

    def test_07_filter_stock_list_verbose(self):
        """测试7: verbose模式过滤股票列表"""
        print("\n[测试7] verbose模式过滤股票列表...")

        filter_verbose = StockFilter(verbose=True)
        result = filter_verbose.filter_stock_list(self.test_stocks)

        self.assertIsInstance(result, pd.DataFrame)

        print("  ✓ verbose模式正常工作")

    # ==================== 价格数据过滤测试 ====================

    def test_08_filter_price_data_normal(self):
        """测试8: 正常价格数据通过"""
        print("\n[测试8] 正常价格数据通过...")

        passed, cleaned_df, reason = self.filter.filter_price_data(
            self.test_price_df,
            '000001',
            min_trading_days=250
        )

        self.assertTrue(passed)
        self.assertIsNotNone(cleaned_df)
        self.assertEqual(reason, "通过")

        print(f"  ✓ 正常数据通过 (数据点: {len(cleaned_df)})")

    def test_09_filter_price_data_empty(self):
        """测试9: 空数据被过滤"""
        print("\n[测试9] 空数据被过滤...")

        empty_df = pd.DataFrame()

        passed, cleaned_df, reason = self.filter.filter_price_data(
            empty_df,
            '000001'
        )

        self.assertFalse(passed)
        self.assertIsNone(cleaned_df)
        self.assertEqual(reason, "数据为空")

        print("  ✓ 空数据过滤正确")

    def test_10_filter_price_data_none(self):
        """测试10: None数据被过滤"""
        print("\n[测试10] None数据被过滤...")

        passed, cleaned_df, reason = self.filter.filter_price_data(
            None,
            '000001'
        )

        self.assertFalse(passed)
        self.assertIsNone(cleaned_df)
        self.assertEqual(reason, "数据为空")

        print("  ✓ None数据过滤正确")

    def test_11_filter_price_data_insufficient_days(self):
        """测试11: 交易天数不足被过滤"""
        print("\n[测试11] 交易天数不足被过滤...")

        # 只有100天数据
        short_df = self.test_price_df.iloc[:100].copy()

        passed, cleaned_df, reason = self.filter.filter_price_data(
            short_df,
            '000001',
            min_trading_days=250
        )

        self.assertFalse(passed)
        self.assertIsNone(cleaned_df)
        self.assertIn("交易天数不足", reason)

        stats = self.filter.get_stats()
        self.assertGreater(stats['insufficient_data_filtered'], 0)

        print(f"  ✓ 交易天数不足过滤正确 (原因: {reason})")

    def test_12_filter_price_data_invalid_price(self):
        """测试12: 无效价格被过滤"""
        print("\n[测试12] 无效价格被过滤...")

        df = self.test_price_df.copy()
        # 添加无效价格
        df.loc[df.index[10], 'close'] = -5
        df.loc[df.index[20], 'close'] = 20000

        passed, cleaned_df, reason = self.filter.filter_price_data(
            df,
            '000001'
        )

        self.assertFalse(passed)
        self.assertIsNone(cleaned_df)
        self.assertEqual(reason, "价格数据异常")

        stats = self.filter.get_stats()
        self.assertGreater(stats['abnormal_price_filtered'], 0)

        print(f"  ✓ 无效价格过滤正确 (原因: {reason})")

    def test_13_filter_price_data_consecutive_zero_volume(self):
        """测试13: 连续停牌被过滤"""
        print("\n[测试13] 连续停牌被过滤...")

        df = self.test_price_df.copy()
        # 添加连续5天以上的零成交量
        df.loc[df.index[10:20], 'vol'] = 0

        passed, cleaned_df, reason = self.filter.filter_price_data(
            df,
            '000001'
        )

        self.assertFalse(passed)
        self.assertIsNone(cleaned_df)
        self.assertIn("停牌", reason)

        stats = self.filter.get_stats()
        self.assertGreater(stats['suspended_filtered'], 0)

        print(f"  ✓ 连续停牌过滤正确 (原因: {reason})")

    def test_14_filter_price_data_remove_suspended_days(self):
        """测试14: 移除停牌日后数据充足"""
        print("\n[测试14] 移除停牌日后数据充足...")

        df = self.test_price_df.copy()
        # 添加少量停牌日（不连续）
        df.loc[df.index[10], 'vol'] = 0
        df.loc[df.index[20], 'vol'] = 0
        df.loc[df.index[30], 'vol'] = 0

        passed, cleaned_df, reason = self.filter.filter_price_data(
            df,
            '000001',
            min_trading_days=250
        )

        # 移除停牌日后仍有足够数据
        self.assertTrue(passed)
        self.assertIsNotNone(cleaned_df)

        # 验证停牌日被移除
        self.assertTrue((cleaned_df['vol'] > 0).all())

        print(f"  ✓ 停牌日移除成功 (剩余: {len(cleaned_df)}天)")

    def test_15_filter_price_data_after_cleaning_insufficient(self):
        """测试15: 清洗后数据不足被过滤"""
        print("\n[测试15] 清洗后数据不足被过滤...")

        df = self.test_price_df.copy()
        # 大量停牌日，清洗后数据不足
        df.loc[df.index[100:], 'vol'] = 0

        passed, cleaned_df, reason = self.filter.filter_price_data(
            df,
            '000001',
            min_trading_days=250
        )

        self.assertFalse(passed)
        self.assertIsNone(cleaned_df)
        # 可能是连续停牌或者清洗后数据不足
        self.assertTrue("停牌" in reason or "数据不足" in reason)

        print(f"  ✓ 清洗后数据不足过滤正确 (原因: {reason})")

    def test_16_filter_price_data_no_volume_column(self):
        """测试16: 无成交量列时正常处理"""
        print("\n[测试16] 无成交量列时正常处理...")

        df = self.test_price_df.drop('vol', axis=1)

        passed, cleaned_df, reason = self.filter.filter_price_data(
            df,
            '000001',
            min_trading_days=250
        )

        # 无成交量列时跳过停牌检测
        self.assertTrue(passed)

        print("  ✓ 无成交量列处理正确")

    # ==================== 批量过滤测试 ====================

    def test_17_batch_filter_stocks_normal(self):
        """测试17: 批量过滤股票"""
        print("\n[测试17] 批量过滤股票...")

        stock_list = ['000001', '000002', '000003']
        price_data_dict = {
            '000001': self.test_price_df.copy(),
            '000002': self.test_price_df.copy(),
            '000003': self.test_price_df.iloc[:100].copy()  # 数据不足
        }

        passed_stocks, filter_reasons = self.filter.batch_filter_stocks(
            stock_list,
            price_data_dict,
            min_trading_days=250
        )

        # 验证结果
        self.assertIn('000001', passed_stocks)
        self.assertIn('000002', passed_stocks)
        self.assertNotIn('000003', passed_stocks)

        self.assertIn('000003', filter_reasons)

        print(f"  ✓ 批量过滤成功 (通过: {len(passed_stocks)}, 过滤: {len(filter_reasons)})")

    def test_18_batch_filter_stocks_with_verbose(self):
        """测试18: 批量过滤（verbose模式）"""
        print("\n[测试18] 批量过滤（verbose模式）...")

        filter_verbose = StockFilter(verbose=True)

        stock_list = ['000001', '000002']
        price_data_dict = {
            '000001': self.test_price_df.copy(),
            '000002': self.test_price_df.copy()
        }

        passed_stocks, filter_reasons = filter_verbose.batch_filter_stocks(
            stock_list,
            price_data_dict
        )

        self.assertEqual(len(passed_stocks), 2)

        print("  ✓ verbose模式批量过滤正常")

    def test_19_batch_filter_stocks_missing_data(self):
        """测试19: 批量过滤时缺少数据"""
        print("\n[测试19] 批量过滤时缺少数据...")

        stock_list = ['000001', '000002', '000003']
        price_data_dict = {
            '000001': self.test_price_df.copy(),
            # 000002和000003的数据缺失
        }

        passed_stocks, filter_reasons = self.filter.batch_filter_stocks(
            stock_list,
            price_data_dict
        )

        # 只有000001有数据且通过
        self.assertIn('000001', passed_stocks)
        self.assertIn('000002', filter_reasons)
        self.assertIn('000003', filter_reasons)

        print(f"  ✓ 缺少数据处理正确 (通过: {len(passed_stocks)})")

    def test_20_batch_filter_update_cleaned_data(self):
        """测试20: 批量过滤更新清洗后的数据"""
        print("\n[测试20] 批量过滤更新清洗后的数据...")

        stock_list = ['000001']
        df = self.test_price_df.copy()
        # 添加停牌日
        df.loc[df.index[10], 'vol'] = 0

        price_data_dict = {'000001': df}

        passed_stocks, filter_reasons = self.filter.batch_filter_stocks(
            stock_list,
            price_data_dict
        )

        # 验证数据被更新为清洗后的版本
        cleaned_df = price_data_dict['000001']
        self.assertTrue((cleaned_df['vol'] > 0).all())

        print("  ✓ 清洗后数据更新正确")

    # ==================== 辅助方法测试 ====================

    def test_21_check_consecutive_days_true(self):
        """测试21: 检测到连续天数"""
        print("\n[测试21] 检测到连续天数...")

        series = pd.Series([False, False, True, True, True, True, True, False])

        result = self.filter._check_consecutive_days(series, 5)

        self.assertTrue(result)

        print("  ✓ 连续天数检测正确 (检测到)")

    def test_22_check_consecutive_days_false(self):
        """测试22: 未检测到连续天数"""
        print("\n[测试22] 未检测到连续天数...")

        series = pd.Series([False, True, False, True, False, True])

        result = self.filter._check_consecutive_days(series, 5)

        self.assertFalse(result)

        print("  ✓ 连续天数检测正确 (未检测到)")

    # ==================== 市场过滤测试 ====================

    def test_23_filter_stocks_by_market_main(self):
        """测试23: 按市场过滤（仅主板）"""
        print("\n[测试23] 按市场过滤（仅主板）...")

        result = filter_stocks_by_market(
            self.test_stocks,
            markets=['main']
        )

        # 验证只保留主板股票
        self.assertTrue(all(result['market'] == '主板'))

        print(f"  ✓ 主板过滤成功 (保留: {len(result)})")

    def test_24_filter_stocks_by_market_multiple(self):
        """测试24: 按市场过滤（多个市场）"""
        print("\n[测试24] 按市场过滤（多个市场）...")

        result = filter_stocks_by_market(
            self.test_stocks,
            markets=['main', 'gem']
        )

        # 验证保留主板和创业板
        self.assertTrue(all(m in ['主板', '创业板'] for m in result['market']))

        print(f"  ✓ 多市场过滤成功 (保留: {len(result)})")

    def test_25_filter_stocks_by_market_no_market_column(self):
        """测试25: 无market列时返回原数据"""
        print("\n[测试25] 无market列时返回原数据...")

        stocks = self.test_stocks.drop('market', axis=1)

        result = filter_stocks_by_market(stocks, markets=['main'])

        # 无market列时应该返回原数据
        self.assertEqual(len(result), len(stocks))

        print("  ✓ 无market列处理正确")

    # ==================== 统计信息测试 ====================

    def test_26_get_stats(self):
        """测试26: 获取统计信息"""
        print("\n[测试26] 获取统计信息...")

        self.filter.filter_stock_list(self.test_stocks)

        stats = self.filter.get_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn('total', stats)
        self.assertIn('st_filtered', stats)
        self.assertIn('passed', stats)

        print(f"  统计信息: {stats}")
        print("  ✓ 统计信息获取成功")

    def test_27_reset_stats(self):
        """测试27: 重置统计信息"""
        print("\n[测试27] 重置统计信息...")

        self.filter.filter_stock_list(self.test_stocks)

        # 重置
        self.filter.reset_stats()

        # 重置后
        stats_after = self.filter.get_stats()
        self.assertEqual(stats_after['total'], 0)

        print("  ✓ 统计信息重置成功")

    # ==================== 综合场景测试 ====================

    def test_28_complex_filter_scenario(self):
        """测试28: 复杂过滤场景"""
        print("\n[测试28] 复杂过滤场景...")

        stocks = pd.DataFrame({
            'symbol': ['000001', '000002', '000003', '000004', '000005'],
            'name': ['平安银行', '*ST万科', '退市大智', '特锐德', '神州泰岳'],
            'market': ['主板', '主板', '主板', '创业板', '创业板']
        })

        filtered_stocks = self.filter.filter_stock_list(stocks)

        # 只有平安银行、特锐德、神州泰岳应该通过
        self.assertEqual(len(filtered_stocks), 3)

        stats = self.filter.get_stats()
        self.assertGreater(stats['st_filtered'] + stats['delisting_filtered'], 0)

        print(f"  原始: {len(stocks)}, 通过: {len(filtered_stocks)}")
        print("  ✓ 复杂场景过滤成功")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStockFilterComprehensive)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

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
