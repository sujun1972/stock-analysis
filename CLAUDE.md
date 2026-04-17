# Claude Development Guide

## 开发环境启动

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## 项目结构

| 子项目 | 技术栈 | 说明 | 详细指南 |
|--------|--------|------|---------|
| `/admin` | Next.js, Zustand, shadcn/ui | 管理后台 | [admin/CLAUDE.md](admin/CLAUDE.md) |
| `/backend` | FastAPI, Celery, PostgreSQL | 后端 API 服务 | [backend/CLAUDE.md](backend/CLAUDE.md) |
| `/core` | Python, Tushare, LightGBM | 核心业务逻辑 | [core/CLAUDE.md](core/CLAUDE.md) |
| `/frontend` | Next.js | 用户前端 | [frontend/CLAUDE.md](frontend/CLAUDE.md) |
| `/db_init` | SQL | 数据库迁移脚本 | — |

## 常用命令

```bash
docker-compose ps                          # 查看容器状态
docker-compose logs -f [service_name]      # 查看日志
docker-compose restart [service_name]      # 重启服务
docker-compose down                        # 停止所有服务
docker-compose restart celery_worker       # 新增 Celery 任务后必须重启
```

## 文档写入规范

- **不要**在项目目录中创建任务过程说明文档（如 `docs/xxx_summary.md`）
- 临时记录使用系统临时目录：`/tmp/claude_notes_<timestamp>.md`
- 项目正式文档仅包括：架构设计、API 文档、用户手册、长期维护的开发指南

## Git Commit 规范

```bash
git commit -m "type(scope): 简短描述

详细说明:
- 问题1: 描述 + 修复
- 问题2: 描述 + 修复

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## 跨项目架构

### 数据流

```
Tushare / AkShare
    ↓
core/src/providers/    ← Provider 封装（统一接口）
    ↓
backend/app/services/  ← Service 层（业务逻辑、Celery 任务）
    ↓
backend/app/repositories/ ← Repository 层（数据库访问）
    ↓
TimescaleDB / Redis
    ↓
backend/app/api/       ← FastAPI 端点
    ↓
admin/ 或 frontend/    ← 前端页面
```

### LLM 调用架构

所有 AI 分析（个股专家、市场情绪、盘前碰撞、策略生成）统一通过 LangChain 调用 LLM：

```
ai_provider_configs 表          ← 数据库驱动的 Provider 配置（api_key、model、temperature 等）
    ↓
AIStrategyService.create_client(provider, config)
    ↓
LangChainClient                 ← backend/app/services/langchain_client.py
    ↓
ChatOpenAI (deepseek/openai)    或  ChatGoogleGenerativeAI (gemini)
```

- **新增 Provider**：在 `langchain_client.py` 的 `_MODEL_FACTORIES` 注册工厂函数，数据库 `ai_provider_configs` 添加配置行
- **Prompt 模板**：数据库驱动（`llm_prompt_template` 表），通过 `PromptTemplateService` 管理
- **调用日志**：`llm_call_logs` 表 + `LLMCallLogger` 单例，手动 `create_log_entry` / `update_log_success`
- **依赖包**：`langchain`、`langchain-core`、`langchain-openai`、`langchain-google-genai`

### CIO Agent 架构（Phase 3）

CIO（首席投资官）专家使用 LangChain Agent 模式，可自主决定查询哪些数据维度：

```
CIOAgentService                      ← backend/app/services/cio_agent_service.py
    ↓
create_agent(model, tools, system_prompt)   ← langchain.agents.create_agent（LangGraph）
    ↓
7 个 LangChain Tool                  ← backend/app/services/langchain_tools.py
    ├── get_basic_market             基础盘面（价格、估值、行业、筹码）
    ├── get_capital_flow             资金流向（主力净流入、北向资金）
    ├── get_shareholder_info         股东信息（人数变化、减持、解禁）
    ├── get_technical_indicators     技术指标（均线结构、RSI、多级别MACD、量价动能）
    ├── get_financial_reports        财报披露日期
    ├── get_risk_alerts              风险警示（ST、质押）
    └── get_nine_turn                神奇九转指标
```

`get_technical_indicators` 内部委托三个独立分析服务（纯计算，无 IO）：

| 服务 | 文件 | 职责 |
|------|------|------|
| `MaAnalysisService` | `ma_analysis_service.py` | 均线多周期结构（排列形态、支撑阻力、核心博弈点） |
| `MacdAnalysisService` | `macd_analysis_service.py` | MACD 多级别分析（零轴、交叉、动能、背离、跨级别共振） |
| `VolumePriceAnalysisService` | `volume_price_analysis_service.py` | 量价动能（逐日推演、中线结构、天量压力、异动检测） |

所有 Tool 输出均为 **Markdown 表格**格式，便于 LLM 结构化解析。

- **触发方式**：`analysis_type == "cio_directive"` 时自动走 Agent 路径（`/generate` 和 `/generate-multi` 端点）
- **非 CIO 类型**不走 Agent，保持现有直接调用方式
- **max_iterations**：5 轮（通过 LangGraph `recursion_limit` 控制）
- **超时**：120 秒
- **Expert Summaries**：`/generate-multi` 的 `include_cio=true` 时，前面专家的输出摘要会注入 Agent 的用户消息

### Celery 任务架构

- Worker：`celery_worker` 容器
- Beat 调度器：`celery_beat` 容器（数据库驱动，30秒同步配置）
- 任务状态持久化：`celery_task_history` 表（通过 `celery_signals.py` 信号自动更新）
- 前端轮询：Header 组件每 5 秒轮询活动任务，每 30 秒同步历史

**fork pool worker 注意**：Celery worker 通过 fork 继承父进程连接池。`celery_signals.py` 中的 `worker_process_init` 信号在每个 fork worker 启动时重置 `DatabaseManager` 单例，避免连接池损坏。

### 数据库连接池总览

| 连接池 | 上限 |
|--------|------|
| SQLAlchemy 同步引擎（backend） | 15 |
| SQLAlchemy 异步引擎（backend） | 15 |
| psycopg2（core） | 20 |
| **合计** | **≈50** |
| PostgreSQL max_connections | **200** |

`max_connections=200` 已通过 `ALTER SYSTEM` 持久化。

### 数据同步架构（异步任务模式）

所有数据同步操作通过 Celery 异步任务执行：

1. 前端点击同步按钮 → `POST /api/{table}/sync-async`
2. 后端提交 Celery task + 记录 `celery_task_history`
3. 前端 `addTask()` + `triggerPoll()` 立即更新 Header 图标
4. Celery worker 执行同步，信号自动更新任务状态
5. 前端完成回调 `registerCompletionCallback` 触发数据刷新

**sync_configs 表**（`db_init/migrations/105_create_sync_configs.sql`）是所有数据表同步配置的单一数据源，驱动同步配置页面（`/settings/sync-config`）的展示和操作。

## 已移除功能（2026-03-25）

以下功能已从系统中移除，勿再添加：

- **概念标签管理**：`/concepts` 页面、`ConceptRepository`、`ConceptSyncService`、相关表（`concept`、`stock_concept`）
- **Frontend 股票/数据中心页面**：`/stocks`、`/stocks/[code]`、`/sync/initialize`、`/sync/extended`（API 和数据保留）
- **市场情绪功能**：大盘情绪指标、涨停板池、龙虎榜数据查询、情绪周期分析（AI 情绪分析和盘前预期保留）
