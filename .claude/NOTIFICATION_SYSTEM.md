# 通知系统架构

## 系统概述

多渠道文字报告推送系统，支持 Email、Telegram Bot、站内消息三种渠道。

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
- `send_email_notification_task` - Email 发送
- `send_telegram_notification_task` - Telegram 发送
- `send_in_app_notification_task` - 站内消息
- `schedule_report_notification_task` - 批量调度（核心任务）

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

## 监控和调试

### 查看 Celery 日志
```bash
docker-compose logs -f celery_worker
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
