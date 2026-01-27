#!/usr/bin/env python3
"""
AkShareProvider 集成测试

真实调用 AkShare API 进行集成测试（免费，无需Token）

注意：
1. 需要网络连接
2. 测试会产生真实 API 调用
3. 可能受到 IP 限流影响
"""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from providers.akshare.provider import AkShareProvider
from providers.akshare.exceptions import (
    AkShareRateLimitError,
    AkShareDataError
)


class TestAkShareProviderIntegration(unittest.TestCase):
    """AkShareProvider 集成测试（真实API调用）"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("AkShareProvider 集成测试")
        print("="*60)

        # 创建 Provider 实例
        try:
            cls.provider = AkShareProvider(
                timeout=60,
                retry_count=2,
                request_delay=0.5  # 增加请求间隔，避免限流
            )
            print(f"✓ Provider 初始化成功")
        except Exception as e:
            raise unittest.SkipTest(f"Provider 初始化失败: {e}")

    def test_01_get_stock_list(self):
        """测试1: 获取股票列表（免费接口）"""
        print("\n[测试1] 获取股票列表...")

        try:
            result = self.provider.get_stock_list()

            # 验证结果
            self.assertIsInstance(result, pd.DataFrame)
            self.assertGreater(len(result), 3000)  # A股至少3000只
            self.assertIn('code', result.columns)
            self.assertIn('name', result.columns)

            print(f"  ✓ 成功获取 {len(result)} 只股票")
            print(f"  示例数据:")
            print(result.head(3).to_string(index=False))

        except AkShareRateLimitError as e:
            self.skipTest(f"IP限流: {e}")

    def test_02_get_daily_data(self):
        """测试2: 获取日线数据（免费接口）"""
        print("\n[测试2] 获取单只股票日线数据...")

        try:
            # 获取平安银行最近30天数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

            result = self.provider.get_daily_data(
                code='000001',
                start_date=start_date,
                end_date=end_date,
                adjust='qfq'
            )

            # 验证结果
            self.assertIsInstance(result, pd.DataFrame)
            if not result.empty:
                self.assertIn('trade_date', result.columns)
                self.assertIn('close', result.columns)

                print(f"  ✓ 成功获取 {len(result)} 条日线数据")
                print(f"  日期范围: {result['trade_date'].min()} - {result['trade_date'].max()}")
            else:
                print("  ⚠ 数据为空（可能是非交易日）")

        except AkShareRateLimitError as e:
            self.skipTest(f"IP限流: {e}")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAkShareProviderIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
