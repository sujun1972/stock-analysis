# 管理后台 (Admin)

股票分析系统的独立管理前端，负责系统设置、数据同步和系统监控等管理功能。

## 🎯 功能模块

### 1. 控制台 (/)
- 系统状态监控
- 股票数据统计
- 快捷操作入口
- 系统信息展示

### 2. 系统设置 (/settings)
- 数据源配置 (AkShare / Tushare)
- Tushare API Token 管理
- 分时数据源设置
- 实时数据源设置

### 3. 数据同步 (/sync)
- 数据初始化 (/sync/initialize)
- 新股列表同步 (/sync/new-stocks)
- 退市列表同步 (/sync/delisted-stocks)
- 实时行情同步 (/sync/realtime)

### 4. 系统日志 (/logs) [待实现]
- 系统日志查看
- 错误日志追踪
- 操作审计日志

### 5. 性能监控 (/monitor) [待实现]
- 系统性能指标
- 数据库状态
- API调用统计

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
│   ├── settings/          # 系统设置
│   │   ├── page.tsx
│   │   └── scheduler/     # 定时任务管理
│   ├── sync/              # 数据同步
│   │   ├── page.tsx
│   │   ├── initialize/
│   │   ├── new-stocks/
│   │   ├── delisted-stocks/
│   │   └── realtime/
│   ├── logs/              # 系统日志 [待实现]
│   └── monitor/           # 性能监控 [待实现]
├── components/
│   ├── ui/                # UI组件库 (shadcn/ui)
│   ├── layouts/
│   │   └── AdminLayout.tsx  # 管理后台布局
│   └── sync/              # 同步相关组件
├── lib/
│   ├── api-client.ts      # API客户端
│   ├── utils.ts           # 工具函数
│   └── react-query-config.ts
├── types/                 # TypeScript类型定义
├── public/                # 静态资源
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
- **状态管理**: Zustand
- **数据查询**: @tanstack/react-query
- **HTTP客户端**: Axios
- **图标**: Lucide React

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

## 🔐 未来扩展

1. **用户管理**
   - 用户列表和权限管理
   - 角色配置
   - 登录日志

2. **高级监控**
   - 实时性能仪表板
   - 告警配置
   - 系统健康检查

3. **数据库管理**
   - 表结构查看
   - SQL查询执行器
   - 数据备份/恢复

4. **定时任务管理**
   - Cron表达式编辑
   - 任务执行历史
   - 手动触发任务

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
