# 异步回测功能使用指南

## 📋 目录
1. [功能概述](#功能概述)
2. [架构设计](#架构设计)
3. [部署步骤](#部署步骤)
4. [使用方法](#使用方法)
5. [监控和调试](#监控和调试)
6. [故障排查](#故障排查)

---

## 功能概述

### 问题背景
原回测系统使用同步 HTTP 请求，存在以下问题：
- **请求超时**：大规模回测（多股票/长时间跨度）导致 API 请求超时
- **服务器资源占用**：同步请求长时间占用 HTTP 连接和服务器资源
- **用户体验差**：页面卡死，无法显示进度
- **不可扩展**：无法分布式处理任务

### 解决方案
采用 **异步任务队列** 架构（Celery + Redis）：
- ✅ 立即返回 `task_id`，释放 HTTP 连接
- ✅ 后台 Worker 异步执行回测
- ✅ 前端轮询获取任务进度和结果
- ✅ 支持任务取消功能
- ✅ 可分布式扩展 Worker 数量

---

## 架构设计

### 系统架构图

```
┌─────────────┐         ┌──────────────┐         ┌────────────┐
│   Frontend  │  POST   │   Backend    │ Publish │   Redis    │
│             ├────────>│   FastAPI    ├────────>│  Message   │
│             │ task_id │              │  Task   │   Queue    │
└──────┬──────┘         └──────────────┘         └─────┬──────┘
       │                                                │
       │ Poll /status/{task_id}                        │ Consume
       │ Every 2s                                       │
       │                                                ▼
       │                                         ┌─────────────┐
       │                                         │   Celery    │
       │                                         │   Worker    │
       │                                         │             │
       │                ┌────────────────────────┤ • 加载策略 │
       │                │        Result          │ • 加载数据 │
       │◄───────────────┘                        │ • 执行回测 │
       │                                         │ • 保存结果 │
       │                                         └──────┬──────┘
       │                                                │
       │                                                ▼
       │                                         ┌─────────────┐
       └────────────────────────────────────────>│  Database   │
                    Get result                   │ (Execution  │
                                                  │   Record)   │
                                                  └─────────────┘
```

### 核心组件

| 组件 | 作用 | 技术栈 |
|------|------|--------|
| **FastAPI 后端** | 接收请求，提交异步任务 | FastAPI + Python |
| **Redis** | 消息队列 + 结果存储 | Redis 7 |
| **Celery Worker** | 执行异步回测任务 | Celery 5.3 |
| **Celery Beat** | 定时任务调度（可选） | Celery Beat |
| **Flower** | 任务监控面板（可选） | Flower |
| **PostgreSQL** | 存储执行记录和结果 | TimescaleDB |

---

## 部署步骤

### 1. 运行数据库迁移

```bash
# 进入 backend 容器
docker-compose exec backend bash

# 连接数据库并执行迁移
psql -h timescaledb -U stock_user -d stock_analysis -f /app/migrations/V012__add_celery_task_support.sql
```

或手动执行：
```sql
ALTER TABLE strategy_executions ADD COLUMN task_id VARCHAR(255) UNIQUE;
CREATE INDEX idx_exec_task_id ON strategy_executions(task_id) WHERE task_id IS NOT NULL;
```

### 2. 安装依赖

```bash
# 在 backend/requirements.txt 中已添加：
# celery>=5.3.4
# flower>=2.0.1

# 重新构建镜像
docker-compose build backend celery_worker
```

### 3. 启动服务

```bash
# 启动所有服务（包括 Celery Worker）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 应该看到以下服务运行中：
# - backend (FastAPI)
# - celery_worker (异步任务处理)
# - celery_beat (定时任务调度，可选)
# - flower (监控面板，可选)
# - redis (消息队列)
```

### 4. 验证服务

```bash
# 查看 Celery Worker 日志
docker-compose logs -f celery_worker

# 应该看到类似输出：
# [2026-03-03 10:00:00,000: INFO/MainProcess] Connected to redis://redis:6379/0
# [2026-03-03 10:00:00,100: INFO/MainProcess] celery@worker1 ready.
```

### 5. 访问 Flower 监控面板（可选）

打开浏览器访问：http://localhost:5555

可以看到：
- 当前活跃的 Worker
- 正在执行的任务
- 已完成/失败的任务
- 任务执行时间统计

---

## 使用方法

### 前端自动模式

前端会**自动判断**是否使用异步模式：

```typescript
// 判断条件：
const shouldUseAsync = stockPool.length > 10 || daysDiff > 365

// 满足以下任一条件时自动使用异步模式：
// 1. 股票数量 > 10
// 2. 回测时间跨度 > 1年
```

**用户体验：**
- 小规模回测（≤10股票，≤1年）：同步执行，直接返回结果
- 大规模回测（>10股票或>1年）：异步执行，显示进度条

### 手动调用异步 API

如果需要强制使用异步模式：

```typescript
// 前端代码
const response = await apiClient.runAsyncBacktest({
  strategy_id: 18,
  stock_pool: ['000001', '600000', ...],
  start_date: '2023-01-01',
  end_date: '2023-12-31',
  initial_capital: 1000000,
  rebalance_freq: 'W',
  exit_strategy_ids: [1, 2]
})

// 返回：{ task_id: 'abc-123', execution_id: 456, status: 'pending' }

// 轮询任务状态
const statusData = await apiClient.getBacktestStatus(response.task_id)

// 返回：
// {
//   task_id: 'abc-123',
//   status: 'PROGRESS',  // PENDING | PROGRESS | SUCCESS | FAILURE
//   progress: { current: 5, total: 11, status: '计算特征数据...' }
// }

// 取消任务
await apiClient.cancelBacktest(response.task_id)
```

### 后端 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/backtest/async` | POST | 提交异步回测任务 |
| `/api/backtest/status/{task_id}` | GET | 查询任务状态和结果 |
| `/api/backtest/cancel/{task_id}` | DELETE | 取消任务 |

---

## 监控和调试

### 1. 查看 Celery Worker 日志

```bash
# 实时查看日志
docker-compose logs -f celery_worker

# 查看最近 100 条日志
docker-compose logs --tail=100 celery_worker
```

### 2. 使用 Flower 监控面板

访问 http://localhost:5555

**功能：**
- 📊 实时任务统计
- 📝 任务详细信息
- ⏱️ 执行时间分析
- 🔄 手动重试失败任务
- 🗑️ 清除历史任务

### 3. 查看 Redis 队列状态

```bash
# 进入 Redis 容器
docker-compose exec redis redis-cli

# 查看队列长度
> LLEN celery

# 查看正在执行的任务
> KEYS celery-task-meta-*

# 查看某个任务的结果
> GET celery-task-meta-abc-123-def
```

### 4. 查看数据库执行记录

```bash
# 进入数据库
docker-compose exec timescaledb psql -U stock_user -d stock_analysis

# 查询最近的异步任务
SELECT id, task_id, status, created_at, started_at, completed_at
FROM strategy_executions
WHERE task_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;

# 查询失败的任务
SELECT id, task_id, error_message
FROM strategy_executions
WHERE status = 'failed' AND task_id IS NOT NULL
ORDER BY created_at DESC
LIMIT 10;
```

---

## 故障排查

### 问题 1: Worker 无法启动

**症状：**
```
docker-compose logs celery_worker
# Error: No module named 'app.celery_app'
```

**解决方案：**
```bash
# 1. 检查 PYTHONPATH 环境变量
docker-compose exec celery_worker env | grep PYTHONPATH
# 应该输出: PYTHONPATH=/app/core:/app

# 2. 检查文件是否存在
docker-compose exec celery_worker ls -la /app/app/celery_app.py

# 3. 重新构建镜像
docker-compose build celery_worker
docker-compose up -d celery_worker
```

---

### 问题 2: 任务一直处于 PENDING 状态

**症状：**
- 前端显示"任务排队中..."超过 5 分钟
- 查询状态一直返回 `status: 'PENDING'`

**排查步骤：**
```bash
# 1. 检查 Worker 是否运行
docker-compose ps celery_worker
# 应该显示 Up 状态

# 2. 查看 Worker 日志
docker-compose logs celery_worker
# 查找是否有错误信息

# 3. 检查 Redis 连接
docker-compose exec backend python -c "
from app.celery_app import celery_app
print(celery_app.broker_connection().ensure_connection(max_retries=3))
"

# 4. 手动触发任务测试
docker-compose exec backend python -c "
from app.tasks.backtest_tasks import run_backtest_async
result = run_backtest_async.delay(1, {})
print(f'Task ID: {result.id}')
"
```

---

### 问题 3: 任务执行失败

**症状：**
- 任务状态变为 `FAILURE`
- 前端显示错误信息

**排查步骤：**
```bash
# 1. 查看任务错误详情
SELECT error_message FROM strategy_executions WHERE task_id = 'abc-123';

# 2. 查看 Worker 日志中的完整错误堆栈
docker-compose logs celery_worker | grep -A 50 "Task failed"

# 3. 检查回测逻辑是否正确
docker-compose exec backend python -c "
from app.repositories.strategy_execution_repository import StrategyExecutionRepository
repo = StrategyExecutionRepository()
execution = repo.get_by_task_id('abc-123')
print(execution['error_message'])
"
```

---

### 问题 4: 内存不足导致 Worker 被杀死

**症状：**
```
docker-compose logs celery_worker
# Killed
```

**解决方案：**
```yaml
# 在 docker-compose.yml 中调整 Worker 资源限制
celery_worker:
  deploy:
    resources:
      limits:
        memory: 4G  # 增加到 4GB
      reservations:
        memory: 1G
```

或减少并发数：
```yaml
celery_worker:
  command: celery -A app.celery_app worker --loglevel=info --concurrency=1
```

---

### 问题 5: 任务结果丢失

**症状：**
- 任务状态显示 `SUCCESS`
- 但查询结果返回空

**排查步骤：**
```bash
# 1. 检查 Redis 中的结果是否过期
docker-compose exec redis redis-cli
> TTL celery-task-meta-abc-123

# 2. 检查数据库中的结果
SELECT result FROM strategy_executions WHERE task_id = 'abc-123';

# 3. 增加 Celery 结果过期时间
# 在 backend/app/celery_app.py 中：
celery_app.conf.update(
    result_expires=172800,  # 增加到 48 小时
)
```

---

## 性能优化建议

### 1. 增加 Worker 数量

```bash
# 启动多个 Worker 实例
docker-compose up -d --scale celery_worker=4
```

### 2. 使用任务优先级队列

```python
# backend/app/celery_app.py
celery_app.conf.update(
    task_routes={
        'app.tasks.backtest_tasks.run_backtest_async': {
            'queue': 'high_priority',
            'priority': 10
        },
    },
)
```

### 3. 启用任务结果压缩

```python
celery_app.conf.update(
    result_compression='gzip',
)
```

---

## 总结

异步回测功能已成功实现，具备以下特性：

✅ **自动判断**：根据任务规模自动选择同步/异步模式
✅ **实时进度**：前端显示任务进度和状态
✅ **可取消**：支持取消正在执行的任务
✅ **可监控**：通过 Flower 面板监控所有任务
✅ **可扩展**：支持水平扩展 Worker 数量
✅ **高可用**：任务失败自动重试，结果持久化

**下一步建议：**
- [ ] 添加任务结果缓存（避免重复计算相同参数的回测）
- [ ] 实现 WebSocket 推送（替代轮询，提升实时性）
- [ ] 添加任务调度策略（限制用户并发任务数）
- [ ] 实现分布式 Worker 部署（跨服务器负载均衡）
