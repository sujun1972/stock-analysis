# 管理后台 (Admin)

股票分析系统的独立管理前端，负责系统设置、数据同步和系统监控等管理功能。

## 🎯 功能模块

### 1. 控制台 (/)
- 系统状态监控
- 股票数据统计
- 快捷操作入口
- 系统信息展示

### 2. 个人资料 (/profile)
- 查看个人基本信息（姓名、邮箱、角色等）
- 编辑个人资料（姓名、手机、头像）
- 修改登录密码
- 默认头像支持

### 3. 系统设置 (/settings)
- 数据源配置 (AkShare / Tushare)
- Tushare API Token 管理
- 分时数据源设置
- 实时数据源设置

### 4. 用户管理 (/users)
- 用户列表展示（分页、搜索、筛选）
- 创建新用户（含密码强度验证）
- 编辑用户信息（邮箱、角色、全名等）
- 删除用户（含二次确认）
- 查看用户详细信息（配额、登录统计、创建时间）
- 邮箱验证状态管理（管理员可手动设置）
- 权限和角色管理（5种角色）
- 配额使用情况展示（带进度条可视化）
- **响应式设计**：桌面端表格视图 + 移动端卡片视图

### 5. 策略管理 (/strategies)
- 策略列表、创建、编辑和详情
- 支持三种策略类型：选股策略、入场策略、离场策略
- 用户策略关联（用户可管理自己的策略）
- Monaco Editor代码编辑（类VSCode编辑器）
- 策略代码验证和风险评估
- 系统内置策略（只读）
- 策略使用统计和回测统计

### 6. 股票管理 (/stocks)
- 股票列表展示（分页、搜索、排序）
- 多维度筛选（市场、概念板块、状态）
- 实时行情数据展示
- 股票详情查看（基本信息、概念标签）
- 概念标签编辑
- 批量同步实时行情
- 懒加载概念选择器（后端搜索、无限滚动）

### 7. 概念管理 (/concepts)
- 概念板块列表（分页、搜索）
- 创建、编辑、删除概念
- 从东方财富同步概念数据（466个概念 + 成分股）
- 概念成分股查看
- 股票数量统计

### 8. 数据同步 (/sync)
- 数据初始化 (/sync/initialize)
- 新股列表同步 (/sync/new-stocks)
- 退市列表同步 (/sync/delisted-stocks)
- 实时行情同步 (/sync/realtime)

### 9. 系统日志 (/logs)
- 用户活动日志查看
- 登录历史追踪
- 操作类型筛选
- 用户搜索和过滤

### 10. 性能监控 (/monitor)
- 系统健康状态检查
- 数据库和Redis连接监控
- API性能指标
- 自动/手动刷新模式

## 🚀 快速开始

### 开发模式

```bash
# 进入admin目录
cd admin

# 安装依赖
npm install

# 启动开发服务器 (端口: 3002)
npm run dev
```

访问: http://localhost:3002

### 生产部署

```bash
# 使用Docker Compose启动所有服务
docker-compose up -d admin

# 或单独构建admin镜像
cd admin
docker build -t stock-admin .
docker run -p 3002:3002 -e NEXT_PUBLIC_API_URL=http://backend:8000 stock-admin
```

访问: http://localhost:3002

## 📁 目录结构

```
admin/
├── app/                    # Next.js App Router
│   ├── page.tsx           # 控制台首页
│   ├── layout.tsx         # 根布局
│   ├── globals.css        # 全局样式
│   ├── login/             # 登录页面
│   ├── profile/           # 个人资料管理
│   │   └── page.tsx
│   ├── users/             # 用户管理
│   ├── strategies/        # 策略管理
│   │   ├── page.tsx       # 策略列表
│   │   ├── new/           # 创建策略
│   │   │   └── page.tsx
│   │   └── [id]/          # 策略详情和编辑
│   │       ├── page.tsx   # 策略详情
│   │       └── edit/
│   │           └── page.tsx  # 编辑策略
│   ├── settings/          # 系统设置
│   │   ├── page.tsx
│   │   └── scheduler/     # 定时任务管理
│   ├── sync/              # 数据同步
│   │   ├── page.tsx
│   │   ├── initialize/
│   │   ├── new-stocks/
│   │   ├── delisted-stocks/
│   │   └── realtime/
│   ├── stocks/            # 股票管理
│   │   └── page.tsx
│   ├── concepts/          # 概念管理
│   │   └── page.tsx
│   ├── logs/              # 系统日志
│   │   └── page.tsx
│   └── monitor/           # 性能监控
│       └── page.tsx
├── components/
│   ├── ui/                # UI组件库 (shadcn/ui)
│   │   ├── separator.tsx  # 分隔线组件
│   │   └── ...
│   ├── auth/              # 认证组件
│   │   └── ProtectedRoute.tsx
│   ├── stocks/            # 股票相关组件
│   │   ├── LazyConceptSelect.tsx  # 懒加载概念选择器
│   │   ├── SimpleConceptSelect.tsx
│   │   └── StockDetailDialog.tsx
│   ├── layout/
│   │   └── Header.tsx     # 顶部用户信息栏
│   ├── layouts/
│   │   └── AdminLayout.tsx  # 管理后台布局 (侧边栏+Header)
│   └── sync/              # 同步相关组件
├── stores/                # Zustand状态管理
│   ├── auth-store.ts      # 认证状态
│   └── config-store.ts    # 配置缓存
├── lib/
│   ├── api-client.ts      # API客户端
│   ├── utils.ts           # 工具函数
│   └── react-query-config.ts
├── types/                 # TypeScript类型定义
├── public/                # 静态资源
│   └── assets/
│       └── default-avatar.svg  # 默认用户头像
├── Dockerfile             # Docker配置
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.mjs
```

## 🔧 技术栈

- **框架**: Next.js 14 (App Router)
- **语言**: TypeScript
- **样式**: Tailwind CSS
- **UI组件**: Radix UI + shadcn/ui
- **状态管理**: Zustand (auth-store, config-store)
- **数据查询**: @tanstack/react-query
- **HTTP客户端**: Axios (带Token自动注入和刷新)
- **图标**: Lucide React
- **代码编辑器**: Monaco Editor (VSCode内核)
- **通知**: Sonner (Toast notifications)

## 🏗️ 架构设计

### 布局结构

采用经典的**侧边栏 + 顶部栏**的管理后台布局：

```
┌─────────────┬──────────────────────────────────┐
│             │  Header (用户头像、资料、登出)      │
│  Sidebar    ├──────────────────────────────────┤
│  (导航菜单)  │                                  │
│             │  Main Content                    │
│             │                                  │
└─────────────┴──────────────────────────────────┘
```

- **AdminLayout**: 主布局组件,包含侧边栏和Header
- **Header**: 顶部用户信息栏
  - 用户头像和角色标识
  - 下拉菜单(个人资料、设置、登出)
  - 默认头像支持(`/assets/default-avatar.svg`)

### 状态管理

采用 Zustand 进行全局状态管理，主要包括：

1. **auth-store** - 认证状态管理
   - 用户信息和Token管理
   - 登录/登出/Token刷新
   - localStorage持久化
   - 优化：只在首次加载时从localStorage恢复，不重复调用API

2. **config-store** - 配置缓存管理
   - 数据源配置缓存（5分钟有效期）
   - 避免重复API请求
   - 支持强制刷新

### 请求拦截

- **请求拦截器**:
  - 自动注入JWT Token到请求头
  - JWT过期检测（解析token exp字段）
  - Token预刷新机制（提前5分钟自动刷新）
  - 刷新互斥锁（防止并发刷新）

- **响应拦截器**:
  - 401错误自动刷新Token并重试原请求
  - 刷新请求排队机制（避免重复刷新）
  - Token刷新失败自动登出并友好提示
  - 避免刷新死循环（不对refresh/login请求刷新）

### 路由保护

使用 `ProtectedRoute` 组件保护所有管理页面：
- 未登录自动跳转登录页
- 权限检查（管理员/超级管理员）
- 优化：只在首次挂载时检查认证状态

## 🌐 环境变量

创建 `.env.local` 文件：

```env
# API服务地址
NEXT_PUBLIC_API_URL=http://localhost:8000

# 环境标识
NODE_ENV=development
```

## 📊 与主前端的区别

| 特性 | Frontend (用户前端) | Admin (管理后台) |
|------|---------------------|------------------|
| **端口** | 3000 | 3002 |
| **职责** | 股票分析、策略回测、数据可视化 | 系统管理、数据同步、监控 |
| **目标用户** | 普通用户、分析师 | 系统管理员 |
| **主要功能** | 策略中心、回测系统、AI实验舱 | 系统设置、数据同步、日志监控 |
| **布局** | 顶部导航 + 内容区 | 侧边栏导航 + 控制台风格 |

## 🔐 已实现的核心功能

1. **认证系统**
   - JWT Token认证（access_token + refresh_token）
   - 智能Token刷新（提前5分钟预刷新 + 401时重试刷新）
   - 刷新互斥锁机制（防止并发刷新竞态条件）
   - 权限控制（管理员/超级管理员）
   - 登录状态持久化（Zustand persist）
   - 登录失败友好提示（Toast通知 + 路径保留）

2. **配置管理**
   - 数据源配置缓存 (5分钟有效期)
   - 避免重复API请求
   - 自动状态同步

3. **用户管理**
   - 用户CRUD操作（创建、编辑、删除）
   - 密码强度验证（8位+大小写字母+数字）
   - 用户详情弹窗（完整信息查看）
   - 邮箱验证状态管理
   - 角色和权限管理（5种角色）
   - 配额使用情况可视化（进度条）
   - 登录历史和活动日志查看
   - 响应式设计（桌面表格 + 移动卡片）
   - 操作下拉菜单（详情、编辑、删除）

4. **股票和概念管理**
   - 股票列表分页、搜索和筛选
   - 懒加载概念选择器（后端搜索、300ms防抖、无限滚动）
   - React Portal渲染（避免z-index问题）
   - 概念板块CRUD操作
   - 东方财富数据源同步（466个概念 + 成分股）
   - 股票-概念多对多关系管理

5. **系统监控**
   - 实时健康状态检查
   - 数据库和Redis监控
   - 自动刷新机制
   - 性能指标展示

## 🚧 未来扩展

1. **高级监控**
   - 系统资源使用率（CPU、内存、磁盘）
   - 实时告警配置
   - 历史趋势图表
   - Prometheus指标集成

2. **数据库管理**
   - 表结构查看
   - SQL查询执行器
   - 数据备份/恢复

3. **定时任务增强**
   - 可视化Cron表达式编辑器
   - 任务执行详细日志
   - 失败重试配置

## 📝 开发指南

### 添加新页面

1. 在 `app/` 下创建新目录和 `page.tsx`
2. 使用 `AdminLayout` 包装页面内容
3. 更新 `components/layouts/AdminLayout.tsx` 中的导航菜单

```tsx
// app/new-page/page.tsx
'use client'

import AdminLayout from '@/components/layouts/AdminLayout'

export default function NewPage() {
  return (
    <AdminLayout>
      <div>
        <h1>新页面</h1>
      </div>
    </AdminLayout>
  )
}
```

### API调用

使用 `lib/api-client.ts` 中的客户端：

```tsx
import { apiClient } from '@/lib/api-client'

// 获取数据源配置
const config = await apiClient.getDataSourceConfig()

// 更新配置
await apiClient.updateDataSourceConfig({
  data_source: 'akshare',
  tushare_token: 'your_token'
})
```

## 🐛 问题排查

### 启动失败

```bash
# 清除缓存重新安装
rm -rf node_modules .next
npm install
npm run dev
```

### 端口冲突

修改 `package.json`:

```json
{
  "scripts": {
    "dev": "next dev -p 3003"  // 改为其他端口
  }
}
```

### API连接失败

检查环境变量 `NEXT_PUBLIC_API_URL` 是否正确指向后端服务。

## 📄 许可证

与主项目相同

## 🙋 支持

如有问题，请在主项目仓库提交Issue。
