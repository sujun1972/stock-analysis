# Core 策略系统改造方案

**文档版本**: v1.0.0
**创建日期**: 2026-02-08
**作者**: Architecture Team
**状态**: 📋 设计阶段 - 待评审

---

## 📋 目录

- [概述](#概述)
- [整合两个方案](#整合两个方案)
- [Core层架构设计](#core层架构设计)
- [安全防范措施](#安全防范措施)
- [新增模块详解](#新增模块详解)
- [现有模块改造](#现有模块改造)
- [数据流设计](#数据流设计)
- [错误处理与日志](#错误处理与日志)
- [性能优化](#性能优化)
- [测试策略](#测试策略)
- [实施计划](#实施计划)

---

## 概述

### 背景

需要改造 Core 项目以同时支持两种策略管理方案：

1. **参数配置方案** (`strategy_config_management.md`)
   - 预定义策略类型 + 参数配置
   - 配置存储在数据库
   - 适合标准策略和新手用户

2. **AI代码生成方案** (`ai_strategy_generation.md`)
   - AI生成完整策略类代码
   - 动态加载和执行
   - 适合创新策略和高级用户

### 改造目标

1. ✅ **统一策略接口**: 两种方案共用 `BaseStrategy` 接口
2. ✅ **配置加载机制**: 从数据库加载策略配置
3. ✅ **动态代码加载**: 安全地加载和执行AI生成的代码
4. ✅ **多层安全防护**: Core层独立的安全验证
5. ✅ **向后兼容**: 保持现有策略代码不变
6. ✅ **可扩展性**: 易于添加新的策略类型

### 设计原则

- **安全第一**: Core层必须有独立的安全验证，不能完全依赖Backend
- **职责清晰**: Core负责策略执行，Backend负责管理和验证
- **最小信任**: 对动态加载的代码采用零信任原则
- **降级策略**: 当安全检查失败时，有明确的降级处理
- **审计完整**: 所有策略加载和执行都有详细日志

---

## 整合两个方案

### 统一架构视图

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (Web UI)                          │
│  - 参数配置界面                                               │
│  - AI代码生成界面                                             │
│  - 策略管理界面                                               │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP API
┌────────────────────────▼────────────────────────────────────┐
│                   Backend (FastAPI)                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Strategy Management Layer                    │   │
│  │  ┌─────────────────┐  ┌──────────────────────┐      │   │
│  │  │ ConfigService   │  │ AIStrategyService    │      │   │
│  │  │ (方案1)         │  │ (方案2)              │      │   │
│  │  └─────────────────┘  └──────────────────────┘      │   │
│  └──────────────┬───────────────┬────────────────────────┘  │
│                 │               │                            │
│  ┌──────────────▼───────────────▼────────────────────────┐  │
│  │            PostgreSQL Database                        │  │
│  │  - strategy_configs (参数配置)                        │  │
│  │  - ai_strategies (AI生成代码)                         │  │
│  └──────────────┬───────────────┬────────────────────────┘  │
└─────────────────┼───────────────┼───────────────────────────┘
                  │               │
           ┌──────┴───────┬───────┴──────┐
           │              │              │
┌──────────▼──────────────▼──────────────▼──────────────────┐
│                    Core (Python)                           │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Strategy Loader (策略加载层) ⭐新增          │   │
│  │  ┌──────────────────┐  ┌─────────────────────┐     │   │
│  │  │ ConfigLoader     │  │ DynamicCodeLoader   │     │   │
│  │  │ (方案1)          │  │ (方案2)             │     │   │
│  │  └────────┬─────────┘  └──────────┬──────────┘     │   │
│  │           └─────────────┬──────────┘                │   │
│  └─────────────────────────┼───────────────────────────┘   │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │         Security Layer (安全层) ⭐新增               │   │
│  │  - CodeSanitizer (代码净化)                         │   │
│  │  - PermissionChecker (权限检查)                      │   │
│  │  - ResourceLimiter (资源限制)                        │   │
│  │  - AuditLogger (审计日志)                            │   │
│  └─────────────────────────┬───────────────────────────┘   │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │         Strategy Factory (策略工厂) ⭐改造           │   │
│  │  - 统一创建接口                                       │   │
│  │  - 策略类型注册                                       │   │
│  │  - 实例化管理                                         │   │
│  └─────────────────────────┬───────────────────────────┘   │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │         BaseStrategy (策略基类) ⭐增强               │   │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────┐   │   │
│  │  │ Predefined │  │ Configured │  │ AI-Generated│   │   │
│  │  │ Strategies │  │ Strategies │  │ Strategies  │   │   │
│  │  └────────────┘  └────────────┘  └─────────────┘   │   │
│  └─────────────────────────┬───────────────────────────┘   │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │         BacktestEngine (回测引擎)                    │   │
│  │  - 统一执行接口                                       │   │
│  │  - 所有策略类型通用                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 策略类型层级

```
BaseStrategy (抽象基类)
│
├── PredefinedStrategy (预定义策略)
│   ├── MomentumStrategy
│   ├── MeanReversionStrategy
│   └── MultiFactorStrategy
│
├── ConfiguredStrategy (配置驱动策略)
│   └── 从数据库加载配置，实例化为具体策略
│
└── DynamicStrategy (动态加载策略)
    └── AI生成的代码，动态编译和加载
```

### 策略识别方式

每个策略实例都有唯一标识：

```python
class StrategyIdentifier:
    """策略标识符"""
    strategy_type: str      # 'predefined' | 'configured' | 'dynamic'
    strategy_id: Optional[int]    # 数据库ID (configured/dynamic)
    strategy_class: str     # 类名
    config_version: Optional[int] # 配置版本号
```

---

## Core层架构设计

### 目录结构

```
core/src/
├── strategies/
│   ├── __init__.py
│   ├── base_strategy.py              (改造)
│   ├── strategy_factory.py           (改造)
│   ├── signal_generator.py
│   │
│   ├── loaders/                      ⭐新增
│   │   ├── __init__.py
│   │   ├── base_loader.py
│   │   ├── config_loader.py          # 参数配置加载器
│   │   ├── dynamic_loader.py         # 动态代码加载器
│   │   └── loader_factory.py
│   │
│   ├── security/                     ⭐新增
│   │   ├── __init__.py
│   │   ├── code_sanitizer.py         # 代码净化
│   │   ├── permission_checker.py     # 权限检查
│   │   ├── resource_limiter.py       # 资源限制
│   │   ├── audit_logger.py           # 审计日志
│   │   └── security_config.py        # 安全配置
│   │
│   ├── validators/                   ⭐新增
│   │   ├── __init__.py
│   │   ├── syntax_validator.py
│   │   ├── interface_validator.py
│   │   └── runtime_validator.py
│   │
│   ├── cache/                        ⭐新增
│   │   ├── __init__.py
│   │   ├── strategy_cache.py
│   │   └── code_cache.py
│   │
│   ├── predefined/                   ⭐新增 (重构)
│   │   ├── __init__.py
│   │   ├── momentum_strategy.py      (移动)
│   │   ├── mean_reversion_strategy.py (移动)
│   │   └── multi_factor_strategy.py  (移动)
│   │
│   └── examples/
│       └── ...
│
├── database/
│   └── db_manager.py                 (增强)
│
├── exceptions.py                      (扩展)
│
└── utils/
    ├── code_utils.py                 ⭐新增
    └── security_utils.py             ⭐新增
```

---

## 安全防范措施

### 多层防御体系

```
┌─────────────────────────────────────────────────────────────┐
│                    第1层: Backend验证                         │
│  - AI生成时的Prompt过滤                                       │
│  - 代码保存前的AST分析                                        │
│  - 沙箱测试                                                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    第2层: Core加载时验证 ⭐                   │
│  - 代码签名验证                                               │
│  - 再次AST分析                                                │
│  - 导入白名单检查                                             │
│  - 危险函数检测                                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    第3层: 运行时隔离 ⭐                       │
│  - 受限的命名空间                                             │
│  - 禁用危险内置函数                                           │
│  - 资源使用限制 (CPU/内存/时间)                               │
│  - 系统调用监控                                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    第4层: 审计与监控 ⭐                       │
│  - 完整的操作日志                                             │
│  - 异常行为告警                                               │
│  - 性能指标收集                                               │
│  - 回滚机制                                                   │
└─────────────────────────────────────────────────────────────┘
```

### Core层独立安全措施

#### 1. 代码签名与验证

```python
# core/src/strategies/security/code_sanitizer.py

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
        'core.strategies.base_strategy',
        'core.strategies.signal_generator',
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

    def __init__(self):
        self.validation_errors: List[str] = []
        self.validation_warnings: List[str] = []

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

            # 检查函数调用
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id

                    if func_name in self.FORBIDDEN_FUNCTIONS:
                        self.validation_errors.append(
                            f"禁止调用函数: {func_name}"
                        )
                        risk_level = 'high'

            # 检查属性访问
            elif isinstance(node, ast.Attribute):
                if node.attr in self.FORBIDDEN_ATTRIBUTES:
                    self.validation_errors.append(
                        f"禁止访问属性: {node.attr}"
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
            'risk_level': risk_level
        }
```

#### 2. 权限检查器

```python
# core/src/strategies/security/permission_checker.py

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
    }

    # 允许的numpy函数
    ALLOWED_NUMPY_FUNCTIONS = {
        'array', 'zeros', 'ones', 'full', 'arange', 'linspace',
        'mean', 'median', 'sum', 'std', 'var', 'min', 'max',
        'abs', 'sqrt', 'exp', 'log', 'log10',
        'sin', 'cos', 'tan',
        'clip', 'where', 'nan', 'isnan', 'isfinite',
    }

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
        if any(pattern in code for pattern in ['open(', 'pathlib', 'Path(']):
            violations.append("不允许访问文件系统")

        # 检查是否试图网络访问
        if any(pattern in code for pattern in ['socket', 'urllib', 'requests', 'http']):
            violations.append("不允许网络访问")

        # 检查是否试图执行系统命令
        if any(pattern in code for pattern in ['os.system', 'subprocess', 'popen']):
            violations.append("不允许执行系统命令")

        allowed = len(violations) == 0

        if not allowed:
            logger.warning(f"权限检查失败: {violations}")

        return {
            'allowed': allowed,
            'violations': violations
        }
```

#### 3. 资源限制器

```python
# core/src/strategies/security/resource_limiter.py

import signal
import resource
from typing import Dict, Any, Callable
from contextlib import contextmanager
from loguru import logger


class ResourceLimiter:
    """
    资源限制器

    限制策略执行时的资源使用
    """

    def __init__(
        self,
        max_memory_mb: int = 512,      # 最大内存 (MB)
        max_cpu_time: int = 30,        # 最大CPU时间 (秒)
        max_wall_time: int = 60        # 最大实际时间 (秒)
    ):
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time = max_cpu_time
        self.max_wall_time = max_wall_time

    @contextmanager
    def limit_resources(self):
        """
        上下文管理器: 限制资源使用

        Usage:
            with limiter.limit_resources():
                # 执行策略代码
                strategy.generate_signals(prices)
        """
        # 保存原始限制
        old_limits = {}

        try:
            # 设置内存限制
            old_limits['memory'] = resource.getrlimit(resource.RLIMIT_AS)
            memory_limit = self.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))

            # 设置CPU时间限制
            old_limits['cpu'] = resource.getrlimit(resource.RLIMIT_CPU)
            resource.setrlimit(resource.RLIMIT_CPU, (self.max_cpu_time, self.max_cpu_time))

            # 设置实际时间限制 (使用signal)
            def timeout_handler(signum, frame):
                raise TimeoutError(f"执行超时 ({self.max_wall_time}秒)")

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.max_wall_time)

            logger.debug(f"已设置资源限制: 内存={self.max_memory_mb}MB, CPU={self.max_cpu_time}s")

            yield

        except MemoryError:
            logger.error(f"内存超限: > {self.max_memory_mb}MB")
            raise

        except TimeoutError:
            logger.error(f"执行超时: > {self.max_wall_time}s")
            raise

        finally:
            # 恢复原始限制
            if 'memory' in old_limits:
                resource.setrlimit(resource.RLIMIT_AS, old_limits['memory'])

            if 'cpu' in old_limits:
                resource.setrlimit(resource.RLIMIT_CPU, old_limits['cpu'])

            # 取消alarm
            signal.alarm(0)
            if 'old_handler' in locals():
                signal.signal(signal.SIGALRM, old_handler)

            logger.debug("已恢复资源限制")
```

#### 4. 审计日志

```python
# core/src/strategies/security/audit_logger.py

import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger


class AuditLogger:
    """
    审计日志记录器

    记录所有策略加载和执行的详细信息
    """

    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 配置专门的审计日志
        self.audit_file = self.log_dir / f"audit_{datetime.now():%Y%m%d}.jsonl"

    def log_strategy_load(
        self,
        strategy_id: int,
        strategy_type: str,
        strategy_class: str,
        code_hash: str,
        validation_result: Dict[str, Any],
        user: Optional[str] = None
    ):
        """记录策略加载事件"""
        event = {
            'event_type': 'strategy_load',
            'timestamp': datetime.now().isoformat(),
            'strategy_id': strategy_id,
            'strategy_type': strategy_type,
            'strategy_class': strategy_class,
            'code_hash': code_hash,
            'validation': validation_result,
            'user': user,
        }

        self._write_event(event)
        logger.info(f"审计: 策略加载 - ID={strategy_id}, 类型={strategy_type}")

    def log_strategy_execution(
        self,
        strategy_id: int,
        execution_type: str,
        execution_params: Dict[str, Any],
        execution_result: Dict[str, Any],
        duration_ms: float,
        success: bool,
        error: Optional[str] = None
    ):
        """记录策略执行事件"""
        event = {
            'event_type': 'strategy_execution',
            'timestamp': datetime.now().isoformat(),
            'strategy_id': strategy_id,
            'execution_type': execution_type,
            'params': execution_params,
            'result': execution_result,
            'duration_ms': duration_ms,
            'success': success,
            'error': error,
        }

        self._write_event(event)
        logger.info(f"审计: 策略执行 - ID={strategy_id}, 成功={success}")

    def log_security_violation(
        self,
        strategy_id: int,
        violation_type: str,
        details: Dict[str, Any]
    ):
        """记录安全违规事件"""
        event = {
            'event_type': 'security_violation',
            'timestamp': datetime.now().isoformat(),
            'strategy_id': strategy_id,
            'violation_type': violation_type,
            'details': details,
        }

        self._write_event(event)
        logger.warning(f"审计: 安全违规 - ID={strategy_id}, 类型={violation_type}")

    def _write_event(self, event: Dict[str, Any]):
        """写入事件到日志文件"""
        with open(self.audit_file, 'a') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
```

---

## 新增模块详解

### 1. 配置加载器 (ConfigLoader)

```python
# core/src/strategies/loaders/config_loader.py

from typing import Dict, Any, Optional
from loguru import logger

from core.database import DatabaseManager
from ..base_strategy import BaseStrategy
from ..strategy_factory import StrategyFactory


class ConfigLoader:
    """
    配置加载器 - 支持方案1 (参数配置)

    从数据库加载策略配置，实例化为预定义的策略类
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.factory = StrategyFactory()
        self._cache = {}

    def load_strategy(
        self,
        config_id: int,
        use_cache: bool = True
    ) -> BaseStrategy:
        """
        从配置ID加载策略

        Args:
            config_id: strategy_configs表的ID
            use_cache: 是否使用缓存

        Returns:
            策略实例
        """
        # 检查缓存
        if use_cache and config_id in self._cache:
            logger.debug(f"从缓存加载策略配置: ID={config_id}")
            return self._cache[config_id]

        # 从数据库加载配置
        config_data = self._load_config_from_db(config_id)

        # 验证配置状态
        if not config_data['is_active']:
            raise ValueError(f"策略配置已禁用: ID={config_id}")

        # 创建策略实例
        strategy = self.factory.create(
            strategy_type=config_data['strategy_type'],
            config=config_data['config'],
            name=config_data['name']
        )

        # 附加元信息
        strategy._config_id = config_id
        strategy._config_version = config_data['version']
        strategy._config_hash = config_data['config_hash']

        # 缓存
        if use_cache:
            self._cache[config_id] = strategy

        logger.info(
            f"已加载策略配置: {config_data['name']} "
            f"(ID={config_id}, Version={config_data['version']})"
        )

        return strategy

    def _load_config_from_db(self, config_id: int) -> Dict[str, Any]:
        """从数据库加载配置"""
        query = """
            SELECT
                id, name, display_name, strategy_type,
                config, config_hash, version,
                is_active, created_at, updated_at
            FROM strategy_configs
            WHERE id = %s
        """

        result = self.db.execute_query(query, (config_id,))

        if not result:
            raise ValueError(f"策略配置不存在: ID={config_id}")

        return result[0]

    def clear_cache(self, config_id: Optional[int] = None):
        """清除缓存"""
        if config_id:
            self._cache.pop(config_id, None)
        else:
            self._cache.clear()
```

### 2. 动态代码加载器 (DynamicCodeLoader)

```python
# core/src/strategies/loaders/dynamic_loader.py

import types
import importlib.util
from typing import Dict, Any, Type, Optional
from loguru import logger

from core.database import DatabaseManager
from ..base_strategy import BaseStrategy
from ..security.code_sanitizer import CodeSanitizer
from ..security.permission_checker import PermissionChecker
from ..security.audit_logger import AuditLogger


class DynamicCodeLoader:
    """
    动态代码加载器 - 支持方案2 (AI代码生成)

    安全地加载和执行AI生成的策略代码
    """

    def __init__(self):
        self.db = DatabaseManager()
        self.sanitizer = CodeSanitizer()
        self.permission_checker = PermissionChecker()
        self.audit_logger = AuditLogger()
        self._cache = {}

    def load_strategy(
        self,
        strategy_id: int,
        use_cache: bool = True,
        strict_mode: bool = True
    ) -> BaseStrategy:
        """
        从AI策略ID加载策略

        Args:
            strategy_id: ai_strategies表的ID
            use_cache: 是否使用缓存
            strict_mode: 严格模式 (任何安全问题都拒绝加载)

        Returns:
            策略实例
        """
        # 检查缓存
        if use_cache and strategy_id in self._cache:
            logger.debug(f"从缓存加载AI策略: ID={strategy_id}")
            return self._cache[strategy_id]

        # 从数据库加载代码
        strategy_data = self._load_strategy_from_db(strategy_id)

        # 验证策略状态
        if not strategy_data['is_enabled']:
            raise ValueError(f"AI策略已禁用: ID={strategy_id}")

        if strategy_data['validation_status'] == 'failed':
            raise ValueError(f"AI策略验证失败: ID={strategy_id}")

        # Core层独立安全验证 (不信任Backend的验证结果)
        code = strategy_data['generated_code']
        expected_hash = strategy_data['code_hash']

        # 1. 代码净化
        sanitize_result = self.sanitizer.sanitize(
            code=code,
            expected_hash=expected_hash,
            strict_mode=strict_mode
        )

        if not sanitize_result['safe']:
            self.audit_logger.log_security_violation(
                strategy_id=strategy_id,
                violation_type='sanitize_failed',
                details=sanitize_result
            )
            raise SecurityError(
                f"代码安全验证失败: {sanitize_result['errors']}"
            )

        # 2. 权限检查
        permission_result = self.permission_checker.check_permissions(code)

        if not permission_result['allowed']:
            self.audit_logger.log_security_violation(
                strategy_id=strategy_id,
                violation_type='permission_denied',
                details=permission_result
            )
            raise SecurityError(
                f"代码权限检查失败: {permission_result['violations']}"
            )

        # 3. 动态加载代码
        try:
            strategy_class = self._compile_and_load(
                code=sanitize_result['sanitized_code'],
                class_name=strategy_data['class_name'],
                module_name=strategy_data['strategy_name']
            )
        except Exception as e:
            logger.error(f"动态加载失败: {e}")
            raise

        # 4. 实例化策略
        strategy = strategy_class(
            name=strategy_data['strategy_name'],
            config={}
        )

        # 附加元信息
        strategy._strategy_id = strategy_id
        strategy._strategy_type = 'dynamic'
        strategy._code_hash = expected_hash
        strategy._risk_level = sanitize_result['risk_level']

        # 缓存
        if use_cache:
            self._cache[strategy_id] = strategy

        # 审计日志
        self.audit_logger.log_strategy_load(
            strategy_id=strategy_id,
            strategy_type='dynamic',
            strategy_class=strategy_data['class_name'],
            code_hash=expected_hash,
            validation_result=sanitize_result
        )

        logger.success(
            f"已加载AI策略: {strategy_data['strategy_name']} "
            f"(ID={strategy_id}, 风险={sanitize_result['risk_level']})"
        )

        return strategy

    def _load_strategy_from_db(self, strategy_id: int) -> Dict[str, Any]:
        """从数据库加载AI策略"""
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

        result = self.db.execute_query(query, (strategy_id,))

        if not result:
            raise ValueError(f"AI策略不存在: ID={strategy_id}")

        return result[0]

    def _compile_and_load(
        self,
        code: str,
        class_name: str,
        module_name: str
    ) -> Type[BaseStrategy]:
        """
        编译并加载代码

        Args:
            code: Python代码
            class_name: 策略类名
            module_name: 模块名

        Returns:
            策略类
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
            raise

        # 获取策略类
        if not hasattr(module, class_name):
            raise AttributeError(f"模块中未找到类: {class_name}")

        strategy_class = getattr(module, class_name)

        # 验证是BaseStrategy的子类
        if not issubclass(strategy_class, BaseStrategy):
            raise TypeError(f"{class_name} 必须继承自 BaseStrategy")

        return strategy_class

    def _create_restricted_globals(self) -> Dict[str, Any]:
        """
        创建受限的全局命名空间

        只允许访问安全的内置函数和模块
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
        from ..base_strategy import BaseStrategy
        from ..signal_generator import SignalGenerator

        safe_modules.update({
            'BaseStrategy': BaseStrategy,
            'SignalGenerator': SignalGenerator,
        })

        return {
            '__builtins__': safe_builtins,
            **safe_modules
        }

    def clear_cache(self, strategy_id: Optional[int] = None):
        """清除缓存"""
        if strategy_id:
            self._cache.pop(strategy_id, None)
        else:
            self._cache.clear()


class SecurityError(Exception):
    """安全错误"""
    pass
```

### 3. 加载器工厂 (LoaderFactory)

```python
# core/src/strategies/loaders/loader_factory.py

from typing import Dict, Any
from loguru import logger

from .base_loader import BaseLoader
from .config_loader import ConfigLoader
from .dynamic_loader import DynamicCodeLoader
from ..base_strategy import BaseStrategy


class LoaderFactory:
    """
    加载器工厂

    根据策略来源选择合适的加载器
    """

    def __init__(self):
        self.config_loader = ConfigLoader()
        self.dynamic_loader = DynamicCodeLoader()

    def load_strategy(
        self,
        strategy_source: str,
        strategy_id: int,
        **kwargs
    ) -> BaseStrategy:
        """
        加载策略

        Args:
            strategy_source: 'config' | 'dynamic'
            strategy_id: 策略ID
            **kwargs: 传递给加载器的参数

        Returns:
            策略实例
        """
        if strategy_source == 'config':
            logger.info(f"使用ConfigLoader加载策略: ID={strategy_id}")
            return self.config_loader.load_strategy(strategy_id, **kwargs)

        elif strategy_source == 'dynamic':
            logger.info(f"使用DynamicCodeLoader加载策略: ID={strategy_id}")
            return self.dynamic_loader.load_strategy(strategy_id, **kwargs)

        else:
            raise ValueError(f"未知的策略来源: {strategy_source}")

    def clear_cache(self):
        """清除所有缓存"""
        self.config_loader.clear_cache()
        self.dynamic_loader.clear_cache()
```

---

## 现有模块改造

### 1. BaseStrategy 增强

```python
# core/src/strategies/base_strategy.py (部分修改)

class BaseStrategy(ABC):
    """策略基类 - 增强版"""

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化策略

        Args:
            name: 策略名称
            config: 策略配置
        """
        self.name = name
        self.config = self._parse_config(config)
        self._signal_cache = {}

        # 元信息 (由加载器设置)
        self._config_id: Optional[int] = None         # 配置ID
        self._strategy_id: Optional[int] = None       # AI策略ID
        self._strategy_type: str = 'predefined'       # 'predefined' | 'configured' | 'dynamic'
        self._config_version: Optional[int] = None    # 配置版本
        self._code_hash: Optional[str] = None         # 代码哈希
        self._risk_level: str = 'safe'                # 风险等级

        logger.info(f"初始化策略: {self.name}")

    def get_metadata(self) -> Dict[str, Any]:
        """
        获取策略元信息

        Returns:
            完整的策略元数据
        """
        return {
            'name': self.name,
            'class': self.__class__.__name__,
            'strategy_type': self._strategy_type,
            'config_id': self._config_id,
            'strategy_id': self._strategy_id,
            'config_version': self._config_version,
            'code_hash': self._code_hash,
            'risk_level': self._risk_level,
            'config': self.config.to_dict() if hasattr(self.config, 'to_dict') else self.config,
        }

    # ... 其他方法保持不变
```

### 2. StrategyFactory 改造

```python
# core/src/strategies/strategy_factory.py (完全重写)

from typing import Dict, Any, Optional, Type
from loguru import logger

from .base_strategy import BaseStrategy
from .predefined.momentum_strategy import MomentumStrategy
from .predefined.mean_reversion_strategy import MeanReversionStrategy
from .predefined.multi_factor_strategy import MultiFactorStrategy
from .loaders.loader_factory import LoaderFactory


class StrategyFactory:
    """
    策略工厂 - 统一的策略创建接口

    支持三种创建方式:
    1. 预定义策略 (直接创建)
    2. 配置驱动策略 (从数据库加载配置)
    3. 动态代码策略 (从数据库加载AI生成的代码)
    """

    # 预定义策略类型映射
    PREDEFINED_STRATEGIES = {
        'momentum': MomentumStrategy,
        'mean_reversion': MeanReversionStrategy,
        'multi_factor': MultiFactorStrategy,
    }

    def __init__(self):
        self.loader_factory = LoaderFactory()

    @classmethod
    def create(
        cls,
        strategy_type: str,
        config: Dict[str, Any],
        name: Optional[str] = None
    ) -> BaseStrategy:
        """
        创建预定义策略 (方式1)

        Args:
            strategy_type: 策略类型
            config: 策略配置
            name: 策略名称

        Returns:
            策略实例
        """
        if strategy_type not in cls.PREDEFINED_STRATEGIES:
            raise ValueError(
                f"不支持的策略类型: {strategy_type}. "
                f"支持的类型: {list(cls.PREDEFINED_STRATEGIES.keys())}"
            )

        strategy_class = cls.PREDEFINED_STRATEGIES[strategy_type]
        strategy_name = name or f"{strategy_type}_strategy"

        logger.debug(f"创建预定义策略: {strategy_name} ({strategy_type})")

        strategy = strategy_class(strategy_name, config)
        strategy._strategy_type = 'predefined'

        return strategy

    def create_from_config(
        self,
        config_id: int,
        **kwargs
    ) -> BaseStrategy:
        """
        从配置创建策略 (方式2 - 参数配置方案)

        Args:
            config_id: strategy_configs表的ID
            **kwargs: 传递给加载器的参数

        Returns:
            策略实例
        """
        logger.info(f"从配置创建策略: config_id={config_id}")

        strategy = self.loader_factory.load_strategy(
            strategy_source='config',
            strategy_id=config_id,
            **kwargs
        )

        strategy._strategy_type = 'configured'

        return strategy

    def create_from_code(
        self,
        strategy_id: int,
        **kwargs
    ) -> BaseStrategy:
        """
        从AI代码创建策略 (方式3 - AI代码生成方案)

        Args:
            strategy_id: ai_strategies表的ID
            **kwargs: 传递给加载器的参数

        Returns:
            策略实例
        """
        logger.info(f"从AI代码创建策略: strategy_id={strategy_id}")

        strategy = self.loader_factory.load_strategy(
            strategy_source='dynamic',
            strategy_id=strategy_id,
            **kwargs
        )

        strategy._strategy_type = 'dynamic'

        return strategy

    @classmethod
    def register_strategy(cls, strategy_type: str, strategy_class: Type[BaseStrategy]):
        """
        注册自定义策略类型

        Args:
            strategy_type: 策略类型标识
            strategy_class: 策略类
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise ValueError(f"{strategy_class} 必须继承自 BaseStrategy")

        cls.PREDEFINED_STRATEGIES[strategy_type] = strategy_class
        logger.info(f"已注册策略类型: {strategy_type} -> {strategy_class.__name__}")
```

---

## 数据流设计

### 方案1: 参数配置流程

```
Backend API
    ↓
创建配置 (strategy_configs表)
    {
        strategy_type: 'momentum',
        config: {lookback_period: 20, ...}
    }
    ↓
保存到数据库 (config_id=123)
    ↓
────────────────────────────────
Core 加载流程:
    ↓
factory.create_from_config(config_id=123)
    ↓
ConfigLoader.load_strategy(123)
    ↓
从数据库读取配置
    ↓
factory.create('momentum', config)
    ↓
实例化 MomentumStrategy
    ↓
返回策略实例
```

### 方案2: AI代码生成流程

```
Backend API + DeepSeek
    ↓
生成代码 (ai_strategies表)
    {
        generated_code: "class SmallCapStrategy...",
        class_name: "SmallCapStrategy"
    }
    ↓
Backend验证 + 保存到数据库 (strategy_id=456)
    ↓
────────────────────────────────
Core 加载流程:
    ↓
factory.create_from_code(strategy_id=456)
    ↓
DynamicCodeLoader.load_strategy(456)
    ↓
从数据库读取代码
    ↓
Core独立安全验证
    ├─ CodeSanitizer (代码净化)
    ├─ PermissionChecker (权限检查)
    └─ 哈希验证
    ↓
动态编译和加载
    ├─ 创建受限命名空间
    ├─ exec(code, restricted_globals)
    └─ 提取策略类
    ↓
实例化策略类
    ↓
返回策略实例 + 附加审计信息
```

---

## 错误处理与日志

### 异常层次

```python
# core/src/exceptions.py (扩展)

class StrategyError(Exception):
    """策略相关错误基类"""
    pass

class StrategyLoadError(StrategyError):
    """策略加载错误"""
    pass

class StrategyValidationError(StrategyError):
    """策略验证错误"""
    pass

class StrategySecurityError(StrategyError):
    """策略安全错误"""
    pass

class StrategyExecutionError(StrategyError):
    """策略执行错误"""
    pass

class ConfigNotFoundError(StrategyLoadError):
    """配置不存在"""
    pass

class CodeCompileError(StrategyLoadError):
    """代码编译错误"""
    pass

class SecurityViolationError(StrategySecurityError):
    """安全违规"""
    pass
```

### 错误处理示例

```python
# 使用示例
from core.strategies import StrategyFactory
from core.exceptions import StrategySecurityError, StrategyLoadError

factory = StrategyFactory()

try:
    # 尝试加载AI生成的策略
    strategy = factory.create_from_code(strategy_id=456, strict_mode=True)

except StrategySecurityError as e:
    logger.error(f"安全错误: {e}")
    # 降级处理: 禁用该策略
    # db.execute("UPDATE ai_strategies SET is_enabled=FALSE WHERE id=456")
    raise

except StrategyLoadError as e:
    logger.error(f"加载错误: {e}")
    # 降级处理: 使用默认策略
    strategy = factory.create('momentum', {'lookback_period': 20})

except Exception as e:
    logger.exception(f"未知错误: {e}")
    raise
```

---

## 性能优化

### 1. 多级缓存

```python
# core/src/strategies/cache/strategy_cache.py

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pickle


class StrategyCache:
    """
    策略缓存

    三级缓存:
    1. 内存缓存 (进程级)
    2. Redis缓存 (应用级)
    3. 数据库 (持久化)
    """

    def __init__(self, redis_client=None):
        self._memory_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self.redis = redis_client
        self.ttl = timedelta(minutes=30)  # 缓存有效期

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        # 1. 检查内存缓存
        if key in self._memory_cache:
            if self._is_valid(key):
                return self._memory_cache[key]
            else:
                del self._memory_cache[key]

        # 2. 检查Redis缓存
        if self.redis:
            cached = self.redis.get(f"strategy:{key}")
            if cached:
                value = pickle.loads(cached)
                self._memory_cache[key] = value
                self._cache_timestamps[key] = datetime.now()
                return value

        return None

    def set(self, key: str, value: Any):
        """设置缓存"""
        # 1. 写入内存
        self._memory_cache[key] = value
        self._cache_timestamps[key] = datetime.now()

        # 2. 写入Redis
        if self.redis:
            self.redis.setex(
                f"strategy:{key}",
                int(self.ttl.total_seconds()),
                pickle.dumps(value)
            )

    def _is_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._cache_timestamps:
            return False

        elapsed = datetime.now() - self._cache_timestamps[key]
        return elapsed < self.ttl

    def invalidate(self, key: str):
        """使缓存失效"""
        self._memory_cache.pop(key, None)
        self._cache_timestamps.pop(key, None)

        if self.redis:
            self.redis.delete(f"strategy:{key}")
```

### 2. 懒加载

```python
# 只在真正需要时才加载策略
class LazyStrategy:
    """懒加载策略包装器"""

    def __init__(self, strategy_id: int, loader):
        self.strategy_id = strategy_id
        self.loader = loader
        self._strategy = None

    def _ensure_loaded(self):
        if self._strategy is None:
            self._strategy = self.loader.load_strategy(self.strategy_id)

    def generate_signals(self, *args, **kwargs):
        self._ensure_loaded()
        return self._strategy.generate_signals(*args, **kwargs)
```

---

## 测试策略

### 1. 单元测试

```python
# core/tests/unit/strategies/security/test_code_sanitizer.py

import pytest
from core.strategies.security.code_sanitizer import CodeSanitizer


class TestCodeSanitizer:

    def test_safe_code(self):
        """测试安全代码"""
        code = """
from core.strategies.base_strategy import BaseStrategy
import pandas as pd

class TestStrategy(BaseStrategy):
    def calculate_scores(self, prices, features=None, date=None):
        return prices.iloc[-1]

    def generate_signals(self, prices, features=None, volumes=None, **kwargs):
        return pd.DataFrame(0, index=prices.index, columns=prices.columns)
"""
        sanitizer = CodeSanitizer()
        result = sanitizer.sanitize(code)

        assert result['safe'] == True
        assert result['risk_level'] == 'safe'
        assert len(result['errors']) == 0

    def test_dangerous_imports(self):
        """测试危险导入"""
        code = """
import os
import subprocess

class BadStrategy:
    def run(self):
        os.system('rm -rf /')
"""
        sanitizer = CodeSanitizer()
        result = sanitizer.sanitize(code)

        assert result['safe'] == False
        assert result['risk_level'] == 'high'
        assert any('os' in str(e) for e in result['errors'])

    def test_dangerous_functions(self):
        """测试危险函数"""
        code = """
class BadStrategy:
    def run(self):
        eval('print("hello")')
"""
        sanitizer = CodeSanitizer()
        result = sanitizer.sanitize(code)

        assert result['safe'] == False
        assert any('eval' in str(e) for e in result['errors'])
```

### 2. 集成测试

```python
# core/tests/integration/test_strategy_loading.py

import pytest
from core.strategies import StrategyFactory


class TestStrategyLoading:

    @pytest.fixture
    def factory(self):
        return StrategyFactory()

    def test_load_config_strategy(self, factory, test_config_id):
        """测试加载配置策略"""
        strategy = factory.create_from_config(config_id=test_config_id)

        assert strategy is not None
        assert strategy._strategy_type == 'configured'
        assert strategy._config_id == test_config_id

    def test_load_dynamic_strategy(self, factory, test_strategy_id):
        """测试加载动态策略"""
        strategy = factory.create_from_code(strategy_id=test_strategy_id)

        assert strategy is not None
        assert strategy._strategy_type == 'dynamic'
        assert strategy._strategy_id == test_strategy_id

    def test_security_rejection(self, factory, malicious_strategy_id):
        """测试拒绝恶意代码"""
        with pytest.raises(SecurityError):
            factory.create_from_code(strategy_id=malicious_strategy_id)
```

---

## 实施计划

### Phase 1: 安全基础设施 (1周) ✅ 已完成

**状态**: ✅ 已完成 (2026-02-08)

**任务**:
1. ✅ 实现 CodeSanitizer (代码净化器) - 覆盖率 89%
2. ✅ 实现 PermissionChecker (权限检查器) - 覆盖率 97%
3. ✅ 实现 ResourceLimiter (资源限制器) - 覆盖率 76%
4. ✅ 实现 AuditLogger (审计日志) - 覆盖率 87%
5. ✅ 实现 SecurityConfig (安全配置管理) - 覆盖率 91%
6. ✅ 扩展异常体系 (新增 8 个策略相关异常)
7. ✅ 单元测试 (86 个测试通过, 1 个跳过)

**交付物**:
- ✅ security/ 模块完整实现 (5 个核心组件)
- ✅ 测试覆盖率 87% (接近 90% 目标)
- ✅ 完整的单元测试套件
- ✅ HTML 覆盖率报告

**实现详情**:

1. **CodeSanitizer** ([code_sanitizer.py](../src/strategies/security/code_sanitizer.py))
   - AST 语法树深度分析
   - 危险导入/函数/属性检测 (黑名单机制)
   - 代码哈希完整性验证
   - 风险等级评估 (safe/low/medium/high)
   - 支持严格模式和宽松模式

2. **PermissionChecker** ([permission_checker.py](../src/strategies/security/permission_checker.py))
   - 文件系统访问检测
   - 网络访问检测
   - 系统命令执行检测
   - 数据库访问检测
   - pandas/numpy 方法白名单

3. **ResourceLimiter** ([resource_limiter.py](../src/strategies/security/resource_limiter.py))
   - CPU 时间限制
   - 墙钟时间限制 (超时控制)
   - 内存使用监控
   - 上下文管理器设计
   - 跨平台兼容 (macOS/Linux/Windows)

4. **AuditLogger** ([audit_logger.py](../src/strategies/security/audit_logger.py))
   - 策略加载/执行事件记录
   - 安全违规事件记录
   - 缓存事件记录
   - 资源使用记录
   - 事件查询与统计
   - JSONL 格式存储

5. **SecurityConfig** ([security_config.py](../src/strategies/security/security_config.py))
   - 配置参数管理
   - 白名单/黑名单动态管理
   - 配置验证
   - JSON 文件导入/导出
   - 预定义环境配置 (DEFAULT/DEVELOPMENT/PRODUCTION)

**测试覆盖率统计**:
```
模块                      覆盖率
-------------------------  ------
__init__.py               100%
permission_checker.py      97%
security_config.py         91%
code_sanitizer.py          89%
audit_logger.py            87%
resource_limiter.py        76%
-------------------------  ------
总计                       87%
```

**文件结构**:
```
core/src/strategies/security/
├── __init__.py
├── code_sanitizer.py
├── permission_checker.py
├── resource_limiter.py
├── audit_logger.py
└── security_config.py

core/tests/unit/strategies/security/
├── __init__.py
├── test_code_sanitizer.py (20 tests)
├── test_permission_checker.py (14 tests)
├── test_resource_limiter.py (13 tests)
├── test_audit_logger.py (15 tests)
└── test_security_config.py (24 tests)
```

### Phase 2: 加载器实现 (1周)

**任务**:
1. 实现 ConfigLoader
2. 实现 DynamicCodeLoader
3. 实现 LoaderFactory
4. 实现缓存机制
5. 集成测试

**交付物**:
- loaders/ 模块完整实现
- 集成测试

### Phase 3: 工厂与基类改造 (3-5天)

**任务**:
1. 重构 StrategyFactory
2. 增强 BaseStrategy
3. 重组目录结构 (移动到 predefined/)
4. 更新 __init__.py
5. 回归测试

**交付物**:
- 重构后的策略系统
- 所有测试通过

### Phase 4: 性能优化与监控 (3-5天)

**任务**:
1. 实现多级缓存
2. 添加性能监控
3. 优化数据库查询
4. 压力测试
5. 文档更新

**交付物**:
- 优化后的系统
- 性能报告
- 完整文档

### Phase 5: 联调与发布 (3天)

**任务**:
1. 与Backend联调
2. 端到端测试
3. 安全审计
4. 部署准备
5. 发布

**交付物**:
- 生产就绪的系统
- 部署文档
- 运维手册

**总计**: 3-4周

---

## 总结

### Core层改造核心要点

1. ✅ **统一接口**: 所有策略类型共用 `BaseStrategy` 接口
2. ✅ **双重方案**: 同时支持参数配置和AI代码生成
3. ✅ **多层安全**: Core层独立的安全验证体系
4. ✅ **动态加载**: 安全的代码编译和执行机制
5. ✅ **完整审计**: 所有操作都有详细日志
6. ✅ **向后兼容**: 现有策略代码无需修改
7. ✅ **高性能**: 多级缓存和懒加载

### 安全防护总结

| 层级 | 措施 | 位置 |
|------|------|------|
| **加载时** | 代码签名验证、AST分析、白名单检查 | Core |
| **运行时** | 受限命名空间、资源限制、系统调用监控 | Core |
| **审计** | 完整操作日志、异常告警 | Core |
| **降级** | 禁用策略、使用默认策略 | Core + Backend |

### 与Backend的职责划分

| 职责 | Backend | Core |
|------|---------|------|
| 策略配置管理 | ✅ | ❌ |
| AI代码生成 | ✅ | ❌ |
| 初次代码验证 | ✅ | ❌ |
| 代码存储 | ✅ | ❌ |
| **加载时验证** | ❌ | ✅ |
| **运行时隔离** | ❌ | ✅ |
| **资源限制** | ❌ | ✅ |
| **审计日志** | ✅ | ✅ |
| 策略执行 | ❌ | ✅ |
| 回测引擎 | ❌ | ✅ |

---

## 实施进度

### 已完成
- ✅ **Phase 1: 安全基础设施** (2026-02-08)
  - 5个核心安全组件全部实现
  - 86个单元测试全部通过
  - 测试覆盖率达到 87%
  - 完整的异常体系扩展

### 进行中
- 🔄 **Phase 2: 加载器实现** (待启动)

### 待开始
- ⏳ Phase 3: 工厂与基类改造
- ⏳ Phase 4: 性能优化与监控
- ⏳ Phase 5: 联调与发布

---

**文档状态**: ✅ Phase 1 已完成

**下一步**:
1. ✅ ~~评审设计方案~~ (已完成)
2. ✅ ~~确定实施优先级~~ (已完成)
3. ✅ ~~Phase 1 开发~~ (已完成)
4. 🔄 启动 Phase 2: 加载器实现
5. 与 Backend 团队对接数据库表结构

**联系人**: Architecture Team
**最后更新**: 2026-02-08
**Phase 1 完成日期**: 2026-02-08
