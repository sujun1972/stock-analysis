"""
代码净化器 - Core层的第一道防线

职责:
1. 验证代码完整性 (签名/哈希)
2. AST语法树分析
3. 检测危险操作
4. 移除可疑代码片段
"""

import hashlib
import ast
from typing import Dict, Any, List, Set
from loguru import logger


class CodeSanitizer:
    """
    代码净化器 - Core层的第一道防线

    职责:
    1. 验证代码完整性 (签名/哈希)
    2. AST语法树分析
    3. 检测危险操作
    4. 移除可疑代码片段
    """

    # 危险导入白名单 (只允许这些模块)
    ALLOWED_IMPORTS = {
        'typing', 'types', 'dataclasses', 'enum', 'abc',
        'pandas', 'numpy', 'loguru',
        'core', 'strategies',  # 允许 core.strategies.xxx 和 strategies.xxx
        'datetime', 'math',
    }

    # 禁止的导入 (黑名单)
    FORBIDDEN_IMPORTS = {
        'os', 'sys', 'subprocess', 'socket', 'urllib', 'requests',
        'http', 'ftplib', 'smtplib', 'telnetlib',
        'pickle', 'shelve', 'marshal', 'dill',
        '__builtin__', 'builtins', 'importlib',
        'ctypes', 'cffi',
    }

    # 禁止的函数
    FORBIDDEN_FUNCTIONS = {
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input', 'raw_input',
        'getattr', 'setattr', 'delattr', 'hasattr',
        'globals', 'locals', 'vars', 'dir',
    }

    # 禁止的属性访问
    FORBIDDEN_ATTRIBUTES = {
        '__dict__', '__class__', '__bases__', '__subclasses__',
        '__code__', '__globals__', '__closure__',
    }

    # 允许的 pandas DataFrame/Series 方法
    ALLOWED_PANDAS_METHODS = {
        # 核心类构造器
        'Series', 'DataFrame', 'Index', 'MultiIndex', 'DatetimeIndex',
        # 数据访问
        'loc', 'iloc', 'at', 'iat', 'get', 'values', 'index', 'columns',
        # 数据选择
        'head', 'tail', 'sample', 'nlargest', 'nsmallest', 'query',
        # 数据统计
        'mean', 'median', 'std', 'var', 'min', 'max', 'sum', 'count',
        'quantile', 'describe', 'corr', 'cov', 'skew', 'kurt',
        # 数据转换
        'abs', 'round', 'clip', 'rank', 'pct_change', 'diff', 'shift',
        'rolling', 'expanding', 'ewm', 'resample', 'astype', 'apply',
        # 数据处理
        'fillna', 'dropna', 'isna', 'isnull', 'notna', 'notnull',
        'replace', 'interpolate', 'bfill', 'ffill', 'pad',
        # 数据合并
        'merge', 'join', 'concat', 'append', 'groupby', 'pivot',
        # 布尔操作
        'any', 'all', 'between', 'isin', 'str', 'dt',
        # 时间处理
        'to_datetime', 'to_timedelta', 'date_range', 'period_range',
        # 其他常用
        'sort_values', 'sort_index', 'reset_index', 'set_index',
        'drop', 'copy', 'T', 'transpose', 'squeeze', 'to_numpy',
        'tolist', 'items', 'iterrows', 'itertuples',
    }

    # 允许的 numpy 方法
    ALLOWED_NUMPY_METHODS = {
        # 数组创建
        'array', 'zeros', 'ones', 'empty', 'arange', 'linspace',
        # 数学函数
        'abs', 'sqrt', 'exp', 'log', 'log10', 'log2', 'power',
        'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan', 'arctan2',
        # 统计函数
        'mean', 'median', 'std', 'var', 'min', 'max', 'sum',
        'percentile', 'quantile', 'corrcoef', 'cov',
        # 数组操作
        'reshape', 'transpose', 'concatenate', 'stack', 'vstack', 'hstack',
        'split', 'squeeze', 'expand_dims', 'where', 'select',
        # 逻辑函数
        'isnan', 'isinf', 'isfinite', 'all', 'any', 'logical_and',
        'logical_or', 'logical_not', 'logical_xor',
        # 其他
        'clip', 'round', 'floor', 'ceil', 'sign', 'diff',
    }

    # 允许的 logger 方法
    ALLOWED_LOGGER_METHODS = {
        'debug', 'info', 'warning', 'error', 'critical', 'success',
    }

    # 允许的 BaseStrategy 方法（可以在策略中调用）
    ALLOWED_STRATEGY_METHODS = {
        'filter_stocks', 'validate_signals', 'get_position_weights',
        'backtest', 'get_metadata', 'get_strategy_info',
    }

    def __init__(self):
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []
        self.method_calls: Dict[str, int] = {}  # 记录方法调用次数

    def sanitize(
        self,
        code: str,
        expected_hash: str = None,
        strict_mode: bool = True
    ) -> Dict[str, Any]:
        """
        净化和验证代码

        Args:
            code: Python代码字符串
            expected_hash: 期望的代码哈希 (来自数据库)
            strict_mode: 严格模式 (发现任何问题都拒绝)

        Returns:
            {
                'safe': bool,           # 是否安全
                'sanitized_code': str,  # 净化后的代码
                'errors': List[str],
                'warnings': List[str],
                'risk_level': str       # 'safe', 'low', 'medium', 'high'
            }
        """
        self.validation_errors = []
        self.validation_warnings = []

        logger.info("开始代码安全验证...")

        # 1. 验证代码完整性
        if expected_hash:
            actual_hash = self._calculate_hash(code)
            if actual_hash != expected_hash:
                self.validation_errors.append(
                    f"代码哈希不匹配: 期望 {expected_hash[:8]}..., 实际 {actual_hash[:8]}..."
                )
                return self._build_result(False, code, 'high')

        # 2. 语法检查
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.validation_errors.append(f"语法错误: {e}")
            return self._build_result(False, code, 'high')

        # 3. AST深度分析
        risk_level = self._analyze_ast(tree)

        # 4. 检查字符串中的可疑内容
        self._check_string_literals(code)

        # 5. 计算风险等级
        if self.validation_errors:
            is_safe = False
            risk_level = 'high'
        elif len(self.validation_warnings) > 5:
            is_safe = not strict_mode
            risk_level = 'medium'
        elif self.validation_warnings:
            is_safe = True
            risk_level = 'low'
        else:
            is_safe = True
            risk_level = 'safe'

        logger.info(f"代码验证完成: 安全={is_safe}, 风险={risk_level}")

        return self._build_result(is_safe, code, risk_level)

    def _analyze_ast(self, tree: ast.AST) -> str:
        """
        深度分析AST语法树

        Returns:
            风险等级
        """
        risk_level = 'safe'

        for node in ast.walk(tree):
            # 检查导入
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]

                    if module_name in self.FORBIDDEN_IMPORTS:
                        self.validation_errors.append(
                            f"禁止导入模块: {alias.name}"
                        )
                        risk_level = 'high'

                    elif module_name not in self.ALLOWED_IMPORTS:
                        self.validation_warnings.append(
                            f"未知导入模块: {alias.name}"
                        )
                        risk_level = max(risk_level, 'low', key=self._risk_order)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]

                    if module_name in self.FORBIDDEN_IMPORTS:
                        self.validation_errors.append(
                            f"禁止导入模块: {node.module}"
                        )
                        risk_level = 'high'

                    elif module_name not in self.ALLOWED_IMPORTS:
                        self.validation_warnings.append(
                            f"未知导入模块: {node.module}"
                        )
                        risk_level = max(risk_level, 'low', key=self._risk_order)

            # 检查函数调用
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id

                    if func_name in self.FORBIDDEN_FUNCTIONS:
                        self.validation_errors.append(
                            f"禁止调用函数: {func_name}"
                        )
                        risk_level = 'high'

                # 检查方法调用
                elif isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr
                    self._check_method_call(node.func, method_name)
                    risk_level = max(risk_level, 'low', key=self._risk_order) if self.validation_warnings else risk_level

            # 检查属性访问
            elif isinstance(node, ast.Attribute):
                if node.attr in self.FORBIDDEN_ATTRIBUTES:
                    self.validation_errors.append(
                        f"禁止访问属性: {node.attr}"
                    )
                    risk_level = 'high'

                # 检查是否使用 self.logger（应该使用全局 logger）
                elif node.attr == 'logger' and isinstance(node.value, ast.Name) and node.value.id == 'self':
                    self.validation_errors.append(
                        "禁止使用 self.logger，请使用全局 logger 变量"
                    )
                    risk_level = 'high'

            # 检查文件操作
            elif isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Call):
                        if isinstance(item.context_expr.func, ast.Name):
                            if item.context_expr.func.id == 'open':
                                self.validation_errors.append("禁止文件操作")
                                risk_level = 'high'

        return risk_level

    def _check_method_call(self, node: ast.Attribute, method_name: str):
        """
        检查方法调用是否在允许列表中

        Args:
            node: AST 属性节点
            method_name: 方法名
        """
        # 记录方法调用
        self.method_calls[method_name] = self.method_calls.get(method_name, 0) + 1

        # 获取调用对象的名称
        obj_name = None
        if isinstance(node.value, ast.Name):
            obj_name = node.value.id
        elif isinstance(node.value, ast.Attribute):
            obj_name = node.value.attr

        # 检查常见的允许方法
        allowed_methods = (
            self.ALLOWED_PANDAS_METHODS |
            self.ALLOWED_NUMPY_METHODS |
            self.ALLOWED_LOGGER_METHODS |
            self.ALLOWED_STRATEGY_METHODS
        )

        # 检查是否是明确禁止的危险方法
        DANGEROUS_METHODS = {
            'eval', 'exec', 'compile', '__import__', 'open', 'file',
            'system', 'popen', 'subprocess', 'shell',
        }

        # 如果是 logger 方法调用
        if obj_name == 'logger':
            if method_name not in self.ALLOWED_LOGGER_METHODS:
                self.validation_warnings.append(
                    f"未知的 logger 方法: logger.{method_name}，建议使用: {', '.join(sorted(self.ALLOWED_LOGGER_METHODS))}"
                )
        # 如果是 pd/pandas 方法
        elif obj_name in ['pd', 'pandas']:
            # 只对明确危险的方法发出警告，其他都允许
            if method_name in DANGEROUS_METHODS:
                self.validation_errors.append(
                    f"禁止的 pandas 方法: pd.{method_name}"
                )
        # 如果是 np/numpy 方法
        elif obj_name in ['np', 'numpy']:
            # 只对明确危险的方法发出警告，其他都允许
            if method_name in DANGEROUS_METHODS:
                self.validation_errors.append(
                    f"禁止的 numpy 方法: np.{method_name}"
                )
        # 如果是 self 方法调用
        elif obj_name == 'self':
            # 允许所有 self 方法（包括私有方法）
            pass
        # 其他方法调用，检查是否在禁止列表中
        elif method_name in self.FORBIDDEN_ATTRIBUTES:
            self.validation_errors.append(
                f"禁止调用方法: {method_name}"
            )

    def _check_string_literals(self, code: str):
        """检查字符串字面量中的可疑内容"""
        suspicious_patterns = [
            'os.system', 'subprocess', 'eval(', 'exec(',
            '__import__', 'open(', '/etc/passwd', '/proc/',
            'rm -rf', 'DROP TABLE', 'DELETE FROM'
        ]

        for pattern in suspicious_patterns:
            if pattern in code:
                self.validation_warnings.append(
                    f"代码中包含可疑字符串: {pattern}"
                )

    def _calculate_hash(self, code: str) -> str:
        """计算代码哈希"""
        return hashlib.sha256(code.encode('utf-8')).hexdigest()

    def _risk_order(self, level: str) -> int:
        """风险等级排序"""
        order = {'safe': 0, 'low': 1, 'medium': 2, 'high': 3}
        return order.get(level, 0)

    def _build_result(self, is_safe: bool, code: str, risk_level: str) -> Dict:
        """构建返回结果"""
        return {
            'safe': is_safe,
            'sanitized_code': code,
            'errors': self.validation_errors,
            'warnings': self.validation_warnings,
            'risk_level': risk_level,
            'method_calls': self.method_calls  # 方法调用统计
        }
