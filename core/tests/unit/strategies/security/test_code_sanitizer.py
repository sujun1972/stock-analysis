"""
CodeSanitizer 单元测试

测试代码净化器的各项安全检查功能
"""

import pytest
from strategies.security.code_sanitizer import CodeSanitizer


class TestCodeSanitizer:
    """测试 CodeSanitizer 类"""

    @pytest.fixture
    def sanitizer(self):
        """创建 CodeSanitizer 实例"""
        return CodeSanitizer()

    def test_safe_code(self, sanitizer):
        """测试安全代码 - 应该通过"""
        code = """
import pandas as pd
import numpy as np

class TestStrategy:
    def calculate_scores(self, prices, features=None, date=None):
        return prices.iloc[-1]

    def generate_signals(self, prices, features=None, volumes=None, **kwargs):
        return pd.DataFrame(0, index=prices.index, columns=prices.columns)
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is True
        assert result['risk_level'] == 'safe'
        assert len(result['errors']) == 0
        assert result['sanitized_code'] == code

    def test_dangerous_imports_os(self, sanitizer):
        """测试危险导入 - os 模块"""
        code = """
import os

class BadStrategy:
    def run(self):
        os.system('ls')
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'
        assert any('os' in str(e).lower() for e in result['errors'])

    def test_dangerous_imports_subprocess(self, sanitizer):
        """测试危险导入 - subprocess 模块"""
        code = """
import subprocess

class BadStrategy:
    def run(self):
        subprocess.call(['ls'])
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'
        assert any('subprocess' in str(e).lower() for e in result['errors'])

    def test_dangerous_imports_socket(self, sanitizer):
        """测试危险导入 - socket 模块"""
        code = """
import socket

class BadStrategy:
    def connect(self):
        s = socket.socket()
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'

    def test_dangerous_function_eval(self, sanitizer):
        """测试危险函数 - eval"""
        code = """
class BadStrategy:
    def run(self):
        eval('print("hello")')
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'
        assert any('eval' in str(e).lower() for e in result['errors'])

    def test_dangerous_function_exec(self, sanitizer):
        """测试危险函数 - exec"""
        code = """
class BadStrategy:
    def run(self):
        exec('print("hello")')
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'
        assert any('exec' in str(e).lower() for e in result['errors'])

    def test_dangerous_function_compile(self, sanitizer):
        """测试危险函数 - compile"""
        code = """
class BadStrategy:
    def run(self):
        compile('print("hello")', '<string>', 'exec')
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'

    def test_forbidden_attributes(self, sanitizer):
        """测试禁止的属性访问"""
        code = """
class BadStrategy:
    def run(self):
        x = self.__dict__
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'

    def test_syntax_error(self, sanitizer):
        """测试语法错误"""
        code = """
class BadStrategy
    def run(self):
        print("hello"
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'
        assert len(result['errors']) > 0

    def test_hash_verification_match(self, sanitizer):
        """测试哈希验证 - 匹配"""
        code = "print('hello')"
        code_hash = sanitizer._calculate_hash(code)

        result = sanitizer.sanitize(code, expected_hash=code_hash)

        # 注意: 即使哈希匹配，仍需检查代码内容安全性
        # 这里的代码包含 print (非禁止函数)，所以应该是安全的
        assert result['safe'] is True  # 简单的print语句应该安全

    def test_hash_verification_mismatch(self, sanitizer):
        """测试哈希验证 - 不匹配"""
        code = "print('hello')"
        wrong_hash = "0" * 64

        result = sanitizer.sanitize(code, expected_hash=wrong_hash)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'
        assert any('哈希不匹配' in str(e) for e in result['errors'])

    def test_string_literal_suspicious_patterns(self, sanitizer):
        """测试可疑字符串模式检测"""
        code = """
class Strategy:
    def run(self):
        # 这只是一个注释提到 os.system，不是真正的调用
        comment = "不要使用 os.system"
"""
        result = sanitizer.sanitize(code)

        # 应该产生警告，但不一定失败
        assert 'os.system' in str(result['warnings'])

    def test_unknown_import_warning(self, sanitizer):
        """测试未知导入 - 应产生警告"""
        code = """
import json

class Strategy:
    def run(self):
        json.dumps({})
"""
        result = sanitizer.sanitize(code, strict_mode=False)

        # json 不在白名单中，应产生警告
        assert len(result['warnings']) > 0
        assert result['risk_level'] in ['low', 'medium']

    def test_strict_mode_with_warnings(self, sanitizer):
        """测试严格模式下的警告处理"""
        code = """
import json

class Strategy:
    pass
"""
        # 严格模式: 有警告就拒绝
        result_strict = sanitizer.sanitize(code, strict_mode=True)
        # 非严格模式: 警告不影响
        result_loose = sanitizer.sanitize(code, strict_mode=False)

        assert len(result_strict['warnings']) > 0
        assert len(result_loose['warnings']) > 0

    def test_multiple_violations(self, sanitizer):
        """测试多个安全违规"""
        code = """
import os
import subprocess

class BadStrategy:
    def run(self):
        eval('print("hello")')
        exec('ls')
        x = self.__dict__
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'
        assert len(result['errors']) >= 3  # 至少3个错误

    def test_allowed_pandas_numpy(self, sanitizer):
        """测试允许的 pandas 和 numpy 导入"""
        code = """
import pandas as pd
import numpy as np

class Strategy:
    def process(self, data):
        return pd.DataFrame(np.zeros((10, 5)))
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is True
        assert len(result['errors']) == 0

    def test_from_import(self, sanitizer):
        """测试 from ... import 语法"""
        code = """
from pandas import DataFrame
from numpy import array

class Strategy:
    pass
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is True
        assert len(result['errors']) == 0

    def test_forbidden_from_import(self, sanitizer):
        """测试禁止的 from import"""
        code = """
from os import system

class Strategy:
    pass
"""
        result = sanitizer.sanitize(code)

        assert result['safe'] is False
        assert result['risk_level'] == 'high'

    def test_calculate_hash(self, sanitizer):
        """测试哈希计算"""
        code1 = "print('hello')"
        code2 = "print('hello')"
        code3 = "print('world')"

        hash1 = sanitizer._calculate_hash(code1)
        hash2 = sanitizer._calculate_hash(code2)
        hash3 = sanitizer._calculate_hash(code3)

        # 相同代码应该有相同哈希
        assert hash1 == hash2
        # 不同代码应该有不同哈希
        assert hash1 != hash3

    def test_risk_order(self, sanitizer):
        """测试风险等级排序"""
        assert sanitizer._risk_order('safe') < sanitizer._risk_order('low')
        assert sanitizer._risk_order('low') < sanitizer._risk_order('medium')
        assert sanitizer._risk_order('medium') < sanitizer._risk_order('high')
