# 通知系统前端功能说明

## 📋 功能概述

本次实现了完整的用户前端通知配置功能,包括通知设置、站内消息中心和未读角标。

## 🎯 实现的功能

### 1. 通知设置页面 (`/settings/notifications`)

**路径**: [/settings/notifications/page.tsx](src/app/settings/notifications/page.tsx)

**功能特性**:
- ✅ 渠道启用/禁用配置
  - Email 通知开关 + 邮箱地址输入
  - Telegram 通知开关 + Chat ID 输入
  - 站内消息(默认启用)
- ✅ 订阅内容选择
  - 盘后情绪分析报告(可配置发送时间)
  - 盘前碰撞分析报告(可配置发送时间)
  - 回测完成通知
  - 策略审核通知
- ✅ 报告格式偏好
  - 完整报告
  - 摘要
  - 仅行动指令
- ✅ 频率控制
  - 每日最大通知数设置
- ✅ 表单验证
  - Email 格式验证
  - Telegram Chat ID 格式验证
  - 必填项检查
- ✅ 用户体验优化
  - 加载状态指示
  - 保存成功/失败提示
  - 恢复默认设置按钮
  - Telegram Chat ID 获取帮助文档

### 2. 站内消息中心

**组件**: [NotificationCenter.tsx](src/components/notifications/NotificationCenter.tsx)

**完整页面**: [/notifications/page.tsx](src/app/notifications/page.tsx)

**功能特性**:
- ✅ 消息列表展示
  - 支持分页(默认50条)
  - 未读/已读状态区分
  - 优先级标识(高/普通/低)
- ✅ 消息操作
  - 单条消息标记已读(点击自动标记)
  - 全部标记为已读
  - 消息展开/收起
- ✅ 筛选功能
  - 仅显示未读消息
- ✅ 消息详情
  - 标题、内容、时间
  - 业务日期、元数据
  - 相对时间显示(刚刚/X分钟前/X小时前)
- ✅ 响应式设计
  - 移动端友好布局
  - 触摸交互优化

### 3. 未读消息角标

**组件**: [NotificationBadge.tsx](src/components/notifications/NotificationBadge.tsx)

**功能特性**:
- ✅ 实时未读数量显示
- ✅ 超过 99 显示 "99+"
- ✅ 无未读时自动隐藏
- ✅ 自动轮询更新(默认30秒)
- ✅ 可配置轮询间隔
- ✅ 支持外部控制未读数量

### 4. 导航栏集成

**桌面导航**: [desktop-nav.tsx](src/components/desktop-nav.tsx)
**移动导航**: [mobile-nav.tsx](src/components/mobile-nav.tsx)

**功能特性**:
- ✅ 桌面端:铃铛图标 + 下拉菜单
  - 显示未读角标
  - 快捷跳转到通知中心
  - 快捷跳转到通知设置
- ✅ 移动端:侧边菜单
  - 通知中心入口 + 未读角标
  - 通知设置入口

## 📂 文件结构

```
frontend/src/
├── types/
│   └── notification.ts              # 类型定义
├── lib/
│   └── api-client.ts                # API 客户端(扩展了7个方法)
├── components/
│   └── notifications/
│       ├── NotificationCenter.tsx   # 站内消息中心组件
│       ├── NotificationBadge.tsx    # 未读消息角标组件
│       └── index.ts                 # 统一导出
├── app/
│   ├── notifications/
│   │   └── page.tsx                 # 通知中心完整页面
│   └── settings/
│       └── notifications/
│           └── page.tsx             # 通知设置页面
└── components/
    ├── desktop-nav.tsx              # 桌面导航(已集成)
    └── mobile-nav.tsx               # 移动导航(已集成)
```

## 🔧 技术实现

### 类型定义

**文件**: [src/types/notification.ts](src/types/notification.ts)

```typescript
// 用户通知配置
interface NotificationSettings {
  email_enabled: boolean
  telegram_enabled: boolean
  in_app_enabled: boolean
  email_address?: string
  telegram_chat_id?: string
  subscribe_sentiment_report: boolean
  subscribe_premarket_report: boolean
  subscribe_backtest_report: boolean
  subscribe_strategy_alert: boolean
  sentiment_report_time: string
  premarket_report_time: string
  report_format: 'full' | 'summary' | 'action_only'
  max_daily_notifications: number
  // ...
}

// 站内消息
interface InAppNotification {
  id: number
  title: string
  content: string
  notification_type: string
  is_read: boolean
  priority: 'high' | 'normal' | 'low'
  // ...
}
```

### API 客户端方法

**文件**: [src/lib/api-client.ts](src/lib/api-client.ts)

新增的 7 个方法:

1. `getNotificationSettings()` - 获取用户通知配置
2. `updateNotificationSettings()` - 更新用户通知配置
3. `getInAppNotifications()` - 获取站内消息列表
4. `markNotificationAsRead()` - 标记消息为已读
5. `markAllNotificationsAsRead()` - 全部标记为已读
6. `getUnreadCount()` - 获取未读消息数量
7. `getNotificationLogs()` - 获取通知发送历史

### UI 组件使用

项目使用 **shadcn/ui** 组件库:

- `Card` - 分组卡片
- `Switch` - 开关按钮
- `Input` - 文本输入框
- `Checkbox` - 复选框
- `RadioGroup` - 单选按钮组
- `Button` - 按钮
- `Label` - 标签
- `Badge` - 角标
- `DropdownMenu` - 下拉菜单
- `ScrollArea` - 滚动区域
- `toast` - 消息提示

## 🧪 测试清单

### 功能测试

- [x] ✅ 构建成功 - `npm run build` 通过
- [ ] 加载用户配置成功
- [ ] 启用/禁用渠道正常
- [ ] Email 格式验证正确
- [ ] Telegram Chat ID 验证正确
- [ ] 保存配置成功
- [ ] 站内消息列表显示正常
- [ ] 标记已读功能正常
- [ ] 未读角标实时更新
- [ ] 响应式布局正常
- [ ] 错误提示友好

### API 对接测试

需要后端 API 正常运行:

```bash
# 后端 API 端点
GET  /api/notifications/settings           # 获取用户通知配置
PUT  /api/notifications/settings           # 更新用户通知配置
GET  /api/notifications/in-app             # 获取站内消息列表
POST /api/notifications/in-app/{id}/read   # 标记消息为已读
POST /api/notifications/in-app/read-all    # 全部标记为已读
GET  /api/notifications/unread-count       # 获取未读消息数量
GET  /api/notifications/logs               # 获取通知发送历史
```

## 🚀 如何使用

### 1. 启动开发服务器

```bash
cd frontend
npm run dev
```

### 2. 访问页面

- 通知设置: http://localhost:3000/settings/notifications
- 通知中心: http://localhost:3000/notifications

### 3. 导航栏入口

登录后在页面顶部:
- **桌面端**: 点击右上角铃铛图标
- **移动端**: 打开汉堡菜单 → 通知中心

## 📝 注意事项

### 1. 安全考虑

- ✅ 前端不存储敏感信息(SMTP密码、Bot Token)
- ✅ 用户只能配置自己的邮箱和 Chat ID
- ✅ 表单提交前验证数据格式
- ✅ API 调用失败时不泄露敏感错误信息

### 2. 与 Admin 后台的区别

| 项目 | Admin 后台 | 用户前端 |
|------|-----------|---------|
| 配置对象 | 系统级渠道参数 | 用户级订阅偏好 |
| 权限 | 仅超级管理员 | 所有认证用户 |
| API 端点 | `/api/notification-channels` | `/api/notifications` |
| 配置内容 | SMTP密码、Bot Token | 邮箱地址、Chat ID |

### 3. Telegram Chat ID 获取

提供给用户的帮助文档(已集成在设置页面):

```
如何获取 Telegram Chat ID:
1. 向系统配置的 Bot 发送任意消息
2. 联系管理员获取您的 Chat ID
3. 将 Chat ID 填入输入框
```

## 🎉 完成状态

所有计划功能已实现:

- ✅ TypeScript 类型定义
- ✅ API 客户端方法扩展
- ✅ 通知设置页面
- ✅ 站内消息中心组件
- ✅ 未读消息角标组件
- ✅ 通知中心完整页面
- ✅ 导航栏集成(桌面端+移动端)
- ✅ 构建测试通过

整个通知系统的用户端功能已**完整闭环**!

## 🔗 相关文档

- 设计文档: [docs/NOTIFICATION_SYSTEM_DESIGN.md](../docs/NOTIFICATION_SYSTEM_DESIGN.md) 第6章
- 后端 API: [backend/app/api/endpoints/notifications.py](../backend/app/api/endpoints/notifications.py)
- Admin 后台参考: [admin/app/(dashboard)/settings/notification-channels/page.tsx](../admin/app/(dashboard)/settings/notification-channels/page.tsx)
