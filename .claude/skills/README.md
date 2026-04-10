# Agent Skills 使用指南

这是 A股AI量化交易系统的 Agent Skills 集合。

## 📋 根项目可用技能（跨项目）

| 技能名称 | 命令 | 用途 |
|---------|------|------|
| 数据库健康检查 | `/db-health-check` | 检查 TimescaleDB 连接、表结构和数据完整性 |
| 完整测试流水线 | `/run-all-tests` | 运行所有单元测试和集成测试 |
| 性能基准测试 | `/performance-benchmark` | 执行 Locust 压力测试和并发性能测试 |
| 股票数据下载 | `/download-stock-data` | 从 AkShare 下载股票数据到数据库 |
| 特征工程 | `/calculate-features` | 计算技术指标和 Alpha 因子（125+特征） |
| 代码规范检查 | `/code-review` | 检查 Python 和 TypeScript 代码质量 |
| 快速回测 | `/quick-backtest` | 运行策略回测并分析绩效 |
| API 端点测试 | `/test-api` | 测试所有 FastAPI 后端端点 |
| 项目架构解释 | `/explain-architecture` | 解释项目架构和设计（新人入职） |
| 智能提交 | `/smart-commit` | 只提交对话中修改的文件，排除其他改动 |
| 数据质量检查 | `/data-quality-check` | 检查数据质量 |
| 通知测试 | `/test-notification` | 测试通知系统功能 |
| 盘前分析 | `/premarket-analysis` | 盘前预期管理系统 |
| 情绪周期分析 | `/sentiment-cycle-analysis` | 分析市场情绪周期 |

## 📦 子项目 Skills

以下 skills 已迁移到对应子项目，在该子项目上下文中使用：

| 技能 | 位置 | 用途 |
|------|------|------|
| `/check-logging` | `core/.claude/skills/` | 检查 core 子项目日志规范 |
| `/test-core` | `core/.claude/skills/` | 专门测试 core 项目 |
| `/exception-handling` | `core/.claude/skills/` | core 异常处理规范 |
| `/response-format` | `core/.claude/skills/` | core Response 格式规范 |
| `/exception-handling` (backend) | `backend/.claude/skills/` | backend 异常处理规范 |
| `/api-response` | `backend/.claude/skills/` | backend API 响应格式 |

## 🚀 快速开始

在 Claude Code 对话中，直接输入技能命令即可：

```
/db-health-check
/smart-commit
/explain-architecture
```

## 📖 相关文档

子项目开发指南：
- [admin/CLAUDE.md](../admin/CLAUDE.md) — Admin 管理后台
- [backend/CLAUDE.md](../backend/CLAUDE.md) — Backend API 服务
- [core/CLAUDE.md](../core/CLAUDE.md) — Core 核心库
- [frontend/CLAUDE.md](../frontend/CLAUDE.md) — Frontend 用户端

---

**最后更新**: 2026-04-10
