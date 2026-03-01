# AI策略生成 - 5分钟快速上手

## 🚀 最快路径（3步骤）

### 步骤1: 打开页面
访问: `http://localhost:3000/strategies/create?source=custom`

### 步骤2: 填写需求 + 复制提示词
在"AI策略生成助手"卡片中：
1. 修改策略需求描述（默认已有示例）
2. 点击"复制提示词"

### 步骤3: 获取代码 + 保存
1. 打开 [Claude](https://claude.ai) 或 [ChatGPT](https://chat.openai.com)
2. 粘贴提示词
3. 复制AI返回的**元信息**和**代码**
4. 填写到页面并保存

---

## 📋 AI输出格式示例

AI会返回两部分内容：

### 1️⃣ 策略元信息（复制到表单）

```
策略标识: trend_momentum_strategy
显示名称: 趋势+动能双重确认策略
Python类名: TrendMomentumStrategy
策略类别: momentum
策略描述: 基于EMA趋势过滤和MACD动能触发的双重确认入场策略
标签: 趋势, 动能, MACD, EMA, 双重确认
```

### 2️⃣ Python代码（复制到代码编辑器）

```python
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from core.strategies.base_strategy import BaseStrategy

class TrendMomentumStrategy(BaseStrategy):
    """趋势+动能双重确认组合策略"""

    def __init__(self, name: str = "trend_momentum_strategy", config: Dict[str, Any] = None):
        # ... 初始化代码

    def calculate_scores(self, prices, features=None, date=None):
        # ... 评分逻辑

    def generate_signals(self, prices, features=None, **kwargs):
        # ... 信号生成
```

---

## ✏️ 策略需求描述模板

直接复制修改：

```
**策略类型**: [趋势跟踪/均值回归/动量/多因子]

**核心逻辑**:
- 使用 [技术指标1] 做 [功能1]
- 使用 [技术指标2] 做 [功能2]
- 买入条件：[条件A] 且 [条件B] 且 [条件C]
- 卖出条件：[条件X] 或 [条件Y]

**技术指标**: [EMA/MACD/RSI/布林带/...]

**参数配置**:
- 参数1: 默认值 (说明)
- 参数2: 默认值 (说明)

**风险控制**:
- 成交量要求
- 持仓数量
- 其他限制
```

---

## 💡 示例：3个常见策略

### 示例1: RSI超卖反弹

```
**策略类型**: 均值回归策略

**核心逻辑**:
- 使用 RSI(14) 判断超卖
- 使用 布林带(20,2) 判断价格位置
- 买入条件：RSI < 30 且 价格触及下轨 且 成交量 > 5日均量2倍
- 卖出条件：RSI > 70 或 价格触及上轨

**技术指标**: RSI, 布林带, 成交量

**参数配置**:
- rsi_period: 14
- bb_period: 20, bb_std: 2
- volume_ratio: 2.0

**风险控制**: 每期选15只股票
```

### 示例2: 双均线金叉

```
**策略类型**: 趋势跟踪策略

**核心逻辑**:
- 使用 EMA(5, 20) 构建快慢均线系统
- 买入条件：EMA5上穿EMA20（金叉）且 成交量放大
- 卖出条件：EMA5下穿EMA20（死叉）

**技术指标**: EMA, 成交量

**参数配置**:
- ema_fast: 5
- ema_slow: 20
- volume_threshold: 1.5倍

**风险控制**: 每期选30只股票
```

### 示例3: MACD+成交量确认

```
**策略类型**: 动量策略

**核心逻辑**:
- 使用 MACD(12,26,9) 判断动能
- 使用 成交量 确认有效性
- 买入条件：MACD零轴上方金叉 且 成交量 > 20日均量1.5倍
- 卖出条件：MACD死叉

**技术指标**: MACD, 成交量

**参数配置**:
- macd_fast: 12, macd_slow: 26, macd_signal: 9
- volume_ratio: 1.5

**风险控制**: 每期选20只股票，要求MACD在零轴上方
```

---

## ⚠️ 常见错误 & 解决

| 错误 | 原因 | 解决方法 |
|------|------|----------|
| 验证失败：缺少方法 | AI没有生成完整代码 | 在提示词中强调"必须实现calculate_scores和generate_signals" |
| 验证失败：导入错误 | 导入路径不对 | 确保使用`from core.strategies.base_strategy import BaseStrategy` |
| 验证失败：类名不匹配 | 类名和填写的不一致 | 检查代码中的`class XXXStrategy` |
| 代码运行错误 | 逻辑错误 | 将错误信息反馈给AI，让它修正 |

---

## 🎯 推荐AI工具

1. **Claude 3.5 Sonnet** ⭐⭐⭐⭐⭐ - 首选，代码质量最高
2. **ChatGPT-4** ⭐⭐⭐⭐ - 速度快，效果好
3. **其他** - Gemini Pro、通义千问等

---

## 📞 需要帮助？

- 查看详细文档: [AI_STRATEGY_PROMPT.md](AI_STRATEGY_PROMPT.md)
- 查看完整示例: [trend_momentum_strategy_code.py](trend_momentum_strategy_code.py)
- 技术指标参考: [core/src/features/indicators/](core/src/features/indicators/)

---

**开始创建你的第一个AI生成策略吧！** 🚀
