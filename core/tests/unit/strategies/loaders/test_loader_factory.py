"""
测试 LoaderFactory
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.strategies.loaders.loader_factory import LoaderFactory


class TestLoaderFactory:
    """测试 LoaderFactory"""

    @pytest.fixture
    def factory(self):
        """创建工厂实例"""
        return LoaderFactory()

    def test_init_singleton(self):
        """测试单例模式"""
        factory1 = LoaderFactory()
        factory2 = LoaderFactory()

        # 应该是同一个实例
        assert factory1 is factory2

    def test_init_loaders(self, factory):
        """测试加载器初始化"""
        assert factory.config_loader is not None
        assert factory.dynamic_loader is not None

    def test_load_strategy_config(self, factory):
        """测试加载配置策略"""
        # Mock config_loader
        mock_strategy = Mock()
        factory.config_loader.load_strategy = Mock(return_value=mock_strategy)

        result = factory.load_strategy('config', 1)

        assert result is mock_strategy
        factory.config_loader.load_strategy.assert_called_once_with(1)

    def test_load_strategy_dynamic(self, factory):
        """测试加载动态策略"""
        # Mock dynamic_loader
        mock_strategy = Mock()
        factory.dynamic_loader.load_strategy = Mock(return_value=mock_strategy)

        result = factory.load_strategy('dynamic', 1)

        assert result is mock_strategy
        factory.dynamic_loader.load_strategy.assert_called_once_with(1)

    def test_load_strategy_invalid_source(self, factory):
        """测试无效的策略来源"""
        with pytest.raises(ValueError) as exc_info:
            factory.load_strategy('invalid', 1)

        assert '未知的策略来源' in str(exc_info.value)

    def test_reload_strategy_config(self, factory):
        """测试重新加载配置策略"""
        mock_strategy = Mock()
        factory.config_loader.reload_strategy = Mock(return_value=mock_strategy)

        result = factory.reload_strategy('config', 1)

        assert result is mock_strategy
        factory.config_loader.reload_strategy.assert_called_once_with(1)

    def test_reload_strategy_dynamic(self, factory):
        """测试重新加载动态策略"""
        mock_strategy = Mock()
        factory.dynamic_loader.reload_strategy = Mock(return_value=mock_strategy)

        result = factory.reload_strategy('dynamic', 1, strict_mode=True)

        assert result is mock_strategy
        factory.dynamic_loader.reload_strategy.assert_called_once()

    def test_batch_load_strategies(self, factory):
        """测试批量加载"""
        # Mock loaders
        config_strategy = Mock()
        dynamic_strategy = Mock()

        factory.config_loader.load_strategy = Mock(return_value=config_strategy)
        factory.dynamic_loader.load_strategy = Mock(return_value=dynamic_strategy)

        configs = [
            {'source': 'config', 'id': 1},
            {'source': 'dynamic', 'id': 2},
        ]

        results = factory.batch_load_strategies(configs)

        assert len(results['config']) == 1
        assert len(results['dynamic']) == 1
        assert results['config'][1] is config_strategy
        assert results['dynamic'][2] is dynamic_strategy

    def test_batch_load_strategies_with_errors(self, factory):
        """测试批量加载时的错误处理"""
        # 第一个成功，第二个失败
        factory.config_loader.load_strategy = Mock(return_value=Mock())
        factory.dynamic_loader.load_strategy = Mock(side_effect=Exception("加载失败"))

        configs = [
            {'source': 'config', 'id': 1},
            {'source': 'dynamic', 'id': 2},
        ]

        results = factory.batch_load_strategies(configs)

        # 第一个应该成功
        assert len(results['config']) == 1
        # 第二个应该失败，但不影响整体
        assert len(results['dynamic']) == 0

    def test_clear_cache_all(self, factory):
        """测试清除所有缓存"""
        factory.config_loader.clear_cache = Mock()
        factory.dynamic_loader.clear_cache = Mock()

        factory.clear_cache()

        factory.config_loader.clear_cache.assert_called_once()
        factory.dynamic_loader.clear_cache.assert_called_once()

    def test_clear_cache_config_only(self, factory):
        """测试只清除配置缓存"""
        factory.config_loader.clear_cache = Mock()
        factory.dynamic_loader.clear_cache = Mock()

        factory.clear_cache('config')

        factory.config_loader.clear_cache.assert_called_once()
        factory.dynamic_loader.clear_cache.assert_not_called()

    def test_clear_cache_dynamic_only(self, factory):
        """测试只清除动态缓存"""
        factory.config_loader.clear_cache = Mock()
        factory.dynamic_loader.clear_cache = Mock()

        factory.clear_cache('dynamic')

        factory.config_loader.clear_cache.assert_not_called()
        factory.dynamic_loader.clear_cache.assert_called_once()

    def test_get_cache_info(self, factory):
        """测试获取缓存信息"""
        factory.config_loader.get_cache_info = Mock(return_value={'cached_count': 2})
        factory.dynamic_loader.get_cache_info = Mock(return_value={'cached_count': 3})

        info = factory.get_cache_info()

        assert 'config_loader' in info
        assert 'dynamic_loader' in info
        assert info['config_loader']['cached_count'] == 2
        assert info['dynamic_loader']['cached_count'] == 3

    def test_get_loader_config(self, factory):
        """测试获取配置加载器"""
        loader = factory.get_loader('config')
        assert loader is factory.config_loader

    def test_get_loader_dynamic(self, factory):
        """测试获取动态加载器"""
        loader = factory.get_loader('dynamic')
        assert loader is factory.dynamic_loader

    def test_get_loader_invalid(self, factory):
        """测试获取无效加载器"""
        with pytest.raises(ValueError) as exc_info:
            factory.get_loader('invalid')

        assert '未知的策略来源' in str(exc_info.value)

    def test_repr(self, factory):
        """测试字符串表示"""
        repr_str = repr(factory)
        assert 'LoaderFactory' in repr_str
        assert 'config=' in repr_str
        assert 'dynamic=' in repr_str
