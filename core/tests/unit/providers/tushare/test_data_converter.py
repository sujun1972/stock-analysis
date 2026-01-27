#!/usr/bin/env python3
"""
TushareDataConverter 单元测试

测试数据转换器的功能：
- 股票代码格式转换
- 股票列表数据转换
- 日线数据转换
- 分钟数据转换
- 实时行情转换
- 新股数据转换
- 退市股票转换
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

from providers.tushare.data_converter import TushareDataConverter


class TestTushareDataConverter(unittest.TestCase):
    """测试 TushareDataConverter 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("TushareDataConverter 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        self.converter = TushareDataConverter()

    # ========== 代码转换测试 ==========

    def test_01_to_ts_code_sz(self):
        """测试1: 转换深圳股票代码"""
        print("\n[测试1] 转换深圳股票代码...")

        result = self.converter.to_ts_code('000001')
        self.assertEqual(result, '000001.SZ')

        result = self.converter.to_ts_code('300001')
        self.assertEqual(result, '300001.SZ')

        print("  ✓ 深圳股票代码转换正确")

    def test_02_to_ts_code_sh(self):
        """测试2: 转换上海股票代码"""
        print("\n[测试2] 转换上海股票代码...")

        result = self.converter.to_ts_code('600000')
        self.assertEqual(result, '600000.SH')

        result = self.converter.to_ts_code('688001')
        self.assertEqual(result, '688001.SH')

        print("  ✓ 上海股票代码转换正确")

    def test_03_to_ts_code_already_formatted(self):
        """测试3: 已格式化的代码不再转换"""
        print("\n[测试3] 已格式化的代码不再转换...")

        result = self.converter.to_ts_code('000001.SZ')
        self.assertEqual(result, '000001.SZ')

        result = self.converter.to_ts_code('600000.SH')
        self.assertEqual(result, '600000.SH')

        print("  ✓ 已格式化代码保持不变")

    def test_04_from_ts_code(self):
        """测试4: 从 Tushare 格式提取代码"""
        print("\n[测试4] 从 Tushare 格式提取代码...")

        result = self.converter.from_ts_code('000001.SZ')
        self.assertEqual(result, '000001')

        result = self.converter.from_ts_code('600000.SH')
        self.assertEqual(result, '600000')

        result = self.converter.from_ts_code('000001')
        self.assertEqual(result, '000001')

        print("  ✓ 代码提取正确")

    # ========== 股票列表转换测试 ==========

    def test_05_convert_stock_list(self):
        """测试5: 转换股票列表"""
        print("\n[测试5] 转换股票列表...")

        # 模拟 Tushare 返回的数据
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '600000.SH', '300001.SZ'],
            'symbol': ['000001', '600000', '300001'],
            'name': ['平安银行', '浦发银行', '特锐德'],
            'area': ['深圳', '上海', '青岛'],
            'industry': ['银行', '银行', '电气设备'],
            'market': ['主板', '主板', '创业板'],
            'list_date': ['19910403', '19991110', '20100126']
        })

        result = self.converter.convert_stock_list(df)

        # 验证字段
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)
        self.assertIn('market', result.columns)
        self.assertIn('status', result.columns)

        # 验证数据
        self.assertEqual(len(result), 3)
        self.assertEqual(result.iloc[0]['code'], '000001')
        self.assertEqual(result.iloc[0]['name'], '平安银行')
        self.assertEqual(result.iloc[0]['status'], '正常')

        # 验证日期转换
        self.assertIsInstance(result.iloc[0]['list_date'], date)

        print("  ✓ 股票列表转换正确")

    def test_06_convert_empty_stock_list(self):
        """测试6: 转换空股票列表"""
        print("\n[测试6] 转换空股票列表...")

        df = pd.DataFrame()
        result = self.converter.convert_stock_list(df)

        self.assertTrue(result.empty)
        self.assertIn('code', result.columns)

        print("  ✓ 空数据处理正确")

    # ========== 日线数据转换测试 ==========

    def test_07_convert_daily_data(self):
        """测试7: 转换日线数据"""
        print("\n[测试7] 转换日线数据...")

        # 模拟 Tushare 返回的数据
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000001.SZ'],
            'trade_date': ['20240101', '20240102'],
            'open': [10.0, 10.2],
            'high': [10.5, 10.8],
            'low': [9.8, 10.0],
            'close': [10.2, 10.5],
            'pre_close': [9.9, 10.2],
            'vol': [10000.0, 12000.0],  # 手
            'amount': [100000.0, 120000.0],  # 千元
            'pct_chg': [3.03, 2.94],
            'turnover': [1.5, 1.8]
        })

        result = self.converter.convert_daily_data(df)

        # 验证字段
        self.assertIn('trade_date', result.columns)
        self.assertIn('open', result.columns)
        self.assertIn('volume', result.columns)
        self.assertIn('amount', result.columns)
        self.assertIn('pct_change', result.columns)
        self.assertIn('amplitude', result.columns)
        self.assertIn('change_amount', result.columns)

        # 验证单位转换
        self.assertEqual(result.iloc[0]['volume'], 1000000)  # 10000手 * 100
        self.assertEqual(result.iloc[0]['amount'], 100000000)  # 100000千元 * 1000

        # 验证派生字段
        self.assertAlmostEqual(result.iloc[0]['change_amount'], 0.3, places=1)
        amplitude = ((10.5 - 9.8) / 9.9) * 100
        self.assertAlmostEqual(result.iloc[0]['amplitude'], amplitude, places=2)

        # 验证日期转换
        self.assertIsInstance(result.iloc[0]['trade_date'], date)

        # 验证排序（应按日期升序）
        self.assertEqual(result.iloc[0]['trade_date'], date(2024, 1, 1))
        self.assertEqual(result.iloc[1]['trade_date'], date(2024, 1, 2))

        print("  ✓ 日线数据转换正确")

    def test_08_convert_empty_daily_data(self):
        """测试8: 转换空日线数据"""
        print("\n[测试8] 转换空日线数据...")

        df = pd.DataFrame()
        result = self.converter.convert_daily_data(df)

        self.assertTrue(result.empty)
        self.assertIn('trade_date', result.columns)

        print("  ✓ 空日线数据处理正确")

    # ========== 分钟数据转换测试 ==========

    def test_09_convert_minute_data(self):
        """测试9: 转换分钟数据"""
        print("\n[测试9] 转换分钟数据...")

        # 模拟 Tushare 返回的数据
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000001.SZ'],
            'trade_time': ['2024-01-01 09:30:00', '2024-01-01 09:35:00'],
            'open': [10.0, 10.2],
            'high': [10.3, 10.5],
            'low': [9.9, 10.1],
            'close': [10.2, 10.4],
            'vol': [1000.0, 1200.0],  # 手
            'amount': [10000.0, 12000.0]  # 千元
        })

        result = self.converter.convert_minute_data(df, period='5')

        # 验证字段
        self.assertIn('trade_time', result.columns)
        self.assertIn('period', result.columns)
        self.assertIn('volume', result.columns)
        self.assertIn('amount', result.columns)

        # 验证周期字段
        self.assertEqual(result.iloc[0]['period'], '5')

        # 验证单位转换
        self.assertEqual(result.iloc[0]['volume'], 100000)  # 1000手 * 100
        self.assertEqual(result.iloc[0]['amount'], 10000000)  # 10000千元 * 1000

        print("  ✓ 分钟数据转换正确")

    # ========== 实时行情转换测试 ==========

    def test_10_convert_realtime_quotes(self):
        """测试10: 转换实时行情"""
        print("\n[测试10] 转换实时行情...")

        # 模拟 Tushare 返回的数据
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '600000.SH'],
            'name': ['平安银行', '浦发银行'],
            'price': [10.5, 8.2],
            'open': [10.0, 8.0],
            'high': [10.8, 8.5],
            'low': [9.9, 7.9],
            'pre_close': [10.2, 8.1],
            'volume': [10000.0, 8000.0],
            'amount': [100000.0, 65000.0],
            'pct_chg': [2.94, 1.23],
            'change': [0.3, 0.1]
        })

        result = self.converter.convert_realtime_quotes(df)

        # 验证字段
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)
        self.assertIn('latest_price', result.columns)
        self.assertIn('amplitude', result.columns)
        self.assertIn('trade_time', result.columns)

        # 验证代码提取
        self.assertEqual(result.iloc[0]['code'], '000001')
        self.assertEqual(result.iloc[1]['code'], '600000')

        # 验证振幅计算
        amplitude = ((10.8 - 9.9) / 10.2) * 100
        self.assertAlmostEqual(result.iloc[0]['amplitude'], amplitude, places=2)

        print("  ✓ 实时行情转换正确")

    # ========== 新股数据转换测试 ==========

    def test_11_convert_new_stocks(self):
        """测试11: 转换新股数据"""
        print("\n[测试11] 转换新股数据...")

        # 模拟 Tushare 返回的数据（使用 ipo_date）
        df = pd.DataFrame({
            'ts_code': ['301234.SZ', '688567.SH'],
            'name': ['新股A', '新股B'],
            'ipo_date': ['20240101', '20240102']
        })

        result = self.converter.convert_new_stocks(df)

        # 验证字段
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)
        self.assertIn('list_date', result.columns)
        self.assertIn('market', result.columns)
        self.assertIn('status', result.columns)

        # 验证数据
        self.assertEqual(len(result), 2)
        self.assertEqual(result.iloc[0]['status'], '正常')

        print("  ✓ 新股数据转换正确")

    def test_12_convert_new_stocks_with_issue_date(self):
        """测试12: 转换新股数据（使用 issue_date）"""
        print("\n[测试12] 转换新股数据（使用 issue_date）...")

        # 模拟 Tushare 返回的数据（使用 issue_date）
        df = pd.DataFrame({
            'symbol': ['301234', '688567'],
            'name': ['新股A', '新股B'],
            'issue_date': ['20240101', '20240102']
        })

        result = self.converter.convert_new_stocks(df)

        # 验证字段
        self.assertIn('code', result.columns)
        self.assertIn('list_date', result.columns)

        print("  ✓ issue_date 字段处理正确")

    # ========== 退市股票转换测试 ==========

    def test_13_convert_delisted_stocks(self):
        """测试13: 转换退市股票"""
        print("\n[测试13] 转换退市股票...")

        # 模拟 Tushare 返回的数据
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '600000.SH'],
            'symbol': ['000001', '600000'],
            'name': ['退市A', '退市B'],
            'list_date': ['20100101', '20000101'],
            'delist_date': ['20240101', '20230601'],
            'market': ['主板', '主板']
        })

        result = self.converter.convert_delisted_stocks(df)

        # 验证字段
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)
        self.assertIn('list_date', result.columns)
        self.assertIn('delist_date', result.columns)
        self.assertIn('market', result.columns)

        # 验证日期转换
        self.assertIsInstance(result.iloc[0]['list_date'], date)
        self.assertIsInstance(result.iloc[0]['delist_date'], date)

        print("  ✓ 退市股票转换正确")

    # ========== 边界情况测试 ==========

    def test_14_convert_with_missing_fields(self):
        """测试14: 缺少字段的数据转换"""
        print("\n[测试14] 缺少字段的数据转换...")

        # 缺少部分字段的日线数据
        df = pd.DataFrame({
            'trade_date': ['20240101'],
            'open': [10.0],
            'close': [10.2]
            # 缺少 high, low, volume 等字段
        })

        result = self.converter.convert_daily_data(df)

        # 应该只包含存在的字段
        self.assertIn('trade_date', result.columns)
        self.assertIn('open', result.columns)
        self.assertIn('close', result.columns)

        print("  ✓ 缺少字段的数据处理正确")

    def test_15_convert_with_null_values(self):
        """测试15: 包含空值的数据转换"""
        print("\n[测试15] 包含空值的数据转换...")

        # 包含空值的数据
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', None],
            'symbol': ['000001', '000002'],
            'name': ['平安银行', None],
            'list_date': ['19910403', None]
        })

        result = self.converter.convert_stock_list(df)

        # 应该能正确处理空值
        self.assertEqual(len(result), 2)

        print("  ✓ 空值数据处理正确")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTushareDataConverter)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
