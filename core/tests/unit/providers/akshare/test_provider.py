#!/usr/bin/env python3
"""
AkShareProvider 单元测试
"""

import sys
import unittest
from datetime import datetime, date
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from src.providers.akshare.provider import AkShareProvider
from src.providers.akshare.exceptions import AkShareDataError


class TestAkShareProvider(unittest.TestCase):
    """测试 AkShareProvider 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("AkShareProvider 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        # Mock AkShareAPIClient
        self.mock_api_client_class = patch('providers.akshare.provider.AkShareAPIClient')
        self.mock_api_client = self.mock_api_client_class.start()

    def tearDown(self):
        """每个测试后的清理"""
        self.mock_api_client_class.stop()

    def test_01_init(self):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        provider = AkShareProvider(
            timeout=30,
            retry_count=3
        )

        self.assertEqual(provider.timeout, 30)
        self.assertEqual(provider.retry_count, 3)

        print("  ✓ 初始化成功")

    def test_02_get_stock_list_success(self):
        """测试2: 成功获取股票列表"""
        print("\n[测试2] 成功获取股票列表...")

        # Mock API 返回数据
        mock_df = pd.DataFrame({
            'code': ['000001', '600000'],
            'name': ['平安银行', '浦发银行']
        })

        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = mock_df
        self.mock_api_client.return_value = mock_client_instance

        provider = AkShareProvider()
        result = provider.get_stock_list()

        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('code', result.columns)
        self.assertIn('name', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 只股票")

    def test_03_get_stock_list_empty(self):
        """测试3: 获取空股票列表应抛出异常"""
        print("\n[测试3] 获取空股票列表应抛出异常...")

        # Mock API 返回空数据
        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = pd.DataFrame()
        self.mock_api_client.return_value = mock_client_instance

        provider = AkShareProvider()

        with self.assertRaises(AkShareDataError):
            provider.get_stock_list()

        print("  ✓ 正确抛出 AkShareDataError")

    def test_04_get_daily_data(self):
        """测试4: 获取日线数据"""
        print("\n[测试4] 获取日线数据...")

        # Mock API 返回数据
        mock_df = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02'],
            '开盘': ['10.00', '10.20'],
            '收盘': ['10.20', '10.50'],
            '最高': ['10.50', '10.80'],
            '最低': ['9.80', '10.00'],
            '成交量': ['1000000', '1200000'],
            '成交额': ['10200000', '12600000']
        })

        mock_client_instance = MagicMock()
        mock_client_instance.execute.return_value = mock_df
        mock_client_instance.stock_zh_a_hist = Mock()
        self.mock_api_client.return_value = mock_client_instance

        provider = AkShareProvider()
        result = provider.get_daily_data(
            code='000001',
            start_date='2024-01-01',
            end_date='2024-01-31'
        )

        # 验证结果
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('trade_date', result.columns)

        print(f"  ✓ 成功获取 {len(result)} 条日线数据")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAkShareProvider)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
