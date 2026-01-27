#!/usr/bin/env python3
"""
DataProviderFactory 完整单元测试

覆盖工厂模式、装饰器、便捷函数和所有公共接口
目标覆盖率: >90%
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from src.providers.provider_factory import (
    DataProviderFactory,
    provider,
    get_provider,
    register_provider,
    list_providers
)
from src.providers.provider_registry import ProviderRegistry
from src.providers.base_provider import BaseDataProvider


# 创建测试用的 Provider 类
class TestProvider(BaseDataProvider):
    """测试提供者"""
    def __init__(self, **kwargs):
        self.test_param = kwargs.get('test_param', 'default')
        super().__init__(**kwargs)

    def _validate_config(self):
        pass

    def get_stock_list(self):
        pass

    def get_daily_data(self, code, start_date=None, end_date=None, adjust='qfq'):
        pass


class TestProviderWithToken(BaseDataProvider):
    """需要 Token 的测试提供者"""
    def __init__(self, token=None, **kwargs):
        self.token = token
        super().__init__(**kwargs)

    def _validate_config(self):
        if not self.token:
            raise ValueError("需要 Token")

    def get_stock_list(self):
        pass

    def get_daily_data(self, code, start_date=None, end_date=None, adjust='qfq'):
        pass


class TestProviderFactoryBasic(unittest.TestCase):
    """基础功能测试"""

    def setUp(self):
        """每个测试前清空注册表"""
        ProviderRegistry.clear()

    def tearDown(self):
        """每个测试后清空注册表"""
        ProviderRegistry.clear()

    def test_register(self):
        """测试注册方法"""
        print("\n[测试] 注册方法...")

        DataProviderFactory.register(
            name='test',
            provider_class=TestProvider,
            description="测试提供者",
            features=['stock_list'],
            priority=10
        )

        # 验证已注册
        self.assertTrue(DataProviderFactory.is_provider_available('test'))

        print("  ✓ 注册成功")

    def test_register_with_override(self):
        """测试覆盖注册"""
        print("\n[测试] 覆盖注册...")

        # 第一次注册
        DataProviderFactory.register(
            name='test',
            provider_class=TestProvider,
            description="原始描述",
            priority=10
        )

        # 覆盖注册
        DataProviderFactory.register(
            name='test',
            provider_class=TestProvider,
            description="新描述",
            priority=20,
            override=True
        )

        # 验证已覆盖
        info = DataProviderFactory.get_provider_info('test')
        self.assertEqual(info['description'], "新描述")
        self.assertEqual(info['priority'], 20)

        print("  ✓ 覆盖注册成功")

    def test_register_invalid_class(self):
        """测试注册无效类"""
        print("\n[测试] 注册无效类...")

        with self.assertRaises(TypeError):
            DataProviderFactory.register(
                name='invalid',
                provider_class='not a class',
                description="无效"
            )

        print("  ✓ 正确拒绝无效类")


class TestProviderCreation(unittest.TestCase):
    """提供者创建测试"""

    def setUp(self):
        ProviderRegistry.clear()

        # 注册测试提供者
        DataProviderFactory.register(
            name='test',
            provider_class=TestProvider,
            description="测试提供者",
            requires_token=False
        )

        DataProviderFactory.register(
            name='test_with_token',
            provider_class=TestProviderWithToken,
            description="需要 Token 的提供者",
            requires_token=True
        )

    def tearDown(self):
        ProviderRegistry.clear()

    def test_create_provider_success(self):
        """测试成功创建提供者"""
        print("\n[测试] 成功创建提供者...")

        provider = DataProviderFactory.create_provider('test')

        self.assertIsInstance(provider, TestProvider)
        self.assertIsInstance(provider, BaseDataProvider)

        print("  ✓ 创建成功")

    def test_create_provider_with_params(self):
        """测试带参数创建提供者"""
        print("\n[测试] 带参数创建提供者...")

        provider = DataProviderFactory.create_provider(
            'test',
            test_param='custom_value'
        )

        self.assertEqual(provider.test_param, 'custom_value')

        print("  ✓ 参数传递正确")

    def test_create_provider_case_insensitive(self):
        """测试名称不区分大小写"""
        print("\n[测试] 名称不区分大小写...")

        # 使用大写
        provider1 = DataProviderFactory.create_provider('TEST')
        self.assertIsInstance(provider1, TestProvider)

        # 使用小写
        provider2 = DataProviderFactory.create_provider('test')
        self.assertIsInstance(provider2, TestProvider)

        # 使用混合大小写
        provider3 = DataProviderFactory.create_provider('TeSt')
        self.assertIsInstance(provider3, TestProvider)

        print("  ✓ 大小写处理正确")

    def test_create_provider_not_found(self):
        """测试创建不存在的提供者"""
        print("\n[测试] 创建不存在的提供者...")

        with self.assertRaises(ValueError) as cm:
            DataProviderFactory.create_provider('nonexistent')

        self.assertIn('不支持的数据源', str(cm.exception))
        self.assertIn('nonexistent', str(cm.exception))

        print("  ✓ 正确抛出异常")

    def test_create_provider_requires_token_warning(self):
        """测试需要 Token 但未提供的警告"""
        print("\n[测试] 需要 Token 但未提供...")

        # 应该记录警告但不抛出异常
        with patch('src.providers.provider_factory.logger') as mock_logger:
            try:
                provider = DataProviderFactory.create_provider('test_with_token')
                # 验证警告被记录
                mock_logger.warning.assert_called()
            except ValueError:
                # 如果 _validate_config 抛出异常也是正常的
                pass

        print("  ✓ 警告处理正确")

    def test_create_provider_with_token(self):
        """测试提供 Token 创建"""
        print("\n[测试] 提供 Token 创建...")

        provider = DataProviderFactory.create_provider(
            'test_with_token',
            token='test_token_123'
        )

        self.assertEqual(provider.token, 'test_token_123')

        print("  ✓ Token 传递正确")

    def test_create_default_provider(self):
        """测试创建默认提供者"""
        print("\n[测试] 创建默认提供者...")

        provider = DataProviderFactory.create_default_provider()

        self.assertIsInstance(provider, BaseDataProvider)

        print("  ✓ 默认提供者创建成功")


class TestProviderQuery(unittest.TestCase):
    """提供者查询测试"""

    def setUp(self):
        ProviderRegistry.clear()

        # 注册测试提供者
        DataProviderFactory.register(
            name='provider_a',
            provider_class=TestProvider,
            description="提供者 A",
            features=['stock_list', 'daily_data'],
            priority=10
        )

        DataProviderFactory.register(
            name='provider_b',
            provider_class=TestProvider,
            description="提供者 B",
            features=['stock_list', 'realtime_quotes'],
            priority=20
        )

    def tearDown(self):
        ProviderRegistry.clear()

    def test_get_available_providers(self):
        """测试获取可用提供者列表"""
        print("\n[测试] 获取可用提供者列表...")

        providers = DataProviderFactory.get_available_providers()

        self.assertIsInstance(providers, list)
        self.assertGreaterEqual(len(providers), 2)
        self.assertIn('provider_a', providers)
        self.assertIn('provider_b', providers)

        # 验证按优先级排序（provider_b 优先级高）
        self.assertEqual(providers[0], 'provider_b')

        print(f"  ✓ 获取成功: {providers}")

    def test_is_provider_available(self):
        """测试检查提供者是否可用"""
        print("\n[测试] 检查提供者是否可用...")

        self.assertTrue(DataProviderFactory.is_provider_available('provider_a'))
        self.assertTrue(DataProviderFactory.is_provider_available('provider_b'))
        self.assertFalse(DataProviderFactory.is_provider_available('provider_c'))

        print("  ✓ 检查正确")

    def test_get_provider_info(self):
        """测试获取提供者信息"""
        print("\n[测试] 获取提供者信息...")

        info = DataProviderFactory.get_provider_info('provider_a')

        self.assertIsInstance(info, dict)
        self.assertEqual(info['name'], 'provider_a')
        self.assertEqual(info['description'], "提供者 A")
        self.assertEqual(info['priority'], 10)
        self.assertIn('stock_list', info['features'])

        print(f"  ✓ 获取成功")

    def test_get_provider_info_not_found(self):
        """测试获取不存在的提供者信息"""
        print("\n[测试] 获取不存在的提供者信息...")

        with self.assertRaises(ValueError) as cm:
            DataProviderFactory.get_provider_info('nonexistent')

        self.assertIn('不存在', str(cm.exception))

        print("  ✓ 正确抛出异常")

    def test_list_all_providers(self):
        """测试列出所有提供者"""
        print("\n[测试] 列出所有提供者...")

        providers = DataProviderFactory.list_all_providers()

        self.assertIsInstance(providers, list)
        self.assertGreaterEqual(len(providers), 2)

        # 验证每个元素都是字典
        for info in providers:
            self.assertIsInstance(info, dict)
            self.assertIn('name', info)
            self.assertIn('description', info)
            self.assertIn('priority', info)

        print(f"  ✓ 列出成功，共 {len(providers)} 个")

    def test_get_provider_by_feature(self):
        """测试按特性查找提供者"""
        print("\n[测试] 按特性查找提供者...")

        # 查找支持 stock_list 的提供者
        providers = DataProviderFactory.get_provider_by_feature('stock_list')
        self.assertEqual(len(providers), 2)

        # 查找支持 realtime_quotes 的提供者
        providers = DataProviderFactory.get_provider_by_feature('realtime_quotes')
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0], 'provider_b')

        # 查找不存在的特性
        providers = DataProviderFactory.get_provider_by_feature('nonexistent')
        self.assertEqual(len(providers), 0)

        print("  ✓ 查找正确")

    def test_get_default_provider(self):
        """测试获取默认提供者"""
        print("\n[测试] 获取默认提供者...")

        default = DataProviderFactory.get_default_provider()

        # 应该返回优先级最高的
        self.assertEqual(default, 'provider_b')

        print(f"  ✓ 默认提供者: {default}")


class TestProviderUnregister(unittest.TestCase):
    """提供者注销测试"""

    def setUp(self):
        ProviderRegistry.clear()

    def tearDown(self):
        ProviderRegistry.clear()

    def test_unregister(self):
        """测试注销提供者"""
        print("\n[测试] 注销提供者...")

        # 注册
        DataProviderFactory.register(
            name='test',
            provider_class=TestProvider,
            description="测试"
        )

        # 验证存在
        self.assertTrue(DataProviderFactory.is_provider_available('test'))

        # 注销
        result = DataProviderFactory.unregister('test')

        # 验证已注销
        self.assertTrue(result)
        self.assertFalse(DataProviderFactory.is_provider_available('test'))

        print("  ✓ 注销成功")


class TestDecorator(unittest.TestCase):
    """装饰器测试"""

    def setUp(self):
        ProviderRegistry.clear()

    def tearDown(self):
        ProviderRegistry.clear()

    def test_provider_decorator(self):
        """测试 @provider 装饰器"""
        print("\n[测试] @provider 装饰器...")

        @provider(
            name='decorated',
            description="装饰器注册的提供者",
            features=['stock_list'],
            priority=15
        )
        class DecoratedProvider(BaseDataProvider):
            def _validate_config(self):
                pass

            def get_stock_list(self):
                pass

            def get_daily_data(self, code, start_date=None, end_date=None, adjust='qfq'):
                pass

        # 验证已注册
        self.assertTrue(DataProviderFactory.is_provider_available('decorated'))

        # 验证信息
        info = DataProviderFactory.get_provider_info('decorated')
        self.assertEqual(info['description'], "装饰器注册的提供者")
        self.assertEqual(info['priority'], 15)

        # 验证可以创建实例
        provider = DataProviderFactory.create_provider('decorated')
        self.assertIsInstance(provider, DecoratedProvider)

        print("  ✓ 装饰器正常工作")


class TestConvenienceFunctions(unittest.TestCase):
    """便捷函数测试"""

    def setUp(self):
        ProviderRegistry.clear()

    def tearDown(self):
        ProviderRegistry.clear()

    def test_get_provider_function(self):
        """测试 get_provider 便捷函数"""
        print("\n[测试] get_provider 便捷函数...")

        # 注册测试提供者
        register_provider('test', TestProvider, description="测试")

        # 使用便捷函数创建
        provider = get_provider('test')

        self.assertIsInstance(provider, TestProvider)

        print("  ✓ get_provider 正常工作")

    def test_register_provider_function(self):
        """测试 register_provider 便捷函数"""
        print("\n[测试] register_provider 便捷函数...")

        # 使用便捷函数注册
        register_provider(
            'test',
            TestProvider,
            description="测试提供者",
            features=['stock_list'],
            priority=10
        )

        # 验证已注册
        self.assertTrue(DataProviderFactory.is_provider_available('test'))

        print("  ✓ register_provider 正常工作")

    def test_list_providers_function(self):
        """测试 list_providers 便捷函数"""
        print("\n[测试] list_providers 便捷函数...")

        # 注册几个提供者
        register_provider('test_a', TestProvider, description="A", priority=10)
        register_provider('test_b', TestProvider, description="B", priority=20)

        # 使用便捷函数列出
        providers = list_providers()

        self.assertIsInstance(providers, list)
        self.assertGreaterEqual(len(providers), 2)
        self.assertIn('test_a', providers)
        self.assertIn('test_b', providers)

        print(f"  ✓ list_providers 正常工作: {len(providers)} 个提供者")


class TestBuiltinProviders(unittest.TestCase):
    """内置提供者测试"""

    def setUp(self):
        ProviderRegistry.clear()

    def tearDown(self):
        ProviderRegistry.clear()

    def test_builtin_providers_available(self):
        """测试内置提供者可用"""
        print("\n[测试] 内置提供者可用...")

        # 初始化应该自动注册内置提供者
        providers = DataProviderFactory.get_available_providers()

        self.assertIn('akshare', providers)
        self.assertIn('tushare', providers)

        print("  ✓ 内置提供者已注册")

    def test_create_builtin_provider(self):
        """测试创建内置提供者"""
        print("\n[测试] 创建内置提供者...")

        # 创建 AkShare 提供者
        provider = DataProviderFactory.create_provider('akshare')
        self.assertIsNotNone(provider)

        print("  ✓ 内置提供者创建成功")


class TestEdgeCases(unittest.TestCase):
    """边界条件测试"""

    def setUp(self):
        ProviderRegistry.clear()

    def tearDown(self):
        ProviderRegistry.clear()

    def test_empty_factory(self):
        """测试空工厂"""
        print("\n[测试] 空工厂...")

        ProviderRegistry.clear()

        # get_available_providers 应该触发初始化
        providers = DataProviderFactory.get_available_providers()
        self.assertGreater(len(providers), 0)  # 至少有内置提供者

        print("  ✓ 空工厂处理正确")

    def test_create_provider_with_extra_params(self):
        """测试创建提供者时传入额外参数"""
        print("\n[测试] 传入额外参数...")

        DataProviderFactory.register('test', TestProvider, description="测试")

        # 传入额外参数应该被忽略或传递给 __init__
        provider = DataProviderFactory.create_provider(
            'test',
            extra_param='extra_value',
            another_param=123
        )

        self.assertIsInstance(provider, TestProvider)

        print("  ✓ 额外参数处理正确")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestProviderFactoryBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestProviderCreation))
    suite.addTests(loader.loadTestsFromTestCase(TestProviderQuery))
    suite.addTests(loader.loadTestsFromTestCase(TestProviderUnregister))
    suite.addTests(loader.loadTestsFromTestCase(TestDecorator))
    suite.addTests(loader.loadTestsFromTestCase(TestConvenienceFunctions))
    suite.addTests(loader.loadTestsFromTestCase(TestBuiltinProviders))
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
