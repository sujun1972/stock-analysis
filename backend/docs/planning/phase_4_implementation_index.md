# Phase 4 三层架构实施方案 - 总览

> **版本**: v1.0
> **日期**: 2026-02-06
> **项目**: Stock Analysis Platform - Backend
> **状态**: 📝 规划中

---

## 📚 文档导航

本文档系统详细规划了 Backend 项目 Phase 4 的三层架构实施方案，共包含 **5 个核心文档**。

---

## 文档结构

```
phase_4_implementation/
├── 📘 phase_4_implementation_index.md          # [本文档] 总览与导航
├── 📗 backtest_three_layer_architecture_implementation_plan.md  # 核心方案（任务 4.0.1-4.0.2）
├── 📙 phase_4_0_strategy_implementations.md    # 策略实现（任务 4.0.3-4.0.4）
├── 📕 phase_4_0_backtest_and_api.md            # 回测引擎与 API（任务 4.0.5-4.0.6）
└── 📓 phase_4_testing_and_workflow.md          # 测试策略与工作流程
```

---

## 📘 文档 1：核心方案

**文件名**：[backtest_three_layer_architecture_implementation_plan.md](./backtest_three_layer_architecture_implementation_plan.md)

**内容概要**：
- ✅ 项目背景与目标
- ✅ 架构设计决策（为什么采用三层架构）
- ✅ 与现有架构的关系
- ✅ 关键技术决策
- ✅ **任务 4.0.1**：创建三层基类
  - StockSelector 基类完整实现
  - EntryStrategy 基类完整实现
  - ExitStrategy 基类完整实现
  - StrategyComposer 组合器完整实现
- ✅ **任务 4.0.2**：实现基础选股器
  - MomentumSelector（动量选股）
  - ExternalSelector（外部选股，支持 StarRanker）
  - ValueSelector（价值选股，简化版）

**适合读者**：
- 项目负责人（了解整体方案）
- 架构师（理解架构决策）
- Backend 开发者（基础类实现参考）

**阅读时长**：30 分钟

---

## 📙 文档 2：策略实现

**文件名**：[phase_4_0_strategy_implementations.md](./phase_4_0_strategy_implementations.md)

**内容概要**：
- ✅ **任务 4.0.3**：实现基础入场策略
  - MABreakoutEntry（均线突破入场）
  - RSIOversoldEntry（RSI 超卖入场）
  - ImmediateEntry（立即入场，测试用）
- ✅ **任务 4.0.4**：实现基础退出策略
  - ATRStopLossExit（ATR 动态止损）
  - FixedStopLossExit（固定止损止盈）
  - TimeBasedExit（时间止损）
  - CombinedExit（组合退出策略）
- ✅ 策略使用示例
- ✅ 测试计划（单元测试用例设计）

**适合读者**：
- Backend 开发者（策略实现参考）
- QA 工程师（测试用例参考）

**阅读时长**：25 分钟

---

## 📕 文档 3：回测引擎与 API

**文件名**：[phase_4_0_backtest_and_api.md](./phase_4_0_backtest_and_api.md)

**内容概要**：
- ✅ **任务 4.0.5**：实现三层回测适配器
  - ThreeLayerBacktestEngine（轻量级回测引擎）
  - ThreeLayerBacktestAdapter（适配器层）
  - 持仓管理、资金管理、手续费计算
  - 绩效指标计算
- ✅ **任务 4.0.6**：创建 REST API 端点
  - 6 个 API 端点完整实现
  - 策略注册表（registry.py）
  - Pydantic 请求/响应模型
- ✅ API 使用示例
- ✅ 性能优化策略

**适合读者**：
- Backend 开发者（回测引擎和 API 实现）
- 前端开发者（API 调用参考）

**阅读时长**：30 分钟

---

## 📓 文档 4：测试策略与工作流程

**文件名**：[phase_4_testing_and_workflow.md](./phase_4_testing_and_workflow.md)

**内容概要**：
- ✅ 完整的测试策略（单元测试、集成测试、E2E 测试）
- ✅ 工作量评估与排期（29 人天，~4 周）
- ✅ 开发工作流程（Git 分支策略、提交规范）
- ✅ 代码审查清单
- ✅ 部署计划（开发、测试、生产环境）
- ✅ 风险管理与应急预案
- ✅ 持续改进路线图

**适合读者**：
- 项目经理（工作量评估、排期）
- QA 工程师（测试策略）
- DevOps 工程师（部署流程）
- 所有开发者（工作流程规范）

**阅读时长**：25 分钟

---

## 快速开始指南

### 如果你是...

#### 📌 **项目负责人**

**阅读路径**：
1. [核心方案](./backtest_three_layer_architecture_implementation_plan.md) - 第一、二章（了解背景和架构）
2. [测试与工作流程](./phase_4_testing_and_workflow.md) - 工作量评估章节（了解排期）
3. 本文档 - 关键指标章节（了解目标）

**关键问题**：
- ✅ 为什么要做三层架构？ → 核心方案第二章
- ✅ 需要多少时间和资源？ → 测试与工作流程：工作量评估
- ✅ 风险有哪些？ → 测试与工作流程：风险管理

---

#### 💻 **Backend 开发者**

**阅读路径**（按实施顺序）：
1. [核心方案](./backtest_three_layer_architecture_implementation_plan.md) - 任务 4.0.1-4.0.2
2. [策略实现](./phase_4_0_strategy_implementations.md) - 任务 4.0.3-4.0.4
3. [回测引擎与 API](./phase_4_0_backtest_and_api.md) - 任务 4.0.5-4.0.6
4. [测试与工作流程](./phase_4_testing_and_workflow.md) - 测试策略和工作流程

**开发清单**：
- [ ] 阅读核心方案，理解三层架构设计
- [ ] 创建功能分支 `feature/three-layer-architecture`
- [ ] 按任务顺序实施（4.0.1 → 4.0.2 → ...）
- [ ] 每个任务完成后编写单元测试
- [ ] 提交 PR 并进行代码审查
- [ ] 合并到 `develop` 分支

---

#### 🧪 **QA 工程师**

**阅读路径**：
1. [测试与工作流程](./phase_4_testing_and_workflow.md) - 测试策略章节
2. [策略实现](./phase_4_0_strategy_implementations.md) - 测试计划章节
3. [回测引擎与 API](./phase_4_0_backtest_and_api.md) - API 使用示例

**测试清单**：
- [ ] 编写单元测试用例（150+）
- [ ] 编写集成测试用例（30+）
- [ ] 编写 E2E 测试用例（5+）
- [ ] 执行性能测试（Locust）
- [ ] 验收测试

---

#### 🎨 **前端开发者**

**阅读路径**：
1. [回测引擎与 API](./phase_4_0_backtest_and_api.md) - API 端点章节
2. [回测引擎与 API](./phase_4_0_backtest_and_api.md) - API 使用示例

**关键信息**：
- ✅ API 端点列表：6 个端点
- ✅ 请求/响应格式：详细的 JSON Schema
- ✅ 调用示例：curl 命令示例
- ✅ 错误处理：标准 HTTP 状态码

---

## 关键指标

### 功能指标

| 指标 | 目标值 | 当前状态 |
|------|--------|---------|
| **选股器数量** | 3 个 | 📝 待实现 |
| **入场策略数量** | 3 个 | 📝 待实现 |
| **退出策略数量** | 4 个 | 📝 待实现 |
| **API 端点数量** | 6 个 | 📝 待实现 |
| **策略组合数** | 36 种（3×3×4） | 📝 待实现 |

### 质量指标

| 指标 | 目标值 | 验收标准 |
|------|--------|---------|
| **测试覆盖率** | 75%+ | 单元测试 + 集成测试 |
| **单元测试数量** | 150+ | 覆盖所有核心逻辑 |
| **集成测试数量** | 30+ | 覆盖所有 API 端点 |
| **E2E 测试数量** | 5+ | 覆盖关键用户故事 |
| **代码质量评分** | 9.0/10 | black + flake8 |

### 性能指标

| 指标 | 目标值 | 测试条件 |
|------|--------|---------|
| **单次回测响应时间** | P95 < 5s | 100 股票 × 180 天 |
| **并发支持** | 20 QPS | 无错误 |
| **缓存命中率** | 40%+ | 相同参数回测 |
| **API 响应时间** | P95 < 100ms | 元数据查询 |

### 开发指标

| 指标 | 目标值 | 备注 |
|------|--------|------|
| **总工作量** | 29 人天 | Phase 4.0 核心功能 |
| **开发周期** | 4 周 | 1 人全职 |
| **并行开发** | 2 周 | 2 人并行 |
| **代码行数增长** | <2000 行 | 保持代码精简 |

---

## 技术栈

### 新增依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| 无 | - | 使用现有技术栈 |

**说明**：三层架构实现不需要新增依赖，完全基于现有技术栈。

### 使用的现有技术

- **Web 框架**：FastAPI 0.104+
- **异步驱动**：asyncpg、asyncio
- **缓存**：Redis
- **监控**：Prometheus + Grafana
- **日志**：Loguru
- **测试**：pytest、pytest-asyncio、httpx

---

## 兼容性说明

### 向后兼容性

✅ **完全兼容**：三层架构与现有架构并行，不影响现有功能。

| 现有功能 | 兼容性 | 说明 |
|---------|--------|------|
| **现有 2 个策略** | ✅ 完全兼容 | ComplexIndicatorStrategy、MLModelStrategy 继续可用 |
| **现有回测 API** | ✅ 完全兼容 | `/api/backtest` 端点保持不变 |
| **现有数据库** | ✅ 完全兼容 | 新增表，不修改现有表 |
| **现有缓存** | ✅ 完全兼容 | 使用独立的缓存 key |

### API 版本管理

```
现有 API：/api/backtest/*       (v1.0, 保持不变)
新增 API：/api/three-layer-strategy/*  (v2.1, 新增)
```

---

## 里程碑

### Milestone 1：基础架构完成（Week 1）

**交付物**：
- ✅ 三层基类（4 个文件）
- ✅ 基础选股器（3 个文件）
- ✅ 单元测试（30 个测试用例）

**验收标准**：
- 所有基类和选股器通过单元测试
- 代码通过 black 和 flake8 检查
- 代码审查通过

### Milestone 2：策略库完成（Week 2）

**交付物**：
- ✅ 入场策略（3 个文件）
- ✅ 退出策略（4 个文件）
- ✅ 单元测试（48 个测试用例）

**验收标准**：
- 所有策略通过单元测试
- 技术指标计算准确（RSI、ATR 等）
- 策略组合逻辑正确

### Milestone 3：回测引擎完成（Week 3）

**交付物**：
- ✅ ThreeLayerBacktestEngine
- ✅ ThreeLayerBacktestAdapter
- ✅ 单元测试（30 个测试用例）

**验收标准**：
- 回测流程正确执行
- 绩效指标计算准确
- 性能达标（<5s）

### Milestone 4：API 与集成完成（Week 4）

**交付物**：
- ✅ 6 个 API 端点
- ✅ 策略注册表
- ✅ 集成测试（30 个测试用例）
- ✅ E2E 测试（5 个测试用例）
- ✅ 完整文档

**验收标准**：
- 所有 API 端点正常工作
- 前端可以正确调用 API
- 测试覆盖率 ≥ 75%
- 性能达标
- 文档完整

---

## 相关链接

### Backend 项目文档

- [Backend README](../../README.md)
- [Phase 0-3 实施总结](./phase_0_3_implementation_summary.md)
- [优化路线图 v3.4](./optimization_roadmap.md)
- [架构总览](../architecture/overview.md)
- [API 参考文档](../api_reference/README.md)

### 前端项目文档

- [前端回测改进计划](/docs/frontend-backtest-improvement-plan.md)（本方案的依据）

### 行业参考

- [Zipline Documentation](https://www.zipline.io/)（Pipeline 架构参考）
- [Backtrader Documentation](https://www.backtrader.com/)（外部调仓表架构）
- [聚宽文档](https://www.joinquant.com/help/)（选股+择时分离）

---

## 常见问题 (FAQ)

### Q1：为什么不直接使用 Core 项目的回测引擎？

**A**：Core 项目的回测引擎不支持三层架构。三层架构需要：
- 独立的选股、入场、退出逻辑
- 不同频率的执行（选股周频，交易日频）
- 外部选股系统集成

因此在 Backend 实现轻量级回测引擎更合适。

### Q2：三层架构会影响现有功能吗？

**A**：不会。三层架构与现有架构并行，使用独立的：
- API 端点（`/api/three-layer-strategy`）
- 数据库表（`strategy_templates`、`backtest_history`）
- 缓存 key

### Q3：如何选择使用现有架构还是三层架构？

**A**：根据使用场景选择：

**使用现有架构**（BaseStrategy）：
- 单股回测
- 一体化策略（选股和交易一体）
- 简单快速的策略测试

**使用三层架构**（StrategyComposer）：
- 多股组合回测
- 需要应用外部选股结果（如 StarRanker）
- 需要独立配置买卖和风控逻辑
- 需要灵活组合不同策略模块

### Q4：性能会不会变差？

**A**：不会。性能优化措施包括：
- 并行数据加载（60% 加载时间↓）
- 异步执行（避免阻塞）
- Redis 缓存（40%+ 命中率）
- 选股频率控制（减少 70% 选股计算）

目标性能：P95 响应时间 < 5s（100 股票 × 180 天）

### Q5：测试覆盖率为什么只要求 75%，不是 100%？

**A**：
- 核心业务逻辑覆盖率 ≥ 90%
- 辅助功能覆盖率 ≥ 80%
- 边缘情况和异常处理已覆盖
- 追求 100% 的边际收益递减
- 75% 已经是很高的水平

参考：Backend v2.0 当前测试覆盖率为 65%，已经是优秀水平。

### Q6：什么时候可以上线？

**A**：预计时间线：
- Week 1-2：开发基础架构和策略
- Week 3：开发回测引擎
- Week 4：开发 API 和集成测试
- Week 5（可选）：灰度发布和调优

**最快上线**：4 周后（如果 2 人并行开发，可缩短至 3 周）

---

## 反馈与支持

### 如何提供反馈

- **文档问题**：在 Issue 中提出
- **技术问题**：在团队会议中讨论
- **功能建议**：在 Issue 中提出，标签：`enhancement`

### 获取帮助

- **Slack 频道**：`#backend-dev`
- **技术负责人**：@backend-lead
- **文档维护**：开发团队

---

## 更新记录

| 版本 | 日期 | 变更 | 作者 |
|------|------|------|------|
| v1.0 | 2026-02-06 | 初始版本，完整的 Phase 4 实施方案 | Claude Code |

---

**文档维护者**：开发团队
**创建日期**：2026-02-06
**最后更新**：2026-02-06
**下次审查**：开发开始前

---

## 开始实施

准备好开始了吗？

1. ✅ **阅读核心方案**：[backtest_three_layer_architecture_implementation_plan.md](./backtest_three_layer_architecture_implementation_plan.md)
2. ✅ **创建功能分支**：`git checkout -b feature/three-layer-architecture`
3. ✅ **开始任务 4.0.1**：创建三层基类
4. ✅ **每日站会**：同步进度和问题

祝开发顺利！🚀
