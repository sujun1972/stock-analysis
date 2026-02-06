# Core v3.0 三层架构升级项目

> **重大版本升级**: Core v2.x → v3.0（架构重构）
> **发布日期**: 2026-02-06
> **项目状态**: 📋 规划完成，待实施

---

## 📚 项目文档

### 主要文档

| 文档 | 描述 | 状态 |
|------|------|------|
| [**项目状态总结**](../architecture/PROJECT_STATUS.md) ⭐ | 项目当前状态、核心成果、技术架构、后续规划 | ✅ 最新 |
| [**2026 年度路线图**](../architecture/roadmap_2026.md) | 季度规划、里程碑、Q1 完成总结 | ✅ 最新 |
| [**技术债务追踪**](./tech_debt.md) | 待优化项和改进计划 | ✅ 维护中 |
| [**StarRanker 外部集成指南**](./starranker_integration_guide.md) | 外部选股系统集成详解（备用参考） | ✅ 完成 |

### 快速导航

#### 👨‍💼 决策者视角
- [项目概述](../architecture/PROJECT_STATUS.md#一项目概述)
- [核心成果](../architecture/PROJECT_STATUS.md#二核心成果)
- [当前进度](../architecture/PROJECT_STATUS.md#六当前进度)
- [后续规划](../architecture/PROJECT_STATUS.md#七后续规划)
- [2026 路线图](../architecture/roadmap_2026.md)

#### 👨‍💻 开发者视角
- [技术架构](../architecture/PROJECT_STATUS.md#三技术架构)
- [功能模块](../architecture/PROJECT_STATUS.md#四功能模块)
- [质量指标](../architecture/PROJECT_STATUS.md#五质量指标)
- [MLSelector 机器学习选股](../architecture/PROJECT_STATUS.md#47-mlselector-机器学习选股)

#### 🏗️ 架构师视角
- [六层架构设计](../architecture/PROJECT_STATUS.md#31-六层架构)
- [三层策略架构](../architecture/PROJECT_STATUS.md#32-三层策略架构)
- [技术栈清单](../architecture/PROJECT_STATUS.md#c-技术栈清单)
- [架构演进路径](../architecture/roadmap_2026.md#技术演进路径)

#### 🔧 运维视角
- [性能指标](../architecture/PROJECT_STATUS.md#53-性能指标)
- [质量指标](../architecture/PROJECT_STATUS.md#五质量指标)
- [技术债务](./tech_debt.md)

---

## 🎯 项目概述

### 核心目标

Stock-Analysis Core 是企业级 A 股量化交易系统核心引擎，提供从数据处理到策略回测的完整解决方案。

**核心特性**：
- **125+ Alpha 因子** + **60+ 技术指标**
- **5 种经典交易策略** + **三层架构设计**
- **并行回测引擎** (3-8× 加速)
- **机器学习选股** (MLSelector + LightGBM)
- **企业级质量** (3,200+ 测试用例，90%+ 覆盖率)

### 项目状态

| 维度 | 状态 | 进度 |
|------|------|------|
| **核心功能** | ✅ 完成 | 100% |
| **三层架构** | ✅ 完成 | 100% |
| **MLSelector** | ✅ 完成 | 100% |
| **文档体系** | 🔄 进行中 | 60% |
| **总体进度** | 🎯 生产就绪 | 95% |

---

## 📊 核心指标汇总

| 类别 | 指标 | 数值 |
|------|------|------|
| **代码规模** | Alpha 因子 + 技术指标 | 125+ 个因子 + 60+ 指标 |
| | 策略数量 | 5 种经典 + 10 个三层组件 |
| **测试质量** | 单元测试 | 3,200+ 用例 |
| | 测试覆盖率 | 90%+ |
| **性能指标** | 回测加速 | 3-8× |
| | MLSelector 选股 | <50ms |
| **质量评分** | 代码质量 | 4.9/5.0 |
| | API 一致性 | 95%+ |

---

## 🚀 快速开始

详细使用说明请参考 [PROJECT_STATUS.md](../architecture/PROJECT_STATUS.md)

### 经典策略使用

```python
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

### 三层架构使用

```python
# 🆕 使用三层架构
from core.src.strategies.three_layer import (
    MomentumSelector,
    ImmediateEntry,
    FixedStopLossExit,
    StrategyComposer
)
from core.src.backtest import BacktestEngine

# 组合策略
composer = StrategyComposer(
    selector=MomentumSelector(params={'top_n': 50}),
    entry=ImmediateEntry(),
    exit_strategy=FixedStopLossExit(params={'stop_loss_pct': -5.0}),
    rebalance_freq='W'
)

# 回测
engine = BacktestEngine()
result = engine.backtest_three_layer(
    selector=composer.selector,
    entry=composer.entry,
    exit_strategy=composer.exit,
    prices=prices,
    start_date='2023-01-01',
    end_date='2023-12-31'
)
```

### 3. StarRanker 集成

```python
# 使用 StarRanker 外部选股
from core.src.strategies.three_layer.selectors import ExternalSelector

selector = ExternalSelector(params={
    'source': 'starranker',
    'starranker_config': {
        'mode': 'api',
        'api_endpoint': 'http://starranker-api:8000'
    }
})

# 其余配置与上面相同
composer = StrategyComposer(
    selector=selector,  # 使用 StarRanker 选股
    entry=ImmediateEntry(),
    exit_strategy=FixedStopLossExit(params={'stop_loss_pct': -5.0}),
    rebalance_freq='W'
)
```

更多使用示例请参考 [PROJECT_STATUS.md](../architecture/PROJECT_STATUS.md#47-mlselector-机器学习选股)

---

## 📚 相关文档

### 架构文档
- [项目状态总结](../architecture/PROJECT_STATUS.md) - 项目当前状态、核心成果
- [2026 年度路线图](../architecture/roadmap_2026.md) - 季度规划、里程碑
- [架构总览](../architecture/overview.md) - 系统架构设计
- [设计模式](../architecture/design_patterns.md) - 核心设计模式
- [技术栈](../architecture/tech_stack.md) - 完整技术栈清单
- [性能分析](../architecture/performance.md) - 性能优化方案

### 规划文档
- [技术债务追踪](./tech_debt.md) - 待优化项和改进计划

### 技术参考
- [StarRanker 外部集成指南](./starranker_integration_guide.md) - 外部选股系统集成方案（备用）

---

**最后更新**: 2026-02-06
**文档维护**: Quant Team
**项目状态**: 🎯 生产就绪 (95%)
