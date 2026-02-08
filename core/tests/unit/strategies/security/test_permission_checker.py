"""
PermissionChecker 单元测试

测试权限检查器的资源访问控制功能
"""

import pytest
from strategies.security.permission_checker import PermissionChecker


class TestPermissionChecker:
    """测试 PermissionChecker 类"""

    @pytest.fixture
    def checker(self):
        """创建 PermissionChecker 实例"""
        return PermissionChecker()

    def test_safe_code(self, checker):
        """测试安全代码 - 只使用 pandas 和 numpy"""
        code = """
import pandas as pd
import numpy as np

class Strategy:
    def process(self, data):
        return data.mean()
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is True
        assert len(result['violations']) == 0

    def test_filesystem_access_open(self, checker):
        """测试文件系统访问 - open()"""
        code = """
class Strategy:
    def run(self):
        with open('file.txt', 'r') as f:
            data = f.read()
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is False
        assert any('文件系统' in v for v in result['violations'])

    def test_filesystem_access_pathlib(self, checker):
        """测试文件系统访问 - pathlib"""
        code = """
from pathlib import Path

class Strategy:
    def run(self):
        p = Path('file.txt')
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is False
        assert len(result['violations']) > 0

    def test_network_access_socket(self, checker):
        """测试网络访问 - socket"""
        code = """
import socket

class Strategy:
    def connect(self):
        s = socket.socket()
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is False
        assert any('网络访问' in v for v in result['violations'])

    def test_network_access_requests(self, checker):
        """测试网络访问 - requests"""
        code = """
import requests

class Strategy:
    def fetch(self):
        requests.get('http://example.com')
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is False
        assert any('网络访问' in v for v in result['violations'])

    def test_network_access_urllib(self, checker):
        """测试网络访问 - urllib"""
        code = """
import urllib

class Strategy:
    def fetch(self):
        urllib.request.urlopen('http://example.com')
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is False
        assert any('网络访问' in v for v in result['violations'])

    def test_system_command_os_system(self, checker):
        """测试系统命令 - os.system"""
        code = """
import os

class Strategy:
    def run(self):
        os.system('ls')
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is False
        assert any('系统命令' in v for v in result['violations'])

    def test_system_command_subprocess(self, checker):
        """测试系统命令 - subprocess"""
        code = """
import subprocess

class Strategy:
    def run(self):
        subprocess.call(['ls'])
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is False
        assert any('系统命令' in v for v in result['violations'])

    def test_database_access_psycopg2(self, checker):
        """测试数据库访问 - psycopg2"""
        code = """
import psycopg2

class Strategy:
    def connect(self):
        conn = psycopg2.connect('dbname=test')
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is False
        assert any('数据库' in v for v in result['violations'])

    def test_database_access_sqlalchemy(self, checker):
        """测试数据库访问 - sqlalchemy"""
        code = """
from sqlalchemy import create_engine

class Strategy:
    def connect(self):
        engine = create_engine('postgresql://...')
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is False
        assert any('数据库' in v for v in result['violations'])

    def test_multiple_violations(self, checker):
        """测试多个违规"""
        code = """
import os
import requests
import psycopg2

class Strategy:
    def run(self):
        os.system('ls')
        requests.get('http://example.com')
        with open('file.txt') as f:
            data = f.read()
"""
        result = checker.check_permissions(code)

        assert result['allowed'] is False
        # 应该检测到多个违规
        assert len(result['violations']) >= 3

    def test_check_method_access_default(self, checker):
        """测试方法访问检查 - 默认模式"""
        code = """
import pandas as pd

class Strategy:
    def process(self, df):
        return df.mean()
"""
        result = checker.check_method_access(code)

        # 默认非严格模式，应该允许
        assert result['allowed'] is True

    def test_allowed_pandas_methods(self, checker):
        """测试允许的 pandas 方法列表"""
        # 验证常用方法在白名单中
        assert 'mean' in checker.ALLOWED_PANDAS_METHODS
        assert 'std' in checker.ALLOWED_PANDAS_METHODS
        assert 'rolling' in checker.ALLOWED_PANDAS_METHODS
        assert 'groupby' in checker.ALLOWED_PANDAS_METHODS

    def test_allowed_numpy_functions(self, checker):
        """测试允许的 numpy 函数列表"""
        # 验证常用函数在白名单中
        assert 'mean' in checker.ALLOWED_NUMPY_FUNCTIONS
        assert 'std' in checker.ALLOWED_NUMPY_FUNCTIONS
        assert 'array' in checker.ALLOWED_NUMPY_FUNCTIONS
        assert 'sqrt' in checker.ALLOWED_NUMPY_FUNCTIONS
