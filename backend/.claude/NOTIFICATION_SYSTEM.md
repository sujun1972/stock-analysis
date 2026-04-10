# 通知系统架构

## 系统概述

多渠道文字报告推送系统，支持 Email、Telegram Bot、站内消息三种渠道。

**完整功能包含**:
- ✅ 后端: 多渠道发送、模板系统、频率限制、监控告警
- ✅ Admin: 渠道配置、模板管理、监控面板
- ✅ 用户前端: 通知设置、站内消息中心、未读角标

## 核心组件

### 1. 通知服务 (`notification_service.py`)
- 用户配置管理
- 订阅用户查询
- 报告内容渲染（已被模板系统替代）
- 通知日志管理

### 2. 渠道发送器
- **Email**: `email_sender.py` - SMTP 发送（异步，支持重试）
- **Telegram**: `telegram_sender.py` - Bot API 发送（支持长消息分割）
- **站内消息**: 直接写入 `in_app_notifications` 表

### 3. 模板渲染器 (`template_renderer.py`)
- Jinja2 模板引擎
- 数据库驱动的模板管理
- 支持 Email HTML、Telegram Markdown、站内纯文本
- 模板预览和验证

### 4. 频率限制器 (`notification_rate_limiter.py`)
- 每日/每小时限制
- 跨天自动重置
- 渠道级别统计

### 5. Celery 异步任务 (`notification_tasks.py`)
- `send_email_notification_task` - Email 发送（支持连接池优化）
- `send_telegram_notification_task` - Telegram 发送
- `send_in_app_notification_task` - 站内消息
- `schedule_report_notification_task` - 批量调度（核心任务）
- `notification_health_check_task` - 健康检查（每小时，Phase 3）
- `reset_daily_rate_limits_task` - 重置频率限制（每天凌晨，Phase 3）
- `cleanup_expired_notifications_task` - 清理过期消息（每天凌晨）

### 6. 监控服务 (`notification_monitor.py`, Phase 3)
- 发送成功率统计（总体 + 按渠道）
- 失败记录分析和失败原因统计
- 渠道性能分析（成功率、平均送达时间、高峰时段）
- 每日发送趋势分析
- 实时监控数据
- 健康检查

### 7. 告警服务 (`notification_alert.py`, Phase 3)
- 自动健康检查并触发告警
- 多级告警阈值（成功率、失败率、积压）
- 渠道异常检测
- 管理员站内消息自动通知
- 失败原因分析与优化建议
- 趋势分析（improving/worsening/stable）

### 8. 用户前端组件
- **通知设置页面** (`/settings/notifications`) - 用户配置订阅偏好、渠道管理
- **通知中心** (`/notifications`) - 查看站内消息、标记已读
- **未读角标** (`NotificationBadge`) - 实时显示未读数量（30秒轮询）
- **导航集成** - 桌面端（下拉菜单）+ 移动端（侧边栏）

## 数据模型

### 用户配置
```
user_notification_settings
├── 渠道启用状态 (email_enabled, telegram_enabled, in_app_enabled)
├── 联系方式 (email_address, telegram_chat_id)
├── 订阅偏好 (subscribe_sentiment_report, subscribe_premarket_report...)
├── 报告格式 (full/summary/action_only)
└── 频率限制 (max_daily_notifications, daily_notification_count)
```

### 通知模板
```
notification_templates
├── template_name (唯一标识)
├── notification_type (sentiment_report, premarket_report...)
├── channel (email, telegram, in_app)
├── subject_template (Jinja2)
├── content_template (Jinja2)
├── available_variables (可用变量列表)
└── example_data (预览用示例数据)
```

### 频率限制
```
notification_rate_limits
├── user_id + notification_date (唯一键)
├── email_count, telegram_count, in_app_count
├── total_count
└── hourly_counts (JSON: {"18": 3, "19": 2})
```

## 工作流程

### 报告推送流程
```
报告生成服务
    ↓
schedule_report_notification_task (Celery)
    ↓
查询订阅用户 → 检查频率限制 → 渲染模板
    ↓
创建通知日志 (pending)
    ↓
异步推送到各渠道队列
    ├─→ Email 队列 → send_email_notification_task → 更新日志 (sent/failed)
    ├─→ Telegram 队列 → send_telegram_notification_task → 更新日志
    └─→ 站内消息队列 → send_in_app_notification_task
```

## 配置说明

### 渠道配置 (Admin 后台)
```json
// Email
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_username": "user@example.com",
  "smtp_password": "app_password",
  "smtp_use_tls": true,
  "from_email": "noreply@example.com",
  "from_name": "股票分析系统"
}

// Telegram
{
  "bot_token": "1234567890:ABCDEF...",
  "parse_mode": "Markdown",
  "timeout": 30
}
```

### 触发通知
```python
from app.tasks.notification_tasks import schedule_report_notification_task

# 手动触发
schedule_report_notification_task.delay(
    report_type='sentiment_report',
    trade_date='2026-03-15',
    report_data={
        'trade_date': '2026-03-15',
        'space_analysis': '...',
        'sentiment_analysis': '...',
        'capital_flow_analysis': '...',
        'tomorrow_tactics': '...',
        'generated_at': '2026-03-15 18:30:00'
    }
)
```

## 模板变量参考

### 盘后情绪报告
- `trade_date`: 交易日期
- `space_analysis`: 空间分析（龙头高度）
- `sentiment_analysis`: 情绪分析（赚钱效应）
- `capital_flow_analysis`: 资金流向分析
- `tomorrow_tactics`: 明日战术
- `generated_at`: 生成时间

### 盘前碰撞报告
- `trade_date`: 交易日期
- `macro_tone`: 宏观定调
- `position_check`: 持仓排雷
- `plan_adjustment`: 计划修正
- `bidding_watch`: 竞价盯盘
- `generated_at`: 生成时间

### 回测结果
- `strategy_name`: 策略名称
- `start_date`, `end_date`: 回测周期
- `total_return`, `annual_return`: 收益率
- `max_drawdown`: 最大回撤
- `sharpe_ratio`: 夏普比率
- `win_rate`: 胜率
- `completed_at`: 完成时间

## 开发指南

### 添加新报告类型
1. 在 `user_notification_settings` 添加订阅字段
2. 在 `notification_templates` 创建模板（Email/Telegram/站内消息）
3. 更新 `NotificationService.get_subscribers()` 的 `subscription_field_map`
4. 在报告生成服务中触发 `schedule_report_notification_task`

### 创建新模板
```sql
INSERT INTO notification_templates (
    template_name, notification_type, channel,
    subject_template, content_template,
    available_variables, example_data
) VALUES (
    'new_report_telegram_full',
    'new_report',
    'telegram',
    NULL,
    '📊 *{{ title }}*\n\n{{ content }}',
    '["title", "content", "generated_at"]'::jsonb,
    '{"title": "测试", "content": "内容"}'::jsonb
);
```

## 用户前端 API 端点

**路由前缀**: `/api/notifications`（需认证）

| 端点 | 方法 | 描述 |
|------|------|------|
| `/settings` | GET | 获取用户通知配置 |
| `/settings` | PUT | 更新用户通知配置 |
| `/in-app` | GET | 获取站内消息列表 |
| `/in-app/{id}/read` | POST | 标记消息为已读 |
| `/in-app/read-all` | POST | 全部标记为已读 |
| `/unread-count` | GET | 获取未读消息数量 |
| `/logs` | GET | 获取通知发送历史 |

**重要**: 所有端点必须使用 `ApiResponse.success(...).to_dict()` 返回，确保前端收到 `success` 字段。

## 监控和调试

### Phase 3: 监控面板 (Admin 后台)

访问路径: `/monitoring/notifications`

**功能**:
- 健康状态概览（系统状态、24h成功率、失败率、待发送）
- 实时统计卡片（总数、成功率、最近1小时、待发送队列）
- 发送趋势图表（最近7天趋势）
- 渠道性能分析（Email/Telegram/站内消息独立卡片）
- 失败分析（饼图分布 + 详细列表 + 最近失败记录）
- 自动刷新（每分钟） + 手动刷新按钮
- 执行健康检查按钮

### 监控 API 端点

**路由前缀**: `/api/notification-monitoring`（仅超级管理员）

| 端点 | 方法 | 描述 |
|------|------|------|
| `/statistics` | GET | 获取成功率统计 |
| `/failures` | GET | 获取失败记录列表 |
| `/failure-reasons` | GET | 获取失败原因汇总 |
| `/channel-performance` | GET | 获取渠道性能分析 |
| `/daily-trend` | GET | 获取每日发送趋势 |
| `/realtime` | GET | 获取实时监控数据 |
| `/health-check` | GET | 执行健康检查 |
| `/check-and-alert` | POST | 执行健康检查并触发告警 |
| `/failure-analysis` | GET | 获取失败分析和优化建议 |
| `/user-stats/{user_id}` | GET | 获取用户通知统计 |

### 告警阈值

| 指标 | 警告阈值 | 严重阈值 |
|------|---------|---------|
| 成功率 | < 90% | < 70% |
| 失败率 | > 10% | > 20% |
| 待发送积压 | > 100 条 | > 500 条 |
| 平均送达时间 | > 300s | - |

### 性能优化 (Phase 3)

**Email 连接池**:
- 默认池大小: 5 个连接
- 批量发送性能提升: **50-70%**
- 使用方式: `EmailSender(config, use_pool=True)`

**建议配置**:
- 小流量 (< 100 封/小时): 池大小 = 3
- 中流量 (100-500 封/小时): 池大小 = 5
- 大流量 (> 500 封/小时): 池大小 = 10

### 查看 Celery 日志
```bash
docker-compose logs -f celery_worker
docker-compose logs -f celery_beat
```

### 查看通知日志
```sql
SELECT * FROM notification_logs
WHERE created_at > NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;
```

### 查看频率限制状态
```sql
SELECT user_id, notification_date, total_count, hourly_counts
FROM notification_rate_limits
WHERE notification_date = CURRENT_DATE
ORDER BY total_count DESC;
```

### 手动触发健康检查
```bash
curl -X POST http://localhost:8000/api/notification-monitoring/check-and-alert \
  -H "Authorization: Bearer <admin_token>"
```
