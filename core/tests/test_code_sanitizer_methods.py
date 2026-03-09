"""
测试 CodeSanitizer 的方法调用检查功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategies.security.code_sanitizer import CodeSanitizer


def test_allowed_methods():
    """测试允许的方法调用"""
    sanitizer = CodeSanitizer()

    # 测试正确使用 logger 的代码
    code_good = """
from loguru import logger
import pandas as pd
import numpy as np
from core.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    def generate_signals(self, prices, features=None, **kwargs):
        logger.info("开始生成信号")

        # 使用允许的 pandas 方法
        data = prices.fillna(method='ffill')
        mean_price = data['close'].mean()
        std_price = data['close'].std()

        # 使用允许的 numpy 方法
        arr = np.array([1, 2, 3])
        result = np.mean(arr)

        logger.success("信号生成完成")
        return pd.DataFrame()
"""

    result = sanitizer.sanitize(code_good, strict_mode=True)

    print("="*60)
    print("测试 1: 正确的代码")
    print(f"安全: {result['safe']}")
    print(f"风险等级: {result['risk_level']}")
    print(f"错误: {result['errors']}")
    print(f"警告: {result['warnings']}")
    print(f"方法调用统计: {result['method_calls']}")

    assert result['safe'], "正确的代码应该通过验证"
    assert result['risk_level'] in ['safe', 'low'], f"风险等级应该是 safe 或 low，但得到 {result['risk_level']}"


def test_forbidden_self_logger():
    """测试禁止使用 self.logger"""
    sanitizer = CodeSanitizer()

    code_bad = """
from core.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    def generate_signals(self, prices, features=None, **kwargs):
        self.logger.info("这是错误的用法")  # 禁止
        return pd.DataFrame()
"""

    result = sanitizer.sanitize(code_bad, strict_mode=True)

    print("\n" + "="*60)
    print("测试 2: 使用 self.logger (应该被拒绝)")
    print(f"安全: {result['safe']}")
    print(f"风险等级: {result['risk_level']}")
    print(f"错误: {result['errors']}")

    assert not result['safe'], "使用 self.logger 的代码应该被拒绝"
    assert any('self.logger' in err for err in result['errors']), "应该有关于 self.logger 的错误"


def test_unknown_logger_method():
    """测试未知的 logger 方法"""
    sanitizer = CodeSanitizer()

    code_warning = """
from loguru import logger
from core.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    def generate_signals(self, prices, features=None, **kwargs):
        logger.unknown_method("这个方法不存在")  # 应该警告
        return pd.DataFrame()
"""

    result = sanitizer.sanitize(code_warning, strict_mode=False)

    print("\n" + "="*60)
    print("测试 3: 未知的 logger 方法 (应该警告)")
    print(f"安全: {result['safe']}")
    print(f"风险等级: {result['risk_level']}")
    print(f"警告: {result['warnings']}")

    assert len(result['warnings']) > 0, "应该有警告"


def test_forbidden_functions():
    """测试禁止的函数"""
    sanitizer = CodeSanitizer()

    code_forbidden = """
from core.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    def generate_signals(self, prices, features=None, **kwargs):
        # 尝试使用禁止的函数
        eval("print('hello')")  # 禁止
        return pd.DataFrame()
"""

    result = sanitizer.sanitize(code_forbidden, strict_mode=True)

    print("\n" + "="*60)
    print("测试 4: 禁止的函数 (应该被拒绝)")
    print(f"安全: {result['safe']}")
    print(f"风险等级: {result['risk_level']}")
    print(f"错误: {result['errors']}")

    assert not result['safe'], "使用禁止函数的代码应该被拒绝"
    assert any('eval' in err for err in result['errors']), "应该有关于 eval 的错误"


def test_pandas_methods():
    """测试 pandas 方法调用"""
    sanitizer = CodeSanitizer()

    code_pandas = """
import pandas as pd
from core.strategies.base_strategy import BaseStrategy

class TestStrategy(BaseStrategy):
    def generate_signals(self, prices, features=None, **kwargs):
        # 使用允许的 pandas 方法
        df = pd.DataFrame()
        df = df.fillna(0)
        df = df.rolling(window=20).mean()
        result = df.loc[:, 'close']

        return df
"""

    result = sanitizer.sanitize(code_pandas, strict_mode=True)

    print("\n" + "="*60)
    print("测试 5: Pandas 方法调用")
    print(f"安全: {result['safe']}")
    print(f"风险等级: {result['risk_level']}")
    print(f"方法调用统计: {result['method_calls']}")

    assert result['safe'], "使用允许的 pandas 方法应该通过"
    assert 'fillna' in result['method_calls'], "应该记录 fillna 调用"
    assert 'rolling' in result['method_calls'], "应该记录 rolling 调用"


if __name__ == '__main__':
    print("\n开始测试 CodeSanitizer 方法检查功能\n")

    try:
        test_allowed_methods()
        print("\n✓ 测试 1 通过")
    except AssertionError as e:
        print(f"\n✗ 测试 1 失败: {e}")

    try:
        test_forbidden_self_logger()
        print("✓ 测试 2 通过")
    except AssertionError as e:
        print(f"✗ 测试 2 失败: {e}")

    try:
        test_unknown_logger_method()
        print("✓ 测试 3 通过")
    except AssertionError as e:
        print(f"✗ 测试 3 失败: {e}")

    try:
        test_forbidden_functions()
        print("✓ 测试 4 通过")
    except AssertionError as e:
        print(f"✗ 测试 4 失败: {e}")

    try:
        test_pandas_methods()
        print("✓ 测试 5 通过")
    except AssertionError as e:
        print(f"✗ 测试 5 失败: {e}")

    print("\n" + "="*60)
    print("所有测试完成!")
