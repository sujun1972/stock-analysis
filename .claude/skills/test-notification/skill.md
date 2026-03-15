# 测试通知系统功能

测试通知系统的各项功能，包括模板渲染、Telegram 发送、频率限制等。

## 执行步骤

1. **检查数据库连接和模板数据**
   - 验证 `notification_templates` 表是否存在
   - 检查已创建的模板数量和内容

2. **测试模板渲染**
   - 使用 `TemplateRenderer` 渲染各种报告类型
   - 测试 Email HTML、Telegram Markdown、站内消息格式
   - 验证 Jinja2 变量替换正确性

3. **测试 Telegram 发送器**（可选，需要配置）
   - 验证 Bot Token 配置
   - 测试连接和 Chat ID 验证
   - 测试消息发送（包括长消息分割）

4. **测试频率限制**
   - 检查用户频率限制配置
   - 测试每日/每小时限制逻辑
   - 验证计数器增加和重置

5. **集成测试**
   - 手动触发 `schedule_report_notification_task`
   - 检查 Celery 任务日志
   - 验证通知日志记录

## 测试代码

```python
from app.core.database import get_db
from app.services.template_renderer import TemplateRenderer
from app.services.telegram_sender import TelegramSender
from app.services.notification_rate_limiter import NotificationRateLimiter

db = next(get_db())

# 1. 测试模板渲染
renderer = TemplateRenderer(db)
result = renderer.render_notification(
    notification_type='sentiment_report',
    channel='telegram',
    context={
        'trade_date': '2026-03-15',
        'space_analysis': '测试空间分析',
        'sentiment_analysis': '测试情绪分析',
        'generated_at': '2026-03-15 18:30:00'
    },
    content_format='full'
)
print(f"主题: {result['subject']}")
print(f"内容: {result['content'][:200]}...")

# 2. 测试频率限制
limiter = NotificationRateLimiter(db)
check = limiter.check_rate_limit(user_id=1)
print(f"允许发送: {check['allowed']}, 剩余配额: {check['remaining_quota']}")

# 3. 测试 Telegram（需要配置）
# config = {
#     "bot_token": "YOUR_BOT_TOKEN",
#     "parse_mode": "Markdown",
#     "timeout": 30
# }
# sender = TelegramSender(config)
# result = sender.test_connection(chat_id="YOUR_CHAT_ID")
# print(result)

db.close()
```

## 预期结果

- ✅ 模板渲染成功，内容包含正确的变量值
- ✅ 频率限制检查正常，返回正确的配额信息
- ✅ Telegram 连接测试成功（如果配置了 Bot）
- ✅ Celery 任务日志显示通知发送成功

## 故障排查

### 模板渲染失败
- 检查 `notification_templates` 表是否有数据
- 验证模板的 Jinja2 语法是否正确
- 检查传入的 context 变量是否完整

### Telegram 发送失败
- 验证 Bot Token 是否正确
- 检查 Chat ID 是否有效（用户需先给 Bot 发消息）
- 查看网络连接是否正常

### 频率限制异常
- 检查 `user_notification_settings` 表中用户配置
- 验证 `notification_rate_limits` 表的数据
- 确认日期重置逻辑是否正常工作
