#!/usr/bin/env python3
"""
AkShareAPIClient 单元测试

测试 API 客户端的功能：
- 初始化和配置
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

from providers.akshare.api_client import AkShareAPIClient
from providers.akshare.exceptions import (
    AkShareImportError,
    AkShareDataError,
    AkShareRateLimitError,
    AkShareTimeoutError,
    AkShareNetworkError
)


class TestAkShareAPIClient(unittest.TestCase):
    """测试 AkShareAPIClient 类"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("AkShareAPIClient 单元测试")
        print("="*60)

    @patch('providers.akshare.api_client.ak')
    def test_01_init_success(self, mock_ak):
        """测试1: 成功初始化"""
        print("\n[测试1] 成功初始化...")

        client = AkShareAPIClient(
            timeout=30,
            retry_count=3,
            retry_delay=1,
            request_delay=0.3
        )

        self.assertEqual(client.timeout, 30)
        self.assertEqual(client.retry_count, 3)
        self.assertEqual(client.retry_delay, 1)
        self.assertEqual(client.request_delay, 0.3)

        print("  ✓ 初始化成功，参数正确")

    @patch('providers.akshare.api_client.ak')
    def test_02_execute_success(self, mock_ak):
        """测试2: 成功执行 API 调用"""
        print("\n[测试2] 成功执行 API 调用...")

        client = AkShareAPIClient(request_delay=0.01)

        # Mock API 函数
        mock_func = Mock(return_value={'data': 'test'})

        # 执行调用
        result = client.execute(mock_func, param1='value1')

        self.assertEqual(result, {'data': 'test'})
        mock_func.assert_called_once_with(param1='value1')

        print("  ✓ API 调用成功")

    @patch('providers.akshare.api_client.ak')
    def test_03_execute_with_retry(self, mock_ak):
        """测试3: 失败后重试机制"""
        print("\n[测试3] 失败后重试机制...")

        client = AkShareAPIClient(
            retry_count=3,
            retry_delay=0.01,
            request_delay=0.01
        )

        # Mock API 函数，前两次失败，第三次成功
        mock_func = Mock(side_effect=[
            Exception("网络错误"),
            Exception("临时错误"),
            {'data': 'success'}
        ])

        # 执行调用
        result = client.execute(mock_func)

        self.assertEqual(result, {'data': 'success'})
        self.assertEqual(mock_func.call_count, 3)

        print("  ✓ 重试机制工作正常")

    @patch('providers.akshare.api_client.ak')
    def test_04_rate_limit_error_no_retry(self, mock_ak):
        """测试4: IP限流错误不重试"""
        print("\n[测试4] IP限流错误不重试...")

        client = AkShareAPIClient(
            retry_count=3,
            retry_delay=0.01,
            request_delay=0.01
        )

        # Mock API 函数，返回限流错误
        mock_func = Mock(side_effect=Exception("IP限流，请稍后重试"))

        # 执行调用，应立即抛出异常
        with self.assertRaises(AkShareRateLimitError):
            client.execute(mock_func)

        # 只调用一次，不重试
        self.assertEqual(mock_func.call_count, 1)

        print("  ✓ IP限流错误不重试，正确抛出异常")


def run_tests():
    """运行所有测试"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAkShareAPIClient)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
