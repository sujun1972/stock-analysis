"""
加载器集成测试

测试完整的策略加载流程，包括动态代码编译和执行
"""

import pytest
import pandas as pd
import numpy as np
from src.strategies.loaders.dynamic_loader import DynamicCodeLoader
from src.strategies.base_strategy import BaseStrategy


class TestDynamicLoaderIntegration:
    """测试动态加载器集成"""

    @pytest.fixture
    def valid_strategy_code(self):
        """有效的策略代码示例"""
        return """
import pandas as pd
import numpy as np
from typing import Optional

class TestMomentumStrategy(BaseStrategy):
    '''简单的动量策略'''

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        '''生成交易信号'''
        # 简单的动量信号：买入价格上涨的股票
        returns = prices.pct_change()
        signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
        signals[returns > 0] = 1
        signals[returns < 0] = -1
        return signals

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        '''计算股票评分'''
        if date is None:
            date = prices.index[-1]

        # 简单评分：最近5日收益率
        recent_returns = prices.pct_change(5).loc[date]
        return recent_returns.fillna(0)
"""

    @pytest.fixture
    def dangerous_strategy_code(self):
        """危险的策略代码示例（应该被拒绝）"""
        return """
import os
import subprocess

class DangerousStrategy(BaseStrategy):
    def generate_signals(self, prices, features=None, **kwargs):
        # 尝试执行系统命令
        os.system('ls -la')
        return pd.DataFrame(0, index=prices.index, columns=prices.columns)

    def calculate_scores(self, prices, features=None, date=None):
        return pd.Series(0, index=prices.columns)
"""

    def test_compile_valid_code(self, valid_strategy_code):
        """测试编译有效代码"""
        loader = DynamicCodeLoader()

        # 测试代码编译
        strategy_class = loader._compile_and_load(
            code=valid_strategy_code,
            class_name='TestMomentumStrategy',
            module_name='test_momentum'
        )

        # 验证类是否正确加载
        assert strategy_class is not None
        assert strategy_class.__name__ == 'TestMomentumStrategy'
        assert issubclass(strategy_class, BaseStrategy)

    def test_instantiate_and_execute(self, valid_strategy_code):
        """测试实例化和执行策略"""
        loader = DynamicCodeLoader()

        # 编译代码
        strategy_class = loader._compile_and_load(
            code=valid_strategy_code,
            class_name='TestMomentumStrategy',
            module_name='test_momentum'
        )

        # 实例化策略
        strategy = strategy_class(
            name='TestStrategy',
            config={'top_n': 10}
        )

        # 准备测试数据
        dates = pd.date_range('2024-01-01', periods=10)
        stocks = ['STOCK1', 'STOCK2', 'STOCK3']
        prices = pd.DataFrame(
            np.random.randn(10, 3).cumsum(axis=0) + 100,
            index=dates,
            columns=stocks
        )

        # 执行策略
        signals = strategy.generate_signals(prices)

        # 验证结果
        assert isinstance(signals, pd.DataFrame)
        assert signals.shape == prices.shape
        assert set(signals.values.flatten()).issubset({-1, 0, 1})

    def test_calculate_scores(self, valid_strategy_code):
        """测试计算评分"""
        loader = DynamicCodeLoader()

        strategy_class = loader._compile_and_load(
            code=valid_strategy_code,
            class_name='TestMomentumStrategy',
            module_name='test_momentum'
        )

        strategy = strategy_class('TestStrategy', {'top_n': 10})

        # 准备测试数据
        dates = pd.date_range('2024-01-01', periods=10)
        stocks = ['STOCK1', 'STOCK2', 'STOCK3']
        prices = pd.DataFrame(
            np.random.randn(10, 3).cumsum(axis=0) + 100,
            index=dates,
            columns=stocks
        )

        # 计算评分
        scores = strategy.calculate_scores(prices)

        # 验证结果
        assert isinstance(scores, pd.Series)
        assert len(scores) == len(stocks)

    def test_sanitize_dangerous_code(self, dangerous_strategy_code):
        """测试拒绝危险代码"""
        loader = DynamicCodeLoader()

        # 代码净化应该检测到危险
        result = loader.sanitizer.sanitize(dangerous_strategy_code, strict_mode=True)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'
        assert len(result['errors']) > 0
        # 应该检测到禁止的导入
        assert any('os' in str(e) or 'subprocess' in str(e) for e in result['errors'])

    def test_restricted_globals(self):
        """测试受限的全局命名空间"""
        loader = DynamicCodeLoader()

        restricted = loader._create_restricted_globals()

        # 验证只包含安全的内置函数
        assert 'eval' not in restricted['__builtins__']
        assert 'exec' not in restricted['__builtins__']
        assert 'open' not in restricted['__builtins__']

        # 验证包含必要的模块
        assert 'pd' in restricted
        assert 'np' in restricted
        assert 'BaseStrategy' in restricted

    def test_code_without_base_strategy(self):
        """测试不继承BaseStrategy的代码"""
        loader = DynamicCodeLoader()

        invalid_code = """
class NotAStrategy:
    def some_method(self):
        pass
"""

        with pytest.raises(TypeError) as exc_info:
            loader._compile_and_load(
                code=invalid_code,
                class_name='NotAStrategy',
                module_name='invalid'
            )

        assert 'BaseStrategy' in str(exc_info.value)

    def test_code_missing_class(self):
        """测试缺少指定类的代码"""
        loader = DynamicCodeLoader()

        code = """
class WrongClassName(BaseStrategy):
    pass
"""

        with pytest.raises(AttributeError) as exc_info:
            loader._compile_and_load(
                code=code,
                class_name='ExpectedClassName',
                module_name='test'
            )

        assert '未找到类' in str(exc_info.value)


class TestLoaderCaching:
    """测试加载器缓存机制"""

    @pytest.fixture
    def simple_code(self):
        """简单的测试代码"""
        return """
class SimpleStrategy(BaseStrategy):
    def generate_signals(self, prices, features=None, **kwargs):
        return pd.DataFrame(0, index=prices.index, columns=prices.columns)

    def calculate_scores(self, prices, features=None, date=None):
        return pd.Series(0, index=prices.columns)
"""

    def test_cache_mechanism(self, simple_code):
        """测试缓存机制"""
        loader = DynamicCodeLoader()

        # 第一次编译
        class1 = loader._compile_and_load(
            code=simple_code,
            class_name='SimpleStrategy',
            module_name='simple1'
        )

        # 第二次编译（相同的代码）
        class2 = loader._compile_and_load(
            code=simple_code,
            class_name='SimpleStrategy',
            module_name='simple2'
        )

        # 类的定义应该相同
        assert class1.__name__ == class2.__name__

        # 两次编译都应该成功
        assert class1 is not None
        assert class2 is not None


class TestSecurityIntegration:
    """测试安全机制集成"""

    def test_permission_checker_integration(self):
        """测试权限检查器集成"""
        loader = DynamicCodeLoader()

        dangerous_patterns = [
            "open('file.txt')",
            "import socket",
            "import urllib",
            "os.system('cmd')",
        ]

        for pattern in dangerous_patterns:
            result = loader.permission_checker.check_permissions(pattern)
            assert result['allowed'] is False
            assert len(result['violations']) > 0

    def test_safe_operations(self):
        """测试安全操作"""
        loader = DynamicCodeLoader()

        safe_code = """
import pandas as pd
import numpy as np

# 这些操作应该是安全的
df = pd.DataFrame({'a': [1, 2, 3]})
mean = df['a'].mean()
result = np.array([1, 2, 3]).sum()
"""

        result = loader.permission_checker.check_permissions(safe_code)
        assert result['allowed'] is True
        assert len(result['violations']) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
