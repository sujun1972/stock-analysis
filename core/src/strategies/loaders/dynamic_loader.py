"""
动态代码加载器模块

安全地加载和执行AI生成的策略代码（方案2 - AI代码生成）
"""

import types
import hashlib
from typing import Dict, Any, Type, Optional
from loguru import logger

from .base_loader import BaseLoader

try:
    from ...database.db_manager import DatabaseManager
    from ...exceptions import (
        StrategyLoadError,
        StrategySecurityError,
        CodeCompileError
    )
except ImportError:
    # 用于测试时的兼容
    DatabaseManager = None
    StrategyLoadError = ValueError
    StrategySecurityError = SecurityError
    CodeCompileError = RuntimeError

try:
    from ..security.code_sanitizer import CodeSanitizer
    from ..security.permission_checker import PermissionChecker
    from ..security.audit_logger import AuditLogger
except ImportError as e:
    logger.error(f"无法导入安全模块: {e}")
    CodeSanitizer = None
    PermissionChecker = None
    AuditLogger = None


class DynamicCodeLoader(BaseLoader):
    """
    动态代码加载器 - 支持方案2 (AI代码生成)

    安全地加载和执行AI生成的策略代码

    核心安全措施:
    1. 代码签名验证（哈希校验）
    2. AST语法树分析（CodeSanitizer）
    3. 权限检查（PermissionChecker）
    4. 受限命名空间（沙箱执行）
    5. 审计日志（AuditLogger）

    数据流:
    1. 从 ai_strategies 表读取代码
    2. 验证策略状态（is_enabled, validation_status）
    3. Core层独立安全验证（不信任Backend）
    4. 动态编译和加载代码
    5. 实例化策略类
    6. 附加元信息和审计
    """

    def __init__(self):
        """初始化动态代码加载器"""
        super().__init__()

        # 延迟初始化组件
        self._db = None
        self._sanitizer = None
        self._permission_checker = None
        self._audit_logger = None

        logger.info("DynamicCodeLoader 初始化完成")

    @property
    def db(self):
        """懒加载数据库管理器"""
        if self._db is None:
            if DatabaseManager is None:
                raise ImportError("DatabaseManager 未正确导入，请检查依赖")
            self._db = DatabaseManager()
        return self._db

    @property
    def sanitizer(self):
        """懒加载代码净化器"""
        if self._sanitizer is None:
            if CodeSanitizer is None:
                raise ImportError("CodeSanitizer 未正确导入，请检查安全模块")
            self._sanitizer = CodeSanitizer()
        return self._sanitizer

    @property
    def permission_checker(self):
        """懒加载权限检查器"""
        if self._permission_checker is None:
            if PermissionChecker is None:
                raise ImportError("PermissionChecker 未正确导入，请检查安全模块")
            self._permission_checker = PermissionChecker()
        return self._permission_checker

    @property
    def audit_logger(self):
        """懒加载审计日志"""
        if self._audit_logger is None:
            if AuditLogger is None:
                raise ImportError("AuditLogger 未正确导入，请检查安全模块")
            self._audit_logger = AuditLogger()
        return self._audit_logger

    def load_strategy(
        self,
        strategy_id: int,
        use_cache: bool = True,
        strict_mode: bool = True,
        **kwargs
    ):
        """
        从AI策略ID加载策略

        Args:
            strategy_id: ai_strategies表的ID
            use_cache: 是否使用缓存
            strict_mode: 严格模式（任何安全问题都拒绝加载）
            **kwargs: 额外参数

        Returns:
            策略实例

        Raises:
            ValueError: 策略不存在或无效
            StrategySecurityError: 安全验证失败
            CodeCompileError: 代码编译失败
        """
        # 检查缓存
        if use_cache and strategy_id in self._cache:
            logger.debug(f"从缓存加载AI策略: ID={strategy_id}")
            return self._cache[strategy_id]

        logger.info(f"开始加载AI策略: ID={strategy_id}, 严格模式={strict_mode}")

        # 从数据库加载代码
        strategy_data = self._load_strategy_from_db(strategy_id)

        # 验证策略状态
        if not strategy_data.get('is_enabled', False):
            raise ValueError(f"AI策略已禁用: ID={strategy_id}")

        if strategy_data.get('validation_status') == 'failed':
            raise ValueError(f"AI策略验证失败: ID={strategy_id}")

        # Core层独立安全验证（不信任Backend的验证结果）
        code = strategy_data['generated_code']
        expected_hash = strategy_data.get('code_hash', '')

        logger.info(f"开始安全验证: 代码长度={len(code)}字符, 预期哈希={expected_hash[:8]}...")

        # 步骤1: 代码净化
        sanitize_result = self.sanitizer.sanitize(
            code=code,
            expected_hash=expected_hash if expected_hash else None,
            strict_mode=strict_mode
        )

        if not sanitize_result['safe']:
            self.audit_logger.log_security_violation(
                strategy_id=strategy_id,
                violation_type='sanitize_failed',
                details=sanitize_result
            )
            raise StrategySecurityError(
                f"代码安全验证失败 (ID={strategy_id}): {sanitize_result['errors']}"
            )

        logger.info(f"代码净化完成: 风险等级={sanitize_result['risk_level']}")

        # 步骤2: 权限检查
        permission_result = self.permission_checker.check_permissions(code)

        if not permission_result['allowed']:
            self.audit_logger.log_security_violation(
                strategy_id=strategy_id,
                violation_type='permission_denied',
                details=permission_result
            )
            raise StrategySecurityError(
                f"代码权限检查失败 (ID={strategy_id}): {permission_result['violations']}"
            )

        logger.success("权限检查通过")

        # 步骤3: 动态加载代码
        try:
            strategy_class = self._compile_and_load(
                code=sanitize_result['sanitized_code'],
                class_name=strategy_data['class_name'],
                module_name=strategy_data['strategy_name']
            )
        except Exception as e:
            logger.error(f"动态加载失败 (ID={strategy_id}): {e}")
            raise CodeCompileError(f"代码编译失败: {e}") from e

        logger.success(f"代码加载成功: {strategy_data['class_name']}")

        # 步骤4: 实例化策略
        try:
            strategy = strategy_class(
                name=strategy_data['strategy_name'],
                config=strategy_data.get('config', {})
            )
        except Exception as e:
            logger.error(f"策略实例化失败 (ID={strategy_id}): {e}")
            raise StrategyLoadError(f"策略实例化失败: {e}") from e

        # 步骤5: 附加元信息
        strategy._strategy_id = strategy_id
        strategy._strategy_type = 'dynamic'
        strategy._code_hash = expected_hash
        strategy._risk_level = sanitize_result['risk_level']
        strategy._validation_warnings = sanitize_result.get('warnings', [])

        # 步骤6: 缓存
        if use_cache:
            self._cache[strategy_id] = strategy

        # 步骤7: 审计日志
        self.audit_logger.log_strategy_load(
            strategy_id=strategy_id,
            strategy_type='dynamic',
            strategy_class=strategy_data['class_name'],
            code_hash=expected_hash,
            validation_result=sanitize_result
        )

        logger.success(
            f"AI策略加载完成: {strategy_data['strategy_name']} "
            f"(ID={strategy_id}, 风险={sanitize_result['risk_level']})"
        )

        return strategy

    def _load_strategy_from_db(self, strategy_id: int) -> Dict[str, Any]:
        """
        从数据库加载AI策略

        Args:
            strategy_id: 策略ID

        Returns:
            策略数据字典

        Raises:
            ValueError: 策略不存在
        """
        query = """
            SELECT
                id, strategy_name, class_name,
                generated_code, code_hash,
                validation_status, test_status,
                is_enabled, version,
                created_at, updated_at
            FROM ai_strategies
            WHERE id = %s
        """

        try:
            result = self.db.execute_query(query, (strategy_id,))

            if not result:
                raise ValueError(f"AI策略不存在: ID={strategy_id}")

            row = result[0]

            return {
                'id': row[0],
                'strategy_name': row[1],
                'class_name': row[2],
                'generated_code': row[3],
                'code_hash': row[4],
                'validation_status': row[5],
                'test_status': row[6],
                'is_enabled': row[7],
                'version': row[8],
                'created_at': row[9],
                'updated_at': row[10],
                'config': {}  # AI策略可能没有额外配置
            }

        except Exception as e:
            logger.error(f"加载AI策略失败: ID={strategy_id}, 错误: {e}")
            raise

    def _compile_and_load(
        self,
        code: str,
        class_name: str,
        module_name: str
    ) -> Type:
        """
        编译并加载代码

        Args:
            code: Python代码
            class_name: 策略类名
            module_name: 模块名

        Returns:
            策略类

        Raises:
            CodeCompileError: 编译失败
            AttributeError: 类不存在
            TypeError: 类型错误
        """
        # 创建模块
        module = types.ModuleType(module_name)
        module.__file__ = f"<dynamic:{module_name}>"

        # 准备受限的全局命名空间
        restricted_globals = self._create_restricted_globals()

        # 执行代码
        try:
            exec(code, restricted_globals, module.__dict__)
        except Exception as e:
            logger.error(f"代码执行失败: {e}")
            raise CodeCompileError(f"代码执行错误: {e}") from e

        # 获取策略类
        if not hasattr(module, class_name):
            raise AttributeError(f"模块中未找到类: {class_name}")

        strategy_class = getattr(module, class_name)

        # 验证是BaseStrategy的子类
        from ..base_strategy import BaseStrategy

        if not issubclass(strategy_class, BaseStrategy):
            raise TypeError(f"{class_name} 必须继承自 BaseStrategy")

        logger.debug(f"策略类验证通过: {class_name}")

        return strategy_class

    def _create_restricted_globals(self) -> Dict[str, Any]:
        """
        创建受限的全局命名空间

        只允许访问安全的内置函数和模块

        Returns:
            受限的全局变量字典
        """
        import pandas as pd
        import numpy as np
        from loguru import logger as loguru_logger

        # 只暴露安全的内置函数
        safe_builtins = {
            'abs': abs,
            'all': all,
            'any': any,
            'bool': bool,
            'dict': dict,
            'float': float,
            'int': int,
            'len': len,
            'list': list,
            'max': max,
            'min': min,
            'range': range,
            'round': round,
            'set': set,
            'str': str,
            'sum': sum,
            'tuple': tuple,
            'zip': zip,
            'enumerate': enumerate,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'type': type,
            'sorted': sorted,
            'reversed': reversed,
            'map': map,
            'filter': filter,
            # 必要的特殊函数（用于类定义和导入）
            '__build_class__': __builtins__['__build_class__'],
            '__import__': __builtins__['__import__'],
            '__name__': '__main__',
        }

        # 允许的模块
        safe_modules = {
            'pd': pd,
            'pandas': pd,
            'np': np,
            'numpy': np,
            'logger': loguru_logger,
        }

        # 导入BaseStrategy等必要类
        from ..base_strategy import BaseStrategy, StrategyConfig
        from ..signal_generator import SignalGenerator

        safe_modules.update({
            'BaseStrategy': BaseStrategy,
            'StrategyConfig': StrategyConfig,
            'SignalGenerator': SignalGenerator,
        })

        # 导入必要的类型注解
        from typing import Dict, List, Optional, Any
        safe_modules.update({
            'Dict': Dict,
            'List': List,
            'Optional': Optional,
            'Any': Any,
        })

        logger.debug(f"创建受限命名空间: {len(safe_builtins)} 个内置函数, {len(safe_modules)} 个模块")

        return {
            '__builtins__': safe_builtins,
            **safe_modules
        }

    def reload_strategy(self, strategy_id: int, strict_mode: bool = True):
        """
        重新加载策略（清除缓存后加载）

        Args:
            strategy_id: 策略ID
            strict_mode: 严格模式

        Returns:
            新的策略实例
        """
        self.clear_cache(strategy_id)
        return self.load_strategy(strategy_id, use_cache=True, strict_mode=strict_mode)

    def batch_load_strategies(
        self,
        strategy_ids: list[int],
        use_cache: bool = True,
        strict_mode: bool = True
    ) -> Dict[int, Any]:
        """
        批量加载策略

        Args:
            strategy_ids: 策略ID列表
            use_cache: 是否使用缓存
            strict_mode: 严格模式

        Returns:
            {strategy_id: strategy_instance} 字典
        """
        strategies = {}

        for strategy_id in strategy_ids:
            try:
                strategy = self.load_strategy(
                    strategy_id,
                    use_cache=use_cache,
                    strict_mode=strict_mode
                )
                strategies[strategy_id] = strategy
            except Exception as e:
                logger.error(f"加载策略失败: ID={strategy_id}, 错误: {e}")
                # 继续加载其他策略
                continue

        logger.info(f"批量加载完成: 成功 {len(strategies)}/{len(strategy_ids)}")

        return strategies

    def list_available_strategies(
        self,
        enabled_only: bool = True,
        validated_only: bool = True
    ) -> list[Dict[str, Any]]:
        """
        列出可用的AI策略

        Args:
            enabled_only: 只返回启用的策略
            validated_only: 只返回验证通过的策略

        Returns:
            策略列表
        """
        query = """
            SELECT
                id, strategy_name, class_name,
                validation_status, test_status,
                is_enabled, version, created_at, updated_at
            FROM ai_strategies
            WHERE 1=1
        """

        params = []

        if enabled_only:
            query += " AND is_enabled = %s"
            params.append(True)

        if validated_only:
            query += " AND validation_status = %s"
            params.append('passed')

        query += " ORDER BY updated_at DESC"

        try:
            results = self.db.execute_query(query, tuple(params))

            strategies = []
            for row in results:
                strategies.append({
                    'id': row[0],
                    'strategy_name': row[1],
                    'class_name': row[2],
                    'validation_status': row[3],
                    'test_status': row[4],
                    'is_enabled': row[5],
                    'version': row[6],
                    'created_at': row[7],
                    'updated_at': row[8],
                })

            logger.info(f"查询到 {len(strategies)} 个AI策略")
            return strategies

        except Exception as e:
            logger.error(f"查询AI策略失败: {e}")
            return []

    def __repr__(self) -> str:
        return f"DynamicCodeLoader(cached={len(self._cache)})"


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例：加载AI策略
    loader = DynamicCodeLoader()

    try:
        # 加载单个策略（严格模式）
        strategy = loader.load_strategy(strategy_id=1, strict_mode=True)
        print(f"策略加载成功: {strategy}")
        print(f"风险等级: {strategy._risk_level}")

        # 批量加载
        strategies = loader.batch_load_strategies([1, 2, 3], strict_mode=True)
        print(f"批量加载: {len(strategies)} 个策略")

        # 列出可用策略
        available = loader.list_available_strategies()
        print(f"可用策略: {len(available)} 个")

    except Exception as e:
        logger.error(f"示例执行失败: {e}")
