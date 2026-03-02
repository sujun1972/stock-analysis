# Frontend - A股AI量化交易系统前端

基于 **Next.js 14** 的现代化前端应用，使用 TypeScript、Tailwind CSS 构建。

## 🚀 技术栈

- **框架**: Next.js 14 (App Router)
- **语言**: TypeScript
- **样式**: Tailwind CSS + shadcn/ui
- **状态管理**: Zustand (with persist)
- **HTTP客户端**: Axios
- **图表**: ECharts, Highcharts, Lightweight Charts
- **日期处理**: date-fns
- **认证**: JWT (Access Token + Refresh Token)

## 📁 项目结构

```
frontend/
├── src/
│   ├── app/              # Next.js App Router页面
│   │   ├── layout.tsx    # 根布局
│   │   ├── page.tsx      # 首页
│   │   ├── stocks/       # 股票列表页
│   │   └── globals.css   # 全局样式
│   ├── components/       # React组件
│   ├── lib/              # 工具库
│   │   └── api-client.ts # API客户端
│   ├── store/            # Zustand状态管理
│   │   └── stock-store.ts
│   ├── types/            # TypeScript类型定义
│   │   └── stock.ts
│   └── hooks/            # 自定义Hooks
├── public/               # 静态资源
├── Dockerfile            # Docker镜像定义
├── next.config.mjs       # Next.js配置
├── tailwind.config.ts    # Tailwind配置
├── tsconfig.json         # TypeScript配置
└── package.json
```

## 🛠️ 本地开发

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 后端API地址
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 4. 其他命令

```bash
# 构建生产版本
npm run build

# 启动生产服务器
npm start

# 运行ESLint检查
npm run lint
```

## 🐳 Docker部署

### 使用Docker Compose（推荐）

```bash
# 从项目根目录运行
cd ..
docker-compose up -d frontend
```

### 单独构建

```bash
# 构建镜像
docker build -t stock-frontend .

# 运行容器
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://backend:8000 \
  stock-frontend
```

## 📦 主要功能

### 1. 用户认证系统

- **登录/注册**: 支持邮箱密码登录，JWT双Token机制
- **Token管理**: 自动预刷新（过期前5分钟）、请求队列管理
- **路由保护**: 灵活的可选登录模式，支持角色权限控制
- **用户中心**: 个人资料管理、配额查看、角色权益展示

### 2. 首页 (`/`)

- 系统概览
- 功能介绍
- 后端服务健康检查

### 3. 股票列表 (`/stocks`)

- 显示所有A股股票
- 支持搜索和筛选（市场、概念板块）
- 分页浏览
- 实时行情智能刷新

### 4. 策略中心 (`/strategies`)

- 浏览所有已启用的策略（内置/AI/自定义）
- 按用户和类别筛选策略
- 策略搜索和克隆
- 快速跳转到回测页面

### 5. 我的策略 (`/my-strategies`)

- 管理当前用户创建的所有策略（包括启用和未启用的）
- 支持多维度筛选（策略类型、状态、类别）
- 策略编辑、删除、克隆
- 策略验证和启用/禁用管理
- 需要登录才能访问

### 6. 回测系统 (`/backtest`)

- 支持多种策略类型
- 股票池选择
- 日期范围配置
- 回测结果可视化

### 7. AI实验舱 (`/ai-lab`)

- ML模型训练
- 预测分析
- 模型性能评估

## 🔌 API集成

前端通过 `src/lib/api-client.ts` 与后端通信：

```typescript
import { apiClient } from '@/lib/api-client'

// 获取股票列表
const stocks = await apiClient.getStockList({ limit: 20 })

// 获取日线数据
const dailyData = await apiClient.getDailyData('000001')

// 计算特征
await apiClient.calculateFeatures('000001')
```

### Token自动刷新机制

API客户端内置智能Token管理：

- **预刷新**: Token过期前5分钟自动刷新
- **请求队列**: 多个并发请求时只刷新一次Token
- **自动重试**: 401错误时自动刷新Token并重试原请求
- **智能重定向**: 刷新失败时保存当前路径用于登录后回跳

## 🎨 样式系统

使用 Tailwind CSS 和自定义类：

```tsx
// 使用预定义的样式类
<div className="card">
  <button className="btn-primary">提交</button>
  <input className="input-field" />
</div>
```

自定义类定义在 `src/app/globals.css`：
- `.card` - 卡片容器
- `.btn-primary` - 主按钮
- `.btn-secondary` - 次按钮
- `.input-field` - 输入框
- `.table-row` - 表格行

## 📊 状态管理

使用 Zustand 管理全局状态：

```typescript
// 股票状态
import { useStockStore } from '@/store/stock-store'

function MyComponent() {
  const { stocks, setStocks, isLoading } = useStockStore()
  // 使用状态...
}

// 认证状态
import { useAuthStore, isVipUser } from '@/stores/auth-store'

function AuthComponent() {
  const { user, isAuthenticated, login, logout } = useAuthStore()

  // 使用辅助函数检查权限
  if (isVipUser()) {
    // VIP功能
  }
}
```

### 认证辅助函数

- `isAdmin()` - 检查是否为管理员
- `isSuperAdmin()` - 检查是否为超级管理员
- `isVipUser()` - 检查是否为VIP用户
- `isTrialUser()` - 检查是否为试用用户
- `hasPremiumAccess()` - 检查是否有高级权限
- `getRoleDisplayName(role)` - 获取角色显示名称

## 🔄 开发流程

### 添加新页面

```bash
# 1. 创建页面目录
mkdir -p src/app/my-page

# 2. 创建页面文件
touch src/app/my-page/page.tsx

# 3. 编写页面组件
# src/app/my-page/page.tsx
export default function MyPage() {
  return <div>My Page</div>
}
```

### 添加新API接口

编辑 `src/lib/api-client.ts`：

```typescript
class ApiClient {
  // 添加新方法
  async getMyData(): Promise<MyData> {
    const response = await axiosInstance.get('/api/my-data')
    return response.data
  }
}
```

### 添加新组件

```bash
# 创建组件文件
touch src/components/MyComponent.tsx
```

```tsx
// src/components/MyComponent.tsx
export default function MyComponent() {
  return <div>My Component</div>
}
```

## 🌐 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `NEXT_PUBLIC_API_URL` | 后端API地址 | `http://localhost:8000` |

> **注意**: 以 `NEXT_PUBLIC_` 开头的变量会暴露到浏览器端

## 📝 注意事项

1. **API调用**: 所有API调用都应使用 `apiClient`，不要直接使用 `axios`
2. **类型安全**: 充分利用TypeScript类型系统，避免使用 `any`
3. **错误处理**: 所有API调用都应包含错误处理
4. **加载状态**: 使用 `isLoading` 状态显示加载指示器
5. **响应式设计**: 使用Tailwind的响应式类（`sm:`, `md:`, `lg:`）

## 🔗 相关文档

- [Next.js文档](https://nextjs.org/docs)
- [Tailwind CSS文档](https://tailwindcss.com/docs)
- [Zustand文档](https://github.com/pmndrs/zustand)
- [项目根目录README](../README.md)
- [Backend README](../backend/README.md)

## 🐛 故障排除

### 问题1: 无法连接后端

**症状**: 前端显示"无法连接到后端服务"

**解决方案**:
1. 确认后端服务正在运行 (`docker-compose ps`)
2. 检查 `NEXT_PUBLIC_API_URL` 环境变量配置
3. 查看浏览器控制台网络请求

### 问题2: 样式不生效

**症状**: Tailwind CSS类不起作用

**解决方案**:
1. 确认 `globals.css` 已导入到 `layout.tsx`
2. 重启开发服务器
3. 清除 `.next` 缓存: `rm -rf .next`

### 问题3: Docker构建失败

**症状**: `docker-compose build frontend` 失败

**解决方案**:
1. 检查 Node.js 版本（需要 20+）
2. 删除 `node_modules` 重新安装
3. 查看构建日志: `docker-compose logs frontend`

## 🔐 路由保护

使用 `ProtectedRoute` 组件保护需要认证的页面：

```tsx
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

// 必须登录
export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <ProfileContent />
    </ProtectedRoute>
  )
}

// 可选登录（未登录也可访问）
export default function StocksPage() {
  return (
    <ProtectedRoute requireAuth={false}>
      <StocksContent />
    </ProtectedRoute>
  )
}

// 限制特定角色
export default function AdminPage() {
  return (
    <ProtectedRoute allowedRoles={['admin', 'super_admin']}>
      <AdminContent />
    </ProtectedRoute>
  )
}
```

## 🎨 UI组件系统

基于 shadcn/ui + Radix UI 构建，支持暗黑模式：

- **表单组件**: Button, Input, Label, Select, Checkbox, Switch
- **布局组件**: Card, Dialog, Sheet, Tabs, Separator
- **反馈组件**: Toast, Alert, Progress, Badge
- **导航组件**: DropdownMenu, Avatar
- **数据展示**: Table, Pagination

所有组件位于 `src/components/ui/`

## 📄 页面路由说明

| 路由 | 说明 | 是否需要登录 |
|------|------|-------------|
| `/` | 首页，系统概览 | 否 |
| `/stocks` | 股票列表，浏览所有A股 | 否 |
| `/strategies` | 策略中心，浏览已启用的策略 | 否 |
| `/my-strategies` | 我的策略，管理自己创建的策略 | **是** |
| `/strategies/create` | 创建新策略 | **是** |
| `/strategies/{id}/edit` | 编辑策略 | **是** |
| `/strategies/{id}/code` | 查看策略代码 | 否 |
| `/backtest` | 回测系统 | 否（登录后有更多功能） |
| `/my-backtests` | 我的回测记录 | **是** |
| `/ai-lab` | AI实验舱 | 否（登录后有更多功能） |
| `/profile` | 个人中心 | **是** |
| `/login` | 登录页面 | 否 |
| `/register` | 注册页面 | 否 |

---

**最后更新**: 2026-03-02
