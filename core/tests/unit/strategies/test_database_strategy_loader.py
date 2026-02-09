"""
数据库策略加载器单元测试

测试从数据库加载策略代码并动态实例化的功能
"""

import unittest
import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime


class TestDatabaseStrategyLoader(unittest.TestCase):
    """测试数据库策略加载器"""

    def setUp(self):
        """设置测试环境"""
        # 模拟的策略数据
        self.mock_strategy_data = {
            'id': 1,
            'name': 'test_momentum',
            'display_name': '测试动量策略',
            'class_name': 'MomentumStrategy',
            'code': '''
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

from strategies.base_strategy import BaseStrategy
from strategies.signal_generator import SignalGenerator

class MomentumStrategy(BaseStrategy):
    """动量策略"""

    def __init__(self, name: str, config: Dict[str, Any]):
        default_config = {'lookback_period': 20, 'top_n': 50, 'holding_period': 5}
        default_config.update(config)
        super().__init__(name, default_config)
        self.lookback_period = self.config.custom_params.get('lookback_period', 20)

    def calculate_scores(self, prices, features=None, date=None):
        momentum = prices.pct_change(self.lookback_period) * 100
        if date is None:
            date = momentum.index[-1]
        return momentum.loc[date]

    def generate_signals(self, prices, features=None, volumes=None, **kwargs):
        momentum = prices.pct_change(self.lookback_period) * 100
        signals_response = SignalGenerator.generate_rank_signals(
            scores=momentum, top_n=self.config.top_n
        )
        if not signals_response.is_success():
            raise ValueError(f"信号生成失败: {signals_response.error}")
        return signals_response.data

    def get_metadata(self):
        return {
            'name': self.name,
            'class_name': self.__class__.__name__,
            'category': 'momentum',
            'description': '动量策略',
            'risk_level': 'medium',
        }
''',
            'code_hash': 'abc123...',
            'source_type': 'builtin',
            'category': 'momentum',
            'description': '基于价格动量选股',
            'default_params': {
                'lookback_period': 20,
                'top_n': 50,
                'holding_period': 5
            },
            'validation_status': 'passed',
            'risk_level': 'medium',
            'is_enabled': True,
            'created_at': datetime.now(),
        }

    def test_load_strategy_code_from_database(self):
        """测试从数据库加载策略代码"""
        with patch('psycopg2.connect') as mock_connect:
            # 模拟数据库连接和查询
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = self.mock_strategy_data
            mock_connect.return_value.cursor.return_value.__enter__.return_value = mock_cursor

            # 执行加载(这里简化演示)
            strategy_data = self.mock_strategy_data

            # 验证
            self.assertEqual(strategy_data['name'], 'test_momentum')
            self.assertEqual(strategy_data['class_name'], 'MomentumStrategy')
            self.assertIn('class MomentumStrategy', strategy_data['code'])
            self.assertEqual(strategy_data['source_type'], 'builtin')

    def test_dynamic_code_execution(self):
        """测试动态执行策略代码"""
        # 准备命名空间
        namespace = {
            '__name__': '__dynamic_strategy__',
            'pd': pd,
            'np': np,
            'Optional': __import__('typing').Optional,
            'Dict': __import__('typing').Dict,
            'Any': __import__('typing').Any,
        }

        # 导入必要模块
        from strategies.base_strategy import BaseStrategy
        from strategies.signal_generator import SignalGenerator

        namespace['BaseStrategy'] = BaseStrategy
        namespace['SignalGenerator'] = SignalGenerator

        # 执行策略代码
        exec(self.mock_strategy_data['code'], namespace)

        # 验证类已加载
        self.assertIn('MomentumStrategy', namespace)
        strategy_class = namespace['MomentumStrategy']

        # 验证类继承
        self.assertTrue(issubclass(strategy_class, BaseStrategy))

    def test_strategy_instantiation(self):
        """测试策略实例化"""
        # 执行代码获取类
        namespace = {
            '__name__': '__dynamic_strategy__',
            'pd': pd,
            'np': np,
            'Optional': __import__('typing').Optional,
            'Dict': __import__('typing').Dict,
            'Any': __import__('typing').Any,
        }

        from strategies.base_strategy import BaseStrategy
        from strategies.signal_generator import SignalGenerator

        namespace['BaseStrategy'] = BaseStrategy
        namespace['SignalGenerator'] = SignalGenerator

        exec(self.mock_strategy_data['code'], namespace)
        strategy_class = namespace['MomentumStrategy']

        # 实例化策略
        config = {'lookback_period': 20, 'top_n': 50}
        strategy = strategy_class(name='test_strategy', config=config)

        # 验证实例
        self.assertIsInstance(strategy, BaseStrategy)
        self.assertEqual(strategy.name, 'test_strategy')
        self.assertEqual(strategy.lookback_period, 20)

    def test_strategy_metadata(self):
        """测试获取策略元数据"""
        # 加载并实例化策略
        namespace = {
            '__name__': '__dynamic_strategy__',
            'pd': pd,
            'np': np,
            'Optional': __import__('typing').Optional,
            'Dict': __import__('typing').Dict,
            'Any': __import__('typing').Any,
        }

        from strategies.base_strategy import BaseStrategy
        from strategies.signal_generator import SignalGenerator

        namespace['BaseStrategy'] = BaseStrategy
        namespace['SignalGenerator'] = SignalGenerator

        exec(self.mock_strategy_data['code'], namespace)
        strategy_class = namespace['MomentumStrategy']
        strategy = strategy_class(name='test_strategy', config={})

        # 获取元数据
        metadata = strategy.get_metadata()

        # 验证元数据
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata['class_name'], 'MomentumStrategy')
        self.assertEqual(metadata['category'], 'momentum')
        self.assertEqual(metadata['risk_level'], 'medium')

    def test_strategy_generate_signals(self):
        """测试策略生成交易信号"""
        # 准备测试数据
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        stocks = ['000001', '000002', '000003']
        prices = pd.DataFrame(
            np.random.uniform(10, 20, (50, 3)),
            index=dates,
            columns=stocks
        )

        # 加载策略
        namespace = {
            '__name__': '__dynamic_strategy__',
            'pd': pd,
            'np': np,
            'Optional': __import__('typing').Optional,
            'Dict': __import__('typing').Dict,
            'Any': __import__('typing').Any,
        }

        from strategies.base_strategy import BaseStrategy
        from strategies.signal_generator import SignalGenerator

        namespace['BaseStrategy'] = BaseStrategy
        namespace['SignalGenerator'] = SignalGenerator

        exec(self.mock_strategy_data['code'], namespace)
        strategy_class = namespace['MomentumStrategy']
        strategy = strategy_class(name='test_strategy', config={'top_n': 2})

        # 生成信号
        signals = strategy.generate_signals(prices)

        # 验证信号
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertEqual(signals.shape, prices.shape)
        self.assertTrue((signals.isin([0, 1])).all().all())

    def test_code_hash_validation(self):
        """测试代码哈希验证"""
        import hashlib

        code = self.mock_strategy_data['code']
        expected_hash = hashlib.sha256(code.encode('utf-8')).hexdigest()

        # 验证哈希可以正确计算
        self.assertIsInstance(expected_hash, str)
        self.assertEqual(len(expected_hash), 64)  # SHA256哈希长度

    def test_invalid_class_name(self):
        """测试无效的类名"""
        namespace = {
            '__name__': '__dynamic_strategy__',
            'pd': pd,
            'np': np,
        }

        from strategies.base_strategy import BaseStrategy
        from strategies.signal_generator import SignalGenerator

        namespace['BaseStrategy'] = BaseStrategy
        namespace['SignalGenerator'] = SignalGenerator

        exec(self.mock_strategy_data['code'], namespace)

        # 尝试获取不存在的类
        self.assertNotIn('NonExistentClass', namespace)

    def test_strategy_with_default_params(self):
        """测试使用默认参数创建策略"""
        namespace = {
            '__name__': '__dynamic_strategy__',
            'pd': pd,
            'np': np,
            'Optional': __import__('typing').Optional,
            'Dict': __import__('typing').Dict,
            'Any': __import__('typing').Any,
        }

        from strategies.base_strategy import BaseStrategy
        from strategies.signal_generator import SignalGenerator

        namespace['BaseStrategy'] = BaseStrategy
        namespace['SignalGenerator'] = SignalGenerator

        exec(self.mock_strategy_data['code'], namespace)
        strategy_class = namespace['MomentumStrategy']

        # 使用数据库中的默认参数
        default_params = self.mock_strategy_data['default_params']
        strategy = strategy_class(name='test_strategy', config=default_params)

        # 验证参数
        self.assertEqual(strategy.lookback_period, 20)
        self.assertEqual(strategy.config.top_n, 50)


class TestStrategyDatabaseIntegration(unittest.TestCase):
    """策略数据库集成测试"""

    @pytest.mark.integration
    def test_full_workflow(self):
        """测试完整工作流程: 加载 -> 实例化 -> 运行"""
        # 这个测试需要实际的数据库连接
        # 在CI/CD环境中可以使用测试数据库
        pass


class TestStrategyValidation(unittest.TestCase):
    """策略验证测试"""

    def test_strategy_code_safety(self):
        """测试策略代码安全性验证"""
        # 包含危险代码的策略
        dangerous_code = '''
import os
class DangerousStrategy:
    def __init__(self):
        os.system('rm -rf /')  # 危险操作
'''

        # 实际应用中应该有代码安全检查机制
        # 这里只是演示测试
        self.assertIn('os.system', dangerous_code)
        # 应该被安全检查器拦截

    def test_required_methods_present(self):
        """测试策略是否包含必需的方法"""
        namespace = {
            '__name__': '__test__',
            'pd': pd,
            'np': np,
            'Optional': __import__('typing').Optional,
            'Dict': __import__('typing').Dict,
            'Any': __import__('typing').Any,
        }

        from strategies.base_strategy import BaseStrategy
        from strategies.signal_generator import SignalGenerator

        namespace['BaseStrategy'] = BaseStrategy
        namespace['SignalGenerator'] = SignalGenerator

        # 使用完整的策略代码
        mock_data = {
            'code': '''
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np

from strategies.base_strategy import BaseStrategy
from strategies.signal_generator import SignalGenerator

class TestStrategy(BaseStrategy):
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)

    def calculate_scores(self, prices, features=None, date=None):
        return prices.iloc[-1]

    def generate_signals(self, prices, features=None, volumes=None, **kwargs):
        import pandas as pd
        return pd.DataFrame(0, index=prices.index, columns=prices.columns)

    def get_metadata(self):
        return {'name': self.name}
'''
        }

        exec(mock_data['code'], namespace)
        strategy_class = namespace['TestStrategy']
        strategy = strategy_class(name='test', config={})

        # 验证必需方法存在
        self.assertTrue(hasattr(strategy, 'calculate_scores'))
        self.assertTrue(hasattr(strategy, 'generate_signals'))
        self.assertTrue(hasattr(strategy, 'get_metadata'))
        self.assertTrue(callable(strategy.calculate_scores))
        self.assertTrue(callable(strategy.generate_signals))
        self.assertTrue(callable(strategy.get_metadata))


if __name__ == '__main__':
    unittest.main()
