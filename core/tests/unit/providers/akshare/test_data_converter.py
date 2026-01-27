#!/usr/bin/env python3
"""
AkShareDataConverter 单元测试
"""

import sys
import unittest
from datetime import datetime, date
from pathlib import Path
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from src.providers.akshare.data_converter import AkShareDataConverter


class TestAkShareDataConverter(unittest.TestCase):
    """测试 AkShareDataConverter 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("AkShareDataConverter 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        self.converter = AkShareDataConverter()

    def test_01_safe_float(self):
        """测试1: 安全浮点数转换"""
        print("\n[测试1] 安全浮点数转换...")

        # 普通数字
        self.assertEqual(self.converter.safe_float('123.45'), 123.45)
        
        # 百分号
        self.assertEqual(self.converter.safe_float('12.5%'), 12.5)
        
        # 逗号
        self.assertEqual(self.converter.safe_float('1,234.56'), 1234.56)
        
        # 空值
        self.assertIsNone(self.converter.safe_float(''))
        self.assertIsNone(self.converter.safe_float(None))
        
        print("  ✓ 浮点数转换正确")

    def test_02_safe_int(self):
        """测试2: 安全整数转换"""
        print("\n[测试2] 安全整数转换...")

        # 普通数字
        self.assertEqual(self.converter.safe_int('123'), 123)
        
        # 浮点数字符串
        self.assertEqual(self.converter.safe_int('123.0'), 123)
        
        # 逗号
        self.assertEqual(self.converter.safe_int('1,234'), 1234)
        
        # 空值
        self.assertIsNone(self.converter.safe_int(''))
        self.assertIsNone(self.converter.safe_int(None))
        
        print("  ✓ 整数转换正确")

    def test_03_convert_stock_list(self):
        """测试3: 转换股票列表"""
        print("\n[测试3] 转换股票列表...")

        # 模拟 AkShare 返回的数据
        df = pd.DataFrame({
            'code': ['000001', '600000', '300001'],
            'name': ['平安银行', '浦发银行', '特锐德']
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
        self.assertEqual(result.iloc[0]['status'], '正常')

        print("  ✓ 股票列表转换正确")

    def test_04_convert_daily_data(self):
        """测试4: 转换日线数据"""
        print("\n[测试4] 转换日线数据...")

        # 模拟 AkShare 返回的数据
        df = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02'],
            '开盘': ['10.00', '10.20'],
            '最高': ['10.50', '10.80'],
            '最低': ['9.80', '10.00'],
            '收盘': ['10.20', '10.50'],
            '成交量': ['1000000', '1200000'],
            '成交额': ['10200000', '12600000']
        })

        result = self.converter.convert_daily_data(df)

        # 验证字段
        self.assertIn('trade_date', result.columns)
        self.assertIn('open', result.columns)
        self.assertIn('close', result.columns)
        self.assertIn('volume', result.columns)

        # 验证数据类型
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result.iloc[0]['open'], float)

        print(f"  ✓ 日线数据转换正确")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAkShareDataConverter)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
