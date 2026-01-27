#!/usr/bin/env python3
"""
TushareAPIClient 单元测试

测试 API 客户端的功能：
- 初始化和配置验证
- 重试机制
- 错误处理
- 频率限制
"""

import sys
import unittest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from providers.tushare.api_client import TushareAPIClient
from providers.tushare.exceptions import (
    TushareTokenError,
    TusharePermissionError,
    TushareRateLimitError,
    TushareAPIError
)


class TestTushareAPIClient(unittest.TestCase):
    """测试 TushareAPIClient 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("TushareAPIClient 单元测试")
        print("="*60)

    def test_01_init_without_token(self):
        """测试1: 无 Token 初始化应失败"""
        print("\n[测试1] 无 Token 初始化应失败...")

        with self.assertRaises(TushareTokenError):
            TushareAPIClient(token='')

        print("  ✓ 正确抛出 TushareTokenError")

    @patch('providers.tushare.api_client.ts')
    def test_02_init_with_token(self, mock_ts):
        """测试2: 有 Token 初始化成功"""
        print("\n[测试2] 有 Token 初始化成功...")

        # Mock tushare
        mock_ts.set_token = Mock()
        mock_ts.pro_api = Mock(return_value=Mock())

        client = TushareAPIClient(
            token='test_token_123',
            timeout=30,
            retry_count=3,
            retry_delay=1,
            request_delay=0.2
        )

        self.assertEqual(client.token, 'test_token_123')
        self.assertEqual(client.timeout, 30)
        self.assertEqual(client.retry_count, 3)
        self.assertEqual(client.retry_delay, 1)
        self.assertEqual(client.request_delay, 0.2)

        print("  ✓ 初始化成功，参数正确")

    @patch('providers.tushare.api_client.ts')
    def test_03_execute_success(self, mock_ts):
        """测试3: 成功执行 API 调用"""
        print("\n[测试3] 成功执行 API 调用...")

        # Mock tushare
        mock_ts.set_token = Mock()
        mock_ts.pro_api = Mock(return_value=Mock())

        client = TushareAPIClient(
            token='test_token',
            request_delay=0.01  # 减少测试时间
        )

        # Mock API 函数
        mock_func = Mock(return_value={'data': 'test'})

        # 执行调用
        result = client.execute(mock_func, param1='value1')

        self.assertEqual(result, {'data': 'test'})
        mock_func.assert_called_once_with(param1='value1')

        print("  ✓ API 调用成功")

    @patch('providers.tushare.api_client.ts')
    def test_04_execute_with_retry(self, mock_ts):
        """测试4: 失败后重试机制"""
        print("\n[测试4] 失败后重试机制...")

        # Mock tushare
        mock_ts.set_token = Mock()
        mock_ts.pro_api = Mock(return_value=Mock())

        client = TushareAPIClient(
            token='test_token',
            retry_count=3,
            retry_delay=0.01,  # 减少测试时间
            request_delay=0.01
        )

        # Mock API 函数，前两次失败，第三次成功
        mock_func = Mock(side_effect=[
            Exception("网络错误"),
            Exception("超时"),
            {'data': 'success'}
        ])

        # 执行调用
        result = client.execute(mock_func)

        self.assertEqual(result, {'data': 'success'})
        self.assertEqual(mock_func.call_count, 3)

        print("  ✓ 重试机制工作正常")

    @patch('providers.tushare.api_client.ts')
    def test_05_execute_permission_error_no_retry(self, mock_ts):
        """测试5: 权限错误不重试"""
        print("\n[测试5] 权限错误不重试...")

        # Mock tushare
        mock_ts.set_token = Mock()
        mock_ts.pro_api = Mock(return_value=Mock())

        client = TushareAPIClient(
            token='test_token',
            retry_count=3,
            retry_delay=0.01,
            request_delay=0.01
        )

        # Mock API 函数，返回积分不足错误
        mock_func = Mock(side_effect=Exception("积分不足，无法访问"))

        # 执行调用，应立即抛出异常
        with self.assertRaises(TusharePermissionError):
            client.execute(mock_func)

        # 只调用一次，不重试
        self.assertEqual(mock_func.call_count, 1)

        print("  ✓ 权限错误不重试，正确抛出异常")

    @patch('providers.tushare.api_client.ts')
    def test_06_execute_rate_limit_error_no_retry(self, mock_ts):
        """测试6: 频率限制错误不重试"""
        print("\n[测试6] 频率限制错误不重试...")

        # Mock tushare
        mock_ts.set_token = Mock()
        mock_ts.pro_api = Mock(return_value=Mock())

        client = TushareAPIClient(
            token='test_token',
            retry_count=3,
            retry_delay=0.01,
            request_delay=0.01
        )

        # Mock API 函数，返回频率限制错误
        mock_func = Mock(side_effect=Exception("抱歉，您每分钟最多访问200次"))

        # 执行调用，应立即抛出异常
        with self.assertRaises(TushareRateLimitError):
            client.execute(mock_func)

        # 只调用一次，不重试
        self.assertEqual(mock_func.call_count, 1)

        print("  ✓ 频率限制错误不重试，正确抛出异常")

    @patch('providers.tushare.api_client.ts')
    def test_07_execute_max_retries_exceeded(self, mock_ts):
        """测试7: 重试次数用尽后抛出异常"""
        print("\n[测试7] 重试次数用尽后抛出异常...")

        # Mock tushare
        mock_ts.set_token = Mock()
        mock_ts.pro_api = Mock(return_value=Mock())

        client = TushareAPIClient(
            token='test_token',
            retry_count=3,
            retry_delay=0.01,
            request_delay=0.01
        )

        # Mock API 函数，总是失败
        mock_func = Mock(side_effect=Exception("网络错误"))

        # 执行调用，应抛出异常
        with self.assertRaises(TushareAPIError):
            client.execute(mock_func)

        # 调用了3次（重试次数）
        self.assertEqual(mock_func.call_count, 3)

        print("  ✓ 重试次数用尽，正确抛出异常")

    @patch('providers.tushare.api_client.ts')
    def test_08_query_method(self, mock_ts):
        """测试8: 通用查询方法"""
        print("\n[测试8] 通用查询方法...")

        # Mock tushare
        mock_ts.set_token = Mock()
        mock_pro = Mock()
        mock_ts.pro_api = Mock(return_value=mock_pro)

        # Mock API 方法
        mock_stock_basic = Mock(return_value={'data': 'stock_list'})
        mock_pro.stock_basic = mock_stock_basic

        client = TushareAPIClient(
            token='test_token',
            request_delay=0.01
        )

        # 调用通用查询方法
        result = client.query('stock_basic', exchange='', list_status='L')

        self.assertEqual(result, {'data': 'stock_list'})
        mock_stock_basic.assert_called_once_with(exchange='', list_status='L')

        print("  ✓ 通用查询方法工作正常")

    @patch('providers.tushare.api_client.ts')
    def test_09_query_invalid_api(self, mock_ts):
        """测试9: 查询不存在的 API"""
        print("\n[测试9] 查询不存在的 API...")

        # Mock tushare
        mock_ts.set_token = Mock()
        mock_ts.pro_api = Mock(return_value=Mock())

        client = TushareAPIClient(token='test_token')

        # 调用不存在的 API
        with self.assertRaises(TushareAPIError):
            client.query('non_existent_api')

        print("  ✓ 不存在的 API 正确抛出异常")

    @patch('providers.tushare.api_client.ts')
    def test_10_api_properties(self, mock_ts):
        """测试10: API 属性访问器"""
        print("\n[测试10] API 属性访问器...")

        # Mock tushare
        mock_ts.set_token = Mock()
        mock_pro = Mock()
        mock_ts.pro_api = Mock(return_value=mock_pro)

        client = TushareAPIClient(token='test_token')

        # 测试各个属性
        _ = client.stock_basic
        _ = client.daily
        _ = client.stk_mins
        _ = client.realtime_quotes
        _ = client.new_share

        print("  ✓ 所有 API 属性访问正常")

    @patch('providers.tushare.api_client.ts')
    def test_11_request_delay(self, mock_ts):
        """测试11: 请求间隔控制"""
        print("\n[测试11] 请求间隔控制...")

        # Mock tushare
        mock_ts.set_token = Mock()
        mock_ts.pro_api = Mock(return_value=Mock())

        client = TushareAPIClient(
            token='test_token',
            request_delay=0.1
        )

        # Mock API 函数
        mock_func = Mock(return_value={'data': 'test'})

        # 执行两次调用，测量时间
        start_time = time.time()
        client.execute(mock_func)
        client.execute(mock_func)
        elapsed = time.time() - start_time

        # 应至少等待 0.2 秒（两次请求间隔）
        self.assertGreaterEqual(elapsed, 0.2)

        print(f"  ✓ 请求间隔控制正常 (耗时: {elapsed:.2f}秒)")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTushareAPIClient)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
