#!/usr/bin/env python3
"""
AkShareDataConverter 完整单元测试

覆盖所有转换方法、边界条件和异常情况
目标覆盖率: >95%
"""

import sys
import unittest
from datetime import datetime, date
from pathlib import Path
import pandas as pd
import numpy as np

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from src.providers.akshare.data_converter import AkShareDataConverter


class TestAkShareDataConverterBasic(unittest.TestCase):
    """基础功能测试"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("AkShareDataConverter 完整单元测试")
        print("="*60)
        cls.converter = AkShareDataConverter()

    def test_01_init(self):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")
        converter = AkShareDataConverter()
        self.assertIsInstance(converter, AkShareDataConverter)
        print("  ✓ 初始化成功")

    def test_02_repr(self):
        """测试2: __repr__ 方法"""
        print("\n[测试2] __repr__ 方法...")
        converter = AkShareDataConverter()
        repr_str = repr(converter)
        self.assertEqual(repr_str, "<AkShareDataConverter>")
        print(f"  ✓ repr: {repr_str}")


class TestSafeConversions(unittest.TestCase):
    """安全转换方法测试"""

    @classmethod
    def setUpClass(cls):
        cls.converter = AkShareDataConverter()

    def test_safe_float_normal(self):
        """测试 safe_float: 正常值"""
        print("\n[测试] safe_float 正常值...")

        # 正常数字
        self.assertEqual(self.converter.safe_float(123.45), 123.45)
        self.assertEqual(self.converter.safe_float("123.45"), 123.45)
        self.assertEqual(self.converter.safe_float("123"), 123.0)

        # 带逗号的数字
        self.assertEqual(self.converter.safe_float("1,234.56"), 1234.56)

        # 百分比
        self.assertEqual(self.converter.safe_float("12.5%"), 12.5)

        print("  ✓ 正常值转换成功")

    def test_safe_float_empty_values(self):
        """测试 safe_float: 空值"""
        print("\n[测试] safe_float 空值...")

        # None
        self.assertIsNone(self.converter.safe_float(None))
        self.assertEqual(self.converter.safe_float(None, default=0.0), 0.0)

        # 空字符串
        self.assertIsNone(self.converter.safe_float(''))
        self.assertEqual(self.converter.safe_float('', default=0.0), 0.0)

        # 横杠
        self.assertIsNone(self.converter.safe_float('-'))
        self.assertEqual(self.converter.safe_float('-', default=0.0), 0.0)

        print("  ✓ 空值处理正确")

    def test_safe_float_invalid_values(self):
        """测试 safe_float: 无效值"""
        print("\n[测试] safe_float 无效值...")

        # 无效字符串
        self.assertIsNone(self.converter.safe_float('abc'))
        self.assertEqual(self.converter.safe_float('abc', default=0.0), 0.0)

        # 无效类型
        self.assertEqual(self.converter.safe_float([], default=0.0), 0.0)
        self.assertEqual(self.converter.safe_float({}, default=0.0), 0.0)

        print("  ✓ 无效值处理正确")

    def test_safe_int_normal(self):
        """测试 safe_int: 正常值"""
        print("\n[测试] safe_int 正常值...")

        # 整数
        self.assertEqual(self.converter.safe_int(123), 123)
        self.assertEqual(self.converter.safe_int("123"), 123)

        # 浮点数（会转换）
        self.assertEqual(self.converter.safe_int(123.45), 123)
        self.assertEqual(self.converter.safe_int("123.45"), 123)

        # 带逗号
        self.assertEqual(self.converter.safe_int("1,234"), 1234)

        print("  ✓ 正常值转换成功")

    def test_safe_int_empty_values(self):
        """测试 safe_int: 空值"""
        print("\n[测试] safe_int 空值...")

        self.assertIsNone(self.converter.safe_int(None))
        self.assertEqual(self.converter.safe_int(None, default=0), 0)
        self.assertIsNone(self.converter.safe_int(''))
        self.assertIsNone(self.converter.safe_int('-'))

        print("  ✓ 空值处理正确")

    def test_safe_int_invalid_values(self):
        """测试 safe_int: 无效值"""
        print("\n[测试] safe_int 无效值...")

        self.assertIsNone(self.converter.safe_int('abc'))
        self.assertEqual(self.converter.safe_int('abc', default=0), 0)
        self.assertEqual(self.converter.safe_int([], default=0), 0)

        print("  ✓ 无效值处理正确")


class TestStockListConversion(unittest.TestCase):
    """股票列表转换测试"""

    @classmethod
    def setUpClass(cls):
        cls.converter = AkShareDataConverter()

    def test_convert_stock_list_normal(self):
        """测试股票列表转换: 正常数据"""
        print("\n[测试] 股票列表转换: 正常数据...")

        # 构造测试数据（使用 AkShare API 返回的字段名）
        df = pd.DataFrame({
            'code': ['000001', '600000', '000002'],
            'name': ['平安银行', '浦发银行', '万科A']
        })

        result = self.converter.convert_stock_list(df)

        # 验证
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)
        self.assertIn('market', result.columns)
        self.assertIn('status', result.columns)

        # 验证市场字段
        self.assertIn(result.iloc[0]['market'], ['深圳主板', '上海主板'])

        # 验证状态字段
        self.assertTrue(all(result['status'] == '正常'))

        print(f"  ✓ 成功转换 {len(result)} 只股票")

    def test_convert_stock_list_empty(self):
        """测试股票列表转换: 空数据"""
        print("\n[测试] 股票列表转换: 空数据...")

        # None
        result = self.converter.convert_stock_list(None)
        self.assertTrue(result.empty)

        # 空 DataFrame
        result = self.converter.convert_stock_list(pd.DataFrame())
        self.assertTrue(result.empty)

        print("  ✓ 空数据处理正确")


class TestDailyDataConversion(unittest.TestCase):
    """日线数据转换测试"""

    @classmethod
    def setUpClass(cls):
        cls.converter = AkShareDataConverter()

    def test_convert_daily_data_normal(self):
        """测试日线数据转换: 正常数据"""
        print("\n[测试] 日线数据转换: 正常数据...")

        df = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02', '2024-01-03'],
            '开盘': ['10.00', '10.20', '10.50'],
            '收盘': ['10.20', '10.50', '10.80'],
            '最高': ['10.50', '10.80', '11.00'],
            '最低': ['9.80', '10.00', '10.30'],
            '成交量': ['1000000', '1200000', '1500000'],
            '成交额': ['10200000', '12600000', '16200000'],
            '振幅': ['7.0', '7.8', '6.7'],
            '涨跌幅': ['2.0', '2.9', '2.9'],
            '涨跌额': ['0.20', '0.30', '0.30'],
            '换手率': ['0.5', '0.6', '0.8']
        })

        result = self.converter.convert_daily_data(df)

        # 验证
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertIn('trade_date', result.columns)
        self.assertIn('open', result.columns)
        self.assertIn('close', result.columns)

        # 验证日期类型
        self.assertIsInstance(result['trade_date'].iloc[0], date)

        # 验证数值类型
        self.assertTrue(pd.api.types.is_numeric_dtype(result['open']))
        self.assertTrue(pd.api.types.is_numeric_dtype(result['close']))

        print(f"  ✓ 成功转换 {len(result)} 条日线数据")

    def test_convert_daily_data_with_string_numbers(self):
        """测试日线数据转换: 字符串数字"""
        print("\n[测试] 日线数据转换: 字符串数字...")

        df = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': ['10.00'],
            '收盘': ['10.20'],
            '最高': ['10.50'],
            '最低': ['9.80'],
            '成交量': ['1000000'],  # pandas to_numeric 不自动处理逗号
            '成交额': ['10200000']
        })

        result = self.converter.convert_daily_data(df)

        # 验证数值转换
        self.assertEqual(result['open'].iloc[0], 10.00)
        self.assertEqual(result['volume'].iloc[0], 1000000)

        print("  ✓ 字符串数字转换正确")

    def test_convert_daily_data_with_invalid_numbers(self):
        """测试日线数据转换: 无效数字"""
        print("\n[测试] 日线数据转换: 无效数字...")

        df = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': ['-'],  # 无效值
            '收盘': ['abc'],  # 无效值
            '最高': ['10.50'],
            '最低': ['9.80'],
            '成交量': [''],  # 空值
            '成交额': ['10200000']
        })

        result = self.converter.convert_daily_data(df)

        # 验证无效值被转换为 NaN
        self.assertTrue(pd.isna(result['open'].iloc[0]))
        self.assertTrue(pd.isna(result['close'].iloc[0]))
        self.assertTrue(pd.isna(result['volume'].iloc[0]))

        print("  ✓ 无效数字处理正确")

    def test_convert_daily_data_empty(self):
        """测试日线数据转换: 空数据"""
        print("\n[测试] 日线数据转换: 空数据...")

        result = self.converter.convert_daily_data(None)
        self.assertTrue(result.empty)

        result = self.converter.convert_daily_data(pd.DataFrame())
        self.assertTrue(result.empty)

        print("  ✓ 空数据处理正确")


class TestMinuteDataConversion(unittest.TestCase):
    """分时数据转换测试"""

    @classmethod
    def setUpClass(cls):
        cls.converter = AkShareDataConverter()

    def test_convert_minute_data_normal(self):
        """测试分时数据转换: 正常数据"""
        print("\n[测试] 分时数据转换: 正常数据...")

        df = pd.DataFrame({
            '时间': ['2024-01-01 09:35:00', '2024-01-01 09:40:00'],
            '开盘': [10.00, 10.20],
            '收盘': [10.20, 10.50],
            '最高': [10.50, 10.80],
            '最低': [9.80, 10.00],
            '成交量': [100000, 120000],
            '成交额': [1020000, 1260000]
        })

        result = self.converter.convert_minute_data(df, period='5')

        # 验证
        self.assertEqual(len(result), 2)
        self.assertIn('trade_time', result.columns)
        self.assertIn('period', result.columns)

        # 验证周期字段
        self.assertTrue(all(result['period'] == '5'))

        # 验证时间类型
        self.assertIsInstance(result['trade_time'].iloc[0], pd.Timestamp)

        print(f"  ✓ 成功转换 {len(result)} 条分时数据")

    def test_convert_minute_data_different_periods(self):
        """测试分时数据转换: 不同周期"""
        print("\n[测试] 分时数据转换: 不同周期...")

        df = pd.DataFrame({
            '时间': ['2024-01-01 09:35:00'],
            '开盘': [10.00],
            '收盘': [10.20],
            '最高': [10.50],
            '最低': [9.80],
            '成交量': [100000],
            '成交额': [1020000]
        })

        for period in ['1', '5', '15', '30', '60']:
            result = self.converter.convert_minute_data(df, period=period)
            self.assertEqual(result['period'].iloc[0], period)

        print("  ✓ 不同周期处理正确")

    def test_convert_minute_data_empty(self):
        """测试分时数据转换: 空数据"""
        print("\n[测试] 分时数据转换: 空数据...")

        result = self.converter.convert_minute_data(None, period='5')
        self.assertTrue(result.empty)

        result = self.converter.convert_minute_data(pd.DataFrame(), period='5')
        self.assertTrue(result.empty)

        print("  ✓ 空数据处理正确")


class TestRealtimeQuotesConversion(unittest.TestCase):
    """实时行情转换测试"""

    @classmethod
    def setUpClass(cls):
        cls.converter = AkShareDataConverter()

    def test_convert_realtime_quotes_normal(self):
        """测试实时行情转换: 正常数据"""
        print("\n[测试] 实时行情转换: 正常数据...")

        df = pd.DataFrame({
            '代码': ['000001', '600000'],
            '名称': ['平安银行', '浦发银行'],
            '最新价': [10.20, 8.50],
            '涨跌幅': [2.0, -1.5],
            '涨跌额': [0.20, -0.13],
            '成交量': [1000000, 800000],
            '成交额': [10200000, 6800000],
            '振幅': [5.0, 3.5],
            '最高': [10.50, 8.70],
            '最低': [9.80, 8.40],
            '今开': [10.00, 8.60],
            '昨收': [10.00, 8.63]
        })

        result = self.converter.convert_realtime_quotes(df)

        # 验证
        self.assertEqual(len(result), 2)
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)
        self.assertIn('trade_time', result.columns)

        # 验证时间字段
        self.assertIsInstance(result['trade_time'].iloc[0], datetime)

        print(f"  ✓ 成功转换 {len(result)} 条实时行情")

    def test_convert_realtime_quote_single(self):
        """测试单个实时行情转换"""
        print("\n[测试] 单个实时行情转换...")

        quote = {
            'code': '000001',
            'name': '平安银行',
            'latest_price': 10.20
        }

        result = self.converter.convert_realtime_quote_single(quote)

        # 当前实现直接返回，不做转换
        self.assertEqual(result, quote)

        print("  ✓ 单个行情转换正确")

    def test_convert_realtime_quotes_empty(self):
        """测试实时行情转换: 空数据"""
        print("\n[测试] 实时行情转换: 空数据...")

        result = self.converter.convert_realtime_quotes(None)
        self.assertTrue(result.empty)

        result = self.converter.convert_realtime_quotes(pd.DataFrame())
        self.assertTrue(result.empty)

        print("  ✓ 空数据处理正确")


class TestNewStocksConversion(unittest.TestCase):
    """新股列表转换测试"""

    @classmethod
    def setUpClass(cls):
        cls.converter = AkShareDataConverter()

    def test_convert_new_stocks_normal(self):
        """测试新股列表转换: 正常数据"""
        print("\n[测试] 新股列表转换: 正常数据...")

        df = pd.DataFrame({
            '代码': ['301234', '688123'],
            '名称': ['测试股票A', '测试股票B'],
            '上市日期': ['2024-01-01', '2024-01-02']
        })

        result = self.converter.convert_new_stocks(df)

        # 验证
        self.assertEqual(len(result), 2)
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)
        self.assertIn('list_date', result.columns)
        self.assertIn('market', result.columns)
        self.assertIn('status', result.columns)

        # 验证日期类型
        self.assertIsInstance(result['list_date'].iloc[0], date)

        # 验证状态
        self.assertTrue(all(result['status'] == '正常'))

        print(f"  ✓ 成功转换 {len(result)} 只新股")

    def test_convert_new_stocks_invalid_date(self):
        """测试新股列表转换: 无效日期"""
        print("\n[测试] 新股列表转换: 无效日期...")

        df = pd.DataFrame({
            '代码': ['301234'],
            '名称': ['测试股票'],
            '上市日期': ['invalid-date']
        })

        result = self.converter.convert_new_stocks(df)

        # 验证无效日期被转换为 NaT
        self.assertTrue(pd.isna(result['list_date'].iloc[0]))

        print("  ✓ 无效日期处理正确")

    def test_convert_new_stocks_empty(self):
        """测试新股列表转换: 空数据"""
        print("\n[测试] 新股列表转换: 空数据...")

        result = self.converter.convert_new_stocks(None)
        self.assertTrue(result.empty)

        result = self.converter.convert_new_stocks(pd.DataFrame())
        self.assertTrue(result.empty)

        print("  ✓ 空数据处理正确")


class TestDelistedStocksConversion(unittest.TestCase):
    """退市股票转换测试"""

    @classmethod
    def setUpClass(cls):
        cls.converter = AkShareDataConverter()

    def test_convert_delisted_stocks_sh(self):
        """测试退市股票转换: 上交所"""
        print("\n[测试] 退市股票转换: 上交所...")

        df = pd.DataFrame({
            '公司代码': ['600001'],
            '公司简称': ['退市股A'],
            '上市日期': ['2010-01-01'],
            '暂停上市日期': ['2023-12-31']
        })

        result = self.converter.convert_delisted_stocks(df, exchange='SH')

        # 验证
        self.assertEqual(len(result), 1)
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)
        self.assertIn('list_date', result.columns)
        self.assertIn('delist_date', result.columns)

        # 验证日期类型
        self.assertIsInstance(result['list_date'].iloc[0], date)
        self.assertIsInstance(result['delist_date'].iloc[0], date)

        print(f"  ✓ 成功转换 {len(result)} 只上交所退市股票")

    def test_convert_delisted_stocks_sz(self):
        """测试退市股票转换: 深交所"""
        print("\n[测试] 退市股票转换: 深交所...")

        df = pd.DataFrame({
            '公司代码': ['000001'],
            '公司简称': ['退市股B'],
            '上市日期': ['2010-01-01'],
            '终止上市日期': ['2023-12-31']
        })

        result = self.converter.convert_delisted_stocks(df, exchange='SZ')

        # 验证
        self.assertEqual(len(result), 1)
        self.assertIn('code', result.columns)
        self.assertIn('delist_date', result.columns)

        print(f"  ✓ 成功转换 {len(result)} 只深交所退市股票")

    def test_convert_delisted_stocks_auto_detect(self):
        """测试退市股票转换: 自动检测交易所"""
        print("\n[测试] 退市股票转换: 自动检测...")

        # 上交所格式
        df_sh = pd.DataFrame({
            '公司代码': ['600001'],
            '公司简称': ['退市股A'],
            '上市日期': ['2010-01-01'],
            '暂停上市日期': ['2023-12-31']
        })

        result_sh = self.converter.convert_delisted_stocks(df_sh)
        self.assertEqual(len(result_sh), 1)

        # 深交所格式
        df_sz = pd.DataFrame({
            '公司代码': ['000001'],
            '公司简称': ['退市股B'],
            '上市日期': ['2010-01-01'],
            '终止上市日期': ['2023-12-31']
        })

        result_sz = self.converter.convert_delisted_stocks(df_sz)
        self.assertEqual(len(result_sz), 1)

        print("  ✓ 自动检测交易所正确")

    def test_convert_delisted_stocks_empty(self):
        """测试退市股票转换: 空数据"""
        print("\n[测试] 退市股票转换: 空数据...")

        result = self.converter.convert_delisted_stocks(None)
        self.assertTrue(result.empty)

        result = self.converter.convert_delisted_stocks(pd.DataFrame())
        self.assertTrue(result.empty)

        print("  ✓ 空数据处理正确")


class TestEdgeCases(unittest.TestCase):
    """边界条件测试"""

    @classmethod
    def setUpClass(cls):
        cls.converter = AkShareDataConverter()

    def test_large_dataset(self):
        """测试大数据集"""
        print("\n[测试] 大数据集...")

        # 创建5000条数据（使用 AkShare API 返回的字段名）
        df = pd.DataFrame({
            'code': [f'{i:06d}' for i in range(5000)],
            'name': [f'股票{i}' for i in range(5000)]
        })

        result = self.converter.convert_stock_list(df)

        self.assertEqual(len(result), 5000)
        print(f"  ✓ 成功处理 {len(result)} 条数据")

    def test_special_characters_in_name(self):
        """测试特殊字符"""
        print("\n[测试] 特殊字符...")

        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['测试*ST股票A(退)']
        })

        result = self.converter.convert_stock_list(df)

        self.assertEqual(result['name'].iloc[0], '测试*ST股票A(退)')
        print("  ✓ 特殊字符处理正确")

    def test_extreme_numbers(self):
        """测试极端数值"""
        print("\n[测试] 极端数值...")

        # 非常大的数
        self.assertEqual(
            self.converter.safe_float('999999999999.99'),
            999999999999.99
        )

        # 非常小的数
        self.assertEqual(
            self.converter.safe_float('0.00000001'),
            0.00000001
        )

        # 负数
        self.assertEqual(
            self.converter.safe_float('-123.45'),
            -123.45
        )

        print("  ✓ 极端数值处理正确")

    def test_unicode_characters(self):
        """测试 Unicode 字符"""
        print("\n[测试] Unicode 字符...")

        df = pd.DataFrame({
            'code': ['000001'],
            'name': ['测试股票🚀']
        })

        result = self.converter.convert_stock_list(df)

        self.assertEqual(result['name'].iloc[0], '测试股票🚀')
        print("  ✓ Unicode 字符处理正确")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestAkShareDataConverterBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestSafeConversions))
    suite.addTests(loader.loadTestsFromTestCase(TestStockListConversion))
    suite.addTests(loader.loadTestsFromTestCase(TestDailyDataConversion))
    suite.addTests(loader.loadTestsFromTestCase(TestMinuteDataConversion))
    suite.addTests(loader.loadTestsFromTestCase(TestRealtimeQuotesConversion))
    suite.addTests(loader.loadTestsFromTestCase(TestNewStocksConversion))
    suite.addTests(loader.loadTestsFromTestCase(TestDelistedStocksConversion))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 统计信息
    print("\n" + "="*60)
    print(f"测试总数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("="*60)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
