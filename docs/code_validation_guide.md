# AI 策略代码验证指南

## 概述

本系统对 AI 生成的策略代码进行多层次的安全验证，确保代码安全可靠。

## 验证流程

```
AI 生成代码
    ↓
1. 代码完整性验证（哈希校验）
    ↓
2. 语法检查（AST 解析）
    ↓
3. 导入模块检查
    ↓
4. 函数调用检查
    ↓
5. 方法调用检查 ⭐ 新增
    ↓
6. 属性访问检查
    ↓
7. 字符串内容检查
    ↓
验证结果（safe/unsafe + 风险等级）
```

## 方法调用验证策略 ⭐ 宽松策略

### 验证原则

系统采用**宽松策略**：
- ✅ **默认允许** - 除非明确禁止，否则都允许使用
- ❌ **仅禁止危险操作** - 只拒绝明确危险的方法（如 `eval`, `exec`, `open` 等）
- ⚠️ **最小化警告** - 减少不必要的警告，让用户更容易生成策略

### 1. Logger 方法（全局 logger）

**允许的方法**：
- `logger.debug()` - 调试信息
- `logger.info()` - 一般信息
- `logger.warning()` - 警告信息
- `logger.error()` - 错误信息
- `logger.critical()` - 严重错误
- `logger.success()` - 成功信息

**示例**：
```python
from loguru import logger

# ✅ 正确
logger.info("策略初始化完成")
logger.warning("数据不足")
logger.error(f"计算失败: {str(e)}")

# ❌ 错误（会被拒绝）
self.logger.info("错误用法")
```

### 2. Pandas 库 - ✅ 几乎全部允许

**核心类**（必须导入）：
```python
import pandas as pd

# ✅ 完全允许
df = pd.DataFrame(data)
series = pd.Series(values)
index = pd.DatetimeIndex(dates)
```

**所有 DataFrame/Series 方法都允许使用**，包括但不限于：
- 数据访问: `loc`, `iloc`, `at`, `iat`, `values`, `index`, `columns`
- 数据处理: `fillna`, `dropna`, `replace`, `interpolate`, `bfill`, `ffill`
- 统计分析: `mean`, `median`, `std`, `var`, `corr`, `describe`, `quantile`
- 数据转换: `rolling`, `ewm`, `groupby`, `resample`, `pivot`, `melt`
- 数据合并: `merge`, `join`, `concat`, `append`
- 其他操作: `apply`, `applymap`, `astype`, `copy`, `sort_values`, `reset_index`

### 3. NumPy 库 - ✅ 几乎全部允许

**所有 NumPy 函数都允许使用**，包括但不限于：
```python
import numpy as np

# ✅ 完全允许
arr = np.array([1, 2, 3])
mean = np.mean(arr)
std = np.std(arr)
result = np.where(condition, x, y)
mask = np.isnan(data)
```

### 4. BaseStrategy 方法 - ✅ 完全允许

**基类方法**：
- `self.filter_stocks()` - 过滤股票
- `self.validate_signals()` - 验证信号
- `self.get_position_weights()` - 计算持仓权重
- `self.config.custom_params.get()` - 获取配置参数

**自定义方法**：
- ✅ 允许定义和调用任何私有方法（以 `_` 开头）
- ✅ 允许定义和调用任何公有方法

**示例**：
```python
class MyStrategy(BaseStrategy):
    def _calculate_indicator(self, prices):
        """✅ 允许：私有辅助方法"""
        return prices.rolling(20).mean()

    def generate_signals(self, prices, features=None, **kwargs):
        # ✅ 允许：调用基类方法
        valid_stocks = self.filter_stocks(prices)

        # ✅ 允许：调用自定义方法
        indicator = self._calculate_indicator(prices)

        # ✅ 允许：访问配置
        top_n = self.config.custom_params.get('top_n', 20)
```

## 禁止的内容

### 1. 禁止的导入模块
```python
# ❌ 禁止
import os
import sys
import subprocess
import socket
import requests
import pickle
```

### 2. 禁止的函数
```python
# ❌ 禁止
eval("code")
exec("code")
compile("code")
open("file.txt")
__import__("module")
getattr(obj, "attr")
```

### 3. 禁止的属性
```python
# ❌ 禁止
obj.__dict__
obj.__class__
obj.__globals__
obj.__code__
```

### 4. 禁止的日志用法
```python
# ❌ 禁止
self.logger.info("message")  # 必须使用全局 logger
```

## 验证结果

### 风险等级

- **safe** - 完全安全，无任何问题
- **low** - 低风险，可能有少量警告
- **medium** - 中风险，有较多警告
- **high** - 高风险，存在安全问题，拒绝加载

### 返回结果示例

```python
{
    'safe': True,
    'sanitized_code': '...',
    'errors': [],
    'warnings': ['未知的 logger 方法: logger.trace'],
    'risk_level': 'low',
    'method_calls': {  # ⭐ 新增
        'info': 3,
        'fillna': 1,
        'mean': 2,
        'std': 1
    }
}
```

## AI 生成时的指导

在 AI 生成策略时，系统会自动提供以下指导：

### 1. 允许使用的库和方法
明确列出可用的 Pandas、NumPy 方法

### 2. 正确的日志使用
- ✅ 使用全局 `logger`
- ❌ 禁止 `self.logger`

### 3. 安全编码规范
- 数据验证
- 错误处理
- 避免危险操作

## 示例：完整的验证流程

```python
from src.strategies.security.code_sanitizer import CodeSanitizer

sanitizer = CodeSanitizer()

# AI 生成的代码
generated_code = """
from loguru import logger
import pandas as pd
import numpy as np
from core.strategies.base_strategy import BaseStrategy

class MomentumStrategy(BaseStrategy):
    def generate_signals(self, prices, features=None, **kwargs):
        try:
            logger.info("开始生成动量信号")

            # 计算动量
            returns = prices.pct_change()
            momentum = returns.rolling(window=20).mean()

            # 生成信号
            signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)
            top_stocks = momentum.iloc[-1].nlargest(10).index
            signals.loc[signals.index[-1], top_stocks] = 1

            logger.success("信号生成完成")
            return signals

        except Exception as e:
            logger.error(f"生成信号失败: {str(e)}")
            raise
"""

# 验证代码
result = sanitizer.sanitize(generated_code, strict_mode=True)

print(f"安全: {result['safe']}")
print(f"风险等级: {result['risk_level']}")
print(f"错误: {result['errors']}")
print(f"警告: {result['warnings']}")
print(f"方法调用统计: {result['method_calls']}")

# 输出:
# 安全: True
# 风险等级: safe
# 错误: []
# 警告: []
# 方法调用统计: {'info': 1, 'pct_change': 1, 'rolling': 1, 'mean': 1, ...}
```

## 相关文件

- **代码验证**: `core/src/strategies/security/code_sanitizer.py`
- **动态加载**: `core/src/strategies/loaders/dynamic_loader.py`
- **AI 服务**: `backend/app/services/ai_service.py`
- **测试文件**: `core/tests/test_code_sanitizer_methods.py`

## 更新日志

### 2026-03-09
- ✅ 添加方法调用白名单检查
- ✅ 禁止使用 `self.logger`
- ✅ 更新 AI 提示词，列出允许的方法
- ✅ 添加方法调用统计功能

---

**最后更新**: 2026-03-09
