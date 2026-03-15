# Admin 管理后台开发文档

## 📍 项目位置

```
stock-analysis/
├── admin/          # Next.js 14 管理后台
│   ├── app/        # App Router 页面
│   ├── components/ # React 组件
│   ├── lib/        # 工具库（日志、API客户端等）
│   └── stores/     # Zustand 状态管理
├── backend/        # FastAPI 后端
└── core/           # Python 核心库
```

---

## 🚀 启动开发环境

### 方式1: Docker Compose（推荐）

**启动所有服务**（包括admin、backend、数据库）:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

**查看日志**:
```bash
# 查看admin前端日志
docker-compose logs -f admin

# 查看backend日志
docker-compose logs -f backend
```

**重启admin服务**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart admin
```

### 方式2: 本地开发（仅admin）

**前提条件**: Backend服务必须运行（通过Docker或本地）

```bash
cd admin

# 安装依赖（首次）
npm install

# 启动开发服务器
npm run dev

# 访问
# http://localhost:3002
```

---

## 🔧 重构后的新功能

### 1. 统一日志系统

**位置**: [admin/lib/logger.ts](../admin/lib/logger.ts)

**使用方法**:
```typescript
import logger from '@/lib/logger'

// Debug日志（仅开发环境）
logger.debug('调试信息', { userId: 123 })

// Info日志
logger.info('操作成功', { action: 'create' })

// Warn日志（自动上报Sentry）
logger.warn('接口响应慢', { duration: 5000 })

// Error日志（自动上报Sentry）
logger.error('操作失败', error, { context: 'user-action' })

// 性能监控
logger.performance('api-response-time', 1250, 'ms')

// 用户行为追踪
logger.track('button-click', { button: 'submit' })

// 设置用户上下文（登录后）
logger.setUser(userId, email, username)

// 清除用户上下文（登出时）
logger.clearUser()
```

**注意**:
- ⚠️ 不要再使用 `console.log` / `console.error`，已全部替换为 logger
- ✅ 开发环境：日志输出到控制台
- ✅ 生产环境：自动上报到Sentry

---

### 2. Sentry 错误监控

**配置文件**:
- [admin/sentry.client.config.ts](../admin/sentry.client.config.ts) - 客户端
- [admin/sentry.server.config.ts](../admin/sentry.server.config.ts) - 服务端
- [admin/sentry.edge.config.ts](../admin/sentry.edge.config.ts) - Edge Runtime

**启用Sentry**:

1. 访问 [sentry.io](https://sentry.io) 创建项目
2. 复制 `.env.example` 为 `.env.local`:
   ```bash
   cp .env.example .env.local
   ```
3. 编辑 `.env.local`:
   ```env
   NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
   ```
4. 重启服务

**功能特性**:
- ✅ 自动捕获客户端和服务端错误
- ✅ Session Replay（错误会话100%录制）
- ✅ 性能监控（APM）
- ✅ 用户行为追踪（Breadcrumbs）
- ✅ 敏感信息自动过滤（Cookie、Authorization等）
- ✅ 开发环境不上报（仅控制台输出）

---

### 3. 全局 Error Boundary

**位置**: [admin/components/ErrorBoundary.tsx](../admin/components/ErrorBoundary.tsx)

**功能**:
- ✅ 捕获React组件树中的JavaScript错误
- ✅ 显示优雅的错误UI（而非白屏）
- ✅ 自动上报错误到Sentry
- ✅ 提供"重新加载"和"返回首页"按钮
- ✅ 开发环境显示详细错误堆栈

**已集成位置**: [admin/app/layout.tsx](../admin/app/layout.tsx)

---

### 4. 统一 API 响应类型

**位置**: [admin/types/api.ts](../admin/types/api.ts)

**重要**: 所有 API 调用必须使用统一的 `ApiResponse<T>` 类型

**标准响应格式**:
```typescript
interface ApiResponse<T> {
  code: number              // HTTP状态码 (200, 400, 500等)
  message: string           // 响应消息
  data?: T                  // 响应数据（泛型）
  success?: boolean         // 成功标识（后端自动计算）
  timestamp?: string        // 时间戳
  request_id?: string       // 请求追踪ID
  api_version?: string      // API版本
}
```

**使用方法**:
```typescript
import { apiClient } from '@/lib/api-client'
import type { ApiResponse } from '@/types'

// ✅ 正确：使用 apiClient + 统一类型
const response = await apiClient.get<User>('/api/users/123')
if (response.code === 200 && response.data) {
  console.log(response.data)  // 完整的类型检查
}

// ❌ 错误：直接使用 fetch（无认证Token，无自动Token刷新）
const res = await fetch('/api/users/123')

// ❌ 错误：直接使用 axios（无认证Token，无自动Token刷新）
import axios from 'axios'
const res = await axios.get('/api/users/123')

// ❌ 错误：使用 as any 绕过类型检查
const result = response as any
```

**类型守卫函数**:
```typescript
import { isSuccessResponse, isErrorResponse } from '@/types'

const response = await apiClient.get<User>('/api/users/123')

if (isSuccessResponse(response)) {
  // TypeScript 自动推断 response.data 存在
  console.log(response.data.username)
}

if (isErrorResponse(response)) {
  // 处理错误
  console.error(response.message)
}
```

**分页响应**:
```typescript
import type { PaginatedResponse } from '@/types'

const response = await apiClient.get<PaginatedResponse<User>>('/api/users')
if (response.code === 200 && response.data) {
  const { items, total, page, page_size } = response.data
}
```

**注意事项**:
- ⚠️ **禁止使用原生 `fetch` 或独立的 `axios` 实例**（会丢失认证Token和自动Token刷新）
- ⚠️ **禁止使用 `as any` 绕过类型检查**
- ⚠️ **禁止自定义响应类型**（必须使用 `types/api.ts`）
- ✅ **始终通过 `apiClient` 调用 API**
- ✅ **使用类型守卫函数提高类型安全**
- ✅ **所有自定义 API 模块必须使用 `apiClient`**（参考 `prompt-template-api.ts`）

**正确示例**（自定义API模块）:
```typescript
// ✅ 正确：使用 apiClient 的自定义 API 模块
import { apiClient } from './api-client'

export const myCustomApi = {
  list: async () => {
    const response = await apiClient.get('/api/my-resource')
    return response.data
  },
  create: async (data: any) => {
    const response = await apiClient.post('/api/my-resource', data)
    return response.data
  }
}
```

```typescript
// ❌ 错误：直接使用 axios 的自定义 API 模块
import axios from 'axios'

export const myCustomApi = {
  list: async () => {
    // 缺少认证 Token！
    const response = await axios.get('http://localhost:8000/api/my-resource')
    return response.data
  }
}
```

---

## 🛠️ 常用命令

### 开发命令

```bash
cd admin

# 启动开发服务器（热重载）
npm run dev

# 类型检查
npx tsc --noEmit

# ESLint检查
npm run lint

# 生产构建
npm run build

# 启动生产服务器
npm start
```

### Docker命令

```bash
# 启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 仅重启admin
docker-compose restart admin

# 查看admin日志
docker-compose logs -f admin

# 停止所有服务
docker-compose down

# 进入admin容器
docker-compose exec admin sh
```

---

## 📦 技术栈

### 前端框架
- **Next.js 14.2** - React框架（App Router）
- **React 18.3** - UI库
- **TypeScript 5.3** - 类型系统

### 状态管理
- **Zustand 4.5** - 轻量级状态管理
- **TanStack React Query 5.90** - 服务端状态管理

### UI组件
- **Radix UI** - 无头组件库（24+ 组件）
- **Tailwind CSS 3.4** - 原子化CSS
- **Sonner** - Toast 通知
- **Lucide React** - 图标库

### 开发工具
- **Monaco Editor** - 代码编辑器
- **Axios 1.6** - HTTP 客户端

### 监控和日志
- **Sentry** - 错误监控和性能追踪
- **自定义Logger** - 统一日志管理

---

## 🏗️ 项目结构

```
admin/
├── app/                          # Next.js App Router
│   ├── (dashboard)/             # 仪表板路由组
│   │   ├── page.tsx             # 主控制台
│   │   ├── concepts/            # 概念管理
│   │   ├── logs/                # 系统日志
│   │   ├── monitor/             # 性能监控
│   │   ├── sentiment/           # 市场情绪分析（6个页面）
│   │   ├── settings/            # 系统设置
│   │   ├── stocks/              # 股票管理
│   │   ├── strategies/          # 策略管理（7个页面）
│   │   ├── sync/                # 数据同步（5个页面）
│   │   └── users/               # 用户管理
│   ├── layout.tsx               # 全局布局（含Error Boundary）
│   └── login/                   # 登录页面
│
├── components/                   # React 组件
│   ├── ui/                      # Radix UI 基础组件（24+）
│   ├── auth/                    # 认证组件
│   ├── layout/                  # 布局组件
│   ├── stocks/                  # 股票相关组件
│   ├── strategies/              # 策略相关组件
│   ├── ErrorBoundary.tsx        # 全局错误边界 ✨ NEW
│   ├── TaskPanel.tsx            # 异步任务面板
│   └── TaskPollingProvider.tsx  # 任务轮询Provider
│
├── lib/                         # 工具库
│   ├── api-client.ts            # Axios API 客户端（1562行）
│   ├── logger.ts                # 统一日志系统 ✨ NEW
│   ├── error-formatter.ts       # 错误格式化
│   ├── jwt-utils.ts             # JWT 工具
│   └── react-query-config.ts    # React Query 配置
│
├── stores/                      # Zustand 状态管理
│   ├── auth-store.ts            # 认证状态（301行）
│   ├── config-store.ts          # 配置状态
│   ├── sidebar-store.ts         # 侧边栏状态
│   └── task-store.ts            # 异步任务状态
│
├── types/                       # TypeScript 类型定义
│   ├── index.ts
│   ├── stock.ts
│   ├── strategy.ts
│   └── sentiment.ts
│
├── sentry.client.config.ts      # Sentry 客户端配置 ✨ NEW
├── sentry.server.config.ts      # Sentry 服务端配置 ✨ NEW
├── sentry.edge.config.ts        # Sentry Edge 配置 ✨ NEW
├── instrumentation.ts           # Next.js 监控集成 ✨ NEW
├── next.config.mjs              # Next.js 配置
├── tailwind.config.ts           # Tailwind 配置
└── tsconfig.json                # TypeScript 配置
```

---

## 🔐 环境变量

**文件**: `.env.local` (本地开发) / `.env` (Docker)

```env
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Sentry Configuration (可选)
NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ORG=your-org
SENTRY_PROJECT=stock-analysis-admin
SENTRY_AUTH_TOKEN=your-token

# Environment
NODE_ENV=development
```

**注意**:
- ✅ `.env.local` 已在 `.gitignore` 中
- ⚠️ 不要提交包含真实 DSN 的文件到 Git

---

## 🐛 问题排查

### 问题1: "Module not found: Can't resolve '@sentry/nextjs'"

**原因**: Sentry依赖未安装

**解决**:
```bash
cd admin
npm install @sentry/nextjs --save
```

### 问题2: 开发服务器端口被占用

**错误**: `EADDRINUSE: address already in use :::3002`

**解决**:
```bash
# 查找并杀死进程
lsof -ti:3002 | xargs kill -9

# 或使用Docker重启
docker-compose restart admin
```

### 问题3: TypeScript 类型错误

**错误**: `Property 'code' does not exist on type 'ApiResponse'`

**原因**: API响应类型不一致（已在重构中修复）

**临时解决**: 使用类型断言
```typescript
const res = response as any
if (res.code === 200) { ... }
```

### 问题4: 热重载失败

**解决**:
```bash
# 清除缓存并重启
rm -rf .next
npm run dev
```

---

## ✅ 代码质量检查

### 构建前检查

```bash
# TypeScript 类型检查
npx tsc --noEmit

# ESLint 检查
npm run lint

# 完整构建测试
npm run build
```

### 代码规范

**禁止使用** (已在重构中替换):
- ❌ `console.log` → 使用 `logger.info()`
- ❌ `console.error` → 使用 `logger.error()`
- ❌ `console.warn` → 使用 `logger.warn()`

**推荐使用**:
- ✅ `logger.*` - 统一日志系统
- ✅ `useCallback` - 正确的依赖管理
- ✅ 类型安全的API调用

---

## 📊 性能监控

### Sentry性能追踪

```typescript
import logger from '@/lib/logger'

// 记录API响应时间
const start = performance.now()
const data = await apiClient.fetchData()
const duration = performance.now() - start

logger.performance('api-fetch-data', duration, 'ms', {
  endpoint: '/api/data',
  status: 'success'
})
```

### React Query 缓存配置

**位置**: [admin/lib/react-query-config.ts](../admin/lib/react-query-config.ts)

**默认配置**:
- `staleTime`: 5分钟
- `gcTime`: 10分钟
- `retry`: 3次

---

## 🎨 UI组件库

**基于 Radix UI + Tailwind CSS**

**已集成组件** (24+):
- Button, Input, Label, Select
- Card, Dialog, Sheet, Tabs
- Alert, Badge, Progress, Toast
- Table, Dropdown Menu, Command
- Avatar, Calendar, Checkbox, Switch
- Popover, Pagination, ScrollArea
- Slider, Radio Group, Separator
- Collapsible

**使用示例**:
```typescript
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

<Card>
  <CardHeader>
    <CardTitle>标题</CardTitle>
  </CardHeader>
  <CardContent>
    <Button onClick={handleClick}>点击</Button>
  </CardContent>
</Card>
```

---

## 🔄 最近重构内容

**日期**: 2026-03-14

### 完成的改进

1. ✅ **移除构建错误忽略**
   - 启用严格的 TypeScript 和 ESLint 检查
   - 修复 20+ 类型错误
   - 修复 12 个 ESLint 错误
   - 修复 26 个 React Hooks 警告

2. ✅ **添加全局 Error Boundary**
   - 优雅的错误UI
   - 自动错误上报
   - 错误恢复机制

3. ✅ **统一日志管理系统**
   - 创建 logger.ts
   - 替换所有 console 调用（28个文件）
   - 集成 Sentry

4. ✅ **引入 Sentry 监控**
   - 错误追踪
   - 性能监控
   - Session Replay
   - 用户行为追踪

**详细文档**: [admin/REFACTORING_SUMMARY.md](../admin/REFACTORING_SUMMARY.md)

---

## 📚 相关文档

- [重构总结](../admin/REFACTORING_SUMMARY.md) - 完整的重构记录
- [Docker配置](./HOOKS_DOCKER_CONFIG.md) - Docker Compose 配置说明
- [开发环境](./HOOKS_DEV_ENV.md) - Hooks 和开发环境配置
- [Next.js 文档](https://nextjs.org/docs)
- [Sentry Next.js](https://docs.sentry.io/platforms/javascript/guides/nextjs/)

---

## 🆘 获取帮助

**问题排查顺序**:
1. 查看本文档的"问题排查"部分
2. 查看 [REFACTORING_SUMMARY.md](../admin/REFACTORING_SUMMARY.md)
3. 检查服务日志: `docker-compose logs -f admin`
4. 检查Sentry错误面板（如已配置）

**常用链接**:
- Admin前端: http://localhost:3002
- Backend API: http://localhost:8000
- API文档: http://localhost:8000/docs

---

**最后更新**: 2026-03-14
**维护者**: Stock Analysis Team
