"""
策略工厂单元测试

测试 StrategyFactory 的策略创建功能
"""

import unittest
import pytest
from strategies import StrategyFactory, BaseStrategy
from strategies import MomentumStrategy, MeanReversionStrategy, MultiFactorStrategy


class TestStrategyFactory(unittest.TestCase):
    """测试策略工厂"""

    def setUp(self):
        """设置测试"""
        self.factory = StrategyFactory()

    def test_create_momentum_strategy(self):
        """测试创建动量策略"""
        config = {
            'lookback_period': 20,
            'top_n': 50,
            'holding_period': 5
        }

        strategy = self.factory.create('momentum', config, name='TEST_MOM')

        self.assertIsInstance(strategy, MomentumStrategy)
        self.assertIsInstance(strategy, BaseStrategy)
        self.assertEqual(strategy.name, 'TEST_MOM')
        self.assertEqual(strategy._strategy_type, 'predefined')
        self.assertEqual(strategy.config.custom_params['lookback_period'], 20)

    def test_create_mean_reversion_strategy(self):
        """测试创建均值回归策略"""
        config = {
            'lookback_period': 20,
            'method': 'zscore',
            'threshold': 2.0
        }

        strategy = self.factory.create('mean_reversion', config)

        self.assertIsInstance(strategy, MeanReversionStrategy)
        self.assertEqual(strategy._strategy_type, 'predefined')

    def test_create_multi_factor_strategy(self):
        """测试创建多因子策略"""
        config = {
            'factors': ['momentum', 'value', 'quality'],
            'weights': [0.4, 0.3, 0.3]
        }

        strategy = self.factory.create('multi_factor', config)

        self.assertIsInstance(strategy, MultiFactorStrategy)
        self.assertEqual(strategy._strategy_type, 'predefined')

    def test_create_with_invalid_type(self):
        """测试使用无效类型创建策略"""
        with self.assertRaises(ValueError) as context:
            self.factory.create('invalid_type', {})

        self.assertIn('不支持的策略类型', str(context.exception))

    def test_list_strategies(self):
        """测试列出可用策略"""
        strategies = StrategyFactory.list_strategies()

        self.assertIsInstance(strategies, list)
        self.assertIn('momentum', strategies)
        self.assertIn('mean_reversion', strategies)
        self.assertIn('multi_factor', strategies)
        self.assertGreaterEqual(len(strategies), 3)

    def test_get_strategy_class(self):
        """测试获取策略类"""
        strategy_class = StrategyFactory.get_strategy_class('momentum')

        self.assertEqual(strategy_class, MomentumStrategy)
        self.assertTrue(issubclass(strategy_class, BaseStrategy))

    def test_get_strategy_class_invalid(self):
        """测试获取不存在的策略类"""
        with self.assertRaises(ValueError) as context:
            StrategyFactory.get_strategy_class('nonexistent')

        self.assertIn('策略类型不存在', str(context.exception))

    def test_register_custom_strategy(self):
        """测试注册自定义策略"""
        # 创建一个自定义策略类
        class CustomStrategy(BaseStrategy):
            def generate_signals(self, prices, features=None, **kwargs):
                import pandas as pd
                return pd.DataFrame(0, index=prices.index, columns=prices.columns)

            def calculate_scores(self, prices, features=None, date=None):
                return prices.iloc[-1]

        # 注册自定义策略
        StrategyFactory.register_strategy('custom_test', CustomStrategy)

        # 验证已注册
        self.assertIn('custom_test', StrategyFactory.list_strategies())

        # 创建自定义策略实例
        strategy = StrategyFactory.create('custom_test', {'top_n': 30})
        self.assertIsInstance(strategy, CustomStrategy)
        self.assertIsInstance(strategy, BaseStrategy)

    def test_register_invalid_strategy(self):
        """测试注册非 BaseStrategy 子类"""
        class InvalidStrategy:
            pass

        with self.assertRaises(ValueError) as context:
            StrategyFactory.register_strategy('invalid', InvalidStrategy)

        self.assertIn('必须继承自 BaseStrategy', str(context.exception))

    def test_default_strategy_name(self):
        """测试默认策略名称"""
        strategy = self.factory.create('momentum', {'lookback_period': 20})

        self.assertEqual(strategy.name, 'momentum_strategy')

    def test_get_metadata(self):
        """测试获取策略元数据"""
        strategy = self.factory.create(
            'momentum',
            {'lookback_period': 20, 'top_n': 50},
            name='TEST_METADATA'
        )

        metadata = strategy.get_metadata()

        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata['name'], 'TEST_METADATA')
        self.assertEqual(metadata['class'], 'MomentumStrategy')
        self.assertEqual(metadata['strategy_type'], 'predefined')
        self.assertIsNone(metadata['config_id'])
        self.assertIsNone(metadata['strategy_id'])
        self.assertEqual(metadata['risk_level'], 'safe')
        self.assertIsNotNone(metadata['config'])

    def test_multiple_instances(self):
        """测试创建多个策略实例"""
        strategy1 = self.factory.create('momentum', {'lookback_period': 10}, name='MOM10')
        strategy2 = self.factory.create('momentum', {'lookback_period': 20}, name='MOM20')

        self.assertIsNot(strategy1, strategy2)
        self.assertEqual(strategy1.config.custom_params['lookback_period'], 10)
        self.assertEqual(strategy2.config.custom_params['lookback_period'], 20)

    def test_backward_compatibility(self):
        """测试向后兼容性 - get_strategy_info"""
        strategy = self.factory.create('momentum', {'lookback_period': 20})

        # get_strategy_info 应该仍然工作
        info = strategy.get_strategy_info()

        self.assertIsInstance(info, dict)
        self.assertIn('name', info)
        self.assertIn('class', info)
        self.assertIn('config', info)


class TestStrategyFactoryIntegration(unittest.TestCase):
    """集成测试 - 测试工厂与加载器的集成"""

    def test_loader_factory_lazy_load(self):
        """测试 LoaderFactory 懒加载"""
        factory = StrategyFactory()

        # loader_factory 应该在第一次访问时初始化
        self.assertIsNone(factory._loader_factory)

        # 访问 loader_factory
        loader_factory = factory.loader_factory

        self.assertIsNotNone(loader_factory)
        self.assertIsNotNone(factory._loader_factory)


if __name__ == '__main__':
    unittest.main()
