# Stock-Analysis Core 系统指南

**文档版本**: v5.1.0
**最后更新**: 2026-02-07
**项目状态**: 🎯 架构设计完成 + ML 系统完整文档

---

## 📋 目录

- [项目概述](#-项目概述)
- [快速开始](#-快速开始)
- [核心架构](#-核心架构)
- [使用示例](#-使用示例)
- [文档导航](#-文档导航)
- [性能指标](#-性能指标)

---

## 🎯 项目概述

**Stock-Analysis Core** 是一个专业的 A 股量化交易系统核心引擎，提供从数据处理、因子计算、策略执行到回测分析的完整解决方案。

### 核心能力

- ✅ **因子计算**: 125+ Alpha 因子 + 60+ 技术指标
- ✅ **ML 评分工具**: MLStockRanker（类似 BigQuant StockRanker）
- ✅ **策略执行**: 入场/退出策略
- ✅ **回测引擎**: 支持多空交易
- ✅ **风险控制**: 统一风控层
- ✅ **性能分析**: 完整的绩效指标

### 设计原则

1. **职责清晰**: 每个组件职责单一，边界明确
2. **高度解耦**: 组件之间低耦合，可独立测试和替换
3. **灵活组合**: 支持策略自由组合
4. **性能优先**: JIT 编译、向量化计算、并行处理
5. **类型安全**: 完整的类型提示，静态类型检查

---

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/your-org/stock-analysis.git
cd stock-analysis/core

# 安装依赖
pip install -r requirements.txt
```

### 基础回测示例

```python
from core.strategies.entries import MomentumEntry
from core.strategies.exits import TimeBasedExit
from core.risk import RiskManager
from core.backtest import BacktestEngine
from core.data import load_market_data

# Step 1: 准备数据
stock_pool = ['600000.SH', '000001.SZ', '600036.SH']
market_data = load_market_data(
    stock_codes=stock_pool,
    start_date='2023-01-01',
    end_date='2024-12-31'
)

# Step 2: 创建策略
entry_strategy = MomentumEntry(lookback=20, threshold=0.10)
exit_strategy = TimeBasedExit(max_holding_days=20)
risk_manager = RiskManager(
    max_position_loss_pct=0.10,
    max_leverage=1.0
)

# Step 3: 运行回测
engine = BacktestEngine(
    entry_strategy=entry_strategy,
    exit_strategy=exit_strategy,
    risk_manager=risk_manager
)

result = engine.run(
    stock_pool=stock_pool,
    market_data=market_data,
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# Step 4: 分析结果
print(f"总收益率: {result.total_return:.2%}")
print(f"夏普比率: {result.sharpe_ratio:.2f}")
print(f"最大回撤: {result.max_drawdown:.2%}")
```

### ML 策略示例

```python
from core.strategies.entries import MLEntry
from core.ml.model_trainer import ModelTrainer, TrainingConfig

# Step 1: 训练模型
config = TrainingConfig(
    model_type='lightgbm',
    train_start_date='2020-01-01',
    train_end_date='2023-12-31',
    forward_window=5
)

trainer = ModelTrainer(config)
trained_model = trainer.train(stock_pool, market_data)
trained_model.save('models/ml_entry_model.pkl')

# Step 2: 使用 ML 策略回测
entry_strategy = MLEntry(
    model_path='models/ml_entry_model.pkl',
    confidence_threshold=0.7,
    top_long=20,
    top_short=10
)

# ... 运行回测（同上）
```

---

## 🏗️ 核心架构

### 架构总览

```
┌──────────────────────────────────────────────┐
│       Stock-Analysis Core 核心引擎            │
└──────────────────────────────────────────────┘
                    ↓
    ┌───────────────────────────────┐
    │   1. 策略层 (Strategy Layer)   │
    │      - 入场策略 (EntryStrategy) │
    │      - 退出策略 (ExitStrategy)  │
    └───────────────────────────────┘
                    ↓
    ┌───────────────────────────────┐
    │   2. 风控层 (RiskManager)      │
    │      - 止损管理                │
    │      - 风险控制                │
    └───────────────────────────────┘
                    ↓
    ┌───────────────────────────────┐
    │   3. 回测引擎 (BacktestEngine) │
    │      - 协调执行                │
    │      - 交易模拟                │
    └───────────────────────────────┘
                    ↓
    ┌───────────────────────────────┐
    │   4. 组合管理 (Portfolio)      │
    │      - 持仓管理                │
    │      - 盈亏计算                │
    └───────────────────────────────┘
                    ↓
    ┌───────────────────────────────┐
    │   5. 绩效分析 (Performance)    │
    │      - 指标计算                │
    │      - 结果可视化              │
    └───────────────────────────────┘
```

### 核心组件

| 组件 | 职责 | 文档链接 |
|------|------|---------|
| **策略层** | 生成入场/退出信号 | [策略文档](./strategies/README.md) |
| **风控层** | 止损和风险控制 | [风控文档](./risk/README.md) |
| **回测引擎** | 协调执行和交易模拟 | [回测文档](./backtest/README.md) |
| **特征工程** | 因子计算和特征生成 | [特征文档](./features/README.md) |
| **机器学习** | ML 模型训练和预测 | [ML 文档](./ml/README.md) |

---

## 💡 使用示例

### 场景 1: 纯技术指标策略

```python
# 使用动量策略
entry = MomentumEntry(lookback=20, threshold=0.10)
exit_strategy = TimeBasedExit(max_holding_days=20)
risk_manager = RiskManager()

# 运行回测
result = engine.run(stock_pool, market_data, ...)
```

### 场景 2: MLStockRanker 辅助筛选

```python
from core.features.ml_ranker import MLStockRanker

# Step 1: 使用 MLStockRanker 筛选股票池
ranker = MLStockRanker(model_path='models/ranker.pkl')
rankings = ranker.rank(
    stock_pool=all_a_stocks,  # 3000 只
    market_data=market_data,
    date='2024-01-01',
    return_top_n=50
)

# Step 2: 在筛选后的股票池上运行技术指标策略
stock_pool = list(rankings.keys())
entry = MomentumEntry(lookback=20, threshold=0.10)
result = engine.run(stock_pool, market_data, ...)
```

### 场景 3: ML 策略

```python
# 使用 ML 入场策略
entry = MLEntry(
    model_path='models/ml_entry_model.pkl',
    confidence_threshold=0.7
)
exit_strategy = SignalReversalExit(indicator='momentum')

# 运行回测
result = engine.run(stock_pool, market_data, ...)
```

---

## 📚 文档导航

### 核心文档

- **[架构详解](./architecture/overview.md)** - 系统架构和设计理念
- **[机器学习系统](./ml/README.md)** - ML 模型训练和使用
- **[API 参考](./api/reference.md)** - 完整的 API 文档
- **[最佳实践](./guides/best-practices.md)** - 使用建议和最佳实践

### 组件文档

- **[策略系统](./strategies/README.md)** - 入场和退出策略
- **[风控系统](./risk/README.md)** - 风险管理和止损
- **[回测引擎](./backtest/README.md)** - 回测执行和结果分析
- **[特征工程](./features/README.md)** - 因子��算和特征生成
- **[数据模型](./models/README.md)** - 核心数据结构

### 开发指南

- **[快速开始](./guides/quick-start.md)** - 快速入门指南
- **[开发环境设置](./guides/development-setup.md)** - 开发环境配置
- **[测试指南](./guides/testing.md)** - 单元测试和集成测试
- **[贡献指南](./guides/contributing.md)** - 如何贡献代码

---

## ⚡ 性能指标

### 回测性能

| 场景 | 股票数 | 日期数 | 耗时 | 性能 |
|------|--------|--------|------|------|
| 纯技术指标 | 50 | 250 | <5s | ✅ 优秀 |
| 使用 MLStockRanker | 50 | 250 | <8s | ✅ 良好 |
| ML 策略 | 50 | 250 | <15s | ✅ 可接受 |

### MLStockRanker 性能

| 操作 | 股票数 | 特征数 | 耗时 | 性能 |
|------|--------|--------|------|------|
| 评分 | 3000 | 125 | <2s | ✅ 优秀 |
| 评分 | 100 | 125 | <100ms | ✅ 优秀 |
| 评分 | 50 | 10 | <50ms | ✅ 优秀 |

---

## 🔗 相关链接

- **项目主页**: [Stock-Analysis Core](https://github.com/your-org/stock-analysis)
- **问题反馈**: [Issues](https://github.com/your-org/stock-analysis/issues)
- **API 文档**: [Sphinx Docs](../sphinx/build/html/index.html)
- **更新日志**: [CHANGELOG.md](./CHANGELOG.md)

---

## 📄 许可证

MIT License

---

**文档版本**: v5.1.0
**最后更新**: 2026-02-07
**更新内容**: 重构文档结构，将架构和 ML 系统细节分离到独立文档
**维护团队**: Quant Team
