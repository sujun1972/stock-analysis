# 代码规范

**Coding Standards for Stock-Analysis Core**

**版本**: v3.0.0
**最后更新**: 2026-02-01

---

## 🎯 总则

本文档定义了 Stock-Analysis Core 项目的代码规范。遵循这些规范可以提高代码质量、可读性和可维护性。

**核心原则**:
- ✅ **可读性优先**: 代码是写给人看的
- ✅ **一致性**: 保持项目风格统一
- ✅ **简洁性**: 简单优于复杂
- ✅ **文档化**: 重要逻辑必须有注释

---

## 🐍 Python风格指南

### 1. 基本规范

遵循 **PEP 8** 标准，但有以下例外和补充：

**行长度**:
```python
# 最大行长度: 100字符（而非PEP 8的79）
# 文档字符串: 72字符

# ✅ 好的
def calculate_alpha_factor(data: pd.DataFrame, window: int = 20) -> pd.Series:
    """计算Alpha因子"""
    pass

# ❌ 避免过长
def calculate_alpha_factor_with_multiple_parameters_and_very_long_name(data: pd.DataFrame, window: int = 20, smooth: bool = True, normalize: bool = False) -> pd.Series:
    pass
```

**缩进**:
```python
# 使用4个空格（禁止Tab）

# ✅ 好的
if condition:
    do_something()
    do_another_thing()

# ❌ 错误：混用Tab和空格
if condition:
	do_something()  # Tab
    do_another_thing()  # 空格
```

### 2. 命名规范

**变量和函数**: `snake_case`
```python
# ✅ 好的
stock_code = "000001.SZ"
def calculate_returns(prices: pd.Series) -> pd.Series:
    pass

# ❌ 避免
stockCode = "000001.SZ"  # camelCase
def CalculateReturns(prices):  # PascalCase
    pass
```

**类名**: `PascalCase`
```python
# ✅ 好的
class AlphaStrategy:
    pass

class BacktestEngine:
    pass

# ❌ 避免
class alpha_strategy:  # snake_case
    pass
```

**常量**: `UPPER_SNAKE_CASE`
```python
# ✅ 好的
MAX_POSITION_SIZE = 0.1
DEFAULT_COMMISSION_RATE = 0.0003

# ❌ 避免
max_position_size = 0.1  # 小写
```

**私有属性/方法**: 单下划线前缀
```python
class DataProvider:
    def __init__(self):
        self._cache = {}  # 私有属性

    def _fetch_data(self):  # 私有方法
        pass

    def get_data(self):  # 公共方法
        return self._fetch_data()
```

**特殊命名**:
```python
# DataFrame列名: 小写+下划线
df.columns = ['stock_code', 'trade_date', 'close_price']

# 配置key: 大写+下划线
config = {
    'DATABASE_URL': '...',
    'REDIS_HOST': 'localhost'
}
```

### 3. 类型提示

**必须使用类型提示**:

```python
from typing import List, Dict, Optional, Union, Tuple

# ✅ 好的：完整的类型提示
def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.03
) -> float:
    """计算夏普比率"""
    pass

def get_stock_data(
    stock_codes: List[str],
    start_date: str,
    end_date: Optional[str] = None
) -> Dict[str, pd.DataFrame]:
    """获取股票数据"""
    pass

# ❌ 避免：缺少类型提示
def calculate_sharpe_ratio(returns, risk_free_rate=0.03):
    pass
```

**复杂类型**:
```python
from typing import TypedDict, Callable

# 使用TypedDict定义字典结构
class TradeSignal(TypedDict):
    stock_code: str
    signal: int  # 1=买入, -1=卖出, 0=持有
    confidence: float

# 函数类型
FeatureFunction = Callable[[pd.DataFrame], pd.Series]

def apply_features(
    data: pd.DataFrame,
    functions: List[FeatureFunction]
) -> pd.DataFrame:
    pass
```

### 4. 文档字符串

使用 **Google Style** 文档字符串：

```python
def calculate_alpha_factor(
    data: pd.DataFrame,
    window: int = 20,
    min_periods: Optional[int] = None
) -> pd.Series:
    """
    计算Alpha因子

    该函数基于历史价格数据计算Alpha因子值，用于量化股票的超额收益潜力。
    计算方法采用滚动窗口统计量。

    Args:
        data: 包含价格数据的DataFrame，必须包含'close'列
        window: 滚动窗口大小，默认20个交易日
        min_periods: 最小观测值数量，默认为None（等于window）

    Returns:
        pd.Series: Alpha因子值，索引与输入data相同

    Raises:
        ValueError: 当data为空或缺少必需列时
        TypeError: 当window不是整数时

    Examples:
        >>> data = pd.DataFrame({'close': [100, 102, 101, 103, 105]})
        >>> alpha = calculate_alpha_factor(data, window=3)
        >>> print(alpha)
        0       NaN
        1       NaN
        2    0.0050
        3    0.0147
        4    0.0244
        dtype: float64

    Notes:
        - 前window-1个值将为NaN
        - 因子值已进行标准化处理
        - 建议window范围: 10-60个交易日

    References:
        - Smith, J. (2023). "Alpha Factor Analysis"
    """
    if data.empty:
        raise ValueError("Input data cannot be empty")

    if 'close' not in data.columns:
        raise ValueError("Data must contain 'close' column")

    # 实现逻辑...
    pass
```

**简短函数**:
```python
def get_stock_code(symbol: str) -> str:
    """将股票代码转换为标准格式"""
    return symbol.upper().replace(' ', '')
```

### 5. 导入规范

**导入顺序**:
```python
# 1. 标准库
import os
import sys
from datetime import datetime
from typing import List, Dict

# 2. 第三方库
import numpy as np
import pandas as pd
import torch
from loguru import logger

# 3. 本地模块
from src.data.database_manager import DatabaseManager
from src.utils.exceptions import DataValidationError
from src.utils.response import Response
```

**避免通配符导入**:
```python
# ✅ 好的
from src.features.alpha_factors import calculate_momentum
from src.features.alpha_factors import calculate_volatility

# ❌ 避免
from src.features.alpha_factors import *
```

---

## 📝 代码组织

### 1. 文件结构

```python
"""
模块文档字符串：简要说明模块用途
"""

# 1. 导入
import pandas as pd
from typing import List

# 2. 常量
DEFAULT_WINDOW = 20
MAX_STOCKS = 100

# 3. 类定义
class AlphaStrategy:
    """策略类"""
    pass

# 4. 函数定义
def calculate_alpha(data: pd.DataFrame) -> pd.Series:
    """计算Alpha"""
    pass

# 5. 主程序入口（如适用）
if __name__ == '__main__':
    main()
```

### 2. 函数长度

**建议**:
- ✅ 单个函数≤50行
- ✅ 复杂函数拆分为多个子函数
- ✅ 一个函数只做一件事

```python
# ✅ 好的：拆分为多个函数
def backtest_strategy(data: pd.DataFrame, strategy: BaseStrategy) -> BacktestResult:
    """执行回测"""
    signals = _generate_signals(data, strategy)
    positions = _calculate_positions(signals)
    trades = _execute_trades(positions)
    metrics = _calculate_metrics(trades)
    return BacktestResult(metrics)

def _generate_signals(data, strategy):
    """生成交易信号"""
    pass

# ❌ 避免：单个函数过长（100+行）
def backtest_strategy_long(data, strategy):
    # 生成信号（30行）
    # 计算仓位（30行）
    # 执行交易（30行）
    # 计算指标（30行）
    pass
```

### 3. 类设计

**单一职责原则**:
```python
# ✅ 好的：职责单一
class DataProvider:
    """数据获取"""
    def get_stock_data(self, code: str) -> pd.DataFrame:
        pass

class DataValidator:
    """数据验证"""
    def validate(self, data: pd.DataFrame) -> bool:
        pass

# ❌ 避免：职责过多
class DataManager:
    def get_data(self):
        pass

    def validate_data(self):
        pass

    def save_data(self):
        pass

    def visualize_data(self):  # 职责过多
        pass
```

---

## 🧪 代码质量

### 1. 错误处理

**使用自定义异常**:
```python
from src.utils.exceptions import DataValidationError, ModelTrainingError

# ✅ 好的：具体的异常类型
def validate_data(data: pd.DataFrame) -> None:
    if data.empty:
        raise DataValidationError("Data cannot be empty")

    if data.isna().any().any():
        raise DataValidationError("Data contains missing values")

# ❌ 避免：通用异常
def validate_data(data):
    if data.empty:
        raise Exception("Error")  # 太笼统
```

**异常处理**:
```python
# ✅ 好的：具体捕获
try:
    data = fetch_stock_data(code)
except ConnectionError as e:
    logger.error(f"Network error: {e}")
    return Response.error("Network connection failed")
except DataValidationError as e:
    logger.warning(f"Invalid data: {e}")
    return Response.error("Data validation failed")

# ❌ 避免：捕获所有异常
try:
    data = fetch_stock_data(code)
except Exception:  # 太宽泛
    pass
```

### 2. 日志记录

```python
from loguru import logger

# ✅ 好的：清晰的日志
logger.info(f"Starting backtest for {stock_code}")
logger.debug(f"Calculated {len(features)} features")
logger.warning(f"Low data quality: missing {missing_pct:.1f}%")
logger.error(f"Failed to fetch data: {error}")

# ❌ 避免：不清晰的日志
logger.info("Starting")  # 缺少上下文
logger.debug(features)  # 输出对象而非描述
```

### 3. 注释规范

**何时写注释**:
```python
# ✅ 好的：解释"为什么"
# 使用指数加权移动平均以减少噪声
ema = data['close'].ewm(span=20).mean()

# 提前7天避免财报发布期的异常波动
earnings_buffer = 7

# ❌ 避免：解释"是什么"（代码本身已清楚）
# 计算平均值
mean = data.mean()  # 无需注释
```

**复杂逻辑**:
```python
def calculate_ic(
    factor_values: pd.DataFrame,
    forward_returns: pd.DataFrame,
    periods: List[int] = [5, 10, 20]
) -> Dict[int, float]:
    """
    计算因子IC值（信息系数）

    IC = Correlation(factor_t, return_{t+n})

    步骤:
    1. 对每个时间点，计算因子值与未来收益的相关性
    2. 对所有时间点的相关系数取平均
    3. 重复上述过程计算不同期限的IC

    高IC值(>0.05)表示因子有较强的预测能力
    """
    ic_results = {}

    for period in periods:
        # 1. 计算未来period天的收益
        future_returns = forward_returns.shift(-period)

        # 2. 计算每个截面期的相关系数
        correlations = []
        for date in factor_values.index:
            if date in future_returns.index:
                corr = factor_values.loc[date].corr(
                    future_returns.loc[date]
                )
                correlations.append(corr)

        # 3. 平均IC
        ic_results[period] = np.mean(correlations)

    return ic_results
```

---

## ✅ 最佳实践

### 1. 使用列表推导式

```python
# ✅ 好的：列表推导式
squared = [x**2 for x in numbers if x > 0]

# ❌ 避免：循环
squared = []
for x in numbers:
    if x > 0:
        squared.append(x**2)
```

### 2. 使用上下文管理器

```python
# ✅ 好的：自动关闭资源
with open('data.csv', 'r') as f:
    data = f.read()

with DatabaseManager() as db:
    results = db.query('SELECT * FROM stocks')

# ❌ 避免：手动管理
f = open('data.csv', 'r')
data = f.read()
f.close()  # 可能忘记关闭
```

### 3. 使用生成器

```python
# ✅ 好的：内存高效
def read_large_file(filepath: str):
    """逐行读取大文件"""
    with open(filepath) as f:
        for line in f:
            yield line.strip()

# ❌ 避免：一次性加载到内存
def read_large_file(filepath):
    with open(filepath) as f:
        return f.readlines()  # 内存占用大
```

### 4. 字符串格式化

```python
name = "AAPL"
price = 150.25

# ✅ 推荐：f-string（Python 3.6+）
message = f"Stock {name} is trading at ${price:.2f}"

# ✅ 可以：format()
message = "Stock {} is trading at ${:.2f}".format(name, price)

# ❌ 避免：%格式化（旧式）
message = "Stock %s is trading at $%.2f" % (name, price)
```

---

## 🔍 代码审查清单

### 提交前自查

- [ ] 代码遵循PEP 8规范
- [ ] 所有函数有类型提示
- [ ] 公共函数有文档字符串
- [ ] 复杂逻辑有注释
- [ ] 没有硬编码的常量
- [ ] 错误处理完善
- [ ] 变量命名清晰
- [ ] 没有重复代码
- [ ] 测试覆盖率≥90%
- [ ] 所有测试通过

---

## 🛠️ 工具配置

### 1. Black（代码格式化）

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py39']
include = '\.pyi?$'
extend-exclude = '''
/(
  \.git
  | \.venv
  | build
  | dist
)/
'''
```

### 2. isort（导入排序）

```toml
# pyproject.toml
[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
```

### 3. pylint（代码检查）

```toml
# pyproject.toml
[tool.pylint.messages_control]
max-line-length = 100
disable = [
    "C0111",  # missing-docstring (由其他工具检查)
    "R0903",  # too-few-public-methods
]
```

### 4. mypy（类型检查）

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

---

## 📚 参考资源

- [PEP 8 -- Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Clean Code in Python](https://github.com/zedr/clean-code-python)

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-01
