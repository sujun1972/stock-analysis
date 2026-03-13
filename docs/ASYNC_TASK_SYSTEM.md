# 异步任务系统架构

## 概述

本系统实现了完整的异步任务管理架构，支持长时间运行的后台任务（如AI分析、数据同步、策略回测等）。用户可以提交任务后离开页面，系统会在任务完成时自动通知。

## 核心特性

- ✅ **异步任务提交**：长时间任务后台执行，不阻塞用户操作
- ✅ **全局任务轮询**：项目级轮询，跨页面、跨标签页持续监控
- ✅ **任务自动恢复**：浏览器刷新或重启后自动恢复正在执行的任务
- ✅ **实时状态展示**：右下角浮动按钮显示活动任务数量和详情
- ✅ **完成通知**：Toast 提示任务完成状态

## 技术架构

### 后端（Backend）

#### 1. Celery 异步任务队列

```python
# backend/app/celery_app.py
celery_app = Celery(
    "stock_analysis",
    broker=f"{settings.REDIS_URL}",
    backend=f"redis://..."
)
```

**配置**：
- 消息队列：Redis
- 结果存储：Redis DB 1
- 超时配置：硬超时 1小时，软超时 50分钟
- 结果过期：24小时

#### 2. 任务状态查询 API

**端点**：`GET /api/sentiment/sync/status/{task_id}`

返回任务状态：
- `PENDING`：等待执行
- `STARTED`：正在执行
- `PROGRESS`：执行中（带进度信息）
- `SUCCESS`：执行成功
- `FAILURE`：执行失败
- `RETRY`：重试中

**PROGRESS 状态响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "task_id": "batch_sentiment_sync_2024-01-01_2024-01-31_xxx",
    "status": "PROGRESS",
    "message": "正在同步 2024-01-15 (15/31)",
    "progress": 48,
    "current": 15,
    "total": 31,
    "details": {
      "success_count": 10,
      "failed_count": 2,
      "skipped_count": 3
    }
  }
}
```

#### 3. 活动任务列表 API

**端点**：`GET /api/sentiment/tasks/active`

使用 Celery Inspector 获取所有活动任务：
```python
inspect = celery_app.control.inspect()
active = inspect.active()      # 正在执行
reserved = inspect.reserved()  # 等待执行
```

### 前端（Admin）

#### 1. 全局任务轮询 Hook

**文件**：`admin/hooks/use-task-polling.ts`

**核心功能**：
- 全局任务队列：`Map<taskId, TaskInfo>`
- 轮询间隔：3 秒
- 超时处理：10 分钟自动移除
- 启动恢复：调用 `/api/sentiment/tasks/active` 恢复任务

**使用示例**：
```typescript
import { addTaskToQueue } from '@/hooks/use-task-polling'

// 提交任务后加入轮询队列
addTaskToQueue(taskId, "AI分析生成（2026-03-12）")
```

#### 2. TaskPollingProvider

**文件**：`admin/components/TaskPollingProvider.tsx`

全局 Provider，在 `admin/app/(dashboard)/layout.tsx` 中注册：
```tsx
<TaskPollingProvider>
  <AdminLayout>{children}</AdminLayout>
  <ActiveTasksPanel />
</TaskPollingProvider>
```

#### 3. ActiveTasksPanel 组件

**文件**：`admin/components/ActiveTasksPanel.tsx`

**特性**：
- 右下角浮动按钮，显示任务数量徽章
- 侧边滑出面板，展示所有活动任务
- 自动刷新（5秒间隔）
- 任务状态可视化（执行中/等待中）

## 工作流程

### 1. 提交异步任务

```typescript
// 前端：提交任务
const response = await apiClient.post("/api/sentiment/ai-analysis/generate", null, {
  params: { date: "2026-03-12", provider: "deepseek" }
})

// 后端：创建 Celery 任务
task = daily_sentiment_ai_analysis_task.apply_async(
  args=[date, provider, 0],
  task_id=f"ai_analysis_{date}_{provider}"
)

// 返回任务ID
return { task_id: task.id, status: "pending" }
```

### 2. 加入轮询队列

```typescript
// 加入全局轮询队列
addTaskToQueue(taskId, "AI分析生成（2026-03-12）")

// 每3秒轮询任务状态
setInterval(async () => {
  const status = await apiClient.get(`/api/sentiment/sync/status/${taskId}`)

  if (status.data.status === 'SUCCESS') {
    // 任务完成，显示 toast
    toast.success("AI分析生成完成")
    // 从队列移除
  }
}, 3000)
```

### 3. 任务自动恢复

```typescript
// 浏览器启动时
useEffect(() => {
  // 获取所有活动任务
  const tasks = await apiClient.get('/api/sentiment/tasks/active')

  // 恢复到轮询队列
  tasks.forEach(task => {
    globalTaskQueue.set(task.task_id, {
      taskId: task.task_id,
      taskName: task.display_name,
      startTime: Date.now()
    })
  })

  startPolling()
}, [])
```

### 4. 任务状态展示

用户点击右下角浮动按钮，查看所有活动任务：
- 任务名称（友好显示）
- 任务ID（可复制）
- 执行状态（执行中/等待中）
- Worker 信息

## 任务类型

系统支持多种异步任务：

| 任务类型 | Task ID 前缀 | 显示名称 | 进度支持 |
|---------|-------------|---------|---------|
| AI分析 | `ai_analysis_` | AI分析生成（日期） | ❌ |
| 单日期同步 | `manual_sentiment_sync_` | 情绪数据同步（日期） | ✅ |
| 批量同步 | `batch_sentiment_sync_` | 情绪数据批量同步（日期范围） | ✅ |
| 策略回测 | - | 策略回测 | ❌ |
| AI策略生成 | - | AI策略生成 | ❌ |
| 盘前预期 | - | 盘前预期管理 | ❌ |

### 批量同步任务

**API 端点**：`POST /api/sentiment/sync/batch?start_date=2024-01-01&end_date=2024-01-31`

**任务特性**：
- 支持日期范围批量同步
- 实时进度更新（显示当前同步的日期和整体进度）
- 自动跳过非交易日
- 统计成功、失败、跳过的数量
- 防止 API 限流（每个日期之间有延迟）

**使用场景**：
- 系统初始化时批量导入历史数据
- 补充缺失的历史情绪数据
- 定期批量更新近期数据

## 扩展指南

### 添加新的异步任务

#### 1. 创建 Celery 任务

```python
# backend/app/tasks/my_task.py
from app.celery_app import celery_app

@celery_app.task(name="my_module.task_name")
def my_async_task(param1, param2):
    # 执行长时间操作
    result = do_something()

    # 返回结果
    return {
        "status": "success",
        "data": result
    }
```

#### 2. 创建 API 端点

```python
@router.post("/my-task/execute")
async def execute_my_task(param1: str):
    from app.tasks.my_task import my_async_task

    task_id = f"my_task_{param1}"

    task = my_async_task.apply_async(
        args=[param1, param2],
        task_id=task_id
    )

    return {
        "code": 200,
        "data": {"task_id": task.id, "status": "pending"}
    }
```

#### 3. 前端集成

```typescript
// 提交任务
const response = await apiClient.post("/api/my-task/execute", { param1 })

// 加入轮询队列
if (response.code === 200) {
  addTaskToQueue(response.data.task_id, "我的任务")
}
```

#### 4. 更新任务显示名称解析

在 `backend/app/api/endpoints/sentiment.py` 的 `_get_task_display_name` 函数中添加：

```python
def _get_task_display_name(task_id: str, task_name: str) -> str:
    # 新任务类型
    if task_id.startswith('my_task_'):
        return f"我的任务（{task_id.split('_')[2]}）"

    # ... 其他类型
```

## 监控与调试

### 查看活动任务

```bash
# API 测试
curl "http://localhost:8000/api/sentiment/tasks/active" | jq
```

### 查看任务状态

```bash
# 查询特定任务
curl "http://localhost:8000/api/sentiment/sync/status/{task_id}" | jq
```

### Celery Worker 日志

```bash
# 查看 Worker 日志
docker-compose logs -f celery-worker

# 过滤特定任务
docker-compose logs celery-worker | grep "ai_analysis"
```

## 性能优化

### 轮询策略

- **全局轮询**：3秒间隔，适用于跨页面任务
- **页面轮询**：3秒间隔，适用于当前页面实时反馈
- **面板刷新**：5秒间隔，减少 API 调用

### 任务去重

使用固定 `task_id` 防止重复提交：
```python
task_id = f"ai_analysis_{date}_{provider}"

# 检查任务是否已存在
existing_task = AsyncResult(task_id)
if existing_task.state in ['PENDING', 'STARTED']:
    return {"code": 409, "message": "任务已在执行中"}
```

### 超时处理

任务超过 10 分钟自动从队列移除，避免内存泄漏。

## 最佳实践

1. **任务命名规范**：使用语义化的 `task_id`，便于识别和调试
2. **错误处理**：任务失败时返回详细错误信息
3. **进度反馈**：长时间任务可返回进度百分比（可选）
4. **结果缓存**：任务结果在 Redis 中缓存 24 小时
5. **幂等性**：任务应设计为可重入，支持重试
