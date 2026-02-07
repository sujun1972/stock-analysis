# 三层策略架构使用指南

**Three-Layer Strategy Architecture Guide**

**版本**: v3.0.0
**最后更新**: 2026-02-06

---

## 📚 概述

三层策略架构是 Stock-Analysis Core v3.0 的核心创新，将传统的"策略"概念解耦为三个独立层级：

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1: StockSelector (选股器层)                               │
│  职责: 从全市场筛选候选股票池                                      │
│  频率: 周频/月频                                                  │
└─────────────────┬───────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 2: EntryStrategy (入场策略层)                             │
│  职责: 决定何时买入候选股票                                        │
│  频率: 日频                                                       │
└─────────────────┬───────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: ExitStrategy (退出策略层)                              │
│  职责: 管理持仓，决定何时卖出                                      │
│  频率: 日频/实时                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 示例文件

### [three_layer_architecture_example.py](three_layer_architecture_example.py)
**三层架构基类使用示例**

**包含示例**:
- 示例1: 简单的选股器实现 (SimpleTopNSelector)
- 示例2: 简单的入场策略实现 (SimpleImmediateEntry)
- 示例3: 简单的退出策略实现 (SimpleFixedStopLossExit)
- 示例4: 策略组合器使用 (StrategyComposer)
- 示例5: 参数验证演示

**适合人群**: 所有开发者
**学习时间**: 40分钟

---

## 🚀 快速开始

### 运行示例

```bash
cd /Volumes/MacDriver/stock-analysis/core/docs/user_guide/examples
python three_layer_architecture_example.py
```

**预期输出**:
```
======================================================================
三层架构策略组合器演示
======================================================================

1. 策略组合信息
----------------------------------------------------------------------
组合名称: 简单 Top N 选股器_简单立即入场_简单固定止损
组合ID: simple_top_n_simple_immediate_simple_fixed_stop

2. 策略元数据
----------------------------------------------------------------------
选股器: 简单 Top N 选股器 (ID: simple_top_n)
  参数: {'top_n': 20}
入场策略: 简单立即入场 (ID: simple_immediate)
  参数: {'max_positions': 10}
退出策略: 简单固定止损 (ID: simple_fixed_stop)
  参数: {'stop_loss_pct': -5.0}
选股频率: W

3. 验证策略组合
----------------------------------------------------------------------
✅ 策略组合有效
```

---

## 📖 架构详解

### 1. 三层架构核心组件

#### Layer 1: StockSelector (选股器)

**职责**: 从全市场筛选候选股票池

**基类定义**:
```python
from abc import ABC, abstractmethod
from typing import List
import pandas as pd

class StockSelector(ABC):
    """选股器抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """选股器名称"""
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """选股器唯一ID"""
        pass

    @abstractmethod
    def select(self, date: pd.Timestamp, market_data: pd.DataFrame) -> List[str]:
        """
        选股方法

        Args:
            date: 选股日期
            market_data: 市场数据 DataFrame(index=日期, columns=股票代码)

        Returns:
            选中的股票代码列表
        """
        pass
```

**内置选股器**:
| 选股器 | ID | 描述 | 核心参数 |
|--------|-----|------|---------|
| MomentumSelector | momentum | 动量选股 | lookback_period, top_n |
| ReversalSelector | reversal | 反转选股 | lookback_period, top_n |
| **MLSelector** ⭐ | ml | 机器学习选股 | mode, features, top_n |
| ExternalSelector | external | 外部系统集成 | source, config |

---

#### Layer 2: EntryStrategy (入场策略)

**职责**: 决定何时买入候选股票

**基类定义**:
```python
from typing import Dict
import pandas as pd

class EntryStrategy(ABC):
    """入场策略抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """策略唯一ID"""
        pass

    @abstractmethod
    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp
    ) -> Dict[str, float]:
        """
        生成入场信号

        Args:
            stocks: 候选股票列表
            data: 市场数据字典 {'prices': DataFrame, 'volume': DataFrame, ...}
            date: 当前日期

        Returns:
            {股票代码: 买入权重} 字典
        """
        pass
```

**内置入场策略**:
| 策略 | ID | 描述 | 触发条件 |
|------|-----|------|---------|
| ImmediateEntry | immediate | 立即入场 | 选中即买入 |
| MABreakoutEntry | ma_breakout | 均线突破 | 价格突破 MA20 |
| RSIOversoldEntry | rsi_oversold | RSI 超卖 | RSI < 30 |

---

#### Layer 3: ExitStrategy (退出策略)

**职责**: 管理持仓，决定何时卖出

**基类定义**:
```python
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Position:
    """持仓信息"""
    stock_code: str
    entry_price: float
    current_price: float
    quantity: int
    entry_date: pd.Timestamp
    holding_days: int
    unrealized_pnl_pct: float  # 未实现盈亏百分比

class ExitStrategy(ABC):
    """退出策略抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """策略唯一ID"""
        pass

    @abstractmethod
    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp
    ) -> List[str]:
        """
        生成退出信号

        Args:
            positions: 当前持仓字典 {股票代码: Position}
            data: 市场数据字典
            date: 当前日期

        Returns:
            需要卖出的股票代码列表
        """
        pass
```

**内置退出策略**:
| 策略 | ID | 描述 | 触发条件 |
|------|-----|------|---------|
| FixedHoldingPeriodExit | fixed_period | 固定持有期 | 持有 N 天后卖出 |
| FixedStopLossExit | fixed_stop | 固定止损 | 亏损达到 X% |
| ATRStopLossExit | atr_stop | ATR 动态止损 | 亏损超过 N 倍 ATR |
| TrendExitStrategy | trend_exit | 趋势退出 | MA5 下穿 MA20 |

---

### 2. StrategyComposer (策略组合器)

**职责**: 将三层策略组合成完整交易策略

**定义**:
```python
class StrategyComposer:
    """策略组合器"""

    def __init__(
        self,
        selector: StockSelector,
        entry: EntryStrategy,
        exit_strategy: ExitStrategy,
        rebalance_freq: str = 'W'
    ):
        """
        组合三层策略

        Args:
            selector: 选股器实例
            entry: 入场策略实例
            exit_strategy: 退出策略实例
            rebalance_freq: 调仓频率 ('D'日/'W'周/'M'月)
        """
        self.selector = selector
        self.entry = entry
        self.exit = exit_strategy
        self.rebalance_freq = rebalance_freq

    def get_strategy_combination_name(self) -> str:
        """获取策略组合名称"""
        return f"{self.selector.name}_{self.entry.name}_{self.exit.name}"

    def get_strategy_combination_id(self) -> str:
        """获取策略组合ID"""
        return f"{self.selector.id}_{self.entry.id}_{self.exit.id}"

    def validate(self) -> Dict[str, Any]:
        """验证策略组合有效性"""
        errors = []

        if self.selector is None:
            errors.append("选股器不能为空")
        if self.entry is None:
            errors.append("入场策略不能为空")
        if self.exit is None:
            errors.append("退出策略不能为空")

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
```

---

## 🎯 实战示例

### 示例 1: 创建自定义选股器

```python
from src.strategies.three_layer import StockSelector, SelectorParameter
from typing import List
import pandas as pd

class SimpleTopNSelector(StockSelector):
    """简单的 Top N 选股器 - 选择收盘价最高的 N 只股票"""

    @property
    def name(self) -> str:
        return "简单 Top N 选股器"

    @property
    def id(self) -> str:
        return "simple_top_n"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="top_n",
                label="选股数量",
                type="integer",
                default=10,
                min_value=1,
                max_value=100,
                description="选择前 N 只股票"
            )
        ]

    def select(self, date: pd.Timestamp, market_data: pd.DataFrame) -> List[str]:
        """选择当日收盘价最高的前 N 只股票"""
        top_n = self.params.get("top_n", 10)

        try:
            current_prices = market_data.loc[date].dropna()
            selected = current_prices.nlargest(top_n).index.tolist()
            return selected
        except KeyError:
            return []
```

---

### 示例 2: 创建自定义入场策略

```python
from src.strategies.three_layer import EntryStrategy
from typing import Dict, List
import pandas as pd

class SimpleImmediateEntry(EntryStrategy):
    """简单的立即入场策略 - 对所有候选股票等权买入"""

    @property
    def name(self) -> str:
        return "简单立即入场"

    @property
    def id(self) -> str:
        return "simple_immediate"

    @classmethod
    def get_parameters(cls) -> List[Dict]:
        return [
            {
                "name": "max_positions",
                "label": "最大持仓数",
                "type": "integer",
                "default": 5,
                "min": 1,
                "max": 50,
                "description": "最多同时持有的股票数量"
            }
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp
    ) -> Dict[str, float]:
        """对所有候选股票生成等权买入信号"""
        max_positions = self.params.get("max_positions", 5)

        # 限制持仓数量
        selected_stocks = stocks[:max_positions]

        if selected_stocks:
            weight = 1.0 / len(selected_stocks)
            return {stock: weight for stock in selected_stocks}
        else:
            return {}
```

---

### 示例 3: 创建自定义退出策略

```python
from src.strategies.three_layer import ExitStrategy, Position
from typing import Dict, List
import pandas as pd

class SimpleFixedStopLossExit(ExitStrategy):
    """简单的固定止损退出策略"""

    @property
    def name(self) -> str:
        return "简单固定止损"

    @property
    def id(self) -> str:
        return "simple_fixed_stop"

    @classmethod
    def get_parameters(cls) -> List[Dict]:
        return [
            {
                "name": "stop_loss_pct",
                "label": "止损百分比",
                "type": "float",
                "default": -5.0,
                "min": -20.0,
                "max": -1.0,
                "description": "亏损达到此百分比时卖出"
            }
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp
    ) -> List[str]:
        """检查止损条件"""
        exit_stocks = []
        stop_loss_pct = self.params.get("stop_loss_pct", -5.0)

        for stock, position in positions.items():
            if position.unrealized_pnl_pct <= stop_loss_pct:
                exit_stocks.append(stock)

        return exit_stocks
```

---

### 示例 4: 组合策略并验证

```python
from src.strategies.three_layer import StrategyComposer

# 创建三层策略实例
selector = SimpleTopNSelector(params={'top_n': 20})
entry = SimpleImmediateEntry(params={'max_positions': 10})
exit_strategy = SimpleFixedStopLossExit(params={'stop_loss_pct': -5.0})

# 组合策略
composer = StrategyComposer(
    selector=selector,
    entry=entry,
    exit_strategy=exit_strategy,
    rebalance_freq='W'  # 周度调仓
)

# 获取策略信息
print(f"策略名称: {composer.get_strategy_combination_name()}")
print(f"策略ID: {composer.get_strategy_combination_id()}")

# 验证策略组合
validation = composer.validate()
if validation['valid']:
    print("✅ 策略组合有效")
else:
    print("❌ 策略组合无效:")
    for error in validation['errors']:
        print(f"  - {error}")

# 获取所有参数
all_params = composer.get_all_parameters()
print(f"所有参数: {all_params}")

# 获取元数据
metadata = composer.get_metadata()
print(f"选股器: {metadata['selector']['name']}")
print(f"入场策略: {metadata['entry']['name']}")
print(f"退出策略: {metadata['exit']['name']}")
print(f"调仓频率: {metadata['rebalance_freq']}")
```

---

## 🎨 策略组合示例

### 组合 1: 动量选股 + 立即入场 + 固定止损

```python
from src.strategies.three_layer import (
    MomentumSelector,
    ImmediateEntry,
    FixedStopLossExit,
    StrategyComposer
)

composer = StrategyComposer(
    selector=MomentumSelector(params={
        'lookback_period': 20,
        'top_n': 50
    }),
    entry=ImmediateEntry(),
    exit_strategy=FixedStopLossExit(params={
        'stop_loss_pct': -5.0
    }),
    rebalance_freq='W'
)
```

**适用场景**: 趋势市场、牛市
**策略特点**: 快速捕捉强势股，及时止损

---

### 组合 2: ML 选股 + MA 突破 + ATR 止损

```python
from src.strategies.three_layer import (
    MLSelector,
    MABreakoutEntry,
    ATRStopLossExit,
    StrategyComposer
)

composer = StrategyComposer(
    selector=MLSelector(params={
        'mode': 'lightgbm_ranker',
        'model_path': './models/stock_ranker.pkl',
        'top_n': 50
    }),
    entry=MABreakoutEntry(params={
        'ma_window': 20
    }),
    exit_strategy=ATRStopLossExit(params={
        'atr_multiplier': 2.0,
        'atr_period': 14
    }),
    rebalance_freq='M'
)
```

**适用场景**: 所有市场
**策略特点**: 机器学习选股 + 技术指标入场 + 动态止损

---

### 组合 3: 反转选股 + RSI 超卖 + 趋势退出

```python
from src.strategies.three_layer import (
    ReversalSelector,
    RSIOversoldEntry,
    TrendExitStrategy,
    StrategyComposer
)

composer = StrategyComposer(
    selector=ReversalSelector(params={
        'lookback_period': 10,
        'top_n': 30
    }),
    entry=RSIOversoldEntry(params={
        'rsi_period': 14,
        'oversold_threshold': 30
    }),
    exit_strategy=TrendExitStrategy(params={
        'fast_ma': 5,
        'slow_ma': 20
    }),
    rebalance_freq='W'
)
```

**适用场景**: 震荡市场、熊市
**策略特点**: 捕捉反转机会，超卖入场，趋势反转退出

---

## 📊 策略组合统计

### 可用组合数量

根据当前实现的组件：
- **选股器**: 4 种（Momentum, Reversal, ML, External）
- **入场策略**: 3 种（Immediate, MABreakout, RSIOversold）
- **退出策略**: 4 种（FixedPeriod, FixedStopLoss, ATRStop, TrendExit）

**总计**: 4 × 3 × 4 = **48 种基础组合**

### 组合矩阵

| 选股器 ↓ / 入场策略 → | Immediate | MABreakout | RSIOversold |
|---------------------|-----------|------------|-------------|
| **Momentum** | 快速动量 | 突破动量 | 超卖动量 |
| **Reversal** | 快速反转 | 突破反转 | 超卖反转⭐ |
| **ML (Multi-Factor)** | 快速ML | 突破ML⭐ | 超卖ML |
| **ML (LightGBM)** | 快速智能⭐ | 突破智能 | 超卖智能 |

⭐ 表示推荐组合

---

## 🔧 参数验证

### 参数定义

**SelectorParameter 结构**:
```python
@dataclass
class SelectorParameter:
    name: str              # 参数名称
    label: str             # 参数标签（UI 显示）
    type: str              # 参数类型（integer/float/string/boolean）
    default: Any           # 默认值
    min_value: Optional[float]  # 最小值（数值类型）
    max_value: Optional[float]  # 最大值（数值类型）
    description: str       # 参数描述
```

### 参数验证示例

```python
# 1. 正确的参数
selector = SimpleTopNSelector(params={'top_n': 50})
# ✅ 创建成功

# 2. 参数超出范围
try:
    selector = SimpleTopNSelector(params={'top_n': 500})  # 超过最大值100
except ValueError as e:
    print(f"❌ 创建失败: {e}")
    # 输出: top_n 超出范围 [1, 100]

# 3. 未知参数
try:
    selector = SimpleTopNSelector(params={'unknown_param': 123})
except ValueError as e:
    print(f"❌ 创建失败: {e}")
    # 输出: 未知参数: unknown_param

# 4. 错误的参数类型
try:
    selector = SimpleTopNSelector(params={'top_n': "50"})  # 应该是整数
except ValueError as e:
    print(f"❌ 创建失败: {e}")
    # 输出: top_n 类型错误，期望 integer，实际 string
```

---

## 🚀 性能优化

### 1. 选股频率优化

| 调仓频率 | 交易次数 | 交易成本 | 适用场景 |
|---------|---------|---------|---------|
| 日频 (D) | 高 | 高 | 短线交易 |
| 周频 (W) | 中⭐ | 中⭐ | 中线交易⭐ |
| 月频 (M) | 低 | 低 | 长线交易 |

**推荐**: 周频调仓（`rebalance_freq='W'`）

---

### 2. 组件复用

```python
# ✅ 好的实践：复用组件
selector = MLSelector(params={'mode': 'multi_factor_weighted', 'top_n': 50})

# 组合1: 立即入场 + 固定止损
composer1 = StrategyComposer(
    selector=selector,
    entry=ImmediateEntry(),
    exit_strategy=FixedStopLossExit(params={'stop_loss_pct': -5.0})
)

# 组合2: 立即入场 + ATR 止损（复用选股器）
composer2 = StrategyComposer(
    selector=selector,
    entry=ImmediateEntry(),
    exit_strategy=ATRStopLossExit(params={'atr_multiplier': 2.0})
)
```

---

### 3. 批量回测优化

```python
from src.backtest import BacktestEngine

engine = BacktestEngine()

# 批量测试多个策略组合
strategies = [composer1, composer2, composer3]

results = []
for composer in strategies:
    result = engine.backtest_three_layer(
        selector=composer.selector,
        entry=composer.entry,
        exit_strategy=composer.exit,
        prices=prices,
        start_date='2023-01-01',
        end_date='2023-12-31'
    )
    results.append({
        'strategy': composer.get_strategy_combination_name(),
        'result': result
    })

# 对比结果
for item in results:
    print(f"{item['strategy']}: 年化收益 {item['result']['annual_return']:.2%}")
```

---

## ❓ 常见问题

### Q1: 三层架构相比传统策略有什么优势？

**A**:
1. **高度解耦**: 选股、入场、退出逻辑独立开发和测试
2. **灵活组合**: 4 × 3 × 4 = 48+ 种基础组合
3. **易于扩展**: 新增策略只需实现对应层的接口
4. **频率独立**: 选股周频，入场/退出日频，互不干扰
5. **向后兼容**: 保留原有 BaseStrategy 接口

---

### Q2: 如何选择合适的策略组合？

**A**:

**趋势市场/牛市**:
- 选股器: MomentumSelector
- 入场策略: ImmediateEntry
- 退出策略: FixedStopLossExit

**震荡市场**:
- 选股器: ReversalSelector
- 入场策略: RSIOversoldEntry
- 退出策略: TrendExitStrategy

**所有市场（稳定）**:
- 选股器: MLSelector (LightGBM)
- 入场策略: MABreakoutEntry
- 退出策略: ATRStopLossExit

---

### Q3: 参数验证失败怎么办？

**A**:
1. 检查参数名称是否正确
2. 检查参数类型是否匹配
3. 检查参数值是否在允许范围内
4. 查看 `get_parameters()` 方法获取参数定义

---

### Q4: 如何回测三层策略？

**A**:
```python
from src.backtest import BacktestEngine

# 创建策略组合
composer = StrategyComposer(selector, entry, exit_strategy, rebalance_freq='W')

# 执行回测
engine = BacktestEngine()
result = engine.backtest_three_layer(
    selector=composer.selector,
    entry=composer.entry,
    exit_strategy=composer.exit,
    prices=prices,
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# 查看结果
print(f"年化收益: {result['annual_return']:.2%}")
print(f"最大回撤: {result['max_drawdown']:.2%}")
print(f"夏普比率: {result['sharpe_ratio']:.2f}")
```

---

### Q5: 如何扩展自己的策略组件？

**A**:

**步骤 1**: 继承对应基类
```python
class MyCustomSelector(StockSelector):
    # 实现 name, id, select() 方法
    pass
```

**步骤 2**: 实现必需方法
```python
@property
def name(self) -> str:
    return "我的自定义选股器"

@property
def id(self) -> str:
    return "my_custom"

def select(self, date, market_data):
    # 实现选股逻辑
    return selected_stocks
```

**步骤 3**: 添加参数定义
```python
@classmethod
def get_parameters(cls):
    return [
        SelectorParameter(
            name="my_param",
            label="我的参数",
            type="integer",
            default=10,
            min_value=1,
            max_value=100
        )
    ]
```

**步骤 4**: 使用自定义策略
```python
my_selector = MyCustomSelector(params={'my_param': 20})
composer = StrategyComposer(my_selector, entry, exit_strategy)
```

---

## 📚 相关文档

- 📖 [MLSelector 使用指南](ML_SELECTOR_GUIDE.md)
- 🏗️ [架构总览](../../architecture/overview.md)
- 🎨 [设计模式详解](../../architecture/design_patterns.md)
- ⚡ [性能优化分析](../../architecture/performance.md)

---

## 🎓 学习路径

### 第1天: 理解架构（1小时）
1. 阅读架构概述
2. 理解三层职责划分
3. 运行示例代码

### 第2天: 实践基础组件（2小时）
4. 创建自定义选股器
5. 创建自定义入场策略
6. 创建自定义退出策略

### 第3天: 策略组合（2小时）
7. 使用 StrategyComposer 组合策略
8. 验证策略组合
9. 测试不同参数配置

### 第4天: 回测验证（3小时）
10. 执行单策略回测
11. 对比多个策略组合
12. 分析回测结果

### 第5天: 高级应用（3小时）
13. 集成 MLSelector
14. 使用 LightGBM 排序模型
15. 优化策略参数

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-06
**核心功能**: 三层架构 (Selector → Entry → Exit) + 策略组合器 + 48+ 种组合
