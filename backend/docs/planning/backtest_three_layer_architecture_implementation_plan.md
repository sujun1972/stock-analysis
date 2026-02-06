# Backend 回测三层架构实施方案

> **版本**: v1.0
> **日期**: 2026-02-06
> **作者**: Claude Code
> **项目**: Stock Analysis Platform - Backend
> **依据文档**: `/docs/frontend-backtest-improvement-plan.md`
> **项目状态**: Phase 0-3 已完成，当前为 Phase 4 规划

---

## 📋 目录

- [一、项目背景与目标](#一项目背景与目标)
- [二、架构设计决策](#二架构设计决策)
- [三、详细实施计划](#三详细实施计划)
- [四、技术实现规范](#四技术实现规范)
- [五、API 接口设计](#五api-接口设计)
- [六、数据库设计](#六数据库设计)
- [七、测试策略](#七测试策略)
- [八、工作量评估与排期](#八工作量评估与排期)
- [九、风险管理](#九风险管理)
- [十、部署与监控](#十部署与监控)

---

## 一、项目背景与目标

### 1.1 项目背景

#### 当前 Backend 状态（v2.0）

根据 Phase 0-3 实施总结，Backend 项目已经完成了重大优化：

| 指标 | 优化前 (v1.0) | 当前状态 (v2.0) | 改进幅度 |
|------|--------------|----------------|---------|
| **代码行数** | 17,737 行 | 3,000 行 | ↓ 83% |
| **测试覆盖率** | 0% | 65%+ | ↑ 65% |
| **API 响应时间** | 586ms | 268ms | ↓ 54% |
| **并发处理能力** | 260 QPS | 850 QPS | ↑ 3.3x |
| **生产就绪度** | 6/10 | 9.5/10 | ↑ 58% |

**当前架构特点**：
- ✅ 基于 Core Adapters 模式（零业务逻辑重复）
- ✅ 异步架构（asyncpg + asyncio）
- ✅ Redis 缓存（88% 命中率）
- ✅ 完整的监控和限流机制

**现有策略系统**：
- 2 个已生产化策略：`ComplexIndicatorStrategy`, `MLModelStrategy`
- 基于抽象基类 `BaseStrategy` 的扩展机制
- 完整的参数定义和验证系统

#### 前端改进计划的核心需求

前端计划引入**三层分离架构**（参考 Zipline Pipeline 设计）：

```
Layer 1: 股票选择器 (StockSelector)
         ↓
Layer 2: 入场策略 (EntryStrategy)
         ↓
Layer 3: 退出策略 (ExitStrategy)
```

**核心价值**：
1. **解耦选股和交易**：支持 StarRanker 等外部选股系统
2. **模块化复用**：买入和卖出策略独立配置
3. **策略组合灵活性**：3选股 × 3入场 × 3退出 = 27种组合
4. **符合行业最佳实践**：Backtrader、Zipline、聚宽等主流平台均采用此架构

### 1.2 项目目标

#### 核心目标

1. **实现三层分离架构**
   - 设计并实现 `StockSelector`、`EntryStrategy`、`ExitStrategy` 基类
   - 提供至少 3 个选股器、3 个入场策略、4 个退出策略的实现
   - 实现策略组合器 `StrategyComposer`

2. **扩展策略库**
   - 将 Core 项目的 3 个策略（Momentum、MeanReversion、MultiFactor）迁移到 Backend
   - 将现有 2 个策略适配到三层架构

3. **增强回测引擎**
   - 修改 `BacktestAdapter` 支持三层架构回测
   - 保留现有单股回测功能（向后兼容）
   - 新增策略组合回测功能

4. **提供完整 API 支持**
   - 新增三层架构专用端点（/api/three-layer-strategy）
   - 保持现有 API 向后兼容
   - 提供策略元数据查询和验证接口

#### 非功能性目标

| 目标 | 指标 | 当前值 | 目标值 |
|------|------|--------|--------|
| **测试覆盖率** | 单元测试 + 集成测试 | 65% | 75% |
| **API 响应时间** | P95 延迟 | <80ms | <100ms |
| **并发处理能力** | QPS | 850 | 800+ (保持) |
| **代码行数增长** | 新增代码 | - | <2000 行 |
| **文档完整性** | API 文档 + 开发指南 | 90% | 100% |

### 1.3 项目范围

#### 包含内容 (In Scope)

- ✅ 三层架构基础类设计与实现
- ✅ 10 个基础策略模块实现
- ✅ 回测引擎适配与增强
- ✅ REST API 端点开发
- ✅ 数据库 Schema 扩展（策略配置持久化）
- ✅ 单元测试和集成测试
- ✅ 完整技术文档

#### 不包含内容 (Out of Scope)

- ❌ 前端页面开发（由前端团队负责）
- ❌ AI 策略生成功能（Phase 5 规划）
- ❌ 历史记录持久化（前端 Phase 2 任务）
- ❌ WebSocket 实时推送（Phase 4 可选特性）
- ❌ 策略性能排行榜（未来特性）

---

## 二、架构设计决策

### 2.1 为什么采用三层分离架构？

#### 行业最佳实践验证

| 平台 | 架构模式 | 核心设计理念 |
|------|---------|-------------|
| **Zipline** | Pipeline + Algorithm | "将 alpha 因子计算与交易订单的下达和执行分离开来" |
| **Backtrader** | 外部调仓表 | "因子研究与回测执行解耦，研究人员专注因子研究" |
| **聚宽** | 选股 + 择时分离 | "支持因子选股 + 技术指标择时的分离策略" |
| **米筐** | 三阶段架构 | "选股池 → 盘前选股 → 盘中交易信号" |

#### 解决的核心问题

**问题 1：当前架构无法应用外部选股结果**

```python
# ❌ 当前无法实现
starranker_stocks = ["600000.SH", "000001.SZ", ...]  # StarRanker选出的10只股票
my_strategy.backtest(stock_pool=starranker_stocks)   # 不支持！

# ✅ 三层架构可以实现
strategy = StrategyComposer(
    selector=ExternalSelector(source="starranker"),
    entry=MABreakoutEntry(short=5, long=20),
    exit=ATRStopLossExit(atr_multiplier=2.0)
)
strategy.backtest(...)
```

**问题 2：买卖逻辑高度耦合**

```python
# ❌ 当前架构：买入和卖出使用相同参数
strategy = ComplexIndicatorStrategy(
    ma_period=20,
    rsi_oversold=30,
    rsi_overbought=70  # 买入和卖出共用RSI参数
)

# ✅ 三层架构：独立配置
strategy = StrategyComposer(
    entry=RSIOversoldEntry(rsi_period=14, oversold=30),
    exit=CombinedExit([
        ATRStopLossExit(atr_multiplier=2.0),  # 动态止损
        TimeBasedExit(holding_period=5)        # 时间止损
    ])
)
```

**问题 3：策略组合灵活性不足**

```
当前架构：需要编写 N 个完整策略
三层架构：只需编写 N 个模块，自由组合

3 选股器 × 3 入场策略 × 3 退出策略 = 27 种组合
耦合架构：需要 27 个完整策略类
分离架构：只需 9 个模块
```

### 2.2 架构设计总览

#### 三层架构概念模型

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
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: 入场策�� (EntryStrategy)                        │
├─────────────────────────────────────────────────────────┤
│  职责：决定何时买入（在选股器选出的股票中）                │
│  频率：日频/分钟频                                         │
│  输入：候选股票、价格数据、日期                            │
│  输出：{股票代码: 买入权重} 字典                          │
│                                                           │
│  实现示例：                                               │
│  - MABreakoutEntry（均线突破）                           │
│  - RSIOversoldEntry（RSI超卖）                          │
│  - ImmediateEntry（立即入场，用于测试）                   │
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

#### 与现有架构的关系

```
┌────────────────────────────────────────────────────────┐
│  现有架构 (v2.0) - 保持不变                              │
├────────────────────────────────────────────────────────┤
│                                                          │
│  BaseStrategy (抽象基类)                                │
│  ├── ComplexIndicatorStrategy                          │
│  └── MLModelStrategy                                   │
│                                                          │
│  适用场景：                                              │
│  - 单股回测                                             │
│  - 一体化策略（选股+交易一体）                           │
│  - 简单快速的策略测试                                    │
└────────────────────────────────────────────────────────┘
                           ↓ 共存
┌────────────────────────────────────────────────────────┐
│  三层架构 (v2.1 新增) - Phase 4                         │
├────────────────────────────────────────────────────────┤
│                                                          │
│  三层基类：                                              │
│  - StockSelector (抽象基类)                            │
│  - EntryStrategy (抽象基类)                            │
│  - ExitStrategy (抽象基类)                             │
│                                                          │
│  StrategyComposer（组合器）                             │
│                                                          │
│  适用场景：                                              │
│  - 多股组合回测                                         │
│  - 外部选股系统集成                                      │
│  - 复杂策略组合测试                                      │
│  - 独立的买卖和风控逻辑                                  │
└────────────────────────────────────────────────────────┘

关键设计决策：
✅ 两套架构共存（不删除现有代码）
✅ 不同使用场景，互不冲突
✅ API 层自动路由到合适的架构
```

#### 数据流示意图

```
用户请求
    ↓
FastAPI 端点
    ↓
┌─────────────────────────────────────────┐
│ 路由判断                                 │
├─────────────────────────────────────────┤
│ if 单股回测 且 一体化策略:               │
│     → BacktestAdapter (现有架构)        │
│                                          │
│ if 多股回测 或 三层组合:                 │
│     → ThreeLayerBacktestAdapter (新)   │
└─────────────────────────────────────────┘
           ↓                    ↓
    BacktestAdapter    ThreeLayerBacktestAdapter
           ↓                    ↓
      Core 引擎          StrategyComposer
           ↓                    ↓
       计算结果              回测结果
           ↓                    ↓
    格式化 + 缓存         格式化 + 缓存
           ↓                    ↓
        返回 JSON
```

### 2.3 关键技术决策

#### 决策 1：不破坏现有架构

**原因**：
- 现有 2 个策略已在生产环境使用
- v2.0 架构已经过优化，性能优秀（850 QPS）
- 测试覆盖率 65%，不应丢弃

**方案**：
- 新增三层架构模块，与现有架构并行
- 在 `app/strategies/` 下创建子目录 `three_layer/`
- 提供独立的 API 端点 `/api/three-layer-strategy`

#### 决策 2：延续 Core Adapters 模式

**原因**：
- Phase 0-3 验证了 Core Adapters 的有效性
- 避免重复实现业务逻辑
- 保持代码精简（<5000 行目标）

**方案**：
- 回测逻辑仍委托给 Core 项目（如果 Core 支持）
- Backend 只负责参数适配和格式转换
- 如 Core 不支持三层架构，则在 Backend 实现轻量级回测循环

#### 决策 3：数据库持久化策略

**需要持久化的数据**：
1. ❌ **不持久化**：三层策略的组合配置（前端管理）
2. ✅ **持久化**：回测历史记录（用户需要跨会话访问）
3. ✅ **持久化**：策略模板（用户保存的常用组合）

**理由**：
- 三层架构的核心是灵活性，不应强制持久化所有组合
- 回测历史需要持久化以支持前端"我的回测"页面
- 策略模板是高频使用功能，需要持久化

#### 决策 4：性能优化策略

| 优化点 | 方案 | 预期效果 |
|--------|------|---------|
| **选股频率控制** | 支持配置 rebalance_freq（W/M） | 减少选股计算 70% |
| **缓存选股结果** | Redis 缓存选股器输出（TTL=1天） | 命中率 60%+ |
| **并行回测** | 支持多策略并行回测（复用现有） | 吞吐量提升 3x |
| **异步架构** | 所有 I/O 操作异步化 | 响应时间保持 <100ms |

---

## 三、详细实施计划

### 3.1 Phase 4.0：三层架构基础（P0 - 最高优先级）

#### 任务 4.0.1：创建三层基类

**目标**：定义三层分离架构的抽象基类

**工作量**：3 天

**文件结构**：
```
backend/app/strategies/three_layer/
├── __init__.py
├── base/
│   ├── __init__.py
│   ├── stock_selector.py       # StockSelector 基类
│   ├── entry_strategy.py       # EntryStrategy 基类
│   ├── exit_strategy.py        # ExitStrategy 基类
│   └── strategy_composer.py    # StrategyComposer 组合器
├── selectors/
│   └── __init__.py
├── entries/
│   └── __init__.py
└── exits/
    └── __init__.py
```

**实施步骤**：

**Step 1：创建目录结构**
```bash
mkdir -p backend/app/strategies/three_layer/{base,selectors,entries,exits}
touch backend/app/strategies/three_layer/__init__.py
touch backend/app/strategies/three_layer/base/{__init__.py,stock_selector.py,entry_strategy.py,exit_strategy.py,strategy_composer.py}
touch backend/app/strategies/three_layer/{selectors,entries,exits}/__init__.py
```

**Step 2：实现 StockSelector 基类**

文件：`backend/app/strategies/three_layer/base/stock_selector.py`

```python
"""
股票选择器基类
职责：从全市场筛选出候选股票池
"""

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
    step: Optional[float] = None
    options: Optional[List[Dict]] = None
    description: str = ""
    category: str = "general"


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
            @property
            def name(self):
                return "动量选股器"

            def select(self, date, market_data):
                momentum = market_data.pct_change(20)
                return momentum.loc[date].nlargest(50).index.tolist()
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        初始化选股器

        参数:
            params: 参数字典，键为参数名，值为参数值
        """
        self.params = params or {}
        self._validate_params()

    @property
    @abstractmethod
    def name(self) -> str:
        """选股器名称（中文）"""
        pass

    @property
    @abstractmethod
    def id(self) -> str:
        """选股器ID（英文，唯一标识）"""
        pass

    @property
    def description(self) -> str:
        """选股器描述"""
        return ""

    @property
    def version(self) -> str:
        """版本号"""
        return "1.0.0"

    @classmethod
    @abstractmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        """
        获取参数定义列表

        返回:
            参数定义列表
        """
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
            market_data: 全市场数据，DataFrame格式
                        索引: 日期 (DatetimeIndex)
                        列: 股票代码 (str)
                        值: 收盘价 (float)

        返回:
            选出的股票代码列表，例如 ['600000.SH', '000001.SZ', ...]

        注意事项:
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
            if param_def.type == "float" and not isinstance(
                param_value, (int, float)
            ):
                raise ValueError(f"参数 {param_name} 必须是数值")
            if param_def.type == "boolean" and not isinstance(param_value, bool):
                raise ValueError(f"参数 {param_name} 必须是布尔值")

            # 范围验证
            if param_def.type in ["integer", "float"]:
                if (
                    param_def.min_value is not None
                    and param_value < param_def.min_value
                ):
                    raise ValueError(
                        f"参数 {param_name} 不能小于 {param_def.min_value}"
                    )
                if (
                    param_def.max_value is not None
                    and param_value > param_def.max_value
                ):
                    raise ValueError(
                        f"参数 {param_name} 不能大于 {param_def.max_value}"
                    )

    def get_metadata(self) -> Dict[str, Any]:
        """获取选股器元数据"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": [
                {
                    "name": p.name,
                    "label": p.label,
                    "type": p.type,
                    "default": p.default,
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                    "step": p.step,
                    "options": p.options,
                    "description": p.description,
                    "category": p.category,
                }
                for p in self.get_parameters()
            ],
        }
```

**Step 3：实现 EntryStrategy 基类**

文件：`backend/app/strategies/three_layer/base/entry_strategy.py`

```python
"""
入场策略基类
职责：决定何时买入（在选股器选出的股票中）
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import pandas as pd

from .stock_selector import SelectorParameter  # 复用参数定义类


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

    @property
    def description(self) -> str:
        """策略描述"""
        return ""

    @property
    def version(self) -> str:
        return "1.0.0"

    @classmethod
    @abstractmethod
    def get_parameters(cls) -> List[SelectorParameter]:
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
                  索引为日期
            date: 当前日期

        返回:
            {股票代码: 买入权重} 字典
            例如: {'600000.SH': 0.3, '000001.SZ': 0.2}
            表示给 600000.SH 分配 30% 仓位，给 000001.SZ 分配 20% 仓位

        注意事项:
            - 只对有买入信号的股票返回权重
            - 如果当日无买入信号，返回空字典 {}
            - 权重可以不归一化，回测引擎会自动处理
        """
        pass

    def _validate_params(self):
        """验证参数"""
        param_defs = {p.name: p for p in self.get_parameters()}
        for param_name, param_value in self.params.items():
            if param_name not in param_defs:
                raise ValueError(f"未知参数: {param_name}")

    def get_metadata(self) -> Dict[str, Any]:
        """获取策略元数据"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": [
                {
                    "name": p.name,
                    "label": p.label,
                    "type": p.type,
                    "default": p.default,
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                    "step": p.step,
                    "options": p.options,
                    "description": p.description,
                    "category": p.category,
                }
                for p in self.get_parameters()
            ],
        }
```

**Step 4：实现 ExitStrategy 基类**

文件：`backend/app/strategies/three_layer/base/exit_strategy.py`

```python
"""
退出策略基类
职责：决定何时卖出（持仓管理）
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from .stock_selector import SelectorParameter


@dataclass
class Position:
    """持仓信息"""

    stock_code: str  # 股票代码
    entry_date: pd.Timestamp  # 入场日期
    entry_price: float  # 入场价格
    shares: int  # 持仓数量
    current_price: float  # 当前价格
    unrealized_pnl: float  # 未实现盈亏
    unrealized_pnl_pct: float  # 未实现盈亏比例


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

    @property
    def description(self) -> str:
        """策略描述"""
        return ""

    @property
    def version(self) -> str:
        return "1.0.0"

    @classmethod
    @abstractmethod
    def get_parameters(cls) -> List[SelectorParameter]:
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

        注意事项:
            - 只返回需要卖出的股票代码
            - 如果当日无卖出信号，返回空列表 []
            - 回测引擎会以当日收盘价执行卖出
        """
        pass

    def _validate_params(self):
        """验证参数"""
        param_defs = {p.name: p for p in self.get_parameters()}
        for param_name, param_value in self.params.items():
            if param_name not in param_defs:
                raise ValueError(f"未知参数: {param_name}")

    def get_metadata(self) -> Dict[str, Any]:
        """获取策略元数据"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "parameters": [
                {
                    "name": p.name,
                    "label": p.label,
                    "type": p.type,
                    "default": p.default,
                    "min_value": p.min_value,
                    "max_value": p.max_value,
                    "step": p.step,
                    "options": p.options,
                    "description": p.description,
                    "category": p.category,
                }
                for p in self.get_parameters()
            ],
        }
```

**Step 5：实现 StrategyComposer 组合器**

文件：`backend/app/strategies/three_layer/base/strategy_composer.py`

```python
"""
三层策略组合器
职责：组合选股器、入场策略、退出策略，执行回测
"""

from typing import Any, Dict

from .entry_strategy import EntryStrategy
from .exit_strategy import ExitStrategy
from .stock_selector import StockSelector


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

        metadata = composer.get_metadata()
        # 返回完整的策略组合元数据
    """

    def __init__(
        self,
        selector: StockSelector,
        entry: EntryStrategy,
        exit: ExitStrategy,
        rebalance_freq: str = "W",
    ):
        """
        初始化策略组合器

        参数:
            selector: 选股器实例
            entry: 入场策略实例
            exit: 退出策略实例
            rebalance_freq: 选股频率（D=日, W=周, M=月）
        """
        self.selector = selector
        self.entry = entry
        self.exit = exit
        self.rebalance_freq = rebalance_freq

    def get_metadata(self) -> Dict[str, Any]:
        """获取组合策略完整元数据"""
        return {
            "selector": self.selector.get_metadata(),
            "entry": self.entry.get_metadata(),
            "exit": self.exit.get_metadata(),
            "rebalance_freq": self.rebalance_freq,
            "rebalance_freq_label": {
                "D": "每日",
                "W": "每周",
                "M": "每月",
            }.get(self.rebalance_freq, "未知"),
        }

    def validate(self) -> Dict[str, Any]:
        """
        验证策略组合的有效性

        返回:
            {
                'valid': bool,
                'errors': List[str]
            }
        """
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

**验收标准**：
- ✅ 4 个基类文件创建完成
- ✅ 所有抽象方法定义清晰
- ✅ 参数验证机制完整
- ✅ 元数据获取方法实现
- ✅ 代码通过 `black` 和 `flake8` 检查

---

#### 任务 4.0.2：实现基础选股器

**目标**：实现 3 个基础选股器

**工作量**：3 天

**实施清单**：

| 选股器 | 文件名 | 功能描述 | 关键参数 |
|--------|--------|---------|---------|
| **MomentumSelector** | `selectors/momentum_selector.py` | 动量选股：选择近期涨幅最大的股票 | lookback_period, top_n, use_log_return |
| **ValueSelector** | `selectors/value_selector.py` | 价值选股：选择低 PE/PB 的股票（简化实现） | metric, top_n |
| **ExternalSelector** | `selectors/external_selector.py` | 外部选股：支持 StarRanker 等外部系统 | source, api_endpoint, manual_stocks |

**实施详情**：

**MomentumSelector 实现**：

文件：`backend/app/strategies/three_layer/selectors/momentum_selector.py`

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
    - 中短期交易

    注意事项：
    - 动量策略在震荡市可能失效
    - 建议配合止损策略使用
    """

    @property
    def id(self) -> str:
        return "momentum"

    @property
    def name(self) -> str:
        return "动量选股器"

    @property
    def description(self) -> str:
        return "选择近期涨幅最大的股票，适用于趋势跟踪策略"

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
                step=5,
                description="计算过去 N 日收益率作为动量指标",
                category="核心参数",
            ),
            SelectorParameter(
                name="top_n",
                label="选股数量",
                type="integer",
                default=50,
                min_value=5,
                max_value=200,
                step=5,
                description="选择动量最高的前 N 只股票",
                category="核心参数",
            ),
            SelectorParameter(
                name="use_log_return",
                label="使用对数收益率",
                type="boolean",
                default=False,
                description="True=对数收益率（适合长期），False=简单收益率（适合短期）",
                category="高级选项",
            ),
            SelectorParameter(
                name="filter_negative",
                label="过滤负动量",
                type="boolean",
                default=True,
                description="是否过滤掉负动量（下跌）的股票",
                category="高级选项",
            ),
        ]

    def select(
        self, date: pd.Timestamp, market_data: pd.DataFrame
    ) -> List[str]:
        """
        动量选股逻辑

        参数:
            date: 选股日期
            market_data: DataFrame(index=日期, columns=股票代码, values=收盘价)

        返回:
            选出的股票代码列表
        """
        lookback = self.params.get("lookback_period", 20)
        top_n = self.params.get("top_n", 50)
        use_log = self.params.get("use_log_return", False)
        filter_negative = self.params.get("filter_negative", True)

        logger.debug(
            f"动量选股: date={date}, lookback={lookback}, top_n={top_n}"
        )

        # 计算动量（收益率）
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

        logger.info(
            f"动量选股完成: 共选出 {len(selected_stocks)} 只股票"
        )

        return selected_stocks
```

**ExternalSelector 实现**（关键功能）：

文件：`backend/app/strategies/three_layer/selectors/external_selector.py`

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
    2. 自定义 API 模式：从用户指定的 API 获取股票列表
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

    @property
    def description(self) -> str:
        return "支持接入 StarRanker 等外部选股系统，或手动输入股票池"

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
                category="核心参数",
            ),
            SelectorParameter(
                name="api_endpoint",
                label="API地址（仅自定义API模式）",
                type="string",
                default="",
                description="自定义 API 的完整 URL",
                category="API配置",
            ),
            SelectorParameter(
                name="api_timeout",
                label="API超时时间（秒）",
                type="integer",
                default=10,
                min_value=1,
                max_value=60,
                description="API 请求超时时间",
                category="API配置",
            ),
            SelectorParameter(
                name="manual_stocks",
                label="手动股票池（仅手动模式）",
                type="string",
                default="",
                description="逗号分隔的股票代码，如：600000.SH,000001.SZ",
                category="手动配置",
            ),
        ]

    def select(
        self, date: pd.Timestamp, market_data: pd.DataFrame
    ) -> List[str]:
        """
        从外部系统获取股票列表
        """
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
        """从 StarRanker 获取股票列表"""
        # TODO: 集成 StarRanker API（需要与 StarRanker 团队协调）
        logger.warning("StarRanker 集成尚未实现，返回空列表")
        return []

    def _fetch_from_custom_api(
        self, date: pd.Timestamp, api_endpoint: str
    ) -> List[str]:
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

**ValueSelector 实现**（简化版）：

由于 Backend 当前没有基本面数据（PE、PB等），这里提供一个基于价格的简化版实现：

```python
"""
价值选股器（简化版）
基于价格低点选股（真实场景应使用 PE/PB 等基本面指标）
"""

from typing import List

import pandas as pd
from loguru import logger

from ..base.stock_selector import SelectorParameter, StockSelector


class ValueSelector(StockSelector):
    """
    价值选股器（简化版）

    注意：当前实现基于价格相对低点选股
    真实生产环境应使用 PE、PB、PS 等基本面指标
    """

    @property
    def id(self) -> str:
        return "value"

    @property
    def name(self) -> str:
        return "价值选股器（简化版）"

    @property
    def description(self) -> str:
        return "基于价格相对低点选股（生产环境建议使用 PE/PB 指标）"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="lookback_period",
                label="价格对比周期（天）",
                type="integer",
                default=252,  # 一年
                min_value=60,
                max_value=500,
                description="计算价格在过去 N 日中的相对位置",
                category="核心参数",
            ),
            SelectorParameter(
                name="top_n",
                label="选股数量",
                type="integer",
                default=50,
                min_value=5,
                max_value=200,
                description="选择价格相对位置最低的前 N 只股票",
                category="核心参数",
            ),
        ]

    def select(
        self, date: pd.Timestamp, market_data: pd.DataFrame
    ) -> List[str]:
        """
        价值选股逻辑（基于价格相对位置）
        """
        lookback = self.params.get("lookback_period", 252)
        top_n = self.params.get("top_n", 50)

        # 计算价格在过去 N 日中的相对位置（0-1）
        rolling_window = market_data.rolling(window=lookback)
        price_percentile = (
            market_data - rolling_window.min()
        ) / (rolling_window.max() - rolling_window.min())

        try:
            current_percentile = price_percentile.loc[date].dropna()
        except KeyError:
            logger.warning(f"日期 {date} 不在数据范围内")
            return []

        # 选择价格相对位置最低的股票（"便宜"的股票）
        selected_stocks = current_percentile.nsmallest(top_n).index.tolist()

        logger.info(f"价值选股完成: 共选出 {len(selected_stocks)} 只股票")

        return selected_stocks
```

**验收标准**：
- ✅ 3 个选股器实现完成
- ✅ MomentumSelector 支持对数/简单收益率
- ✅ ExternalSelector 支持三种模式（StarRanker、自定义API、手动）
- ✅ ValueSelector 提供基础实现和改进建议
- ✅ 所有选股器通过单元测试

---

*(由于篇幅限制，文档继续...)*

### 继续完成任务 4.0.3 到 4.0.6...

由于文档篇幅较大，我将继续生成剩余的核心内容：

- 任务 4.0.3：实现基础入场策略（3个）
- 任务 4.0.4：实现基础退出策略（4个）
- 任务 4.0.5：实现三层回测适配器
- 任务 4.0.6：创建 REST API 端点

以及后续的：
- Phase 4.1：策略库扩展
- Phase 4.2：测试与文档
- 详细的技术实现规范
- API 接口设计
- 数据库设计
- 测试策略
- 工作量评估

请确认是否继续生成完整文档？文档预计总长度约 **8000-10000 行**。

或者您希望：
1. 先生成概要版本（2000 行左右）
2. 分多个文件生成（按 Phase 分文件）
3. 继续生成当前文件直到完成
