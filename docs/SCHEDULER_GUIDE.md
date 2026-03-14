# 定时任务动态配置系统使用指南

## 📖 概述

本系统实现了基于数据库的动态定时任务配置，支持在Admin管理后台实时修改定时任务的启用状态、执行时间和参数，**无需重启服务即可生效**。

## 🎯 核心特性

- ✅ **动态配置**: 修改后30秒内自动生效，无需重启Celery Beat
- ✅ **可视化管理**: Admin界面支持启用/禁用、修改Cron表达式和参数
- ✅ **自动日志**: 记录每次任务执行的开始、成功、失败状态
- ✅ **Cron验证**: 自动验证Cron表达式格式，计算下次执行时间
- ✅ **执行历史**: 查看任务历史执行记录和错误信息

## 🏗️ 系统架构

```
Admin管理界面
    ↓ (修改配置)
scheduled_tasks表 (PostgreSQL)
    ↓ (每30秒轮询)
DatabaseScheduler (自定义调度器)
    ↓ (生成任务计划)
Celery Beat (调度引擎)
    ↓ (发送任务到队列)
Celery Worker (执行任务)
    ↓ (记录执行日志)
task_execution_history表
```

## 📦 部署步骤

### 1. 初始化数据库

如果是全新部署，数据库表会在Docker启动时自动创建。如果是升级现有系统，需要手动执行迁移脚本：

```bash
# 进入数据库容器
docker-compose exec timescaledb psql -U stock_user -d stock_analysis

# 执行迁移脚本（如果之前没有执行过）
\i /docker-entrypoint-initdb.d/03_scheduler_schema.sql
\i /docker-entrypoint-initdb.d/04_scheduler_default_tasks.sql

# 或者在宿主机直接执行
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -f /docker-entrypoint-initdb.d/04_scheduler_default_tasks.sql
```

### 2. 重启Celery Beat服务

更新配置后，需要重启Celery Beat服务以加载新的DatabaseScheduler：

```bash
# 方式1：重启单个服务
docker-compose restart celery_beat

# 方式2：重新构建并启动
docker-compose up -d --build celery_beat

# 查看日志确认启动成功
docker-compose logs -f celery_beat
```

**预期日志输出**：
```
🔧 DatabaseScheduler 已初始化
📋 正在从数据库加载定时任务配置...
  ✓ 加载任务: daily_sentiment_sync -> sentiment.daily_sync_17_30 (30 9 * * 1-5)
  ✓ 加载任务: daily_premarket_workflow -> premarket.full_workflow_8_00 (0 0 * * 1-5)
✅ 定时任务加载完成，共 8 个任务
```

### 3. 验证系统运行

```bash
# 1. 检查Celery Beat是否正常运行
docker-compose ps celery_beat

# 2. 查看Celery Beat日志
docker-compose logs -f celery_beat | grep "DatabaseScheduler"

# 3. 检查数据库中的任务配置
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "SELECT task_name, enabled, cron_expression FROM scheduled_tasks;"

# 4. 访问Admin界面
# http://localhost:3002/settings/scheduler
```

## 🎮 使用指南

### 在Admin界面管理定时任务

1. **访问定时任务管理页面**
   - 登录Admin后台：`http://localhost:3002`
   - 导航：系统设置 → 定时任务

2. **启用定时任务**
   - 找到要启用的任务
   - 点击右侧的开关按钮
   - 等待约30秒，配置自动生效

3. **修改执行时间**
   - 点击任务行的"编辑"按钮
   - 修改Cron表达式（格式：分 时 日 月 周）
   - 点击"保存"
   - 系统会自动验证格式并计算下次执行时间

4. **修改任务参数**
   - 点击"编辑"按钮
   - 在"任务参数"文本框中编辑JSON格式的参数
   - 点击"保存"

### Cron表达式格式说明

格式：`分 时 日 月 周`

| 字段 | 取值范围 | 说明 |
|------|----------|------|
| 分 | 0-59 | 分钟 |
| 时 | 0-23 | 小时（UTC时区） |
| 日 | 1-31 | 每月第几天 |
| 月 | 1-12 | 月份 |
| 周 | 0-6 | 星期几（0=周日） |

**特殊字符**：
- `*` : 每个值
- `,` : 值列表，如 `1,3,5`
- `-` : 值范围，如 `1-5`
- `/` : 步长，如 `*/2` 表示每2个单位

**常用示例**：

```bash
# 每天凌晨1点
0 1 * * *

# 工作日早上9点（UTC时区）
0 9 * * 1-5

# 每2小时
0 */2 * * *

# 每周一早上8点
0 8 * * 1

# 每月1号凌晨2点
0 2 1 * *
```

**时区注意事项**：
- 系统使用UTC时区
- 北京时间需要**减8小时**
- 例如：北京时间9点 = UTC 1点

### 查看任务执行历史

1. 在任务列表中查看：
   - "上次运行"列显示最后执行时间
   - "运行状态"列显示成功/失败状态
   - "已运行X次"显示总执行次数

2. 查看详细历史（未来功能）：
   - 点击任务行可展开查看最近10次执行记录
   - 包含开始时间、结束时间、耗时、错误信息等

## 📊 预定义的定时任务

系统预置了8个定时任务（默认禁用），可以根据需要在Admin界面启用：

| 任务名称 | 模块 | 默认时间（UTC） | 北京时间 | 说明 |
|----------|------|----------------|----------|------|
| daily_sentiment_sync | sentiment | 30 9 * * 1-5 | 17:30 | 每日市场情绪数据同步 |
| daily_sentiment_ai_analysis | sentiment_ai | 0 10 * * 1-5 | 18:00 | AI情绪分析 |
| daily_premarket_workflow | premarket | 0 0 * * 1-5 | 08:00 | 盘前分析工作流 |
| daily_concept_sync | concept | 0 18 * * 0-4 | 02:00 | 概念数据同步 |
| daily_stock_list_sync | stock_list | 0 17 * * * | 01:00 | 股票列表同步 |
| daily_new_stocks_sync | new_stocks | 0 18 * * * | 02:00 | 新股列表同步 |
| weekly_delisted_stocks_sync | delisted_stocks | 0 19 * * 0 | 周一03:00 | 退市股票同步 |
| daily_data_batch_sync | daily | 0 10 * * 1-5 | 18:00 | 批量日线数据同步 |

## 🔧 高级配置

### 修改同步间隔

默认每30秒从数据库同步一次配置。如需修改：

编辑 `backend/app/scheduler/database_scheduler.py`:

```python
def __init__(self, *args, **kwargs):
    self.sync_interval = 60  # 改为60秒
```

### 添加新的任务模块映射

如果要添加新的定时任务类型，需要在两个地方添加映射：

1. **DatabaseScheduler** (`backend/app/scheduler/database_scheduler.py`):

```python
TASK_MAPPING = {
    'sentiment': 'sentiment.daily_sync_17_30',
    'new_module': 'new_module.task_name',  # 添加新映射
    # ...
}
```

2. **Scheduler API** (`backend/app/api/endpoints/scheduler.py`):

```python
valid_modules = [
    "stock_list",
    "new_module",  # 添加新模块
    # ...
]
```

### 使用任务执行日志装饰器

为新的Celery任务添加自动日志记录：

```python
from app.celery_app import celery_app
from app.utils.task_decorator import log_task_execution

@celery_app.task(name='new_module.task_name')
@log_task_execution('task_db_name', 'new_module')
def my_scheduled_task():
    # 任务逻辑
    return {"status": "success", "count": 100}
```

## 🐛 故障排查

### 任务未按预期执行

1. **检查任务是否启用**
   ```sql
   SELECT task_name, enabled FROM scheduled_tasks;
   ```

2. **查看Celery Beat日志**
   ```bash
   docker-compose logs celery_beat | grep -A 5 "检测到定时任务配置变更"
   ```

3. **验证Cron表达式**
   - 在Admin界面编辑任务时会自动验证
   - 或使用在线工具：https://crontab.guru/

### 配置修改未生效

1. **等待30秒**
   - DatabaseScheduler每30秒同步一次

2. **手动触发同步**
   ```bash
   # 重启Celery Beat
   docker-compose restart celery_beat
   ```

3. **检查数据库连接**
   ```bash
   # 查看Celery Beat日志中是否有数据库错误
   docker-compose logs celery_beat | grep -i "error\|failed"
   ```

### 任务执行失败

1. **查看执行历史表**
   ```sql
   SELECT
       task_name,
       status,
       error_message,
       started_at,
       completed_at
   FROM task_execution_history
   ORDER BY started_at DESC
   LIMIT 10;
   ```

2. **查看Celery Worker日志**
   ```bash
   docker-compose logs celery_worker | grep -A 10 "ERROR\|FAILED"
   ```

## 📚 API参考

### 定时任务管理 API

所有API需要Admin权限。

#### 获取任务列表
```http
GET /api/v1/scheduler/tasks
```

#### 更新任务配置
```http
PUT /api/v1/scheduler/tasks/{task_id}
Content-Type: application/json

{
  "cron_expression": "0 10 * * 1-5",
  "enabled": true,
  "params": {"max_stocks": 200}
}
```

#### 启用/禁用任务
```http
POST /api/v1/scheduler/tasks/{task_id}/toggle
```

#### 验证Cron表达式
```http
POST /api/v1/scheduler/validate-cron?cron_expression=0 9 * * 1-5
```

#### 获取执行历史
```http
GET /api/v1/scheduler/tasks/{task_id}/history?limit=20
```

## 🔐 安全建议

1. **限制Admin访问**
   - 只有管理员账户可以修改定时任务配置
   - 建议启用API访问日志审计

2. **参数验证**
   - 系统会验证Cron表达式格式
   - 任务参数必须是有效的JSON格式

3. **备份配置**
   ```bash
   # 导出定时任务配置
   docker-compose exec timescaledb pg_dump -U stock_user -d stock_analysis -t scheduled_tasks > scheduled_tasks_backup.sql
   ```

## 📈 监控建议

1. **使用Flower监控Celery**
   ```bash
   # 访问Flower界面
   http://localhost:5555
   ```

2. **定期检查失败任务**
   ```sql
   SELECT
       task_name,
       COUNT(*) as failure_count
   FROM task_execution_history
   WHERE status = 'failed'
       AND started_at > NOW() - INTERVAL '7 days'
   GROUP BY task_name
   ORDER BY failure_count DESC;
   ```

3. **监控任务执行时长**
   ```sql
   SELECT
       task_name,
       AVG(duration_seconds) as avg_duration,
       MAX(duration_seconds) as max_duration
   FROM task_execution_history
   WHERE status = 'success'
   GROUP BY task_name;
   ```

## 🎉 总结

本系统通过自定义DatabaseScheduler实现了完全动态的定时任务配置管理，相比传统的硬编码方式具有以下优势：

- **灵活性**: 无需修改代码即可调整任务执行时间
- **便捷性**: 在Web界面即可管理所有定时任务
- **可靠性**: 自动记录执行日志，便于追踪和排查问题
- **实时性**: 配置修改后30秒内自动生效

如有问题，请查看故障排查章节或联系系统管理员。
