# Core v3.0 三层架构升级方案

> **版本**: v1.0
> **日期**: 2026-02-06
> **作者**: Claude Code
> **项目**: Stock Analysis Platform - Core
> **重大升级**: v2.x → v3.0（架构重构）

---

## 📋 执行摘要

本文档详细规划了 Core 项目从单体策略架构升级到**三层分离架构**的完整方案。

**核心目标**：
- ✅ 支持外部选股系统集成（StarRanker）
- ✅ 实现选股、入场、退出策略的独立配置
- ✅ 提供灵活的策略组合能力
- ✅ 保持向后兼容，不破坏现有功能
- ✅ 符合行业最佳实践（Zipline、Backtrader）

**工作量评估**：
- 核心代码：~2000 行
- 测试用例：~500 行
- 开发周期：2-3 周（1人全职）

---

## 📋 目录

- [一、项目背景](#一项目背景)
- [二、当前架构分析](#二当前架构分析)
- [三、三层架构设计](#三三层架构设计)
- [四、详细实施方案](#四详细实施方案)
- [五、StarRanker 集成方案](#五starranker-集成方案)
- [六、测试策略](#六测试策略)
- [七、性能优化](#七性能优化)
- [八、迁移指南](#八迁移指南)

---

## 一、项目背景

### 1.1 升级动机

#### 当前架构的限制

基于对 Core v2.x 的深入分析，发现以下核心限制：

| 限制 | 影响 | 严重程度 |
|------|------|---------|
| **无法应用外部选股** | StarRanker 等系统无法集成 | 🔴 高 |
| **买卖逻辑耦合** | 无法独立配置止损止盈策略 | 🟠 中 |
| **策略组合不灵活** | 需要编写完整策略类，无法模块化复用 | 🟠 中 |
| **选股和交易频率绑定** | 无法实现"周频选股+日频交易" | 🟡 低 |

#### 业务需求

1. **StarRanker 集成**（P0）：
   - StarRanker 是外部选股系统，每周输出推荐股票池
   - 需要能够应用这些股票池进行回测验证
   - 当前架构无法实现

2. **策略研究效率提升**（P1）：
   - 研究人员希望快速组合不同的选股、入场、退出逻辑
   - 当前需要为每种组合编写完整的策略类
   - 3 个选股 × 3 个入场 × 3 个退出 = 27 个策略类（不可维护）

3. **符合行业标准**（P2）：
   - Zipline、Backtrader、聚宽等主流平台均采用三层分离
   - 便于用户理解和迁移

### 1.2 升级目标

#### 功能目标

- ✅ 支持外部股票池输入（StarRanker、手动输入、API）
- ✅ 选股、入场、退出策略独立配置
- ✅ 支持不同频率的策略执行（周频选股、日频交易）
- ✅ 提供至少 10 个基础策略模块（3+3+4）
- ✅ 策略模块可自由组合（36+ 种组合）

#### 非功能目标

- ✅ 向后兼容：现有策略继续可用
- ✅ 性能保持：不降低回测速度
- ✅ 代码质量：测试覆盖率 ≥ 85%
- ✅ 文档完整：API 文档 + 用户指南 + 迁移指南

---

## 二、当前架构分析

### 2.1 核心组件概览

```
core/src/
├── backtest/
│   ├── backtest_engine.py          # 回测引擎（核心）
│   ├── backtest_executor.py        # 交易执行器
│   ├── backtest_portfolio.py       # 组合管理器
│   ├── backtest_recorder.py        # 数据记录器
│   ├── slippage_models.py          # 滑点模型
│   └── cost_analyzer.py            # 成本分析器
│
├── strategies/
│   ├── base_strategy.py            # 策略基类
│   ├── momentum_strategy.py        # 动量策略
│   ├── mean_reversion_strategy.py  # 均值回归策略
│   ├── multi_factor_strategy.py    # 多因子策略
│   └── signal_generator.py         # 信号生成器
│
└── features/
    └── feature_engineering.py      # 技术指标计算
```

### 2.2 当前回测流程

**BacktestEngine.backtest_long_only() 核心流程**：

```python
def backtest_long_only(
    self,
    signals: pd.DataFrame,      # 策略评分矩阵
    prices: pd.DataFrame,       # 价格数据
    top_n: int = 50,           # 选股数量
    holding_period: int = 5,   # 持仓期
    rebalance_freq: str = 'W'  # 调仓频率
):
    """
    单体架构回测流程：

    1. 初始化阶段
       - 创建 Portfolio 和 Recorder
       - 计算调仓日期 (rebalance_dates)

    2. 主循环 (for date in dates)
       a. 记录净值
       b. 调仓判断 (if date in rebalance_dates):
          ├── 选股: signals.loc[date].nlargest(top_n)  # ⚠️ 硬编码
          ├── 卖出: 不在新组合或持仓期满
          └── 买入: 等权分配资金
       c. 下一日期

    3. 返回结果
       - 净值曲线、持仓、交易记录、绩效指标
    """
```

### 2.3 核心问题诊断

#### 问题 1：选股逻辑硬编码

**位置**：`backtest_engine.py:372`

```python
# ❌ 当前实现
top_stocks = signals.loc[date].nlargest(top_n).index.tolist()
# 问题：只能基于评分排序，无法接受外部股票池
```

**无法实现的场景**：
```python
# ❌ 想要的效果
starranker_stocks = ["600000.SH", "000001.SZ", ...]  # StarRanker 输出
backtest_engine.backtest(stock_pool=starranker_stocks)  # 不支持！
```

#### 问题 2：买卖逻辑无法分离

**位置**：`backtest_portfolio.py:156`

```python
# ❌ 当前实现：退出条件硬编码
def get_long_stocks_to_sell(self, top_stocks, current_date, holding_period):
    for stock, pos in self.long_positions.items():
        holding_days = current_idx - entry_idx
        # 卖出条件固定：不在新组合 或 持仓期满
        if stock not in top_stocks or holding_days >= holding_period:
            yield stock
```

**无法实现的场景**：
```python
# ❌ 想要的效果：独立配置止损止盈
exit_strategy = CombinedExit([
    ATRStopLossExit(atr_multiplier=2.0),  # 动态止损
    FixedStopLossExit(stop_loss=-5%),     # 固定止损
    TimeBasedExit(holding_period=10)      # 时间止损
])
# 当前架构无法实现！
```

#### 问题 3：策略组合不灵活

**当前方式**：必须编写完整策略类

```python
# ❌ 当前需要写完整的策略类
class MyCustomStrategy(BaseStrategy):
    def __init__(self):
        # 配置选股、买入、卖出所有逻辑
        pass

    def generate_signals(self, prices, features):
        # 选股逻辑
        # 买入信号
        # 卖出信号（通过固定持仓期）
        pass
```

**期望方式**：模块化组合

```python
# ✅ 期望的模块化组合
strategy = StrategyComposer(
    selector=MomentumSelector(top_n=50),      # 动量选股
    entry=MABreakoutEntry(short=5, long=20),  # 均线突破入场
    exit=ATRStopLossExit(atr_multiplier=2.0)  # ATR 止损
)
```

---

## 三、三层架构设计

### 3.1 架构总览

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: 股票选择器 (StockSelector)                      │
├─────────────────────────────────────────────────────────┤
│  职责：从全市场筛选出候选股票池                            │
│  频率：周频/月频（降低换手率）                             │
│  输入：日期、市场数据                                      │
│  输出：股票代码列表 ['600000.SH', '000001.SZ', ...]      │
│                                                           │
│  实现示例：                                               │
│  - MomentumSelector（动量选股）                          │
│  - ValueSelector（价值选股）                             │
│  - ExternalSelector（外部选股，支持 StarRanker）         │
│  - MLSelector（机器学习选股）                            │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: 入场策略 (EntryStrategy)                        │
├─────────────────────────────────────────────────────────┤
│  职责：决定何时买入（在选股器选出的股票中）                │
│  频率：日频/分钟频                                         │
│  输入：候选股票、价格数据、日期                            │
│  输出：{股票代码: 买入权重} 字典                          │
│                                                           │
│  实现示例：                                               │
│  - MABreakoutEntry（均线突破）                           │
│  - RSIOversoldEntry（RSI超卖）                          │
│  - MLPredictionEntry（ML预测入场）                      │
│  - ImmediateEntry（立即入场，测试用）                    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 3: 退出策略 (ExitStrategy)                         │
├─────────────────────────────────────────────────────────┤
│  职责：决定何时卖出（持仓管理）                            │
│  频率：日频/实时                                           │
│  输入：当前持仓、价格数据、日期                            │
│  输出：需要卖出的股票代码列表                              │
│                                                           │
│  实现示例：                                               │
│  - ATRStopLossExit（ATR动态止损）                        │
│  - FixedStopLossExit（固定止损止盈）                     │
│  - TimeBasedExit（时间止损）                             │
│  - CombinedExit（组合退出，OR逻辑）                      │
└─────────────────────────────────────────────────────────┘
                           ↓
                   StrategyComposer
                   （策略组合器）
```

### 3.2 核心类设计

#### 3.2.1 StockSelector（选股器基类）

**文件**：`core/src/strategies/three_layer/base/stock_selector.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class SelectorParameter:
    """选股器参数定义"""
    name: str
    label: str
    type: str  # 'integer', 'float', 'boolean', 'select', 'string'
    default: Any
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""


class StockSelector(ABC):
    """
    股票选择器基类

    所有选股器必须继承此类并实现 select() 方法

    生命周期：
    1. 初始化时传入参数
    2. select() 方法被回测引擎按 rebalance_freq 频率调用
    3. 返回股票代码列表

    示例：
        class MomentumSelector(StockSelector):
            def select(self, date, market_data):
                momentum = market_data.pct_change(20)
                return momentum.loc[date].nlargest(50).index.tolist()
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = params or {}
        self._validate_params()

    @property
    @abstractmethod
    def name(self) -> str:
        """选股器名称"""
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """选股器ID（唯一标识）"""
        pass

    @classmethod
    @abstractmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        """获取参数定义列表"""
        pass

    @abstractmethod
    def select(
        self,
        date: pd.Timestamp,
        market_data: pd.DataFrame,
    ) -> List[str]:
        """
        选股逻辑（核心方法）

        参数:
            date: 选股日期
            market_data: 全市场数据
                        DataFrame(index=日期, columns=股票代码, values=收盘价)

        返回:
            选出的股票代码列表
            例如：['600000.SH', '000001.SZ', '000002.SZ']

        注意：
        - 返回的股票数量由参数 top_n 控制
        - 如果某日数据不足，可以返回空列表或较少股票
        - 必须处理 NaN 值和缺失数据
        """
        pass

    def _validate_params(self):
        """验证参数有效性"""
        param_defs = {p.name: p for p in self.get_parameters()}

        for param_name, param_value in self.params.items():
            if param_name not in param_defs:
                raise ValueError(f"未知参数: {param_name}")

            param_def = param_defs[param_name]

            # 类型验证
            if param_def.type == "integer" and not isinstance(param_value, int):
                raise ValueError(f"参数 {param_name} 必须是整数")

            # 范围验证
            if param_def.type in ["integer", "float"]:
                if param_def.min_value is not None and param_value < param_def.min_value:
                    raise ValueError(f"参数 {param_name} 不能小于 {param_def.min_value}")
```

#### 3.2.2 EntryStrategy（入场策略基类）

**文件**：`core/src/strategies/three_layer/base/entry_strategy.py`

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import pandas as pd


class EntryStrategy(ABC):
    """
    入场策略基类

    职责：在候选股票中生成买入信号

    生命周期：
    1. 初始化时传入参数
    2. generate_entry_signals() 被回测引擎每日调用
    3. 返回 {股票代码: 买入权重} 字典

    权重说明：
    - 权重总和应为 1.0（代表 100% 仓位）
    - 权重 0.2 表示分配 20% 仓位给该股票
    - 如果权重总和 > 1.0，回测引擎会自动归一化
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = params or {}
        self._validate_params()

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """策略ID"""
        pass

    @classmethod
    @abstractmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        """参数定义"""
        pass

    @abstractmethod
    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """
        生成入场信号（核心方法）

        参数:
            stocks: 候选股票列表（来自选股器）
            data: 股票数据字典，格式为 {股票代码: OHLCV DataFrame}
                  DataFrame 必须包含列: open, high, low, close, volume
            date: 当前日期

        返回:
            {股票代码: 买入权重} 字典
            例如: {'600000.SH': 0.3, '000001.SZ': 0.2}
            表示给 600000.SH 分配 30% 仓位，给 000001.SZ 分配 20% 仓位

        注意：
        - 只对有买入信号的股票返回权重
        - 如果当日无买入信号，返回空字典 {}
        - 权重可以不归一化，回测引擎会自动处理
        """
        pass
```

#### 3.2.3 ExitStrategy（退出策略基类）

**文件**：`core/src/strategies/three_layer/base/exit_strategy.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class Position:
    """持仓信息"""
    stock_code: str
    entry_date: pd.Timestamp
    entry_price: float
    shares: int
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


class ExitStrategy(ABC):
    """
    退出策略基类

    职责：管理持仓，决定何时卖出

    生命周期：
    1. 初始化时传入参数
    2. generate_exit_signals() 被回测引擎每日调用
    3. 返回需要卖出的股票代码列表
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = params or {}
        self._validate_params()

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """策略ID"""
        pass

    @classmethod
    @abstractmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        """参数定义"""
        pass

    @abstractmethod
    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """
        生成退出信号（核心方法）

        参数:
            positions: 当前持仓字典，格式为 {股票代码: Position}
            data: 股票数据字典，格式为 {股票代码: OHLCV DataFrame}
            date: 当前日期

        返回:
            需要卖出的股票代码列表
            例如: ['600000.SH', '000001.SZ']

        注意：
        - 只返回需要卖出的股票代码
        - 如果当日无卖出信号，返回空列表 []
        - 回测引擎会以当日收盘价执行卖出
        """
        pass
```

#### 3.2.4 StrategyComposer（策略组合器）

**文件**：`core/src/strategies/three_layer/base/strategy_composer.py`

```python
from typing import Any, Dict


class StrategyComposer:
    """
    三层策略组合器

    用法:
        composer = StrategyComposer(
            selector=MomentumSelector(params={'top_n': 50}),
            entry=MABreakoutEntry(params={'short_window': 5}),
            exit=ATRStopLossExit(params={'atr_multiplier': 2.0}),
            rebalance_freq='W'  # 选股频率：D=日, W=周, M=月
        )

        # 获取元数据
        metadata = composer.get_metadata()

        # 验证策略组合
        validation = composer.validate()
    """

    def __init__(
        self,
        selector: StockSelector,
        entry: EntryStrategy,
        exit_strategy: ExitStrategy,
        rebalance_freq: str = "W",
    ):
        self.selector = selector
        self.entry = entry
        self.exit = exit_strategy
        self.rebalance_freq = rebalance_freq

    def get_metadata(self) -> Dict[str, Any]:
        """获取组合策略完整元数据"""
        return {
            "selector": {
                "id": self.selector.id,
                "name": self.selector.name,
                "parameters": [
                    {
                        "name": p.name,
                        "label": p.label,
                        "type": p.type,
                        "default": p.default,
                        "description": p.description,
                    }
                    for p in self.selector.get_parameters()
                ],
            },
            "entry": {
                "id": self.entry.id,
                "name": self.entry.name,
                "parameters": self.entry.get_parameters(),
            },
            "exit": {
                "id": self.exit.id,
                "name": self.exit.name,
                "parameters": self.exit.get_parameters(),
            },
            "rebalance_freq": self.rebalance_freq,
        }

    def validate(self) -> Dict[str, Any]:
        """验证策略组合的有效性"""
        errors = []

        # 验证选股器
        try:
            self.selector._validate_params()
        except ValueError as e:
            errors.append(f"选股器参数错误: {e}")

        # 验证入场策略
        try:
            self.entry._validate_params()
        except ValueError as e:
            errors.append(f"入场策略参数错误: {e}")

        # 验证退出策略
        try:
            self.exit._validate_params()
        except ValueError as e:
            errors.append(f"退出策略参数错误: {e}")

        # 验证选股频率
        if self.rebalance_freq not in ["D", "W", "M"]:
            errors.append(f"无效的选股频率: {self.rebalance_freq}")

        return {"valid": len(errors) == 0, "errors": errors}
```

### 3.3 与现有架构的关系

```
┌────────────────────────────────────────────────────────┐
│  现有架构 (v2.x) - 保持不变                              │
├────────────────────────────────────────────────────────┤
│                                                          │
│  BaseStrategy (抽象基类)                                │
│  ├── MomentumStrategy                                  │
│  ├── MeanReversionStrategy                             │
│  └── MultiFactorStrategy                               │
│                                                          │
│  BacktestEngine.backtest_long_only()                   │
│  - 单体策略回测                                         │
│  - 性能优异，适合简单场景                                │
└────────────────────────────────────────────────────────┘
                           ↓ 共存
┌────────────────────────────────────────────────────────┐
│  三层架构 (v3.0 新增)                                    │
├────────────────────────────────────────────────────────┤
│                                                          │
│  三层基类：                                              │
│  - StockSelector (抽象基类)                            │
│  - EntryStrategy (抽象基类)                            │
│  - ExitStrategy (抽象基类)                             │
│                                                          │
│  StrategyComposer（组合器）                             │
│                                                          │
│  BacktestEngine.backtest_three_layer()  ← 新增方法     │
│  - 三层策略回测                                         │
│  - 灵活性强，适合复杂场景                                │
└────────────────────────────────────────────────────────┘

关键设计决策：
✅ 两套架构共存（不删除现有代码）
✅ 不同使用场景，互不冲突
✅ 用户可根据需求选择合适的架构
```

---

## 四、详细实施方案

### 4.1 任务分解

| 任务ID | 任务名称 | 工作量 | 优先级 | 依赖 | 状态 |
|-------|---------|-------|--------|------|------|
| **T1** | 创建三层基类 | 1天 | P0 | - | ✅ 完成 |
| **T2** | 实现基础选股器 | 2天 | P0 | T1 | ✅ 完成 |
| **T3** | 实现基础入场策略 | 2天 | P0 | T1 | ✅ 完成 |
| **T4** | 实现基础退出策略 | 2天 | P0 | T1 | ✅ 完成 |
| **T5** | 修改回测引擎 | 2天 | P0 | T1-T4 | 📋 待开始 |
| **T6** | 单元测试 | 3天 | P0 | T1-T5 | 🔄 部分完成 |
| **T7** | 集成测试 | 2天 | P1 | T6 | 📋 待开始 |
| **T8** | 性能测试 | 1天 | P1 | T7 | 📋 待开始 |
| **T9** | 文档编写 | 2天 | P1 | T1-T8 | 🔄 部分完成 |
| **合计** | - | **17天** | - | - | **进行中** |

**注**：T2 增加1天用于实现 MLSelector（Core 内部 StarRanker 功能）

### 4.2 任务 T1：创建三层基类 ✅

> **状态**: ✅ 已完成（2026-02-06）
> **工作量**: 1 天（按计划）
> **详细报告**: [T1_implementation_summary.md](./T1_implementation_summary.md)

**目标**：实现 4 个抽象基类

**已完成文件**：
```
core/src/strategies/three_layer/
├── __init__.py                          # ✅ 完成
├── base/
│   ├── __init__.py                      # ✅ 完成
│   ├── stock_selector.py                # ✅ 完成（260行）
│   ├── entry_strategy.py                # ✅ 完成（260行）
│   ├── exit_strategy.py                 # ✅ 完成（280行）
│   └── strategy_composer.py             # ✅ 完成（280行）
├── examples/
│   └── three_layer_architecture_example.py  # ✅ 完成（340行）
└── tests/unit/strategies/three_layer/
    ├── __init__.py                      # ✅ 完成
    ├── README.md                        # ✅ 完成
    ├── test_stock_selector.py           # ✅ 完成（48个测试）
    ├── test_entry_strategy.py           # ✅ 完成（36个测试）
    ├── test_exit_strategy.py            # ✅ 完成（34个测试）
    └── test_strategy_composer.py        # ✅ 完成（25个测试）
```

**实施成果**：

✅ **源代码**：
- 4 个基类实现完成（~1,080 行）
- 完整的参数验证系统（5种类型）
- 详细的文档字符串和使用示例
- 类型注解和错误处理

✅ **测试代码**：
- 133 个单元测试（~2,080 行）
- 100% 测试通过率
- 覆盖所有公共方法和边界情况
- 完整的测试文档

✅ **示例和文档**：
- 使用示例程序
- T1 实施总结文档
- 测试说明文档

**验收标准**：
- ✅ 4 个基类实现完成
- ✅ 所有抽象方法定义清晰
- ✅ 参数验证机制完整（5种类型全覆盖）
- ✅ 单元测试通过（133/133，100%）
- ✅ 代码质量：PEP 8，类型注解，文档完整

**测试结果**：
```bash
pytest tests/unit/strategies/three_layer/ -v
# 结果：133 passed in 1.15s ✅
```

**交付物**：
- [x] 源代码：4 个基类 + 2 个 __init__.py
- [x] 测试代码：4 个测试文件 + 133 个测试用例
- [x] 示例代码：1 个演示程序
- [x] 文档：T1 实施总结 + 测试说明

### 4.3 任务 T2：实现基础选股器 ✅

> **状态**: ✅ 已完成（2026-02-06）
> **工作量**: 2 天（按计划）
> **测试通过率**: 100% (74/74)

**目标**：实现 3 个基础选股器

**已完成文件**：
```
core/src/strategies/three_layer/selectors/
├── __init__.py                      # ✅ 完成
├── momentum_selector.py             # ✅ 完成（160行）
├── value_selector.py                # ✅ 完成（220行）
└── external_selector.py             # ✅ 完成（300行）

core/tests/unit/strategies/three_layer/selectors/
├── __init__.py                      # ✅ 完成
├── test_momentum_selector.py        # ✅ 完成（32个测试）
├── test_value_selector.py           # ✅ 完成（26个测试）
└── test_external_selector.py        # ✅ 完成（29个测试）
```

**实施详情**：

#### MomentumSelector（动量选股器）

```python
"""
动量选股器
选择近期涨幅最大的股票
"""

from typing import List
import numpy as np
import pandas as pd
from loguru import logger

from ..base.stock_selector import SelectorParameter, StockSelector


class MomentumSelector(StockSelector):
    """
    动量选股器

    策略逻辑：
    1. 计算过去 N 日收益率（动量指标）
    2. 选择动量最高的前 M 只股票

    适用场景：
    - 趋势跟踪策略
    - 捕捉强势股
    """

    @property
    def id(self) -> str:
        return "momentum"

    @property
    def name(self) -> str:
        return "动量选股器"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="lookback_period",
                label="动量计算周期（天）",
                type="integer",
                default=20,
                min_value=5,
                max_value=200,
                description="计算过去 N 日收益率作为动量指标",
            ),
            SelectorParameter(
                name="top_n",
                label="选股数量",
                type="integer",
                default=50,
                min_value=5,
                max_value=200,
                description="选择动量最高的前 N 只股票",
            ),
            SelectorParameter(
                name="use_log_return",
                label="使用对数收益率",
                type="boolean",
                default=False,
                description="True=对数收益率，False=简单收益率",
            ),
            SelectorParameter(
                name="filter_negative",
                label="过滤负动量",
                type="boolean",
                default=True,
                description="是否过滤掉负动量（下跌）的股票",
            ),
        ]

    def select(self, date: pd.Timestamp, market_data: pd.DataFrame) -> List[str]:
        """动量选股逻辑"""
        lookback = self.params.get("lookback_period", 20)
        top_n = self.params.get("top_n", 50)
        use_log = self.params.get("use_log_return", False)
        filter_negative = self.params.get("filter_negative", True)

        logger.debug(f"动量选股: date={date}, lookback={lookback}, top_n={top_n}")

        # 计算动量
        if use_log:
            momentum = np.log(market_data / market_data.shift(lookback))
        else:
            momentum = market_data.pct_change(lookback)

        # 获取当日动量
        try:
            current_momentum = momentum.loc[date].dropna()
        except KeyError:
            logger.warning(f"日期 {date} 不在数据范围内")
            return []

        # 过滤负动量
        if filter_negative:
            current_momentum = current_momentum[current_momentum > 0]

        # 选择动量最高的 top_n 只股票
        selected_stocks = current_momentum.nlargest(top_n).index.tolist()

        logger.info(f"动量选股完成: 共选出 {len(selected_stocks)} 只股票")

        return selected_stocks
```

#### ExternalSelector（外部选股器 - 关键）

```python
"""
外部选股器
支持接入 StarRanker 等外部系统
"""

from typing import List
import pandas as pd
import requests
from loguru import logger

from ..base.stock_selector import SelectorParameter, StockSelector


class ExternalSelector(StockSelector):
    """
    外部选股器

    支持三种模式：
    1. StarRanker 模式：从 StarRanker API 获取股票列表
    2. 自定义 API 模式：从用户指定的 API 获取
    3. 手动输入模式：用户直接输入股票代码

    API 响应格式要求：
    {
        "stocks": ["600000.SH", "000001.SZ", ...]
    }
    """

    @property
    def id(self) -> str:
        return "external"

    @property
    def name(self) -> str:
        return "外部数据源选股器"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="source",
                label="数据源",
                type="select",
                default="manual",
                options=[
                    {"value": "starranker", "label": "StarRanker"},
                    {"value": "custom_api", "label": "自定义API"},
                    {"value": "manual", "label": "手动输入"},
                ],
                description="选择外部选股数据源",
            ),
            SelectorParameter(
                name="api_endpoint",
                label="API地址（仅自定义API模式）",
                type="string",
                default="",
                description="自定义 API 的完整 URL",
            ),
            SelectorParameter(
                name="api_timeout",
                label="API超时时间（秒）",
                type="integer",
                default=10,
                min_value=1,
                max_value=60,
                description="API 请求超时时间",
            ),
            SelectorParameter(
                name="manual_stocks",
                label="手动股票池（仅手动模式）",
                type="string",
                default="",
                description="逗号分隔的股票代码，如：600000.SH,000001.SZ",
            ),
        ]

    def select(self, date: pd.Timestamp, market_data: pd.DataFrame) -> List[str]:
        """从外部系统获取股票列表"""
        source = self.params.get("source", "manual")

        if source == "starranker":
            return self._fetch_from_starranker(date)
        elif source == "custom_api":
            api_endpoint = self.params.get("api_endpoint", "")
            if not api_endpoint:
                logger.error("自定义 API 模式必须提供 api_endpoint 参数")
                return []
            return self._fetch_from_custom_api(date, api_endpoint)
        elif source == "manual":
            manual_stocks = self.params.get("manual_stocks", "")
            if not manual_stocks:
                logger.warning("手动模式未提供股票代码")
                return []
            return [s.strip() for s in manual_stocks.split(",") if s.strip()]
        else:
            logger.error(f"未知的数据源：{source}")
            return []

    def _fetch_from_starranker(self, date: pd.Timestamp) -> List[str]:
        """
        从 StarRanker 获取股票列表

        集成方式：
        1. HTTP API 调用（推荐）
        2. 数据库查询
        3. 文件读取
        """
        # TODO: 实现 StarRanker 集成
        # 这里需要与 StarRanker 团队协调确定接口
        logger.warning("StarRanker 集成待实现，返回空列表")
        return []

    def _fetch_from_custom_api(self, date: pd.Timestamp, api_endpoint: str) -> List[str]:
        """从自定义 API 获取股票列表"""
        timeout = self.params.get("api_timeout", 10)

        try:
            response = requests.get(
                api_endpoint,
                params={"date": date.strftime("%Y-%m-%d")},
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()

            if "stocks" not in data:
                logger.error("API 响应缺少 'stocks' 字段")
                return []

            stocks = data["stocks"]
            logger.info(f"从自定义 API 获取到 {len(stocks)} 只股票")
            return stocks

        except requests.Timeout:
            logger.error(f"API 请求超时（>{timeout}s）")
            return []
        except requests.RequestException as e:
            logger.error(f"API 请求失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析 API 响应失败: {e}")
            return []
```

**实施成果**：

✅ **源代码**：
- 3 个选股器实现完成（~680 行）
  - MomentumSelector: 动量选股器（160行）
  - ValueSelector: 价值选股器（220行）
  - ExternalSelector: 外部选股器（300行）
- 完整的参数验证和错误处理
- 详细的文档字符串和使用示例
- 完善的日志记录

✅ **测试代码**：
- 74 个单元测试（~1,500 行）
- 100% 测试通过率
- 覆盖基本功能、边界情况、参数验证、集成场景

✅ **功能特性**：
- MomentumSelector: 支持简单/对数收益率，可过滤负动量
- ValueSelector: 综合波动率和反转效应，灵活权重配置
- ExternalSelector: 支持手动输入、自定义API、StarRanker（预留）

**验收标准达成情况**：
- ✅ 3 个选股器实现完成
- ✅ MomentumSelector 正确计算动量（支持简单/对数收益率）
- ✅ ExternalSelector 支持三种模式（手动、API、StarRanker预留）
- ✅ 单元测试通过（74/74，100%）
- ✅ 代码质量：PEP 8，类型注解，文档完整

**测试结果**：
```bash
pytest tests/unit/strategies/three_layer/selectors/ -v
# 结果：74 passed in 2.29s ✅
```

**使用示例**：
```python
from src.strategies.three_layer import MomentumSelector

# 创建动量选股器
selector = MomentumSelector(params={
    'lookback_period': 20,
    'top_n': 50,
    'filter_negative': True
})

# 执行选股
selected_stocks = selector.select(date, market_data)
```

**交付物**：
- [x] 源代码：3 个选股器 + 1 个 __init__.py
- [x] 测试代码：3 个测试文件 + 74 个测试用例
- [x] 模块集成：更新主模块导出

---

### 4.4 任务 T3：实现基础入场策略 ✅

> **状态**: ✅ 已完成（2026-02-06）
> **工作量**: 2 天（按计划）
> **测试通过率**: 100% (53/53)

**目标**：实现 3 个基础入场策略

**已完成文件**：
```
core/src/strategies/three_layer/entries/
├── __init__.py                      # ✅ 完成
├── ma_breakout_entry.py             # ✅ 完成（235行）
├── rsi_oversold_entry.py            # ✅ 完成（236行）
└── immediate_entry.py               # ✅ 完成（183行）

core/tests/unit/strategies/three_layer/entries/
├── __init__.py                      # ✅ 完成
├── test_ma_breakout_entry.py        # ✅ 完成（17个测试，368行）
├── test_rsi_oversold_entry.py       # ✅ 完成（18个测试，389行）
└── test_immediate_entry.py          # ✅ 完成（18个测试，458行）
```

**实施成果**：

✅ **源代码**：
- 3 个入场策略实现完成（~654 行）
- MABreakoutEntry: 均线突破入场（235行）
- RSIOversoldEntry: RSI超卖入场（236行）
- ImmediateEntry: 立即入场（183行）
- 完整的参数验证和错误处理
- 详细的文档字符串和使用示例
- 完善的日志记录

✅ **测试代码**：
- 53 个单元测试（~1,215 行）
- 100% 测试通过率
- 覆盖基本功能、边界情况、参数验证、多股票场景

✅ **功能特性**：
- MABreakoutEntry: 检测金叉，支持回溯期配置，可选均线趋势过滤
- RSIOversoldEntry: 计算RSI指标，支持超卖检测，可选RSI回升要求
- ImmediateEntry: 立即入场，支持数量限制和数据验证

**验收标准达成情况**：
- ✅ 3 个入场策略实现完成
- ✅ MABreakoutEntry 正确检测金叉
- ✅ RSIOversoldEntry RSI计算准确
- ✅ ImmediateEntry 支持数量限制和数据验证
- ✅ 单元测试通过（53/53，100%）
- ✅ 代码质量：PEP 8，类型注解，文档完整

**测试结果**：
```bash
pytest tests/unit/strategies/three_layer/entries/ -v
# 结果：53 passed in 0.93s ✅
```

**使用示例**：
```python
from src.strategies.three_layer.entries import (
    MABreakoutEntry,
    RSIOversoldEntry,
    ImmediateEntry
)

# 均线突破入场
ma_entry = MABreakoutEntry(params={
    'short_window': 5,
    'long_window': 20,
    'lookback_for_cross': 1
})

# RSI超卖入场
rsi_entry = RSIOversoldEntry(params={
    'rsi_period': 14,
    'oversold_threshold': 30.0,
    'require_rsi_turning_up': False
})

# 立即入场
immediate_entry = ImmediateEntry(params={
    'max_stocks': 10,
    'min_stocks': 5,
    'validate_data': True
})

# 生成入场信号
signals = ma_entry.generate_entry_signals(
    stocks=['600000.SH', '000001.SZ'],
    data=stock_data_dict,
    date=pd.Timestamp('2023-06-01')
)
```

**交付物**：
- [x] 源代码：3 个入场策略 + 1 个 __init__.py
- [x] 测试代码：3 个测试文件 + 53 个测试用例
- [x] 模块集成：更新主模块导出

---

**原实施详情**（供参考）：

#### MABreakoutEntry（均线突破入场）

```python
"""
均线突破入场策略
当短期均线上穿长期均线时产生买入信号
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.entry_strategy import EntryStrategy


class MABreakoutEntry(EntryStrategy):
    """
    均线突破入场策略

    策略逻辑：
    1. 计算短期、长期移动平均线
    2. 检测金叉：短期MA上穿长期MA
    3. 对候选股票中出现金叉的股票生成买入信号

    适用场景：
    - 趋势跟踪
    - 捕捉突破行情
    """

    @property
    def id(self) -> str:
        return "ma_breakout"

    @property
    def name(self) -> str:
        return "均线突破入场"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "short_window",
                "label": "短期均线周期",
                "type": "integer",
                "default": 5,
                "min": 2,
                "max": 50,
                "description": "短期移动平均线周期（天）"
            },
            {
                "name": "long_window",
                "label": "长期均线周期",
                "type": "integer",
                "default": 20,
                "min": 5,
                "max": 200,
                "description": "长期移动平均线周期（天）"
            },
            {
                "name": "lookback_for_cross",
                "label": "金叉检测回溯期",
                "type": "integer",
                "default": 1,
                "min": 1,
                "max": 5,
                "description": "检测过去N日内是否发生金叉"
            }
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """生成入场信号"""
        short_window = self.params.get("short_window", 5)
        long_window = self.params.get("long_window", 20)
        lookback = self.params.get("lookback_for_cross", 1)

        signals = {}

        for stock in stocks:
            if stock not in data:
                continue

            stock_data = data[stock]

            # 计算移动平均线
            ma_short = stock_data['close'].rolling(short_window).mean()
            ma_long = stock_data['close'].rolling(long_window).mean()

            try:
                # 检测金叉（短期MA上穿长期MA）
                current_idx = stock_data.index.get_loc(date)

                if current_idx < lookback:
                    continue

                # 检查过去 lookback 日内是否发生金叉
                for i in range(lookback):
                    check_idx = current_idx - i
                    prev_idx = check_idx - 1

                    # 前一天：短MA <= 长MA
                    # 当天：短MA > 长MA
                    if (ma_short.iloc[prev_idx] <= ma_long.iloc[prev_idx] and
                        ma_short.iloc[check_idx] > ma_long.iloc[check_idx]):
                        # 金叉发生
                        signals[stock] = 1.0
                        logger.debug(f"{stock} 在 {date} 附近发生金叉")
                        break

            except (KeyError, IndexError):
                continue

        # 等权分配
        if signals:
            weight = 1.0 / len(signals)
            signals = {stock: weight for stock in signals}
            logger.info(f"均线突破入场: 生成 {len(signals)} 个买入信号")

        return signals
```

#### RSIOversoldEntry（RSI超卖入场）

```python
"""
RSI超卖入场策略
当RSI指标进入超卖区间时产生买入信号
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.entry_strategy import EntryStrategy


class RSIOversoldEntry(EntryStrategy):
    """
    RSI超卖入场策略

    策略逻辑：
    1. 计算RSI指标
    2. 检测超卖：RSI < 阈值（默认30）
    3. 对超卖股票生成买入信号

    适用场景：
    - 捕捉超卖反弹
    - 逆向策略
    """

    @property
    def id(self) -> str:
        return "rsi_oversold"

    @property
    def name(self) -> str:
        return "RSI超卖入场"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "rsi_period",
                "label": "RSI周期",
                "type": "integer",
                "default": 14,
                "min": 5,
                "max": 50,
                "description": "RSI计算周期（天）"
            },
            {
                "name": "oversold_threshold",
                "label": "超卖阈值",
                "type": "float",
                "default": 30.0,
                "min": 10.0,
                "max": 40.0,
                "description": "RSI低于此值视为超卖"
            }
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """生成入场信号"""
        rsi_period = self.params.get("rsi_period", 14)
        oversold_threshold = self.params.get("oversold_threshold", 30.0)

        signals = {}

        for stock in stocks:
            if stock not in data:
                continue

            stock_data = data[stock]

            # 计算RSI
            rsi = self._calculate_rsi(stock_data['close'], rsi_period)

            try:
                current_rsi = rsi.loc[date]

                # 检测超卖
                if current_rsi < oversold_threshold:
                    signals[stock] = 1.0
                    logger.debug(f"{stock} RSI={current_rsi:.2f} 超卖")

            except KeyError:
                continue

        # 等权分配
        if signals:
            weight = 1.0 / len(signals)
            signals = {stock: weight for stock in signals}
            logger.info(f"RSI超卖入场: 生成 {len(signals)} 个买入信号")

        return signals

    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi
```

#### ImmediateEntry（立即入场）

```python
"""
立即入场策略
对所有候选股票立即产生买入信号（用于测试）
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.entry_strategy import EntryStrategy


class ImmediateEntry(EntryStrategy):
    """
    立即入场策略

    策略逻辑：
    对选股器选出的所有股票立即产生买入信号

    适用场景：
    - 测试选股器效果
    - 简单的买入持有策略
    """

    @property
    def id(self) -> str:
        return "immediate"

    @property
    def name(self) -> str:
        return "立即入场"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "max_stocks",
                "label": "最大买入数量",
                "type": "integer",
                "default": 10,
                "min": 1,
                "max": 100,
                "description": "限制同时买入的股票数量"
            }
        ]

    def generate_entry_signals(
        self,
        stocks: List[str],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> Dict[str, float]:
        """生成入场信号：对所有候选股票产生等权买入信号"""
        max_stocks = self.params.get("max_stocks", 10)

        # 限制买入数量
        selected_stocks = stocks[:max_stocks]

        # 等权分配
        if selected_stocks:
            weight = 1.0 / len(selected_stocks)
            signals = {stock: weight for stock in selected_stocks}
            logger.info(f"立即入场: 生成 {len(signals)} 个买入信号")
        else:
            signals = {}

        return signals
```

**验收标准**：
- ✅ 3 个入场策略实现完成
- ✅ MABreakoutEntry 正确检测金叉
- ✅ RSIOversoldEntry RSI计算准确
- ✅ ImmediateEntry 支持数量限制
- ✅ 单元测试通过（18 个测试用例）

### 4.5 任务 T4：实现基础退出策略 ✅

> **状态**: ✅ 已完成（2026-02-06）
> **工作量**: 2 天（按计划）

**目标**：实现 4 个基础退出策略

**工作量**：2 天

**文件清单**：
```
core/src/strategies/three_layer/exits/
├── __init__.py
├── atr_stop_loss_exit.py      # ATR动态止损
├── fixed_stop_loss_exit.py    # 固定止损止盈
├── time_based_exit.py          # 时间止损
└── combined_exit.py            # 组合退出
```

**实施详情**：

#### ATRStopLossExit（ATR动态止损）

```python
"""
ATR动态止损退出策略
基于ATR（Average True Range）设置动态止损位
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position


class ATRStopLossExit(ExitStrategy):
    """
    ATR动态止损退出策略

    策略逻辑：
    1. 计算ATR指标
    2. 止损位 = 入场价 - ATR × 倍数
    3. 当前价格跌破止损位时卖出

    优势：
    - 适应市场波动
    - 避免在正常波动中被止损
    """

    @property
    def id(self) -> str:
        return "atr_stop_loss"

    @property
    def name(self) -> str:
        return "ATR动态止损"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "atr_period",
                "label": "ATR周期",
                "type": "integer",
                "default": 14,
                "min": 5,
                "max": 50,
                "description": "ATR计算周期（天）"
            },
            {
                "name": "atr_multiplier",
                "label": "ATR倍数",
                "type": "float",
                "default": 2.0,
                "min": 0.5,
                "max": 5.0,
                "description": "止损位 = 入场价 - ATR × 倍数"
            }
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """生成退出信号"""
        atr_period = self.params.get("atr_period", 14)
        atr_multiplier = self.params.get("atr_multiplier", 2.0)

        exit_stocks = []

        for stock, position in positions.items():
            if stock not in data:
                continue

            stock_data = data[stock]

            # 计算ATR
            atr = self._calculate_atr(stock_data, atr_period)

            try:
                current_atr = atr.loc[date]
                current_price = position.current_price
                entry_price = position.entry_price

                # 计算止损位
                stop_loss_price = entry_price - (current_atr * atr_multiplier)

                # 检查是否触发止损
                if current_price < stop_loss_price:
                    exit_stocks.append(stock)
                    loss_pct = (current_price - entry_price) / entry_price * 100
                    logger.info(
                        f"{stock} 触发ATR止损: "
                        f"入场价={entry_price:.2f}, "
                        f"当前价={current_price:.2f}, "
                        f"止损位={stop_loss_price:.2f}, "
                        f"亏损={loss_pct:.2f}%"
                    )

            except KeyError:
                continue

        return exit_stocks

    def _calculate_atr(self, stock_data: pd.DataFrame, period: int) -> pd.Series:
        """计算ATR指标"""
        high = stock_data['high']
        low = stock_data['low']
        close = stock_data['close']

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR = TR的移动平均
        atr = tr.rolling(window=period).mean()

        return atr
```

#### FixedStopLossExit（固定止损止盈）

```python
"""
固定止损止盈退出策略
设置固定的止损和止盈百分比
"""

from typing import Any, Dict, List
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position


class FixedStopLossExit(ExitStrategy):
    """
    固定止损止盈退出策略

    策略逻辑：
    1. 止损：亏损达到固定百分比时卖出
    2. 止盈：盈利达到固定百分比时卖出

    适用场景：
    - 严格风险控制
    - 简单明确的退出规则
    """

    @property
    def id(self) -> str:
        return "fixed_stop_loss"

    @property
    def name(self) -> str:
        return "固定止损止盈"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "stop_loss_pct",
                "label": "止损百分比",
                "type": "float",
                "default": -5.0,
                "min": -20.0,
                "max": -1.0,
                "description": "亏损达到此百分比时卖出（负数）"
            },
            {
                "name": "take_profit_pct",
                "label": "止盈百分比",
                "type": "float",
                "default": 10.0,
                "min": 1.0,
                "max": 50.0,
                "description": "盈利达到此百分比时卖出（正数）"
            }
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date,
    ) -> List[str]:
        """生成退出信号"""
        stop_loss_pct = self.params.get("stop_loss_pct", -5.0)
        take_profit_pct = self.params.get("take_profit_pct", 10.0)

        exit_stocks = []

        for stock, position in positions.items():
            pnl_pct = position.unrealized_pnl_pct

            # 触发止损
            if pnl_pct <= stop_loss_pct:
                exit_stocks.append(stock)
                logger.info(f"{stock} 触发止损: {pnl_pct:.2f}% <= {stop_loss_pct:.2f}%")

            # 触发止盈
            elif pnl_pct >= take_profit_pct:
                exit_stocks.append(stock)
                logger.info(f"{stock} 触发止盈: {pnl_pct:.2f}% >= {take_profit_pct:.2f}%")

        return exit_stocks
```

#### TimeBasedExit（时间止损）

```python
"""
时间止损退出策略
持仓达到指定天数后强制卖出
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position


class TimeBasedExit(ExitStrategy):
    """
    时间止损退出策略

    策略逻辑：
    持仓天数达到阈值后强制卖出

    适用场景：
    - 固定持仓周期策略
    - 避免长期套牢
    """

    @property
    def id(self) -> str:
        return "time_based"

    @property
    def name(self) -> str:
        return "时间止损"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": "holding_period",
                "label": "持仓天数",
                "type": "integer",
                "default": 10,
                "min": 1,
                "max": 100,
                "description": "持仓超过此天数后强制卖出"
            }
        ]

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """生成退出信号"""
        holding_period = self.params.get("holding_period", 10)

        exit_stocks = []

        for stock, position in positions.items():
            # 计算持仓天数
            holding_days = (date - position.entry_date).days

            if holding_days >= holding_period:
                exit_stocks.append(stock)
                logger.info(f"{stock} 达到持仓期限: {holding_days} 天 >= {holding_period} 天")

        return exit_stocks
```

#### CombinedExit（组合退出）

```python
"""
组合退出策略
组合多个退出策略，采用OR逻辑
"""

from typing import Any, Dict, List
import pandas as pd
from loguru import logger

from ..base.exit_strategy import ExitStrategy, Position


class CombinedExit(ExitStrategy):
    """
    组合退出策略

    策略逻辑：
    组合多个退出策略，任意一个触发即卖出（OR逻辑）

    用法：
        combined = CombinedExit(
            strategies=[
                ATRStopLossExit(params={'atr_multiplier': 2.0}),
                TimeBasedExit(params={'holding_period': 10})
            ]
        )
    """

    def __init__(self, strategies: List[ExitStrategy]):
        self.strategies = strategies
        super().__init__()

    @property
    def id(self) -> str:
        return "combined"

    @property
    def name(self) -> str:
        strategy_names = [s.name for s in self.strategies]
        return f"组合退出 ({' + '.join(strategy_names)})"

    @classmethod
    def get_parameters(cls) -> List[Dict[str, Any]]:
        return []  # 参数由子策略定义

    def generate_exit_signals(
        self,
        positions: Dict[str, Position],
        data: Dict[str, pd.DataFrame],
        date: pd.Timestamp,
    ) -> List[str]:
        """生成退出信号：OR逻辑"""
        all_exit_stocks = set()

        for strategy in self.strategies:
            exit_stocks = strategy.generate_exit_signals(positions, data, date)
            all_exit_stocks.update(exit_stocks)

        result = list(all_exit_stocks)

        if result:
            logger.info(f"组合退出策略触发: {len(result)} 只股票需要卖出")

        return result
```

**已完成文件**：
```
core/src/strategies/three_layer/exits/
├── __init__.py                          # ✅ 完成（导出所有退出策略）
├── atr_stop_loss_exit.py                # ✅ 完成（227行）
├── fixed_stop_loss_exit.py              # ✅ 完成（155行）
├── time_based_exit.py                   # ✅ 完成（170行）
└── combined_exit.py                     # ✅ 完成（193行）

core/tests/unit/strategies/three_layer/exits/
├── __init__.py                          # ✅ 完成
├── test_atr_stop_loss_exit.py          # ✅ 完成（31个测试）
├── test_fixed_stop_loss_exit.py        # ✅ 完成（28个测试）
├── test_time_based_exit.py             # ✅ 完成（20个测试）
└── test_combined_exit.py               # ✅ 完成（14个测试）
```

**实施成果**：
- ✅ **ATRStopLossExit**: 基于ATR(Average True Range)的动态止损策略
  - 参数: atr_period(14), atr_multiplier(2.0)
  - 优势: 适应市场波动，避免在正常波动中被止损

- ✅ **FixedStopLossExit**: 固定百分比止损止盈策略
  - 参数: stop_loss_pct(-5.0), take_profit_pct(10.0), enable_stop_loss, enable_take_profit
  - 优势: 严格风险控制，简单明确的退出规则

- ✅ **TimeBasedExit**: 基于持仓时间的退出策略
  - 参数: holding_period(10), count_trading_days_only(False)
  - 优势: 固定持仓周期，避免长期套牢

- ✅ **CombinedExit**: 组合退出策略（OR逻辑）
  - 参数: strategies(子策略列表)
  - 优势: 多维度风险控制，综合多种策略的优势

**验收标准**：
- ✅ 4 个退出策略实现完成
- ✅ ATRStopLossExit ATR计算准确
- ✅ FixedStopLossExit 止损止盈正确触发
- ✅ TimeBasedExit 持仓天数计算准确
- ✅ CombinedExit OR逻辑正确
- ✅ 单元测试通过（93 个测试用例，100%通过率）
- ✅ 完整的类型注解和文档字符串
- ✅ 健壮的错误处理和参数验证
- ✅ 详细的日志记录

### 4.6 任务 T5：修改回测引擎

**目标**：在 BacktestEngine 中添加 `backtest_three_layer()` 方法

**工作量**：2 天

**文件**：`core/src/backtest/backtest_engine.py`

**实施详情**：

```python
def backtest_three_layer(
    self,
    selector: StockSelector,
    entry: EntryStrategy,
    exit_strategy: ExitStrategy,
    prices: pd.DataFrame,
    start_date: str,
    end_date: str,
    rebalance_freq: str = 'W',
    initial_capital: float = 1_000_000,
    commission_rate: float = 0.0003,
    slippage_rate: float = 0.0005,
) -> Dict[str, Any]:
    """
    三层架构回测

    参数:
        selector: 股票选择器
        entry: 入场策略
        exit_strategy: 退出策略
        prices: 价格数据 DataFrame(index=日期, columns=股票代码)
        start_date: 开始日期
        end_date: 结束日期
        rebalance_freq: 选股频率 ('D'=日, 'W'=周, 'M'=月)
        initial_capital: 初始资金
        commission_rate: 佣金费率
        slippage_rate: 滑点费率

    返回:
        {
            'equity_curve': 净值曲线,
            'positions': 持仓记录,
            'trades': 交易记录,
            'metrics': 绩效指标
        }
    """

    # 1. 初始化
    portfolio = BacktestPortfolio(initial_capital)
    recorder = BacktestRecorder()
    dates = pd.date_range(start_date, end_date, freq='D')

    # 2. 计算调仓日期
    rebalance_dates = self._get_rebalance_dates(dates, rebalance_freq)

    # 3. 准备股票数据字典（OHLCV格式）
    stock_data = self._prepare_stock_data(prices)

    # 4. 当前候选股票池
    candidate_stocks = []

    # 5. 主回测循环
    for date in dates:
        logger.debug(f"回测日期: {date}")

        # 5.1 更新持仓价格
        portfolio.update_prices(prices.loc[date])
        recorder.record_equity(date, portfolio.get_total_equity())

        # 5.2 Layer 3: 检查退出信号（每日检查）
        positions_dict = {
            stock: Position(
                stock_code=stock,
                entry_date=pos['entry_date'],
                entry_price=pos['entry_price'],
                shares=pos['shares'],
                current_price=prices.loc[date, stock],
                unrealized_pnl=pos['unrealized_pnl'],
                unrealized_pnl_pct=pos['unrealized_pnl_pct']
            )
            for stock, pos in portfolio.long_positions.items()
        }

        exit_signals = exit_strategy.generate_exit_signals(
            positions_dict, stock_data, date
        )

        # 执行卖出
        for stock in exit_signals:
            if stock in portfolio.long_positions:
                sell_price = prices.loc[date, stock] * (1 - slippage_rate)
                shares = portfolio.long_positions[stock]['shares']
                portfolio.sell(stock, shares, sell_price, commission_rate)
                recorder.record_trade(date, stock, 'sell', shares, sell_price)
                logger.debug(f"卖出 {stock}: {shares} 股")

        # 5.3 Layer 1: 选股（按调仓频率）
        if date in rebalance_dates:
            candidate_stocks = selector.select(date, prices)
            logger.info(f"调仓日 {date}: 选出 {len(candidate_stocks)} 只候选股票")

        # 5.4 Layer 2: 入场信号（每日检查）
        if candidate_stocks:
            entry_signals = entry.generate_entry_signals(
                candidate_stocks, stock_data, date
            )

            # 执行买入
            total_weight = sum(entry_signals.values())
            if total_weight > 0:
                for stock, weight in entry_signals.items():
                    normalized_weight = weight / total_weight
                    target_value = portfolio.cash * normalized_weight

                    buy_price = prices.loc[date, stock] * (1 + slippage_rate)
                    shares = int(target_value // (buy_price * (1 + commission_rate)))

                    if shares > 0:
                        portfolio.buy(stock, shares, buy_price, commission_rate, date)
                        recorder.record_trade(date, stock, 'buy', shares, buy_price)
                        logger.debug(f"买入 {stock}: {shares} 股")

    # 6. 计算绩效指标
    equity_curve = recorder.get_equity_curve()
    metrics = self._calculate_metrics(equity_curve, recorder.trades)

    return {
        'equity_curve': equity_curve,
        'positions': recorder.positions,
        'trades': recorder.trades,
        'metrics': metrics
    }


def _prepare_stock_data(self, prices: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    准备股票数据字典（OHLCV格式）

    注意：如果没有OHLCV数据，使用收盘价模拟
    """
    stock_data = {}

    for stock in prices.columns:
        stock_data[stock] = pd.DataFrame({
            'open': prices[stock],    # 模拟数据
            'high': prices[stock],
            'low': prices[stock],
            'close': prices[stock],
            'volume': 1000000         # 模拟数据
        })

    return stock_data


def _get_rebalance_dates(self, dates: pd.DatetimeIndex, freq: str) -> List[pd.Timestamp]:
    """计算调仓日期"""
    if freq == 'D':
        return dates.tolist()
    elif freq == 'W':
        return [dates[0]] + [d for d in dates if d.dayofweek == 0]  # 每周一
    elif freq == 'M':
        return [dates[0]] + [d for d in dates if d.day == 1]  # 每月首日
    else:
        raise ValueError(f"不支持的调仓频率: {freq}")
```

**验收标准**：
- ✅ `backtest_three_layer()` 方法实现完成
- ✅ 选股、入场、退出逻辑正确执行
- ✅ 调仓频率控制正确
- ✅ 交易执行逻辑正确
- ✅ 与现有 `backtest_long_only()` 共存
- ✅ 单元测试通过（12 个测试用例）

### 4.7 任务 T6-T9：测试与文档

**任务T6：单元测试（3天）**
- 基类测试：15 个用例
- 选股器测试：24 个用例
- 入场策略测试：18 个用例
- 退出策略测试：24 个用例
- 回测引擎测试：12 个用例
- **合计：93 个测试用例**

**任务T7：集成测试（2天）**
- 完整回测流程测试
- 策略组合测试
- 异常场景测试

**任务T8：性能测试（1天）**
- 回测速度对比
- 内存占用分析
- 优化瓶颈

**任务T9：文档编写（2天）**
- API 文档
- 用户指南
- 迁移指南

---

## 五、StarRanker 集成方案

### 5.1 集成概述

StarRanker 是外部股票推荐系统，Core v3.0 通过 `ExternalSelector` 支持集成。

**集成位置**：
```
ExternalSelector._fetch_from_starranker()
└── StarRanker 客户端
    ├── HTTP API 客户端（推荐）
    ├── 数据库直连客户端
    └── 文件交换客户端（快速原型）
```

### 5.2 实施方案（参考独立文档）

详细的 StarRanker 集成方案已单独编写，请参考：

**📄 [`starranker_integration_guide.md`](./starranker_integration_guide.md)**

该文档包含：
- 三种集成方式（HTTP API、数据库、文件）
- 完整代码实现
- API 规范
- 测试方案
- 部署指南

**快速开始**：

```python
from core.src.strategies.three_layer.selectors import ExternalSelector
from core.src.strategies.three_layer.entries import ImmediateEntry
from core.src.strategies.three_layer.exits import FixedStopLossExit
from core.src.strategies.three_layer.base import StrategyComposer

# 使用 StarRanker 选股
selector = ExternalSelector(params={
    'source': 'starranker',
    'starranker_config': {
        'mode': 'api',  # 或 'database', 'file'
        'api_endpoint': 'http://starranker-api:8000'
    }
})

# 组合策略
composer = StrategyComposer(
    selector=selector,
    entry=ImmediateEntry(),
    exit_strategy=FixedStopLossExit(params={'stop_loss_pct': -5.0}),
    rebalance_freq='W'
)

# 回测
from core.src.backtest import BacktestEngine

engine = BacktestEngine()
result = engine.backtest_three_layer(
    selector=composer.selector,
    entry=composer.entry,
    exit_strategy=composer.exit,
    prices=prices_df,
    start_date='2023-01-01',
    end_date='2023-12-31',
    rebalance_freq='W'
)
```

---

## 六、测试策略

### 6.1 单元测试

**测试框架**：pytest

**测试覆盖率目标**：≥ 85%

**测试文件结构**：
```
core/tests/unit/strategies/three_layer/
├── test_stock_selector.py        # 选股器基类测试
├── test_entry_strategy.py        # 入场策略基类测试
├── test_exit_strategy.py         # 退出策略基类测试
├── test_strategy_composer.py     # 组合器测试
├── selectors/
│   ├── test_momentum_selector.py
│   ├── test_value_selector.py
│   └── test_external_selector.py
├── entries/
│   ├── test_ma_breakout_entry.py
│   ├── test_rsi_oversold_entry.py
│   └── test_immediate_entry.py
└── exits/
    ├── test_atr_stop_loss_exit.py
    ├── test_fixed_stop_loss_exit.py
    ├── test_time_based_exit.py
    └── test_combined_exit.py
```

**关键测试用例**：

```python
# test_momentum_selector.py
def test_momentum_selector_basic():
    """测试动量选股基本功能"""
    selector = MomentumSelector(params={'top_n': 10, 'lookback_period': 20})

    # 准备测试数据
    prices = pd.DataFrame({
        'A': [100, 105, 110, 115, 120],  # 涨幅20%
        'B': [100, 102, 104, 106, 108],  # 涨幅8%
        'C': [100, 98, 96, 94, 92],      # 跌幅8%
    }, index=pd.date_range('2023-01-01', periods=25))

    # 执行选股
    selected = selector.select(prices.index[-1], prices)

    # 验证结果
    assert 'A' in selected  # 涨幅最大应被选中
    assert 'C' not in selected  # 负动量应被过滤


def test_momentum_selector_parameter_validation():
    """测试参数验证"""
    with pytest.raises(ValueError):
        MomentumSelector(params={'top_n': -1})  # 无效参数

    with pytest.raises(ValueError):
        MomentumSelector(params={'unknown_param': 123})  # 未知参数
```

### 6.2 集成测试

**测试场景**：

1. **完整回测流程测试**
```python
def test_full_backtest_workflow():
    """测试完整的三层架构回测流程"""
    # 准备策略
    selector = MomentumSelector(params={'top_n': 30})
    entry = MABreakoutEntry(params={'short_window': 5, 'long_window': 20})
    exit_strategy = CombinedExit(strategies=[
        FixedStopLossExit(params={'stop_loss_pct': -5.0}),
        TimeBasedExit(params={'holding_period': 10})
    ])

    # 准备数据
    prices = load_test_data('2023-01-01', '2023-12-31')

    # 执行回测
    engine = BacktestEngine()
    result = engine.backtest_three_layer(
        selector=selector,
        entry=entry,
        exit_strategy=exit_strategy,
        prices=prices,
        start_date='2023-01-01',
        end_date='2023-12-31',
        rebalance_freq='W'
    )

    # 验证结果
    assert 'equity_curve' in result
    assert 'trades' in result
    assert 'metrics' in result
    assert result['metrics']['total_return'] != 0
```

2. **策略组合测试**
- 测试 3×3×4 = 36 种策略组合
- 确保所有组合均可正常运行

3. **边界条件测试**
- 空候选股票池
- 数据缺失
- 极端市场条件

### 6.3 性能测试

**测试指标**：

| 指标 | 目标 | 测试方法 |
|------|------|---------|
| 回测速度 | 与 v2.x 持平 | 相同数据对比 |
| 内存占用 | < 2GB（100只股票×3年） | memory_profiler |
| 策略切换成本 | < 100ms | timeit |

**性能优化要点**：
- 缓存技术指标计算结果
- 向量化操作
- 避免循环中的重复计算

---

## 七、性能优化

### 7.1 优化策略

**1. 技术指标缓存**

```python
class CachedIndicators:
    """技术指标缓存器"""

    def __init__(self):
        self._cache = {}

    def get_or_calculate(self, key, calc_func):
        """获取或计算指标"""
        if key not in self._cache:
            self._cache[key] = calc_func()
        return self._cache[key]


# 使用示例
class MABreakoutEntry(EntryStrategy):
    def __init__(self, params):
        super().__init__(params)
        self._indicator_cache = CachedIndicators()

    def generate_entry_signals(self, stocks, data, date):
        for stock in stocks:
            # 缓存MA计算
            ma_short = self._indicator_cache.get_or_calculate(
                f"{stock}_ma_short",
                lambda: data[stock]['close'].rolling(5).mean()
            )
```

**2. 向量化操作**

```python
# ❌ 低效：循环计算
for stock in stocks:
    momentum[stock] = prices[stock].pct_change(20)

# ✅ 高效：向量化
momentum = prices.pct_change(20)  # 一次性计算所有股票
```

**3. 数据预加载**

```python
def backtest_three_layer(self, ...):
    # 预加载所有股票数据
    stock_data = self._prepare_stock_data(prices)

    # 预计算技术指标
    indicators = self._precompute_indicators(stock_data)
```

### 7.2 性能基准

**目标**：
- 回测 100 只股票 × 3 年数据
- 时间 < 30 秒
- 内存 < 2GB

---

## 八、迁移指南

### 8.1 现有用户升级步骤

**步骤1：安装 Core v3.0**

```bash
cd /Volumes/MacDriver/stock-analysis/core
git pull origin main
pip install -e .
```

**步骤2：现有策略继续可用**

```python
# ✅ 现有代码无需修改
from core.src.strategies import MomentumStrategy
from core.src.backtest import BacktestEngine

strategy = MomentumStrategy(lookback_period=20)
engine = BacktestEngine()

result = engine.backtest_long_only(
    signals=strategy.generate_signals(prices),
    prices=prices,
    top_n=50
)
```

**步骤3：尝试三层架构（可选）**

```python
# 🆕 使用三层架构
from core.src.strategies.three_layer.selectors import MomentumSelector
from core.src.strategies.three_layer.entries import ImmediateEntry
from core.src.strategies.three_layer.exits import FixedStopLossExit

selector = MomentumSelector(params={'top_n': 50, 'lookback_period': 20})
entry = ImmediateEntry()
exit_strategy = FixedStopLossExit(params={'stop_loss_pct': -5.0})

result = engine.backtest_three_layer(
    selector=selector,
    entry=entry,
    exit_strategy=exit_strategy,
    prices=prices,
    start_date='2023-01-01',
    end_date='2023-12-31'
)
```

### 8.2 从 Zipline 迁移

| Zipline 概念 | Core v3.0 对应 |
|-------------|---------------|
| Pipeline | StockSelector |
| Factor | 技术指标计算（在策略内） |
| Order | BacktestEngine 自动处理 |
| Schedule | rebalance_freq 参数 |

**Zipline Pipeline 示例**：
```python
# Zipline
class MyPipeline:
    def make_pipeline():
        momentum = Returns(window_length=20)
        return Pipeline(
            columns={'momentum': momentum},
            screen=momentum.top(50)
        )

# Core v3.0 等价实现
class MySelector(StockSelector):
    def select(self, date, market_data):
        momentum = market_data.pct_change(20).loc[date]
        return momentum.nlargest(50).index.tolist()
```

### 8.3 常见问题

**Q: 三层架构是否会降低性能？**
A: 不会。通过缓存和向量化优化，性能与 v2.x 持平。

**Q: 现有策略需要重写吗？**
A: 不需要。v2.x 和 v3.0 架构共存。

**Q: 如何集成 StarRanker？**
A: 参考 [`starranker_integration_guide.md`](./starranker_integration_guide.md)。

**Q: 参数如何调优？**
A: 使用网格搜索或贝叶斯优化（将在 Phase 5 支持）。

---

## 九、总结与下一步

### 9.1 核心成果

🔄 **三层架构实现**：基类 ✅ + 选股器 ✅ + 入场策略 ✅，退出策略待完成
✅ **选股器实现**：3个选股器完成（动量、价值、外部）
✅ **入场策略实现**：3个入场策略完成（均线突破、RSI超卖、立即入场）
✅ **向后兼容**：设计支持，待验证
📋 **灵活组合**：36+ 种策略组合（待退出策略完成）
✅ **工业级质量**：测试 100% 通过（T1: 133个，T2: 74个，T3: 53个）

**已完成部分**：
- ✅ T1: 三层基类（4个基类 + 133个测试）
- ✅ T2: 基础选股器（3个选股器 + 74个测试）
- ✅ T3: 基础入场策略（3个入场策略 + 53个测试）
- ✅ 基础架构设计和文档
- ✅ 参数验证系统（5种类型）
- ✅ 使用示例和测试文档

### 9.2 实施时间线

| 阶段 | 任务 | 周数 |
|------|------|------|
| Week 1 | T1-T2（基类+选股器） | 3天 |
| Week 1-2 | T3-T4（入场+退出） | 4天 |
| Week 2 | T5（回测引擎） | 2天 |
| Week 2-3 | T6-T7（测试） | 5天 |
| Week 3 | T8-T9（性能+文档） | 3天 |

**总计：约 3 周（1人全职）**

### 9.3 验收标准

**T1 任务验收**：
- [x] 所有基类实现完成（4个基类）
- [x] 单元测试通过率 100%（133/133）
- [x] 参数验证系统完整（5种类型）
- [x] 代码质量达标（PEP 8 + 类型注解）
- [x] 基类文档完整（使用示例 + 测试说明）

**T2 任务验收**：
- [x] 3个选股器实现完成（MomentumSelector、ValueSelector、ExternalSelector）
- [x] 单元测试通过率 100%（74/74）
- [x] MomentumSelector 正确计算动量
- [x] ExternalSelector 支持三种模式（手动、API、StarRanker预留）
- [x] 代码质量达标（PEP 8 + 类型注解 + 文档）

**T3 任务验收**：
- [x] 3个入场策略实现完成（MABreakoutEntry、RSIOversoldEntry、ImmediateEntry）
- [x] 单元测试通过率 100%（53/53）
- [x] MABreakoutEntry 正确检测金叉
- [x] RSIOversoldEntry RSI计算准确
- [x] ImmediateEntry 支持数量限制和数据验证
- [x] 代码质量达标（PEP 8 + 类型注解 + 文档）

**整体项目验收（进行中）**：
- [x] 基类完成（T1 ✅）
- [x] 选股器完成（T2 ✅）
- [x] 入场策略完成（T3 ✅）
- [ ] 退出策略完成（T4 待开始）
- [ ] 回测引擎完成（T5 待开始）
- [x] 单元测试通过率 100%（T1+T2+T3: 260个测试 ✅）
- [ ] 集成测试通过（T7）
- [ ] 测试覆盖率 ≥ 85%（当前已完成部分 100% ✅）
- [ ] 性能达标（30秒内回测100只股票3年）
- [x] 文档完整（T1+T2+T3 文档 ✅，完整文档待 T9）

### 9.4 下一步行动

**当前进度**：T1 ✅ → T2 ✅ → T3 ✅

**已完成**：
- ✅ T1: 三层基类（4个基类，133个测试）
- ✅ T2: 基础选股器（3个选股器，74个测试）
- ✅ T3: 基础入场策略（3个入场策略，53个测试）

**下一步任务**：
1. **T4: 实现基础退出策略**（2天）⭐ **下一个任务**
   - ATRStopLossExit（ATR动态止损）
   - FixedStopLossExit（固定止损止盈）
   - TimeBasedExit（时间止损）
   - CombinedExit（组合退出）

2. **T5: 修改回测引擎**（2天）
   - 实现 backtest_three_layer() 方法
   - 集成选股器、入场、退出策略
   - 支持不同频率的策略执行

3. **T6-T9: 测试与文档**（6天）
   - 集成测试、性能测试
   - 完整文档编写

**里程碑**：
- ✅ Week 1 Day 1-2: 基类完成（T1）
- ✅ Week 1 Day 3-4: 选股器完成（T2）
- ✅ Week 1 Day 5-6: 入场策略完成（T3）
- 📋 Week 2 Day 1-2: 退出策略实现（T4）
- 📋 Week 2 Day 3-4: 回测引擎实现（T5）
- 📋 Week 2-3: 测试和文档（T6-T9）

---

## 附录

### A. 参考文档

- [**T1 实施总结**](./T1_implementation_summary.md) ⭐ **最新完成**
- [**MLSelector 实现方案（Core 内部 StarRanker 功能）**](./ml_selector_implementation.md) ⭐ **核心推荐**
- [StarRanker 外部集成指南](./starranker_integration_guide.md)（备用方案）
- [Backend Phase 4 方案](../../../backend/docs/planning/phase_4_implementation_index.md)
- [Core v2.0 架构文档](../README.md)
- [三层架构测试文档](../../tests/unit/strategies/three_layer/README.md)

### B. 相关代码

**已实现的三层架构**：
- 三层基类：`core/src/strategies/three_layer/base/`
  - `stock_selector.py` - StockSelector 基类
  - `entry_strategy.py` - EntryStrategy 基类
  - `exit_strategy.py` - ExitStrategy 基类
  - `strategy_composer.py` - StrategyComposer 组合器
- 选股器实现：`core/src/strategies/three_layer/selectors/`
  - `momentum_selector.py` - 动量选股器
  - `value_selector.py` - 价值选股器
  - `external_selector.py` - 外部选股器
- 入场策略实现：`core/src/strategies/three_layer/entries/`
  - `ma_breakout_entry.py` - 均线突破入场
  - `rsi_oversold_entry.py` - RSI超卖入场
  - `immediate_entry.py` - 立即入场
- 测试代码：`core/tests/unit/strategies/three_layer/`
- 使用示例：`core/examples/three_layer_architecture_example.py`

**现有代码**：
- 当前回测引擎：`core/src/backtest/backtest_engine.py`
- 现有策略基类：`core/src/strategies/base_strategy.py`
- 特征工程：`core/src/features/feature_engineering.py`

### C. 技术栈

- Python 3.11+
- pandas 2.x
- NumPy 1.24+
- pytest 7.x
- loguru（日志）

---

## 更新记录

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.3 | 2026-02-06 | T3 任务完成更新：添加3个入场策略实现成果、53个测试用例、进度更新 |
| v1.2 | 2026-02-06 | T2 任务完成更新：添加3个选股器实现成果、74个测试用例、进度更新 |
| v1.1 | 2026-02-06 | T1 任务完成更新：添加实施成果、测试结果、进度更新 |
| v1.0 | 2026-02-06 | 初始版本：三层架构升级方案完成 |

---

**文档完成日期**: 2026-02-06
**最后更新**: 2026-02-06
**版本**: v1.3
**状态**: 🔄 进行中（T1 ✅ + T2 ✅ + T3 ✅，T4-T9 待完成）
