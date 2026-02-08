"""
安全配置管理

管理策略安全相关的配置参数
"""

from typing import Dict, Any, Set
from dataclasses import dataclass, field
from pathlib import Path
import json
from loguru import logger


@dataclass
class SecurityConfig:
    """
    安全配置类

    管理所有安全相关的配置参数
    """

    # 代码验证配置
    strict_mode: bool = True
    enable_hash_verification: bool = True
    enable_ast_analysis: bool = True
    enable_permission_check: bool = True

    # 资源限制配置
    max_memory_mb: int = 512
    max_cpu_time: int = 30
    max_wall_time: int = 60

    # 审计配置
    enable_audit_logging: bool = True
    audit_log_dir: str = "logs/audit"
    audit_retention_days: int = 90

    # 缓存配置
    enable_cache: bool = True
    cache_ttl_minutes: int = 30
    cache_max_size: int = 100

    # 白名单/黑名单配置
    allowed_imports: Set[str] = field(default_factory=lambda: {
        'typing', 'types', 'dataclasses', 'enum', 'abc',
        'pandas', 'numpy', 'loguru',
        'core.strategies.base_strategy',
        'core.strategies.signal_generator',
        'datetime', 'math',
    })

    forbidden_imports: Set[str] = field(default_factory=lambda: {
        'os', 'sys', 'subprocess', 'socket', 'urllib', 'requests',
        'http', 'ftplib', 'smtplib', 'telnetlib',
        'pickle', 'shelve', 'marshal', 'dill',
        '__builtin__', 'builtins', 'importlib',
        'ctypes', 'cffi',
    })

    forbidden_functions: Set[str] = field(default_factory=lambda: {
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input',
        'getattr', 'setattr', 'delattr', 'hasattr',
        'globals', 'locals', 'vars', 'dir',
    })

    forbidden_attributes: Set[str] = field(default_factory=lambda: {
        '__dict__', '__class__', '__bases__', '__subclasses__',
        '__code__', '__globals__', '__closure__',
    })

    # 风险等级阈值
    max_warnings_for_low_risk: int = 2
    max_warnings_for_medium_risk: int = 5

    @classmethod
    def from_file(cls, config_file: str) -> 'SecurityConfig':
        """
        从配置文件加载

        Args:
            config_file: 配置文件路径 (JSON格式)

        Returns:
            SecurityConfig实例
        """
        config_path = Path(config_file)

        if not config_path.exists():
            logger.warning(f"配置文件不存在: {config_file}, 使用默认配置")
            return cls()

        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # 转换集合类型
            for key in ['allowed_imports', 'forbidden_imports',
                       'forbidden_functions', 'forbidden_attributes']:
                if key in config_data:
                    config_data[key] = set(config_data[key])

            logger.info(f"已从文件加载安全配置: {config_file}")
            return cls(**config_data)

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}, 使用默认配置")
            return cls()

    def to_file(self, config_file: str):
        """
        保存到配置文件

        Args:
            config_file: 配置文件路径 (JSON格式)
        """
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # 转换为可序列化的格式
        config_data = self.to_dict()
        for key in ['allowed_imports', 'forbidden_imports',
                   'forbidden_functions', 'forbidden_attributes']:
            if key in config_data:
                config_data[key] = list(config_data[key])

        try:
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            logger.info(f"已保存安全配置到: {config_file}")

        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'strict_mode': self.strict_mode,
            'enable_hash_verification': self.enable_hash_verification,
            'enable_ast_analysis': self.enable_ast_analysis,
            'enable_permission_check': self.enable_permission_check,
            'max_memory_mb': self.max_memory_mb,
            'max_cpu_time': self.max_cpu_time,
            'max_wall_time': self.max_wall_time,
            'enable_audit_logging': self.enable_audit_logging,
            'audit_log_dir': self.audit_log_dir,
            'audit_retention_days': self.audit_retention_days,
            'enable_cache': self.enable_cache,
            'cache_ttl_minutes': self.cache_ttl_minutes,
            'cache_max_size': self.cache_max_size,
            'allowed_imports': self.allowed_imports,
            'forbidden_imports': self.forbidden_imports,
            'forbidden_functions': self.forbidden_functions,
            'forbidden_attributes': self.forbidden_attributes,
            'max_warnings_for_low_risk': self.max_warnings_for_low_risk,
            'max_warnings_for_medium_risk': self.max_warnings_for_medium_risk,
        }

    def validate(self) -> bool:
        """
        验证配置有效性

        Returns:
            配置是否有效
        """
        errors = []

        # 检查资源限制
        if self.max_memory_mb <= 0:
            errors.append("max_memory_mb 必须大于0")

        if self.max_cpu_time <= 0:
            errors.append("max_cpu_time 必须大于0")

        if self.max_wall_time <= 0:
            errors.append("max_wall_time 必须大于0")

        # 检查缓存配置
        if self.cache_ttl_minutes <= 0:
            errors.append("cache_ttl_minutes 必须大于0")

        if self.cache_max_size <= 0:
            errors.append("cache_max_size 必须大于0")

        # 检查审计配置
        if self.audit_retention_days <= 0:
            errors.append("audit_retention_days 必须大于0")

        # 检查白名单/黑名单
        if not self.allowed_imports:
            errors.append("allowed_imports 不能为空")

        if not self.forbidden_imports:
            errors.append("forbidden_imports 不能为空")

        # 检查冲突
        conflicts = self.allowed_imports & self.forbidden_imports
        if conflicts:
            errors.append(f"allowed_imports 和 forbidden_imports 有冲突: {conflicts}")

        if errors:
            for error in errors:
                logger.error(f"配置验证失败: {error}")
            return False

        logger.info("配置验证通过")
        return True

    def add_allowed_import(self, module_name: str):
        """添加允许的导入模块"""
        if module_name in self.forbidden_imports:
            logger.warning(f"模块 {module_name} 在黑名单中，无法添加到白名单")
            return

        self.allowed_imports.add(module_name)
        logger.info(f"已添加允许导入: {module_name}")

    def remove_allowed_import(self, module_name: str):
        """移除允许的导入模块"""
        self.allowed_imports.discard(module_name)
        logger.info(f"已移除允许导入: {module_name}")

    def add_forbidden_import(self, module_name: str):
        """添加禁止的导入模块"""
        self.forbidden_imports.add(module_name)

        # 同时从白名单中移除
        self.allowed_imports.discard(module_name)
        logger.warning(f"已添加禁止导入: {module_name}")

    def remove_forbidden_import(self, module_name: str):
        """移除禁止的导入模块"""
        self.forbidden_imports.discard(module_name)
        logger.info(f"已移除禁止导入: {module_name}")


# 默认安全配置实例
DEFAULT_SECURITY_CONFIG = SecurityConfig()


# 开发环境配置 (更宽松)
DEVELOPMENT_SECURITY_CONFIG = SecurityConfig(
    strict_mode=False,
    max_memory_mb=1024,
    max_cpu_time=60,
    max_wall_time=120,
    enable_cache=True,
)


# 生产环境配置 (更严格)
PRODUCTION_SECURITY_CONFIG = SecurityConfig(
    strict_mode=True,
    max_memory_mb=256,
    max_cpu_time=15,
    max_wall_time=30,
    enable_cache=True,
    cache_ttl_minutes=60,
)
