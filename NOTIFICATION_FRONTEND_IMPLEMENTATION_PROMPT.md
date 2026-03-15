# 通知系统用户前端实施 Prompt

## 📋 任务概述

你需要为股票分析系统实现**用户前端的通知配置功能**，允许用户管理自己的通知订阅偏好、查看站内消息、配置通知渠道。

**重要**: Admin 后台的通知渠道配置已经完成（commit: 78054dc），本次任务专注于用户前端部分。

---

## 🎯 实施目标

实现 `/docs/NOTIFICATION_SYSTEM_DESIGN.md` 文档第 6 章的用户前端功能：

### 1. 用户通知设置页面
- 路径: `/frontend/src/app/settings/notifications/page.tsx`
- 功能: 用户订阅偏好配置、渠道管理、联系方式设置

### 2. 站内消息中心
- 组件: `/frontend/src/components/notifications/NotificationCenter.tsx`
- 功能: 消息列表、未读标记、全部已读

### 3. 未读消息角标
- 组件: `/frontend/src/components/notifications/NotificationBadge.tsx`
- 功能: 显示未读数量，实时更新

---

## 📂 项目背景

### 后端 API 已完成

所有后端 API 端点已实现，位于 `/backend/app/api/endpoints/notifications.py`:

```python
# 用户通知配置
GET  /api/notifications/settings           # 获取用户通知配置
PUT  /api/notifications/settings           # 更新用户通知配置

# 站内消息
GET  /api/notifications/in-app             # 获取站内消息列表（支持分页、筛选未读）
POST /api/notifications/in-app/{id}/read   # 标记消息为已读
POST /api/notifications/in-app/read-all    # 全部标记为已读

# 统计和日志
GET  /api/notifications/unread-count       # 获取未读消息数量
GET  /api/notifications/logs               # 获取通知发送历史
```

### 数据库模型

参考后端模型定义 `/backend/app/models/notification_setting.py`:

**用户通知配置 (`user_notification_settings`)**:
- `email_enabled`, `telegram_enabled`, `in_app_enabled` - 渠道启用状态
- `email_address`, `telegram_chat_id` - 联系方式
- `subscribe_sentiment_report`, `subscribe_premarket_report`, `subscribe_backtest_report` - 订阅内容
- `report_format` - 报告格式（'full', 'summary', 'action_only'）
- `sentiment_report_time`, `premarket_report_time` - 发送时间偏好
- `max_daily_notifications` - 每日最大通知数

**站内消息 (`in_app_notifications`)**:
- `title`, `content`, `notification_type` - 消息内容
- `is_read`, `read_at` - 已读状态
- `priority` - 优先级（'high', 'normal', 'low'）
- `business_date`, `reference_id` - 关联数据

---

## 🎨 UI/UX 设计要求

### 通知设置页面布局

```
┌─────────────────────────────────────────────────────────┐
│  通知设置                                                │
├─────────────────────────────────────────────────────────┤
│  📧 通知渠道                                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ☑ Email 通知          [email@example.com     ]   │  │
│  │ ☐ Telegram 通知       [Chat ID: _________    ]   │  │
│  │ ☑ 站内消息            默认启用                    │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  📬 订阅内容                                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ☑ 盘后情绪分析报告    发送时间: [18:30]          │  │
│  │ ☑ 盘前碰撞分析报告    发送时间: [08:00]          │  │
│  │ ☑ 回测完成通知                                    │  │
│  │ ☑ 策略审核通知                                    │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ⚙️ 偏好设置                                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 报告格式: ◉ 完整报告 ○ 摘要 ○ 仅行动指令         │  │
│  │ 每日最大通知数: [10]                              │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│                            [保存设置] [恢复默认]        │
└─────────────────────────────────────────────────────────┘
```

### 站内消息中心布局

```
┌─────────────────────────────────────────────────────────┐
│  通知中心                    [全部已读] [仅显示未读 ☐]  │
├─────────────────────────────────────────────────────────┤
│  🔴 [高] 盘后情绪分析报告 - 2026-03-15                  │
│       今日市场情绪回暖，涨停板池扩容...                 │
│       2026-03-15 18:30 · 查看详情                       │
│  ─────────────────────────────────────────────────────  │
│  ● [普通] 回测完成通知                                  │
│       您的策略回测已完成，收益率 15.6%...               │
│       2026-03-15 14:20 · 查看详情                       │
│  ─────────────────────────────────────────────────────  │
│  ○ [低] 系统维护通知 ✓已读                             │
│       系统将于今晚 22:00 进行维护...                    │
│       2026-03-14 10:00                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 实施步骤

### Step 1: 创建 TypeScript 类型定义

**文件**: `/frontend/src/types/notification.ts`

```typescript
/**
 * 用户通知配置接口
 */
export interface NotificationSettings {
  // 渠道启用状态
  email_enabled: boolean
  telegram_enabled: boolean
  in_app_enabled: boolean

  // 联系方式
  email_address?: string
  telegram_chat_id?: string
  telegram_username?: string

  // 订阅偏好
  subscribe_sentiment_report: boolean
  subscribe_premarket_report: boolean
  subscribe_backtest_report: boolean
  subscribe_strategy_alert: boolean

  // 发送时间
  sentiment_report_time: string  // "18:30"
  premarket_report_time: string  // "08:00"

  // 报告格式
  report_format: 'full' | 'summary' | 'action_only'

  // 频率控制
  max_daily_notifications: number

  created_at: string
  updated_at: string
}

/**
 * 站内消息接口
 */
export interface InAppNotification {
  id: number
  title: string
  content: string
  notification_type: string
  is_read: boolean
  read_at?: string
  priority: 'high' | 'normal' | 'low'
  business_date?: string
  reference_id?: string
  metadata?: Record<string, any>
  created_at: string
}

/**
 * 未读数量响应
 */
export interface UnreadCountResponse {
  unread_count: number
}

/**
 * 通知日志
 */
export interface NotificationLog {
  id: number
  notification_type: string
  channel: 'email' | 'telegram' | 'in_app'
  status: 'pending' | 'sent' | 'failed' | 'skipped'
  title: string
  sent_at?: string
  failed_reason?: string
  created_at: string
}
```

### Step 2: 扩展 API 客户端

**文件**: `/frontend/src/lib/api-client.ts`

在现有 `ApiClient` 类中添加方法：

```typescript
// ========== 用户通知 API ==========

/**
 * 获取用户通知配置
 */
async getNotificationSettings(): Promise<ApiResponse<NotificationSettings>> {
  const response = await axiosInstance.get('/api/notifications/settings')
  return response.data
}

/**
 * 更新用户通知配置
 */
async updateNotificationSettings(
  settings: Partial<NotificationSettings>
): Promise<ApiResponse<NotificationSettings>> {
  const response = await axiosInstance.put('/api/notifications/settings', settings)
  return response.data
}

/**
 * 获取站内消息列表
 */
async getInAppNotifications(params?: {
  unread_only?: boolean
  limit?: number
  offset?: number
}): Promise<ApiResponse<InAppNotification[]>> {
  const response = await axiosInstance.get('/api/notifications/in-app', { params })
  return response.data
}

/**
 * 标记消息为已读
 */
async markNotificationAsRead(id: number): Promise<ApiResponse<void>> {
  const response = await axiosInstance.post(`/api/notifications/in-app/${id}/read`)
  return response.data
}

/**
 * 全部标记为已读
 */
async markAllNotificationsAsRead(): Promise<ApiResponse<{ count: number }>> {
  const response = await axiosInstance.post('/api/notifications/in-app/read-all')
  return response.data
}

/**
 * 获取未读消息数量
 */
async getUnreadCount(): Promise<ApiResponse<UnreadCountResponse>> {
  const response = await axiosInstance.get('/api/notifications/unread-count')
  return response.data
}

/**
 * 获取通知发送历史
 */
async getNotificationLogs(params?: {
  limit?: number
  offset?: number
}): Promise<ApiResponse<NotificationLog[]>> {
  const response = await axiosInstance.get('/api/notifications/logs', { params })
  return response.data
}
```

### Step 3: 创建通知设置页面

**文件**: `/frontend/src/app/settings/notifications/page.tsx`

主要功能：
- 加载和显示用户当前配置
- 渠道启用/禁用 Switch
- 联系方式输入框（Email 地址、Telegram Chat ID）
- 订阅内容复选框
- 报告格式单选按钮
- 发送时间选择器
- 保存配置按钮
- 表单验证（Email 格式、必填项）

**UI 组件使用**:
- `Card` - 分组卡片
- `Switch` - 开关
- `Input` - 文本输入
- `Checkbox` - 复选框
- `RadioGroup` - 单选按钮组
- `Button` - 按钮
- `Label` - 标签
- `toast` - 成功/错误提示

**关键逻辑**:
```typescript
const [settings, setSettings] = useState<NotificationSettings | null>(null)
const [isSaving, setIsSaving] = useState(false)

// 加载配置
useEffect(() => {
  const loadSettings = async () => {
    const response = await apiClient.getNotificationSettings()
    if (response.success && response.data) {
      setSettings(response.data)
    }
  }
  loadSettings()
}, [])

// 保存配置
const handleSave = async () => {
  setIsSaving(true)
  try {
    const response = await apiClient.updateNotificationSettings(settings)
    if (response.success) {
      toast.success('通知设置已保存')
    }
  } catch (error) {
    toast.error('保存失败，请重试')
  } finally {
    setIsSaving(false)
  }
}
```

### Step 4: 创建站内消息中心组件

**文件**: `/frontend/src/components/notifications/NotificationCenter.tsx`

主要功能：
- 消息列表展示（分页）
- 未读/已读状态区分
- 优先级标识（颜色区分）
- 单条消息标记已读
- 全部标记已读按钮
- 筛选未读消息
- 点击查看详情（展开内容）

**UI 样式**:
- 未读消息：粗体标题 + 蓝色圆点
- 高优先级：红色图标
- 普通优先级：蓝色图标
- 低优先级：灰色图标
- 已读消息：灰色文字

### Step 5: 创建未读消息角标组件

**文件**: `/frontend/src/components/notifications/NotificationBadge.tsx`

主要功能：
- 实时显示未读数量
- 超过 99 显示 "99+"
- 无未读时隐藏
- 可选：轮询更新（每 30 秒）

**使用示例**:
```tsx
<NotificationBadge
  count={unreadCount}
  className="absolute -top-1 -right-1"
/>
```

### Step 6: 集成到导航栏

修改主导航组件（Header 或 Navbar），添加通知中心入口：

```tsx
<DropdownMenu>
  <DropdownMenuTrigger>
    <Bell className="h-5 w-5" />
    <NotificationBadge count={unreadCount} />
  </DropdownMenuTrigger>
  <DropdownMenuContent>
    <NotificationCenter limit={5} />
    <DropdownMenuItem asChild>
      <Link href="/notifications">查看全部</Link>
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

---

## 🎯 关键功能要求

### 1. 表单验证

- Email 地址格式验证
- Telegram Chat ID 格式验证（纯数字或负数）
- 必填项检查（启用渠道时必填联系方式）
- 时间格式验证（HH:MM）

### 2. 用户体验

- 加载状态指示（Skeleton 或 Spinner）
- 保存成功/失败提示（Toast）
- 按钮禁用状态（保存中、表单无效）
- 友好的错误消息
- 配置说明提示（Tooltip）

### 3. 实时更新

- 未读数量实时刷新（可选轮询或 WebSocket）
- 标记已读后立即更新 UI
- 保存配置后更新本地状态

### 4. 响应式设计

- 移动端适配（单列布局）
- 触摸友好的交互
- 合理的字体大小和间距

---

## 📚 参考资料

### 设计文档
- **主要参考**: `/docs/NOTIFICATION_SYSTEM_DESIGN.md` 第 6 章
- **API 文档**: 后端 `/backend/app/api/endpoints/notifications.py`
- **数据模型**: 后端 `/backend/app/models/notification_setting.py`

### 已完成的 Admin 后台
- **类型定义参考**: `/admin/types/notification-channel.ts`
- **API 集成参考**: `/admin/lib/api-client.ts`
- **页面结构参考**: `/admin/app/(dashboard)/settings/notification-channels/page.tsx`

### UI 组件库
- 项目使用 **shadcn/ui** + **Tailwind CSS**
- 组件路径: `/frontend/src/components/ui/`
- 常用组件: Card, Switch, Input, Button, Checkbox, RadioGroup, Label

---

## ⚠️ 注意事项

### 1. 与 Admin 后台的区别

| 项目 | Admin 后台 | 用户前端 |
|------|-----------|---------|
| 配置对象 | 系统级渠道参数（SMTP、Bot Token） | 用户级订阅偏好 |
| 权限 | 仅超级管理员 | 所有认证用户 |
| API 端点 | `/api/notification-channels` | `/api/notifications` |
| 配置内容 | SMTP 密码、Bot Token | 邮箱地址、Chat ID |

### 2. 安全考虑

- **不要**在前端存储敏感信息（SMTP 密码、Bot Token）
- 用户只能配置自己的邮箱和 Chat ID
- 表单提交前验证数据格式
- API 调用失败时不要泄露敏感错误信息

### 3. Telegram Chat ID 获取指南

在页面中提供帮助文档：

```
如何获取 Telegram Chat ID：
1. 向管理员配置的 Bot 发送任意消息
2. 访问 https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
3. 在返回的 JSON 中找到 "chat": { "id": 123456789 }
4. 将 Chat ID 填入下方输入框
```

### 4. 测试检查清单

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

---

## 🚀 实施优先级

### 第一优先级（核心功能）
1. ✅ TypeScript 类型定义
2. ✅ API 客户端方法
3. ✅ 通知设置页面（基础版）
4. ✅ 站内消息列表展示

### 第二优先级（完善体验）
5. ✅ 未读消息角标
6. ✅ 全部标记已读
7. ✅ 表单验证和错误提示
8. ✅ 加载和保存状态

### 第三优先级（优化增强）
9. ⭐ 消息详情展开/收起
10. ⭐ 通知发送历史查看
11. ⭐ 配置预览功能
12. ⭐ 实时未读数轮询

---

## 💡 实施建议

### 开发顺序
1. 先创建类型定义，确保类型安全
2. 再扩展 API 客户端，测试 API 调用
3. 实现通知设置页面，验证配置保存
4. 最后实现站内消息和角标，完善交互

### 代码风格
- 遵循项目现有的代码风格
- 使用 TypeScript 严格模式
- 组件拆分合理，职责单一
- 添加必要的注释和文档

### 测试策略
- 先在开发环境测试 API 调用
- 使用浏览器控制台查看网络请求
- 测试各种边界情况（空数据、错误响应）
- 验证响应式布局

---

## 📝 提交规范

完成后创建 Git Commit，格式参考：

```
feat(notification): 实现用户前端通知配置功能

## 新增功能

### 通知设置页面
- 渠道启用/禁用配置
- 订阅内容选择
- 报告格式和时间偏好
- 联系方式管理

### 站内消息中心
- 消息列表展示
- 未读/已读状态
- 优先级标识
- 标记已读功能

### 未读消息角标
- 实时未读数量显示
- 导航栏集成

## 技术实现

### 新增文件
- frontend/src/types/notification.ts
- frontend/src/app/settings/notifications/page.tsx
- frontend/src/components/notifications/NotificationCenter.tsx
- frontend/src/components/notifications/NotificationBadge.tsx

### API 集成
- 新增 7 个 API 客户端方法

## 相关文档
- 设计文档: docs/NOTIFICATION_SYSTEM_DESIGN.md 第6章
- 对应后端 API: backend/app/api/endpoints/notifications.py

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 🎉 预期成果

完成后，用户可以：
- ✅ 配置自己的通知订阅偏好
- ✅ 管理 Email 和 Telegram 联系方式
- ✅ 选择订阅的报告类型
- ✅ 自定义报告格式和发送时间
- ✅ 查看站内消息
- ✅ 标记消息已读/未读
- ✅ 查看未读消息数量
- ✅ 查看通知发送历史

整个通知系统的用户端功能将**完整闭环**！

---

**准备好开始了吗？** 按照上述步骤逐步实施，有任何问题随时询问！
