# Agent Skills 使用指南

这是 A股AI量化交易系统的 Agent Skills 集合，旨在提升开发效率和规范化程度。

## 📋 可用技能列表

| 技能名称 | 命令 | 用途 | 优先级 |
|---------|------|------|--------|
| 数据库健康检查 | `/db-health-check` | 检查 TimescaleDB 连接、表结构和数据完整性 | ⭐⭐⭐⭐⭐ |
| 完整测试流水线 | `/run-all-tests` | 运行所有单元测试和集成测试 | ⭐⭐⭐⭐⭐ |
| 股票数据下载 | `/download-stock-data` | 从 AkShare 下载股票数据到数据库 | ⭐⭐⭐⭐ |
| 特征工程 | `/calculate-features` | 计算技术指标和 Alpha 因子（125+特征） | ⭐⭐⭐⭐ |
| 代码规范检查 | `/code-review` | 检查 Python 和 TypeScript 代码质量 | ⭐⭐⭐ |
| 快速回测 | `/quick-backtest` | 运行策略回测并分析绩效 | ⭐⭐⭐⭐ |
| API 端点测试 | `/test-api` | 测试所有 FastAPI 后端端点 | ⭐⭐⭐ |
| 项目架构解释 | `/explain-architecture` | 解释项目架构和设计（新人入职） | ⭐⭐⭐⭐⭐ |

## 🚀 快速开始

### 使用技能

在 Claude Code 对话中，直接输入技能命令即可：

```
/db-health-check
```

或者通过自然语言触发：

```
帮我检查一下数据库状态
```

### 新人入职流程

```
第1步: /explain-architecture      # 理解整体架构
第2步: /db-health-check           # 验证环境配置
第3步: /run-all-tests             # 运行测试熟悉功能
第4步: /download-stock-data       # 准备数据
第5步: /calculate-features        # 理解特征工程
第6步: /quick-backtest            # 运行完整流程
```

## 📚 技能详解

详细说明请查看各技能的 SKILL.md 文件。

## 📖 相关文档

- [Agent Skills 官方文档](https://agentskills.io)
- [Claude Code Skills 文档](https://code.claude.com/docs/en/skills.md)
- [项目主文档](../README.md)
- [快速开始指南](../QUICKSTART.md)

---

**最后更新**: 2026-01-26
