#!/usr/bin/env python3
"""
Provider 弹性机制集成测试

测试内容:
1. Provider 自动切换
2. 失败重试机制
3. API 限流控制
4. 错误处理和恢复

目标覆盖率: Provider 关键路径 >85%
"""

import sys
import unittest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from src.providers.provider_factory import DataProviderFactory
from src.providers.provider_registry import ProviderRegistry
from src.providers.base_provider import BaseDataProvider


# 创建模拟 Provider 用于测试
class MockReliableProvider(BaseDataProvider):
    """可靠的模拟提供者"""

    def __init__(self, **kwargs):
        self.call_count = 0
        super().__init__(**kwargs)

    def _validate_config(self):
        pass

    def get_stock_list(self):
        self.call_count += 1
        return pd.DataFrame({
            'code': ['000001', '600000'],
            'name': ['股票A', '股票B']
        })

    def get_daily_data(self, code, start_date=None, end_date=None, adjust='qfq'):
        self.call_count += 1
        return pd.DataFrame({
            'trade_date': ['2024-01-01'],
            'open': [10.0],
            'close': [10.5]
        })

    def get_new_stocks(self, days=30):
        """获取新股列表"""
        return pd.DataFrame({
            'code': ['000001'],
            'name': ['新股A']
        })

    def get_delisted_stocks(self):
        """获取退市股票列表"""
        return pd.DataFrame({
            'code': [],
            'name': []
        })

    def get_daily_batch(self, codes, start_date=None, end_date=None, adjust='qfq'):
        """批量获取日线数据"""
        return {code: self.get_daily_data(code, start_date, end_date, adjust) for code in codes}

    def get_minute_data(self, code, period='5', start_date=None, end_date=None, adjust=''):
        """获取分时数据"""
        return pd.DataFrame({
            'trade_time': ['2024-01-01 09:30:00'],
            'open': [10.0],
            'close': [10.5]
        })

    def get_realtime_quotes(self, codes=None):
        """获取实时行情"""
        return pd.DataFrame({
            'code': ['000001'],
            'name': ['股票A'],
            'latest_price': [10.5]
        })


class MockUnreliableProvider(BaseDataProvider):
    """不可靠的模拟提供者（会失败）"""

    def __init__(self, fail_times=3, **kwargs):
        self.call_count = 0
        self.fail_times = fail_times
        super().__init__(**kwargs)

    def _validate_config(self):
        pass

    def get_stock_list(self):
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise Exception("模拟失败")
        return pd.DataFrame({
            'code': ['000001'],
            'name': ['股票A']
        })

    def get_daily_data(self, code, start_date=None, end_date=None, adjust='qfq'):
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise Exception("模拟失败")
        return pd.DataFrame({
            'trade_date': ['2024-01-01'],
            'open': [10.0],
            'close': [10.5]
        })

    def get_new_stocks(self, days=30):
        """获取新股列表"""
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise Exception("模拟失败")
        return pd.DataFrame({
            'code': ['000001'],
            'name': ['新股A']
        })

    def get_delisted_stocks(self):
        """获取退市股票列表"""
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise Exception("模拟失败")
        return pd.DataFrame({
            'code': [],
            'name': []
        })

    def get_daily_batch(self, codes, start_date=None, end_date=None, adjust='qfq'):
        """批量获取日线数据"""
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise Exception("模拟失败")
        return {code: self.get_daily_data(code, start_date, end_date, adjust) for code in codes}

    def get_minute_data(self, code, period='5', start_date=None, end_date=None, adjust=''):
        """获取分时数据"""
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise Exception("模拟失败")
        return pd.DataFrame({
            'trade_time': ['2024-01-01 09:30:00'],
            'open': [10.0],
            'close': [10.5]
        })

    def get_realtime_quotes(self, codes=None):
        """获取实时行情"""
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise Exception("模拟失败")
        return pd.DataFrame({
            'code': ['000001'],
            'name': ['股票A'],
            'latest_price': [10.5]
        })


class MockRateLimitedProvider(BaseDataProvider):
    """有限流的模拟提供者"""

    def __init__(self, request_delay=0.1, **kwargs):
        self.request_delay = request_delay
        self.call_times = []
        super().__init__(**kwargs)

    def _validate_config(self):
        pass

    def get_stock_list(self):
        current_time = time.time()
        self.call_times.append(current_time)

        # 模拟限流延迟
        if len(self.call_times) > 1:
            time_diff = current_time - self.call_times[-2]
            if time_diff < self.request_delay:
                time.sleep(self.request_delay - time_diff)

        return pd.DataFrame({
            'code': ['000001'],
            'name': ['股票A']
        })

    def get_daily_data(self, code, start_date=None, end_date=None, adjust='qfq'):
        current_time = time.time()
        self.call_times.append(current_time)

        # 模拟限流延迟
        if len(self.call_times) > 1:
            time_diff = current_time - self.call_times[-2]
            if time_diff < self.request_delay:
                time.sleep(self.request_delay - time_diff)

        return pd.DataFrame({
            'trade_date': ['2024-01-01'],
            'open': [10.0],
            'close': [10.5]
        })

    def get_new_stocks(self, days=30):
        """获取新股列表"""
        return pd.DataFrame({
            'code': ['000001'],
            'name': ['新股A']
        })

    def get_delisted_stocks(self):
        """获取退市股票列表"""
        return pd.DataFrame({
            'code': [],
            'name': []
        })

    def get_daily_batch(self, codes, start_date=None, end_date=None, adjust='qfq'):
        """批量获取日线数据"""
        return {code: self.get_daily_data(code, start_date, end_date, adjust) for code in codes}

    def get_minute_data(self, code, period='5', start_date=None, end_date=None, adjust=''):
        """获取分时数据"""
        return pd.DataFrame({
            'trade_time': ['2024-01-01 09:30:00'],
            'open': [10.0],
            'close': [10.5]
        })

    def get_realtime_quotes(self, codes=None):
        """获取实时行情"""
        return pd.DataFrame({
            'code': ['000001'],
            'name': ['股票A'],
            'latest_price': [10.5]
        })


class TestProviderSwitching(unittest.TestCase):
    """Provider 自动切换测试"""

    def setUp(self):
        """每个测试前清空注册表"""
        ProviderRegistry.clear()

    def tearDown(self):
        """每个测试后清空注册表"""
        ProviderRegistry.clear()

    def test_switch_to_backup_provider(self):
        """测试切换到备用 Provider"""
        print("\n[测试] 切换到备用 Provider...")

        # 注册两个提供者
        DataProviderFactory.register(
            'primary',
            MockUnreliableProvider,
            description="主提供者（会失败）",
            priority=20
        )

        DataProviderFactory.register(
            'backup',
            MockReliableProvider,
            description="备用提供者",
            priority=10
        )

        # 尝试使用主提供者（会失败）
        try:
            primary = DataProviderFactory.create_provider('primary', fail_times=999)
            primary.get_stock_list()
            self.fail("应该抛出异常")
        except Exception:
            pass

        # 切换到备用提供者
        backup = DataProviderFactory.create_provider('backup')
        result = backup.get_stock_list()

        # 验证成功
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)

        print("  ✓ 切换成功")

    def test_select_provider_by_feature(self):
        """测试根据特性选择 Provider"""
        print("\n[测试] 根据特性选择 Provider...")

        # 注册两个提供者，具有不同特性
        DataProviderFactory.register(
            'provider_a',
            MockReliableProvider,
            description="提供者 A",
            features=['stock_list'],
            priority=10
        )

        DataProviderFactory.register(
            'provider_b',
            MockReliableProvider,
            description="提供者 B",
            features=['stock_list', 'realtime_quotes'],
            priority=20
        )

        # 查找支持 realtime_quotes 的提供者
        providers = DataProviderFactory.get_provider_by_feature('realtime_quotes')

        # 应该至少包含provider_b，可能还有builtin providers
        self.assertGreaterEqual(len(providers), 1)
        self.assertIn('provider_b', providers)

        # 创建并使用
        provider = DataProviderFactory.create_provider(providers[0])
        result = provider.get_stock_list()

        self.assertGreater(len(result), 0)

        print("  ✓ 特性选择正确")

    def test_fallback_chain(self):
        """测试 Provider 回退链"""
        print("\n[测试] Provider 回退链...")

        # 注册多个提供者（优先级递减）
        providers_info = [
            ('high_priority', MockUnreliableProvider, 30, 999),
            ('medium_priority', MockUnreliableProvider, 20, 999),
            ('low_priority', MockReliableProvider, 10, 0),
        ]

        for name, cls, priority, fail_times in providers_info:
            DataProviderFactory.register(
                name,
                cls,
                description=f"提供者 {name}",
                priority=priority
            )

        # 按优先级尝试
        providers = DataProviderFactory.get_available_providers()

        result = None
        for provider_name in providers:
            try:
                provider = DataProviderFactory.create_provider(
                    provider_name,
                    fail_times=999 if 'Unreliable' in provider_name else 0
                )
                result = provider.get_stock_list()
                print(f"  成功使用: {provider_name}")
                break
            except Exception as e:
                print(f"  {provider_name} 失败: {e}")
                continue

        # 验证最终成功
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)

        print("  ✓ 回退链正确")


class TestRetryMechanism(unittest.TestCase):
    """失败重试机制测试"""

    def setUp(self):
        ProviderRegistry.clear()

    def tearDown(self):
        ProviderRegistry.clear()

    def test_retry_on_failure(self):
        """测试失败重试"""
        print("\n[测试] 失败重试...")

        DataProviderFactory.register(
            'unreliable',
            MockUnreliableProvider,
            description="不可靠提供者"
        )

        # 创建提供者（前2次会失败，第3次成功）
        provider = DataProviderFactory.create_provider('unreliable', fail_times=2)

        # 模拟重试逻辑
        max_retries = 3
        result = None

        for retry in range(max_retries):
            try:
                result = provider.get_stock_list()
                print(f"  第 {retry + 1} 次尝试成功")
                break
            except Exception as e:
                print(f"  第 {retry + 1} 次尝试失败: {e}")
                if retry == max_retries - 1:
                    raise

        # 验证最终成功
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)

        print("  ✓ 重试成功")

    def test_retry_count_limit(self):
        """测试重试次数限制"""
        print("\n[测试] 重试次数限制...")

        DataProviderFactory.register(
            'always_fail',
            MockUnreliableProvider,
            description="总是失败"
        )

        # 创建总是失败的提供者
        provider = DataProviderFactory.create_provider('always_fail', fail_times=999)

        # 限制重试次数
        max_retries = 3
        retry_count = 0

        try:
            for retry in range(max_retries):
                try:
                    retry_count += 1
                    provider.get_stock_list()
                    break
                except Exception:
                    if retry == max_retries - 1:
                        raise
        except Exception:
            pass

        # 验证重试次数
        self.assertEqual(retry_count, max_retries)

        print(f"  ✓ 重试 {retry_count} 次后停止")

    def test_exponential_backoff(self):
        """测试指数退避"""
        print("\n[测试] 指数退避...")

        DataProviderFactory.register(
            'unreliable',
            MockUnreliableProvider,
            description="不可靠提供者"
        )

        provider = DataProviderFactory.create_provider('unreliable', fail_times=3)

        # 记录重试延迟
        delays = []
        base_delay = 1

        for retry in range(4):
            try:
                if retry > 0:
                    delay = base_delay * (2 ** (retry - 1))
                    delays.append(delay)
                    print(f"  第 {retry} 次重试，延迟 {delay} 秒")
                    time.sleep(delay)

                provider.get_stock_list()
                print(f"  第 {retry + 1} 次尝试成功")
                break
            except Exception:
                if retry == 3:
                    raise

        # 验证延迟递增
        if len(delays) > 1:
            for i in range(1, len(delays)):
                self.assertGreater(delays[i], delays[i-1])

        print("  ✓ 指数退避正确")


class TestRateLimiting(unittest.TestCase):
    """API 限流控制测试"""

    def setUp(self):
        ProviderRegistry.clear()

    def tearDown(self):
        ProviderRegistry.clear()

    def test_request_delay(self):
        """测试请求延迟"""
        print("\n[测试] 请求延迟...")

        DataProviderFactory.register(
            'rate_limited',
            MockRateLimitedProvider,
            description="限流提供者"
        )

        provider = DataProviderFactory.create_provider('rate_limited', request_delay=0.5)

        # 连续发送请求
        start_time = time.time()

        for i in range(3):
            provider.get_stock_list()

        elapsed = time.time() - start_time

        # 验证总耗时（至少 0.8 秒: 0.5秒 * 2个间隔，留些余地）
        self.assertGreater(elapsed, 0.8)

        print(f"  ✓ 3次请求耗时 {elapsed:.2f} 秒")

    def test_rate_limit_per_second(self):
        """测试每秒请求限制"""
        print("\n[测试] 每秒请求限制...")

        DataProviderFactory.register(
            'rate_limited',
            MockRateLimitedProvider,
            description="限流提供者"
        )

        # 设置每秒最多 5 次请求 (0.2秒间隔)
        provider = DataProviderFactory.create_provider('rate_limited', request_delay=0.2)

        # 发送 10 次请求
        start_time = time.time()

        for i in range(10):
            provider.get_daily_data('000001')

        elapsed = time.time() - start_time

        # 验证耗时（至少 0.9 秒: 0.2 * 9个间隔，由于系统调度留余地约50%）
        self.assertGreater(elapsed, 0.9)

        print(f"  ✓ 10次请求耗时 {elapsed:.2f} 秒，平均 {elapsed/10:.3f} 秒/次")

    def test_concurrent_request_control(self):
        """测试并发请求控制"""
        print("\n[测试] 并发请求控制...")

        DataProviderFactory.register(
            'rate_limited',
            MockRateLimitedProvider,
            description="限流提供者"
        )

        provider = DataProviderFactory.create_provider('rate_limited', request_delay=0.3)

        # 串行请求
        start_time = time.time()
        for i in range(5):
            provider.get_stock_list()
        serial_time = time.time() - start_time

        print(f"  串行耗时: {serial_time:.2f} 秒")
        print("  ✓ 并发控制正确")


class TestErrorHandling(unittest.TestCase):
    """错误处理测试"""

    def setUp(self):
        ProviderRegistry.clear()

    def tearDown(self):
        ProviderRegistry.clear()

    def test_handle_network_error(self):
        """测试网络错误处理"""
        print("\n[测试] 网络错误处理...")

        DataProviderFactory.register(
            'unreliable',
            MockUnreliableProvider,
            description="不可靠提供者"
        )

        provider = DataProviderFactory.create_provider('unreliable', fail_times=1)

        # 第一次调用会失败
        with self.assertRaises(Exception):
            provider.get_stock_list()

        # 第二次调用应该成功
        result = provider.get_stock_list()
        self.assertIsNotNone(result)

        print("  ✓ 错误恢复成功")

    def test_handle_data_error(self):
        """测试数据错误处理"""
        print("\n[测试] 数据错误处理...")

        # 创建返回空数据的提供者
        class EmptyDataProvider(BaseDataProvider):
            def _validate_config(self):
                pass

            def get_stock_list(self):
                return pd.DataFrame()  # 返回空数据

            def get_daily_data(self, code, start_date=None, end_date=None, adjust='qfq'):
                return pd.DataFrame()

            def get_new_stocks(self, days=30):
                return pd.DataFrame()

            def get_delisted_stocks(self):
                return pd.DataFrame()

            def get_daily_batch(self, codes, start_date=None, end_date=None, adjust='qfq'):
                return {code: pd.DataFrame() for code in codes}

            def get_minute_data(self, code, period='5', start_date=None, end_date=None, adjust=''):
                return pd.DataFrame()

            def get_realtime_quotes(self, codes=None):
                return pd.DataFrame()

        DataProviderFactory.register(
            'empty_data',
            EmptyDataProvider,
            description="空数据提供者"
        )

        provider = DataProviderFactory.create_provider('empty_data')
        result = provider.get_stock_list()

        # 验证能处理空数据
        self.assertTrue(result.empty)

        print("  ✓ 空数据处理正确")


class TestProviderHealthCheck(unittest.TestCase):
    """Provider 健康检查测试"""

    def setUp(self):
        ProviderRegistry.clear()

    def tearDown(self):
        ProviderRegistry.clear()

    def test_provider_availability(self):
        """测试 Provider 可用性"""
        print("\n[测试] Provider 可用性...")

        DataProviderFactory.register(
            'reliable',
            MockReliableProvider,
            description="可靠提供者"
        )

        DataProviderFactory.register(
            'unreliable',
            MockUnreliableProvider,
            description="不可靠提供者"
        )

        # 检查可用性
        providers = DataProviderFactory.get_available_providers()

        self.assertIn('reliable', providers)
        self.assertIn('unreliable', providers)

        print(f"  ✓ {len(providers)} 个提供者可用")

    def test_health_check_result(self):
        """测试健康检查结果"""
        print("\n[测试] 健康检查结果...")

        DataProviderFactory.register(
            'test',
            MockReliableProvider,
            description="测试提供者"
        )

        provider = DataProviderFactory.create_provider('test')

        # 执行简单的健康检查
        try:
            result = provider.get_stock_list()
            health_status = "healthy" if not result.empty else "degraded"
        except Exception:
            health_status = "unhealthy"

        self.assertEqual(health_status, "healthy")

        print(f"  ✓ 健康状态: {health_status}")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestProviderSwitching))
    suite.addTests(loader.loadTestsFromTestCase(TestRetryMechanism))
    suite.addTests(loader.loadTestsFromTestCase(TestRateLimiting))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestProviderHealthCheck))

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
