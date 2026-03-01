# AI 策略生成提示词 - 快速参考

这个文档提供了完整的AI提示词模板，可以直接复制给 Claude、ChatGPT 等AI工具生成量化策略代码。

---

## 🚀 快速开始

### 使用前端页面（推荐）

1. 访问策略创建页面：`http://localhost:3000/strategies/create?source=custom`
2. 在"AI策略生成助手"卡片中填写策略需求
3. 点击"复制提示词"
4. 粘贴到AI对话（Claude 3.5 Sonnet 推荐）
5. 获取代码和元信息，填写到页面中

### 手动复制使用

如果需要手动使用提示词，请复制下方的完整模板，并替换 `[策略需求描述]` 部分。

---

## 📋 完整提示词模板

```markdown
# 量化交易策略代码生成任务

## 任务目标
请为我生成一个完整的Python量化交易策略代码，要求能够通过系统验证并可直接使用。

## 代码框架要求

### 1. 必须的导入语句
```python
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from core.strategies.base_strategy import BaseStrategy
```

### 2. 必须实现的三个方法

#### 2.1 初始化方法 (__init__)
```python
def __init__(self, name: str = "strategy_name", config: Dict[str, Any] = None):
    """
    初始化策略

    Args:
        name: 策略名称
        config: 策略配置字典
    """
    # 定义默认配置
    default_config = {
        'name': 'StrategyName',
        'description': '策略描述',
        'top_n': 20,                # 每期选择前N只股票
        'holding_period': 5,        # 最短持仓期（天）
        'rebalance_freq': 'W',      # 调仓频率 ('D'=日, 'W'=周, 'M'=月)

        # 在这里添加策略特有参数
        # 例如: 'ema_short': 20, 'ema_mid': 60
    }

    # 合并用户配置
    if config:
        default_config.update(config)

    super().__init__(name, default_config)
```

#### 2.2 计算评分方法 (calculate_scores) - 必须实现
```python
def calculate_scores(
    self,
    prices: pd.DataFrame,
    features: Optional[pd.DataFrame] = None,
    date: Optional[pd.Timestamp] = None
) -> pd.Series:
    """
    计算股票评分（用于排序选股）

    Args:
        prices: 价格DataFrame (index=date, columns=stock_codes)
        features: 特征DataFrame (可选)
        date: 指定日期（None表示最新日期）

    Returns:
        scores: 股票评分Series (index=stock_codes, values=scores)
                分数越高越好
    """
    if date is None:
        date = prices.index[-1]

    scores = pd.Series(0.0, index=prices.columns)

    for stock in prices.columns:
        try:
            stock_prices = prices[stock].dropna()
            if len(stock_prices) < 120:  # 数据不足，跳过
                continue

            # TODO: 在这里实现评分逻辑
            # 示例: 基于趋势和动能的综合评分
            # scores[stock] = trend_score * 0.6 + momentum_score * 0.4

        except Exception:
            continue

    return scores
```

#### 2.3 生成信号方法 (generate_signals) - 必须实现
```python
def generate_signals(
    self,
    prices: pd.DataFrame,
    features: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.DataFrame:
    """
    生成交易信号

    Args:
        prices: 价格DataFrame (index=date, columns=stock_codes, values=close_price)
        features: 特征DataFrame (可选)
        **kwargs: 其他参数

    Returns:
        signals: 信号DataFrame (index=date, columns=stock_codes)
            值: 1 = 买入, 0 = 持有, -1 = 卖出
    """
    # 初始化信号矩阵
    signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)

    # 逐个股票计算信号
    for stock in prices.columns:
        try:
            stock_prices = prices[stock].dropna()
            if len(stock_prices) < 120:
                continue

            # TODO: 在这里实现信号生成逻辑
            # 1. 计算技术指标
            # 2. 判断买入条件
            # 3. 判断卖出条件

        except Exception:
            continue

    return signals
```

## 常用技术指标计算参考

### 趋势指标
```python
# 简单移动平均线 (SMA)
sma = prices.rolling(window=20).mean()

# 指数移动平均线 (EMA)
ema = prices.ewm(span=20, adjust=False).mean()

# 布林带 (Bollinger Bands)
sma = prices.rolling(window=20).mean()
std = prices.rolling(window=20).std()
upper_band = sma + (std * 2)
lower_band = sma - (std * 2)
```

### 动量指标
```python
# MACD
ema_fast = prices.ewm(span=12, adjust=False).mean()
ema_slow = prices.ewm(span=26, adjust=False).mean()
macd = ema_fast - ema_slow
signal = macd.ewm(span=9, adjust=False).mean()
histogram = macd - signal

# RSI (相对强弱指数)
delta = prices.diff()
gain = delta.where(delta > 0, 0).rolling(window=14).mean()
loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
rs = gain / loss
rsi = 100 - (100 / (1 + rs))

# 动量 (Momentum)
momentum = prices.pct_change(periods=20)  # 20日收益率
```

### 波动率指标
```python
# ATR (平均真实波幅) - 需要 high, low, close
tr1 = high - low
tr2 = abs(high - close.shift(1))
tr3 = abs(low - close.shift(1))
tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
atr = tr.rolling(window=14).mean()

# 标准差 (Volatility)
volatility = prices.pct_change().rolling(window=20).std()
```

### 成交量指标
```python
# 成交量移动平均
volume_ma = volumes.rolling(window=20).mean()
volume_ratio = volumes / volume_ma

# OBV (能量潮)
price_change = prices.diff()
obv = (volumes * np.sign(price_change)).cumsum()
```

### 金叉/死叉检测
```python
# 金叉（快线上穿慢线）
golden_cross = (fast_line > slow_line) & (fast_line.shift(1) <= slow_line.shift(1))

# 死叉（快线下穿慢线）
death_cross = (fast_line < slow_line) & (fast_line.shift(1) >= slow_line.shift(1))
```

## 我的策略需求

[在这里详细描述你的策略需求，例如:]

**策略类型**: 趋势跟踪策略

**核心逻辑**:
- 使用 EMA(20, 60, 120) 定义趋势层级
- 使用 MACD(12, 26, 9) 捕捉动能转折
- 买入条件：股价 > EMA120 且 EMA20 > EMA60 且 MACD在零轴上方金叉
- 卖出条件：MACD死叉 或 股价跌破EMA60

**技术指标**:
- EMA（指数移动平均线）
- MACD（指数平滑异同移动平均线）

**参数配置**:
- ema_short: 20 (短期均线周期)
- ema_mid: 60 (中期均线周期)
- ema_long: 120 (长期均线周期)
- macd_fast: 12, macd_slow: 26, macd_signal: 9

**风险控制**:
- 成交量需大于20日均量的80%
- 每期选择前20只股票

## 代码规范要求

### 1. 类命名规范
- 使用大写驼峰命名（PascalCase）
- 例如: `TrendMomentumStrategy`, `RSIReversalStrategy`

### 2. 文档字符串
- 类和每个方法都必须有完整的文档字符串
- 使用Google风格的docstring
- 包含参数说明和返回值说明

### 3. 错误处理和数据验证
- 在循环中使用 try-except 捕获异常
- 数据不足时跳过该股票：`if len(data) < min_length: continue`
- 计算指标后必须验证结果：`if pd.isna(value): continue`
- 避免除零错误：使用 `(value + 1e-9)` 作为分母
- 避免因单只股票错误导致整个策略失败

### 4. 性能优化
- 避免在循环中重复计算
- 使用向量化操作替代循环（如果可能）

## 输出要求

请按照以下格式输出：

### 1. 策略元信息
```
策略标识: trend_momentum_strategy (小写字母、数字和下划线)
显示名称: 趋势+动能双重确认策略
Python类名: TrendMomentumStrategy (大写驼峰)
策略类别: momentum (可选: momentum/reversal/factor/technical/ml)
策略描述: 基于EMA趋势过滤和MACD动能触发的双重确认入场策略
标签: 趋势, 动能, MACD, EMA, 双重确认
```

### 2. 完整Python代码
生成完整的策略代码，包括:
- ✅ 文档字符串（策略说明）
- ✅ 正确继承 BaseStrategy 基类
- ✅ 实现 __init__, calculate_scores, generate_signals 三个方法
- ✅ 包含完整的参数配置
- ✅ 添加错误处理（try-except）
- ✅ 代码注释清晰
- ✅ 符合PEP 8编码规范

## 特别注意

1. **数据结构理解**:
   - prices: DataFrame, index=日期, columns=股票代码, values=收盘价
   - 访问单只股票: `prices[stock_code]`
   - 访问某日所有股票: `prices.loc[date]`

2. **信号值规范**:
   - 1 = 买入信号
   - 0 = 持有/无操作
   - -1 = 卖出信号

3. **配置参数访问（非常重要！）**:
   - ⚠️ 策略自定义参数必须使用 `self.config.custom_params.get('param_name', default_value)`
   - ❌ 错误写法：`self.config.get('bb_window', 20)` （会报错！）
   - ✅ 正确写法：`self.config.custom_params.get('bb_window', 20)`
   - 通用参数可直接访问：`self.config.top_n`, `self.config.holding_period`

4. **信号赋值正确方式（非常重要！）**:
   - 不要直接使用布尔Series作为loc索引
   - 正确步骤：
     ```python
     # 1. 获取满足条件的日期索引
     buy_dates = buy_condition[buy_condition].index

     # 2. 与信号DataFrame的索引求交集
     valid_dates = signals.index.intersection(buy_dates)

     # 3. 赋值
     signals.loc[valid_dates, stock] = 1
     ```
   - ❌ 错误写法：`signals.loc[buy_cond, stock] = 1` （可能索引错误！）
   - ✅ 正确写法：见上方示例

5. **数据验证**:
   - 计算指标后验证：`if pd.isna(indicator): continue`
   - 检查数据长度：`if len(data) < min_length: continue`
   - 避免除零：使用 `(denominator + 1e-9)`

6. **性能考虑**:
   - 单只股票计算失败不应影响其他股票
   - 使用 try-except 包裹每只股票的处理逻辑
   - 优先使用向量化操作

---

**现在请根据以上模板和我的策略需求，生成完整的策略代码和元信息。**
```

---

## 💡 策略描述示例

### ✅ 好的描述（详细清晰）

```
**策略类型**: 趋势跟踪策略

**核心逻辑**:
- 使用EMA(20,60,120)定义趋势，MACD(12,26,9)捕捉动能
- 买入条件：股价>EMA120 且 EMA20>EMA60 且 MACD零轴上方金叉
- 卖出条件：MACD死叉 或 股价跌破EMA60

**技术指标**: EMA, MACD

**参数配置**: ema_short:20, ema_mid:60, ema_long:120

**风险控制**: 成交量>20日均量80%, 每期选20只股票
```

### ❌ 不好的描述（过于简单）

```
使用MACD策略
均线策略
一个赚钱的策略
```

---

## 🎯 推荐AI工具

| AI工具 | 推荐度 | 优势 | 访问方式 |
|--------|--------|------|----------|
| **Claude 3.5 Sonnet** | ⭐⭐⭐⭐⭐ | 代码质量高，理解准确 | claude.ai |
| **ChatGPT-4** | ⭐⭐⭐⭐ | 生成速度快，代码规范 | chat.openai.com |
| **Gemini Pro** | ⭐⭐⭐ | 免费额度高 | gemini.google.com |
| **通义千问** | ⭐⭐⭐ | 中文理解好 | tongyi.aliyun.com |
| **文心一言** | ⭐⭐ | 适合简单策略 | yiyan.baidu.com |

---

## 📝 使用流程图

```
1. 填写策略需求
   ↓
2. 复制完整提示词
   ↓
3. 粘贴到AI对话
   ↓
4. AI生成：元信息 + 代码
   ↓
5. 复制元信息到表单
   - 策略标识
   - 显示名称
   - Python类名
   - 策略类别
   - 策略描述
   - 标签
   ↓
6. 复制代码到编辑器
   ↓
7. 验证代码
   ↓
8. 保存策略
```

---

## 🔧 常见问题

### Q1: AI生成的代码验证失败怎么办？

**A**:
1. 查看具体的错误信息
2. 将错误信息反馈给AI，让它修正
3. 常见错误：
   - 缺少必要方法：确保实现了 `calculate_scores` 和 `generate_signals`
   - 导入路径错误：确保使用 `from core.strategies.base_strategy import BaseStrategy`
   - 类名不匹配：检查类定义中的名字

### Q2: 如何让AI生成更好的代码？

**A**:
1. 提供详细的策略描述
2. 明确技术指标和参数
3. 说明买入/卖出条件
4. 指定风险控制要求

### Q3: 元信息应该填写在哪里？

**A**:
AI会生成类似这样的元信息：
```
策略标识: trend_momentum_strategy
显示名称: 趋势+动能双重确认策略
Python类名: TrendMomentumStrategy
策略类别: momentum
策略描述: 基于EMA趋势过滤和MACD动能触发的双重确认入场策略
标签: 趋势, 动能, MACD, EMA, 双重确认
```

分别填写到策略创建页面的对应字段中。

### Q4: 如何修改已生成的策略？

**A**:
1. 在动态策略列表中找到该策略
2. 点击"编辑"按钮
3. 修改代码
4. 重新验证并保存

---

## ⚡ 快捷技巧

### 技巧1: 使用模板快速开始

在策略需求描述中，直接修改默认模板：
```
**策略类型**: [改为你的策略类型]
**核心逻辑**: [改为你的逻辑]
...
```

### 技巧2: 参考现有策略

查看已成功保存的策略（如"趋势+动能策略"），学习其代码结构。

### 技巧3: 迭代优化

如果第一次生成的代码不理想，可以：
1. 继续对话："请优化评分逻辑，加入成交量因素"
2. 或者："请简化代码，去掉不必要的计算"

---

## 📚 扩展阅读

- **BaseStrategy基类文档**: [core/src/strategies/base_strategy.py](core/src/strategies/base_strategy.py)
- **技术指标库**: [core/src/features/indicators/](core/src/features/indicators/)
- **预定义策略示例**: [core/src/strategies/predefined/](core/src/strategies/predefined/)

---

**提示**: 建议保存此文档为书签，方便随时查阅！
