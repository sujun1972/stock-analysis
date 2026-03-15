# 通知系统 Phase 2 功能说明

## 新增功能

### 1. Telegram Bot 集成
- 完整的 Telegram 消息推送支持
- 自动处理长消息分割（4096 字符限制）
- 连接测试和 Chat ID 验证
- 重试机制（3 次，指数退避）

### 2. Jinja2 模板系统
- 数据库驱动的动态模板管理
- 支持 Email（HTML）、Telegram（Markdown）、站内消息多渠道
- 模板预览和语法验证
- 5 个默认模板（盘后情绪、盘前碰撞、回测结果）

### 3. 通知频率限制
- 每日/每小时双重限制
- 跨天自动重置
- 渠道级别统计
- 全局统计报告

## 核心文件

**服务层**:
- `backend/app/services/telegram_sender.py` - Telegram 发送器
- `backend/app/services/template_renderer.py` - 模板渲染引擎
- `backend/app/services/notification_rate_limiter.py` - 频率限制器

**数据模型**:
- `backend/app/models/notification_template.py` - 模板表
- `backend/app/models/notification_rate_limit.py` - 频率限制表

**数据库迁移**:
- `db_init/phase2_notification_templates.sql` - Phase 2 Schema

## 使用示例

### Telegram 发送
```python
from app.services.telegram_sender import TelegramSender

config = {
    "bot_token": "YOUR_BOT_TOKEN",
    "parse_mode": "Markdown",
    "timeout": 30
}
sender = TelegramSender(config)
sender.send(chat_id="123456789", message="📊 测试消息")
```

### 模板渲染
```python
from app.services.template_renderer import TemplateRenderer

renderer = TemplateRenderer(db)
result = renderer.render_notification(
    notification_type='sentiment_report',
    channel='telegram',
    context={'trade_date': '2026-03-15', ...},
    content_format='full'
)
```

### 频率限制
```python
from app.services.notification_rate_limiter import NotificationRateLimiter

limiter = NotificationRateLimiter(db)
check = limiter.check_rate_limit(user_id=1)
if check['allowed']:
    # 发送通知
    limiter.increment_counter(user_id=1, channel='email')
```

## 数据库表

- `notification_templates` - 通知模板（支持 Jinja2）
- `notification_rate_limits` - 频率限制记录
- `user_notification_settings` - 新增频率限制字段

## 配置

### Telegram Bot 设置
1. 通过 @BotFather 创建 Bot，获取 Token
2. 用户通过 @userinfobot 获取 Chat ID
3. 在 Admin 后台配置 Bot Token
4. 用户在前端设置中配置 Chat ID

### 依赖
- `jinja2>=3.1.0` - 模板引擎
- `requests>=2.31.0` - Telegram HTTP 请求
