# 📋 股票分析系统 - 通知发送功能完整实施方案

**版本**: v1.0
**创建日期**: 2026-03-15
**目标**: 实现多渠道文字报告推送系统（Email、Telegram、站内消息），支持管理后台配置

---

## 📑 目录

1. [需求概述](#1-需求概述)
2. [系统架构设计](#2-系统架构设计)
3. [数据库设计](#3-数据库设计)
4. [后端实现](#4-后端实现)
5. [Admin管理后台实现](#5-admin管理后台实现)
6. [用户前端实现](#6-用户前端实现)
7. [部署与测试](#7-部署与测试)
8. [实施计划](#8-实施计划)

---

## 1. 需求概述

### 1.1 业务需求

系统每日生成多种分析报告（文字内容），需要推送给用户：

| 报告类型 | 生成时间 | 内容描述 | 存储表 |
|---------|---------|---------|--------|
| **盘后情绪分析报告** | 每日 18:00 | 四个灵魂拷问分析（空间、情绪、资金、战术） | `market_sentiment_ai_analysis` |
| **盘前碰撞分析报告** | 每日 08:00 | 四维分析（宏观定调、持仓排雷、计划修正、竞价盯盘） | `premarket_collision_analysis` |
| **回测完成通知** | 异步触发 | 策略回测结果通知 | `backtest_results` |

### 1.2 功能需求

#### 1.2.1 核心功能
- ✅ **多渠道推送**: Email、Telegram Bot、站内消息
- ✅ **管理后台配置**: 通知渠道参数可视化管理（SMTP、Telegram Bot Token 等）
- ✅ **用户订阅管理**: 用户可配置订阅偏好、发送时间、内容格式
- ✅ **异步队列**: 基于 Celery + Redis 的消息队列，避免阻塞
- ✅ **失败重试**: Email/Telegram 失败自动重试 3 次（指数退避）
- ✅ **发送日志**: 完整的发送记录和状态追踪

#### 1.2.2 可配置项

**系统级配置（Admin 后台）**:
- SMTP 服务器参数（Host、Port、用户名、密码、发件人）
- Telegram Bot Token 和默认配置
- 通道启用/禁用、优先级设置

**用户级配置（用户前端）**:
- 订阅的报告类型
- 接收渠道选择（Email/Telegram/站内消息）
- 报告内容格式（完整报告/摘要/仅行动指令）
- 发送时间偏好

### 1.3 技术约束

- ✅ 利用现有 Celery + Redis 基础设施
- ✅ Admin 后台使用现有技术栈（Next.js 14 + shadcn/ui）
- ✅ 敏感信息（Token、密码）后端脱敏存储
- ✅ 兼容现有 API 统一响应格式

---

## 2. 系统架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         报告生成层                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ 情绪分析服务  │  │ 盘前碰撞服务  │  │  回测任务    │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
│         │ 报告保存完成       │ 报告保存完成      │ 任务完成           │
│         └──────────────────┴──────────────────┴──────────┐         │
└───────────────────────────────────────────────────────────┼─────────┘
                                                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│              通知调度器 (Celery Task)                                 │
│  • 接收报告生成事件                                                   │
│  • 查询订阅用户列表 (user_notification_settings)                     │
│  • 根据用户偏好渲染内容 (NotificationService.render_report)          │
│  • 创建通知日志记录 (notification_logs)                               │
│  • 推送任务到各渠道队列                                               │
└──────────────────────────┬────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Email 队列    │  │Telegram 队列  │  │ 站内消息队列  │
│ (Redis List)  │  │ (Redis List)  │  │ (Redis List)  │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Email Worker  │  │Telegram Worker│  │ 站内消息Worker│
│ (Celery Task) │  │ (Celery Task) │  │ (Celery Task) │
│ • 查询 SMTP   │  │ • 查询 Bot    │  │ • 直接写库    │
│   配置        │  │   Token       │  │ • 无需重试    │
│ • SMTP 发送   │  │ • Bot API 发送│  │               │
│ • 重试 3 次   │  │ • 重试 3 次   │  │               │
│ • 更新日志    │  │ • 更新日志    │  │               │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
            ┌──────────────────────────┐
            │   通知日志表              │
            │ (notification_logs)      │
            │  • pending → sent/failed │
            └──────────────────────────┘
```

### 2.2 核心流程

#### 2.2.1 报告推送流程

1. **报告生成服务** 完成分析，保存结果到数据库
2. **触发通知调度任务** (`schedule_report_notification_task`)
3. **查询订阅用户列表** (从 `user_notification_settings` 表)
4. **渲染报告内容** (根据用户偏好：完整/摘要/仅行动指令)
5. **创建通知日志** (状态为 `pending`)
6. **推送到各渠道队列** (Email/Telegram/站内消息)
7. **Worker 异步消费**
   - 查询渠道配置 (SMTP/Bot Token)
   - 执行发送
   - 更新日志状态 (`sent` 或 `failed`)
   - 失败自动重试 (最多 3 次，指数退避)

#### 2.2.2 用户订阅配置流程

1. 用户访问通知设置页面
2. 更新订阅偏好（报告类型、渠道、格式）
3. 后端保存到 `user_notification_settings` 表
4. 下次报告生成时按新配置推送

---

## 3. 数据库设计

### 3.1 ��知渠道配置表 (`notification_channel_configs`)

**用途**: 管理员在 Admin 后台配置通知渠道参数（SMTP、Telegram Bot 等）

```sql
CREATE TABLE notification_channel_configs (
    id SERIAL PRIMARY KEY,

    -- 渠道标识
    channel_type VARCHAR(20) NOT NULL UNIQUE,  -- 'email', 'telegram'
    channel_name VARCHAR(100) NOT NULL,        -- '邮件通知', 'Telegram Bot'

    -- 启用状态
    is_enabled BOOLEAN DEFAULT false,
    is_default BOOLEAN DEFAULT false,          -- 是否为默认渠道
    priority INTEGER DEFAULT 10,               -- 优先级（数字越小优先级越高）

    -- 配置参数（JSON 格式，根据渠道类型不同）
    config JSONB NOT NULL DEFAULT '{}',
    -- Email 示例:
    -- {
    --   "smtp_host": "smtp.gmail.com",
    --   "smtp_port": 587,
    --   "smtp_username": "noreply@example.com",
    --   "smtp_password": "********",  -- 前端脱敏显示
    --   "smtp_use_tls": true,
    --   "from_email": "noreply@example.com",
    --   "from_name": "股票分析系统"
    -- }
    -- Telegram 示例:
    -- {
    --   "bot_token": "1234567890:ABCDEF********",  -- 前端脱敏显示
    --   "webhook_url": "https://api.telegram.org/bot{token}/sendMessage",
    --   "parse_mode": "Markdown",
    --   "timeout": 30
    -- }

    -- 描述信息
    description TEXT,

    -- 测试状态
    last_test_at TIMESTAMPTZ,                  -- 最后测试时间
    last_test_status VARCHAR(20),              -- 'success', 'failed'
    last_test_message TEXT,                    -- 测试结果消息

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notification_channel_configs_type ON notification_channel_configs(channel_type);
CREATE INDEX idx_notification_channel_configs_enabled ON notification_channel_configs(is_enabled);

-- 自动更新 updated_at
CREATE TRIGGER update_notification_channel_configs_updated_at
BEFORE UPDATE ON notification_channel_configs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 初始化默认配置
INSERT INTO notification_channel_configs (channel_type, channel_name, is_enabled, config, description) VALUES
('email', '邮件通知', false, '{
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password": "",
    "smtp_use_tls": true,
    "from_email": "noreply@example.com",
    "from_name": "股票分析系统"
}'::jsonb, 'SMTP 邮件推送服务'),
('telegram', 'Telegram Bot', false, '{
    "bot_token": "",
    "parse_mode": "Markdown",
    "timeout": 30
}'::jsonb, 'Telegram Bot 消息推送');
```

### 3.2 用户通知配置表 (`user_notification_settings`)

**用途**: 用户个性化订阅配置

```sql
CREATE TABLE user_notification_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 通知渠道启用状态
    email_enabled BOOLEAN DEFAULT false,
    telegram_enabled BOOLEAN DEFAULT false,
    in_app_enabled BOOLEAN DEFAULT true,           -- 站内消息默认开启

    -- 联系方式
    email_address VARCHAR(255),
    telegram_chat_id VARCHAR(100),                  -- 用户的 Telegram Chat ID
    telegram_username VARCHAR(100),

    -- 报告订阅偏好
    subscribe_sentiment_report BOOLEAN DEFAULT false,    -- 盘后情绪报告
    subscribe_premarket_report BOOLEAN DEFAULT false,    -- 盘前碰撞报告
    subscribe_backtest_report BOOLEAN DEFAULT true,      -- 回测完成通知
    subscribe_strategy_alert BOOLEAN DEFAULT true,       -- 策略审核通知

    -- 发送时间偏好
    sentiment_report_time TIME DEFAULT '18:30',          -- 盘后报告发送时间
    premarket_report_time TIME DEFAULT '08:00',          -- 盘前报告发送时间

    -- 报告内容偏好
    report_format VARCHAR(20) DEFAULT 'full',            -- 'full'=完整报告, 'summary'=摘要, 'action_only'=仅行动指令

    -- 频率控制
    max_daily_notifications INTEGER DEFAULT 10,          -- 每日最大通知数

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id),
    CONSTRAINT valid_report_format CHECK (report_format IN ('full', 'summary', 'action_only'))
);

CREATE INDEX idx_user_notification_settings_user_id ON user_notification_settings(user_id);
CREATE INDEX idx_user_notification_settings_sentiment ON user_notification_settings(subscribe_sentiment_report) WHERE subscribe_sentiment_report = true;
CREATE INDEX idx_user_notification_settings_premarket ON user_notification_settings(subscribe_premarket_report) WHERE subscribe_premarket_report = true;

-- 自动更新 updated_at
CREATE TRIGGER update_user_notification_settings_updated_at
BEFORE UPDATE ON user_notification_settings
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 新用户自动创建默认配置（触发器）
CREATE OR REPLACE FUNCTION create_default_notification_settings()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO user_notification_settings (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_create_default_notification_settings
AFTER INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION create_default_notification_settings();
```

### 3.3 通知发送记录表 (`notification_logs`)

**用途**: 追踪每条通知的发送状态和历史

```sql
CREATE TABLE notification_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 通知内容
    notification_type VARCHAR(50) NOT NULL,              -- 'sentiment_report', 'premarket_report', 'backtest_result'
    content_type VARCHAR(20) NOT NULL,                   -- 'full', 'summary', 'action_only'
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,

    -- 发送渠道
    channel VARCHAR(20) NOT NULL,                        -- 'email', 'telegram', 'in_app'

    -- 发送状态
    status VARCHAR(20) NOT NULL DEFAULT 'pending',       -- 'pending', 'sent', 'failed', 'skipped'
    sent_at TIMESTAMPTZ,
    failed_reason TEXT,
    retry_count INTEGER DEFAULT 0,

    -- 关联数据
    business_date DATE,                                   -- 关联的交易日
    reference_id VARCHAR(100),                            -- 关联的业务ID (如回测ID)

    -- Celery 任务ID
    task_id VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_channel CHECK (channel IN ('email', 'telegram', 'in_app')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'sent', 'failed', 'skipped'))
);

CREATE INDEX idx_notification_logs_user_id ON notification_logs(user_id);
CREATE INDEX idx_notification_logs_status ON notification_logs(status);
CREATE INDEX idx_notification_logs_created_at ON notification_logs(created_at DESC);
CREATE INDEX idx_notification_logs_business_date ON notification_logs(business_date);
CREATE INDEX idx_notification_logs_type ON notification_logs(notification_type);

-- 自动更新 updated_at
CREATE TRIGGER update_notification_logs_updated_at
BEFORE UPDATE ON notification_logs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 分区表 (按月分区，提升查询性能)
SELECT create_hypertable('notification_logs', 'created_at', chunk_time_interval => INTERVAL '1 month');

-- 自动清理 6 个月前的日志（保留策略）
SELECT add_retention_policy('notification_logs', INTERVAL '6 months');
```

### 3.4 站内消息表 (`in_app_notifications`)

**用途**: 存储站内消息（用户前端的通知中心）

```sql
CREATE TABLE in_app_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- 消息内容
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL,              -- 'sentiment_report', 'premarket_report', 'backtest_result', 'system_alert'

    -- 状态
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,

    -- 优先级
    priority VARCHAR(20) DEFAULT 'normal',               -- 'high', 'normal', 'low'

    -- 关联数据
    business_date DATE,
    reference_id VARCHAR(100),
    metadata JSONB,                                       -- 额外数据 (JSON格式)

    -- 过期时间
    expires_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_priority CHECK (priority IN ('high', 'normal', 'low'))
);

CREATE INDEX idx_in_app_notifications_user_id_unread ON in_app_notifications(user_id, is_read) WHERE is_read = false;
CREATE INDEX idx_in_app_notifications_created_at ON in_app_notifications(created_at DESC);
CREATE INDEX idx_in_app_notifications_expires_at ON in_app_notifications(expires_at) WHERE expires_at IS NOT NULL;

-- 分区表 (按月分区)
SELECT create_hypertable('in_app_notifications', 'created_at', chunk_time_interval => INTERVAL '1 month');

-- 自动清理 3 个月前的已读消息
SELECT add_retention_policy('in_app_notifications', INTERVAL '3 months',
    'SELECT id FROM in_app_notifications WHERE is_read = true');
```

### 3.5 通知模板表 (`notification_templates`) - 可选扩展

**用途**: 支持 Jinja2 模板渲染（Phase 2 功能）

```sql
CREATE TABLE notification_templates (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(100) NOT NULL UNIQUE,
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL,                        -- 'email', 'telegram', 'in_app'

    -- 模板内容
    subject_template TEXT,                                -- 邮件主题/消息标题模板
    content_template TEXT NOT NULL,                       -- 内容模板 (支持Jinja2变量)

    -- 变量说明
    available_variables JSONB,                            -- 可用变量列表 (JSON数组)

    -- 状态
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notification_templates_type_channel ON notification_templates(notification_type, channel);
```

---

## 4. 后端实现

### 4.1 目录结构

```
backend/app/
├── api/endpoints/
│   ├── notification_channels.py      # Admin 后台：通知渠道配置 CRUD
│   └── notifications.py               # 用户前端：订阅配置、站内消息
├── services/
│   ├── notification_service.py        # 通知服务层（核心逻辑）
│   ├── notification_channel_service.py # 渠道配置服务
│   ├── email_sender.py                # Email 发送器
│   └── telegram_sender.py             # Telegram 发送器
├── tasks/
│   ├── notification_tasks.py          # Celery 通知任务
│   └── notification_scheduler.py      # 定时批量发送任务
├── schemas/
│   ├── notification_channel.py        # 通知渠道配置 Schema
│   └── notification.py                # 用户通知配置 Schema
└── models/
    ├── notification_channel_config.py # ORM 模型
    └── notification_setting.py        # ORM 模型
```

### 4.2 API 端点 - 通知渠道配置 (Admin 后台)

**文件**: `backend/app/api/endpoints/notification_channels.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_super_admin  # 仅超级管理员可访问
from app.schemas.notification_channel import (
    NotificationChannelConfigResponse,
    NotificationChannelConfigCreate,
    NotificationChannelConfigUpdate,
    TestChannelResponse
)
from app.services.notification_channel_service import NotificationChannelService

router = APIRouter()

@router.get("", response_model=List[NotificationChannelConfigResponse])
def get_all_notification_channels(
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """获取所有通知渠道配置（仅管理员）"""
    service = NotificationChannelService(db)
    return service.get_all_channels()


@router.get("/{channel_type}", response_model=NotificationChannelConfigResponse)
def get_notification_channel(
    channel_type: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """获取指定渠道配置"""
    service = NotificationChannelService(db)
    channel = service.get_channel_by_type(channel_type)
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")
    return channel


@router.put("/{channel_type}", response_model=NotificationChannelConfigResponse)
def update_notification_channel(
    channel_type: str,
    data: NotificationChannelConfigUpdate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """更新渠道配置（敏感信息加密存储）"""
    service = NotificationChannelService(db)
    return service.update_channel(channel_type, data)


@router.post("/{channel_type}/toggle", response_model=NotificationChannelConfigResponse)
def toggle_notification_channel(
    channel_type: str,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """启用/禁用渠道"""
    service = NotificationChannelService(db)
    return service.toggle_channel(channel_type)


@router.post("/{channel_type}/test", response_model=TestChannelResponse)
async def test_notification_channel(
    channel_type: str,
    test_target: str,  # 测试目标：邮箱地址或 Telegram Chat ID
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_super_admin)
):
    """测试渠道连接（发送测试消息）"""
    service = NotificationChannelService(db)
    result = await service.test_channel(channel_type, test_target)
    return result
```

### 4.3 API 端点 - 用户通知配置

**文件**: `backend/app/api/endpoints/notifications.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.schemas.notification import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    InAppNotificationResponse,
    NotificationLogResponse
)
from app.services.notification_service import NotificationService

router = APIRouter()

@router.get("/settings", response_model=NotificationSettingsResponse)
def get_notification_settings(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取用户通知配置"""
    service = NotificationService(db)
    return service.get_user_settings(current_user.id)


@router.put("/settings", response_model=NotificationSettingsResponse)
def update_notification_settings(
    settings: NotificationSettingsUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新用户通知配置"""
    service = NotificationService(db)
    return service.update_user_settings(current_user.id, settings)


@router.get("/in-app", response_model=List[InAppNotificationResponse])
def get_in_app_notifications(
    unread_only: bool = Query(False, description="仅未读消息"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取站内消息列表"""
    service = NotificationService(db)
    return service.get_in_app_notifications(
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset
    )


@router.post("/in-app/{notification_id}/read")
def mark_notification_as_read(
    notification_id: int,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """标记消息为已读"""
    service = NotificationService(db)
    service.mark_as_read(notification_id, current_user.id)
    return {"success": True, "message": "已标记为已读"}


@router.post("/in-app/read-all")
def mark_all_as_read(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """全部标记为已读"""
    service = NotificationService(db)
    count = service.mark_all_as_read(current_user.id)
    return {"success": True, "message": f"已标记 {count} 条消息为已读"}


@router.get("/logs", response_model=List[NotificationLogResponse])
def get_notification_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取通知发送历史"""
    service = NotificationService(db)
    return service.get_notification_logs(current_user.id, limit, offset)


@router.get("/unread-count")
def get_unread_count(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取未读消息数量"""
    service = NotificationService(db)
    count = service.get_unread_count(current_user.id)
    return {"unread_count": count}
```

### 4.4 Celery 通知任务

**文件**: `backend/app/tasks/notification_tasks.py`

```python
from celery import shared_task
from celery.utils.log import get_task_logger
from typing import Dict, Any
from datetime import datetime

from app.services.notification_service import NotificationService
from app.services.email_sender import EmailSender
from app.services.telegram_sender import TelegramSender
from app.core.database import get_db

logger = get_task_logger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_notification_task(
    self,
    user_id: int,
    email_address: str,
    subject: str,
    html_content: str,
    notification_log_id: int
):
    """
    发送邮件通知

    重试策略: 3次，指数退避 (60s, 120s, 240s)
    """
    try:
        logger.info(f"发送邮件: user_id={user_id}, email={email_address}")

        # 查询 SMTP 配置
        db = next(get_db())
        service = NotificationService(db)
        smtp_config = service.get_channel_config('email')

        if not smtp_config or not smtp_config.get('smtp_host'):
            raise ValueError("SMTP 配置不存在或未启用")

        # 发送邮件
        email_sender = EmailSender(smtp_config)
        success = email_sender.send(
            to_email=email_address,
            subject=subject,
            html_content=html_content
        )

        if success:
            service.update_notification_log(notification_log_id, 'sent')
            logger.info(f"邮件发送成功: log_id={notification_log_id}")
        else:
            raise Exception("邮件发送失败")

    except Exception as exc:
        logger.error(f"邮件发送失败: {exc}")
        service.update_notification_log(
            notification_log_id,
            'failed',
            failed_reason=str(exc),
            retry_count=self.request.retries
        )

        # 指数退避重试
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        else:
            logger.error(f"邮件最终发送失败: log_id={notification_log_id}")


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_telegram_notification_task(
    self,
    user_id: int,
    chat_id: str,
    message: str,
    notification_log_id: int
):
    """发送 Telegram 通知"""
    try:
        logger.info(f"发送 Telegram: user_id={user_id}, chat_id={chat_id}")

        db = next(get_db())
        service = NotificationService(db)
        bot_config = service.get_channel_config('telegram')

        if not bot_config or not bot_config.get('bot_token'):
            raise ValueError("Telegram Bot 配置不存在或未启用")

        telegram_sender = TelegramSender(bot_config)
        success = telegram_sender.send(
            chat_id=chat_id,
            message=message,
            parse_mode='Markdown'
        )

        if success:
            service.update_notification_log(notification_log_id, 'sent')
            logger.info(f"Telegram 发送成功: log_id={notification_log_id}")
        else:
            raise Exception("Telegram 发送失败")

    except Exception as exc:
        logger.error(f"Telegram 发送失败: {exc}")
        service.update_notification_log(
            notification_log_id,
            'failed',
            failed_reason=str(exc),
            retry_count=self.request.retries
        )

        if self.request.retries < self.max_retries:
            countdown = 30 * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)


@shared_task
def send_in_app_notification_task(
    user_id: int,
    title: str,
    content: str,
    notification_type: str,
    business_date: str = None,
    reference_id: str = None,
    metadata: Dict = None,
    priority: str = 'normal'
):
    """发送站内消息（直接写库，无需重试）"""
    try:
        db = next(get_db())
        service = NotificationService(db)

        service.create_in_app_notification(
            user_id=user_id,
            title=title,
            content=content,
            notification_type=notification_type,
            business_date=business_date,
            reference_id=reference_id,
            metadata=metadata,
            priority=priority
        )

        logger.info(f"站内消息创建成功: user_id={user_id}, type={notification_type}")

    except Exception as e:
        logger.error(f"站内消息创建失败: {e}", exc_info=True)


@shared_task
def schedule_report_notification_task(
    report_type: str,
    trade_date: str,
    report_data: Dict[str, Any]
):
    """
    调度报告通知（批量生成发送任务）

    Args:
        report_type: 'sentiment_report', 'premarket_report', 'backtest_result'
        trade_date: 交易日期
        report_data: 报告原始数据
    """
    try:
        logger.info(f"开始调度 {report_type} 通知: date={trade_date}")

        db = next(get_db())
        service = NotificationService(db)

        # 获取订阅用户列表
        subscribers = service.get_subscribers(report_type)
        logger.info(f"找到 {len(subscribers)} 个订阅用户")

        for user in subscribers:
            # 渲染报告内容
            rendered = service.render_report(
                report_type=report_type,
                report_data=report_data,
                user_preferences=user
            )

            # 创建通知日志
            log_ids = service.create_notification_logs(
                user_id=user['user_id'],
                notification_type=report_type,
                title=rendered['title'],
                content=rendered['content'],
                business_date=trade_date,
                channels=user['enabled_channels']
            )

            # 异步发送
            if 'email' in user['enabled_channels']:
                send_email_notification_task.delay(
                    user_id=user['user_id'],
                    email_address=user['email_address'],
                    subject=rendered['title'],
                    html_content=rendered['email_html'],
                    notification_log_id=log_ids['email']
                )

            if 'telegram' in user['enabled_channels']:
                send_telegram_notification_task.delay(
                    user_id=user['user_id'],
                    chat_id=user['telegram_chat_id'],
                    message=rendered['telegram_markdown'],
                    notification_log_id=log_ids['telegram']
                )

            if 'in_app' in user['enabled_channels']:
                send_in_app_notification_task.delay(
                    user_id=user['user_id'],
                    title=rendered['title'],
                    content=rendered['content'],
                    notification_type=report_type,
                    business_date=trade_date
                )

        logger.info(f"{report_type} 通知调度完成")

    except Exception as e:
        logger.error(f"调度通知失败: {e}", exc_info=True)
```

### 4.5 Email 发送器

**文件**: `backend/app/services/email_sender.py`

```python
import smtplib
from email.message import EmailMessage
from typing import Dict
from loguru import logger


class EmailSender:
    """邮件发送器"""

    def __init__(self, config: Dict):
        """
        初始化邮件发送器

        Args:
            config: SMTP 配置字典
            {
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_username": "user@example.com",
                "smtp_password": "password",
                "smtp_use_tls": true,
                "from_email": "noreply@example.com",
                "from_name": "股票分析系统"
            }
        """
        self.config = config

    def send(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        发送邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML 格式邮件内容

        Returns:
            发送成功返回 True，失败返回 False
        """
        try:
            message = EmailMessage()
            message['From'] = f"{self.config.get('from_name', '系统')} <{self.config['from_email']}>"
            message['To'] = to_email
            message['Subject'] = subject
            message.set_content(html_content, subtype='html')

            # 同步发送（Celery Worker 中可以用同步方式）
            if self.config.get('smtp_use_tls', True):
                with smtplib.SMTP(self.config['smtp_host'], self.config['smtp_port']) as server:
                    server.starttls()
                    server.login(self.config['smtp_username'], self.config['smtp_password'])
                    server.send_message(message)
            else:
                with smtplib.SMTP_SSL(self.config['smtp_host'], self.config['smtp_port']) as server:
                    server.login(self.config['smtp_username'], self.config['smtp_password'])
                    server.send_message(message)

            logger.info(f"邮件发送成功: {to_email}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {e}", exc_info=True)
            return False
```

### 4.6 Telegram 发送器

**文件**: `backend/app/services/telegram_sender.py`

```python
import requests
from typing import Dict
from loguru import logger


class TelegramSender:
    """Telegram Bot 发送器"""

    def __init__(self, config: Dict):
        """
        初始化 Telegram 发送器

        Args:
            config: Bot 配置字典
            {
                "bot_token": "1234567890:ABCDEF...",
                "parse_mode": "Markdown",
                "timeout": 30
            }
        """
        self.config = config
        self.bot_token = config['bot_token']
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def send(self, chat_id: str, message: str, parse_mode: str = 'Markdown') -> bool:
        """
        发送 Telegram 消息

        Args:
            chat_id: 用户的 Chat ID
            message: 消息内容（支持 Markdown 或 HTML）
            parse_mode: 解析模式（'Markdown' 或 'HTML'）

        Returns:
            发送成功返回 True，失败返回 False
        """
        try:
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }

            timeout = self.config.get('timeout', 30)
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=timeout
            )

            if response.status_code == 200:
                logger.info(f"Telegram 发送成功: chat_id={chat_id}")
                return True
            else:
                logger.error(f"Telegram 发送失败: {response.status_code}, {response.text}")
                return False

        except Exception as e:
            logger.error(f"Telegram 发送异常: {e}", exc_info=True)
            return False
```

### 4.7 在现有报告服务中添加钩子

**修改文件**: `backend/app/services/sentiment_ai_analysis_service.py`

在 `_save_ai_analysis` 方法的最后添加：

```python
# 第 696 行之后
logger.success(f"{trade_date} AI分析结果已保存到数据库")

# 🆕 触发通知调度（异步）
from app.tasks.notification_tasks import schedule_report_notification_task

schedule_report_notification_task.delay(
    report_type='sentiment_report',
    trade_date=trade_date,
    report_data={
        'trade_date': trade_date,
        'full_report': full_report,
        'space_analysis': space_analysis,
        'sentiment_analysis': sentiment_analysis,
        'capital_flow_analysis': capital_flow_analysis,
        'tomorrow_tactics': tomorrow_tactics
    }
)
logger.info(f"已触发 {trade_date} 情绪报告通知调度")
```

**同样修改**: `backend/app/services/premarket_analysis_service.py` (第 679 行之后)

---

## 5. Admin管理后台实现

### 5.1 文件结构

```
admin/
├── app/(dashboard)/settings/notification-channels/
│   └── page.tsx                        # 通知渠道配置页面
├── components/settings/
│   ├── EmailConfigForm.tsx             # Email 配置表单
│   └── TelegramConfigForm.tsx          # Telegram 配置表单
├── lib/
│   └── api-client.ts                   # 添加通知渠道 API 方法
└── types/
    └── notification-channel.ts         # 类型定义
```

### 5.2 类型定义

**文件**: `admin/types/notification-channel.ts`

```typescript
export interface NotificationChannelConfig {
  id: number
  channel_type: 'email' | 'telegram'
  channel_name: string
  is_enabled: boolean
  is_default: boolean
  priority: number
  config: EmailConfig | TelegramConfig
  description?: string
  last_test_at?: string
  last_test_status?: 'success' | 'failed'
  last_test_message?: string
  created_at: string
  updated_at: string
}

export interface EmailConfig {
  smtp_host: string
  smtp_port: number
  smtp_username: string
  smtp_password: string  // 前端脱敏显示
  smtp_use_tls: boolean
  from_email: string
  from_name: string
}

export interface TelegramConfig {
  bot_token: string      // 前端脱敏显示
  parse_mode: 'Markdown' | 'HTML'
  timeout: number
}

export interface NotificationChannelUpdateRequest {
  is_enabled?: boolean
  config?: Partial<EmailConfig | TelegramConfig>
  description?: string
}

export interface TestChannelResponse {
  success: boolean
  message: string
  test_time: string
}
```

### 5.3 API 客户端方法

**文件**: `admin/lib/api-client.ts`

在现有 `ApiClient` 类中添加：

```typescript
class ApiClient {
  // ... 现有方法 ...

  /**
   * 获取所有通知渠道配置
   */
  async getNotificationChannels(): Promise<ApiResponse<NotificationChannelConfig[]>> {
    const response = await axiosInstance.get('/api/notification-channels')
    return response.data
  }

  /**
   * 获取指定渠道配置
   */
  async getNotificationChannel(channelType: string): Promise<ApiResponse<NotificationChannelConfig>> {
    const response = await axiosInstance.get(`/api/notification-channels/${channelType}`)
    return response.data
  }

  /**
   * 更新通知渠道配置
   */
  async updateNotificationChannel(
    channelType: string,
    data: NotificationChannelUpdateRequest
  ): Promise<ApiResponse<NotificationChannelConfig>> {
    const response = await axiosInstance.put(`/api/notification-channels/${channelType}`, data)
    return response.data
  }

  /**
   * 启用/禁用通知渠道
   */
  async toggleNotificationChannel(
    channelType: string
  ): Promise<ApiResponse<NotificationChannelConfig>> {
    const response = await axiosInstance.post(`/api/notification-channels/${channelType}/toggle`)
    return response.data
  }

  /**
   * 测试通知渠道
   */
  async testNotificationChannel(
    channelType: string,
    testTarget: string  // 邮箱地址或 Telegram Chat ID
  ): Promise<ApiResponse<TestChannelResponse>> {
    const response = await axiosInstance.post(`/api/notification-channels/${channelType}/test`, {
      test_target: testTarget
    })
    return response.data
  }
}
```

### 5.4 更新侧边栏菜单

**文件**: `admin/components/layouts/AdminLayout.tsx`

在 `navItems` 数组的"系统设置"部分添加新菜单项：

```typescript
{
  name: '系统设置',
  icon: Settings,
  children: [
    { name: '数据源设置', href: '/settings/datasource', icon: Database },
    { name: 'AI 配置', href: '/settings/ai-config', icon: Sparkles },
    { name: '提示词管理', href: '/settings/prompt-templates', icon: FileText },
    { name: '定时任务', href: '/settings/scheduler', icon: Clock },
    { name: '通知渠道', href: '/settings/notification-channels', icon: Bell }  // 🆕 新增
  ]
}
```

### 5.5 通知渠道配置页面（核心代码）

**文件**: `admin/app/(dashboard)/settings/notification-channels/page.tsx`

页面主要功能：
- 卡片列表展示所有通知渠道（Email、Telegram）
- Switch 切换启用/禁用
- Dialog 对话框编辑配置
- 测试连接功能
- 显示最后测试状态

详细代码请参考完整实施方案中的前端章节。

---

## 6. 用户前端实现

### 6.1 文件结构

```
frontend/src/
├── app/settings/notifications/
│   └── page.tsx                        # 用户通知配置页面
├── components/notifications/
│   ├── NotificationCenter.tsx          # 通知中心（站内消息列表）
│   └── NotificationBadge.tsx           # 未读消息角标
├── lib/
│   └── api-client.ts                   # 添加通知 API 方法
└── types/
    └── notification.ts                 # 类型定义
```

### 6.2 用户通知配置页面（核心功能）

**文件**: `frontend/src/app/settings/notifications/page.tsx`

主要功能：
- 通知渠道管理（Email、Telegram、站内消息）
- 订阅内容选择（盘后情绪报告、盘前碰撞报告、回测通知）
- 报告格式选择（完整报告/摘要/仅行动指令）
- 联系方式配置（邮箱地址、Telegram Chat ID）

---

## 7. 部署与测试

### 7.1 数据库迁移

```bash
# 创建数据库初始化脚本
cat > db_init/notification_tables.sql << 'EOF'
-- 通知渠道配置表
CREATE TABLE notification_channel_configs (
    -- 详见第 3 章数据库设计
);

-- 用户通知配置表
CREATE TABLE user_notification_settings (
    -- 详见第 3 章数据库设计
);

-- 通知发送记录表
CREATE TABLE notification_logs (
    -- 详见第 3 章数据库设计
);

-- 站内消息表
CREATE TABLE in_app_notifications (
    -- 详见第 3 章数据库设计
);
EOF

# 执行迁移
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -f /docker-entrypoint-initdb.d/notification_tables.sql
```

### 7.2 安装 Python 依赖

```bash
cd backend
pip install aiosmtplib==3.0.0 email-validator==2.1.0 python-telegram-bot==20.7

# 更新 requirements.txt
echo "aiosmtplib==3.0.0" >> requirements.txt
echo "email-validator==2.1.0" >> requirements.txt
echo "python-telegram-bot==20.7" >> requirements.txt
```

### 7.3 环境变量配置（可选）

在 `.env` 文件中添加默认配置（实际优先使用数据库配置）：

```bash
# 默认 SMTP 配置（可选，优先使用数据库配置）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@example.com
SMTP_FROM_NAME=股票分析系统

# 默认 Telegram Bot 配置（可选）
TELEGRAM_BOT_TOKEN=
```

### 7.4 重启服务

```bash
docker-compose restart backend celery_worker celery_beat
```

### 7.5 测试流程

#### 7.5.1 管理后台配置测试

1. 登录 Admin 后台 `http://localhost:3002`
2. 进入"系统设置" → "通知渠道"
3. 配置 Email SMTP 参数
4. 点击"测试连接"，输入测试邮箱
5. 检查是否收到测试邮件

#### 7.5.2 用户订阅测试

1. 登录用户前端 `http://localhost:3000`
2. 进入"设置" → "通知设置"
3. 启用邮件通知，填写邮箱
4. 订阅"盘后情绪分析报告"
5. 等待定时任务触发或手动触发报告生成

#### 7.5.3 手动触发报告推送（测试用）

```bash
# 进入 backend 容器
docker-compose exec backend bash

# 进入 Python 环境
python

# 手动触发通知调度
from app.tasks.notification_tasks import schedule_report_notification_task

schedule_report_notification_task.delay(
    report_type='sentiment_report',
    trade_date='2026-03-15',
    report_data={
        'trade_date': '2026-03-15',
        'full_report': '测试报告内容...',
        # ... 其他字段
    }
)
```

---

## 8. 实施计划

### Phase 1: 核心功能（1-2 周）

**Week 1:**
- [ ] 数据库表创建和迁移
- [ ] 后端 API 端点实现（通知渠道配置 + 用户订阅配置）
- [ ] Celery 通知任务实现
- [ ] Email 发送器实现
- [ ] 站内消息功能实现

**Week 2:**
- [ ] Admin 后台通知渠道配置页面
- [ ] 用户前端订阅配置页面
- [ ] 在现有报告服务中添加通知钩子
- [ ] 集成测试

### Phase 2: 增强功能（1 周）

- [ ] Telegram Bot 集成
- [ ] 报告内容模板系统（Jinja2）
- [ ] 定时批量发送优化
- [ ] 通知频率限制

### Phase 3: 优化与监控（1 周）

- [ ] 发送成功率监控
- [ ] 失败告警机制
- [ ] 用户偏好 AI 推荐
- [ ] 性能优化（批量发送、连接池）

---

## 9. 附录

### 9.1 配置示例

#### SMTP 配置（Gmail）
```json
{
  "smtp_host": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_username": "your_email@gmail.com",
  "smtp_password": "your_app_password",
  "smtp_use_tls": true,
  "from_email": "noreply@yourdomain.com",
  "from_name": "股票分析系统"
}
```

**注意**: Gmail 需要生成应用专用密码（2FA 启用后）

#### Telegram Bot 配置
```json
{
  "bot_token": "1234567890:ABCDEF1234567890ABCDEF1234567890ABC",
  "parse_mode": "Markdown",
  "timeout": 30
}
```

### 9.2 技术栈总结

#### 后端
- FastAPI 0.104.0
- Celery 5.3.4 + Redis 7
- SQLAlchemy 2.0.0 + TimescaleDB
- aiosmtplib 3.0.0 (Email)
- python-telegram-bot 20.7 (Telegram)

#### Admin 后台
- Next.js 14 (App Router)
- TypeScript 5.3.0
- shadcn/ui + Radix UI
- Tailwind CSS 3.4.0
- Zustand 4.5.0

#### 用户前端
- Next.js 14
- React Query
- 相同 UI 技术栈

---

## 10. 总结

### 方案优势

1. ✅ **利用现有基础设施**: 完全基于 Celery + Redis，无需引入额外消息队列
2. ✅ **可视化配置管理**: Admin 后台统一管理通知渠道，无需手动修改配置文件
3. ✅ **用户个性化**: 支持订阅偏好、内容格式、发送时间自定义
4. ✅ **异步非阻塞**: 所有��送任务异步执行，不影响主业务流程
5. ✅ **可靠重试机制**: Email/Telegram 失败自动重试 3 次
6. ✅ **完整日志追踪**: 每条通知都有发送记录和状态
7. ✅ **敏感信息保护**: 密码、Token 加密存储，前端脱敏显示
8. ✅ **易于扩展**: 可方便添加新渠道（企业微信、钉钉、飞书等）

### 技术亮点

- **双层配置**: 系统级（Admin 配置渠道）+ 用户级（订阅偏好）分离
- **测试连接**: 管理员可在保存前测试 SMTP/Bot 连接
- **内容渲染**: 支持多格式（完整报告/摘要/仅行动指令）
- **分区表**: 使用 TimescaleDB Hypertable 自动分区，性能优化
- **保留策略**: 自动清理历史日志，节省存储空间

---

**文档版本**: v1.0
**最后更新**: 2026-03-15
**作者**: AI Assistant
