#!/usr/bin/env python3
"""
ProviderConfigManager 完整单元测试

覆盖提供者配置管理的所有功能
目标覆盖率: >90%
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))

from src.config.providers import (
    ProviderConfigManager,
    get_provider_config_manager,
    get_current_provider,
    get_current_provider_config,
    get_tushare_config,
    get_akshare_config
)


class TestProviderConfigManager(unittest.TestCase):
    """ProviderConfigManager 测试"""

    def setUp(self):
        """每个测试前重置单例"""
        import src.config.providers
        src.config.providers._provider_config_manager = None

    def test_init(self):
        """测试初始化"""
        print("\n[测试] 初始化...")

        manager = ProviderConfigManager()
        self.assertIsNotNone(manager.settings)
        self.assertIsInstance(manager._configs, dict)

        print("  ✓ 初始化成功")

    @patch('src.config.providers.get_settings')
    def test_get_provider_name(self, mock_get_settings):
        """测试获取提供者名称"""
        print("\n[测试] 获取提供者名称...")

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'akshare'
        mock_get_settings.return_value = mock_settings

        manager = ProviderConfigManager()
        provider_name = manager.get_provider_name()

        self.assertEqual(provider_name, 'akshare')

        print(f"  ✓ 提供者名称: {provider_name}")

    def test_get_tushare_config(self):
        """测试获取 Tushare 配置"""
        print("\n[测试] 获取 Tushare 配置...")

        manager = ProviderConfigManager()
        config = manager.get_tushare_config()

        # 验证配置内容
        self.assertIsInstance(config, dict)
        self.assertIn('token', config)
        self.assertIn('timeout', config)
        self.assertIn('retry_count', config)
        self.assertIn('retry_delay', config)
        self.assertIn('request_delay', config)
        self.assertIn('config_class', config)
        self.assertIn('error_messages', config)
        self.assertIn('fields', config)

        print("  ✓ Tushare 配置获取成功")

    def test_get_akshare_config(self):
        """测试获取 AkShare 配置"""
        print("\n[测试] 获取 AkShare 配置...")

        manager = ProviderConfigManager()
        config = manager.get_akshare_config()

        # 验证配置内容
        self.assertIsInstance(config, dict)
        self.assertIn('timeout', config)
        self.assertIn('retry_count', config)
        self.assertIn('retry_delay', config)
        self.assertIn('request_delay', config)
        self.assertIn('config_class', config)
        self.assertIn('fields', config)
        self.assertIn('notes', config)

        # AkShare 不需要 token
        self.assertNotIn('token', config)

        print("  ✓ AkShare 配置获取成功")

    def test_config_cache(self):
        """测试配置缓存"""
        print("\n[测试] 配置缓存...")

        manager = ProviderConfigManager()

        # 第一次获取
        config1 = manager.get_tushare_config()

        # 第二次获取应该返回缓存的配置
        config2 = manager.get_tushare_config()

        # 应该是同一个对象
        self.assertIs(config1, config2)

        print("  ✓ 配置缓存正确")

    @patch('src.config.providers.get_settings')
    def test_get_current_provider_config_tushare(self, mock_get_settings):
        """测试获取当前配置（Tushare）"""
        print("\n[测试] 获取当前配置（Tushare）...")

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'tushare'
        mock_get_settings.return_value = mock_settings

        manager = ProviderConfigManager()
        config = manager.get_current_provider_config()

        # 应该返回 Tushare 配置
        self.assertIn('token', config)
        self.assertIn('error_messages', config)

        print("  ✓ 当前配置获取成功（Tushare）")

    @patch('src.config.providers.get_settings')
    def test_get_current_provider_config_akshare(self, mock_get_settings):
        """测试获取当前配置（AkShare）"""
        print("\n[测试] 获取当前配置（AkShare）...")

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'akshare'
        mock_get_settings.return_value = mock_settings

        manager = ProviderConfigManager()
        config = manager.get_current_provider_config()

        # 应该返回 AkShare 配置
        self.assertIn('notes', config)
        self.assertNotIn('token', config)

        print("  ✓ 当前配置获取成功（AkShare）")

    @patch('src.config.providers.get_settings')
    def test_get_current_provider_config_unsupported(self, mock_get_settings):
        """测试不支持的提供者"""
        print("\n[测试] 不支持的提供者...")

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'unsupported'
        mock_get_settings.return_value = mock_settings

        manager = ProviderConfigManager()

        with self.assertRaises(ValueError) as cm:
            manager.get_current_provider_config()

        self.assertIn('不支持的数据提供者', str(cm.exception))

        print("  ✓ 正确抛出异常")

    @patch('src.config.providers.get_settings')
    def test_has_tushare_token(self, mock_get_settings):
        """测试检查 Tushare Token"""
        print("\n[测试] 检查 Tushare Token...")

        # Mock settings with token
        mock_settings = MagicMock()
        mock_settings.data_source.has_tushare = True
        mock_get_settings.return_value = mock_settings

        manager = ProviderConfigManager()
        has_token = manager.has_tushare_token()

        self.assertTrue(has_token)

        # Mock settings without token
        mock_settings.data_source.has_tushare = False
        has_token = manager.has_tushare_token()

        self.assertFalse(has_token)

        print("  ✓ Token 检查正确")

    def test_get_provider_info_tushare(self):
        """测试获取 Tushare 信息"""
        print("\n[测试] 获取 Tushare 信息...")

        manager = ProviderConfigManager()
        info = manager.get_provider_info('tushare')

        self.assertIsInstance(info, dict)
        self.assertEqual(info['name'], 'Tushare Pro')
        self.assertIn('description', info)
        self.assertIn('has_token', info)
        self.assertFalse(info['free'])
        self.assertEqual(info['data_quality'], 'high')

        print("  ✓ Tushare 信息获取成功")

    def test_get_provider_info_akshare(self):
        """测试获取 AkShare 信息"""
        print("\n[测试] 获取 AkShare 信息...")

        manager = ProviderConfigManager()
        info = manager.get_provider_info('akshare')

        self.assertIsInstance(info, dict)
        self.assertEqual(info['name'], 'AkShare')
        self.assertIn('description', info)
        self.assertTrue(info['free'])
        self.assertEqual(info['data_quality'], 'medium')
        self.assertEqual(info['rate_limit'], 'ip_based')

        print("  ✓ AkShare 信息获取成功")

    @patch('src.config.providers.get_settings')
    def test_get_provider_info_current(self, mock_get_settings):
        """测试获取当前提供者信息"""
        print("\n[测试] 获取当前提供者信息...")

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'akshare'
        mock_get_settings.return_value = mock_settings

        manager = ProviderConfigManager()
        info = manager.get_provider_info()  # None = 当前提供者

        self.assertEqual(info['name'], 'AkShare')

        print("  ✓ 当前提供者信息获取成功")

    def test_get_provider_info_unknown(self):
        """测试获取未知提供者信息"""
        print("\n[测试] 获取未知提供者信息...")

        manager = ProviderConfigManager()

        with self.assertRaises(ValueError) as cm:
            manager.get_provider_info('unknown')

        self.assertIn('未知的数据提供者', str(cm.exception))

        print("  ✓ 正确抛出异常")


class TestSingletonBehavior(unittest.TestCase):
    """单例行为测试"""

    def setUp(self):
        """每个测试前重置单例"""
        import src.config.providers
        src.config.providers._provider_config_manager = None

    def test_singleton(self):
        """测试单例模式"""
        print("\n[测试] 单例模式...")

        manager1 = get_provider_config_manager()
        manager2 = get_provider_config_manager()

        # 应该是同一个实例
        self.assertIs(manager1, manager2)

        print("  ✓ 单例模式正确")


class TestConvenienceFunctions(unittest.TestCase):
    """便捷函数测试"""

    def setUp(self):
        """每个测试前重置单例"""
        import src.config.providers
        src.config.providers._provider_config_manager = None

    @patch('src.config.providers.get_settings')
    def test_get_current_provider_function(self, mock_get_settings):
        """测试 get_current_provider 便捷函数"""
        print("\n[测试] get_current_provider 便捷函数...")

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'akshare'
        mock_get_settings.return_value = mock_settings

        provider = get_current_provider()

        self.assertEqual(provider, 'akshare')

        print(f"  ✓ 当前提供者: {provider}")

    @patch('src.config.providers.get_settings')
    def test_get_current_provider_config_function(self, mock_get_settings):
        """测试 get_current_provider_config 便捷函数"""
        print("\n[测试] get_current_provider_config 便捷函数...")

        # Mock settings
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'akshare'
        mock_get_settings.return_value = mock_settings

        config = get_current_provider_config()

        self.assertIsInstance(config, dict)
        self.assertIn('timeout', config)

        print("  ✓ 当前配置获取成功")

    def test_get_tushare_config_function(self):
        """测试 get_tushare_config 便捷函数"""
        print("\n[测试] get_tushare_config 便捷函数...")

        config = get_tushare_config()

        self.assertIsInstance(config, dict)
        self.assertIn('token', config)

        print("  ✓ Tushare 配置获取成功")

    def test_get_akshare_config_function(self):
        """测试 get_akshare_config 便捷函数"""
        print("\n[测试] get_akshare_config 便捷函数...")

        config = get_akshare_config()

        self.assertIsInstance(config, dict)
        self.assertIn('notes', config)

        print("  ✓ AkShare 配置获取成功")


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestProviderConfigManager))
    suite.addTests(loader.loadTestsFromTestCase(TestSingletonBehavior))
    suite.addTests(loader.loadTestsFromTestCase(TestConvenienceFunctions))

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
