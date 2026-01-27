#!/usr/bin/env python3
"""
config/providers.py 模块的完整测试套件

测试覆盖:
1. ProviderConfigManager 类的所有方法
2. 全局单例函数
3. 便捷函数
4. 配置缓存机制
5. 不同提供者的配置
6. 异常处理
"""

import pytest
from unittest.mock import patch, MagicMock


class TestProviderConfigManager:
    """测试 ProviderConfigManager 类"""

    def test_init(self):
        """测试初始化"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()

        assert manager.settings is not None
        assert manager._configs == {}

    def test_get_provider_name_default(self):
        """测试获取默认提供者名称"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        provider = manager.get_provider_name()

        assert provider in ['tushare', 'akshare']

    @patch('src.config.providers.get_settings')
    def test_get_provider_name_tushare(self, mock_get_settings):
        """测试获取 Tushare 提供者名称"""
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'tushare'
        mock_get_settings.return_value = mock_settings

        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        provider = manager.get_provider_name()

        assert provider == 'tushare'

    @patch('src.config.providers.get_settings')
    def test_get_provider_name_akshare(self, mock_get_settings):
        """测试获取 AkShare 提供者名称"""
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'akshare'
        mock_get_settings.return_value = mock_settings

        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        provider = manager.get_provider_name()

        assert provider == 'akshare'


class TestTushareConfig:
    """测试 Tushare 配置获取"""

    def test_get_tushare_config_structure(self):
        """测试 Tushare 配置结构"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        config = manager.get_tushare_config()

        # 验证配置包含所有必要字段
        assert 'token' in config
        assert 'timeout' in config
        assert 'retry_count' in config
        assert 'retry_delay' in config
        assert 'request_delay' in config
        assert 'config_class' in config
        assert 'error_messages' in config
        assert 'fields' in config

    def test_get_tushare_config_types(self):
        """测试 Tushare 配置类型"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        config = manager.get_tushare_config()

        # 验证类型
        assert isinstance(config['token'], str)
        assert isinstance(config['timeout'], (int, float))
        assert isinstance(config['retry_count'], int)
        assert isinstance(config['retry_delay'], (int, float))
        assert isinstance(config['request_delay'], (int, float))

    def test_get_tushare_config_caching(self):
        """测试 Tushare 配置缓存"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()

        # 第一次调用
        config1 = manager.get_tushare_config()

        # 第二次调用应该从缓存返回
        config2 = manager.get_tushare_config()

        assert config1 is config2

    def test_get_tushare_config_with_token(self):
        """测试带 Token 的 Tushare 配置"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        config = manager.get_tushare_config()

        # token 应该是字符串（可能为空）
        assert isinstance(config['token'], str)

    def test_get_tushare_config_constants(self):
        """测试 Tushare 配置常量"""
        from src.config.providers import ProviderConfigManager, TushareConfig

        manager = ProviderConfigManager()
        config = manager.get_tushare_config()

        # 验证配置常量来自 TushareConfig
        assert config['timeout'] == TushareConfig.DEFAULT_TIMEOUT
        assert config['retry_count'] == TushareConfig.DEFAULT_RETRY_COUNT
        assert config['retry_delay'] == TushareConfig.DEFAULT_RETRY_DELAY
        assert config['request_delay'] == TushareConfig.DEFAULT_REQUEST_DELAY


class TestAkShareConfig:
    """测试 AkShare 配置获取"""

    def test_get_akshare_config_structure(self):
        """测试 AkShare 配置结构"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        config = manager.get_akshare_config()

        # 验证配置包含所有必要字段
        assert 'timeout' in config
        assert 'retry_count' in config
        assert 'retry_delay' in config
        assert 'request_delay' in config
        assert 'config_class' in config
        assert 'fields' in config
        assert 'notes' in config

    def test_get_akshare_config_types(self):
        """测试 AkShare 配置类型"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        config = manager.get_akshare_config()

        # 验证类型
        assert isinstance(config['timeout'], (int, float))
        assert isinstance(config['retry_count'], int)
        assert isinstance(config['retry_delay'], (int, float))
        assert isinstance(config['request_delay'], (int, float))

    def test_get_akshare_config_caching(self):
        """测试 AkShare 配置缓存"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()

        # 第一次调用
        config1 = manager.get_akshare_config()

        # 第二次调用应该从缓存返回
        config2 = manager.get_akshare_config()

        assert config1 is config2

    def test_get_akshare_config_no_token(self):
        """测试 AkShare 配置不需要 Token"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        config = manager.get_akshare_config()

        # AkShare 不需要 token
        assert 'token' not in config

    def test_get_akshare_config_constants(self):
        """测试 AkShare 配置常量"""
        from src.config.providers import ProviderConfigManager, AkShareConfig

        manager = ProviderConfigManager()
        config = manager.get_akshare_config()

        # 验证配置常量来自 AkShareConfig
        assert config['timeout'] == AkShareConfig.DEFAULT_TIMEOUT
        assert config['retry_count'] == AkShareConfig.DEFAULT_RETRY_COUNT
        assert config['retry_delay'] == AkShareConfig.DEFAULT_RETRY_DELAY
        assert config['request_delay'] == AkShareConfig.DEFAULT_REQUEST_DELAY


class TestGetCurrentProviderConfig:
    """测试获取当前提供者配置"""

    @patch('src.config.providers.get_settings')
    def test_get_current_provider_config_tushare(self, mock_get_settings):
        """测试获取 Tushare 当前配置"""
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'tushare'
        mock_settings.data_source.tushare_token = 'test_token'
        mock_settings.data_source.has_tushare = True
        mock_get_settings.return_value = mock_settings

        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        config = manager.get_current_provider_config()

        # 应该返回 Tushare 配置
        assert 'token' in config
        assert config['token'] == 'test_token'

    @patch('src.config.providers.get_settings')
    def test_get_current_provider_config_akshare(self, mock_get_settings):
        """测试获取 AkShare 当前配置"""
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'akshare'
        mock_get_settings.return_value = mock_settings

        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        config = manager.get_current_provider_config()

        # 应该返回 AkShare 配置
        assert 'notes' in config
        assert 'token' not in config

    @patch('src.config.providers.get_settings')
    def test_get_current_provider_config_unsupported(self, mock_get_settings):
        """测试不支持的提供者"""
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'unknown_provider'
        mock_get_settings.return_value = mock_settings

        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()

        with pytest.raises(ValueError) as exc_info:
            manager.get_current_provider_config()

        assert '不支持的数据提供者' in str(exc_info.value)


class TestHasTushareToken:
    """测试 Tushare Token 检查"""

    @patch('src.config.providers.get_settings')
    def test_has_tushare_token_true(self, mock_get_settings):
        """测试有 Tushare Token"""
        mock_settings = MagicMock()
        mock_settings.data_source.has_tushare = True
        mock_get_settings.return_value = mock_settings

        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        result = manager.has_tushare_token()

        assert result is True

    @patch('src.config.providers.get_settings')
    def test_has_tushare_token_false(self, mock_get_settings):
        """测试没有 Tushare Token"""
        mock_settings = MagicMock()
        mock_settings.data_source.has_tushare = False
        mock_get_settings.return_value = mock_settings

        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        result = manager.has_tushare_token()

        assert result is False


class TestGetProviderInfo:
    """测试获取提供者信息"""

    def test_get_provider_info_tushare(self):
        """测试获取 Tushare 提供者信息"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        info = manager.get_provider_info('tushare')

        assert info['name'] == 'Tushare Pro'
        assert '专业金融数据接口' in info['description']
        assert 'has_token' in info
        assert info['free'] is False
        assert info['data_quality'] == 'high'
        assert info['rate_limit'] == 'based_on_points'

    def test_get_provider_info_akshare(self):
        """测试获取 AkShare 提供者信息"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        info = manager.get_provider_info('akshare')

        assert info['name'] == 'AkShare'
        assert '开源免费' in info['description']
        assert info['has_token'] is True  # 不需要token所以总是True
        assert info['free'] is True
        assert info['data_quality'] == 'medium'
        assert info['rate_limit'] == 'ip_based'

    def test_get_provider_info_current(self):
        """测试获取当前提供者信息"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        current_provider = manager.get_provider_name()

        # 使用 None 应该返回当前提供者信息
        info = manager.get_provider_info(None)

        assert 'name' in info
        assert 'description' in info

    def test_get_provider_info_unknown(self):
        """测试获取未知提供者信息"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()

        with pytest.raises(ValueError) as exc_info:
            manager.get_provider_info('unknown_provider')

        assert '未知的数据提供者' in str(exc_info.value)


class TestSingletonFunctions:
    """测试全局单例函数"""

    def test_get_provider_config_manager_singleton(self):
        """测试获取单例管理器"""
        from src.config.providers import get_provider_config_manager

        manager1 = get_provider_config_manager()
        manager2 = get_provider_config_manager()

        # 应该返回同一个实例
        assert manager1 is manager2

    def test_get_provider_config_manager_not_none(self):
        """测试单例管理器不为空"""
        from src.config.providers import get_provider_config_manager

        manager = get_provider_config_manager()

        assert manager is not None

    def test_get_provider_config_manager_type(self):
        """测试单例管理器类型"""
        from src.config.providers import get_provider_config_manager, ProviderConfigManager

        manager = get_provider_config_manager()

        assert isinstance(manager, ProviderConfigManager)


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_get_current_provider(self):
        """测试获取当前提供者"""
        from src.config.providers import get_current_provider

        provider = get_current_provider()

        assert provider in ['tushare', 'akshare']
        assert isinstance(provider, str)

    def test_get_current_provider_config(self):
        """测试获取当前提供者配置"""
        from src.config.providers import get_current_provider_config

        config = get_current_provider_config()

        assert isinstance(config, dict)
        assert len(config) > 0

    def test_get_tushare_config(self):
        """测试获取 Tushare 配置便捷函数"""
        from src.config.providers import get_tushare_config

        config = get_tushare_config()

        assert isinstance(config, dict)
        assert 'token' in config

    def test_get_akshare_config(self):
        """测试获取 AkShare 配置便捷函数"""
        from src.config.providers import get_akshare_config

        config = get_akshare_config()

        assert isinstance(config, dict)
        assert 'notes' in config


class TestExportedClasses:
    """测试导出的配置类"""

    def test_tushare_config_imported(self):
        """测试 TushareConfig 可导入"""
        from src.config.providers import TushareConfig

        assert TushareConfig is not None
        assert hasattr(TushareConfig, 'DEFAULT_TIMEOUT')
        assert hasattr(TushareConfig, 'DEFAULT_RETRY_COUNT')

    def test_tushare_error_messages_imported(self):
        """测试 TushareErrorMessages 可导入"""
        from src.config.providers import TushareErrorMessages

        assert TushareErrorMessages is not None

    def test_tushare_fields_imported(self):
        """测试 TushareFields 可导入"""
        from src.config.providers import TushareFields

        assert TushareFields is not None

    def test_akshare_config_imported(self):
        """测试 AkShareConfig 可导入"""
        from src.config.providers import AkShareConfig

        assert AkShareConfig is not None
        assert hasattr(AkShareConfig, 'DEFAULT_TIMEOUT')
        assert hasattr(AkShareConfig, 'DEFAULT_RETRY_COUNT')

    def test_akshare_fields_imported(self):
        """测试 AkShareFields 可导入"""
        from src.config.providers import AkShareFields

        assert AkShareFields is not None

    def test_akshare_notes_imported(self):
        """测试 AkShareNotes 可导入"""
        from src.config.providers import AkShareNotes

        assert AkShareNotes is not None


class TestModuleExports:
    """测试模块导出"""

    def test_all_exports(self):
        """测试 __all__ 包含所有导出"""
        from src.config.providers import __all__

        expected_exports = [
            'ProviderConfigManager',
            'get_provider_config_manager',
            'get_current_provider',
            'get_current_provider_config',
            'get_tushare_config',
            'get_akshare_config',
            'TushareConfig',
            'TushareErrorMessages',
            'TushareFields',
            'AkShareConfig',
            'AkShareFields',
            'AkShareNotes',
        ]

        for export in expected_exports:
            assert export in __all__, f"Missing export: {export}"

    def test_all_exports_accessible(self):
        """测试所有导出可访问"""
        from src.config.providers import __all__
        import src.config.providers as providers_module

        for name in __all__:
            assert hasattr(providers_module, name), f"Cannot access: {name}"


class TestProviderConfigManagerCoverage:
    """测试 ProviderConfigManager 的边界情况和覆盖率"""

    def test_config_cache_isolation(self):
        """测试配置缓存隔离"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()

        # 获取两个不同的配置
        tushare_config = manager.get_tushare_config()
        akshare_config = manager.get_akshare_config()

        # 应该是不同的对象
        assert tushare_config is not akshare_config

        # 应该都在缓存中
        assert 'tushare' in manager._configs
        assert 'akshare' in manager._configs

    def test_provider_info_has_token_check(self):
        """测试提供者信息中的 token 检查"""
        from src.config.providers import ProviderConfigManager

        manager = ProviderConfigManager()
        info = manager.get_provider_info('tushare')

        # has_token 应该根据实际配置返回
        assert isinstance(info['has_token'], bool)

    @patch('src.config.providers.get_settings')
    def test_multiple_manager_instances(self, mock_get_settings):
        """测试多个管理器实例"""
        mock_settings = MagicMock()
        mock_settings.data_source.provider = 'akshare'
        mock_settings.data_source.tushare_token = ''
        mock_settings.data_source.has_tushare = False
        mock_get_settings.return_value = mock_settings

        from src.config.providers import ProviderConfigManager

        # 创建多个实例
        manager1 = ProviderConfigManager()
        manager2 = ProviderConfigManager()

        # 应该是不同的实例
        assert manager1 is not manager2

        # 但都应该访问相同的设置
        assert manager1.get_provider_name() == manager2.get_provider_name()

    def test_config_class_references(self):
        """测试配置类引用正确"""
        from src.config.providers import ProviderConfigManager, TushareConfig, AkShareConfig

        manager = ProviderConfigManager()

        tushare_config = manager.get_tushare_config()
        assert tushare_config['config_class'] is TushareConfig

        akshare_config = manager.get_akshare_config()
        assert akshare_config['config_class'] is AkShareConfig


class TestImportFallback:
    """测试导入降级逻辑"""

    def test_imports_work(self):
        """测试导入正常工作"""
        # 这个测试验证导入不会失败
        from src.config.providers import (
            TushareConfig,
            TushareErrorMessages,
            TushareFields,
            AkShareConfig,
            AkShareFields,
            AkShareNotes,
        )

        assert TushareConfig is not None
        assert TushareErrorMessages is not None
        assert TushareFields is not None
        assert AkShareConfig is not None
        assert AkShareFields is not None
        assert AkShareNotes is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
