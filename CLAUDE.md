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
