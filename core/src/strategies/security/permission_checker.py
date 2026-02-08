"""
权限检查器

检查策略代码是否只访问允许的资源
"""

from typing import Dict, Any, Set
from loguru import logger


class PermissionChecker:
    """
    权限检查器

    检查策略代码是否只访问允许的资源
    """

    # 允许的pandas操作
    ALLOWED_PANDAS_METHODS = {
        # DataFrame方法
        'head', 'tail', 'describe', 'info', 'shape', 'columns', 'index',
        'iloc', 'loc', 'at', 'iat',
        'mean', 'median', 'sum', 'std', 'var', 'min', 'max',
        'rolling', 'expanding', 'ewm',
        'shift', 'diff', 'pct_change',
        'fillna', 'dropna', 'isna', 'notna',
        'sort_values', 'sort_index',
        'groupby', 'pivot', 'pivot_table',
        'merge', 'join', 'concat',
        'apply', 'map', 'applymap',
        'copy', 'astype',

        # Series方法
        'nlargest', 'nsmallest', 'rank',

        # 时间序列方法
        'resample', 'between_time', 'at_time',

        # 索引方法
        'reset_index', 'set_index', 'reindex',
    }

    # 允许的numpy函数
    ALLOWED_NUMPY_FUNCTIONS = {
        'array', 'zeros', 'ones', 'full', 'arange', 'linspace',
        'mean', 'median', 'sum', 'std', 'var', 'min', 'max',
        'abs', 'sqrt', 'exp', 'log', 'log10', 'log2',
        'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan',
        'clip', 'where', 'nan', 'isnan', 'isfinite', 'isinf',
        'concatenate', 'stack', 'vstack', 'hstack',
        'reshape', 'flatten', 'ravel',
        'transpose', 'swapaxes',
        'corrcoef', 'cov',
        'percentile', 'quantile',
    }

    # 禁止的文件系统访问模式
    FORBIDDEN_FILESYSTEM_PATTERNS = [
        'open(', 'pathlib', 'Path(', 'with open',
        'file(', 'os.path', 'glob.glob', 'shutil'
    ]

    # 禁止的网络访问模式
    FORBIDDEN_NETWORK_PATTERNS = [
        'socket', 'urllib', 'requests', 'http.client',
        'ftplib', 'smtplib', 'telnetlib', 'xmlrpc',
        'websocket', 'aiohttp'
    ]

    # 禁止的系统命令模式
    FORBIDDEN_SYSTEM_PATTERNS = [
        'os.system', 'subprocess', 'popen', 'spawn',
        'call(', 'check_output', 'check_call'
    ]

    # 禁止的数据库访问模式
    FORBIDDEN_DATABASE_PATTERNS = [
        'psycopg2', 'pymongo', 'redis', 'sqlite3',
        'sqlalchemy', 'mysql', 'cx_Oracle'
    ]

    def check_permissions(self, code: str) -> Dict[str, Any]:
        """
        检查代码权限

        Returns:
            {
                'allowed': bool,
                'violations': List[str]
            }
        """
        violations = []

        # 检查是否试图访问文件系统
        for pattern in self.FORBIDDEN_FILESYSTEM_PATTERNS:
            if pattern in code:
                violations.append(f"不允许访问文件系统: {pattern}")

        # 检查是否试图网络访问
        for pattern in self.FORBIDDEN_NETWORK_PATTERNS:
            if pattern in code:
                violations.append(f"不允许网络访问: {pattern}")

        # 检查是否试图执行系统命令
        for pattern in self.FORBIDDEN_SYSTEM_PATTERNS:
            if pattern in code:
                violations.append(f"不允许执行系统命令: {pattern}")

        # 检查是否试图直接访问数据库
        for pattern in self.FORBIDDEN_DATABASE_PATTERNS:
            if pattern in code:
                violations.append(f"不允许直接访问数据库: {pattern}")

        allowed = len(violations) == 0

        if not allowed:
            logger.warning(f"权限检查失败: {violations}")
        else:
            logger.debug("权限检查通过")

        return {
            'allowed': allowed,
            'violations': violations
        }

    def check_method_access(self, code: str, strict: bool = False) -> Dict[str, Any]:
        """
        检查方法访问权限 (可选的更细粒度检查)

        Args:
            code: 代码字符串
            strict: 是否启用严格模式 (只允许白名单中的方法)

        Returns:
            {
                'allowed': bool,
                'warnings': List[str]
            }
        """
        warnings = []

        if strict:
            # TODO: 实现严格模式下的方法白名单检查
            # 需要更复杂的AST分析来提取方法调用
            pass

        return {
            'allowed': True,
            'warnings': warnings
        }
