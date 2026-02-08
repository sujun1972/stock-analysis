# Core策略系统改造 - 实施检查清单

**文档版本**: v1.0.0
**创建日期**: 2026-02-08
**关联文档**: [core_strategy_system_refactoring.md](./core_strategy_system_refactoring.md)
**状态**: 📋 实施指南

---

## 📋 文档完整性评估

### ✅ 已覆盖的内容

当前文档 `core_strategy_system_refactoring.md` 已经很详尽，包含：

1. ✅ **架构设计** - 完整的模块划分和层级关系
2. ✅ **安全设计** - 四层防御体系和具体实现
3. ✅ **代码示例** - 关键模块的完整代码
4. ✅ **数据流** - 两种方案的完整流程
5. ✅ **错误处理** - 异常层次和处理策略
6. ✅ **测试策略** - 单元测试和集成测试框架
7. ✅ **实施计划** - 分阶段实施路线图

### ⚠️ 需要补充的内容

以下是实施时需要补充的细节：

---

## 🔧 技术细节补充

### 1. 数据库连接与依赖

#### 问题
文档中的加载器需要访问数据库，但未明确：
- 数据库连接如何管理？
- 是否复用现有的 `DatabaseManager`？
- 连接池配置？

#### 补充方案

```python
# core/src/strategies/loaders/base_loader.py

from typing import Optional
from core.database import DatabaseManager, get_db_manager


class BaseLoader:
    """加载器基类"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化加载器

        Args:
            db_manager: 数据库管理器实例
                       如果不提供，使用全局单例
        """
        self.db = db_manager or get_db_manager()

    def _execute_query(self, query: str, params: tuple = None):
        """
        执行数据库查询

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            查询结果
        """
        try:
            return self.db.execute_query(query, params)
        except Exception as e:
            logger.error(f"数据库查询失败: {e}")
            raise


# 使用示例
class ConfigLoader(BaseLoader):
    def load_strategy(self, config_id: int):
        query = "SELECT * FROM strategy_configs WHERE id = %s"
        result = self._execute_query(query, (config_id,))
        # ...
```

#### 配置文件

```yaml
# core/config/database.yaml

database:
  # 策略加载专用连接池
  strategy_loader:
    pool_size: 10
    max_overflow: 20
    pool_timeout: 30
    pool_recycle: 3600
```

---

### 2. 配置与环境变量

#### 问题
安全配置（白名单、资源限制等）应该如何管理？

#### 补充方案

```python
# core/src/strategies/security/security_config.py

from dataclasses import dataclass, field
from typing import Set, Dict, Any
import os
import yaml
from pathlib import Path


@dataclass
class SecurityConfig:
    """安全配置"""

    # 代码安全
    allowed_imports: Set[str] = field(default_factory=lambda: {
        'typing', 'types', 'dataclasses', 'enum', 'abc',
        'pandas', 'numpy', 'loguru',
        'core.strategies.base_strategy',
        'core.strategies.signal_generator',
    })

    forbidden_imports: Set[str] = field(default_factory=lambda: {
        'os', 'sys', 'subprocess', 'socket',
        'urllib', 'requests', 'http',
        'pickle', 'shelve', 'marshal',
    })

    forbidden_functions: Set[str] = field(default_factory=lambda: {
        'eval', 'exec', 'compile', '__import__',
        'open', 'file', 'input',
        'getattr', 'setattr', 'delattr',
    })

    # 资源限制
    max_memory_mb: int = 512
    max_cpu_time_seconds: int = 30
    max_wall_time_seconds: int = 60

    # 缓存配置
    cache_enabled: bool = True
    cache_ttl_seconds: int = 1800  # 30分钟

    # 审计配置
    audit_enabled: bool = True
    audit_log_dir: str = "logs/audit"

    # 严格模式
    strict_mode: bool = True  # 生产环境建议True

    @classmethod
    def from_yaml(cls, config_path: str = None) -> "SecurityConfig":
        """从YAML文件加载配置"""
        if config_path is None:
            config_path = os.getenv(
                'CORE_SECURITY_CONFIG',
                'core/config/security.yaml'
            )

        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"配置文件不存在，使用默认配置: {config_path}")
            return cls()

        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        return cls(**config_data.get('security', {}))

    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """从环境变量加载配置"""
        return cls(
            max_memory_mb=int(os.getenv('CORE_MAX_MEMORY_MB', 512)),
            max_cpu_time_seconds=int(os.getenv('CORE_MAX_CPU_TIME', 30)),
            max_wall_time_seconds=int(os.getenv('CORE_MAX_WALL_TIME', 60)),
            strict_mode=os.getenv('CORE_STRICT_MODE', 'true').lower() == 'true',
            cache_enabled=os.getenv('CORE_CACHE_ENABLED', 'true').lower() == 'true',
        )


# 全局配置单例
_security_config: SecurityConfig = None


def get_security_config() -> SecurityConfig:
    """获取全局安全配置"""
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig.from_yaml()
    return _security_config
```

```yaml
# core/config/security.yaml

security:
  # 允许的导入模块
  allowed_imports:
    - typing
    - types
    - pandas
    - numpy
    - loguru
    - core.strategies.base_strategy
    - core.strategies.signal_generator

  # 禁止的导入模块
  forbidden_imports:
    - os
    - sys
    - subprocess
    - socket
    - requests

  # 禁止的函数
  forbidden_functions:
    - eval
    - exec
    - compile
    - open
    - __import__

  # 资源限制
  max_memory_mb: 512
  max_cpu_time_seconds: 30
  max_wall_time_seconds: 60

  # 缓存
  cache_enabled: true
  cache_ttl_seconds: 1800

  # 审计
  audit_enabled: true
  audit_log_dir: logs/audit

  # 严格模式
  strict_mode: true
```

---

### 3. 依赖注入与测试

#### 问题
如何在测试时替换依赖（数据库、安全配置等）？

#### 补充方案

```python
# core/src/strategies/loaders/loader_factory.py

from typing import Optional
from .config_loader import ConfigLoader
from .dynamic_loader import DynamicCodeLoader
from ..security.security_config import SecurityConfig


class LoaderFactory:
    """加载器工厂 - 支持依赖注入"""

    def __init__(
        self,
        db_manager=None,
        security_config: Optional[SecurityConfig] = None,
        cache_manager=None
    ):
        """
        初始化工厂

        Args:
            db_manager: 数据库管理器（测试时可注入Mock）
            security_config: 安全配置（测试时可注入自定义配置）
            cache_manager: 缓存管理器（测试时可注入Mock）
        """
        self.config_loader = ConfigLoader(
            db_manager=db_manager,
            cache_manager=cache_manager
        )

        self.dynamic_loader = DynamicCodeLoader(
            db_manager=db_manager,
            security_config=security_config,
            cache_manager=cache_manager
        )

    # ... 其他方法
```

```python
# core/tests/unit/strategies/test_config_loader.py

import pytest
from unittest.mock import Mock, MagicMock
from core.strategies.loaders.config_loader import ConfigLoader


class TestConfigLoader:
    """ConfigLoader单元测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock数据库"""
        db = Mock()
        db.execute_query = MagicMock(return_value=[{
            'id': 1,
            'name': 'test_strategy',
            'strategy_type': 'momentum',
            'config': {'lookback_period': 20},
            'is_active': True,
            'version': 1,
            'config_hash': 'abc123'
        }])
        return db

    @pytest.fixture
    def loader(self, mock_db):
        """创建加载器实例"""
        return ConfigLoader(db_manager=mock_db)

    def test_load_strategy_success(self, loader, mock_db):
        """测试成功加载策略"""
        strategy = loader.load_strategy(config_id=1)

        # 验证数据库调用
        mock_db.execute_query.assert_called_once()

        # 验证策略实例
        assert strategy is not None
        assert strategy.name == 'test_strategy'
        assert strategy._config_id == 1
        assert strategy._config_version == 1

    def test_load_strategy_not_found(self, loader, mock_db):
        """测试策略不存在"""
        mock_db.execute_query.return_value = []

        with pytest.raises(ValueError, match="策略配置不存在"):
            loader.load_strategy(config_id=999)

    def test_load_strategy_disabled(self, loader, mock_db):
        """测试加载已禁用的策略"""
        mock_db.execute_query.return_value = [{
            'id': 1,
            'name': 'test_strategy',
            'is_active': False,
            # ...
        }]

        with pytest.raises(ValueError, match="策略配置已禁用"):
            loader.load_strategy(config_id=1)
```

---

### 4. 日志配置

#### 问题
审计日志和普通日志如何区分？日志格式？

#### 补充方案

```python
# core/src/strategies/security/audit_logger.py (增强版)

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class AuditLogger:
    """审计日志记录器 - 增强版"""

    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 配置专门的审计日志
        self.audit_file = self.log_dir / f"audit_{datetime.now():%Y%m%d}.jsonl"

        # 配置loguru的审计日志handler
        logger.add(
            self.audit_file,
            format="{message}",  # 只记录消息（JSON格式）
            filter=lambda record: record["extra"].get("audit", False),
            rotation="100 MB",
            retention="90 days",
            compression="zip"
        )

    def log_strategy_load(
        self,
        strategy_id: int,
        strategy_type: str,
        strategy_class: str,
        code_hash: str,
        validation_result: Dict[str, Any],
        user: Optional[str] = None,
        **extra
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
            **extra
        }

        self._write_event(event)
        logger.bind(audit=True).info(json.dumps(event, ensure_ascii=False))

    def _write_event(self, event: Dict[str, Any]):
        """写入事件到日志文件"""
        with open(self.audit_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')


# 使用示例
audit_logger = AuditLogger()
audit_logger.log_strategy_load(
    strategy_id=456,
    strategy_type='dynamic',
    strategy_class='SmallCapStrategy',
    code_hash='abc123',
    validation_result={'safe': True},
    user='user_001'
)
```

---

### 5. 错误恢复与降级

#### 问题
当加载失败时，如何优雅降级？

#### 补充方案

```python
# core/src/strategies/loaders/fallback_handler.py

from typing import Optional, Dict, Any
from loguru import logger
from ..base_strategy import BaseStrategy
from ..predefined.momentum_strategy import MomentumStrategy


class FallbackHandler:
    """降级处理器"""

    DEFAULT_STRATEGY_CONFIG = {
        'lookback_period': 20,
        'top_n': 50,
        'holding_period': 5
    }

    @staticmethod
    def get_fallback_strategy(
        reason: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseStrategy:
        """
        获取降级策略

        Args:
            reason: 降级原因
            config: 自定义配置（可选）

        Returns:
            默认的安全策略
        """
        logger.warning(f"触发降级策略: {reason}")

        config = config or FallbackHandler.DEFAULT_STRATEGY_CONFIG

        # 使用最简单、最安全的动量策略
        return MomentumStrategy('fallback_momentum', config)


# 在加载器中使用
class DynamicCodeLoader:
    def load_strategy(self, strategy_id: int, **kwargs):
        try:
            # 正常加载逻辑
            return self._load_strategy_internal(strategy_id, **kwargs)

        except SecurityError as e:
            logger.error(f"安全错误: {e}")

            # 记录到审计日志
            self.audit_logger.log_security_violation(
                strategy_id=strategy_id,
                violation_type='load_failed',
                details={'error': str(e)}
            )

            # 是否允许降级？
            if kwargs.get('allow_fallback', False):
                return FallbackHandler.get_fallback_strategy(
                    reason=f"策略{strategy_id}加载失败，使用默认策略"
                )
            else:
                raise

        except Exception as e:
            logger.exception(f"未知错误: {e}")

            if kwargs.get('allow_fallback', False):
                return FallbackHandler.get_fallback_strategy(
                    reason=f"未知错误: {e}"
                )
            else:
                raise
```

---

### 6. 性能监控指标

#### 问题
如何监控加载和执行性能？

#### 补充方案

```python
# core/src/strategies/monitoring/performance_monitor.py

import time
import functools
from typing import Dict, Any, Callable
from datetime import datetime
from loguru import logger


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics: Dict[str, list] = {
            'load_times': [],
            'execution_times': [],
            'memory_usage': [],
        }

    def monitor_load(self, func: Callable) -> Callable:
        """监控加载性能的装饰器"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = self._get_memory_usage()

            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                end_time = time.time()
                end_memory = self._get_memory_usage()

                # 记录指标
                metric = {
                    'timestamp': datetime.now().isoformat(),
                    'function': func.__name__,
                    'duration_ms': (end_time - start_time) * 1000,
                    'memory_delta_mb': (end_memory - start_memory) / 1024 / 1024,
                    'success': success,
                    'error': error,
                }

                self.metrics['load_times'].append(metric)

                logger.debug(
                    f"性能: {func.__name__} "
                    f"耗时={metric['duration_ms']:.2f}ms "
                    f"内存={metric['memory_delta_mb']:.2f}MB"
                )

            return result

        return wrapper

    def _get_memory_usage(self) -> int:
        """获取当前内存使用（字节）"""
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss

    def get_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.metrics['load_times']:
            return {'message': '暂无数据'}

        load_times = [m['duration_ms'] for m in self.metrics['load_times']]
        memory_deltas = [m['memory_delta_mb'] for m in self.metrics['load_times']]

        return {
            'total_loads': len(load_times),
            'avg_load_time_ms': sum(load_times) / len(load_times),
            'max_load_time_ms': max(load_times),
            'avg_memory_delta_mb': sum(memory_deltas) / len(memory_deltas),
            'success_rate': sum(1 for m in self.metrics['load_times'] if m['success']) / len(self.metrics['load_times']),
        }


# 全局实例
performance_monitor = PerformanceMonitor()


# 使用示例
class DynamicCodeLoader:
    @performance_monitor.monitor_load
    def load_strategy(self, strategy_id: int):
        # ... 加载逻辑
        pass
```

---

## 📝 实施前检查清单

### Phase 1: 环境准备

- [ ] **数据库准备**
  - [ ] 创建 `strategy_configs` 表
  - [ ] 创建 `ai_strategies` 表
  - [ ] 配置数据库连接池
  - [ ] 测试数据库连接

- [ ] **配置文件**
  - [ ] 创建 `core/config/security.yaml`
  - [ ] 创建 `core/config/database.yaml`
  - [ ] 设置环境变量
  - [ ] 验证配置加载

- [ ] **目录结构**
  - [ ] 创建 `core/src/strategies/loaders/`
  - [ ] 创建 `core/src/strategies/security/`
  - [ ] 创建 `core/src/strategies/cache/`
  - [ ] 创建 `core/src/strategies/predefined/`
  - [ ] 创建 `logs/audit/`

- [ ] **依赖安装**
  - [ ] `pip install psutil` (资源监控)
  - [ ] `pip install pyyaml` (配置管理)
  - [ ] 验证所有依赖版本兼容

### Phase 2: 核心模块实施

- [ ] **安全模块**
  - [ ] 实现 `SecurityConfig`
  - [ ] 实现 `CodeSanitizer`
  - [ ] 实现 `PermissionChecker`
  - [ ] 实现 `ResourceLimiter`
  - [ ] 实现 `AuditLogger`
  - [ ] 单元测试覆盖率 > 90%

- [ ] **加载器模块**
  - [ ] 实现 `BaseLoader`
  - [ ] 实现 `ConfigLoader`
  - [ ] 实现 `DynamicCodeLoader`
  - [ ] 实现 `LoaderFactory`
  - [ ] 实现 `FallbackHandler`
  - [ ] 集成测试

- [ ] **工厂改造**
  - [ ] 重构 `StrategyFactory`
  - [ ] 增强 `BaseStrategy`
  - [ ] 重组目录（移动到predefined/）
  - [ ] 更新 `__init__.py`
  - [ ] 回归测试

### Phase 3: 辅助功能

- [ ] **缓存系统**
  - [ ] 实现 `StrategyCache`
  - [ ] 集成 Redis（可选）
  - [ ] 缓存失效策略
  - [ ] 测试缓存效果

- [ ] **监控系统**
  - [ ] 实现 `PerformanceMonitor`
  - [ ] 集成到加载器
  - [ ] 性能指标导出
  - [ ] 告警机制

- [ ] **异常处理**
  - [ ] 扩展异常类
  - [ ] 统一错误码
  - [ ] 错误恢复流程
  - [ ] 测试异常场景

### Phase 4: 测试验证

- [ ] **单元测试**
  - [ ] 安全模块测试（覆盖率 > 95%）
  - [ ] 加载器测试（覆盖率 > 90%）
  - [ ] 工厂测试（覆盖率 > 90%）

- [ ] **集成测试**
  - [ ] 端到端加载测试
  - [ ] 多线程并发测试
  - [ ] 数据库集成测试
  - [ ] 缓存集成测试

- [ ] **安全测试**
  - [ ] 恶意代码注入测试
  - [ ] 资源超限测试
  - [ ] 权限绕过测试
  - [ ] 渗透测试

- [ ] **性能测试**
  - [ ] 加载性能基准
  - [ ] 并发加载测试
  - [ ] 内存泄漏测试
  - [ ] 长时间运行测试

### Phase 5: 文档与部署

- [ ] **文档更新**
  - [ ] API文档
  - [ ] 使用示例
  - [ ] 故障排查指南
  - [ ] 性能调优指南

- [ ] **部署准备**
  - [ ] 数据库迁移脚本
  - [ ] 配置模板
  - [ ] 部署检查清单
  - [ ] 回滚方案

---

## 🔍 潜在风险点

### 1. Python版本兼容性
- **问题**: `resource.setrlimit()` 在不同操作系统行为不一致
- **建议**:
  - 开发时在Linux环境测试
  - Windows环境使用替代方案
  - 增加平台检测逻辑

### 2. 多进程/多线程安全
- **问题**: 数据库连接池在多进程下的行为
- **建议**:
  - 使用进程池模式时，每个进程独立连接
  - 避免在fork后共享数据库连接
  - 测试多进程场景

### 3. 内存管理
- **问题**: 动态加载的代码可能导致内存泄漏
- **建议**:
  - 定期清理缓存
  - 监控内存使用
  - 设置缓存大小上限

### 4. 代码哈希验证
- **问题**: 代码格式变化（空格、换行）导致哈希不匹配
- **建议**:
  - 标准化代码格式（使用black）
  - 存储前后都格式化
  - 或者使用AST哈希

---

## 📊 质量指标

### 代码质量
- [ ] 单元测试覆盖率 > 85%
- [ ] 集成测试覆盖率 > 70%
- [ ] 代码复杂度 < 10 (pylint)
- [ ] 类型提示覆盖率 > 90%

### 性能指标
- [ ] 配置加载 < 100ms (P95)
- [ ] AI策略加载 < 500ms (P95)
- [ ] 内存使用 < 512MB (单策略)
- [ ] 并发支持 > 10 QPS

### 安全指标
- [ ] 通过OWASP Top 10检查
- [ ] 无已知CVE漏洞
- [ ] 代码注入防护 100%
- [ ] 审计日志完整性 100%

---

## 🚀 快速开始

### 1. 克隆并设置环境

```bash
cd /Volumes/MacDriver/stock-analysis/core

# 安装依赖
pip install -r requirements.txt
pip install psutil pyyaml pytest pytest-cov

# 创建配置文件
mkdir -p config
cp docs/planning/examples/security.yaml config/
cp docs/planning/examples/database.yaml config/

# 创建日志目录
mkdir -p logs/audit
```

### 2. 数据库初始化

```bash
# 运行迁移脚本
python scripts/db_migrate.py

# 验证表结构
python scripts/db_verify.py
```

### 3. 运行测试

```bash
# 运行单元测试
pytest tests/unit/strategies/ -v --cov=src/strategies

# 运行集成测试
pytest tests/integration/strategies/ -v

# 运行安全测试
pytest tests/security/strategies/ -v
```

### 4. 验证安装

```python
from core.strategies import StrategyFactory

factory = StrategyFactory()

# 测试预定义策略
strategy = factory.create('momentum', {'lookback_period': 20})
print(f"✓ 预定义策略创建成功: {strategy.name}")

# 测试配置加载（需要数据库）
# strategy = factory.create_from_config(config_id=1)
# print(f"✓ 配置加载成功: {strategy.name}")
```

---

## 📞 支持

**问题反馈**: 创建 GitHub Issue
**紧急联系**: Architecture Team
**文档贡献**: 提交 Pull Request

---

**最后更新**: 2026-02-08
**下一步**: 开始 Phase 1 实施
