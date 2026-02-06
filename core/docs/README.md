# Stock-Analysis Core 文档中心

> **项目版本**: v3.0.0
> **最后更新**: 2026-02-06
> **项目状态**: 🎯 生产就绪 (95%)

---

## 📋 目录

- [项目概述](#-项目概述)
- [快速开始](#-快速开始)
- [核心特性](#-核心特性)
- [技术架构](#-技术架构)
- [文档导航](#-文档导航)
- [质量指标](#-质量指标)
- [开发进度](#-开发进度)
- [后续规划](#-后续规划)

---

## 🎯 项目概述

### 项目简介

**Stock-Analysis Core** 是一个企业级的 A 股量化交易系统核心引擎，提供从数据处理到策略回测的完整解决方案。

### 核心特性

- **125+ Alpha 因子库**: 动量、反转、波动率、成交量、趋势、流动性等 6 大类因子
- **60+ 技术指标**: MA、EMA、RSI、MACD、布林带、ATR、CCI 等 7 大类指标
- **5 种经典交易策略**: 动量、均值回归、网格交易、ML 选股、轮动策略
- **三层架构设计**⭐: 选股层 → 入场层 → 退出层独立解耦，支持 36+ 种策略组合
- **MLSelector 机器学习选股**⭐: 多因子加权 + LightGBM 排序模型
- **并行回测引擎**: 3-8× 加速，支持多进程并行计算
- **企业级质量**: 3,200+ 测试用例，90%+ 覆盖率

### 技术栈

| 层级 | 技术选型 |
|------|---------|
| 数据层 | TimescaleDB (PostgreSQL 时序扩展) |
| 计算层 | NumPy, Pandas, Numba (JIT 加速) |
| 机器学习 | scikit-learn, LightGBM (Ranking⭐) |
| 并行计算 | multiprocessing (3-8× 加速) |
| API 标准 | Response 统一响应 + 异常系统 |
| 测试框架 | pytest (3,200+ 用例, 90%+ 覆盖率) |
| 日志监控 | loguru |

### 项目状态

| 维度 | 状态 | 进度 |
|------|------|------|
| **核心功能** | ✅ 完成 | 100% |
| **三层架构** | ✅ 完成 | 100% |
| **MLSelector** | ✅ 完成 | 100% |
| **文档体系** | ✅ 完成 | 100% |
| **总体进度** | 🎯 生产就绪 | 95% |

---

## 🚀 快速开始

### 新用户路径

1. **了解项目**: 阅读本文档了解项目概况
2. **环境搭建**: 按照 [安装指南](user_guide/installation.md) 完成环境配置
3. **快速上手**: 学习 [快速开始](user_guide/quick_start.md) 30分钟教程
4. **示例学习**: 查看 [示例代码](user_guide/examples/) 学习完整工作流
5. **问题排查**: 遇到问题查阅 [FAQ](user_guide/faq.md)

### 经典策略使用示例

```python
from core.src.strategies import MomentumStrategy
from core.src.backtest import BacktestEngine

# 创建动量策略
strategy = MomentumStrategy(lookback_period=20)
engine = BacktestEngine()

# 运行回测
result = engine.backtest_long_only(
    signals=strategy.generate_signals(prices),
    prices=prices,
    top_n=50
)
```

### 三层架构使用示例⭐

```python
# v3.0 三层架构 - 灵活组合选股、入场、退出策略
from core.src.strategies.three_layer import (
    MLSelector,           # 机器学习选股⭐
    ImmediateEntry,       # 立即入场
    FixedStopLossExit,    # 固定止损退出
    StrategyComposer      # 策略组合器
)
from core.src.backtest import BacktestEngine

# 组合策略: ML选股 + 立即入场 + 固定止损
composer = StrategyComposer(
    selector=MLSelector(params={
        'mode': 'lightgbm_ranker',
        'model_path': './models/stock_ranker.pkl',
        'top_n': 50
    }),
    entry=ImmediateEntry(),
    exit_strategy=FixedStopLossExit(params={'stop_loss_pct': -5.0}),
    rebalance_freq='W'  # 周度调仓
)

# 运行回测
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

**三层架构优势**:
- ✅ 高度解耦: 选股、入场、退出独立开发
- ✅ 灵活组合: 3 选股器 × 3 入场 × 4 退出 = 36+ 种组合
- ✅ 易于扩展: 新增策略只需实现对应接口

---

## 🏗️ 核心特性

### v3.0 核心升级

#### 1. 三层策略架构⭐

将传统策略解耦为三个独立层级：

```
┌─────────────────────────────────────┐
│  选股器层 (StockSelector)            │
│  职责: 从全市场筛选候选股票池         │
│  频率: 周频/月频                     │
│  组件: Momentum, Reversal, MLSelector, External
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  入场策略层 (EntryStrategy)          │
│  职责: 决定何时买入候选股票           │
│  频率: 日频                          │
│  组件: Immediate, MABreakout, RSIOversold
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  退出策略层 (ExitStrategy)           │
│  职责: 管理持仓，决定何时卖出         │
│  频率: 日频/实时                     │
│  组件: FixedPeriod, StopLoss, ATRStop, TrendExit
└─────────────────────────────────────┘
```

#### 2. MLSelector 机器学习选股⭐

**核心特性**:
- ✅ **多因子加权模式**: 支持 4 种归一化方法（z_score、min_max、rank、none）
- ✅ **LightGBM 排序模式**: 5 档智能评分，NDCG@10 优化
- ✅ **因子库集成**: 125+ Alpha 因子 + 60+ 技术指标
- ✅ **通配符特征**: 支持 `alpha:*`、`tech:rsi` 等表达式

**性能指标**:
- 快速模式: <15ms (20 只股票, 3 个因子)
- 完整模式: <700ms (20 只股票, 125+ 因子)
- 训练速度: <5 秒 (1000+ 样本)
- 推理速度: <100ms (100 只股票)

---

## 🏛️ 技术架构

### 六层架构

```
┌──────────────────────────────────────┐
│  Layer 6: API Layer (API接口层)       │
│  REST API / CLI / Response统一响应     │
└────────────────┬─────────────────────┘
                 ↓
┌──────────────────────────────────────┐
│  Layer 5: Risk Layer (风控层)         │
│  风险指标 / 风险预警 / 仓位管理        │
└────────────────┬─────────────────────┘
                 ↓
┌──────────────────────────────────────┐
│  Layer 4: Backtest Layer (回测层)     │
│  并行回测引擎 (3-8× 加速)             │
└────────────────┬─────────────────────┘
                 ↓
┌──────────────────────────────────────┐
│  Layer 3: Strategy Layer (策略层)     │
│  三层架构 / 5种经典策略 / 策略组合器   │
└────────────────┬─────────────────────┘
                 ↓
┌──────────────────────────────────────┐
│  Layer 2: Feature & Model Layer       │
│  125+ Alpha因子 / 60+ 技术指标        │
│  ML模型训练 / MLSelector选股⭐        │
└────────────────┬─────────────────────┘
                 ↓
┌──────────────────────────────────────┐
│  Layer 1: Data Layer (数据层)         │
│  TimescaleDB / 数据清洗 / 质量检查    │
└──────────────────────────────────────┘
```

详见: [架构总览](architecture/overview.md) | [设计模式](architecture/design_patterns.md)

---

## 📚 文档导航

### 📖 用户指南 (User Guide)

快速上手和日常使用指南。

**入门指南**:
- 🚀 [安装指南](user_guide/installation.md) - 环境配置、依赖安装、数据库设置
- 📖 [快速开始](user_guide/quick_start.md) - 30分钟完整教程
- 🔧 [CLI命令指南](user_guide/CLI_GUIDE.md) - 命令行工具详解
- 💡 [示例代码](user_guide/examples/) - 12个完整工作流示例
- ❓ [常见问题](user_guide/faq.md) - FAQ和问题排查

**功能指南**:
- 🎨 [可视化指南](user_guide/VISUALIZATION_GUIDE.md) - 30+图表使用说明
- 🧬 [特征配置指南](user_guide/FEATURE_CONFIG_GUIDE.md) - 因子计算配置
- 🤖 [模型使用指南](user_guide/MODEL_USAGE_GUIDE.md) - 模型训练与评估
- 🔙 [回测使用指南](user_guide/BACKTEST_USAGE_GUIDE.md) - 回测引擎使用
- 📋 [配置模板指南](user_guide/TEMPLATES_GUIDE.md) - 6种配置模板说明

**高级指南**:
- 📊 [数据质量指南](user_guide/DATA_QUALITY_GUIDE.md) - 数据验证与清洗
- 🤝 [模型集成指南](user_guide/ENSEMBLE_GUIDE.md) - 模型集成方法
- 📈 [因子分析指南](user_guide/FACTOR_ANALYSIS_GUIDE.md) - 因子分析工具

---

### 🏗️ 架构文档 (Architecture)

深入了解系统架构设计和技术实现。

- 📋 [项目状态总结](architecture/PROJECT_STATUS.md)⭐ - 当前状态、核心成果、质量指标、后续规划
- 🏛️ [架构总览](architecture/overview.md) - 六层架构、三层策略架构、数据流、目录结构
- 🎨 [设计模式](architecture/design_patterns.md) - 10种设计模式应用（含组合模式⭐）
- ⚡ [性能优化](architecture/performance.md) - 35倍性能提升分析 + MLSelector性能⭐
- 🔧 [技术栈详解](architecture/tech_stack.md) - 完整技术选型说明 + LightGBM Ranking⭐

**v3.0 核心升级** (2026-02-06):
- ✅ 三层策略架构完整文档化
- ✅ MLSelector 机器学习选股详细说明
- ✅ LightGBM Ranking 技术栈详解
- ✅ 组合模式在三层架构中的应用
- ✅ 性能指标全面更新

---

### 👨‍💻 开发指南 (Developer Guide)

为贡献者提供的开发指南。

- 🤝 [贡献指南](developer_guide/contributing.md) - Fork流程、PR规范、代码审查标准
- 🎨 [代码规范](developer_guide/coding_standards.md) - PEP 8、命名规范、类型提示、文档字符串
- 🧪 [测试指南](developer_guide/testing.md) - 如何编写测试、测试哲学、最佳实践
  - 📋 [运行测试](../tests/README.md) - 交互式菜单、测试统计（3,200+测试）
  - 🔗 [集成测试](../tests/integration/README.md) - 端到端工作流测试
  - ⚡ [性能测试](../tests/performance/README.md) - 性能基准测试
- 📚 [API参考文档](sphinx/README.md) - Sphinx自动生成的API文档（197个模块）

---

### 📅 规划与版本 (Planning & Versions)

了解项目发展规划和版本历史。

**规划文档**:
- 🗺️ [开发路线图](ROADMAP.md) - 核心路线图概览（Phase 3 已完成✅）
- 📅 [2026年度规划](planning/roadmap_2026.md) - 年度详细规划（Q1 100%完成）
- ✅ [Phase 3 规划](planning/phase3.md) - 文档与生产化（已完成）
- 🚀 [Phase 4 规划](planning/phase4.md) - 实盘交易系统（规划中）
- 🔧 [技术债务追踪](planning/tech_debt.md) - 技术债务管理

**版本历史**:
- 📄 [完整变更日志](versions/CHANGELOG.md) - 所有版本变更记录
- ⭐ [v3.0.0 发布说明](versions/v3.0.0.md) - 当前版本详情

---

## 📊 质量指标

### 核心指标汇总

| 类别 | 指标 | 数值 | 状态 |
|------|------|------|------|
| **代码规模** | 总代码量 | 50,000+ 行 | ✅ |
| | Alpha 因子 | 125+ 个 | ✅ |
| | 技术指标 | 60+ 个 | ✅ |
| | 策略数量 | 5 经典 + 10 组件 | ✅ |
| **测试质量** | 单元测试 | 3,200+ 用例 | ✅ |
| | 测试覆盖率 | 90%+ | ✅ |
| | 三层架构测试 | 385 用例 | ✅ |
| | MLSelector 测试 | 120+ 用例 | ✅ |
| **性能指标** | 回测加速 | 3-8× | ✅ |
| | MLSelector 选股 | <50ms | ✅ |
| | LightGBM 训练 | <5 秒 | ✅ |
| **质量评分** | 代码质量 | 4.9/5.0 | ✅ |
| | API 一致性 | 95%+ | ✅ |
| | 文档覆盖率 | 99.5% (API) | ✅ |

### 测试覆盖

| 测试类型 | 用例数 | 通过率 | 状态 |
|---------|--------|--------|------|
| 单元测试 | 3,200+ | 100% | ✅ |
| 集成测试 | 50+ | 100% | ✅ |
| 三层架构测试 | 385 | 100% | ✅ |
| MLSelector 测试 | 120+ | 100% | ✅ |
| 性能基准测试 | 20+ | 100% | ✅ |

---

## 📈 开发进度

### 总体进度

**项目完成度**: 95% ✅

```
Phase 1: 核心功能完善      ████████████████ 100% ✅
Phase 2: 深度重构与优化    ████████████████ 100% ✅
Phase 3: 文档与生产化      ████████████████ 100% ✅
三层架构升级              ████████████████ 100% ✅
MLSelector 实现           ████████████████ 100% ✅
```

### 里程碑

| 里程碑 | 计划日期 | 实际日期 | 状态 |
|--------|---------|---------|------|
| Phase 1 完成 | 2026-01-20 | 2026-01-20 | ✅ 按时完成 |
| Phase 2 完成 | 2026-01-31 | 2026-01-31 | ✅ 按时完成 |
| 三层架构完成 | 2026-02-06 | 2026-02-06 | ✅ 按时完成 |
| MLSelector 完成 | 2026-02-06 | 2026-02-06 | ✅ 按时完成 |
| Phase 3 完成 | 2026-02-15 | 2026-02-06 | ✅ 提前完成 |
| 文档站点上线 | 2026-Q2 | - | 📋 规划中 |

### Phase 3: 文档与生产化 ✅ 已完成

**完成时间**: 2026-02-01 ~ 2026-02-06
**完成度**: 100% | **状态**: 🎉 全部完成

**核心交付**:
- ✅ README 简化 (1,369 行 → 412 行, -70%)
- ✅ ARCHITECTURE 精简 (2,389 行 → 739 行, -69%)
- ✅ ROADMAP 重组 (436 行 → <200 行, -54%)
- ✅ Sphinx API 文档生成系统 (99.5% 导入成功率, 197个模块)
- ✅ backtest_engine.py 重构 (1,275 行 → 488 行, -62%)
- ✅ model_trainer.py 优化 (1,135 行 → 1,022 行, -10%)
- ✅ **架构文档完整更新** (overview, tech_stack, performance, design_patterns)
- ✅ **docs 目录完整结构** (用户指南 13 个 + 架构文档 4 个)

---

## 🚀 后续规划

### 短期规划 (2026-Q2)

**主题**: 文档完善 + 代码优化

**核心任务**:
1. **文档生成与部署**
   - GitHub Pages 部署文档站点
   - 用户手册与示例完善
   - 视频教程录制

2. **代码优化（可选）**
   - 大文件拆分优化
   - 代码复杂度降低
   - 性能调优

3. **性能提升（可选）**
   - 分布式计算支持 (Ray/Dask)
   - 特征预计算引擎
   - GPU 加速扩展

**预期成果**:
- 文档站点上线
- API 文档覆盖率 100%

---

### 中期规划 (2026-Q3)

**主题**: 实盘交易系统开发

**核心任务**:
1. 券商接口对接（华泰/中信/国金等）
2. 订单管理系统（OMS）
3. 实时风控引擎
4. 监控告警系统

**预期成果**:
- 支持 3+ 主流券商
- 完整的订单管理系统
- 实时风控与告警
- 模拟盘测试通过

详见: [Phase 4 规划](planning/phase4.md)

---

### 长期规划 (2026-Q4)

**主题**: 生产部署 + 实盘验证

**核心任务**:
1. 实盘测试（小额资金验证）
2. 生产环境部署（高可用架构）
3. 监控系统完善
4. 用户文档与培训

**预期成果**:
- 实盘系统正式上线
- 系统可用性 ≥ 99.9%
- 完整的用户文档
- 稳定的交易业绩

---

## 📂 文档目录结构

```
docs/
├── README.md                      # 📍 本文档 - 文档中心
├── ROADMAP.md                     # 开发路线图
│
├── architecture/                  # 架构详细文档
│   ├── PROJECT_STATUS.md          # 项目状态总结⭐
│   ├── overview.md                # 架构总览（六层架构 + 三层策略）
│   ├── design_patterns.md         # 设计模式（含组合模式⭐）
│   ├── performance.md             # 性能优化（含MLSelector性能⭐）
│   └── tech_stack.md              # 技术栈（含LightGBM Ranking⭐）
│
├── user_guide/                    # 用户指南
│   ├── installation.md            # 安装指南
│   ├── quick_start.md             # 快速开始
│   ├── faq.md                     # 常见问题
│   ├── examples/                  # 示例代码 (12个)
│   ├── BACKTEST_USAGE_GUIDE.md    # 回测使用指南
│   ├── CLI_GUIDE.md               # CLI命令指南
│   ├── DATA_QUALITY_GUIDE.md      # 数据质量指南
│   ├── ENSEMBLE_GUIDE.md          # 模型集成指南
│   ├── FACTOR_ANALYSIS_GUIDE.md   # 因子分析指南
│   ├── FEATURE_CONFIG_GUIDE.md    # 特征配置指南
│   ├── MODEL_USAGE_GUIDE.md       # 模型使用指南
│   ├── TEMPLATES_GUIDE.md         # 配置模板指南
│   └── VISUALIZATION_GUIDE.md     # 可视化指南
│
├── developer_guide/               # 开发指南
│   ├── contributing.md            # 贡献指南
│   ├── coding_standards.md        # 代码规范
│   └── testing.md                 # 测试指南
│
├── sphinx/                        # API 文档
│   ├── README.md                  # Sphinx 文档说明
│   ├── build.sh                   # 构建脚本
│   ├── source/                    # 源文件
│   └── build/html/                # HTML 输出 (197个模块)
│
├── versions/                      # 版本历史
│   ├── CHANGELOG.md               # 完整变更日志
│   └── v3.0.0.md                  # v3.0.0 发布说明
│
└── planning/                      # 规划文档
    ├── phase3.md                  # Phase 3 实施计划
    ├── phase4.md                  # Phase 4 规划
    ├── roadmap_2026.md            # 2026 年度路线图
    └── tech_debt.md               # 技术债务追踪
```

---

## 🎓 学习路径

### 👤 新用户路径

1. **第1天**: [项目概述](#-项目概述) → [快速开始](#-快速开始)
2. **第2天**: [安装指南](user_guide/installation.md) → [快速开始教程](user_guide/quick_start.md)
3. **第3天**: [示例代码](user_guide/examples/) 学习完整工作流
4. **第4-7天**: 根据需求学习功能指南（回测/特征/模型）
5. **持续**: [FAQ](user_guide/faq.md) 问题排查

### 👨‍💻 开发者路径

1. **了解架构**: [架构总览](architecture/overview.md) → [项目状态](architecture/PROJECT_STATUS.md)
2. **深入技术**: [技术栈](architecture/tech_stack.md) → [设计模式](architecture/design_patterns.md)
3. **性能优化**: [性能分析](architecture/performance.md)
4. **参与贡献**: [贡献指南](developer_guide/contributing.md) → [代码规范](developer_guide/coding_standards.md)

### 🏗️ 架构师路径

1. **六层架构**: [架构总览 - 六层架构](architecture/overview.md#%E5%85%AD%E5%B1%82%E6%9E%B6%E6%9E%84)
2. **三层策略**: [架构总览 - 三层策略架构](architecture/overview.md#%E4%B8%89%E5%B1%82%E7%AD%96%E7%95%A5%E6%9E%B6%E6%9E%84)
3. **设计模式**: [设计模式详解](architecture/design_patterns.md)
4. **技术演进**: [2026路线图](planning/roadmap_2026.md)

---

## 📝 文档贡献

### 文档原则

1. **清晰性**: 简洁明了，避免冗长
2. **完整性**: 覆盖核心功能和常见问题
3. **示例性**: 提供可运行的代码示例
4. **更新性**: 与代码保持同步

### 贡献方式

1. **报告问题**: 发现文档错误或遗漏时提 Issue
2. **改进文档**: 完善现有文档内容
3. **新增文档**: 补充缺失的文档
4. **翻译文档**: 提供英文版本（可选）

### 文档格式

- 使用 Markdown 格式
- 代码块标注语言类型
- 使用相对路径链接
- 长文档（>500行）需要目录

---

## 🔗 相关链接

- **GitHub 仓库**: [stock-analysis](https://github.com/your-org/stock-analysis)
- **问题反馈**: [Issues](https://github.com/your-org/stock-analysis/issues)
- **讨论区**: [Discussions](https://github.com/your-org/stock-analysis/discussions)

---

## 📅 文档版本信息

**文档版本**: v3.0.0
**最后更新**: 2026-02-06
**维护团队**: Quant Team
**项目状态**: 🎯 生产就绪 (95%)

**v3.0 文档更新亮点** (2026-02-06):
- ✅ 整合三个核心文档（README + PROJECT_STATUS + architecture/README）
- ✅ 完整的文档中心结构
- ✅ 清晰的学习路径（新用户/开发者/架构师）
- ✅ 全面的质量指标展示
- ✅ v3.0 核心特性完整说明（三层架构 + MLSelector）

---

**💡 提示**: 本文档是整个文档系统的入口和导航中心，建议从这里开始探索项目文档。
