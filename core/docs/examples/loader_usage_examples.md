# 策略加载器使用示例

本文档提供策略加载器系统的详细使用示例。

---

## 📋 目录

1. [基础使用](#基础使用)
2. [参数配置方案](#参数配置方案)
3. [AI代码生成方案](#ai代码生成方案)
4. [批量操作](#批量操作)
5. [缓存管理](#缓存管理)
6. [错误处理](#错误处理)
7. [高级用法](#高级用法)

---

## 基础使用

### 1. 导入模块

```python
from src.strategies.loaders import LoaderFactory
from loguru import logger

# 创建加载器工厂（单例模式）
factory = LoaderFactory()
```

---

## 参数配置方案

### 1. 加载单个配置策略

```python
# 从数据库加载配置ID为1的策略
strategy = factory.load_strategy(
    strategy_source='config',
    strategy_id=1,
    use_cache=True
)

print(f"策略名称: {strategy.name}")
print(f"策略类型: {strategy._strategy_type}")
print(f"配置版本: {strategy._config_version}")
```

### 2. 列出可用配置

```python
# 获取配置加载器
config_loader = factory.get_loader('config')

# 列出所有激活的配置
configs = config_loader.list_available_configs(
    active_only=True,
    strategy_type='momentum'  # 可选：过滤类型
)

for config in configs:
    print(f"ID: {config['id']}, 名称: {config['name']}")
```

### 3. 重新加载配置

```python
# 清除缓存并重新加载
strategy = factory.reload_strategy(
    strategy_source='config',
    strategy_id=1
)
```

---

## AI代码生成方案

### 1. 加载动态策略（严格模式）

```python
# 加载AI生成的策略，开启严格安全检查
try:
    strategy = factory.load_strategy(
        strategy_source='dynamic',
        strategy_id=1,
        strict_mode=True,  # 任何安全问题都拒绝
        use_cache=True
    )

    print(f"策略名称: {strategy.name}")
    print(f"风险等级: {strategy._risk_level}")
    print(f"代码哈希: {strategy._code_hash[:8]}...")

    # 检查警告
    if strategy._validation_warnings:
        logger.warning(f"安全警告: {strategy._validation_warnings}")

except Exception as e:
    logger.error(f"加载失败: {e}")
```

### 2. 加载动态策略（宽松模式）

```python
# 宽松模式：允许低风险警告
strategy = factory.load_strategy(
    strategy_source='dynamic',
    strategy_id=1,
    strict_mode=False  # 允许一些警告
)

# 检查风险等级
if strategy._risk_level in ['medium', 'high']:
    logger.warning(f"策略风险等级较高: {strategy._risk_level}")
```

### 3. 列出可用的AI策略

```python
# 获取动态加载器
dynamic_loader = factory.get_loader('dynamic')

# 列出所有启用且验证通过的策略
strategies = dynamic_loader.list_available_strategies(
    enabled_only=True,
    validated_only=True
)

for strat in strategies:
    print(f"ID: {strat['id']}, 名称: {strat['strategy_name']}")
    print(f"验证状态: {strat['validation_status']}")
    print(f"测试状态: {strat['test_status']}")
```

---

## 批量操作

### 1. 批量加载混合策略

```python
# 混合加载配置策略和动态策略
strategy_configs = [
    {'source': 'config', 'id': 1},
    {'source': 'config', 'id': 2},
    {'source': 'dynamic', 'id': 1},
    {'source': 'dynamic', 'id': 2},
]

results = factory.batch_load_strategies(
    strategy_configs,
    use_cache=True,
    strict_mode=True
)

# 结果分组
print(f"成功加载配置策略: {len(results['config'])} 个")
print(f"成功加载动态策略: {len(results['dynamic'])} 个")

# 使用策略
for strategy_id, strategy in results['config'].items():
    print(f"配置策略 {strategy_id}: {strategy.name}")

for strategy_id, strategy in results['dynamic'].items():
    print(f"动态策略 {strategy_id}: {strategy.name}")
```

### 2. 容错的批量加载

```python
# 即使部分加载失败，也继续加载其他策略
results = factory.batch_load_strategies(strategy_configs)

# 检查失败的策略
total = len(strategy_configs)
success = len(results['config']) + len(results['dynamic'])

if success < total:
    logger.warning(f"部分策略加载失败: {success}/{total}")
```

---

## 缓存管理

### 1. 查看缓存信息

```python
# 获取所有加载器的缓存信息
cache_info = factory.get_cache_info()

print("配置加载器缓存:")
print(f"  缓存数量: {cache_info['config_loader']['cached_count']}")
print(f"  缓存ID: {cache_info['config_loader']['cached_ids']}")

print("动态加载器缓存:")
print(f"  缓存数量: {cache_info['dynamic_loader']['cached_count']}")
print(f"  缓存ID: {cache_info['dynamic_loader']['cached_ids']}")
```

### 2. 清除缓存

```python
# 清除所有缓存
factory.clear_cache()

# 只清除配置加载器的缓存
factory.clear_cache('config')

# 只清除动态加载器的缓存
factory.clear_cache('dynamic')
```

### 3. 使用策略缓存

```python
from src.strategies.cache import StrategyCache

# 创建自定义缓存（TTL=60分钟）
cache = StrategyCache(ttl_minutes=60)

# 设置缓存
cache.set('my_strategy', strategy)

# 获取缓存
cached_strategy = cache.get('my_strategy')

# 查看统计
stats = cache.get_stats()
print(f"缓存统计: {stats}")

# 清理过期缓存
cache.cleanup_expired()
```

---

## 错误处理

### 1. 处理加载错误

```python
from src.exceptions import (
    StrategyLoadError,
    StrategySecurityError,
    ConfigNotFoundError
)

try:
    strategy = factory.load_strategy('dynamic', 1, strict_mode=True)

except StrategySecurityError as e:
    # 安全验证失败
    logger.error(f"安全错误: {e}")
    # 可能需要：禁用该策略、通知管理员

except ConfigNotFoundError as e:
    # 配置不存在
    logger.error(f"配置不存在: {e}")

except StrategyLoadError as e:
    # 其他加载错误
    logger.error(f"加载错误: {e}")

except Exception as e:
    # 未知错误
    logger.exception(f"未知错误: {e}")
```

### 2. 安全降级

```python
def load_strategy_with_fallback(strategy_id: int):
    """加载策略，失败时使用默认策略"""
    try:
        # 尝试加载动态策略
        strategy = factory.load_strategy('dynamic', strategy_id, strict_mode=True)
        return strategy

    except StrategySecurityError:
        logger.warning(f"策略 {strategy_id} 安全验证失败，使用默认策略")

        # 降级：使用配置策略
        try:
            return factory.load_strategy('config', 1)  # 默认配置
        except Exception:
            # 最终降级：返回None或抛出异常
            return None
```

---

## 高级用法

### 1. 直接使用加载器

```python
# 直接使用ConfigLoader
from src.strategies.loaders import ConfigLoader

config_loader = ConfigLoader()

# 加载策略
strategy = config_loader.load_strategy(1)

# 批量加载
strategies = config_loader.batch_load_strategies([1, 2, 3])
```

### 2. 自定义受限命名空间

```python
from src.strategies.loaders import DynamicCodeLoader

# 创建加载器
loader = DynamicCodeLoader()

# 查看默认的受限命名空间
restricted = loader._create_restricted_globals()

print("允许的内置函数:", restricted['__builtins__'].keys())
print("允许的模块:", [k for k in restricted.keys() if k != '__builtins__'])
```

### 3. 手动编译代码

```python
# 直接编译AI代码（高级用法）
loader = DynamicCodeLoader()

# Python代码字符串
code = """
class MyStrategy(BaseStrategy):
    def generate_signals(self, prices, features=None, **kwargs):
        return pd.DataFrame(0, index=prices.index, columns=prices.columns)

    def calculate_scores(self, prices, features=None, date=None):
        return pd.Series(0, index=prices.columns)
"""

# 编译加载
try:
    StrategyClass = loader._compile_and_load(
        code=code,
        class_name='MyStrategy',
        module_name='custom_strategy'
    )

    # 实例化
    strategy = StrategyClass('MyCustomStrategy', {'top_n': 10})

except Exception as e:
    logger.error(f"编译失败: {e}")
```

### 4. 审计日志查询

```python
from src.strategies.security import AuditLogger

# 创建审计日志记录器
audit = AuditLogger()

# 记录会自动保存到 logs/audit/audit_YYYYMMDD.jsonl

# 可以使用Python读取和分析
import json

log_file = 'logs/audit/audit_20260208.jsonl'

with open(log_file, 'r') as f:
    for line in f:
        event = json.loads(line)

        if event['event_type'] == 'security_violation':
            print(f"安全违规: {event}")
```

---

## 完整示例：端到端流程

```python
from src.strategies.loaders import LoaderFactory
from src.exceptions import StrategySecurityError
from loguru import logger
import pandas as pd
import numpy as np

# 1. 初始化工厂
factory = LoaderFactory()

# 2. 加载策略（混合方式）
strategies = []

try:
    # 加载配置策略
    config_strat = factory.load_strategy('config', 1)
    strategies.append(config_strat)
    logger.success(f"配置策略加载成功: {config_strat.name}")

except Exception as e:
    logger.error(f"配置策略加载失败: {e}")

try:
    # 加载AI策略（严格模式）
    ai_strat = factory.load_strategy('dynamic', 1, strict_mode=True)
    strategies.append(ai_strat)
    logger.success(f"AI策略加载成功: {ai_strat.name}, 风险={ai_strat._risk_level}")

except StrategySecurityError as e:
    logger.error(f"AI策略安全验证失败: {e}")

# 3. 准备测试数据
dates = pd.date_range('2024-01-01', periods=100)
stocks = ['STOCK1', 'STOCK2', 'STOCK3', 'STOCK4', 'STOCK5']
prices = pd.DataFrame(
    np.random.randn(100, 5).cumsum(axis=0) + 100,
    index=dates,
    columns=stocks
)

# 4. 执行策略
for strategy in strategies:
    try:
        # 生成信号
        signals = strategy.generate_signals(prices)

        # 计算评分
        scores = strategy.calculate_scores(prices)

        logger.info(f"策略 {strategy.name} 执行成功")
        logger.info(f"  信号形状: {signals.shape}")
        logger.info(f"  平均评分: {scores.mean():.4f}")

    except Exception as e:
        logger.error(f"策略 {strategy.name} 执行失败: {e}")

# 5. 查看缓存统计
cache_info = factory.get_cache_info()
logger.info(f"缓存统计: {cache_info}")

# 6. 清理（可选）
# factory.clear_cache()
```

---

## 🔒 安全最佳实践

### 1. 始终使用严格模式加载AI策略

```python
# ✅ 推荐
strategy = factory.load_strategy('dynamic', 1, strict_mode=True)

# ⚠️ 谨慎使用
strategy = factory.load_strategy('dynamic', 1, strict_mode=False)
```

### 2. 检查风险等级

```python
strategy = factory.load_strategy('dynamic', 1, strict_mode=True)

if strategy._risk_level != 'safe':
    logger.warning(f"策略风险等级: {strategy._risk_level}")
    # 考虑是否继续使用
```

### 3. 监控审计日志

```python
# 定期检查审计日志
from src.strategies.security import AuditLogger

audit = AuditLogger()
# 日志会自动记录到 logs/audit/ 目录
```

### 4. 限制策略权限

动态策略默认受限，不能：
- ❌ 访问文件系统
- ❌ 进行网络操作
- ❌ 执行系统命令
- ❌ 导入危险模块
- ✅ 只能使用 pandas/numpy 进行数据分析

---

## 📚 相关文档

- [Phase 2 实现报告](../planning/phase2_loader_implementation_report.md)
- [策略系统架构设计](../planning/core_strategy_system_refactoring.md)
- [安全模块文档](../security/security_module_guide.md)

---

**文档版本**: v1.0
**最后更新**: 2026-02-08
