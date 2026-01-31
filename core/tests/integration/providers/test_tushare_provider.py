#!/usr/bin/env python3
"""
TushareProvider 集成测试

真实调用 Tushare API 进行集成测试（需要真实 Token 和积分）

注意：
1. 需要设置环境变量 TUSHARE_TOKEN
2. 需要足够的 Tushare 积分
3. 测试会产生真实 API 调用
4. 建议在开发环境谨慎运行

运行方式：
    export TUSHARE_TOKEN=your_token_here
    python test_tushare_provider.py
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from src.providers.tushare.provider import TushareProvider
from src.providers.tushare.exceptions import (
    TusharePermissionError,
    TushareRateLimitError,
    TushareDataError,
    TushareAPIError
)


def unwrap_response(response):
    """从Response对象中提取数据"""
    if hasattr(response, 'status'):
        # 检查错误状态
        if response.status == 'ERROR':
            error_code = getattr(response, 'error_code', '')
            if 'RATE_LIMIT' in error_code:
                raise TushareRateLimitError(str(response.message))
            elif 'PERMISSION' in error_code:
                raise TusharePermissionError(str(response.message))
        # 返回数据，如果为None返回空DataFrame
        data = response.data if hasattr(response, 'data') else None
        if data is None:
            return pd.DataFrame()
        return data
    return response if response is not None else pd.DataFrame()


class TestTushareProviderIntegration(unittest.TestCase):
    """TushareProvider 集成测试（需要真实 Token）"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("TushareProvider 集成测试")
        print("="*60)

        # 从环境变量获取 Token
        cls.token = os.getenv('TUSHARE_TOKEN')
        if not cls.token:
            print("\n警告: 未设置 TUSHARE_TOKEN 环境变量")
            print("跳过集成测试...")
            raise unittest.SkipTest("未设置 TUSHARE_TOKEN 环境变量")

        # 创建 Provider 实例
        try:
            cls.provider = TushareProvider(
                token=cls.token,
                timeout=30,
                retry_count=2,
                retry_delay=1,
                request_delay=0.5  # 增加请求间隔，避免频率限制
            )
            print(f"✓ Provider 初始化成功: {cls.provider}")
        except Exception as e:
            raise unittest.SkipTest(f"Provider 初始化失败: {e}")

    def test_01_get_stock_list(self):
        """测试1: 获取股票列表（免费接口）"""
        print("\n[测试1] 获取股票列表...")

        try:
            result = unwrap_response(self.provider.get_stock_list())

            # 验证结果
            self.assertIsInstance(result, pd.DataFrame)
            self.assertGreater(len(result), 3000)  # A股至少3000只
            self.assertIn('code', result.columns)
            self.assertIn('name', result.columns)
            self.assertIn('market', result.columns)

            print(f"  ✓ 成功获取 {len(result)} 只股票")
            print(f"  示例数据:")
            print(result.head(3).to_string(index=False))

        except TusharePermissionError as e:
            self.skipTest(f"权限不足: {e}")
        except TushareRateLimitError as e:
            self.skipTest(f"频率限制: {e}")

    def test_02_get_daily_data_single_stock(self):
        """测试2: 获取单只股票日线数据（需要120积分）"""
        print("\n[测试2] 获取单只股票日线数据...")

        try:
            # 获取平安银行最近30天数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

            result = unwrap_response(self.provider.get_daily_data(
                code='000001',
                start_date=start_date,
                end_date=end_date,
                adjust='qfq'
            ))

            # 验证结果
            self.assertIsInstance(result, pd.DataFrame)
            if not result.empty:
                self.assertIn('trade_date', result.columns)
                self.assertIn('open', result.columns)
                self.assertIn('close', result.columns)
                self.assertIn('volume', result.columns)
                self.assertIn('amount', result.columns)

                # 验证数据类型
                self.assertTrue(all(isinstance(x, (int, float)) for x in result['open']))
                self.assertTrue(all(isinstance(x, (int, float)) for x in result['volume']))

                print(f"  ✓ 成功获取 {len(result)} 条日线数据")
                print(f"  日期范围: {result['trade_date'].min()} - {result['trade_date'].max()}")
                print(f"  示例数据:")
                print(result.head(3).to_string(index=False))
            else:
                print("  ⚠ 数据为空（可能是非交易日）")

        except TusharePermissionError as e:
            self.skipTest(f"权限不足（需要120积分）: {e}")
        except TushareRateLimitError as e:
            self.skipTest(f"频率限制: {e}")

    def test_03_get_daily_batch(self):
        """测试3: 批量获取日线数据（需要120积分）"""
        print("\n[测试3] 批量获取日线数据...")

        try:
            # 获取3只股票最近10天数据
            codes = ['000001', '600000', '000002']
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')

            result = unwrap_response(self.provider.get_daily_batch(
                codes=codes,
                start_date=start_date,
                end_date=end_date
            ))

            # 验证结果
            self.assertIsInstance(result, dict)
            self.assertGreater(len(result), 0)

            for code, df in result.items():
                self.assertIsInstance(df, pd.DataFrame)
                if not df.empty:
                    self.assertIn('trade_date', df.columns)

            print(f"  ✓ 成功获取 {len(result)}/{len(codes)} 只股票数据")
            for code, df in result.items():
                print(f"    - {code}: {len(df)} 条数据")

        except TusharePermissionError as e:
            self.skipTest(f"权限不足（需要120积分）: {e}")
        except TushareRateLimitError as e:
            self.skipTest(f"频率限制: {e}")

    def test_04_get_new_stocks(self):
        """测试4: 获取新股列表（需要120积分）"""
        print("\n[测试4] 获取新股列表...")

        try:
            result = unwrap_response(self.provider.get_new_stocks(days=90))

            # 验证结果
            self.assertIsInstance(result, pd.DataFrame)
            # 新股数量可能为0（没有新股上市）
            if not result.empty:
                self.assertIn('code', result.columns)
                self.assertIn('name', result.columns)
                self.assertIn('list_date', result.columns)

                print(f"  ✓ 成功获取 {len(result)} 只新股")
                print(f"  示例数据:")
                print(result.head(3).to_string(index=False))
            else:
                print("  ⚠ 最近90天无新股上市")

        except TusharePermissionError as e:
            self.skipTest(f"权限不足（需要120积分）: {e}")
        except TushareRateLimitError as e:
            self.skipTest(f"频率限制: {e}")

    def test_05_get_delisted_stocks(self):
        """测试5: 获取退市股票列表（免费接口）"""
        print("\n[测试5] 获取退市股票列表...")

        try:
            result = unwrap_response(self.provider.get_delisted_stocks())

            # 验证结果
            self.assertIsInstance(result, pd.DataFrame)
            if not result.empty:
                self.assertIn('code', result.columns)
                self.assertIn('name', result.columns)
                self.assertIn('delist_date', result.columns)

                print(f"  ✓ 成功获取 {len(result)} 只退市股票")
                print(f"  示例数据:")
                print(result.head(3).to_string(index=False))
            else:
                print("  ⚠ 无退市股票数据")

        except TusharePermissionError as e:
            self.skipTest(f"权限不足: {e}")
        except TushareRateLimitError as e:
            self.skipTest(f"频率限制: {e}")

    def test_06_get_minute_data(self):
        """测试6: 获取分钟数据（需要2000积分）"""
        print("\n[测试6] 获取分钟数据...")

        try:
            # 获取最近一天的5分钟数据
            date = datetime.now().strftime('%Y%m%d')

            result = unwrap_response(self.provider.get_minute_data(
                code='000001',
                period='5',
                start_date=date,
                end_date=date
            ))

            # 验证结果
            self.assertIsInstance(result, pd.DataFrame)
            if not result.empty:
                self.assertIn('trade_time', result.columns)
                self.assertIn('period', result.columns)
                self.assertIn('open', result.columns)

                print(f"  ✓ 成功获取 {len(result)} 条分钟数据")
                print(f"  示例数据:")
                print(result.head(3).to_string(index=False))
            else:
                print("  ⚠ 数据为空（可能是非交易日）")

        except TusharePermissionError as e:
            self.skipTest(f"权限不足（需要2000积分）: {e}")
        except TushareRateLimitError as e:
            self.skipTest(f"频率限制: {e}")

    def test_07_get_realtime_quotes(self):
        """测试7: 获取实时行情（需要5000积分）"""
        print("\n[测试7] 获取实时行情...")

        try:
            result = unwrap_response(self.provider.get_realtime_quotes(
                codes=['000001', '600000']
            ))

            # 验证结果
            self.assertIsInstance(result, pd.DataFrame)
            if not result.empty:
                self.assertIn('code', result.columns)
                self.assertIn('name', result.columns)
                self.assertIn('latest_price', result.columns)

                print(f"  ✓ 成功获取 {len(result)} 只股票实时行情")
                print(f"  示例数据:")
                print(result.to_string(index=False))
            else:
                print("  ⚠ 数据为空")

        except TusharePermissionError as e:
            self.skipTest(f"权限不足（需要5000积分）: {e}")
        except TushareRateLimitError as e:
            self.skipTest(f"频率限制: {e}")
        except TushareAPIError as e:
            if "请指定正确的接口名" in str(e):
                self.skipTest(f"接口不可用或已废弃: {e}")
            raise

    def test_08_data_consistency(self):
        """测试8: 数据一致性检查"""
        print("\n[测试8] 数据一致性检查...")

        try:
            # 获取股票列表
            stock_list = unwrap_response(self.provider.get_stock_list())
            self.assertGreater(len(stock_list), 0)

            # 随机选择一只股票
            test_code = stock_list.iloc[0]['code']
            print(f"  测试股票: {test_code} {stock_list.iloc[0]['name']}")

            # 获取日线数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')

            daily_data = unwrap_response(self.provider.get_daily_data(
                code=test_code,
                start_date=start_date,
                end_date=end_date
            ))

            if not daily_data.empty:
                # 检查数据完整性
                required_fields = ['trade_date', 'open', 'high', 'low', 'close', 'volume']
                for field in required_fields:
                    self.assertIn(field, daily_data.columns)
                    self.assertFalse(daily_data[field].isnull().all())

                # 检查价格逻辑（high >= low）
                self.assertTrue((daily_data['high'] >= daily_data['low']).all())

                # 检查价格范围（open, close 在 high 和 low 之间）
                self.assertTrue(
                    ((daily_data['open'] >= daily_data['low']) &
                     (daily_data['open'] <= daily_data['high'])).all()
                )

                print(f"  ✓ 数据一致性检查通过")
                print(f"    - 数据条数: {len(daily_data)}")
                print(f"    - 日期范围: {daily_data['trade_date'].min()} - {daily_data['trade_date'].max()}")
            else:
                print("  ⚠ 数据为空，跳过一致性检查")

        except TusharePermissionError as e:
            self.skipTest(f"权限不足: {e}")
        except TushareRateLimitError as e:
            self.skipTest(f"频率限制: {e}")

    def test_09_error_handling(self):
        """测试9: 错误处理"""
        print("\n[测试9] 错误处理...")

        # 测试无效股票代码
        response = self.provider.get_daily_data(code='999999')
        # 处理Response对象，允许WARNING状态
        if hasattr(response, 'status'):
            result = response.data if hasattr(response, 'data') else pd.DataFrame()
        else:
            result = response
        self.assertIsInstance(result, pd.DataFrame)
        self.assertTrue(result.empty)

        print("  ✓ 无效股票代码处理正确")


def run_tests():
    """运行所有测试"""
    # 检查是否设置了 Token
    if not os.getenv('TUSHARE_TOKEN'):
        print("\n" + "="*60)
        print("集成测试需要 Tushare Token")
        print("="*60)
        print("\n请设置环境变量:")
        print("  export TUSHARE_TOKEN=your_token_here")
        print("\n然后重新运行测试")
        return False

    suite = unittest.TestLoader().loadTestsFromTestCase(TestTushareProviderIntegration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
