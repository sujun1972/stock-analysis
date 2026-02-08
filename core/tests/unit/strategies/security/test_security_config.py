"""
SecurityConfig 单元测试

测试安全配置管理功能
"""

import pytest
import json
import tempfile
from pathlib import Path
from strategies.security.security_config import (
    SecurityConfig,
    DEFAULT_SECURITY_CONFIG,
    DEVELOPMENT_SECURITY_CONFIG,
    PRODUCTION_SECURITY_CONFIG
)


class TestSecurityConfig:
    """测试 SecurityConfig 类"""

    def test_default_initialization(self):
        """测试默认初始化"""
        config = SecurityConfig()

        assert config.strict_mode is True
        assert config.enable_hash_verification is True
        assert config.enable_ast_analysis is True
        assert config.enable_permission_check is True
        assert config.max_memory_mb == 512
        assert config.max_cpu_time == 30
        assert config.max_wall_time == 60
        assert config.enable_audit_logging is True
        assert config.enable_cache is True

    def test_custom_initialization(self):
        """测试自定义初始化"""
        config = SecurityConfig(
            strict_mode=False,
            max_memory_mb=1024,
            max_cpu_time=60
        )

        assert config.strict_mode is False
        assert config.max_memory_mb == 1024
        assert config.max_cpu_time == 60

    def test_allowed_imports(self):
        """测试允许的导入列表"""
        config = SecurityConfig()

        assert 'pandas' in config.allowed_imports
        assert 'numpy' in config.allowed_imports
        assert 'typing' in config.allowed_imports

    def test_forbidden_imports(self):
        """测试禁止的导入列表"""
        config = SecurityConfig()

        assert 'os' in config.forbidden_imports
        assert 'sys' in config.forbidden_imports
        assert 'subprocess' in config.forbidden_imports

    def test_forbidden_functions(self):
        """测试禁止的函数列表"""
        config = SecurityConfig()

        assert 'eval' in config.forbidden_functions
        assert 'exec' in config.forbidden_functions
        assert 'compile' in config.forbidden_functions

    def test_forbidden_attributes(self):
        """测试禁止的属性列表"""
        config = SecurityConfig()

        assert '__dict__' in config.forbidden_attributes
        assert '__class__' in config.forbidden_attributes

    def test_to_dict(self):
        """测试转换为字典"""
        config = SecurityConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert 'strict_mode' in config_dict
        assert 'max_memory_mb' in config_dict
        assert 'allowed_imports' in config_dict

    def test_validate_success(self):
        """测试验证成功"""
        config = SecurityConfig()
        assert config.validate() is True

    def test_validate_fail_negative_memory(self):
        """测试验证失败 - 负数内存"""
        config = SecurityConfig(max_memory_mb=-100)
        assert config.validate() is False

    def test_validate_fail_negative_cpu_time(self):
        """测试验证失败 - 负数CPU时间"""
        config = SecurityConfig(max_cpu_time=-10)
        assert config.validate() is False

    def test_validate_fail_negative_wall_time(self):
        """测试验证失败 - 负数墙钟时间"""
        config = SecurityConfig(max_wall_time=-5)
        assert config.validate() is False

    def test_validate_fail_empty_allowed_imports(self):
        """测试验证失败 - 空的允许导入列表"""
        config = SecurityConfig(allowed_imports=set())
        assert config.validate() is False

    def test_validate_fail_empty_forbidden_imports(self):
        """测试验证失败 - 空的禁止导入列表"""
        config = SecurityConfig(forbidden_imports=set())
        assert config.validate() is False

    def test_add_allowed_import(self):
        """测试添加允许的导入"""
        config = SecurityConfig()
        initial_count = len(config.allowed_imports)

        config.add_allowed_import('new_module')

        assert 'new_module' in config.allowed_imports
        assert len(config.allowed_imports) == initial_count + 1

    def test_add_allowed_import_conflict(self):
        """测试添加已在黑名单中的导入"""
        config = SecurityConfig()

        # 尝试添加已在黑名单中的模块
        config.add_allowed_import('os')

        # 应该不会被添加
        assert 'os' not in config.allowed_imports

    def test_remove_allowed_import(self):
        """测试移除允许的导入"""
        config = SecurityConfig()
        config.add_allowed_import('temp_module')

        config.remove_allowed_import('temp_module')

        assert 'temp_module' not in config.allowed_imports

    def test_add_forbidden_import(self):
        """测试添加禁止的导入"""
        config = SecurityConfig()
        initial_count = len(config.forbidden_imports)

        config.add_forbidden_import('bad_module')

        assert 'bad_module' in config.forbidden_imports
        assert len(config.forbidden_imports) == initial_count + 1

    def test_add_forbidden_import_removes_from_allowed(self):
        """测试添加禁止导入时从允许列表移除"""
        config = SecurityConfig()
        config.add_allowed_import('temp_module')

        config.add_forbidden_import('temp_module')

        assert 'temp_module' in config.forbidden_imports
        assert 'temp_module' not in config.allowed_imports

    def test_remove_forbidden_import(self):
        """测试移除禁止的导入"""
        config = SecurityConfig()
        config.add_forbidden_import('temp_bad_module')

        config.remove_forbidden_import('temp_bad_module')

        assert 'temp_bad_module' not in config.forbidden_imports

    def test_to_file(self):
        """测试保存到文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = SecurityConfig(strict_mode=False, max_memory_mb=256)
            config_file = Path(temp_dir) / 'config.json'

            config.to_file(str(config_file))

            assert config_file.exists()

            # 验证文件内容
            with open(config_file, 'r') as f:
                data = json.load(f)
                assert data['strict_mode'] is False
                assert data['max_memory_mb'] == 256

    def test_from_file_existing(self):
        """测试从文件加载 - 文件存在"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / 'config.json'

            # 先保存配置
            original_config = SecurityConfig(
                strict_mode=False,
                max_memory_mb=256,
                max_cpu_time=45
            )
            original_config.to_file(str(config_file))

            # 从文件加载
            loaded_config = SecurityConfig.from_file(str(config_file))

            assert loaded_config.strict_mode is False
            assert loaded_config.max_memory_mb == 256
            assert loaded_config.max_cpu_time == 45

    def test_from_file_not_existing(self):
        """测试从文件加载 - 文件不存在"""
        config = SecurityConfig.from_file('/nonexistent/config.json')

        # 应该返回默认配置
        assert config.strict_mode is True
        assert config.max_memory_mb == 512

    def test_default_security_config(self):
        """测试默认安全配置常量"""
        assert isinstance(DEFAULT_SECURITY_CONFIG, SecurityConfig)
        assert DEFAULT_SECURITY_CONFIG.strict_mode is True

    def test_development_security_config(self):
        """测试开发环境配置常量"""
        assert isinstance(DEVELOPMENT_SECURITY_CONFIG, SecurityConfig)
        assert DEVELOPMENT_SECURITY_CONFIG.strict_mode is False
        assert DEVELOPMENT_SECURITY_CONFIG.max_memory_mb == 1024

    def test_production_security_config(self):
        """测试生产环境配置常量"""
        assert isinstance(PRODUCTION_SECURITY_CONFIG, SecurityConfig)
        assert PRODUCTION_SECURITY_CONFIG.strict_mode is True
        assert PRODUCTION_SECURITY_CONFIG.max_memory_mb == 256
