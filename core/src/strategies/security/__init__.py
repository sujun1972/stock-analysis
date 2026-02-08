"""
策略安全模块

提供策略加载和执行的多层安全防护:
1. 代码净化与验证 (CodeSanitizer)
2. 权限检查 (PermissionChecker)
3. 资源限制 (ResourceLimiter)
4. 审计日志 (AuditLogger)
5. 安全配置管理 (SecurityConfig)
"""

from .code_sanitizer import CodeSanitizer
from .permission_checker import PermissionChecker
from .resource_limiter import ResourceLimiter, ResourceLimitError
from .audit_logger import AuditLogger
from .security_config import (
    SecurityConfig,
    DEFAULT_SECURITY_CONFIG,
    DEVELOPMENT_SECURITY_CONFIG,
    PRODUCTION_SECURITY_CONFIG
)

__all__ = [
    # 核心安全组件
    'CodeSanitizer',
    'PermissionChecker',
    'ResourceLimiter',
    'AuditLogger',

    # 配置管理
    'SecurityConfig',
    'DEFAULT_SECURITY_CONFIG',
    'DEVELOPMENT_SECURITY_CONFIG',
    'PRODUCTION_SECURITY_CONFIG',

    # 异常
    'ResourceLimitError',
]
