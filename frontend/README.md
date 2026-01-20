# Frontend - A股AI量化交易系统前端

基于 **Next.js 14** 的现代化前端应用，使用 TypeScript、Tailwind CSS 构建。

## 🚀 技术栈

- **框架**: Next.js 14 (App Router)
- **语言**: TypeScript
- **样式**: Tailwind CSS
- **状态管理**: Zustand
- **HTTP客户端**: Axios
- **图表**: Recharts
- **日期处理**: date-fns

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

### 1. 首页 (`/`)

- 系统概览
- 功能介绍
- 后端服务健康检查

### 2. 股票列表 (`/stocks`)

- 显示所有A股股票
- 支持搜索和筛选
- 分页浏览
- 跳转到分析页面

### 3. 数据分析 (`/analysis`) - 待实现

- 股票数据可视化
- 技术指标计算
- 特征工程

### 4. 策略回测 (`/backtest`) - 待实现

- 回测参数配置
- 回测结果展示
- 绩效分析

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
import { useStockStore } from '@/store/stock-store'

function MyComponent() {
  const { stocks, setStocks, isLoading } = useStockStore()

  // 使用状态...
}
```

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

---

**最后更新**: 2026-01-20
